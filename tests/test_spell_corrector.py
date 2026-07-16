"""
اختبارات المصحح الإملائي
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestSpellCorrector:
    """اختبارات المصحح الإملائي."""

    def test_import(self):
        """اختبار استيراد المصحح."""
        from modules.nlp.spell_corrector import SpellCorrector
        assert SpellCorrector is not None

    def test_initialization(self):
        """اختبار التهيئة."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()
        assert corrector is not None

    def test_protected_python_keywords(self):
        """اختبار حماية كلمات Python."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()

        keywords = ["def", "class", "import", "return", "if", "else", "for"]
        for kw in keywords:
            result = corrector.correct_word(kw)
            assert result == kw, f"الكلمة المحمية '{kw}' تم تصحيحها خطأً إلى '{result}'"

    def test_protected_module_names(self):
        """اختبار حماية أسماء الوحدات."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()

        modules = ["numpy", "pandas", "torch", "flask", "django"]
        for mod in modules:
            result = corrector.correct_word(mod)
            assert result == mod

    def test_skip_numbers(self):
        """اختبار تخطي الأرقام."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()

        assert corrector.correct_word("123") == "123"
        assert corrector.correct_word("3.14") == "3.14"
        assert corrector.correct_word("100%") == "100%"

    def test_skip_empty(self):
        """اختبار تخطي النصوص الفارغة."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()

        assert corrector.correct_word("") == ""
        assert corrector.correct_word(" ") == " "

    def test_correct_text_returns_dict(self):
        """اختبار أن correct_text يعيد قاموساً."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()

        result = corrector.correct_text("Hello World")
        assert isinstance(result, dict)
        assert "corrected_text" in result
        assert "corrections" in result
        assert "total_corrections" in result

    def test_correct_text_empty(self):
        """اختبار تصحيح نص فارغ."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()

        result = corrector.correct_text("")
        assert result["corrected_text"] == ""
        assert result["total_corrections"] == 0

    def test_learn_correction(self):
        """اختبار تعلم تصحيح جديد."""
        from modules.nlp.spell_corrector import SpellCorrector
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            tmp_file = f.name

        try:
            corrector = SpellCorrector(correction_file=tmp_file)
            corrector.learn_correction("teh", "the")
            corrector.learn_correction("teh", "the")

            # بعد تعلمين نفس التصحيح
            learned = corrector._get_learned_correction("teh")
            # min_votes default = 2, so after 2 learns it should work
            assert learned == "the"
        finally:
            os.unlink(tmp_file) if os.path.exists(tmp_file) else None

    def test_is_available(self):
        """اختبار فحص التوفر."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()

        availability = corrector.is_available()
        assert isinstance(availability, dict)
        assert "english" in availability
        assert "arabic" in availability
        assert "learned" in availability

    def test_protected_terms_management(self):
        """اختبار إدارة المصطلحات المحمية."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()

        # إضافة مصطلح
        corrector.add_protected_term("myCustomTerm")
        assert "myCustomTerm" in corrector.get_protected_terms()

        # إزالته
        assert corrector.remove_protected_term("myCustomTerm") is True
        assert "myCustomTerm" not in corrector.get_protected_terms()

    def test_cannot_remove_python_keyword(self):
        """اختبار عدم القدرة على إزالة كلمة Python محجوزة."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()

        assert corrector.remove_protected_term("def") is False
