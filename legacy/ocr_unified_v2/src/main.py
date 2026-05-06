"""
HandwrittenOCR - الوحدة الرئيسية v5.0
========================================
نقطة الدخول الرئيسية - تجمع بين جميع المكونات.
يدعم: التشغيل المحلي (Offline)، المزامنة بين الأجهزة، واجهة الشبكة المحلية.
"""

import time
import logging
import os
from config import Config
from src.logger import setup_logging
from src.recognition import OCREngine
from src.correction import init_correctors
from src.database import HandwritingDB
from src.pdf_processor import PDFProcessor
from src.review_ui import ReviewUI
from src.metrics import compute_metrics


def _check_available_memory() -> tuple[int, int]:
    """كشف الذاكرة المتاحة (RAM + Swap) بالميجابايت."""
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    value = int(parts[1])  # كيلوبايت
                    meminfo[key] = value

        mem_total = meminfo.get("MemTotal", 0) // 1024  # MB
        mem_available = meminfo.get("MemAvailable", 0) // 1024  # MB
        swap_total = meminfo.get("SwapTotal", 0) // 1024  # MB
        return mem_available, swap_total
    except Exception:
        return 0, 0


def _auto_detect_low_memory(config: Config) -> bool:
    """كشف تلقائي: هل يجب تفعيل الوضع الخفيف؟

    يُفعّل تلقائياً إذا كانت الذاكرة المتاحة < 3 GB.
    يمكن تجاوزه يدوياً بـ config.low_memory.
    """
    mem_available_mb, swap_mb = _check_available_memory()
    total_available = mem_available_mb + swap_mb

    logger = logging.getLogger("HandwrittenOCR")
    logger.info(f"الذاكرة المتاحة: {mem_available_mb} MB RAM + {swap_mb} MB Swap")

    # إذا الذاكرة < 3 GB: فعّل الوضع الخفيف تلقائياً
    if total_available < 3072 and not config.low_memory:
        logger.warning(
            f"الذاكرة المتاحة ({total_available} MB) أقل من 3 GB — "
            f"يُفعَّل الوضع الخفيف تلقائياً. استخدم --low-memory لتخطي هذا التحذير."
        )
        config.low_memory = True

    return config.low_memory


