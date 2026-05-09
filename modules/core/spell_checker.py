"""
modules/core/spell_checker.py — Hybrid Spell Checker v7.0
مدقق إملائي هجين يكتشف اللغة تلقائياً ويدعم العربية/الإنجليزية/الألمانية

v7.0 changes:
- إضافة enhance_digit_recognition() (من src/correction.py)
- إضافة spell_correct_word() (تصحيح كلمة واحدة مع digit recognition)
- الملف هو الآن Backend الموحّد — src/correction.py يُفوّض إليه بالكامل

v6.0 changes:
- دمج TECHNICAL_KEYWORDS + PYTHON_KEYWORDS من src/correction.py مباشرة
- حماية المصطلحات البرمجية من التصحيح الخاطئ (المراجعة المعمارية)
- إضافة _is_protected_word() مع دعم الكلمات المخصصة
- get_suggestions/auto_correct/check_text تتجاوز الكلمات المحمية
"""
import json, logging, re
from difflib import get_close_matches
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
ARABIC_FIXES_PATH = "data/arabic_fixes.json"
_AR_RE = re.compile(r'[\u0600-\u06ff]')
_EN_RE = re.compile(r'[a-zA-Z]')

# ===================== قائمة المصطلحات المحمية =====================
# هذه الكلمات لن يُقترح أي تصحيح لها — تحل مشكلة "تصحيح" الكلمات البرمجية

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

# مجموعة داخلية للحصول على أفضل أداء (كلها lowercase)
_PROTECTED_WORDS_LOWER: set = set()


def _rebuild_protected_set():
    """إعادة بناء مجموعة الكلمات المحمية."""
    global _PROTECTED_WORDS_LOWER
    _PROTECTED_WORDS_LOWER = {k.lower() for k in TECHNICAL_KEYWORDS} | {k.lower() for k in PYTHON_KEYWORDS}


# بناء المجموعة عند استيراد الوحدة
_rebuild_protected_set()


