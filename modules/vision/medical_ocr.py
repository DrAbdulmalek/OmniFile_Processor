#!/usr/bin/env python3
"""
Medical Handwriting OCR - Offline Pipeline v12.0
==================================================
يدعم العربية والإنجليزية، يعمل محلياً، يعالج PDF والصور، ويُصدر JSON و HTML.

القدرات:
- استخراج النصوص من ملفات PDF (PyMuPDF) والصور
- معالجة مسبقة: CLAHE + Otsu binarization + تقسيم الأسطر
- تصحيح تلقائي باستخدام قاموس طبي مخصص (regex)
- تصدير نتائج JSON + HTML تفاعلي للمراجعة البشرية
- تكامل مع EasyOCR (عربي + إنجليزي)

OmniFile AI Processor - وحدة معالجة النصوص الطبية المكتوبة بخط اليد
"""

import os
import re
import json
import cv2
import numpy as np
import fitz  # PyMuPDF
import easyocr
from pathlib import Path
from typing import List, Dict, Any, Union


class MedicalOCRProcessor:
    """
    معالج OCR الطبي للنصوص المكتوبة بخط اليد.

    Usage:
        ocr = MedicalOCRProcessor(use_gpu=False)
        results = ocr.process_pdf("notes.pdf", max_pages=10)
        ocr.save_results(results, "./output")
        ocr.generate_html_review(results, "./output/review.html")
    """

    def __init__(self, use_gpu: bool = False, dict_path: Union[str, Path] = None):
        self.device = "cuda" if use_gpu and cv2.cuda.getCudaEnabledDeviceCount() else "cpu"
        print(f"[MedicalOCR] تحميل النماذج على {self.device}...")
        self.reader = easyocr.Reader(
            ['ar', 'en'],
            gpu=(self.device == "cuda"),
            verbose=False,
            paragraph=False
        )

        # تحميل القاموس الطبي
        self.dict_path = Path(dict_path) if dict_path else Path(__file__).parent.parent.parent / "config" / "medical_dict.json"
        self.corrections = self._load_dict()
        print(f"[MedicalOCR] تم تحميل {len(self.corrections)} تصحيحاً طبياً")

    def _load_dict(self) -> Dict[str, str]:
        """تحميل القاموس الطبي مع دمج القاموس الافتراضي مع القاموس المخصص."""
        default = {
            r'\bHkstovy\b': 'History',
            r'\baPpslyai\b': 'Physical Examination',
            r'\bgslwigeociis\b': 'Clinical Evaluation',
            r'\bFibrous elyspasi\b': 'Fibrous Dysplasia',
            r'\bAnuerysm bonccge kyste\b': 'Aneurysmal Bone Cyst',
            r'\bAVN\b': 'Avascular Necrosis',
            r'\bLMWH\b': 'Low Molecular Weight Heparin',
            r'\bبون سكان\b': 'المسح العظمي',
            r'\bكيس عظمي وحيد\b': 'كيسة عظمية وحيدة',
            r'\bورم حبيبي يوزيني\b': 'ورم حبيبي أيوزيني',
        }

        if self.dict_path and self.dict_path.exists():
            try:
                with open(self.dict_path, 'r', encoding='utf-8') as f:
                    user = json.load(f)
                    default.update({re.escape(k): v for k, v in user.items()})
            except Exception as e:
                print(f"[MedicalOCR] تحذير: فشل تحميل القاموس المخصص ({e})")

        return default

    def _correct_text(self, text: str) -> str:
        """تصحيح النص باستخدام القاموس الطبي (regex-based)."""
        for pattern, repl in self.corrections.items():
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', text).strip()

    def process_image(self, image_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        معالجة صورة واحدة واستخراج النصوص.

        Args:
            image_path: مسار ملف الصورة (PNG, JPG, etc.)

        Returns:
            قائمة بالأسطر المستخرجة مع النص الخام والمصحح
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"الملف غير موجود: {image_path}")

        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"فشل قراءة الصورة: {image_path}")

        return self._extract_lines(img, page_num=1)

    def process_pdf(self, pdf_path: Union[str, Path], max_pages: int = None) -> List[Dict[str, Any]]:
        """
        معالجة ملف PDF واستخراج النصوص من كل صفحة.

        Args:
            pdf_path: مسار ملف PDF
            max_pages: الحد الأقصى لعدد الصفحات (None = الكل)

        Returns:
            قائمة بنتائج كل صفحة مع الأسطر المستخرجة
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"الملف غير موجود: {pdf_path}")

        doc = fitz.open(str(pdf_path))
        total = len(doc) if max_pages is None else min(max_pages, len(doc))
        results = []

        for pnum in range(total):
            page = doc[pnum]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img = np.frombuffer(pix.tobytes(), np.uint8).reshape(pix.h, pix.w, 4)
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

            page_lines = self._extract_lines(img, page_num=pnum + 1)
            results.append({"page": pnum + 1, "lines": page_lines})

        doc.close()
        return results

    def _extract_lines(self, img: np.ndarray, page_num: int = 1) -> List[Dict[str, Any]]:
        """
        استخراج الأسطر من صورة مع المعالجة المسبقة والتعرف على النصوص.

        الخطوات:
        1. تحويل للرمادي
        2. CLAHE (تحسين التباين)
        3. Otsu Binarization
        4. تقسيم أفقي للأسطر (projection profile)
        5. EasyOCR لكل سطر
        6. تصحيح بالقاموس الطبي
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # CLAHE - تحسين التباين المحلي
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Otsu Binarization
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # تقسيم الأسطر باستخدام Projection Profile
        proj = np.sum(binary > 0, axis=1)
        lines = []
        start, in_line = 0, False
        thr = np.percentile(proj[proj > 0], 20) if np.any(proj > 0) else 30

        for y, val in enumerate(proj):
            if val > thr and not in_line:
                in_line, start = True, y
            elif val <= thr and in_line:
                in_line = False
                if y - start >= 12:
                    lines.append((start, y))

        if in_line and len(proj) - start >= 12:
            lines.append((start, len(proj)))

        # استخراج النصوص من كل سطر
        page_lines = []
        for y1, y2 in lines:
            crop = img[y1:y2, :]
            if crop.size == 0:
                continue

            raw = " ".join(self.reader.readtext(crop, detail=0, paragraph=False)).strip()
            if raw:
                page_lines.append({
                    "raw": raw,
                    "corrected": self._correct_text(raw),
                    "bbox": (0, y1, crop.shape[1], y2),
                    "page": page_num,
                })

        return page_lines

    def save_results(self, results: List[Dict], output_dir: Union[str, Path]) -> Path:
        """
        حفظ النتائج بتنسيق JSON.

        Args:
            results: نتائج process_pdf أو process_image
            output_dir: مجلد المخرجات

        Returns:
            مسار ملف JSON
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "ocr_results.json"

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"[MedicalOCR] حفظ JSON: {json_path}")
        return json_path

    def generate_html_review(self, results: List[Dict], output_html: Union[str, Path]) -> Path:
        """
        إنشاء صفحة HTML تفاعلية لمراجعة وتصحيح النصوص المستخرجة.

        Args:
            results: نتائج process_pdf أو process_image
            output_html: مسار ملف HTML الناتج

        Returns:
            مسار ملف HTML
        """
        html_template = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>مراجعة OCR الطبية</title>
<style>
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f2f5; padding: 20px; margin: 0; }
.container { max-width: 1200px; margin: auto; background: white; border-radius: 12px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
h2 { color: #2c3e50; margin-bottom: 5px; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; }
th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: right; }
th { background: #2c3e50; color: white; font-weight: 600; }
.raw { color: #e74c3c; font-family: 'Courier New', monospace; background: #fef2f2; padding: 8px; border-radius: 6px; display: block; font-size: 14px; }
input { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; box-sizing: border-box; transition: border-color 0.2s; }
input:focus { outline: none; border-color: #3498db; }
input.edited { border-color: #27ae60; background: #eafaf1; }
.btn { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin-top: 20px; transition: background 0.2s; }
.btn:hover { background: #2980b9; }
.stats { background: #ecf0f1; padding: 15px; border-radius: 8px; margin: 15px 0; display: flex; gap: 20px; }
.stats span { font-size: 14px; color: #555; }
.stats strong { color: #2c3e50; }
.progress { height: 8px; background: #ecf0f1; border-radius: 4px; margin: 15px 0; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #27ae60, #2ecc71); width: 0%; border-radius: 4px; transition: width 0.3s ease; }
h3 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; }
</style>
</head>
<body>
<div class="container">
<h2>مراجعة وتصحيح النصوص الطبية المستخرجة</h2>
<div class="stats">
  <span>إجمالي الأسطر: <strong id="totalLines">0</strong></span>
  <span>تمت المراجعة: <strong id="reviewed">0</strong></span>
  <span>التقدم: <strong id="progressPercent">0%</strong></span>
</div>
<div class="progress"><div class="progress-fill" id="progressFill"></div></div>
<div id="content"></div>
<button class="btn" onclick="exportCorrections()">تصدير التصحيحات (JSON)</button>
</div>
<script>
const data = DATA_PLACEHOLDER;
let total = 0, reviewed = 0;

function escapeHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function render() {
    let html = '';
    data.forEach(page => {
        html += '<h3>صفحة ' + page.page + '</h3>';
        html += '<table><thead><tr><th>#</th><th style="width:40%">النص الخام</th><th style="width:50%">النص المصحح</th></tr></thead><tbody>';
        page.lines.forEach((line, idx) => {
            total++;
            html += '<tr>';
            html += '<td>' + (idx+1) + '</td>';
            html += '<td><div class="raw">' + escapeHtml(line.raw) + '</div></td>';
            html += '<td><input type="text" id="page' + page.page + '_line' + idx + '" value="' + escapeHtml(line.corrected) + '" onchange="markReviewed(' + page.page + ',' + idx + ',this.value)"></td>';
            html += '</tr>';
        });
        html += '</tbody></table>';
    });
    document.getElementById('content').innerHTML = html;
    document.getElementById('totalLines').innerText = total;
}

function markReviewed(page, idx, newVal) {
    const pageData = data.find(p => p.page === page);
    if (pageData) {
        pageData.lines[idx].corrected = newVal;
        pageData.lines[idx].reviewed = true;
    }
    reviewed = data.reduce((acc, p) => acc + p.lines.filter(l => l.reviewed).length, 0);
    document.getElementById('reviewed').innerText = reviewed;
    const pct = Math.round((reviewed / total) * 100);
    document.getElementById('progressFill').style.width = pct + '%';
    document.getElementById('progressPercent').innerText = pct + '%';
}

function exportCorrections() {
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'medical_corrections.json';
    a.click();
    URL.revokeObjectURL(a.href);
}

render();
</script>
</body>
</html>"""

        html_content = html_template.replace(
            "DATA_PLACEHOLDER", json.dumps(results, ensure_ascii=False)
        )
        out_path = Path(output_html)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html_content, encoding='utf-8')

        print(f"[MedicalOCR] HTML تم إنشاؤه: {out_path}")
        return out_path


