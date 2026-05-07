"""
معالج النصوص المختلطة (Mixed Language Handler)
==================================================
يكتشف اللغة على مستوى الكلمة وينفذ التصحيح الإملائي المناسب
لكل مقطع. يدعم العربية والإنجليزية والفرنسية والألمانية.

الاستخدام:
    >>> handler = MixedLanguageHandler(languages=['ar', 'en'])
    >>> segments = handler.split_by_language("مرحبا world مرحبا")
    >>> corrected = handler.correct_text_mixed("مرحبا world")
    >>> langs = handler.get_ocr_language_params("مرحبا world")

المؤلف: Dr Abdulmalek Tamer Al-husseini
الترخيص: MIT
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# بذرة ثابتة لضمان نتائج متسقة من langdetect
try:
    from langdetect import DetectorFactory
    DetectorFactory.seed = 0
except ImportError:
    pass

# قاموس تصحيحات عربية مخصص (يمكن توسيعه لاحقاً)
ARABIC_CORRECTIONS: dict[str, str] = {
    "السلام": "السلام",
    "مرحبا": "مرحباً",
    "الكتاب": "الكتاب",
    "العالم": "العالم",
    "الحياه": "الحياة",
    "الدراسه": "الدراسة",
    "الجامعه": "الجامعة",
    "الطالب": "الطالب",
    "العمل": "العمل",
    "البحث": "البحث",
}


class MixedLanguageHandler:
    """
    معالج متعدد اللغات للنصوص المختلطة.

    مثال الاستخدام:
        >>> handler = MixedLanguageHandler(languages=['ar', 'en', 'fr'])
        >>> text = "مرحبا Hello bonjour"
        >>> segments = handler.split_by_language(text)
        >>> corrected = handler.correct_text_mixed(text)
    """

    def __init__(self, languages: Optional[list[str]] = None):
        """
        تهيئة المعالج.

        Args:
            languages: قائمة اللغات المدعومة
                       (الافتراضي: ['ar', 'en', 'fr', 'de'])
        """
        if languages is None:
            languages = ["ar", "en", "fr", "de"]
        self.languages = languages
        self.spell_checkers: dict[str, object] = {}

        # تحميل مدققي الإملاء لكل لغة (ما عدا العربية)
        for lang in languages:
            if lang != "ar":
                try:
                    from spellchecker import SpellChecker
                    self.spell_checkers[lang] = SpellChecker(language=lang)
                except Exception:
                    logger.debug(
                        "تعذر تحميل مدقق إملائي للغة %s", lang
                    )

    def detect_language(self, text: str) -> str:
        """
        كشف لغة نص معين.

        Args:
            text: النص المطلوب تحليل لغته

        Returns:
            رمز اللغة (ar, en, fr, de, ...)
        """
        if not text or not text.strip():
            return "ar"

        try:
            from langdetect import detect
            return detect(text)
        except Exception:
            # تراجع: فحص محارف عربية
            if re.search(r"[\u0600-\u06FF]", text):
                return "ar"
            return "en"

    def split_by_language(self, text: str) -> list[tuple[str, str]]:
        """
        تقسيم النص إلى مقاطع حسب اللغة.

        Args:
            text: النص المختلط

        Returns:
            قائمة أزواج (لغة, مقطع نصي)
        """
        tokens = re.findall(r"\S+|\s+", text)
        segments: list[tuple[str, str]] = []
        current_lang: Optional[str] = None
        current_segment = ""

        for token in tokens:
            if token.isspace():
                current_segment += token
                continue

            lang = self.detect_language(token)

            if lang != current_lang:
                if current_segment:
                    segments.append((current_lang or "ar", current_segment))
                current_lang = lang
                current_segment = token
            else:
                current_segment += token

        if current_segment:
            segments.append((current_lang or "ar", current_segment))

        return segments

    def correct_text_mixed(self, text: str) -> str:
        """
        تصحيح النص المختلط باستخدام المدقق المناسب لكل مقطع.

        Args:
            text: النص المختلط

        Returns:
            النص المصحح
        """
        segments = self.split_by_language(text)
        corrected_parts = []

        for lang, segment in segments:
            if lang == "ar":
                corrected = self._correct_arabic(segment)
            elif lang in self.spell_checkers:
                corrected = self._correct_with_spellchecker(lang, segment)
            else:
                corrected = segment
            corrected_parts.append(corrected)

        return "".join(corrected_parts)

    def process(self, text: str) -> str:
        """واجهة متوافقة مع الـ notebook — تساوي correct_text_mixed."""
        return self.correct_text_mixed(text)

    def _correct_arabic(self, text: str) -> str:
        """
        تصحيح النص العربي باستخدام القاموس المحلي.

        Args:
            text: النص العربي

        Returns:
            النص المصحح
        """
        words = re.findall(r"\S+", text)
        corrected_words = []

        for w in words:
            if w in ARABIC_CORRECTIONS:
                corrected_words.append(ARABIC_CORRECTIONS[w])
            else:
                corrected_words.append(w)

        return " ".join(corrected_words)

    def _correct_with_spellchecker(self, lang: str, text: str) -> str:
        """
        تصحيح النص باستخدام pyspellchecker.

        Args:
            lang: رمز اللغة
            text: النص

        Returns:
            النص المصحح
        """
        checker = self.spell_checkers.get(lang)
        if checker is None:
            return text

        words = re.findall(r"\S+", text)
        corrected = []

        for w in words:
            suggestion = checker.correction(w)
            corrected.append(suggestion if suggestion else w)

        return " ".join(corrected)

    def get_ocr_language_params(self, full_text: str) -> list[str]:
        """
        استخراج معلمات اللغات المناسبة لتمريرها إلى محرك OCR.

        يفحص أول 50 كلمة من النص ويجمع اللغات المكتشفة.

        Args:
            full_text: النص الكامل

        Returns:
            قائمة رموز اللغات المكتشفة
        """
        langs_detected: set[str] = set()

        # فحص أول 50 كلمة
        words = full_text.split()[:50]
        for w in words:
            detected_lang = self.detect_language(w)
            langs_detected.add(detected_lang)

        # دائماً إضافة العربية والإنجليزية كحد أدنى
        if not langs_detected:
            langs_detected = {"ar", "en"}

        return list(langs_detected)
