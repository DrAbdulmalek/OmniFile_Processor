"""
HandwrittenOCR - محرك التصحيح الإملائي وقاموس التصحيح v5.0
================================================================
المحسنات (مبنية على اقتراحات Gemini + تحسينات يدوية):
- TECHNICAL_KEYWORDS: حماية المصطلحات البرمجية من التصحيح الخاطئ
- PYTHON_KEYWORDS: كلمات بايثون المحجوزة لا تُصحَّح أبداً
- تحميل كلمات مخصصة في word_frequency للمدقق الإملائي
- correct_text() تعترف الآن بالكلمات التقنية وتتجاوزها
- spell_correct_word() محسّن بنفس الطريقة

التغييرات عن v4.0:
1. إضافة _TECH_KEYWORDS_LOWER (مجموعة مقارنة حالة الأحرف الصغيرة)
2. إضافة _PYTHON_KEYWORDS (كلمات بايثون المحجوزة)
3. تحديث init_correctors() لتحميل الكلمات المخصصة
4. إضافة _is_protected_word() للتحقق السريع
5. تحديث _correct_english() لتجاوز الكلمات المحمية
6. تحديث spell_correct_word() بنفس المنطق
7. إضافة load_custom_vocabulary() لتحميل مصطلحات إضافية ديناميكياً
"""

import json
import os
import logging
import pandas as pd
from datetime import datetime
from collections import Counter, defaultdict
from spellchecker import SpellChecker
from langdetect import detect, DetectorFactory

logger = logging.getLogger("HandwrittenOCR")

DetectorFactory.seed = 0

_ar_corrector = None
_en_spellchecker = None

# ===================== قائمة المصطلحات المحمية =====================
# مصطلحات تقنية مستخرجة من ملاحظات "python notes.pdf"
# لا يُطبَّق عليها المدقق الإملائي أبدًا لمنع تحريفها
TECHNICAL_KEYWORDS = {
    # مصطلحات برمجية عامة
    "python", "pythonistas", "scraping", "parsing", "ocr",
    "batch", "programming", "script", "database", "configure",
    "setup", "env", "immutable", "concatenation", "tuples",
    "dictionaries", "debugging", "programmatically", "spreadsheet",
    "integers", "float", "boolean", "syntax", "web",
    "etl", "dataframe", "json", "csv", "yaml", "markdown",
    "mermaid", "repository", "clone", "commit", "push",
    # اختصارات تقنية
    "repl", "dpi", "api", "gpu", "cpu", "ram", "rom",
    "lora", "huggingface", "transformers", "pytorch", "tensorboard",
    # كلمات من ملاحظات المستخدم
    "printouts", "involve", "scattered", "skyrocketed", "stacked",
    "affectionately", "serpentine", "cryptic", "sophisticated",
    "intricate", "throwaway", "surreal", "conventions",
    "trade", "off", "boot", "camps",
    # مفاهيم تقنية
    "comprehensions", "replication", "precedence", "modulo",
    "exponent", "traceback", "overriding",
}

# كلمات بايثون المحجوزة — لا تُصحَّح أبدًا
PYTHON_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
    # دوال مدمجة
    "print", "input", "len", "range", "type", "int", "str", "float",
    "list", "dict", "set", "tuple", "bool", "open", "file", "super",
    "self", "cls", "init", "repr", "main", "name", "args", "kwargs",
    "append", "extend", "pop", "sort", "join", "split", "strip",
    "format", "replace", "lower", "upper", "title", "capitalize",
    "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "isinstance", "issubclass", "hasattr", "getattr", "setattr",
    "import", "from", "as", "module", "package",
}

# كلمات إضافية قابلة للتوسيع (مصطلحات خاصة بالمستخدم)
_CUSTOM_VOCAB = set()

# مجموعة داخلية للحصول على أفضل أداء (كلها lowercase)
_PROTECTED_WORDS_LOWER = set()


def _rebuild_protected_set():
    """إعادة بناء مجموعة الكلمات المحمية (تُستدعى بعد كل تعديل)"""
    global _PROTECTED_WORDS_LOWER
    _PROTECTED_WORDS_LOWER = (
        {k.lower() for k in TECHNICAL_KEYWORDS}
        | {k.lower() for k in PYTHON_KEYWORDS}
        | {k.lower() for k in _CUSTOM_VOCAB}
    )


