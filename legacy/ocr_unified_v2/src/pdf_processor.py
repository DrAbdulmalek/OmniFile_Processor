"""
HandwrittenOCR - معالجة PDF v5.4
====================================
المحسنات الرئيسية:
- PyMuPDF (fitz) بدلاً من pdf2image — أسرع 10x وأخف بمراحل
- تتبع الذاكرة التفصيلي لتشخيص OOM
- Batch TrOCR inference (3-6x تسريع)
- Smart Ensemble: تخطي TrOCR إذا ثقة EasyOCR عالية
- run_id tracking + processing_runs table
- DELETE-before-INSERT لمنع التكرار
- Checkpoint للاستئناف
- دعم PDF + صور منفصلة
- حماية قاعدة البيانات عند المزامنة (File Locking + Sync Status)
- v5.3: تحسين الذاكرة — تحميل صفحة بصفحة + تنظيف ذاكرة صريح
- v5.4: PyMuPDF + تتبع الذاكرة + تخطي المدققات الإملائية في الوضع الخفيف
"""

import cv2
import json
import time
import gc
import os
import resource
import logging
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import torch

from config import Config
from src.preprocessing import (
    preprocess_image, smart_segmentation,
    match_boxes_with_detections, crop_safe,
)
from src.recognition import OCREngine
from src.correction import (
    build_correction_dict,
    apply_correction_dict, spell_correct_word,
)
from src.database import HandwritingDB
from src.sync import FileLock, SyncManager

logger = logging.getLogger("HandwrittenOCR")


def _get_memory_mb() -> int:
    """قراءة الذاكرة المستخدمة بالعملية الحالية (RSS) بالميجابايت."""
    try:
        # الطريقة 1: /proc/self/status (Linux)
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    try:
        # الطريقة 2: resource (cross-platform)
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    except Exception:
        pass
    return -1


def _load_page_fitz(pdf_path: str, page_num: int, dpi: int) -> np.ndarray:
    """تحميل صفحة PDF واحدة باستخدام PyMuPDF — أخف بـ 10x من pdf2image.

    Returns:
        numpy array BGR أو None إذا فشل.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF غير مثبت — يُرجى تثبيته: pip install PyMuPDF")
        return None

    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num - 1)  # الفهرس يبدأ من 0

        # تحويل DPI إلى مقياس fitz (72 = DPI الأساسية)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # تحويل Pixmap إلى numpy array
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

        doc.close()

        # تحويل الألوان إلى BGR (OpenCV format)
        if pix.n == 4:    # RGBA → BGR
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 1:  # Gray → BGR
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:             # RGB → BGR
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        return img

    except Exception as e:
        logger.error(f"PyMuPDF فشل في تحميل صفحة {page_num}: {e}")
        return None


def _load_page_pdf2image(pdf_path: str, page_num: int, dpi: int) -> np.ndarray:
    """تحميل صفحة PDF باستخدام pdf2image (بديل إذا PyMuPDF غير متاح).

    Returns:
        numpy array BGR أو None إذا فشل.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.error("pdf2image غير مثبت — يُرجى تثبيته: pip install pdf2image")
        return None

    try:
        page_images = convert_from_path(
            pdf_path, dpi=dpi,
            first_page=page_num, last_page=page_num,
        )
        if not page_images:
            return None
        pil_img = page_images[0]
        del page_images

        arr_rgb = np.array(pil_img)
        img_bgr = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)
        del arr_rgb, pil_img
        return img_bgr

    except Exception as e:
        logger.error(f"pdf2image فشل في تحميل صفحة {page_num}: {e}")
        return None


