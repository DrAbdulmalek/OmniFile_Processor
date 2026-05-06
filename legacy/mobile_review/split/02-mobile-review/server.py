# server.py - Flask server for mobile OCR review

import json
import os
import argparse
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

# تكوين المجلدات (يمكن تغييرها من سطر الأوامر)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ocr_result.json")
IMAGE_FOLDER = os.path.join(BASE_DIR, "images")

@app.route('/')
def index():
    """عرض الواجهة الرئيسية مع بيانات OCR إن وجدت"""
    data = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    return render_template('review.html', data=data)

@app.route('/images/<path:filename>')
def serve_image(filename):
    """تقديم الصور الأصلية من المجلد المحدد"""
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/save', methods=['POST'])
def save_corrections():
    """حفظ التصحيحات القادمة من الواجهة"""
    corrections = request.get_json()
    output_path = os.path.join(BASE_DIR, "ocr_corrected.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2)
    return jsonify({"status": "success", "path": output_path})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='عنوان الاستضافة')
    parser.add_argument('--port', type=int, default=5000, help='رقم المنفذ')
    args = parser.parse_args()

    print(f"🚀 شغّل المتصفح على http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)