def _is_protected_word(word: str) -> bool:
    """التحقق مما إذا كانت الكلمة محمية (لا تحتاج تصحيح)"""
    return word.lower() in _PROTECTED_WORDS_LOWER


def init_correctors() -> None:
    """
    تهيئة المدققات الإملائية.
    v5.0: يحمل الكلمات المخصصة في word_frequency أيضًا.
    """
    global _ar_corrector, _en_spellchecker

    try:
        from ar_corrector.corrector import Corrector
        _ar_corrector = Corrector()
        logger.info("تم تحميل المدقق الإملائي العربي")
    except ImportError:
        logger.warning("ar-corrector غير مثبت. التصحيح العربي لن يكون متاحاً.")

    _en_spellchecker = SpellChecker(language="en")

    # v5.0: تحميل الكلمات المحمية في قاموس التردد
    # هذا يمنع SpellChecker من اقتراح بدائل لها
    all_known_words = list(TECHNICAL_KEYWORDS | PYTHON_KEYWORDS | _CUSTOM_VOCAB)
    if all_known_words:
        _en_spellchecker.word_frequency.load_words(all_known_words)
        logger.info(f"تم تحميل {len(all_known_words)} كلمة محمية في المدقق الإملائي")

    _rebuild_protected_set()
    logger.info("تم تحميل المدقق الإملائي الإنجليزي (مع حماية المصطلحات التقنية)")


def load_custom_vocabulary(vocab_list: list[str]) -> None:
    """
    تحميل مصطلحات إضافية لحمايتها من التصحيح.
    يمكن استدعاؤها ديناميكياً لتحميل مصطلحات مستخدم جديدة.

    Parameters:
        vocab_list: قائمة بالكلمات الإنجليزية الواجب حمايتها
    """
    global _CUSTOM_VOCAB
    _CUSTOM_VOCAB.update(w.strip() for w in vocab_list if w.strip())
    _rebuild_protected_set()

    if _en_spellchecker:
        new_words = [w.strip() for w in vocab_list if w.strip()]
        if new_words:
            _en_spellchecker.word_frequency.load_words(new_words)

    logger.info(f"تم تحميل {len(vocab_list)} مصطلح إضافي في القائمة المحمية (المجموع: {len(_PROTECTED_WORDS_LOWER)})")


def correct_text(text: str) -> str:
    """
    تصحيح إملائي حسب اللغة المكتشفة.
    v5.0: يتجاوز الكلمات المحمية (تقنية + بايثون + مخصصة).
    """
    if not text or not text.strip():
        return text

    text = text.strip()
    try:
        lang = detect(text)
        if lang == "ar":
            return _correct_arabic(text)
        elif lang == "en":
            return _correct_english(text)
    except Exception:
        pass
    return text


def _correct_arabic(text: str) -> str:
    if _ar_corrector is None:
        return text
    try:
        return _ar_corrector.contextual_correct(text)
    except Exception as e:
        logger.debug(f"خطأ في التصحيح العربي: {e}")
        return text


def _correct_english(text: str) -> str:
    """
    تصحيح الجمل الإنجليزية كلمة بكلمة مع حفظ الترقيم.
    v5.0: يتجاوز الكلمات المحمية من التصحيح.
    """
    if _en_spellchecker is None:
        return text
    try:
        words = text.split()
        corrected = []
        for word in words:
            # v5.0: إذا كانت الكلمة محمية، اتركها كما هي
            if _is_protected_word(word):
                corrected.append(word)
                continue

            clean = word.strip(".,;:!?\"'()-")
            if clean:
                # التحقق مرة أخرى من النظيف (بدون ترقيم)
                if _is_protected_word(clean):
                    corrected.append(word)
                    continue

                fixed = _en_spellchecker.correction(clean)
                corrected_word = word.replace(clean, fixed) if fixed else word
                corrected.append(corrected_word)
            else:
                corrected.append(word)
        return " ".join(corrected)
    except Exception as e:
        logger.debug(f"خطأ في التصحيح الإنجليزي: {e}")
        return text


def spell_correct_word(text: str) -> str:
    """
    تصحيح سريع كلمة بكلمة — للمعالجة في الحلقات.
    v5.0: يتجاوز الكلمات المحمية.
    """
    text = text.strip()
    if not text:
        return ""

    # v5.0: إذا كانت الكلمة محمية، أعدّها كما هي
    if _is_protected_word(text):
        return text

    try:
        lang = detect(text)
        if lang == "ar" and _ar_corrector:
            return _ar_corrector.contextual_correct(text)

        words = text.split()
        corrected = []
        for w in words:
            if _is_protected_word(w):
                corrected.append(w)
            else:
                corrected.append(_en_spellchecker.correction(w) or w)
        return " ".join(corrected)
    except Exception:
        return text