class PDFProcessor:
    """معالج ملفات PDF مع Batch TrOCR + Smart Ensemble + Run Tracking + Memory Management."""

    def __init__(self, config: Config, ocr_engine: OCREngine, db: HandwritingDB):
        self.config = config
        self.ocr = ocr_engine
        self.db = db
        self._use_fitz = True  # نحاول PyMuPDF أولاً

    def _load_page(self, page_num: int) -> np.ndarray:
        """تحميل صفحة واحدة — يستخدم PyMuPDF أولاً ثم pdf2image كبديل."""
        mem_before = _get_memory_mb()
        logger.info(f"  [ذاكرة] قبل تحميل الصفحة: {mem_before} MB")

        if self._use_fitz:
            img = _load_page_fitz(self.config.pdf_path, page_num, self.config.dpi)
            if img is not None:
                mem_after = _get_memory_mb()
                logger.info(f"  [ذاكرة] بعد تحميل الصفحة (PyMuPDF): {mem_after} MB (Δ{mem_after - mem_before:+d})")
                return img
            # PyMuPDF فشل — ننتقل لـ pdf2image
            self._use_fitz = False
            logger.warning("الانتقال لـ pdf2image (PyMuPDF غير متاح)")

        img = _load_page_pdf2image(self.config.pdf_path, page_num, self.config.dpi)
        if img is not None:
            mem_after = _get_memory_mb()
            logger.info(f"  [ذاكرة] بعد تحميل الصفحة (pdf2image): {mem_after} MB (Δ{mem_after - mem_before:+d})")
        return img

    def process(self, resume: bool = True) -> dict:
        """معالجة كاملة مع Batch TrOCR + run_id + auto-export + حماية المزامنة."""
        start_time = time.time()
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
        pages_start = self.config.pages_start
        pages_end = self.config.pages_end

        # حماية قاعدة البيانات عند تفعيل المزامنة
        sync_mgr = None
        lock = None
        if self.config.sync_enabled:
            sync_mgr = SyncManager(self.config)
            lock = FileLock(
                self.config.lock_file_path,
                timeout=self.config.sync_lock_timeout,
            )

            # كشف التعارضات قبل البدء
            conflicts = sync_mgr.detect_conflicts()
            if conflicts:
                for conflict in conflicts:
                    logger.warning(f"تعارض مزامنة: {conflict['message']}")

            try:
                lock.acquire()
            except TimeoutError as e:
                logger.error(str(e))
                return self._empty_stats(run_id, error="lock_timeout")

        try:
            stats = self._process_core(
                run_id, pages_start, pages_end, resume, start_time, sync_mgr
            )
            return stats
        finally:
            # تحرير القفل دائماً
            if lock:
                lock.release()

    def _process_core(self, run_id, pages_start, pages_end, resume, start_time, sync_mgr) -> dict:
        """المنطق الأساسي للمعالجة (يُستدعى داخل القفل)"""

        # بناء قاموس التصحيح
        correction_dict = build_correction_dict(
            self.config.feedback_csv,
            self.config.correction_dict_path,
            self.config.correction_min_votes,
        )
        if correction_dict:
            logger.info(f"قاموس التصحيح: {len(correction_dict)} كلمة")

        # استئناف من checkpoint
        checkpoint = self._load_checkpoint() if resume else None
        if checkpoint and checkpoint.get("input_path") == self.config.pdf_path:
            pages_start = int(
                checkpoint.get("next_page", self.config.pages_start)
            )
            logger.info(f"استئناف من الصفحة {pages_start}")

        # تسجيل بداية التشغيل
        self.db.insert_run(run_id, self.config.pdf_path)

        # === v5.4: تحسين الذاكرة الشامل ===
        page_nums = list(range(pages_start, pages_end + 1))
        total_pages = len(page_nums)
        logger.info(f"بدء معالجة {total_pages} صفحة (PyMuPDF + تحميل صفحة بصفحة)")

        # حذف بيانات الصفحات المعاد معالجتها (منع التكرار)
        if page_nums:
            deleted = self.db.delete_pages(min(page_nums), max(page_nums))
            if deleted:
                logger.info(f"تم حذف {deleted} سجل قديم")

        total_words = 0
        conf_acc = []

        for idx, actual_pg in enumerate(page_nums):
            logger.info(f"معالجة صفحة {idx + 1}/{total_pages} (صفحة {actual_pg})")

            # تنظيف الذاكرة قبل كل صفحة
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            mem_start = _get_memory_mb()

            # === تحميل صفحة واحدة فقط (PyMuPDF أو pdf2image) ===
            img_bgr = self._load_page(actual_pg)
            if img_bgr is None:
                logger.error(f"الملف غير موجود أو فشل التحويل: {self.config.pdf_path}")
                return self._empty_stats(run_id)

            logger.info(f"  [ذاكرة] بعد التحميل: {_get_memory_mb()} MB | حجم الصورة: {img_bgr.shape}")

            # كشف الكلمات باستخدام EasyOCR
            try:
                logger.info(f"  [ذاكرة] قبل EasyOCR detect: {_get_memory_mb()} MB")
                detections = self.ocr.detect_words_full(img_bgr)
                logger.info(f"  [ذاكرة] بعد EasyOCR detect: {_get_memory_mb()} MB | كشف: {len(detections)} كلمة")
            except Exception as e:
                detections = []
                logger.warning(f"EasyOCR p{actual_pg}: {e}")

            # معالجة مسبقة + تجزئة ذكية
            logger.info(f"  [ذاكرة] قبل preprocess: {_get_memory_mb()} MB")
            binary, _ = preprocess_image(img_bgr, self.config)
            logger.info(f"  [ذاكرة] بعد preprocess: {_get_memory_mb()} MB")

            boxes = smart_segmentation(img_bgr, binary, detections)
            boxes_info = match_boxes_with_detections(boxes, detections)
            del binary, boxes  # تحرير فوري

            logger.info(f"  [ذاكرة] بعد segmentation: {_get_memory_mb()} MB | مربعات: {len(boxes_info)}")

            # ---- BATCH TROCR + تجنب القص المزدوج ----
            need_trocr_idx = []
            word_crops = []
            easy_results = []

            for i, ((x, y, w, h), easy_item) in enumerate(boxes_info):
                crop = crop_safe(img_bgr, x, y, w, h)
                word_crops.append(crop)

                if crop.size == 0:
                    easy_results.append(None)
                    continue

                if easy_item is not None:
                    _, txt, conf = easy_item
                    txt_str = txt.strip() if txt else ""
                    easy_results.append(("easyocr", txt_str, float(conf)))

                    if float(conf) < self.config.easy_conf_threshold:
                        need_trocr_idx.append(i)
                else:
                    easy_results.append(None)
                    need_trocr_idx.append(i)

            # Batch inference
            trocr_texts = {}
            if need_trocr_idx:
                batch_indices = []
                for b_start in range(0, len(need_trocr_idx), self.ocr.trocr_batch_size):
                    batch_indices = need_trocr_idx[b_start:b_start + self.ocr.trocr_batch_size]
                    batch = [word_crops[i] for i in batch_indices]
                    texts = self.ocr.batch_predict(batch)
                    del batch
                    for k, txt in enumerate(texts):
                        trocr_texts[batch_indices[k]] = txt

            # الدمج والإدراج في DB
            for i, ((x, y, w, h), easy_item) in enumerate(boxes_info):
                crop = word_crops[i]
                if crop.size == 0:
                    continue

                easy_res = easy_results[i]

                # اختيار أفضل نتيجة
                if easy_res and easy_res[2] >= self.config.easy_conf_threshold:
                    raw, conf, src = easy_res[1], easy_res[2], easy_res[0]
                elif i in trocr_texts and trocr_texts[i]:
                    raw = trocr_texts[i]
                    conf = self.config.trocr_default_confidence
                    src = "trocr"
                    if easy_res and easy_res[2] > conf:
                        raw, conf, src = easy_res[1], easy_res[2], easy_res[0]
                elif easy_res:
                    raw, conf, src = easy_res[1], easy_res[2], easy_res[0]
                else:
                    raw, conf, src = "", 0.0, "none"

                # التصحيح الإملائي + قاموس التصحيح
                corrected = apply_correction_dict(
                    spell_correct_word(raw), correction_dict
                )

                _, buf = cv2.imencode(".png", crop)
                self.db.insert_word(
                    image_data=buf.tobytes(),
                    predicted_text=corrected,
                    raw_text=raw,
                    status="unverified",
                    confidence=conf,
                    model_source=src,
                    x=x, y=y, w=w, h=h,
                    page_num=actual_pg,
                    run_id=run_id,
                )
                total_words += 1
                conf_acc.append(conf)

            # حفظ checkpoint
            self._save_checkpoint({
                "run_id": run_id,
                "input_path": self.config.pdf_path,
                "next_page": actual_pg + 1,
                "words": total_words,
                "ts": datetime.now().isoformat(),
            })

            # === تنظيف الذاكرة بعد كل صفحة ===
            del img_bgr, detections, boxes_info
            del word_crops, easy_results, trocr_texts
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            mem_end = _get_memory_mb()
            logger.info(f"  [ذاكرة] بعد تنظيف صفحة {actual_pg}: {mem_end} MB (إجمالي: Δ{mem_end - mem_start:+d} MB)")

        # مسح checkpoint عند الاكتمال
        self._clear_checkpoint()

        duration = time.time() - start_time
        avg_conf = float(np.mean(conf_acc)) if conf_acc else 0.0

        # إنهاء تسجيل التشغيل
        self.db.finish_run(run_id, total_pages, total_words, avg_conf)

        stats = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "input": self.config.pdf_path,
            "pages": total_pages,
            "words": total_words,
            "avg_confidence": round(avg_conf, 4),
            "duration_sec": round(duration, 2),
        }

        # حفظ الإحصائيات
        os.makedirs(os.path.dirname(self.config.stats_json), exist_ok=True)
        with open(self.config.stats_json, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        # سجل التشغيلات
        self._save_run_history(stats)

        # تحديث حالة المزامنة
        if sync_mgr:
            sync_mgr.update_device_status(
                action="process",
                details={
                    "words": total_words,
                    "pages": total_pages,
                    "avg_conf": round(avg_conf, 4),
                }
            )

        # تنظيف نهائي
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info(
            f"اكتملت المعالجة: {total_words} كلمة في {duration:.1f}s"
        )
        return stats

    def _save_checkpoint(self, data: dict) -> None:
        """حفظ checkpoint لاستئناف المعالجة"""
        ckpt_path = self.config.checkpoint_file
        os.makedirs(os.path.dirname(ckpt_path), exist_ok=True)
        try:
            with open(ckpt_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"فشل حفظ checkpoint: {e}")

    def _load_checkpoint(self) -> dict | None:
        """تحميل checkpoint"""
        ckpt_path = self.config.checkpoint_file
        if os.path.exists(ckpt_path):
            try:
                with open(ckpt_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _clear_checkpoint(self) -> None:
        """مسح checkpoint عند الاكتمال"""
        ckpt_path = self.config.checkpoint_file
        if os.path.exists(ckpt_path):
            try:
                os.remove(ckpt_path)
            except Exception:
                pass

    def _save_run_history(self, stats: dict) -> None:
        """حفظ سجل التشغيل في CSV"""
        os.makedirs(os.path.dirname(self.config.runs_csv), exist_ok=True)
        runs = pd.read_csv(self.config.runs_csv, encoding="utf-8-sig")
        runs = pd.concat([
            runs,
            pd.DataFrame([{
                "run_id": stats["run_id"],
                "timestamp": stats["timestamp"],
                "pages": stats["pages"],
                "words": stats["words"],
                "avg_conf": stats["avg_confidence"],
                "duration_sec": stats["duration_sec"],
                "status": "completed",
            }]),
        ], ignore_index=True)
        runs.to_csv(self.config.runs_csv, index=False, encoding="utf-8-sig")

    def _empty_stats(self, run_id: str = "", error: str = "") -> dict:
        return {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "input": self.config.pdf_path,
            "pages": 0,
            "words": 0,
            "avg_confidence": 0.0,
            "duration_sec": 0.0,
            "error": error or True,
        }
