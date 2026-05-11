#!/usr/bin/env python3
# scheduler_daemon.py
"""
مجدول التدريب الدائم - بديل خفيف لـ cron
يشغل التدريب التلقائي ضمن حلقة مستمرة دون الحاجة لـ cron.
مفيد لحاويات Docker أو السيرفرات المستمرة.

الاستخدام:
    python scheduler_daemon.py                          # تشغيل كل يوم الساعة 2 صباحاً
    python scheduler_daemon.py --time 03:30             # تشغيل كل يوم الساعة 3:30
    python scheduler_daemon.py --interval 360           # تشغيل كل 6 ساعات
    python scheduler_daemon.py --once                   # تشغيل مرة واحدة ثم الخروج
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    import schedule
except ImportError:
    print("❌ مكتبة schedule غير مثبتة. قم بتثبيتها:")
    print("   pip install schedule")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.resolve()
AUTO_TRAIN_SCRIPT = SCRIPT_DIR / "auto_train_htr.py"


def run_auto_training():
    """تشغيل سكريبت التدريب التلقائي"""
    print(f"\n{'='*60}")
    print(f"🔄 تشغيل التدريب التلقائي - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(
            [sys.executable, str(AUTO_TRAIN_SCRIPT)],
            capture_output=False,  # إظهار المخرجات مباشرة
            text=True,
            check=False
        )
        if result.returncode == 0:
            print(f"\n✅ اكتمل التدريب بنجاح - {datetime.now().strftime('%H:%M:%S')}\n")
        else:
            print(f"\n❌ فشل التدريب (كود {result.returncode}) - {datetime.now().strftime('%H:%M:%S')}\n")
    except Exception as e:
        print(f"\n❌ استثناء: {e}\n")


def run_dry_run():
    """تشغيل فحص تجريبي (بدون تدريب فعلي)"""
    print(f"\n🔍 فحص تجريبي - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        result = subprocess.run(
            [sys.executable, str(AUTO_TRAIN_SCRIPT), "--dry-run"],
            capture_output=False,
            text=True,
            check=False
        )
    except Exception as e:
        print(f"❌ خطأ: {e}")


def calculate_next_run(target_time: str) -> str:
    """حساب الوقت المتبقي للتشغيل التالي"""
    now = datetime.now()
    hour, minute = map(int, target_time.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    delta = target - now
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours} ساعة و {minutes} دقيقة"


def main():
    parser = argparse.ArgumentParser(
        description="مجدول التدريب الدائم - OmniFile HTR"
    )
    parser.add_argument("--time", type=str, default="02:00",
                       help="وقت التشغيل اليومي (صيغة HH:MM، الافتراضي: 02:00)")
    parser.add_argument("--interval", type=int, default=None,
                       help="فاصل التشغيل بالدقائق (يتجاوز --time)")
    parser.add_argument("--once", action="store_true",
                       help="تشغيل مرة واحدة ثم الخروج")
    parser.add_argument("--dry-run", action="store_true",
                       help="فحص تجريبي بدون تدريب فعلي")
    args = parser.parse_args()

    print("=" * 60)
    print("مجدول التدريب الدائم - OmniFile HTR")
    print("=" * 60)
    print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"⚙️  سكريبت التدريب: {AUTO_TRAIN_SCRIPT}")

    if not AUTO_TRAIN_SCRIPT.exists():
        print(f"❌ سكريبت التدريب غير موجود: {AUTO_TRAIN_SCRIPT}")
        sys.exit(1)

    if args.dry_run:
        run_dry_run()
        return

    if args.once:
        print("🔄 وضع التشغيل الفردي...")
        run_auto_training()
        return

    if args.interval:
        minutes = args.interval
        print(f"⏰ فاصل التشغيل: كل {minutes} دقيقة ({minutes/60:.1f} ساعة)")
        schedule.every(minutes).minutes.do(run_auto_training)
    else:
        print(f"⏰ وقت التدريب اليومي: {args.time}")
        schedule.every().day.at(args.time).do(run_auto_training)
        next_run = calculate_next_run(args.time)
        print(f"⏳ التشغيل التالي بعد: {next_run}")

    print("\nالمجدول قيد التشغيل... اضغط Ctrl+C للإيقاف\n")

    # تشغيل فحص تجريبي عند البدء
    run_dry_run()
    print()

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # فحص كل دقيقة
    except KeyboardInterrupt:
        print("\n\n⏹️ تم إيقاف المجدول.")


if __name__ == "__main__":
    main()