class HybridSpellChecker:
    """مدقق إملائي هجين — يكتشف اللغة تلقائياً من النص المكتوب."""

    def __init__(self, arabic_fixes_path: str = ARABIC_FIXES_PATH) -> None:
        self._fixes_path = Path(arabic_fixes_path)
        self._arabic_fixes: dict = {}
        self._spell_en = self._spell_ar = self._spell_de = None
        self._custom_protected: set = set()  # كلمات محمية إضافية من المستخدم
        self._load_fixes()

    def _load_fixes(self) -> None:
        try:
            if self._fixes_path.exists():
                with open(self._fixes_path, encoding="utf-8") as f:
                    self._arabic_fixes = json.load(f)
        except Exception as e:
            logger.warning("arabic_fixes: %s", e)

    def reload_fixes(self) -> None:
        self._load_fixes()

    def _sc(self, lang: str):
        """Lazy-load pyspellchecker for given language."""
        attr = f"_spell_{lang}"
        if getattr(self, attr) is None:
            try:
                from spellchecker import SpellChecker
                sc = SpellChecker(language=lang, distance=1)
                # تحميل الكلمات المحمية في قاموس التردد لمنع اقتراح بدائلها
                all_protected = list(TECHNICAL_KEYWORDS | PYTHON_KEYWORDS)
                if all_protected:
                    sc.word_frequency.load_words(all_protected)
                setattr(self, attr, sc)
            except Exception:
                setattr(self, attr, False)
        obj = getattr(self, attr)
        return obj if obj else None

    # ── حماية الكلمات البرمجية ──────────────────────────────────────

    @staticmethod
    def is_protected_word(word: str) -> bool:
        """
        التحقق مما إذا كانت الكلمة محمية (مصطلح برمجي/كلمة بايثون).
        الكلمات المحمية لا تُصحَّح أبداً — تُعاد كما هي.
        """
        if not word:
            return False
        return word.lower() in _PROTECTED_WORDS_LOWER

    def add_protected_words(self, words: list[str]) -> None:
        """إضافة كلمات مخصصة للحماية من التصحيح."""
        new_words = [w.strip().lower() for w in words if w.strip()]
        if new_words:
            self._custom_protected.update(new_words)
            # تحديث المجموعة العامة أيضاً
            global _PROTECTED_WORDS_LOWER
            _PROTECTED_WORDS_LOWER = _PROTECTED_WORDS_LOWER | self._custom_protected
            logger.debug("تم إضافة %d كلمة محمية مخصصة (المجموع: %d)", len(new_words), len(_PROTECTED_WORDS_LOWER))

    def _is_protected(self, word: str) -> bool:
        """فحص محلي يشمل الكلمات المخصصة أيضاً."""
        if not word:
            return False
        return word.lower() in (_PROTECTED_WORDS_LOWER | self._custom_protected)

    # ── اكتشاف اللغة ─────────────────────────────────────────────────

    def detect_language(self, text: str) -> str:
        """
        اكتشاف لغة النص من محتواه — بدون اختيار يدوي.
        Returns: "ar" | "en" | "de" | "mixed"
        """
        if not text or not text.strip():
            return "en"
        clean = text.replace(" ", "")
        ar = len(_AR_RE.findall(clean)) / max(len(clean), 1)
        en = len(_EN_RE.findall(clean)) / max(len(clean), 1)
        if ar > 0.50:   return "ar"
        if en > 0.50:
            de_chars = len(re.findall(r'[äöüßÄÖÜ]', text))
            de_words = sum(1 for w in ["der","die","das","und","ist","nicht"] if w in text.lower())
            return "de" if (de_chars > 0 or de_words >= 2) else "en"
        if ar > 0.15 or en > 0.15:
            return "mixed"
        return "en"

    # ── الاقتراحات ───────────────────────────────────────────────────

    def get_suggestions(self, word: str, lang: Optional[str] = None, n: int = 5) -> list:
        """
        اقتراحات تصحيح من أربعة مصادر: fixes + DB + spellchecker + difflib.
        الكلمات المحمية تُتجاوز مباشرة وتُعاد كما هي.
        """
        if not word or not word.strip():
            return []

        # ⛔ تخطي الكلمات المحمية
        if self._is_protected(word):
            return []  # لا توجد اقتراحات لكلمة محمية

        if lang is None:
            lang = self.detect_language(word)
        suggestions = []

        # 1. arabic_fixes.json (أعلى أولوية لأخطاء OCR)
        if lang in ("ar", "mixed") and word in self._arabic_fixes:
            fixed = self._arabic_fixes[word]
            if fixed != word:
                suggestions.append(fixed)

        # 2. WordCorrectionDB (تعلّم من تصحيحات المستخدم)
        try:
            from modules.core.word_trainer import WordCorrectionDB
            db = WordCorrectionDB()
            best = db.get_best_correction(word, lang=lang)
            if best and best != word and best not in suggestions:
                suggestions.insert(0, best)
            for s in db.get_suggestions(word, lang=lang, n=n):
                if s != word and s not in suggestions:
                    suggestions.append(s)
        except Exception:
            pass

        # 3. pyspellchecker
        lang_map = {"ar": "ar", "en": "en", "de": "de", "mixed": "en"}
        sc_lang = lang_map.get(lang, "en")
        sc = self._sc(sc_lang)
        if sc:
            try:
                if word.lower() not in sc:
                    for c in list(sc.candidates(word) or [])[:n]:
                        if c != word and c not in suggestions:
                            suggestions.append(c)
            except Exception:
                pass

        # 4. Difflib على arabic_fixes كـ fallback
        if not suggestions and lang in ("ar", "mixed"):
            pool = list(self._arabic_fixes.keys())
            for c in get_close_matches(word, pool, n=n, cutoff=0.72):
                if c not in suggestions:
                    suggestions.append(c)

        seen, unique = set(), []
        for s in suggestions:
            if s not in seen:
                seen.add(s); unique.append(s)
        return unique[:n]

    def auto_correct(self, word: str) -> tuple:
        """
        تصحيح تلقائي + كشف لغة. Returns: (corrected, lang)
        الكلمات المحمية تُعاد كما هي مع lang=en.
        """
        lang = self.detect_language(word)

        # ⛔ تخطي الكلمات المحمية
        if self._is_protected(word):
            return word, lang

        if lang in ("ar", "mixed") and word in self._arabic_fixes:
            return self._arabic_fixes[word], lang
        sugg = self.get_suggestions(word, lang=lang, n=1)
        return (sugg[0] if sugg else word), lang

    def check_text(self, text: str) -> dict:
        """
        فحص نص كامل. Returns: {lang, words: [...], total}
        الكلمات المحمية تُعلَّم "protected": True.
        """
        lang = self.detect_language(text)
        results = []
        for w in text.split():
            corrected, _ = self.auto_correct(w)
            results.append({
                "word": w, "corrected": corrected,
                "suggestions": self.get_suggestions(w, lang=lang, n=3),
                "changed": corrected != w,
                "protected": self._is_protected(w),
            })
        return {"lang": lang, "words": results, "total": len(results)}

    # ── تصحيح الأرقام البصري ───────────────────────────────────────

    _DIGIT_CORRECTIONS = {
        "O": "0", "o": "0",
        "I": "1", "l": "1", "|": "1",
        "Z": "2", "z": "2",
        "S": "5", "s": "5",
        "G": "6",
        "T": "7", "t": "7",
        "B": "8",
    }

    def enhance_digit_recognition(self, text: str) -> str:
        """
        تصحيح حرفي للأرقام في النص (OCR artifact fix).
        يحوّل الحروف المشابهة بصرياً للأرقام: O→0, I→1, S→5, ...
        يعمل فقط على الكلمات الخالصة من الأرقام والحروف المشابهة.
        """
        if not text:
            return text
        words = text.split()
        corrected = []
        for word in words:
            clean = word.strip(".,;:!?\"'()-")
            if clean and all(c.isalnum() or c in "_-/" for c in clean):
                if any(c.isdigit() for c in clean):
                    fixed = clean
                    for letter, digit in self._DIGIT_CORRECTIONS.items():
                        fixed = fixed.replace(letter, digit)
                    if fixed != clean and fixed.isdigit():
                        corrected.append(word.replace(clean, fixed))
                        continue
            corrected.append(word)
        return " ".join(corrected)

    # ── تصحيح نص كامل ───────────────────────────────────────────────

    def correct_text(self, text: str) -> str:
        """
        تصحيح نص كامل كلمة بكلمة مع حفظ الكلمات المحمية + digit recognition.
        بديل متوافق مع src/correction.correct_text().
        """
        if not text or not text.strip():
            return text
        words = text.split()
        corrected = []
        for w in words:
            clean = w.strip(".,;:!?\"'()-")
            if clean and self._is_protected(clean):
                corrected.append(w)
                continue
            if clean:
                c, _ = self.auto_correct(clean)
                corrected.append(w.replace(clean, c))
            else:
                corrected.append(w)
        result = self.enhance_digit_recognition(" ".join(corrected))
        return result

    def spell_correct_word(self, word: str) -> str:
        """
        تصحيح سريع كلمة واحدة مع digit recognition.
        بديل متوافق مع src/correction.spell_correct_word().
        """
        word = word.strip()
        if not word:
            return ""
        if self._is_protected(word):
            return word
        corrected, _ = self.auto_correct(word)
        return self.enhance_digit_recognition(corrected)

    def get_protected_count(self) -> dict:
        """إرجاع عدد الكلمات المحمية لكل فئة."""
        return {
            "technical_keywords": len(TECHNICAL_KEYWORDS),
            "python_keywords": len(PYTHON_KEYWORDS),
            "custom_words": len(self._custom_protected),
            "total_protected": len(_PROTECTED_WORDS_LOWER),
        }
