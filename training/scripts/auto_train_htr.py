#!/usr/bin/env python3
# auto_train_htr.py
"""
سكريبت التدريب التلقائي لـ HTR
يُشغل دورياً (مثلاً كل ليلة) لتدريب النموذج على التصحيحات الجديدة
يدعم:
- النسخ الاحتياطي التلقائي للنموذج قبل التدريب
- التقييم قبل وبعد التدريب للكشف عن الانحدار
- الاستعادة التلقائية إذا انخفض الأداء
- الجدولة عبر cron (Linux/macOS) أو Task Scheduler (Windows)
"""

import os
import sys
import json
import logging
import subprocess
import argparse
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

# ========== الإعدادات ==========
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "htr_corrections.csv"
LAST_TRAIN_RECORD = PROJECT_ROOT / "training" / "last_train_state.json"
TRAIN_SCRIPT = SCRIPT_DIR / "train_trocr_lora.py"
MODEL_PATH = PROJECT_ROOT / "training" / "models" / "htr_model"
BACKUP_DIR = PROJECT_ROOT / "training" / "model_backups"
FIXED_EVAL_SET = PROJECT_ROOT / "training" / "data" / "fixed_eval_set.csv"
EVAL_RESULTS_FILE = PROJECT_ROOT / "training" / "reports" / "last_eval_results.json"
LOG_FILE = PROJECT_ROOT / "training" / "logs" / "auto_train.log"

MIN_NEW_SAMPLES = 10     # الحد الأدنى من العينات الجديدة لتشغيل التدريب
FORCE_TRAIN_DAYS = 7     # القوة كل 7 أيام حتى لو لم يصل للحد الأدنى
MAX_REGRESSION = 0.10    # أقصى زيادة مسموحة في CER (10%)
MAX_BACKUPS = 5          # الحد الأقصى للنسخ الاحتياطية المحفوظة


