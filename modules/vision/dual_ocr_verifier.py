# ══════════════════════════════════════════════════════════╗
#  Dual-OCR Verification Engine - Medical Safety Layer v5.0
#  TrOCR + EasyOCR | Intelligent Comparison | Critical Mismatch Detection
# ══════════════════════════════════════════════════════════╝

import re
import json
import torch
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

# Lazy imports to avoid circular dependency
_trocr_processor = None
_trocr_model = None
_easyocr_reader = None


class DualOCRVerifier:
    """
    محرك التحقق المزدوج - يجمع بين TrOCR (النموذج المدرب) و EasyOCR (المرجع الخارجي)
    لمقارنة النتائج وكشف التناقضات الحرجة في المحتوى الطبي.
    """

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        global _trocr_processor, _trocr_model, _easyocr_reader

        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_path = model_path
        self.model_version = 'unknown'

        # ─── 1. Load TrOCR Model (Trained or Fallback) ───
        if model_path and Path(model_path).exists():
            print(f"📥 Loading trained model from: {model_path}")
            self._load_trocr(model_path)
            self.model_version = Path(model_path).name
        else:
            fallback = "microsoft/trocr-base-handwritten"
            print(f"⚠️ No trained model found. Using {fallback} as fallback")
            self._load_trocr(fallback)
            self.model_version = fallback

        # ─── 2. EasyOCR as Independent Reference ───
        if _easyocr_reader is None:
            print("📥 Loading EasyOCR for comparison...")
            _easyocr_reader = self._get_easyocr()
        self.easyocr_reader = _easyocr_reader

        # ─── 3. Critical Content Patterns (Medical Safety) ───
        self.critical_patterns = {
            'dosage': r'\b\d+(\.\d+)?\s*(mg|ml|kg|mcg|g|units?|iu)\b',
            'frequency': r'\b(BID|TID|QID|QD|QOD|PRN|STAT)\b',
            'route': r'\b(IV|IM|PO|SC|SL|PR|PV)\b',
            'drug_name': r'\b[A-Z][a-z]+(cillin|mycin|floxacin|zolam|pril|sartan|statin)\b',
            'lab_value': r'\b\d+(\.\d+)?\s*(mmol/L|mg/dL|g/dL|%)\b',
            'critical_terms': r'\b(CAFFEY|AIDS|HIV|MRI|CT|X-ray|ESR|CRP)\b',
        }

        # ─── 4. Load Protected Terms ───
        self.protected_terms: List[str] = []
        terms_paths = [
            Path(__file__).parent.parent.parent / 'data' / 'audit_logs' / 'protected_terms.json',
        ]
        for tp in terms_paths:
            if tp.exists():
                self.protected_terms = json.loads(tp.read_text(encoding='utf-8'))
                break

        # ─── 5. Audit Logger (optional) ───
        self.audit_logger = None

    # ────────────────────────────────────────────────────────
    # Model Loading (lazy helpers)
    # ────────────────────────────────────────────────────────

    def _load_trocr(self, model_name_or_path: str):
        global _trocr_processor, _trocr_model
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        if _trocr_processor is None:
            _trocr_processor = TrOCRProcessor.from_pretrained(model_name_or_path)
            _trocr_model = VisionEncoderDecoderModel.from_pretrained(model_name_or_path).to(self.device)
            _trocr_model.eval()

        self.trocr_processor = _trocr_processor
        self.trocr_model = _trocr_model

    def _get_easyocr(self):
        import easyocr
        return easyocr.Reader(['ar', 'en'], gpu=(self.device == 'cuda'), verbose=False)

    # ────────────────────────────────────────────────────────
    # Critical Content Detection
    # ────────────────────────────────────────────────────────

    def detect_critical_content(self, text: str) -> List[Dict]:
        """
        يكشف إذا كان النص يحتوي على معلومات طبية حساسة.
        Returns list of dicts with 'category' and 'matches'.
        """
        found = []
        for category, pattern in self.critical_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found.append({'category': category, 'matches': matches})
        return found

    # ────────────────────────────────────────────────────────
    # Image Preprocessing
    # ────────────────────────────────────────────────────────

    def preprocess_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """تجهيز الصورة للمحركات - تحسين التباين عبر CLAHE"""
        if len(img.shape) == 2:
            gray = img
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return enhanced

    # ────────────────────────────────────────────────────────
    # OCR Prediction (individual engines)
    # ────────────────────────────────────────────────────────

    def trocr_predict(self, img: np.ndarray) -> str:
        """التعرف عبر TrOCR"""
        img_pil = Image.fromarray(img).convert('RGB')
        px = self.trocr_processor(images=img_pil, return_tensors='pt').to(self.device).pixel_values

        with torch.no_grad():
            out = self.trocr_model.generate(
                px,
                max_length=80,
                num_beams=6,
                early_stopping=True,
                no_repeat_ngram_size=2,
            )

        text = self.trocr_processor.batch_decode(out, skip_special_tokens=True)[0].strip()
        return text

    def easyocr_predict(self, img: np.ndarray) -> str:
        """التعرف عبر EasyOCR"""
        results = self.easyocr_reader.readtext(img, detail=0, paragraph=False)
        return " ".join(results).strip()

    # ────────────────────────────────────────────────────────
    # Similarity Calculation
    # ────────────────────────────────────────────────────────

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """حساب نسبة التشابه بين النصين (SequenceMatcher)"""
        t1 = re.sub(r'\s+', ' ', text1.lower())
        t2 = re.sub(r'\s+', ' ', text2.lower())
        return SequenceMatcher(None, t1, t2).ratio()

    # ────────────────────────────────────────────────────────
    # Difference Highlighting
    # ────────────────────────────────────────────────────────

    @staticmethod
    def highlight_differences(text1: str, text2: str) -> str:
        """
        تمييز الاختلافات بين النصين للعرض.
        Example: "abc" vs "adc" → "ab【c→d】"
        """
        diff = SequenceMatcher(None, text1, text2)
        output = []
        for tag, i1, i2, j1, j2 in diff.get_opcodes():
            if tag == 'equal':
                output.append(text1[i1:i2])
            elif tag == 'replace':
                output.append(f"\u3010{text1[i1:i2]}\u2192{text2[j1:j2]}\u3011")
            elif tag == 'delete':
                output.append(f"\u3010-{text1[i1:i2]}-\u3011")
            elif tag == 'insert':
                output.append(f"\u3010+{text2[j1:j2]}+\u3011")
        return "".join(output)

    # ────────────────────────────────────────────────────────
    # Main Verification Logic
    # ────────────────────────────────────────────────────────

    def verify_line(self, img: np.ndarray, line_idx: int = 0) -> Dict:
        """
        التحقق المزدوج لسطر واحد.
        Returns dict with: trocr_text, easyocr_text, similarity,
        recommendation, confidence, final_text, critical_warnings, etc.
        """
        enhanced = self.preprocess_for_ocr(img)

        # Run both engines independently
        trocr_text = self.trocr_predict(enhanced)
        easyocr_text = self.easyocr_predict(enhanced)

        # Calculate similarity
        similarity = self.calculate_similarity(trocr_text, easyocr_text)

        # Detect critical content in both results
        critical_trocr = self.detect_critical_content(trocr_text)
        critical_easy = self.detect_critical_content(easyocr_text)

        # ─── Detect Critical Mismatches ───
        has_critical_mismatch = False
        critical_warnings: List[str] = []

        if critical_trocr or critical_easy:
            # If one detected critical content and the other didn't
            if len(critical_trocr) != len(critical_easy):
                has_critical_mismatch = True
                critical_warnings.append("⚠️ Difference in critical content detection")

            # Compare numeric values in dosages and lab values
            for cat in ['dosage', 'lab_value']:
                trocr_vals = re.findall(self.critical_patterns[cat], trocr_text, re.IGNORECASE)
                easy_vals = re.findall(self.critical_patterns[cat], easyocr_text, re.IGNORECASE)
                if trocr_vals != easy_vals and (trocr_vals or easy_vals):
                    has_critical_mismatch = True
                    critical_warnings.append(
                        f"⚠️ Contradiction in {cat}: TrOCR={trocr_vals} vs EasyOCR={easy_vals}"
                    )

        # ─── Recommendation Logic ───
        if similarity >= 0.85 and not has_critical_mismatch:
            recommendation = "AUTO_ACCEPT"
            confidence = "HIGH"
            final_text = trocr_text  # Trust trained TrOCR
        elif similarity < 0.60 or has_critical_mismatch:
            recommendation = "MANUAL_REVIEW_REQUIRED"
            confidence = "LOW"
            final_text = None  # Wait for human review
        else:
            recommendation = "QUICK_CHECK"
            confidence = "MEDIUM"
            final_text = trocr_text

        return {
            'line_idx': line_idx,
            'trocr_text': trocr_text,
            'easyocr_text': easyocr_text,
            'similarity': similarity,
            'critical_content': critical_trocr or critical_easy,
            'has_critical_mismatch': has_critical_mismatch,
            'critical_warnings': critical_warnings,
            'recommendation': recommendation,
            'confidence': confidence,
            'final_text': final_text,
            'image': img,
        }

    # ────────────────────────────────────────────────────────
    # Batch Processing Helpers
    # ────────────────────────────────────────────────────────

    def extract_lines(self, img: np.ndarray,
                      min_height: int = 8,
                      percentile_threshold: float = 20) -> List[Tuple[int, int]]:
        """
        تقسيم الصفحة إلى أسطر عبر تحليل الإسقاط الرأسي.
        Returns list of (y_start, y_end) tuples.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        proj = np.sum(th, axis=1)

        lines = []
        in_line, start = False, 0
        threshold = np.percentile(proj[proj > 0], percentile_threshold) if np.any(proj > 0) else 50

        for y in range(len(proj)):
            if proj[y] > threshold and not in_line:
                in_line, start = True, y
            elif proj[y] <= threshold and in_line:
                in_line = False
                if y - start > min_height:
                    lines.append((start, y))

        if in_line:
            lines.append((start, len(proj)))

        return lines

    def verify_page(self, img: np.ndarray) -> List[Dict]:
        """التحقق المزدوج لصفحة كاملة - يُرجع نتائج كل الأسطر."""
        lines = self.extract_lines(img)
        results = []
        for i, (y1, y2) in enumerate(lines):
            line_img = img[y1:y2]
            result = self.verify_line(line_img, i)
            results.append(result)
        return results
