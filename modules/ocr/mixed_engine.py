"""
Mixed Language OCR Engine — محرك OCR ذكي يدعم العربية والإنجليزية
مع دعم التعلم من التصحيحات عبر PatternDB
"""
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class WordResult:
    """نتيجة التعرف على كلمة واحدة"""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    language: str  # 'en', 'ar', 'mixed', 'symbol'
    is_corrected: bool = False
    pattern_id: Optional[int] = None


class MixedLanguageOCR:
    """
    محرك OCR ذكي يدعم العربية والإنجليزية في نفس الصفحة
    مع دعم التعلم من التصحيحات عبر PatternDB
    """

    def __init__(self,
                 pattern_db_path: str = "data/vocab_patterns.db",
                 use_trocr: bool = True,
                 use_easyocr_fallback: bool = True,
                 min_confidence: float = 0.6):

        self.min_confidence = min_confidence
        self.pattern_db = None
        self.engines = {}

        try:
            from modules.learning.pattern_db import PatternDB
            self.pattern_db = PatternDB(pattern_db_path)
        except ImportError:
            print("⚠️ PatternDB غير متاح")

        if use_trocr:
            self._init_trocr()

        if use_easyocr_fallback:
            self._init_easyocr()

    def _init_trocr(self):
        """تهيئة TrOCR للتعرف على الخط اليدوي"""
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            import torch

            model_name = "microsoft/trocr-base-handwritten"
            self.trocr_processor = TrOCRProcessor.from_pretrained(model_name)
            self.trocr_model = VisionEncoderDecoderModel.from_pretrained(model_name)

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.trocr_model.to(device)
            self.trocr_device = device
            self.engines['trocr'] = True
        except ImportError:
            print("⚠️ TrOCR غير متاح. تأكد من تثبيت: transformers torch")

    def _init_easyocr(self):
        """تهيئة EasyOCR كاحتياطي"""
        try:
            import easyocr
            self.easyocr_reader = easyocr.Reader(['en', 'ar'], gpu=False, verbose=False)
            self.engines['easyocr'] = True
        except ImportError:
            print("⚠️ EasyOCR غير متاح. قم بالتثبيت: pip install easyocr")

    def extract_from_column(self,
                           column_image: np.ndarray,
                           language_hint: str = 'en',
                           line_positions: Optional[List[int]] = None) -> List[WordResult]:
        """استخراج الكلمات من عمود واحد"""
        results = []

        if line_positions is None:
            line_positions = self._detect_lines_simple(column_image)

        for i, line_y in enumerate(line_positions):
            line_height = 40
            if i + 1 < len(line_positions):
                line_height = line_positions[i+1] - line_y

            line_img = column_image[line_y:line_y+line_height, :]
            if line_img.size == 0:
                continue

            words = self._segment_line_words(line_img, line_y)

            for word_img, bbox in words:
                result = self._recognize_word(word_img, language_hint, bbox)
                if result:
                    results.append(result)

        return results

    def _recognize_word(self,
                       word_image: np.ndarray,
                       language_hint: str,
                       bbox: Tuple[int, int, int, int]) -> Optional[WordResult]:
        """التعرف على كلمة واحدة مع الاستفادة من الأنماط المحفوظة"""

        if self.pattern_db:
            pattern_match = self.pattern_db.find_similar(
                image=word_image,
                language=language_hint,
                threshold=0.92
            )
            if pattern_match:
                return WordResult(
                    text=pattern_match['corrected_text'],
                    confidence=0.99,
                    bbox=bbox,
                    language=language_hint,
                    is_corrected=True,
                    pattern_id=pattern_match.get('id')
                )

        if 'trocr' in self.engines:
            trocr_result = self._trocr_predict(word_image, language_hint)
            if trocr_result and trocr_result['confidence'] >= self.min_confidence:
                return WordResult(
                    text=trocr_result['text'],
                    confidence=trocr_result['confidence'],
                    bbox=bbox,
                    language=language_hint
                )

        if 'easyocr' in self.engines:
            easyocr_result = self._easyocr_predict(word_image, language_hint)
            if easyocr_result and easyocr_result['confidence'] >= self.min_confidence:
                return WordResult(
                    text=easyocr_result['text'],
                    confidence=easyocr_result['confidence'],
                    bbox=bbox,
                    language=language_hint
                )

        return WordResult(text="", confidence=0.0, bbox=bbox, language='unknown')

    def _trocr_predict(self, image: np.ndarray, language_hint: str) -> Optional[Dict]:
        """التنبؤ باستخدام TrOCR"""
        try:
            from PIL import Image
            import torch

            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            pil_image = Image.fromarray(image)

            inputs = self.trocr_processor(images=pil_image, return_tensors="pt")
            inputs = {k: v.to(self.trocr_device) for k, v in inputs.items()}

            with torch.no_grad():
                generated_ids = self.trocr_model.generate(**inputs, max_length=50)

            predicted_text = self.trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
            confidence = self._estimate_confidence(predicted_text, language_hint)

            return {'text': predicted_text, 'confidence': confidence}

        except Exception as e:
            print(f"⚠️ خطأ في TrOCR: {e}")
            return None

    def _easyocr_predict(self, image: np.ndarray, language_hint: str) -> Optional[Dict]:
        """التنبؤ باستخدام EasyOCR"""
        try:
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

            results = self.easyocr_reader.readtext(
                image,
                detail=1,
                paragraph=False,
                canvas_size=max(image.shape[:2])
            )

            if results:
                best = max(results, key=lambda x: x[2])
                text, confidence = best[1], best[2]
                return {'text': text.strip(), 'confidence': confidence}

            return None
        except Exception as e:
            print(f"⚠️ خطأ في EasyOCR: {e}")
            return None

    def _segment_line_words(self, line_image: np.ndarray, line_y: int) -> List[Tuple[np.ndarray, Tuple]]:
        """تقسيم سطر إلى كلمات فردية"""
        words = []

        if len(line_image.shape) == 3:
            gray = cv2.cvtColor(line_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = line_image.copy()

        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        vertical_proj = np.sum(binary, axis=0)
        avg_density = np.mean(vertical_proj[vertical_proj > 0]) if np.any(vertical_proj > 0) else 0
        gap_threshold = avg_density * 0.15

        in_word = False
        word_start = 0
        min_word_width = 8

        for x in range(binary.shape[1]):
            if vertical_proj[x] > gap_threshold and not in_word:
                in_word = True
                word_start = x
            elif vertical_proj[x] <= gap_threshold and in_word:
                in_word = False
                word_width = x - word_start
                if word_width >= min_word_width:
                    word_img = line_image[:, word_start:x].copy()
                    bbox = (word_start, line_y, x, line_y + line_image.shape[0])
                    words.append((word_img, bbox))

        if in_word and binary.shape[1] - word_start >= min_word_width:
            word_img = line_image[:, word_start:].copy()
            bbox = (word_start, line_y, binary.shape[1], line_y + line_image.shape[0])
            words.append((word_img, bbox))

        return words

    def _detect_lines_simple(self, image: np.ndarray) -> List[int]:
        """اكتشاف بسيط لمواقع الأسطر"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        horizontal_proj = np.sum(binary, axis=1)

        threshold = np.percentile(horizontal_proj, 70)

        lines = []
        in_line = False
        for y in range(len(horizontal_proj)):
            if horizontal_proj[y] > threshold and not in_line:
                in_line = True
                lines.append(y)
            elif horizontal_proj[y] <= threshold:
                in_line = False

        return lines

    def _estimate_confidence(self, text: str, language_hint: str) -> float:
        """تقدير ثقة مبسط للنص المنتج"""
        if not text:
            return 0.0

        penalty = 0.0

        if len(text) < 2:
            penalty += 0.2

        if language_hint == 'en':
            arabic_chars = 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي'
            if any(c in text for c in arabic_chars):
                penalty += 0.3
        elif language_hint == 'ar':
            en_chars = sum(c.isascii() and c.isalpha() for c in text)
            if en_chars > len(text) * 0.3:
                penalty += 0.2

        if any(text.count(c) > len(text) * 0.5 for c in set(text) if text.count(c) > 3):
            penalty += 0.15

        return max(0.0, min(1.0, 0.95 - penalty))
