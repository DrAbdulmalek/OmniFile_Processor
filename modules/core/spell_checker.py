"""
modules/core/spell_checker.py — Hybrid Spell Checker v5.0
مدقق إملائي هجين يكتشف اللغة تلقائياً ويدعم العربية/الإنجليزية/الألمانية
"""
import json, logging, re
from difflib import get_close_matches
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
ARABIC_FIXES_PATH = "data/arabic_fixes.json"
_AR_RE = re.compile(r'[\u0600-\u06ff]')
_EN_RE = re.compile(r'[a-zA-Z]')


class HybridSpellChecker:
    """مدقق إملائي هجين — يكتشف اللغة تلقائياً من النص المكتوب."""

    def __init__(self, arabic_fixes_path: str = ARABIC_FIXES_PATH) -> None:
        self._fixes_path = Path(arabic_fixes_path)
        self._arabic_fixes: dict = {}
        self._spell_en = self._spell_ar = self._spell_de = None
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
                setattr(self, attr, SpellChecker(language=lang, distance=1))
            except Exception:
                setattr(self, attr, False)
        obj = getattr(self, attr)
        return obj if obj else None

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
        """اقتراحات تصحيح من ثلاثة مصادر: fixes + DB + spellchecker."""
        if not word or not word.strip():
            return []
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
        """تصحيح تلقائي + كشف لغة. Returns: (corrected, lang)"""
        lang = self.detect_language(word)
        if lang in ("ar", "mixed") and word in self._arabic_fixes:
            return self._arabic_fixes[word], lang
        sugg = self.get_suggestions(word, lang=lang, n=1)
        return (sugg[0] if sugg else word), lang

    def check_text(self, text: str) -> dict:
        """فحص نص كامل. Returns: {lang, words: [...], total}"""
        lang = self.detect_language(text)
        results = []
        for w in text.split():
            corrected, _ = self.auto_correct(w)
            results.append({
                "word": w, "corrected": corrected,
                "suggestions": self.get_suggestions(w, lang=lang, n=3),
                "changed": corrected != w,
            })
        return {"lang": lang, "words": results, "total": len(results)}