def process_medical_pdf(
    pdf_path: Union[str, Path],
    output_dir: str = "./medical_ocr_output",
    max_pages: int = None,
    use_gpu: bool = False,
) -> tuple:
    """
    وظيفة مساعدة لمعالجة PDF وإرجاع المسارات الناتجة.

    Args:
        pdf_path: مسار ملف PDF
        output_dir: مجلد المخرجات
        max_pages: الحد الأقصى لعدد الصفحات
        use_gpu: استخدام GPU

    Returns:
        (json_path, html_path) - مساري الملفات الناتجة
    """
    ocr = MedicalOCRProcessor(use_gpu=use_gpu)
    results = ocr.process_pdf(pdf_path, max_pages=max_pages)
    json_path = ocr.save_results(results, output_dir)
    html_path = ocr.generate_html_review(results, Path(output_dir) / "review.html")
    return str(json_path), str(html_path)


def main():
    """نقطة الدخول لتشغيل المعالجة من سطر الأوامر."""
    import argparse

    p = argparse.ArgumentParser(description="Medical Handwriting OCR - Offline Pipeline v12.0")
    p.add_argument("input", help="مسار ملف PDF أو صورة")
    p.add_argument("-o", "--output", default="./ocr_output", help="مجلد المخرجات")
    p.add_argument("--max-pages", type=int, default=None, help="الحد الأقصى لعدد الصفحات")
    p.add_argument("--gpu", action="store_true", help="استخدام GPU")
    args = p.parse_args()

    ocr = MedicalOCRProcessor(use_gpu=args.gpu)

    input_path = Path(args.input)
    if input_path.suffix.lower() == ".pdf":
        results = ocr.process_pdf(args.input, max_pages=args.max_pages)
    else:
        lines = ocr.process_image(args.input)
        results = [{"page": 1, "lines": lines}]

    ocr.save_results(results, args.output)
    ocr.generate_html_review(results, Path(args.output) / "review.html")
    print("تمت المعالجة. افتح review.html في المتصفح للمراجعة.")


if __name__ == "__main__":
    main()
