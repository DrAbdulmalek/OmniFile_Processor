# ══════════════════════════════════════════════════════════╗
#  Batch Medical OCR Engine - Multi-file Processing
#  PDF -> Images -> Preprocess -> Segment -> OCR -> Extract Refs
# ══════════════════════════════════════════════════════════╝

import re
import cv2
import numpy as np
import torch
from pathlib import Path
from PIL import Image
from typing import Dict, List, Optional, Tuple

# Lazy imports
_fitz = None
_easyocr_module = None


class BatchMedicalOCR:
    """
    محرك معالجة دفعات طبية - يدعم صور متعددة وملفات PDF.

    القدرات:
    - تحويل PDF لصور عالية الدقة (PyMuPDF)
    - معالجة مسبقة (إزالة الشطب + CLAHE)
    - تقسيم ذكي للأسطر
    - OCR عبر TrOCR مع حماية المصطلحات الطبية
    - استخراج المراجع والأرقام الطرفية
    - حفظ نتائج خام للمراجعة اللاحقة
    """

    def __init__(self, model_path: Optional[str] = None):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        src = model_path if model_path and Path(model_path).exists() else "microsoft/trocr-base-handwritten"
        self.model_path = src
        self._load_model(src)
        self._load_easyocr()

        # Medical lexicon for term protection
        self.med_lexicon = [
            "Flucloxacillin", "Cefotaxime", "Benzylpenicillin", "Haemophilus",
            "Influenzae", "Fucidic", "Cefuroxime", "Teicoplanin", "Vancomycin",
            "Ciprofloxacin", "MRSA", "HIV", "trough", "peak", "Gentamicin",
            "Chloramphenicol", "Polyptides", "SPACER", "Garre", "Amoxicillin",
            "Azithromycin", "Metformin", "Amlodipine", "Losartan", "Atorvastatin",
            "Omeprazole", "Ibuprofen", "Paracetamol", "Aspirin", "Prednisone",
            "Alprazolam", "Lorazepam", "Diazepam", "Cephalexin", "Doxycycline",
            "Fluconazole", "Tramadol", "Gabapentin",
        ]

    # ────────────────────────────────────────────────────────
    # Model Loading
    # ────────────────────────────────────────────────────────

    def _load_model(self, model_src: str):
        """تحميل نموذج TrOCR"""
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        self.processor = TrOCRProcessor.from_pretrained(model_src)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_src).to(self.device)
        self.model.eval()

    def _load_easyocr(self):
        """تحميل EasyOCR"""
        import easyocr
        self.easy_reader = easyocr.Reader(
            ['ar', 'en'],
            gpu=(self.device == 'cuda'),
            verbose=False,
        )

    # ────────────────────────────────────────────────────────
    # PDF to Images
    # ────────────────────────────────────────────────────────

    def pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[Tuple[str, np.ndarray]]:
        """
        تحويل PDF لصور عالية الدقة.

        Args:
            pdf_path: Path to PDF file.
            dpi: Resolution (default 300).

        Returns:
            List of (page_name, grayscale_image) tuples.
        """
        import fitz
        doc = fitz.open(str(pdf_path))
        imgs = []
        for i, page in enumerate(doc):
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes()
            img = np.frombuffer(img_bytes, np.uint8).reshape(pix.h, pix.w, 4)
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
            page_name = f"{Path(pdf_path).stem}_P{i + 1}"
            imgs.append((page_name, gray))
        doc.close()
        return imgs

    # ────────────────────────────────────────────────────────
    # Preprocessing (Scribble Removal + CLAHE)
    # ────────────────────────────────────────────────────────

    def preprocess(self, gray: np.ndarray) -> np.ndarray:
        """
        إزالة الشطب + تحسين التباين.

        يزيل الكتل الصغيرة الكثيفة (الشطب) مع الحفاظ على النص.
        """
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        mask = np.ones_like(gray) * 255

        for i in range(1, num_labels):
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            area = stats[i, cv2.CC_STAT_AREA]
            fill_ratio = area / max(1, w * h)

            # Hide dense small blocks (scribbles)
            if 100 < area < 5000 and fill_ratio > 0.6:
                cv2.rectangle(mask, (x, y), (x + w, y + h), 0, -1)

        cleaned = cv2.bitwise_and(gray, gray, mask=mask)
        return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(cleaned)

    # ────────────────────────────────────────────────────────
    # Line Segmentation
    # ────────────────────────────────────────────────────────

    def segment_lines(self, img: np.ndarray, min_h: int = 10) -> List[Tuple[int, int]]:
        """
        تقسيم الصورة إلى أسطر عبر تحليل الإسقاط الرأسي.

        Returns:
            List of (y_start, y_end) tuples.
        """
        _, th = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        proj = np.sum(th, axis=1)
        lines = []
        in_line, start = False, 0
        thr = np.percentile(proj[proj > 0], 15) if np.any(proj > 0) else 30

        for y in range(len(proj)):
            if proj[y] > thr and not in_line:
                in_line, start = True, y
            elif proj[y] <= thr and in_line:
                in_line = False
                if y - start >= min_h:
                    lines.append((start, y))

        if in_line and len(proj) - start >= min_h:
            lines.append((start, len(proj)))

        return lines

    # ────────────────────────────────────────────────────────
    # OCR with Medical Term Protection
    # ────────────────────────────────────────────────────────

    def ocr_line(self, crop: np.ndarray) -> str:
        """
        التعرف على سطر واحد مع حماية المصطلحات الطبية.

        Args:
            crop: Line crop image (grayscale).

        Returns:
            Recognized text string.
        """
        if len(crop.shape) == 2:
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_GRAY2RGB)
        else:
            crop_rgb = crop

        px = self.processor(
            images=Image.fromarray(crop_rgb),
            return_tensors='pt',
        ).to(self.device).pixel_values

        with torch.no_grad():
            out = self.model.generate(
                px,
                max_length=60,
                num_beams=5,
                early_stopping=True,
            )

        txt = self.processor.batch_decode(out, skip_special_tokens=True)[0].strip()

        # Protect medical terms from being merged/split
        for term in self.med_lexicon:
            txt = re.sub(
                rf'([^\s]){re.escape(term)}',
                rf'\1 {term}',
                txt,
                flags=re.IGNORECASE,
            )
            txt = re.sub(
                rf'{re.escape(term)}([^\s])',
                rf'{term} \1',
                txt,
                flags=re.IGNORECASE,
            )

        return re.sub(r'\s+', ' ', txt).strip()

    # ────────────────────────────────────────────────────────
    # Reference Extraction
    # ────────────────────────────────────────────────────────

    @staticmethod
    def extract_refs(text: str) -> Tuple[str, List[str]]:
        """
        عزل المراجع والأرقام الطرفية.

        Supports: #, *, arrows, Arabic/Latin digits.
        """
        patterns = [
            r'^[\*\#\-\u2192\u25CF]?\s*([\u0660-\u0669\u06F0-\u06F9\d]{2,5})\s*[\.\-\:\)]?',
            r'[\*\#\-\u2192\u25CF]?\s*([\u0660-\u0669\u06F0-\u06F9\d]{2,5})\s*[\.\-\:\)]?$',
        ]

        refs = []
        clean = text
        for p in patterns:
            matches = re.findall(p, clean)
            if matches:
                refs.extend(matches)
                clean = re.sub(p, '', clean)

        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean, refs

    # ────────────────────────────────────────────────────────
    # Main: Process Folder (Batch)
    # ────────────────────────────────────────────────────────

    def process_folder(
        self,
        input_dir: str,
        output_dir: str,
    ) -> List[Dict]:
        """
        معالجة مجلد كامل من الصور وملفات PDF.

        Args:
            input_dir: Directory containing images and PDFs.
            output_dir: Directory for output JSON.

        Returns:
            List of page results, each with 'page' and 'lines'.
        """
        input_dir = Path(input_dir)
        if not input_dir.exists():
            raise FileNotFoundError(str(input_dir))

        # Collect all files
        files = (
            list(input_dir.glob('*.jpg'))
            + list(input_dir.glob('*.png'))
            + list(input_dir.glob('*.jpeg'))
            + list(input_dir.glob('*.bmp'))
            + list(input_dir.glob('*.tiff'))
            + list(input_dir.glob('*.pdf'))
        )

        if not files:
            raise ValueError("No image or PDF files found in the input directory.")

        results = []

        for f in sorted(files):
            if f.suffix.lower() == '.pdf':
                pages = self.pdf_to_images(str(f))
            else:
                gray = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
                pages = [(f.stem, gray)] if gray is not None else []

            for name, gray in pages:
                if gray is None:
                    continue

                clean = self.preprocess(gray)
                lines = self.segment_lines(clean)
                page_lines = []

                for i, (y1, y2) in enumerate(lines):
                    crop = clean[y1:y2]
                    raw = self.ocr_line(crop)
                    main_text, refs = self.extract_refs(raw)

                    if main_text:
                        page_lines.append({
                            'idx': i,
                            'text': main_text,
                            'refs': refs,
                            'raw': raw,
                        })

                results.append({'page': name, 'lines': page_lines})

        # Save raw output for review
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        out_file = output_path / 'raw_output.json'
        import json
        with open(out_file, 'w', encoding='utf-8') as fp:
            json.dump(results, fp, ensure_ascii=False, indent=2)

        return results

    # ────────────────────────────────────────────────────────
    # Process Single File
    # ────────────────────────────────────────────────────────

    def process_single_file(self, file_path: str) -> List[Dict]:
        """
        معالجة ملف واحد (صورة أو PDF).

        Returns:
            List of page results.
        """
        file_path = Path(file_path)
        if file_path.suffix.lower() == '.pdf':
            pages = self.pdf_to_images(str(file_path))
        else:
            gray = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            pages = [(file_path.stem, gray)] if gray is not None else []

        results = []
        for name, gray in pages:
            if gray is None:
                continue
            clean = self.preprocess(gray)
            lines = self.segment_lines(clean)
            page_lines = []
            for i, (y1, y2) in enumerate(lines):
                crop = clean[y1:y2]
                raw = self.ocr_line(crop)
                main_text, refs = self.extract_refs(raw)
                if main_text:
                    page_lines.append({
                        'idx': i,
                        'text': main_text,
                        'refs': refs,
                        'raw': raw,
                    })
            results.append({'page': name, 'lines': page_lines})

        return results