def main(config: Config | None = None):
    if config is None:
        config = Config()

    # إعداد شامل
    config.setup()
    config.apply_hf_token()
    config.apply_cache_env()
    if not config.is_colab:
        # لا حاجة لربط EasyOCR بالـ Drive محلياً
        pass
    else:
        config.setup_easyocr_symlink()

    logger = setup_logging(config)
    logger.info(f"بدء تشغيل HandwrittenOCR v5.3")
    logger.info(f"ملف PDF: {config.pdf_path}")
    logger.info(f"مجلد الإخراج: {config.output_dir or config.project_root}")
    if config.model_cache_dir or config.cache_dir:
        logger.info(f"تخزين مؤقت: {config.model_cache_dir or config.cache_dir}")

    # === كشف الذاكرة وتفعيل الوضع الخفيف تلقائياً ===
    low_mem = _auto_detect_low_memory(config)
    if low_mem or config.low_memory:
        config.apply_low_memory()
        print("\n  ⚠️  الوضع الخفيف مفعّل (توفير الذاكرة)")
        print(f"      DPI={config.dpi}, EasyOCR={config.ocr_languages}, batch={config.trocr_batch_size}")
        print("      استخدم: python run.py --local --pdf FILE  (بدون --low-memory) للوضع الكامل\n")

    # عرض معلومات المزامنة
    if config.sync_enabled:
        from src.sync import SyncManager
        sync_mgr = SyncManager(config)
        network = sync_mgr.get_network_info()

        print("\n" + "=" * 50)
        print("  نظام المزامنة: مفعّل")
        print("=" * 50)
        print(f"  معرف الجهاز:  {sync_mgr.device_id}")
        print(f"  شبكة محلية:   {network.get('local_ip', 'N/A')}")
        print(f"  واجهة المراجعة: {network.get('server_url', 'N/A')}")
        print(f"  API:           {network.get('api_url', 'N/A')}")
        print("=" * 50)

        # كشف التعارضات
        conflicts = sync_mgr.detect_conflicts()
        if conflicts:
            for c in conflicts:
                print(f"  تحذير: {c['message']}")

    # تحميل المدققات الإملائية (اختياري — يمكن تخطيه في الوضع الخفيف)
    if not config.skip_spellcheck:
        init_correctors()
    else:
        logger.info("تخطي المدققات الإملائية (توفير الذاكرة)")

    # تحميل محرك التعرف (مع LoRA تلقائي)
    start = time.time()
    ocr_engine = OCREngine(
        trocr_model_name=config.trocr_model_name,
        ocr_languages=config.ocr_languages,
        max_text_length=config.max_text_length,
        cache_dir=config.model_cache_dir or config.cache_dir,
        hf_token=config.hf_token,
        trocr_default_confidence=config.trocr_default_confidence,
        easy_conf_threshold=config.easy_conf_threshold,
        num_beams=config.num_beams,
        trocr_batch_size=config.trocr_batch_size,
        lora_save_path=config.lora_save_path,
        skip_trocr=config.skip_trocr,
    )
    logger.info(f"تم تحميل النماذج في {time.time() - start:.2f} ثانية")
    if ocr_engine.lora_loaded:
        print("تم تحميل النموذج المُحسَّن (LoRA)")
    else:
        print("يستخدم النموذج الأساسي")

    # تهيئة قاعدة البيانات
    db = HandwritingDB(config.db_path)

    # معالجة PDF
    processor = PDFProcessor(config, ocr_engine, db)
    stats = processor.process()

    if stats.get("error"):
        logger.error("فشلت المعالجة!")
        if isinstance(stats.get("error"), str):
            logger.error(f"السبب: {stats['error']}")
            if stats.get("error") == "lock_timeout":
                print("\nتعذر الحصول على قفل المعالجة - جهاز آخر يعمل حالياً.")
                print("انتظر حتى يكتمل الجهاز الآخر أو أوقف المعالجة عليه.")
        return

    # عرض الإحصائيات
    print("\n" + "=" * 50)
    print("  إحصائيات المعالجة v5.3")
    print("=" * 50)
    print(f"  Run ID:        {stats.get('run_id', 'N/A')}")
    print(f"  الصفحات:       {stats.get('pages', 0)}")
    print(f"  الكلمات:       {stats.get('words', 0)}")
    print(f"  متوسط الثقة:   {stats.get('avg_confidence', 0):.2%}")
    print(f"  الوقت:         {stats.get('duration_sec', 0):.1f} ثانية")
    print("=" * 50)

    # حساب المقاييس (WER/CER)
    if config.metrics_log:
        try:
            m = compute_metrics(db, metrics_log=config.metrics_log)
            if m.get("wer") is not None:
                print(f"\n  WER: {m['wer']:.2%} | CER: {m['cer']:.2%} ({m['samples']} عينة)")
        except Exception as e:
            logger.debug(f"Metrics: {e}")

    # ملفات المراقبة
    print(f"\nملفات المراقبة:")
    print(f"  سجل الأحداث:   {config.log_file}")
    print(f"  إحصائيات:      {config.stats_json}")
    print(f"  تصحيحات:       {config.feedback_csv}")
    print(f"  قاموس التصحيح: {config.correction_dict_path}")

    if config.sync_enabled:
        print(f"  حالة المزامنة: {config.sync_status_path}")

    # تشغيل واجهة المراجعة
    print("\nتشغيل واجهة المراجعة...")
    review_ui = ReviewUI(db, config.feedback_csv)
    review_ui.launch()


if __name__ == "__main__":
    main()