def setup_logging():
    """تهيئة نظام تسجيل الأحداث"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def get_last_train_info():
    """قراءة معلومات آخر تدريب من ملف JSON"""
    if not LAST_TRAIN_RECORD.exists():
        return {
            "last_train_date": None,
            "last_sample_count": 0,
            "last_train_cmd": None,
            "last_eval_results": None
        }
    try:
        with open(LAST_TRAIN_RECORD, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        logger.warning("ملف حالة آخر تدريب تالف، سيتم إنشاء واحد جديد")
        return {
            "last_train_date": None,
            "last_sample_count": 0,
            "last_train_cmd": None,
            "last_eval_results": None
        }


def save_last_train_info(sample_count, eval_results=None, cmd="train_trocr_lora.py"):
    """حفظ معلومات آخر تدريب"""
    LAST_TRAIN_RECORD.parent.mkdir(parents=True, exist_ok=True)
    info = {
        "last_train_date": datetime.now().isoformat(),
        "last_sample_count": sample_count,
        "last_train_cmd": cmd,
        "last_eval_results": eval_results
    }
    with open(LAST_TRAIN_RECORD, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    logger.info(f"تم حفظ حالة آخر تدريب: {info['last_train_date']}")


def get_current_sample_count():
    """عدد العينات المصححة حالياً (صفوف غير فارغة)"""
    if not CSV_PATH.exists():
        return 0
    try:
        df = pd.read_csv(CSV_PATH)
        if 'corrected_text' not in df.columns:
            return 0
        df = df[df['corrected_text'].notna()]
        df = df[df['corrected_text'].astype(str).str.strip() != ""]
        return len(df)
    except Exception as e:
        logger.error(f"خطأ في قراءة ملف التصحيحات: {e}")
        return 0


def should_train(last_info, current_count, min_new=MIN_NEW_SAMPLES, force_days=FORCE_TRAIN_DAYS):
    """
    تقرر ما إذا كان يجب تشغيل التدريب بناءً على:
    - عدد العينات الجديدة
    - مرور فترة طويلة بدون تدريب
    """
    last_count = last_info.get("last_sample_count", 0)
    new_samples = current_count - last_count

    if new_samples >= min_new:
        logger.info(f"يوجد {new_samples} عينة جديدة (الحد الأدنى {min_new}) -> سيتم التدريب")
        return True

    last_date_str = last_info.get("last_train_date")
    if last_date_str:
        try:
            last_date = datetime.fromisoformat(last_date_str)
            days_since_last = (datetime.now() - last_date).days
            if days_since_last >= force_days and current_count > 0:
                logger.info(
                    f"آخر تدريب كان منذ {days_since_last} يوم "
                    f"(أكثر من {force_days}) -> سيتم التدريب القسري"
                )
                return True
        except (ValueError, TypeError):
            pass
    else:
        if current_count >= min_new:
            logger.info("لم يتم تدريب النموذج مسبقاً ويوجد عدد كافٍ من العينات -> سيتم التدريب")
            return True

    logger.info(f"لا حاجة للتدريب: العينات الجديدة = {new_samples} (الحد {min_new})")
    return False


def backup_current_model():
    """عمل نسخة احتياطية من النموذج الحالي (إن وجد) قبل التدريب"""
    if not MODEL_PATH.exists():
        logger.info("لا يوجد نموذج سابق لعمل نسخة احتياطية.")
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"htr_model_backup_{timestamp}"

    try:
        shutil.copytree(MODEL_PATH, backup_path)
        logger.info(f"تم إنشاء نسخة احتياطية للنموذج في {backup_path}")

        # تنظيف النسخ القديمة (الاحتفاظ بأحدث MAX_BACKUPS نسخ)
        cleanup_old_backups()

        return str(backup_path)
    except Exception as e:
        logger.error(f"فشل إنشاء النسخة الاحتياطية: {e}")
        return None


def cleanup_old_backups():
    """حذف أقدم النسخ الاحتياطية عند تجاوز الحد الأقصى"""
    if not BACKUP_DIR.exists():
        return
    backups = sorted(BACKUP_DIR.glob("htr_model_backup_*"), reverse=True)
    for old_backup in backups[MAX_BACKUPS:]:
        try:
            shutil.rmtree(old_backup)
            logger.info(f"تم حذف نسخة احتياطية قديمة: {old_backup.name}")
        except Exception as e:
            logger.warning(f"فشل حذف {old_backup.name}: {e}")


def evaluate_model(model_path=None, label=""):
    """
    تقييم النموذج على المجموعة الثابتة
    يعيد قاموساً يحتوي على cer, wer, num_samples أو None إذا تعذر التقييم
    """
    eval_path = model_path if model_path else str(MODEL_PATH)

    if not FIXED_EVAL_SET.exists():
        logger.warning(f"ملف التقييم الثابت {FIXED_EVAL_SET} غير موجود. لن يتم التقييم.")
        return None

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "evaluate_checkpoint.py"),
             "--model-path", eval_path,
             "--eval-data", str(FIXED_EVAL_SET)],
            capture_output=True,
            text=True,
            check=False,
            timeout=300
        )
        if result.returncode == 0:
            # محاولة قراءة النتائج من ملف JSON
            if EVAL_RESULTS_FILE.exists():
                with open(EVAL_RESULTS_FILE, 'r') as f:
                    metrics = json.load(f)
                logger.info(f"📊 نتائج تقييم {label}: CER = {metrics.get('cer', 'N/A'):.4f}, "
                           f"WER = {metrics.get('wer', 'N/A'):.4f}")
                return metrics
        logger.warning(f"فشل تقييم النموذج {label} (كود {result.returncode})")
        if result.stderr:
            logger.debug(f"خطأ التقييم: {result.stderr[-500:]}")
        return None
    except subprocess.TimeoutExpired:
        logger.error("انتهت مهلة التقييم (300 ثانية)")
        return None
    except Exception as e:
        logger.exception(f"خطأ أثناء تقييم النموذج {label}: {e}")
        return None


def compare_performance(before_metrics, after_metrics):
    """
    مقارنة أداء النموذج قبل وبعد التدريب.
    ترجع True إذا كان الأداء الجديد مقبولاً (لم يزد CER بأكثر من MAX_REGRESSION)
    """
    if before_metrics is None or after_metrics is None:
        logger.info("لا توجد مقاييس كافية للمقارنة، تخطي التحقق من الانحدار.")
        return True

    before_cer = before_metrics.get("cer", 1.0)
    after_cer = after_metrics.get("cer", 1.0)

    if before_cer == 0:
        logger.warning("CER قبل التدريب = 0، لا يمكن حساب التغير النسبي")
        return after_cer <= 0.05  # قبول أي قيمة صغيرة

    relative_change = (after_cer - before_cer) / before_cer

    logger.info(f"معدل خطأ الحروف (CER) قبل التدريب: {before_cer:.4f}")
    logger.info(f"بعد التدريب: {after_cer:.4f} (تغير نسبي: {relative_change:.2%})")

    if relative_change > MAX_REGRESSION:
        logger.error(
            f"⚠️ انحدار الأداء! CER ارتفع بنسبة {relative_change:.2%} "
            f"(أكثر من {MAX_REGRESSION:.0%}). سيتم استعادة النموذج السابق."
        )
        return False
    else:
        logger.info("✅ الأداء مقبول أو محسّن.")
        return True


def restore_backup(backup_path):
    """استعادة النموذج من النسخة الاحتياطية"""
    if not backup_path or not os.path.exists(backup_path):
        logger.error("مسار النسخة الاحتياطية غير صالح")
        return False
    try:
        if MODEL_PATH.exists():
            shutil.rmtree(MODEL_PATH)
        shutil.copytree(backup_path, MODEL_PATH)
        logger.info(f"تم استعادة النموذج من النسخة الاحتياطية {backup_path}")
        return True
    except Exception as e:
        logger.exception(f"فشل استعادة النسخة الاحتياطية: {e}")
        return False


def run_training():
    """تشغيل سكريبت التدريب"""
    if not TRAIN_SCRIPT.exists():
        logger.error(f"سكريبت التدريب غير موجود: {TRAIN_SCRIPT}")
        return False

    logger.info("بدء تشغيل سكريبت التدريب...")
    try:
        result = subprocess.run(
            [sys.executable, str(TRAIN_SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
            timeout=3600  # حد أقصى ساعة واحدة
        )
        if result.returncode == 0:
            logger.info("✅ انتهى التدريب بنجاح")
            if result.stdout:
                logger.debug(f"المخرجات: {result.stdout[-500:]}")
            return True
        else:
            logger.error(f"❌ فشل التدريب (كود {result.returncode})")
            if result.stderr:
                logger.error(f"خطأ: {result.stderr[-500:]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("انتهت مهلة التدريب (3600 ثانية)")
        return False
    except Exception as e:
        logger.exception(f"استثناء أثناء تشغيل التدريب: {e}")
        return False


def run_training_with_safety():
    """تشغيل التدريب مع النسخ الاحتياطي والتحقق من الانحدار"""
    # 1. عمل نسخة احتياطية من النموذج الحالي
    backup_path = backup_current_model()

    # 2. تقييم النموذج الحالي (قبل التدريب) إن وجد
    before_metrics = None
    if MODEL_PATH.exists() and FIXED_EVAL_SET.exists():
        before_metrics = evaluate_model(label="قبل التدريب")

    # 3. تشغيل التدريب
    success = run_training()

    if not success:
        if backup_path:
            logger.warning("فشل التدريب، جارٍ استعادة النموذج السابق...")
            restore_backup(backup_path)
        return False

    # 4. تقييم النموذج الجديد بعد التدريب
    after_metrics = None
    if FIXED_EVAL_SET.exists():
        after_metrics = evaluate_model(label="بعد التدريب")

    # 5. مقارنة الأداء والتحقق من الانحدار
    if not compare_performance(before_metrics, after_metrics):
        if backup_path:
            logger.warning("جارٍ استعادة النموذج السابق بسبب الانحدار...")
            restore_backup(backup_path)
            logger.warning("تم استعادة النموذج السابق. النموذج الجديد لم يُحفظ.")
        else:
            logger.warning("لا توجد نسخة احتياطية للاستعادة، لكن الأداء انحدر.")
        return False

    logger.info("✅ التدريب ناجح والأداء مقبول، تم الاحتفاظ بالنموذج الجديد.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="HTR Auto Training Scheduler - سكريبت التدريب التلقائي"
    )
    parser.add_argument("--force", action="store_true",
                       help="تجاهل الشروط وتشغيل التدريب فوراً")
    parser.add_argument("--min-samples", type=int, default=MIN_NEW_SAMPLES,
                       help=f"الحد الأدنى للعينات الجديدة (الافتراضي: {MIN_NEW_SAMPLES})")
    parser.add_argument("--dry-run", action="store_true",
                       help="تحقق فقط دون تشغيل التدريب")
    parser.add_argument("--eval-only", action="store_true",
                       help="تقييم النموذج الحالي فقط دون تدريب")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("سكريبت التدريب التلقائي - OmniFile HTR")
    logger.info(f"التاريخ: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    if args.eval_only:
        metrics = evaluate_model(label="الحالي")
        if metrics:
            logger.info(f"📊 نتائج التقييم: CER = {metrics.get('cer', 'N/A')}, "
                       f"WER = {metrics.get('wer', 'N/A')}, "
                       f"العينات = {metrics.get('num_samples', 'N/A')}")
        else:
            logger.warning("لم يتم التقييم. تأكد من وجود ملف التقييم الثابت.")
        return

    if args.force:
        logger.info("⚠️ تشغيل التدريب بالقوة (--force)")
        success = run_training_with_safety()
        if success:
            current_count = get_current_sample_count()
            after_metrics = evaluate_model(label="نهائي") if FIXED_EVAL_SET.exists() else None
            save_last_train_info(current_count, after_metrics)
        else:
            logger.error("فشل التدريب.")
            sys.exit(1)
        return

    # التحقق من وجود بيانات
    current_count = get_current_sample_count()
    logger.info(f"العدد الحالي للعينات المصححة: {current_count}")

    if current_count == 0:
        logger.warning("لا توجد أي عينات مصححة. قم باستخدام أداة التصحيح أولاً.")
        sys.exit(0)

    last_info = get_last_train_info()

    if args.dry_run:
        logger.info("وضع التجربة الجافة (dry-run) - لن يتم تشغيل التدريب")
        decision = should_train(last_info, current_count, args.min_samples, FORCE_TRAIN_DAYS)
        logger.info(f"قرار بدء التدريب: {decision}")
        logger.info(f"معلومات آخر تدريب: {json.dumps(last_info, indent=2, ensure_ascii=False)}")
        return

    if should_train(last_info, current_count, args.min_samples, FORCE_TRAIN_DAYS):
        success = run_training_with_safety()
        if success:
            after_metrics = evaluate_model(label="نهائي") if FIXED_EVAL_SET.exists() else None
            save_last_train_info(current_count, after_metrics)
        else:
            logger.error("فشل التدريب، لن يتم تحديث حالة آخر تدريب حتى المحاولة التالية.")
            sys.exit(1)
    else:
        logger.info("لم يتم تشغيل التدريب.")


if __name__ == "__main__":
    main()
