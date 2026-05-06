#!/usr/bin/env python3
"""Lightweight OCR benchmark utility for OmniFile AI Processor.

يشغّل محركات OCR على مجموعة صور ويُنتج تقرير JSON/CSV مبسطاً عن السرعة
والنصوص الناتجة، مع إمكانية مقارنة اختيارية ضد ground truth.

Usage:
    python tools/benchmark_ocr.py --images samples/ --output artifacts/ocr_benchmark
    python tools/benchmark_ocr.py --images samples/ --ground-truth samples/ground_truth.json \
        --engines easyocr trocr --output artifacts/ocr_benchmark
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

from modules.evaluation.metrics import calculate_cer, calculate_wer
from modules.vision.ocr_engine import OCREngine

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def load_ground_truth(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, dict):
        return {str(k): str(v) for k, v in payload.items()}
    raise ValueError("ground truth file must be a JSON object mapping filename to text")


def iter_images(folder: Path):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def build_engine_kwargs(enabled_engines: list[str]) -> dict[str, Any]:
    enabled = set(enabled_engines or [])
    return {
        "enable_easyocr": not enabled or "easyocr" in enabled,
        "enable_trocr": not enabled or "trocr" in enabled,
        "enable_tesseract": not enabled or "tesseract" in enabled,
        "enable_paddleocr": not enabled or "paddleocr" in enabled,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    avg_time = round(sum(item.get("processing_time", 0.0) for item in results) / total, 4) if total else 0.0
    with_gt = [item for item in results if item.get("has_ground_truth")]
    avg_cer = round(sum(item["cer"] for item in with_gt) / len(with_gt), 4) if with_gt else None
    avg_wer = round(sum(item["wer"] for item in with_gt) / len(with_gt), 4) if with_gt else None
    return {
        "total_images": total,
        "images_with_ground_truth": len(with_gt),
        "average_processing_time_sec": avg_time,
        "average_cer": avg_cer,
        "average_wer": avg_wer,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark OmniFile OCR engines on a folder of images")
    parser.add_argument("--images", required=True, help="Folder containing input images")
    parser.add_argument("--ground-truth", help="Optional JSON file mapping filename to expected text")
    parser.add_argument(
        "--engines",
        nargs="*",
        choices=["easyocr", "trocr", "tesseract", "paddleocr"],
        default=[],
        help="Restrict benchmark to selected engines",
    )
    parser.add_argument("--languages", nargs="*", default=["ar", "en"], help="OCR languages")
    parser.add_argument("--output", required=True, help="Output prefix, e.g. artifacts/ocr_benchmark")
    args = parser.parse_args()

    image_dir = Path(args.images)
    output_prefix = Path(args.output)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)

    ground_truth = load_ground_truth(Path(args.ground_truth) if args.ground_truth else None)
    engine = OCREngine(**build_engine_kwargs(args.engines))

    results: list[dict[str, Any]] = []
    for image_path in iter_images(image_dir):
        started = time.perf_counter()
        ocr_result = engine.recognize(str(image_path), languages=args.languages)
        processing_time = round(time.perf_counter() - started, 4)
        text = (ocr_result or {}).get("text", "")

        item = {
            "file": image_path.name,
            "path": str(image_path),
            "source": (ocr_result or {}).get("source", "unknown"),
            "confidence": (ocr_result or {}).get("confidence", 0.0),
            "processing_time": processing_time,
            "text_length": len(text),
            "text_preview": text[:200],
            "has_ground_truth": image_path.name in ground_truth,
        }

        if image_path.name in ground_truth:
            reference = ground_truth[image_path.name]
            cer, _, _ = calculate_cer(reference, text)
            wer, _, _ = calculate_wer(reference, text)
            item["cer"] = round(cer, 4)
            item["wer"] = round(wer, 4)

        results.append(item)

    summary = summarize(results)
    report = {
        "summary": summary,
        "config": {
            "images": str(image_dir),
            "engines": args.engines or ["easyocr", "trocr", "tesseract", "paddleocr"],
            "languages": args.languages,
            "ground_truth": args.ground_truth,
        },
        "results": results,
    }

    json_path = output_prefix.with_suffix(".json")
    csv_path = output_prefix.with_suffix(".csv")

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    fieldnames = [
        "file", "path", "source", "confidence", "processing_time", "text_length",
        "has_ground_truth", "cer", "wer", "text_preview",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({key: row.get(key) for key in fieldnames})

    print(f"✅ JSON report: {json_path}")
    print(f"✅ CSV report: {csv_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
