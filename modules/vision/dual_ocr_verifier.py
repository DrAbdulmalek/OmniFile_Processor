# ══════════════════════════════════════════════════════════╗
#  Dual-OCR Verification Engine - Medical Safety Layer v5.1
#  TrOCR + EasyOCR | Intelligent Comparison | Critical Mismatch Detection
#  v5.1: Added preprocess_v3.1, segment_v3.1, extract_references_v3.1
#        Handles: rotation, dense lines, strike-through, complex references
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

    v5.1 Updates:
    - preprocess_for_ocr_v3: Handles header rotation, notebook lines, smart component filtering
    - segment_lines_v3: Dense packing support, strike-through detection, Gaussian smoothing
    - extract_references_v3: Handles #, *, arrows, Arabic numerals, parentheses
    """

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        global _trocr_processor, _trocr_model, _easyocr_reader

        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_path = model_path
        self.model_version = 'unknown'

        # ─── 1. Load TrOCR Model (Trained or Fallback) ───
        if model_path and Path(model_path).exists():
            print(f"Loading trained model from: {model_path}")
            self._load_trocr(model_path)
            self.model_version = Path(model_path).name
        else:
            fallback = "microsoft/trocr-base-handwritten"
            print(f"No trained model found. Using {fallback} as fallback")
            self._load_trocr(fallback)
            self.model_version = fallback

        # ─── 2. EasyOCR as Independent Reference ───
        if _easyocr_reader is None:
            print("Loading EasyOCR for comparison...")
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
    # Image Preprocessing (v1 - Original)
    # ────────────────────────────────────────────────────────

    def preprocess_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """تجهيز الصورة للمحركات - تحسين التباين عبر CLAHE (الإصدار الأصلي)"""
        if len(img.shape) == 2:
            gray = img
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return enhanced

    # ────────────────────────────────────────────────────────
    # Image Preprocessing v3.1 (Handles Rotation, Density, Strike-through)
    # ────────────────────────────────────────────────────────

    def preprocess_for_ocr_v3(self, img: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int]]:
        """
        معالجة محسّنة v3.1: تصحيح الميل/القلب، فلترة الرسوم، تحسين التباين.

        يتعامل مع 4 تحديات بصرية:
        1. نص مقلوب/رأسي في الهيدر
        2. كثافة سطر عالية + تشابك
        3. خطوط دفتر أفقية/عمودية باهتة
        4. رموز وأسهم تُلتقط كحروف

        Args:
            img: الصورة الأصلية (BGR أو grayscale)

        Returns:
            Tuple of (enhanced_image, (margin_x, margin_y))
        """
        if len(img.shape) == 2:
            gray = img.copy()
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape

        # 1. Detect and fix inverted header text (top 15% of page)
        header_region = gray[0:int(h * 0.15), :]
        _, bin_h = cv2.threshold(header_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(bin_h > 0))
        if len(coords) > 50:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            # If angle is close to 180 (upside-down text)
            if abs(angle) > 150:
                gray[0:int(h * 0.15), :] = cv2.rotate(header_region, cv2.ROTATE_180)

        # 2. Remove horizontal and vertical notebook lines
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        h_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, h_kernel, iterations=2)
        v_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, v_kernel, iterations=1)
        cleaned = cv2.subtract(cv2.subtract(gray, h_lines), v_lines)

        # 3. CLAHE enhancement (preserving diacritics and dots)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(10, 10))
        enhanced = clahe.apply(cleaned)
        _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 4. Smart filtering: keep text-like components, remove arrows/graphics/noise
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(thresh, connectivity=8)
        mask = np.zeros_like(thresh)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            cw = stats[i, cv2.CC_STAT_WIDTH]
            ch = stats[i, cv2.CC_STAT_HEIGHT]
            aspect = cw / max(1, ch)

            # Keep text-like components (reasonable area, logical aspect ratio)
            if 20 < area < 10000 and 0.1 < aspect < 8.0:
                mask[labels == i] = 255

        final = cv2.bitwise_and(enhanced, enhanced, mask=mask)
        return final, (int(w * 0.03), int(h * 0.06))

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
        Example: "abc" vs "adc" -> "ab[c->d]"
        """
        diff = SequenceMatcher(None, text1, text2)
        output = []
        for tag, i1, i2, j1, j2 in diff.get_opcodes():
            if tag == 'equal':
                output.append(text1[i1:i2])
            elif tag == 'replace':
                output.append(f"[{text1[i1:i2]}->{text2[j1:j2]}]")
            elif tag == 'delete':
                output.append(f"[-{text1[i1:i2]}-]")
            elif tag == 'insert':
                output.append(f"[+{text2[j1:j2]}+]")
        return "".join(output)

    # ────────────────────────────────────────────────────────
    # Reference Extraction v3.1
    # ────────────────────────────────────────────────────────

    @staticmethod
    def extract_references_v3(text: str) -> Tuple[str, List[str]]:
        """
        عزل المراجع والرموز الطرفية بدقة أعلى.

        يدعم: #, *, arrows, Arabic/Latin numerals, parentheses.
        Patterns: '# 224', '* 2188', '-> 300', '(15)', end-of-line and start-of-line.

        Args:
            text: Raw OCR text line.

        Returns:
            Tuple of (cleaned_text, list_of_references).
        """
        patterns = [
            # End of line: optional #,*,-> followed by Arabic/Latin digits
            r'[\*\#\-\u2192\u25CF]?\s*([\u0660-\u0669\u06F0-\u06F9\d]{2,5})\s*[\.\)\-\:]?$',
            # Start of line
            r'^[\*\#\-\u2192\u25CF]?\s*([\u0660-\u0669\u06F0-\u06F9\d]{2,5})\s*[\.\)\-\:]?',
            # Parenthesized: (123), (45)
            r'\(\s*([\u0660-\u0669\u06F0-\u06F9\d]{1,4})\s*\)',
        ]

        refs = []
        clean = text
        for p in patterns:
            matches = re.findall(p, clean)
            if matches:
                refs.extend(matches)
                clean = re.sub(p, '', clean)

        # Clean up extra whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean, refs

    # ────────────────────────────────────────────────────────
    # Main Verification Logic
    # ────────────────────────────────────────────────────────

    def verify_line(self, img: np.ndarray, line_idx: int = 0,
                    use_v3: bool = False) -> Dict:
        """
        التحقق المزدوج لسطر واحد.
        Returns dict with: trocr_text, easyocr_text, similarity,
        recommendation, confidence, final_text, critical_warnings, etc.

        Args:
            img: Line image (grayscale or BGR).
            line_idx: Index of the line on the page.
            use_v3: If True, uses v3.1 preprocessing (rotation, line removal, smart filter).
        """
        if use_v3:
            enhanced, _ = self.preprocess_for_ocr_v3(img)
        else:
            enhanced = self.preprocess_for_ocr(img)

        # Run both engines independently
        trocr_text = self.trocr_predict(enhanced)
        easyocr_text = self.easyocr_predict(enhanced)

        # Extract references from both results
        trocr_clean, trocr_refs = self.extract_references_v3(trocr_text)
        easyocr_clean, easyocr_refs = self.extract_references_v3(easyocr_text)

        # Use cleaned text for comparison (without reference noise)
        comparison_text_trocr = trocr_clean if trocr_refs else trocr_text
        comparison_text_easyocr = easyocr_clean if easyocr_refs else easyocr_text

        # Calculate similarity (on cleaned text)
        similarity = self.calculate_similarity(comparison_text_trocr, comparison_text_easyocr)

        # Detect critical content in both results (on raw text)
        critical_trocr = self.detect_critical_content(trocr_text)
        critical_easy = self.detect_critical_content(easyocr_text)

        # ─── Detect Critical Mismatches ───
        has_critical_mismatch = False
        critical_warnings: List[str] = []

        if critical_trocr or critical_easy:
            if len(critical_trocr) != len(critical_easy):
                has_critical_mismatch = True
                critical_warnings.append("Difference in critical content detection")

            for cat in ['dosage', 'lab_value']:
                trocr_vals = re.findall(self.critical_patterns[cat], trocr_text, re.IGNORECASE)
                easy_vals = re.findall(self.critical_patterns[cat], easyocr_text, re.IGNORECASE)
                if trocr_vals != easy_vals and (trocr_vals or easy_vals):
                    has_critical_mismatch = True
                    critical_warnings.append(
                        f"Contradiction in {cat}: TrOCR={trocr_vals} vs EasyOCR={easy_vals}"
                    )

        # ─── Recommendation Logic ───
        if similarity >= 0.85 and not has_critical_mismatch:
            recommendation = "AUTO_ACCEPT"
            confidence = "HIGH"
            final_text = trocr_clean  # Use cleaned text (without references)
        elif similarity < 0.60 or has_critical_mismatch:
            recommendation = "MANUAL_REVIEW_REQUIRED"
            confidence = "LOW"
            final_text = None
        else:
            recommendation = "QUICK_CHECK"
            confidence = "MEDIUM"
            final_text = trocr_clean

        return {
            'line_idx': line_idx,
            'trocr_text': trocr_text,
            'easyocr_text': easyocr_text,
            'trocr_clean': trocr_clean,
            'easyocr_clean': easyocr_clean,
            'trocr_refs': trocr_refs,
            'easyocr_refs': easyocr_refs,
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
    # Line Segmentation (v1 - Original)
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

    # ────────────────────────────────────────────────────────
    # Line Segmentation v3.1 (Dense Packing + Strike-through)
    # ────────────────────────────────────────────────────────

    def segment_lines_v3(self, img: np.ndarray) -> List[Dict]:
        """
        تقسيم محسّن للنصوص الكثيفة مع كشف المشطوب.

        يتعامل مع:
        - أسطر متقاربة جداً وحروف متداخلة
        - خطوط دفتر باهتة تسبب دمج خاطئ
        - أسطر مشطوبة بخط أفقي

        Args:
            img: الصورة (grayscale أو BGR).

        Returns:
            List of dicts, each with:
            - 'bbox': (y_start, y_end)
            - 'image': cropped line image
            - 'is_crossed': bool indicating strike-through detection
        """
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Connect broken letters within same line (important for dense connected script)
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
        th_connected = cv2.morphologyEx(th, cv2.MORPH_CLOSE, v_kernel)

        # Horizontal projection with Gaussian smoothing to avoid small jumps
        proj = np.sum(th_connected, axis=1)
        proj_smooth = cv2.GaussianBlur(proj.reshape(-1, 1), (1, 7), 0).flatten()

        lines = []
        in_line, start = False, 0

        # Dynamic threshold based on page density
        active_pixels = proj[proj > 0]
        dyn_thr = np.percentile(active_pixels, 25) if len(active_pixels) > 0 else 50

        for y in range(len(proj_smooth)):
            if proj_smooth[y] > dyn_thr and not in_line:
                in_line, start = True, y
            elif proj_smooth[y] <= dyn_thr and in_line:
                in_line = False
                height = y - start
                # Accept shorter lines for high density, with noise filtering
                if 12 <= height <= 120:
                    lines.append((start, y))

        if in_line and len(proj) - start >= 12:
            lines.append((start, len(proj)))

        # Detect strike-through lines and mark them
        processed_lines = []
        for idx, (y1, y2) in enumerate(lines):
            line_crop = gray[y1:y2, :]
            line_th = th[y1:y2, :]

            # Detect horizontal line crossing through middle of the line
            mid_h = line_th.shape[0] // 2
            mid_start = max(0, mid_h - 2)
            mid_end = min(line_th.shape[0], mid_h + 3)
            horizontal_proj_mid = np.sum(line_th[mid_start:mid_end, :], axis=0)

            # If >60% of width has ink in the middle band -> likely strike-through
            is_crossed = np.mean(horizontal_proj_mid > 0) > 0.6

            processed_lines.append({
                'idx': idx,
                'bbox': (y1, y2),
                'image': line_crop,
                'is_crossed': is_crossed,
            })

        return processed_lines

    # ────────────────────────────────────────────────────────
    # Page Verification (v1 - Original)
    # ────────────────────────────────────────────────────────

    def verify_page(self, img: np.ndarray) -> List[Dict]:
        """التحقق المزدوج لصفحة كاملة - يُرجع نتائج كل الأسطر (الإصدار الأصلي)."""
        lines = self.extract_lines(img)
        results = []
        for i, (y1, y2) in enumerate(lines):
            line_img = img[y1:y2] if len(img.shape) == 2 else img[y1:y2, :]
            result = self.verify_line(line_img, i)
            results.append(result)
        return results

    # ────────────────────────────────────────────────────────
    # Page Verification v3.1 (with strike-through + references)
    # ────────────────────────────────────────────────────────

    def verify_page_v3(self, img: np.ndarray) -> Tuple[List[Dict], List[Dict]]:
        """
        التحقق المزدوج لصفحة كاملة v3.1.

        يستخدم:
        - segment_lines_v3 للكشف عن الأسطر المشطوبة
        - extract_references_v3 لعزل المراجع
        - preprocess_for_ocr_v3 للمعالجة المحسّنة

        Returns:
            Tuple of (verification_results, rejected_lines).
            rejected_lines contains lines that were skipped (crossed-out, etc.)
        """
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Apply v3.1 preprocessing
        enhanced_page, margins = self.preprocess_for_ocr_v3(gray)

        # Segment with v3.1 (includes strike-through detection)
        lines_data = self.segment_lines_v3(gray)

        results = []
        rejected = []

        for line_info in lines_data:
            y1, y2 = line_info['bbox']
            crop = line_info['image']

            if line_info['is_crossed']:
                # Reject crossed-out lines
                rejected.append({
                    'idx': line_info['idx'],
                    'bbox': line_info['bbox'],
                    'reason': 'crossed_out',
                    'image': crop,
                })
                continue

            # Verify non-crossed lines with v3 preprocessing
            result = self.verify_line(crop, line_info['idx'], use_v3=True)
            results.append(result)

        return results, rejected
