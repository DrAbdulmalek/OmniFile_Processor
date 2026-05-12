"""
backend/celery_worker.py
========================
Celery worker for Medical OCR async processing.
عامل Celery لمعالجة OCR الطبي بشكل غير متزامن.

يتم استخدامه مع FastAPI لمعالجة الملفات الكبيرة في الخلفية
مع إمكانية تتبع التقدم عبر Celery + Redis.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from celery import Celery

# إعداد Celery (يقرأ Redis URL من البيئة أو القيمة الافتراضية)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "medical_ocr",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,       # 30 دقيقة كحد أقصى
    task_soft_time_limit=25 * 60,  # 25 دقيقة تحذير
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@celery_app.task(bind=True, name="medical_ocr.process_pdf")
def process_pdf_task(
    self,
    file_path: str,
    max_pages: Optional[int] = None,
    use_gpu: bool = False,
):
    """
    مهمة Celery لمعالجة ملف PDF باستخدام OCR الطبي.

    Args:
        self: مرجع المهمة (bind=True)
        file_path: مسار ملف PDF
        max_pages: الحد الأقصى لعدد الصفحات
        use_gpu: استخدام GPU

    Returns:
        dict: نتائج المعالجة مع مسارات الملفات
    """
    import time

    start_time = time.time()
    file_path = Path(file_path)

    try:
        if not file_path.exists():
            raise FileNotFoundError(f"الملف غير موجود: {file_path}")

        # تحديث الحالة: بدء المعالجة
        self.update_state(
            state="PROCESSING",
            meta={"progress": 0, "message": "بدء المعالجة..."},
        )

        # تحميل المعالج (lazy loading)
        from modules.vision.medical_ocr import MedicalOCRProcessor

        ocr = MedicalOCRProcessor(use_gpu=use_gpu)

        self.update_state(
            state="PROCESSING",
            meta={"progress": 10, "message": "جاري استخراج النصوص..."},
        )

        # معالجة الملف
        results = ocr.process_pdf(file_path, max_pages=max_pages)

        self.update_state(
            state="PROCESSING",
            meta={"progress": 60, "message": "حفظ النتائج..."},
        )

        # حفظ النتائج
        output_dir = Path(tempfile.mkdtemp()) / "ocr_output"
        json_path = ocr.save_results(results, output_dir)
        html_path = ocr.generate_html_review(results, output_dir / "review.html")

        self.update_state(
            state="PROCESSING",
            meta={"progress": 85, "message": "تجهيز الملفات النهائية..."},
        )

        # نسخ الملفات إلى موقع دائم
        final_dir = Path("media/ocr_results")
        final_dir.mkdir(parents=True, exist_ok=True)

        task_id = self.request.id
        final_json = final_dir / f"{task_id}_results.json"
        final_html = final_dir / f"{task_id}_review.html"
        shutil.copy(json_path, final_json)
        shutil.copy(html_path, final_html)

        processing_time = round((time.time() - start_time) * 1000, 2)
        total_lines = sum(len(p.get("lines", [])) for p in results)

        self.update_state(
            state="PROCESSING",
            meta={"progress": 100, "message": "تمت المعالجة بنجاح!"},
        )

        return {
            "status": "completed",
            "json_file": str(final_json),
            "html_file": str(final_html),
            "total_pages": len(results),
            "total_lines": total_lines,
            "processing_time_ms": processing_time,
        }

    except FileNotFoundError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="medical_ocr.health_check")
def health_check_task():
    """مهمة فحص صحة النظام."""
    try:
        import easyocr
        return {"status": "healthy", "easyocr_available": True}
    except ImportError:
        return {"status": "degraded", "easyocr_available": False}
