"""
اختبارات ملخص النصوص
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestTextSummarizer:
    """اختبارات ملخص النصوص."""

    def test_import(self):
        """اختبار استيراد الملخص."""
        from modules.nlp.summarizer import TextSummarizer
        assert TextSummarizer is not None

    def test_initialization(self):
        """اختبار التهيئة."""
        from modules.nlp.summarizer import TextSummarizer
        summarizer = TextSummarizer()
        assert summarizer is not None

    def test_detect_language_english(self):
        """اختبار كشف اللغة الإنجليزية."""
        from modules.nlp.summarizer import TextSummarizer
        assert TextSummarizer._detect_language("Hello World") == "en"

    def test_detect_language_arabic(self):
        """اختبار كشف اللغة العربية."""
        from modules.nlp.summarizer import TextSummarizer
        assert TextSummarizer._detect_language("مرحبا بالعالم") == "ar"

    def test_detect_language_german(self):
        """اختبار كشف اللغة الألمانية."""
        from modules.nlp.summarizer import TextSummarizer
        assert TextSummarizer._detect_language("Grüß Gott") == "de"

    def test_summarize_empty_text(self):
        """اختبار تلخيص نص فارغ."""
        from modules.nlp.summarizer import TextSummarizer
        summarizer = TextSummarizer()

        result = summarizer.summarize("")
        assert result["summary"] == ""
        assert result["original_length"] == 0

    def test_summarize_short_text(self):
        """اختبار تلخيص نص قصير (يجب أن يُرجع النص كما هو)."""
        from modules.nlp.summarizer import TextSummarizer
        summarizer = TextSummarizer()

        short_text = "Short text."
        result = summarizer.summarize(short_text)
        assert result["summary"] == short_text
        assert result.get("reason") == "text_too_short"

    def test_summarize_returns_dict(self, sample_text_en):
        """اختبار أن summarize يعيد قاموساً."""
        from modules.nlp.summarizer import TextSummarizer
        summarizer = TextSummarizer()

        result = summarizer.summarize(sample_text_en)
        assert isinstance(result, dict)
        assert "summary" in result
        assert "original_length" in result
        assert "summary_length" in result
        assert "compression_ratio" in result
        assert "language" in result

    def test_summarize_detects_language(self, sample_text_ar):
        """اختبار كشف اللغة أثناء التلخيص."""
        from modules.nlp.summarizer import TextSummarizer
        summarizer = TextSummarizer()

        result = summarizer.summarize(sample_text_ar)
        assert result["language"] == "ar"

    def test_get_available_models(self):
        """اختبار قائمة النماذج المتاحة."""
        from modules.nlp.summarizer import TextSummarizer
        summarizer = TextSummarizer()

        en_models = summarizer.get_available_models("en")
        assert isinstance(en_models, list)
        assert len(en_models) > 0

    def test_clear_cache(self):
        """اختبار مسح الكاش."""
        from modules.nlp.summarizer import TextSummarizer
        summarizer = TextSummarizer()

        summarizer._cache = {"key": {"summary": "test"}}
        summarizer.clear_cache()
        assert len(summarizer._cache) == 0

    def test_is_available(self):
        """اختبار فحص التوفر."""
        from modules.nlp.summarizer import TextSummarizer
        summarizer = TextSummarizer()

        available = summarizer.is_available()
        assert isinstance(available, bool)
