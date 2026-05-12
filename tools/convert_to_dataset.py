#!/usr/bin/env python3
"""
Dataset Builder - From Corrected Text to Training Images
بناء مجموعة بيانات التدريب - من النص المصحح إلى صور التدريب

Reads output_flat_text.txt with --- filename.jpg --- delimiters,
crops lines from cleaned images, produces training_dataset_v2/images/ + labels.txt

يقرأ ملف output_flat_text.txt مع فواصل --- filename.jpg ---،
ويقص الأسطر من الصور المنظفة، وينتج training_dataset_v2/images/ + labels.txt
"""

import cv2
import numpy as np
import os
import re
import argparse
from pathlib import Path

# Default paths
DEFAULT_TEXT_FILE = Path('output_flat_text.txt')
DEFAULT_IMAGES_DIR = Path('input_pages')
DEFAULT_OUTPUT_DATASET = Path('training_dataset_v2')


def parse_args():
    """Parse command line arguments / تحليل معاملات سطر الأوامر"""
    parser = argparse.ArgumentParser(
        description='Dataset Builder - Convert corrected text to training images\n'
                    'بناء مجموعة بيانات التدريب - تحويل النص المصحح إلى صور تدريب',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples / أمثلة:
  python convert_to_dataset.py
  python convert_to_dataset.py --text-file data/output.txt --images-dir scans/ --output-dir dataset_v2/
  python convert_to_dataset.py -t output_flat_text.txt -i input_pages -o training_dataset_v2
        """
    )
    parser.add_argument(
        '-t', '--text-file',
        type=str, default=None,
        help='Path to output_flat_text.txt (default: output_flat_text.txt)\n'
             'مسار ملف output_flat_text.txt'
    )
    parser.add_argument(
        '-i', '--images-dir',
        type=str, default=None,
        help='Path to input images directory (default: input_pages)\n'
             'مسار مجلد الصور المدخلة'
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str, default=None,
        help='Path to output dataset directory (default: training_dataset_v2)\n'
             'مسار مجلد مجموعة البيانات الناتجة'
    )
    parser.add_argument(
        '--min-line-height',
        type=int, default=10,
        help='Minimum line height in pixels to keep (default: 10)\n'
             'الحد الأدنى لارتفاع السطر بالبكسل للاحتفاظ به'
    )
    parser.add_argument(
        '--padding',
        type=int, default=5,
        help='Vertical padding around each line crop in pixels (default: 5)\n'
             'حشوة عمودية حول كل قص سطر بالبكسل'
    )
    return parser.parse_args()


def clean_scribbles(img_gray):
    """
    Remove scribbles and noise using connected component analysis.
    Uses area and fill-ratio heuristics to filter out small dense marks.

    إزالة الخربشة والضوضاء باستخدام تحليل المكونات المتصلة.
    يستخدم مساحة ونسبة الحشو لتصفية العلامات الصغيرة الكثيفة.

    Args:
        img_gray: Grayscale image (numpy array)
                  صورة ذات تدرج رمادي

    Returns:
        Cleaned grayscale image
        صورة رمادية منظفة
    """
    if img_gray is None:
        raise ValueError("Input image is None / الصورة المدخلة فارغة")

    _, binary = cv2.threshold(img_gray, 50, 255, cv2.THRESH_BINARY_INV)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    mask = np.ones_like(img_gray) * 255
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        fill_ratio = area / max(1, w * h)
        # Remove small dense scribbles: area between 100-5000px and high fill ratio
        if 100 < area < 5000 and fill_ratio > 0.6:
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

    return cv2.bitwise_and(img_gray, img_gray, mask=mask)


def get_line_crops(img_gray, min_height=10, padding=5):
    """
    Crop individual text lines from a grayscale image using horizontal projection.

    قص أسطر النص الفردية من صورة رمادية باستخدام الإسقاط الأفقي.

    Args:
        img_gray: Grayscale input image / صورة مدخلة ذات تدرج رمادي
        min_height: Minimum line height in pixels to keep (default: 10)
                    الحد الأدنى لارتفاع السطر بالبكسل
        padding: Vertical padding around each crop (default: 5)
                 حشوة عمودية حول كل قص

    Returns:
        List of cropped line images (numpy arrays)
        قائمة بصور الأسطر المقصوصة
    """
    if img_gray is None:
        return []

    _, thresh = cv2.threshold(
        img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    proj = np.sum(thresh, axis=1)

    lines = []
    in_line = False
    start = 0

    # Dynamic threshold based on projection distribution
    nonzero_proj = proj[proj > 0]
    thr = np.percentile(nonzero_proj, 15) if len(nonzero_proj) > 0 else 30

    for y in range(len(proj)):
        if proj[y] > thr and not in_line:
            in_line = True
            start = y
        elif proj[y] <= thr and in_line:
            in_line = False
            if y - start >= min_height:
                lines.append((start, y))

    # Handle last line if image ends while still in a line
    if in_line and len(proj) - start >= min_height:
        lines.append((start, len(proj)))

    # Crop with padding, clamped to image boundaries
    return [
        img_gray[max(0, y1 - padding): y2 + padding, :]
        for y1, y2 in lines
    ]


def build_dataset(text_file=None, images_dir=None, output_dir=None,
                  min_line_height=10, padding=5):
    """
    Main dataset building function.
    Reads corrected text, pairs lines with image crops, writes training data.

    الوظيفة الرئيسية لبناء مجموعة البيانات.
    يقرأ النص المصحح، يقرن الأسطر مع قصوص الصور، ويكتب بيانات التدريب.

    Args:
        text_file: Path to output_flat_text.txt / مسار ملف النص المصحح
        images_dir: Path to input images directory / مسار مجلد الصور المدخلة
        output_dir: Path to output dataset directory / مسار مجلد الإخراج
        min_line_height: Minimum height for a valid line crop / الحد الأدنى لارتفاع السطر
        padding: Padding pixels around each line / حشوة بالبكسل حول كل سطر
    """
    text_file = Path(text_file) if text_file else DEFAULT_TEXT_FILE
    images_dir = Path(images_dir) if images_dir else DEFAULT_IMAGES_DIR
    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DATASET

    # Create output directories
    images_output = output_dir / 'images'
    images_output.mkdir(parents=True, exist_ok=True)

    if not text_file.exists():
        print(f"[خطأ] Error: Text file not found: {text_file}")
        print(f"       تأكد من أن ملف النص المصحح موجود في المسار المحدد")
        return

    if not images_dir.exists():
        print(f"[خطأ] Error: Images directory not found: {images_dir}")
        print(f"       تأكد من أن مجلد الصور موجود في المسار المحدد")
        return

    print(f"[معلومات] Text file / ملف النص:   {text_file}")
    print(f"[معلومات] Images dir / مجلد الصور: {images_dir}")
    print(f"[معلومات] Output dir / مجلد الإخراج: {output_dir}")
    print("-" * 60)

    content = text_file.read_text(encoding='utf-8')

    # Split by --- filename.jpg --- delimiters
    pages_data = re.split(r'--- (.*\.jpg) ---\n', content)

    if len(pages_data) < 3:
        print("[تحذير] Warning: No page delimiters found in text file.")
        print("         Expected format: --- filename.jpg ---")
        print("         التنسيق المتوقع: --- filename.jpg ---")
        return

    pages_iter = iter(pages_data[1:])
    total_lines = 0
    total_pages = 0
    labels_content = []
    errors = []

    try:
        while True:
            img_name = next(pages_iter)
            text_block = next(pages_iter)
            total_pages += 1

            img_path = images_dir / img_name
            if not img_path.exists():
                msg = f"Image not found / الصورة غير موجودة: {img_name}"
                print(f"  [تحذير] Warning: {msg}")
                errors.append(msg)
                continue

            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                msg = f"Failed to read image / فشل في قراءة الصورة: {img_name}"
                print(f"  [تحذير] Warning: {msg}")
                errors.append(msg)
                continue

            # Clean scribbles then crop lines
            clean_img = clean_scribbles(img)
            line_crops = get_line_crops(clean_img, min_height=min_line_height,
                                        padding=padding)

            # Split text block into individual lines
            text_lines = [
                t.strip() for t in text_block.strip().split('\n') if t.strip()
            ]

            count = min(len(line_crops), len(text_lines))

            for i in range(count):
                base_name = img_name.replace('.jpg', '')
                new_name = f"{base_name}_L{i:03d}.png"
                crop_path = images_output / new_name

                cv2.imwrite(str(crop_path), line_crops[i])
                labels_content.append(f"{new_name}\t{text_lines[i]}")
                total_lines += 1

            # Warn about mismatched line counts
            diff = abs(len(line_crops) - len(text_lines))
            if diff > 0:
                msg = (f"Line count mismatch in {img_name}: "
                       f"{len(line_crops)} image lines vs {len(text_lines)} text lines")
                errors.append(msg)

            print(f"  [تم] Processed {img_name}: {count} lines / سطور")

    except StopIteration:
        pass

    # Write labels file
    labels_path = output_dir / 'labels.txt'
    labels_path.write_text('\n'.join(labels_content), encoding='utf-8')

    # Summary
    print("-" * 60)
    print(f"[نتيجة] Dataset built successfully!")
    print(f"        تم بناء مجموعة البيانات بنجاح!")
    print(f"        Pages processed / الصفحات المعالجة: {total_pages}")
    print(f"        Lines extracted / الأسطر المستخرجة: {total_lines}")
    print(f"        Location / الموقع: {output_dir}")
    print(f"        Labels file / ملف التسميات: {labels_path}")

    if errors:
        print(f"\n[تحذير] Warnings ({len(errors)}):")
        for e in errors[:10]:  # Show first 10 errors
            print(f"  - {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")


if __name__ == "__main__":
    args = parse_args()
    build_dataset(
        text_file=args.text_file,
        images_dir=args.images_dir,
        output_dir=args.output_dir,
        min_line_height=args.min_line_height,
        padding=args.padding,
    )
