#!/usr/bin/env python3
"""
Offline Medical Handwriting OCR v11.0
التعرف الضوئي على الكتابة الطبية يدوياً - إصدار غير متصل

Works without internet | Custom medical dictionary | Page-line-word processing
يعمل بدون إنترنت | قاموس طبي مخصص | معالجة صف-سطر-كلمة

Supports:
- Arabic + English medical handwriting / كتابة طبية عربية وإنجليزية
- PDF processing via PyMuPDF / معالجة PDF
- Smart medical dictionary corrections / تصحيحات ذكية بالقاموس الطبي
- CLI and library usage / استخدام من سطر الأوامر ومكتبة

Usage:
    python offline_medical_ocr.py --image page.jpg
    python offline_medical_ocr.py --pdf report.pdf --output results.md
    python offline_medical_ocr.py --image page.jpg --gpu
    python offline_medical_ocr.py --dir ./scans/ --output-dir ./results/
"""

import os
import re
import cv2
import json
import argparse
import numpy as np
from pathlib import Path
from PIL import Image
from typing import Optional, List, Tuple, Dict


class OfflineMedicalOCR:
    """
    Complete offline medical handwriting OCR engine.
    محرك كامل للتعرف على الكتابة الطبية يعمل بدون إنترنت.

    Features:
    - EasyOCR with Arabic + English / EasyOCR مع عربية وإنجليزية
    - CLAHE image enhancement / تحسين الصور بـ CLAHE
    - Smart medical dictionary / قاموس طبي ذكي
    - Line grouping and section detection / تجميع الأسطر واكتشاف الأقسام
    - PDF support via PyMuPDF / دعم PDF عبر PyMuPDF
    """

    def __init__(self, use_gpu: bool = False, custom_dict_path: Optional[str] = None):
        """
        Initialize the OCR engine.
        تهيئة محرك OCR.

        Args:
            use_gpu: Enable GPU acceleration (default: False)
                     تفعيل تسريع GPU
            custom_dict_path: Path to custom JSON dictionary file
                              مسار ملف قاموس مخصص بصيغة JSON
        """
        self.use_gpu = use_gpu

        # Lazy-load easyocr to avoid startup cost when not needed
        self._reader = None

        # Load built-in medical dictionary
        self.medical_dict = self._default_medical_dict()

        # Load custom dictionary if provided
        if custom_dict_path:
            self.load_custom_dictionary(custom_dict_path)

    @property
    def reader(self):
        """Lazy-loaded EasyOCR reader instance. / كائن EasyOCR يُحمّل عند الحاجة."""
        if self._reader is None:
            try:
                import easyocr
            except ImportError:
                raise ImportError(
                    "EasyOCR is required. Install with: pip install easyocr\n"
                    "EasyOCR مطلوب. ثبته بـ: pip install easyocr"
                )
            self._reader = easyocr.Reader(
                ['ar', 'en'], gpu=self.use_gpu, verbose=False, paragraph=False
            )
        return self._reader

    @staticmethod
    def _default_medical_dict() -> Dict[str, str]:
        """
        Built-in medical dictionary for OCR error correction.
        قاموس طبي مدمج لتصحيح أخطاء OCR.

        Contains:
        - Arabic medical term corrections / تصحيحات المصطلحات الطبية العربية
        - English bone tumor terms / مصطلحات أورام العظام الإنجليزية
        - Common OCR misreads / أخطاء OCR الشائعة
        """
        return {
            # ---- Arabic medical corrections / تصحيحات طبية عربية ----
            r'بون سكان': 'المسح العظمي',
            r'كيس عظمي وحيد': 'كيسة عظمية وحيدة',
            r'ورم حبيبي يوزيني': 'ورم حبيبي أيوزيني',
            r'تكلسات جانبية': 'تكلسات جانبية للعمود الفقري',
            r'كسر ضغط': 'كسر انضغاطي',
            r'التهاب مفاصل': 'التهاب المفاصل',
            r'ورم خبيث': 'ورم خبيث (سرطان)',
            r'ورم حميد': 'ورم حميد',

            # ---- English bone tumor terms / مصطلحات أورام العظام ----
            r'\bHkstovy\b': 'History',
            r'\baPpslyai\b': 'Physical',
            r'\bgslwigeociis\b': 'Clinical',
            r'\bFibrous elyspasi\b': 'Fibrous Dysplasia',
            r'\bosfochndonwwe\b': 'Osteochondroma',
            r'\b5olifaty bons kysfe\b': 'Solitary Bone Cyst',
            r'\bAnuerysm bonccge kyste\b': 'Aneurysmal Bone Cyst',
            r'\bChenalroblasfa\b': 'Chondrosarcoma',
            r'\bFibro AeVans\b': 'Fibrosarcoma',
            r'\bchhovelnblasfana\b': 'Chondroblastoma',
            r'\benchendrona\b': 'Enchondroma',
            r'\bOsteob\(as}oa\b': 'Osteoblastoma',
            r'\bfogMActn.*GiGain1cellTuwor\b': 'Giant Cell Tumor',
            r'\bLnkeciioa\b': 'Infection',
            r'\bLefournel\b': 'Letournel',

            # ---- Common clinical terms / مصطلحات سريرية شائعة ----
            r'\bPatienf\b': 'Patient',
            r'\bDaignosis\b': 'Diagnosis',
            r'\bTreafment\b': 'Treatment',
            r'\bFolow[ -]?up\b': 'Follow-up',
            r'\bAdmisison\b': 'Admission',
            r'\bDischarege\b': 'Discharge',
            r'\bRadiograh\b': 'Radiograph',
            r'\bX[ -]?ray\b': 'X-Ray',
            r'\bMRI\b': 'MRI',
            r'\bCT[ -]?sacn\b': 'CT Scan',
            r'\bBlod\b': 'Blood',
            r'\bUirne\b': 'Urine',

            # ---- Numeric patterns / أنماط رقمية ----
            r'\by\.?o\.?\s+(\d+)': r'year-old \1',
        }

    def load_custom_dictionary(self, dict_path: str):
        """
        Load custom dictionary from JSON file.
        تحميل قاموس مخصص من ملف JSON.

        Args:
            dict_path: Path to JSON file with pattern-replacement pairs
                       مسار ملف JSON يحتوي أزواج نمط-استبدال

        Expected format / التنسيق المتوقع:
            {"pattern1": "replacement1", "pattern2": "replacement2", ...}
        """
        path = Path(dict_path)
        if not path.exists():
            print(f"[تحذير] Dictionary file not found: {dict_path}")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                custom = json.load(f)

            if isinstance(custom, dict):
                self.medical_dict.update(custom)
                print(f"[معلومات] Loaded {len(custom)} custom dictionary entries "
                      f"from {dict_path}")
            else:
                print(f"[خطأ] Invalid dictionary format in {dict_path}. "
                      f"Expected JSON object/dict.")

        except json.JSONDecodeError as e:
            print(f"[خطأ] Failed to parse dictionary JSON: {e}")

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy.
        معالجة الصورة مسبقاً لتحسين دقة OCR.

        Pipeline:
        1. Convert BGR to grayscale if needed / تحويل إلى تدرج رمادي
        2. CLAHE contrast enhancement / تحسين التباين بـ CLAHE
        3. (Optional) Adaptive binarization / تثنيت تكيفي

        Args:
            image: Input image (BGR or grayscale) / صورة مدخلة

        Returns:
            Enhanced grayscale image / صورة رمادية محسنة
        """
        if image is None:
            raise ValueError("Input image is None / الصورة المدخلة فارغة")

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        return enhanced

    def correct_medical_text(self, text: str) -> str:
        """
        Apply medical dictionary corrections to OCR output text.
        تطبيق تصحيحات القاموس الطبي على نص OCR الناتج.

        Uses regex patterns for flexible matching of common OCR errors.
        يستخدم أنماط regex لمطابقة مرنة لأخطاء OCR الشائعة.

        Args:
            text: Raw OCR output text / نص OCR الخام

        Returns:
            Corrected text / نص مصحح
        """
        for pattern, replacement in self.medical_dict.items():
            try:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            except re.error as e:
                print(f"[تحذير] Regex error for pattern '{pattern}': {e}")

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def group_into_lines(self, results: list,
                         y_threshold: int = 10) -> List[list]:
        """
        Group OCR bounding box results into text lines based on Y position.
        تجميع نتائج OCR إلى أسطر نصية بناءً على الموضع Y.

        Args:
            results: List of (bbox, text, confidence) from EasyOCR
                     قائمة من (bounding_box, نص, ثقة)
            y_threshold: Maximum vertical distance to group words into same line
                         المسافة العمودية القصوى لتجميع الكلمات في نفس السطر

        Returns:
            List of line groups, each containing (bbox, text, confidence) items
            قائمة مجموعات الأسطر
        """
        if not results:
            return []

        # Sort by Y position (top to bottom)
        results_sorted = sorted(results, key=lambda x: x[0][0][1])

        lines = []
        current_line = [results_sorted[0]]
        current_y = results_sorted[0][0][0][1]

        for i in range(1, len(results_sorted)):
            box, text, conf = results_sorted[i]
            y_center = (box[0][1] + box[3][1]) / 2.0

            if abs(y_center - current_y) <= y_threshold:
                current_line.append(results_sorted[i])
            else:
                # Sort words in line left-to-right (for LTR) or right-to-left
                current_line.sort(key=lambda k: k[0][0][0])
                lines.append(current_line)
                current_line = [results_sorted[i]]
                current_y = y_center

        # Don't forget the last line
        current_line.sort(key=lambda k: k[0][0][0])
        lines.append(current_line)

        return lines

    def process_image(self, image: np.ndarray,
                      min_confidence: float = 0.0) -> str:
        """
        Perform full OCR pipeline on a single image.
        إجراء خط أنبوب OCR كامل على صورة واحدة.

        Pipeline:
        1. Preprocess image / معالجة الصورة مسبقاً
        2. Run EasyOCR detection / تشغيل كشف EasyOCR
        3. Group results into lines / تجميع النتائج في أسطر
        4. Apply medical dictionary corrections / تطبيق تصحيحات القاموس
        5. Format output with section headers / تنسيق المخرجات مع عناوين الأقسام

        Args:
            image: Input image (BGR or grayscale) / صورة مدخلة
            min_confidence: Minimum confidence to include result (default: 0)
                            الحد الأدنى للثقة لتضمين النتيجة

        Returns:
            Formatted OCR text with medical corrections
            نص OCR منسق مع تصحيحات طبية
        """
        if image is None:
            return ""

        processed = self.preprocess_image(image)
        raw_results = self.reader.readtext(processed, detail=1, paragraph=False)

        # Filter by confidence threshold
        filtered = [
            (box, text, conf) for box, text, conf in raw_results
            if conf >= min_confidence
        ]

        lines = self.group_into_lines(filtered)
        output = []

        # Section header patterns / أنماط عناوين الأقسام
        section_pattern = re.compile(
            r'\b(History|Physical|Diagnosis|Treatment|Plan|Notes|'
            r'Impression|Recommendation|Follow-up)\b',
            re.IGNORECASE,
        )

        for line_items in lines:
            line_texts = []
            for box, text, conf in line_items:
                corrected = self.correct_medical_text(text)
                line_texts.append(corrected)

            line_str = " ".join(line_texts)

            if not line_str.strip():
                continue

            # Highlight section headers
            if section_pattern.search(line_str):
                output.append(f"\n### {line_str}\n")
            else:
                output.append(line_str)

        return "\n".join(output)

    def process_pdf(self, pdf_path: str,
                    output_path: str = "output_notes.md",
                    min_confidence: float = 0.0) -> str:
        """
        Process PDF file through OCR pipeline.
        معالجة ملف PDF عبر خط أنبوب OCR.

        For each page:
        - First tries to extract embedded text (for digital PDFs)
        - If text is too short, renders page as image and runs OCR
        - Applies medical dictionary corrections

        لكل صفحة:
        - يحاول أولاً استخراج النص المضمّن (لملفات PDF الرقمية)
        - إذا كان النص قصيراً، يعرض الصفحة كصورة ويشغل OCR
        - يطبق تصحيحات القاموس الطبي

        Args:
            pdf_path: Path to PDF file / مسار ملف PDF
            output_path: Path to output Markdown file / مسار ملف Markdown الناتج
            min_confidence: Minimum confidence threshold / حد أدنى للثقة

        Returns:
            Path to the saved output file / مسار ملف الإخراج المحفوظ
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PyMuPDF (fitz) required for PDF. Install: pip install PyMuPDF\n"
                "PyMuPDF مطلوب لـ PDF. ثبته: pip install PyMuPDF"
            )

        doc = fitz.open(str(pdf_path))
        full_content = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Try extracting embedded text first
            raw_text = page.get_text("text")

            # If embedded text is too short, use OCR on rendered image
            if len(raw_text.strip()) < 50:
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                img = np.frombuffer(pix.tobytes(), np.uint8).reshape(
                    pix.h, pix.w, 4
                )
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                raw_text = self.process_image(img, min_confidence=min_confidence)
            else:
                # Still apply dictionary corrections to digital text
                raw_text = self.correct_medical_text(raw_text)

            full_content.append(
                f"<!-- Page {page_num + 1} / صفحة {page_num + 1} -->\n"
                f"{raw_text}\n---\n"
            )
            print(f"  Processed page {page_num + 1}/{len(doc)}")

        doc.close()

        # Write output
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(full_content), encoding="utf-8")

        print(f"[نتيجة] Saved: {output_path} ({len(full_content)} pages)")
        return str(output_path)

    def process_directory(self, dir_path: str,
                          output_dir: str = "output_dir",
                          min_confidence: float = 0.0,
                          extensions: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Process all image/PDF files in a directory.
        معالجة جميع ملفات الصور وPDF في مجلد.

        Args:
            dir_path: Input directory path / مسار مجلد الإدخال
            output_dir: Output directory for results / مجلد الإخراج للنتائج
            min_confidence: Minimum confidence threshold / حد أدنى للثقة
            extensions: File extensions to process (default: jpg, png, pdf)
                        امتدادات الملفات للمعالجة

        Returns:
            Dict mapping input filename to output filepath
            قاموس يربط اسم ملف الإدخال بمسار ملف الإخراج
        """
        dir_path = Path(dir_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if extensions is None:
            extensions = ['jpg', 'jpeg', 'png', 'tif', 'tiff', 'bmp', 'pdf']

        ext_set = {e.lower().lstrip('.') for e in extensions}
        results = {}

        files = sorted(dir_path.iterdir())
        print(f"[معلومات] Found {len(files)} files in {dir_path}")

        for fpath in files:
            if not fpath.is_file():
                continue
            ext = fpath.suffix.lstrip('.').lower()
            if ext not in ext_set:
                continue

            print(f"\n[معالجة] Processing: {fpath.name}")

            try:
                if ext == 'pdf':
                    out_name = fpath.stem + '.md'
                    out_path = self.process_pdf(
                        str(fpath),
                        str(output_dir / out_name),
                        min_confidence=min_confidence,
                    )
                    results[fpath.name] = out_path
                else:
                    img = cv2.imread(str(fpath))
                    if img is None:
                        print(f"  [تحذير] Cannot read image: {fpath.name}")
                        continue

                    text = self.process_image(img, min_confidence=min_confidence)
                    out_name = fpath.stem + '.txt'
                    out_path = output_dir / out_name
                    out_path.write_text(text, encoding='utf-8')
                    results[fpath.name] = str(out_path)
                    print(f"  [تم] Saved: {out_path}")

            except Exception as e:
                print(f"  [خطأ] Error processing {fpath.name}: {e}")

        print(f"\n[نتيجة] Processed {len(results)}/{len(files)} files")
        return results


def parse_args():
    """Parse command line arguments / تحليل معاملات سطر الأوامر"""
    parser = argparse.ArgumentParser(
        description='Offline Medical Handwriting OCR v11.0\n'
                    'التعرف على الكتابة الطبية يدوياً - إصدار غير متصل',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples / أمثلة:
  # Single image / صورة واحدة
  python offline_medical_ocr.py --image scan.jpg

  # PDF file / ملف PDF
  python offline_medical_ocr.py --pdf report.pdf --output results.md

  # Directory / مجلد
  python offline_medical_ocr.py --dir ./scans/ --output-dir ./results/

  # With GPU and custom dictionary / مع GPU وقاموس مخصص
  python offline_medical_ocr.py --image scan.jpg --gpu --dict medical_terms.json

  # With confidence threshold / مع حد أدنى للثقة
  python offline_medical_ocr.py --pdf report.pdf --min-conf 0.5
        """
    )

    # Input source (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '-i', '--image',
        type=str, default=None,
        help='Path to a single image file / مسار صورة واحدة'
    )
    source_group.add_argument(
        '-p', '--pdf',
        type=str, default=None,
        help='Path to a PDF file / مسار ملف PDF'
    )
    source_group.add_argument(
        '-d', '--dir',
        type=str, default=None,
        help='Path to directory of images/PDFs / مسار مجلد صور وملفات PDF'
    )

    # Output options
    parser.add_argument(
        '-o', '--output',
        type=str, default="output_notes.md",
        help='Output file path (default: output_notes.md)\n'
             'مسار ملف الإخراج'
    )
    parser.add_argument(
        '--output-dir',
        type=str, default="output_dir",
        help='Output directory for batch processing (default: output_dir)\n'
             'مجلد الإخراج للمعالجة الدفعية'
    )

    # Processing options
    parser.add_argument(
        '--gpu',
        action='store_true',
        help='Enable GPU acceleration / تفعيل تسريع GPU'
    )
    parser.add_argument(
        '--dict',
        type=str, default=None,
        help='Path to custom medical dictionary JSON / مسار قاموس طبي مخصص'
    )
    parser.add_argument(
        '--min-conf',
        type=float, default=0.0,
        help='Minimum confidence threshold 0.0-1.0 (default: 0.0)\n'
             'حد أدنى للثقة بين 0.0 و 1.0'
    )
    parser.add_argument(
        '--extensions',
        type=str, nargs='+',
        default=['jpg', 'jpeg', 'png', 'pdf'],
        help='File extensions to process in directory mode\n'
             'امتدادات الملفات للمعالجة في وضع المجلد'
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("=" * 60)
    print("  Offline Medical Handwriting OCR v11.0")
    print("  التعرف على الكتابة الطبية - إصدار غير متصل")
    print("=" * 60)

    ocr = OfflineMedicalOCR(
        use_gpu=args.gpu,
        custom_dict_path=args.dict,
    )

    if args.image:
        print(f"\n[إدخال] Image: {args.image}")
        img = cv2.imread(args.image)
        if img is None:
            print(f"[خطأ] Cannot read image: {args.image}")
        else:
            text = ocr.process_image(img, min_confidence=args.min_conf)
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text, encoding='utf-8')
            print(f"\n{text}")
            print(f"\n[نتيجة] Saved to: {output_path}")

    elif args.pdf:
        print(f"\n[إدخال] PDF: {args.pdf}")
        ocr.process_pdf(args.pdf, args.output, min_confidence=args.min_conf)

    elif args.dir:
        print(f"\n[إدخال] Directory: {args.dir}")
        results = ocr.process_directory(
            args.dir, args.output_dir,
            min_confidence=args.min_conf,
            extensions=args.extensions,
        )
        for fname, fpath in results.items():
            print(f"  {fname} -> {fpath}")
