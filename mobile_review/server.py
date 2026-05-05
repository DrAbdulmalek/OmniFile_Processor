"""
mobile_review/server.py — خادم Flask لمراجعة نتائج OCR من الجوال.

التشغيل:
    python mobile_review/server.py --host 0.0.0.0 --port 5000

ثم افتح http://<IP-الجهاز>:5000 من متصفح الهاتف.
للوصول عن بُعد: ngrok http 5000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__, template_folder="templates")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.build_training_data import build_dataset, write_outputs  # noqa: E402

DATA_FILE = os.path.join(BASE_DIR, "ocr_result.json")
IMAGE_FOLDER = os.path.join(BASE_DIR, "images")
OUTPUT_FILE = os.path.join(BASE_DIR, "ocr_corrected.json")
DATASET_OUTPUT_DIR = os.path.join(BASE_DIR, "dataset")


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_output_prefix(custom_output: str | None = None) -> Path:
    if custom_output:
        return Path(custom_output)
    return Path(DATASET_OUTPUT_DIR) / "review_dataset"


def export_review_dataset(output_prefix: str | None = None) -> dict[str, Any]:
    """تحويل التصحيحات المحفوظة إلى JSONL وملف ملخص."""
    if not os.path.exists(OUTPUT_FILE):
        raise FileNotFoundError("لا يوجد ملف تصحيحات محفوظ حتى الآن")

    payload = _load_json(OUTPUT_FILE)
    records, summary = build_dataset(payload)
    output_path = _resolve_output_prefix(output_prefix)
    write_outputs(records, summary, output_path)

    return {
        "status": "success",
        "input_file": OUTPUT_FILE,
        "output_jsonl": str(output_path.with_suffix(".jsonl")),
        "output_summary": str(output_path.with_name(output_path.name + "_summary.json")),
        "summary": summary,
    }


@app.route("/")
def index():
    """الصفحة الرئيسية مع بيانات OCR."""
    data = {}
    if os.path.exists(DATA_FILE):
        data = _load_json(DATA_FILE)
    return render_template("review.html", data=data)


@app.route("/images/<path:filename>")
def serve_image(filename):
    """تقديم الصور الأصلية."""
    return send_from_directory(IMAGE_FOLDER, filename)


@app.route("/save", methods=["POST"])
def save_corrections():
    """حفظ التصحيحات من الواجهة."""
    corrections = request.get_json(silent=True)
    if corrections is None:
        return jsonify({"status": "error", "message": "لم يتم إرسال JSON صالح"}), 400

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2)

    item_count = len(corrections) if isinstance(corrections, list) else 1
    return jsonify({"status": "success", "saved_to": OUTPUT_FILE, "items": item_count})


@app.route("/load", methods=["GET"])
def load_corrections():
    """تحميل التصحيحات المحفوظة مسبقاً (للاستمرار من جلسة سابقة)."""
    if os.path.exists(OUTPUT_FILE):
        return jsonify(_load_json(OUTPUT_FILE))
    return jsonify({})


@app.route("/export_dataset", methods=["GET", "POST"])
def export_dataset_route():
    """تحويل تصحيحات المراجعة إلى JSONL صالح للتدريب والتحليل."""
    try:
        custom_output = request.args.get("output") or (request.get_json(silent=True) or {}).get("output")
        result = export_review_dataset(custom_output)
        return jsonify(result)
    except FileNotFoundError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 404
    except Exception as exc:  # pragma: no cover - حماية للخادم
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniFile Mobile Review Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--data", help="مسار ملف نتائج OCR")
    parser.add_argument("--images", help="مجلد الصور")
    parser.add_argument("--export-dataset", action="store_true", help="حوّل ملف التصحيحات الحالي إلى JSONL ثم اخرج")
    parser.add_argument("--export-output", help="مسار prefix لملفات dataset الناتجة")
    args = parser.parse_args()

    if args.data:
        DATA_FILE = args.data
    if args.images:
        IMAGE_FOLDER = args.images

    if args.export_dataset:
        result = export_review_dataset(args.export_output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0)

    print(f"🚀 Mobile Review Server: http://{args.host}:{args.port}")
    print(f"📄 بيانات OCR: {DATA_FILE}")
    print(f"🖼️  مجلد الصور: {IMAGE_FOLDER}")
    print("🧪 تصدير dataset: GET /export_dataset أو --export-dataset")
    app.run(host=args.host, port=args.port, debug=False)