# ===================== قاموس التصحيح المستمر =====================

def build_correction_dict(
    feedback_csv: str,
    correction_dict_path: str,
    min_votes: int = 1,
) -> dict:
    """
    بناء قاموس تصحيح من تصحيحات المستخدم.
    يستخدم defaultdict(Counter) للعد الفعّال.
    """
    if not os.path.exists(feedback_csv):
        return {}

    try:
        df_fb = pd.read_csv(feedback_csv, encoding="utf-8-sig")
        if df_fb.empty:
            return {}

        buckets = defaultdict(Counter)
        for _, row in df_fb.iterrows():
            orig = str(row.get("original_text", "")).strip()
            corr = str(row.get("corrected_text", "")).strip()
            if orig and corr and orig != corr:
                buckets[orig][corr] += 1

        result = {
            orig: cnt.most_common(1)[0][0]
            for orig, cnt in buckets.items()
            if cnt.most_common(1)[0][1] >= min_votes
        }

        os.makedirs(os.path.dirname(correction_dict_path), exist_ok=True)
        with open(correction_dict_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"تم تحديث قاموس التصحيح: {len(result)} كلمة")
        return result

    except Exception as e:
        logger.error(f"خطأ في بناء القاموس: {e}")
        return {}


def load_correction_dict(correction_dict_path: str) -> dict:
    """تحميل قاموس التصحيح من الملف."""
    if not os.path.exists(correction_dict_path):
        return {}
    try:
        with open(correction_dict_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"خطأ في تحميل القاموس: {e}")
        return {}


def apply_correction_dict(text: str, correction_dict: dict) -> str:
    """تطبيق قاموس التصحيح على نص."""
    if not correction_dict or not text:
        return text
    words = text.split()
    corrected = [correction_dict.get(w, w) for w in words]
    return " ".join(corrected)


def append_feedback(
    feedback_csv: str,
    image_id: int,
    original: str,
    corrected: str,
    status: str = "verified",
) -> None:
    """تسجيل تصحيح في ملف CSV."""
    os.makedirs(os.path.dirname(feedback_csv), exist_ok=True)
    ts = datetime.now().isoformat()
    record = {
        "timestamp": ts,
        "image_id": image_id,
        "original_text": original,
        "corrected_text": corrected,
        "status": status,
    }
    file_exists = os.path.exists(feedback_csv)
    pd.DataFrame([record]).to_csv(
        feedback_csv, mode="a",
        header=not file_exists,
        index=False, encoding="utf-8-sig",
    )


def get_protected_words_count() -> dict:
    """إرجاع عدد الكلمات المحمية لكل فئة (مفيد للـ API)."""
    return {
        "technical_keywords": len(TECHNICAL_KEYWORDS),
        "python_keywords": len(PYTHON_KEYWORDS),
        "custom_vocabulary": len(_CUSTOM_VOCAB),
        "total_protected": len(_PROTECTED_WORDS_LOWER),
    }


# === Compatibility class for OmniFile_v500_Colab ===
class CorrectionManager:
    """واجهة متوافقة مع الـ notebook — تغلف الدوال المستقلة في class."""
    def __init__(self, feedback_csv="", correction_dict_path=""):
        self.feedback_csv = feedback_csv
        self.correction_dict_path = correction_dict_path
        self._dict = {}

    def correct(self, text: str) -> str:
        return correct_text(text)

    def build_dict(self, min_votes=1) -> dict:
        if self.feedback_csv and self.correction_dict_path:
            self._dict = build_correction_dict(
                self.feedback_csv, self.correction_dict_path, min_votes=min_votes
            )
        return self._dict

    def load_dict(self) -> dict:
        if self.correction_dict_path:
            self._dict = load_correction_dict(self.correction_dict_path)
        return self._dict

    def apply_dict(self, text: str) -> str:
        if not self._dict:
            self.load_dict()
        return apply_correction_dict(text, self._dict)

    def add_feedback(self, image_id, original, corrected, status="verified"):
        if self.feedback_csv:
            append_feedback(self.feedback_csv, image_id, original, corrected, status)
