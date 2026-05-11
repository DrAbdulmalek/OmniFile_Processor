#!/usr/bin/env python3
# prepare_fixed_eval_set.py
"""
أداة إعداد مجموعة التقييم الثابتة (Fixed Evaluation Set)
تختار عينات عشوائية من بيانات التصحيحات لتُستخدم كمعيار ثابت
لتقييم أداء النموذج بعد كل تدريب والكشف عن الانحدار.

الاستخدام:
    python prepare_fixed_eval_set.py                    # إنشاء مجموعة من 50 عينة
    python prepare_fixed_eval_set.py --num 100          # إنشاء مجموعة من 100 عينة
    python prepare_fixed_eval_set.py --seed 42          # بذرة عشوائية محددة
    python prepare_fixed_eval_set.py --append            # إضافة عينات للمجموعة الموجودة
"""

import argparse
import random
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "htr_corrections.csv"
FIXED_SET_PATH = PROJECT_ROOT / "training" / "data" / "fixed_eval_set.csv"

DEFAULT_NUM_SAMPLES = 50
DEFAULT_SEED = 42


def load_valid_corrections(csv_path: Path) -> pd.DataFrame:
    """تحميل التصحيحات الصالحة فقط (غير فارغة)"""
    if not csv_path.exists():
        raise FileNotFoundError(f"ملف التصحيحات غير موجود: {csv_path}")

    df = pd.read_csv(csv_path)

    required_cols = {'image_path', 'corrected_text'}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"أعمدة مفقودة في ملف التصحيحات: {missing}")

    # تصفية الصفوف الفارغة
    df = df[df['corrected_text'].notna()]
    df = df[df['corrected_text'].astype(str).str.strip() != ""]

    if 'image_path' in df.columns:
        df = df[df['image_path'].notna()]
        df = df[df['image_path'].astype(str).str.strip() != ""]

    return df


def prepare_fixed_set(
    csv_path: Path,
    output_path: Path,
    num_samples: int = DEFAULT_NUM_SAMPLES,
    seed: int = DEFAULT_SEED,
    append: bool = False
):
    """
    إعداد مجموعة التقييم الثابتة.

    Args:
        csv_path: مسار ملف التصحيحات
        output_path: مسار ملف الإخراج
        num_samples: عدد العينات المطلوبة
        seed: البذرة العشوائية
        append: إضافة للمجموعة الموجودة بدلاً من استبدالها
    """
    print(f"📂 تحميل التصحيحات من: {csv_path}")
    df = load_valid_corrections(csv_path)
    print(f"   إجمالي العينات الصالحة: {len(df)}")

    if len(df) == 0:
        print("❌ لا توجد عينات صالحة لإنشاء مجموعة التقييم.")
        return

    # إضافة للمجموعة الموجودة
    existing_count = 0
    if append and output_path.exists():
        existing_df = pd.read_csv(output_path)
        existing_count = len(existing_df)
        print(f"📊 المجموعة الموجودة: {existing_count} عينة")

        # استبعاد العينات الموجودة مسبقاً
        if 'image_path' in existing_df.columns and 'image_path' in df.columns:
            existing_paths = set(existing_df['image_path'].astype(str))
            df = df[~df['image_path'].astype(str).isin(existing_paths)]
            print(f"   عينات جديدة متاحة بعد الاستبعاد: {len(df)}")

    # تحديد عدد العينات
    actual_num = min(num_samples, len(df))
    if actual_num < num_samples:
        print(f"⚠️ عدد العينات المتاحة ({len(df)}) أقل من المطلوب ({num_samples})")

    # اختيار عشوائي
    fixed = df.sample(n=actual_num, random_state=seed)
    print(f"✅ تم اختيار {len(fixed)} عينة (بذرة: {seed})")

    # حفظ
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if append and output_path.exists():
        existing_df = pd.read_csv(output_path)
        combined = pd.concat([existing_df, fixed], ignore_index=True)
        combined.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"📊 المجموعة النهائية: {len(combined)} عينة")
    else:
        fixed.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"📊 المجموعة المحفوظة: {len(fixed)} عينة")

    print(f"💾 تم الحفظ في: {output_path}")

    # إحصائيات
    print("\n📈 إحصائيات المجموعة:")
    if 'language' in fixed.columns:
        lang_counts = fixed['language'].value_counts()
        for lang, count in lang_counts.items():
            print(f"   {lang}: {count} عينة ({100*count/len(fixed):.1f}%)")

    if 'writer_id' in fixed.columns:
        writer_counts = fixed['writer_id'].value_counts()
        print(f"\n📝 الكُتّاب: {len(writer_counts)} كاتب مختلف")

    text_lengths = fixed['corrected_text'].astype(str).str.len()
    print(f"📏 متوسط طول النص: {text_lengths.mean():.1f} حرف")
    print(f"📏 أقصر نص: {text_lengths.min()} حرف")
    print(f"📏 أطول نص: {text_lengths.max()} حرف")


def main():
    parser = argparse.ArgumentParser(
        description="إعداد مجموعة التقييم الثابتة لـ HTR"
    )
    parser.add_argument("--csv", type=str, default=str(CSV_PATH),
                       help=f"مسار ملف التصحيحات (الافتراضي: {CSV_PATH})")
    parser.add_argument("--output", type=str, default=str(FIXED_SET_PATH),
                       help=f"مسار ملف الإخراج (الافتراضي: {FIXED_SET_PATH})")
    parser.add_argument("--num", type=int, default=DEFAULT_NUM_SAMPLES,
                       help=f"عدد العينات (الافتراضي: {DEFAULT_NUM_SAMPLES})")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                       help=f"البذرة العشوائية (الافتراضي: {DEFAULT_SEED})")
    parser.add_argument("--append", action="store_true",
                       help="إضافة للمجموعة الموجودة بدلاً من استبدالها")
    args = parser.parse_args()

    print("=" * 50)
    print("أداة إعداد مجموعة التقييم الثابتة - OmniFile HTR")
    print("=" * 50)
    print()

    try:
        prepare_fixed_set(
            csv_path=Path(args.csv),
            output_path=Path(args.output),
            num_samples=args.num,
            seed=args.seed,
            append=args.append
        )
    except FileNotFoundError as e:
        print(f"❌ خطأ: {e}")
        print("   تأكد من وجود ملف التصحيحات في المسار المحدد.")
    except ValueError as e:
        print(f"❌ خطأ: {e}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")


if __name__ == "__main__":
    main()
