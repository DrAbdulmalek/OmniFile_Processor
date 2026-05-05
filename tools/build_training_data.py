#!/usr/bin/env python3
"""Build lightweight training data from OCR review corrections.

يدعم ملفات JSON الصادرة من واجهات المراجعة اليدوية أو ملفات مشابهة تحتوي
على كتل نصية مع bbox أو image_path. الهدف هو تحويل التصحيحات إلى JSONL
سهل الاستخدام في التدريب أو التحليل اللاحق.

Usage:
    python tools/build_training_data.py \
        --corrections mobile_review/ocr_corrected.json \
        --output dataset/review_dataset

Outputs:
    - {output}.jsonl      : one record per reviewed block
    - {output}_summary.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _iter_items(payload: Any):
    if isinstance(payload, list):
        for item in payload:
            yield item
        return

    if isinstance(payload, dict):
        for key in ("items", "blocks", "results", "pages", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                for item in value:
                    yield item
                return
        yield payload


def _pick_text(item: dict[str, Any]) -> tuple[str, str]:
    original = (
        item.get("original_text")
        or item.get("ocr_text")
        or item.get("text_before")
        or item.get("raw_text")
        or item.get("text")
        or ""
    )
    corrected = (
        item.get("corrected_text")
        or item.get("text_after")
        or item.get("final_text")
        or item.get("reviewed_text")
        or item.get("text")
        or original
    )
    return str(original), str(corrected)


def _pick_bbox(item: dict[str, Any]):
    return item.get("bbox") or item.get("box") or item.get("bounding_box")


def build_dataset(payload: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    changed = 0

    for idx, item in enumerate(_iter_items(payload), start=1):
        if not isinstance(item, dict):
            continue

        original, corrected = _pick_text(item)
        if not original and not corrected:
            continue

        record = {
            "id": item.get("id") or f"sample-{idx:05d}",
            "image_path": item.get("image_path") or item.get("image") or item.get("page_image"),
            "page": item.get("page") or item.get("page_num"),
            "block_type": item.get("block_type") or item.get("type") or "text",
            "bbox": _pick_bbox(item),
            "ocr_text": original,
            "corrected_text": corrected,
            "changed": original != corrected,
            "metadata": item.get("metadata") or {},
        }
        if record["changed"]:
            changed += 1
        records.append(record)

    summary = {
        "total_records": len(records),
        "changed_records": changed,
        "unchanged_records": len(records) - changed,
        "change_ratio": round((changed / len(records)) if records else 0.0, 4),
    }
    return records, summary


def write_outputs(records: list[dict[str, Any]], summary: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path = output.with_suffix(".jsonl")
    summary_path = output.with_name(output.name + "_summary.json")

    with jsonl_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"✅ Wrote dataset: {jsonl_path}")
    print(f"✅ Wrote summary: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert OCR review corrections to JSONL dataset")
    parser.add_argument("--corrections", required=True, help="Path to corrections JSON file")
    parser.add_argument("--output", required=True, help="Output path prefix, e.g. dataset/review_dataset")
    args = parser.parse_args()

    corrections_path = Path(args.corrections)
    output_path = Path(args.output)

    payload = _load_json(corrections_path)
    records, summary = build_dataset(payload)
    write_outputs(records, summary, output_path)


if __name__ == "__main__":
    main()
