"""
modules/core/protected_vocab.py
═══════════════════════════════
قاموس الكلمات المحمية من التصحيح الإملائي الخاطئ
==================================================
يحمي:
  - الكلمات البرمجية (Python keywords + builtins)
  - المصطلحات التقنية (OCR, API, GPU, LoRA, ...)
  - الكلمات المخصصة من ملف JSON قابل للتعديل

يُستخدم من: HybridSpellChecker + src/correction.py
مصدر الفكرة: src/correction.py (TECHNICAL_KEYWORDS) — مُوحَّد هنا

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import json
import logging
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

_CUSTOM_JSON = Path("data/protected_words.json")

# ── كلمات بايثون المحجوزة ─────────────────────────────────────────
PYTHON_KEYWORDS: frozenset[str] = frozenset({
    # كلمات محجوزة
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
    # دوال مدمجة شائعة
    "print", "input", "len", "range", "type", "int", "str", "float",
    "list", "dict", "set", "tuple", "bool", "open", "super",
    "self", "cls", "__init__", "__repr__", "__main__", "__name__",
    "args", "kwargs", "append", "extend", "pop", "sort", "join",
    "split", "strip", "format", "replace", "lower", "upper",
    "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "isinstance", "issubclass", "hasattr", "getattr", "setattr",
    "module", "package",
})

# ── مصطلحات تقنية (من src/correction.py) ────────────────────────
TECHNICAL_KEYWORDS: frozenset[str] = frozenset({
    # OCR & ML
    "ocr", "trocr", "easyocr", "tesseract", "paddleocr",
    "lora", "peft", "qlora", "finetune", "finetuning",
    "transformers", "huggingface", "pytorch", "tensorflow",
    "onnx", "bert", "gpt", "llm", "tokenizer", "embedding",
    # برمجة عامة
    "python", "json", "csv", "yaml", "markdown", "html", "xml",
    "api", "rest", "http", "url", "sql", "sqlite", "database",
    "git", "github", "clone", "commit", "push", "pull", "merge",
    "docker", "dockerfile", "colab", "jupyter", "notebook",
    "dataframe", "numpy", "pandas", "matplotlib", "sklearn",
    "batch", "epoch", "loss", "gradient", "optimizer", "scheduler",
    "encoder", "decoder", "attention", "transformer",
    # أجهزة
    "gpu", "cpu", "ram", "rom", "cuda", "tpu", "dpi",
    # اختصارات
    "repl", "etl", "cli", "gui", "sdk", "ide",
    "regex", "utf", "ascii", "unicode",
    "scraping", "parsing", "preprocessing",
    "checkpoint", "inference", "pipeline",
})


class ProtectedVocab:
    """
    قاموس الكلمات المحمية — Singleton.

    يُدمج:
      PYTHON_KEYWORDS + TECHNICAL_KEYWORDS + كلمات مخصصة (JSON)

    مثال:
        vocab = ProtectedVocab()
        vocab.is_protected("isinstance")   # True
        vocab.is_protected("مرحبا")        # False
        vocab.add("MyLibName")
        vocab.save()
    """

    _instance: "ProtectedVocab | None" = None

    def __new__(cls) -> "ProtectedVocab":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._custom: set[str] = set()
        self._cache:  set[str] = set()
        self._load_custom()
        self._rebuild()
        self._initialized = True

    # ── تحميل وحفظ ──────────────────────────────────────────────────

    def _load_custom(self) -> None:
        try:
            if _CUSTOM_JSON.exists():
                data = json.loads(_CUSTOM_JSON.read_text(encoding="utf-8"))
                self._custom = set(data.get("words", []))
                logger.debug("ProtectedVocab: loaded %d custom words", len(self._custom))
        except Exception as e:
            logger.warning("ProtectedVocab load error: %s", e)

    def save(self) -> None:
        """حفظ الكلمات المخصصة إلى JSON."""
        _CUSTOM_JSON.parent.mkdir(parents=True, exist_ok=True)
        _CUSTOM_JSON.write_text(
            json.dumps({"words": sorted(self._custom)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("ProtectedVocab: saved %d custom words", len(self._custom))

    def _rebuild(self) -> None:
        """إعادة بناء الـ cache الداخلي."""
        self._cache = (
            {w.lower() for w in PYTHON_KEYWORDS}
            | {w.lower() for w in TECHNICAL_KEYWORDS}
            | {w.lower() for w in self._custom}
        )

    # ── الواجهة العامة ───────────────────────────────────────────────

    def is_protected(self, word: str) -> bool:
        """هل الكلمة محمية من التصحيح؟"""
        return bool(word) and word.lower() in self._cache

    def add(self, *words: str) -> None:
        """إضافة كلمات للحماية."""
        for w in words:
            if w.strip():
                self._custom.add(w.strip())
        self._rebuild()

    def add_many(self, words: Iterable[str]) -> int:
        """إضافة قائمة كلمات. Returns عدد المضافة."""
        before = len(self._custom)
        for w in words:
            if w.strip():
                self._custom.add(w.strip())
        self._rebuild()
        return len(self._custom) - before

    def remove(self, word: str) -> bool:
        """إزالة كلمة مخصصة. Returns True إذا أُزيلت."""
        if word in self._custom:
            self._custom.discard(word)
            self._rebuild()
            return True
        return False

    def stats(self) -> dict:
        return {
            "python_keywords":    len(PYTHON_KEYWORDS),
            "technical_keywords": len(TECHNICAL_KEYWORDS),
            "custom_words":       len(self._custom),
            "total":              len(self._cache),
        }

    def load_into_spellchecker(self, sc) -> None:
        """تحميل الكلمات المحمية في قاموس pyspellchecker لمنع تصحيحها."""
        try:
            words = list(self._cache)
            sc.word_frequency.load_words(words)
            logger.debug("ProtectedVocab: loaded %d words into spellchecker", len(words))
        except Exception as e:
            logger.warning("ProtectedVocab.load_into_spellchecker: %s", e)

    @classmethod
    def reset(cls) -> None:
        """إعادة تعيين الـ singleton (للاختبار)."""
        cls._instance = None


# ── Singleton جاهز للاستيراد ─────────────────────────────────────
vocab = ProtectedVocab()
