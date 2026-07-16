"""
وحدة تحويل مخرجات أي محرك OCR إلى الهيكل القياسي JSON.

هذه الوحدة مسؤولة عن توحيد نتائج جميع محركات OCR (Tesseract, EasyOCR,
TrOCR, PaddleOCR, Surya) في هيكل JSON موحد يمكن استهلاكه من وحدات
التصدير (layout_preserving.py) وواجهة المراجعة (mobile_review).

هيكل JSON القياسي:
{
    "metadata": {
        "source_file": "image.jpg",
        "processing_date": "2026-05-03T13:00:00",
        "engine": "surya",
        "languages_detected": ["ar", "en"],
        "page_count": 1,
        "version": "1.0"
    },
    "pages": [{
        "page_index": 0,
        "width": 2480,
        "height": 3508,
        "image_path": "image.jpg",
        "blocks": [{
            "id": "block_1",
            "type": "paragraph",
            "bbox": [0.1, 0.2, 0.9, 0.3],
            "text": "...",
            "confidence": 0.95
        }]
    }]
}

المؤلف: Dr Abdulmalek Tamer Al-husseini
الترخيص: MIT
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def normalize_ocr_output(
    raw_blocks: list[dict[str, Any]],
    image_path: str,
    page_width: int,
    page_height: int,
    engine_name: str,
    languages: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    تحويل كتل OCR الخام إلى الهيكل القياسي JSON.

    Args:
        raw_blocks: قائمة كائنات (block) من المحرك. كل كائن يحتوي على:
            - bbox (نسبي): [x1, y1, x2, y2]
            - text: النص
            - confidence: (اختياري) نسبة الثقة 0-1
            - type: نوع الكتلة ('paragraph', 'table', 'image', 'header', ...)
            - cells: (للجداول) قائمة صفوف تحتوي على نصوص الخلايا
            - image_file: (للصور) مسار ملف الصورة
            - caption: (للصور) {'text': ..., 'bbox': ...}
        image_path: مسار ملف الصورة الأصلي
        page_width: عرض الصورة بالبكسل
        page_height: ارتفاع الصورة بالبكسل
        engine_name: اسم المحرك المستخدم (surya, tesseract, easyocr, ...)
        languages: قائمة اللغات المكتشفة

    Returns:
        dict يمثل صفحة واحدة متوافقة مع الهيكل القياسي
    """
    if languages is None:
        languages = ["ar", "en"]

    blocks_normalized = []
    for idx, block in enumerate(raw_blocks):
        entry: dict[str, Any] = {
            "id": f"block_{idx + 1}",
            "type": block.get("type", "paragraph"),
            "bbox": block.get("bbox", [0, 0, 1, 1]),
            "text": block.get("text", ""),
            "confidence": block.get("confidence", 0.0),
        }

        # إذا كان جدولاً، التعامل مع الخلايا
        if entry["type"] == "table" and "cells" in block:
            cells_list = []
            cells_data = block["cells"]
            if isinstance(cells_data, list):
                for r_idx, row in enumerate(cells_data):
                    if isinstance(row, list):
                        for c_idx, cell_text in enumerate(row):
                            cells_list.append({
                                "row": r_idx,
                                "col": c_idx,
                                "text": str(cell_text),
                                "bbox": [],
                                "confidence": block.get("confidence", 0.0),
                            })
            entry["structure"] = {
                "rows": len(cells_data) if isinstance(cells_data, list) else 0,
                "cols": (
                    len(cells_data[0])
                    if isinstance(cells_data, list) and cells_data
                    else 0
                ),
                "cells": cells_list,
            }

        # التعامل مع الصور والتسميات
        if entry["type"] == "image":
            entry["image_file"] = block.get("image_file", "")
            if "caption" in block:
                caption_data = block["caption"]
                entry["caption"] = {
                    "text": caption_data.get("text", "")
                    if isinstance(caption_data, dict)
                    else str(caption_data),
                    "bbox": caption_data.get("bbox", [])
                    if isinstance(caption_data, dict)
                    else [],
                }

        blocks_normalized.append(entry)

    # بناء كائن الصفحة
    page = {
        "page_index": 0,
        "width": page_width,
        "height": page_height,
        "image_path": image_path,
        "blocks": blocks_normalized,
    }

    # بناء الهيكل الكامل
    result = {
        "metadata": {
            "source_file": image_path,
            "processing_date": datetime.now(timezone.utc).isoformat(),
            "engine": engine_name,
            "languages_detected": languages,
            "page_count": 1,
            "version": "1.0",
        },
        "pages": [page],
    }

    logger.info(
        "تم تطبيع %d كتلة من محرك %s",
        len(blocks_normalized),
        engine_name,
    )

    return result


def merge_pages(normalized_results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    دمج نتائج تطبيع متعددة (صفحات متعددة) في نتيجة واحدة.

    Args:
        normalized_results: قائمة نتائج من normalize_ocr_output()

    Returns:
        dict يحتوي على كل الصفحات المدمجة
    """
    if not normalized_results:
        return {}

    if len(normalized_results) == 1:
        return normalized_results[0]

    # البدء بالنتيجة الأولى كأساس
    merged = {
        "metadata": dict(normalized_results[0]["metadata"]),
        "pages": [],
    }

    total_pages = 0
    all_engines = set()

    for result in normalized_results:
        for page in result.get("pages", []):
            page["page_index"] = total_pages
            merged["pages"].append(page)
            total_pages += 1

        meta = result.get("metadata", {})
        all_engines.add(meta.get("engine", "unknown"))

    merged["metadata"]["page_count"] = total_pages
    merged["metadata"]["engine"] = ", ".join(sorted(all_engines))

    return merged


def save_normalized(
    normalized_data: dict[str, Any],
    output_path: str,
) -> str:
    """
    حفظ النتيجة الموحدة في ملف JSON.

    Args:
        normalized_data: بيانات من normalize_ocr_output() أو merge_pages()
        output_path: مسار ملف JSON المطلوب

    Returns:
        مسار الملف المحفوظ
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalized_data, f, ensure_ascii=False, indent=2)

    logger.info("تم حفظ النتيجة الموحدة: %s", output_path)
    return output_path


def load_normalized(input_path: str) -> dict[str, Any]:
    """
    تحميل ملف JSON بتنسيق الهيكل القياسي.

    Args:
        input_path: مسار ملف JSON

    Returns:
        dict يحتوي على البيانات الموحدة
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # التحقق الأساسي من الهيكل
    if "pages" not in data:
        raise ValueError("ملف JSON غير صالح: يفتقد حقل 'pages'")
    if "metadata" not in data:
        raise ValueError("ملف JSON غير صالح: يفتقد حقل 'metadata'")

    return data
