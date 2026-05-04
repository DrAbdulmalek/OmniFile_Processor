"""
مهام الخلفية غير المتزامنة (Celery Tasks)
==============================================
معالجة الملفات بشكل غير متزامن باستخدام Celery + Redis.

الاستخدام:
    # تشغيل Redis
    redis-server

    # تشغيل worker
    celery -A tasks worker --loglevel=info

    # من الكود
    from tasks import process_ocr_async
    result = process_ocr_async.delay(file_path, options)
"""

import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# تهيئة Celery (اختياري - يعمل فقط إذا كان Redis متاحاً)
_celery_app = None
CELERY_AVAILABLE = False

try:
    from celery import Celery

    _celery_app = Celery(
        "omnifile_tasks",
        broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    )

    _celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=600,  # 10 دقائق كحد أقصى
        task_soft_time_limit=540,  # 9 دقائق تحذير
    )

    CELERY_AVAILABLE = True
    logger.info("تم تهيئة Celery بنجاح")
except ImportError:
    logger.info("Celery غير مثبت. المهام غير المتزامنة غير متوفرة.")
except Exception as e:
    logger.warning("فشل تهيئة Celery: %s", e)


def run_ocr_task(
    file_path: str,
    options: Optional[dict] = None,
) -> dict:
    """
    معالجة OCR لملف (متزامنة - يمكن استدعاؤها مباشرة).

    المعاملات:
        file_path: مسار الملف
        options: إعدادات إضافية

    العائد:
        نتيجة المعالجة
    """
    start_time = time.time()
    options = options or {}

    try:
        from config import OmniFileConfig
        from modules.vision.ocr_engine import OCREngine

        # إعداد الإعدادات
        cfg = OmniFileConfig()

        # تطبيق الخيارات
        if options.get("enable_trocr") is not None:
            cfg.enable_trocr = options["enable_trocr"]
        if options.get("enable_easyocr") is not None:
            cfg.enable_easyocr = options["enable_easyocr"]
        if options.get("enable_tesseract") is not None:
            cfg.enable_tesseract = options["enable_tesseract"]
        if options.get("use_gpu") is not None:
            cfg.use_gpu = options["use_gpu"]

        # إنشاء محرك OCR
        engine = OCREngine(
            trocr_model_name=cfg.trocr_model_name,
            easyocr_languages=cfg.easyocr_languages,
            tesseract_langs=cfg.tesseract_langs,
            use_gpu=cfg.use_gpu,
            enable_trocr=cfg.enable_trocr,
            enable_easyocr=cfg.enable_easyocr,
            enable_tesseract=cfg.enable_tesseract,
        )

        # معالجة الملف
        if file_path.lower().endswith(".pdf"):
            results = engine.recognize_pdf(file_path)
        else:
            from PIL import Image
            img = Image.open(file_path)
            result = engine.recognize(img)
            results = [result]

        duration = time.time() - start_time

        return {
            "success": True,
            "file_path": file_path,
            "results": results,
            "processing_time": duration,
            "pages_processed": len(results),
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error("فشلت معالجة '%s': %s", file_path, e)

        return {
            "success": False,
            "file_path": file_path,
            "error": str(e),
            "processing_time": duration,
            "pages_processed": 0,
        }


# تسجيل المهام في Celery إذا كان متاحاً
if CELERY_AVAILABLE and _celery_app is not None:

    @_celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
    def process_ocr_async(self, file_path: str, options: Optional[dict] = None):
        """
        معالجة OCR بشكل غير متزامن عبر Celery.

        المعاملات:
            file_path: مسار الملف
            options: إعدادات إضافية

        العائد:
            نتيجة المعالجة
        """
        try:
            return run_ocr_task(file_path, options)
        except Exception as exc:
            logger.error("فشلت المهمة غير المتزامنة: %s", exc)
            raise self.retry(exc=exc)

    @_celery_app.task(bind=True, max_retries=2)
    def process_batch_async(self, file_paths: list[str], options: Optional[dict] = None):
        """
        معالجة دفعة ملفات بشكل غير متزامن.

        المعاملات:
            file_paths: قائمة مسارات الملفات
            options: إعدادات إضافية

        العائد:
            قائمة نتائج المعالجة
        """
        results = []
        for fp in file_paths:
            try:
                result = run_ocr_task(fp, options)
                results.append(result)
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": len(results),
                        "total": len(file_paths),
                        "file": fp,
                    },
                )
            except Exception as e:
                results.append({
                    "success": False,
                    "file_path": fp,
                    "error": str(e),
                })

        return {
            "total_files": len(file_paths),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results,
        }
