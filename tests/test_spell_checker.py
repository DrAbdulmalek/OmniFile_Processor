"""Tests for modules.core.spell_checker.HybridSpellChecker"""
import pytest
import json

class TestHybridSpellChecker:
    """Test HybridSpellChecker with temp arabic_fixes."""
    
    def _make_checker(self, tmp_path):
        from modules.core.spell_checker import HybridSpellChecker
        fixes_path = str(tmp_path / "arabic_fixes.json")
        Path(fixes_path).write_text(
            json.dumps({"الاختبار": "الاختبار"}), encoding="utf-8"
        )
        return HybridSpellChecker(arabic_fixes_path=fixes_path)
    
    def test_detect_language_arabic(self, tmp_path):
        checker = self._make_checker(tmp_path)
        assert checker.detect_language("مرحبا بالعالم") == "ar"
    
    def test_detect_language_english(self, tmp_path):
        checker = self._make_checker(tmp_path)
        assert checker.detect_language("hello world") == "en"
    
    def test_protected_word(self, tmp_path):
        checker = self._make_checker(tmp_path)
        assert checker.is_protected_word("def") is True
        assert checker.is_protected_word("normalword") is False
    
    def test_add_protected_words(self, tmp_path):
        checker = self._make_checker(tmp_path)
        checker.add_protected_words(["my_term"])
        assert checker.is_protected_word("my_term") is True
    
    def test_check_text(self, tmp_path):
        checker = self._make_checker(tmp_path)
        result = checker.check_text("hello world")
        assert "lang" in result
        assert "words" in result
    
    def test_enhance_digit_recognition(self, tmp_path):
        checker = self._make_checker(tmp_path)
        # Should handle digit-like OCR errors
        result = checker.enhance_digit_recognition("5mg")
        assert isinstance(result, str)
    
    def test_reload_fixes(self, tmp_path):
        checker = self._make_checker(tmp_path)
        checker.reload_fixes()  # Should not raise
