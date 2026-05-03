#!/usr/bin/env python3
"""
سكربت شامل: OCR -> تصحيح مختلط -> كشف جداول -> تطبيع -> تصدير مطابق.
========================================================================
سير عمل متكامل من الصورة إلى التصدير المنسق.

الاستخدام:
    # معالجة كاملة مع التصحيح والتصدير
    python process.py --input image.jpg --output out --engine surya \\
        --langs ar en --correct --detect-tables --export-docx

    # OCR فقط مع Surya
    python process.py --input image.jpg --output out --engine surya

    # مع Tesseract والتصدير
    python process.py --input image.jpg --output out --engine tesseract \\
        --correct --export-docx

المؤلف: Dr Abdulmalek Tamer Al-husseini
الترخيص: MIT
"""

import argparse
import json
import os
import sys
import logging
from datetime import datetime

# إضافة جذر المشروع إلى المسار
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("process")


def parse_args():
    """تحليل معلمات سطر الأوامر."""
    parser = argparse.ArgumentParser(
        description="سكربت معالجة متكامل لـ OmniFile Processor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  python process.py -i image.jpg -o results -e surya
  python process.py -i doc.pdf -o out -e tesseract --correct --export-docx
  python process.py -i scan.png -o out -e surya --detect-tables --langs ar en
        """,
    )
    parser.add_argument(
        "-i", "--input", required=True,
        help="مسار ملف الإدخال (صورة JPG/PNG أو PDF)",
    )
    parser.add_argument(
        "-o", "--output", required=True,
        help="مسار مجلد الإخراج",
    )
    parser.add_argument(
        "-e", "--engine", default="tesseract",
        choices=["tesseract", "easyocr", "trocr", "paddleocr", "surya"],
        help="محرك OCR (الافتراضي: tesseract)",
    )
    parser.add_argument(
        "-l", "--langs", nargs="+", default=["ar", "en"],
        help="اللغات المطلوبة (الافتراضي: ar en)",
    )
    parser.add_argument(
        "--correct", action="store_true",
        help="تفعيل تصحيح اللغات المختلطة",
    )
    parser.add_argument(
        "--detect-tables", action="store_true",
        help="تفعيل كشف الجداول (يتطلب transformers+torch)",
    )
    parser.add_argument(
        "--export-docx", action="store_true",
        help="تصدير DOCX مطابق للتنسيق",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.7,
        help="عتبة كشف الجداول (الافتراضي: 0.7)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="عرض معلومات تفصيلية",
    )
    return parser.parse_args()


def run_ocr_by_engine(engine_name: str, image_path: str, langs: list[str]):
    """
    تشغيل محرك OCR المحدد وإرجاع (نص, كتل خام).

    Args:
        engine_name: اسم المحرك
        image_path: مسار الصورة
        langs: اللغات المطلوبة

    Returns:
        tuple (نص كامل, قائمة كتل)
    """
    if engine_name == "surya":
        from modules.vision.surya_ocr import SuryaOCREngine
        engine = SuryaOCREngine(langs=langs)
        text, blocks = engine.extract_text(image_path)
        return text, blocks

    elif engine_name == "tesseract":
        import pytesseract
        from PIL import Image
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang="+".join(langs))
        blocks = []
        for line in text.strip().split("\n"):
            if line.strip():
                blocks.append({
                    "type": "paragraph",
                    "bbox": [0, 0, 1, 1],
                    "text": line.strip(),
                    "confidence": 0.8,
                })
        return text, blocks

    elif engine_name == "easyocr":
        import easyocr
        import numpy as np
        from PIL import Image
        reader = easyocr.Reader(langs, gpu=False, verbose=False)
        img = np.array(Image.open(image_path).convert("RGB"))
        results = reader.readtext(img)
        blocks = []
        full_text = []
        for bbox, text, conf in results:
            blocks.append({
                "type": "paragraph",
                "bbox": [0, 0, 1, 1],
                "text": text,
                "confidence": float(conf),
            })
            full_text.append(text)
        return "\n".join(full_text), blocks

    elif engine_name == "trocr":
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        from PIL import Image
        import torch
        processor = TrOCRProcessor.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        model = VisionEncoderDecoderModel.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        image = Image.open(image_path).convert("RGB")
        pixel_values = processor(image, return_tensors="pt").pixel_values
        with torch.no_grad():
            generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]
        blocks = [{
            "type": "paragraph",
            "bbox": [0, 0, 1, 1],
            "text": text,
            "confidence": 0.85,
        }]
        return text, blocks

    elif engine_name == "paddleocr":
        from paddleocr import PaddleOCR
        import numpy as np
        from PIL import Image
        ocr = PaddleOCR(use_angle_cls=True, lang="ar", use_gpu=False, show_log=False)
        img = np.array(Image.open(image_path).convert("RGB"))
        results = ocr.ocr(img, cls=True)
        blocks = []
        full_text = []
        if results and results[0]:
            for item in results[0]:
                text, conf = item[1]
                blocks.append({
                    "type": "paragraph",
                    "bbox": [0, 0, 1, 1],
                    "text": text,
                    "confidence": float(conf),
                })
                full_text.append(text)
        return "\n".join(full_text), blocks

    else:
        raise ValueError(f"محرك غير معروف: {engine_name}")


def main():
    """الدالة الرئيسية لسير العمل المتكامل."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("OmniFile Processor — سير العمل المتكامل")
    logger.info("=" * 60)
    logger.info("ملف الإدخال:  %s", args.input)
    logger.info("مجلد الإخراج: %s", args.output)
    logger.info("المحرك:        %s", args.engine)
    logger.info("اللغات:         %s", args.langs)
    logger.info("-" * 60)

    # إنشاء مجلد الإخراج
    os.makedirs(args.output, exist_ok=True)

    # ─── 1. تشغيل OCR ───
    logger.info("[1/5] تشغيل OCR بمحرك %s...", args.engine)
    try:
        text, raw_blocks = run_ocr_by_engine(
            args.engine, args.input, args.langs
        )
        logger.info(
            "تم استخراج %d حرف في %d كتلة",
            len(text),
            len(raw_blocks),
        )
    except Exception as e:
        logger.error("فشل OCR: %s", e)
        sys.exit(1)

    # ─── 2. تصحيح النص المختلط ───
    if args.correct:
        logger.info("[2/5] تصحيح اللغات المختلطة...")
        try:
            from modules.nlp.mixed_language import MixedLanguageHandler
            handler = MixedLanguageHandler(languages=args.langs)
            text = handler.correct_text_mixed(text)
            for block in raw_blocks:
                if "text" in block:
                    block["text"] = handler.correct_text_mixed(block["text"])
            logger.info("تم تصحيح النص المختلط")
        except Exception as e:
            logger.warning("فشل التصحيح المختلط: %s", e)
    else:
        logger.info("[2/5] تصحيح مختلط: معطّل")

    # ─── 3. كشف الجداول ───
    if args.detect_tables:
        logger.info("[3/5] كشف الجداول (TATR)...")
        try:
            from modules.vision.table_detection import TableDetectionTransformer
            detector = TableDetectionTransformer(device="cpu")
            tables = detector.detect_tables(args.input, threshold=args.threshold)
            logger.info("تم كشف %d جدول", len(tables))

            # تحويل الجداول المكتشفة إلى كتل وإضافتها
            from PIL import Image
            image = Image.open(args.input)
            w, h = image.size
            for t in tables:
                x1, y1, x2, y2 = t["bbox"]
                bbox_rel = [x1 / w, y1 / h, x2 / w, y2 / h]
                raw_blocks.append({
                    "type": "table",
                    "bbox": bbox_rel,
                    "confidence": t["score"],
                    "cells": [],
                    "label": t["label"],
                })
        except Exception as e:
            logger.warning("فشل كشف الجداول: %s", e)
    else:
        logger.info("[3/5] كشف الجداول: معطّل")

    # ─── 4. تطبيع النتائج ───
    logger.info("[4/5] تطبيع النتائج إلى الهيكل القياسي...")
    try:
        from modules.vision.normalize import (
            normalize_ocr_output,
            save_normalized,
        )
        from PIL import Image

        img = Image.open(args.input)
        normalized = normalize_ocr_output(
            raw_blocks, args.input, img.width, img.height,
            args.engine, args.langs,
        )
        json_path = os.path.join(args.output, "result.json")
        save_normalized(normalized, json_path)
        logger.info("تم حفظ النتيجة الموحدة: %s", json_path)
    except Exception as e:
        logger.error("فشل التطبيع: %s", e)
        sys.exit(1)

    # ─── 5. تصدير DOCX ───
    if args.export_docx:
        logger.info("[5/5] تصدير DOCX مطابق للتنسيق...")
        try:
            from modules.export.layout_preserving import layout_to_docx
            docx_path = os.path.join(args.output, "output_preserved.docx")
            layout_to_docx(json_path, docx_path)
            logger.info("تم تصدير الملف المنسق: %s", docx_path)
        except Exception as e:
            logger.warning("فشل تصدير DOCX: %s", e)
    else:
        logger.info("[5/5] تصدير DOCX: معطّل")

    # ─── ملخص ───
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("-" * 60)
    logger.info("تمت المعالجة بنجاح!")
    logger.info("  الوقت: %.2f ثانية", elapsed)
    logger.info("  الكتل: %d", len(raw_blocks))
    logger.info("  المحرك: %s", args.engine)
    logger.info("  الإخراج: %s", args.output)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
