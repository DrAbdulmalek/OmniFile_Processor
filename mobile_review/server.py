"""
mobile_review/server.py — خادم Flask لمراجعة نتائج OCR من الجوال.

التشغيل:
    python mobile_review/server.py --host 0.0.0.0 --port 5000

ثم افتح http://<IP-الجهاز>:5000 من متصفح الهاتف.
للوصول عن بُعد: ngrok http 5000
"""
import json
import os
import argparse
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__, template_folder='templates')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ocr_result.json")
IMAGE_FOLDER = os.path.join(BASE_DIR, "images")
OUTPUT_FILE = os.path.join(BASE_DIR, "ocr_corrected.json")


@app.route('/')
def index():
    """الصفحة الرئيسية مع بيانات OCR."""
    data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    return render_template('review.html', data=data)


@app.route('/images/<path:filename>')
def serve_image(filename):
    """تقديم الصور الأصلية."""
    return send_from_directory(IMAGE_FOLDER, filename)


@app.route('/save', methods=['POST'])
def save_corrections():
    """حفظ التصحيحات من الواجهة."""
    corrections = request.get_json()
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2)
    return jsonify({"status": "success", "saved_to": OUTPUT_FILE})


@app.route('/load', methods=['GET'])
def load_corrections():
    """تحميل التصحيحات المحفوظة مسبقاً (للاستمرار من جلسة سابقة)."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OmniFile Mobile Review Server')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--data', help='مسار ملف نتائج OCR')
    parser.add_argument('--images', help='مجلد الصور')
    args = parser.parse_args()

    if args.data:
        DATA_FILE = args.data
    if args.images:
        IMAGE_FOLDER = args.images

    print(f"🚀 Mobile Review Server: http://{args.host}:{args.port}")
    print(f"📄 بيانات OCR: {DATA_FILE}")
    print(f"🖼️  مجلد الصور: {IMAGE_FOLDER}")
    app.run(host=args.host, port=args.port, debug=False)
