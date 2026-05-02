"""
Tests for Arabic RTL Processing
=================================
Tests for right-to-left text processing, Arabic character detection,
reading order correction, and bidirectional text handling.

Based on modules.vision.text_reconstructor which provides RTL support.
"""

import pytest

from modules.vision.text_reconstructor import TextReconstructor


# ─── Arabic Character Detection Tests ────────────────────────────────

class TestArabicCharacterDetection:
    """Tests for Arabic character and text detection."""

    def test_arabic_letter_detection(self):
        """Test detection of individual Arabic letters."""
        assert TextReconstructor._is_arabic_text("م") is True
        assert TextReconstructor._is_arabic_text("ا") is True
        assert TextReconstructor._is_arabic_text("ب") is True
        assert TextReconstructor._is_arabic_text("ت") is True
        assert TextReconstructor._is_arabic_text("ث") is True

    def test_arabic_word_detection(self):
        """Test detection of Arabic words."""
        assert TextReconstructor._is_arabic_text("مرحبا") is True
        assert TextReconstructor._is_arabic_text("العالم") is True
        assert TextReconstructor._is_arabic_text("إسلام") is True
        assert TextReconstructor._is_arabic_text("كتاب") is True

    def test_arabic_sentence_detection(self):
        """Test detection of Arabic sentences."""
        assert TextReconstructor._is_arabic_text("مرحبا بالعالم") is True
        assert TextReconstructor._is_arabic_text("هذا نص عربي طويل") is True

    def test_latin_not_arabic(self):
        """Test that Latin text is not detected as Arabic."""
        assert TextReconstructor._is_arabic_text("Hello") is False
        assert TextReconstructor._is_arabic_text("World") is False
        assert TextReconstructor._is_arabic_text("ABC") is False

    def test_digits_not_arabic(self):
        """Test that digits are not detected as Arabic."""
        assert TextReconstructor._is_arabic_text("123") is False
        assert TextReconstructor._is_arabic_text("456789") is False

    def test_punctuation_not_arabic(self):
        """Test that punctuation is not detected as Arabic."""
        assert TextReconstructor._is_arabic_text("!@#$%") is False
        assert TextReconstructor._is_arabic_text(".") is False

    def test_empty_string(self):
        """Test empty string handling."""
        assert TextReconstructor._is_arabic_text("") is False

    def test_arabic_extended_unicode(self):
        """Test Arabic extended Unicode ranges."""
        # Arabic Presentation Forms
        assert TextReconstructor._is_arabic_text("ﺍ") is True  # U+FE8D
        # Arabic Supplement
        assert TextReconstructor._is_arabic_text("ݐ") is True  # U+0750

    def test_arabic_indic_digits(self):
        """Test Arabic-Indic digit detection."""
        assert TextReconstructor._is_arabic_text("٠١٢٣") is True  # U+0660-U+0663

    def test_mixed_text_detected_as_arabic(self):
        """Test mixed Arabic/Latin text is detected as Arabic."""
        assert TextReconstructor._is_arabic_text("Hello مرحبا") is True
        assert TextReconstructor._is_arabic_text("مرحبا World") is True


# ─── Latin Character Detection Tests ─────────────────────────────────

class TestLatinCharacterDetection:
    """Tests for Latin character detection."""

    def test_latin_uppercase(self):
        assert TextReconstructor._is_latin_text("HELLO") is True

    def test_latin_lowercase(self):
        assert TextReconstructor._is_latin_text("hello") is True

    def test_latin_mixed_case(self):
        assert TextReconstructor._is_latin_text("Hello World") is True

    def test_arabic_not_latin(self):
        assert TextReconstructor._is_latin_text("مرحبا") is False

    def test_empty_string(self):
        assert TextReconstructor._is_latin_text("") is False

    def test_digits_not_latin(self):
        assert TextReconstructor._is_latin_text("123") is False


# ─── RTL Direction Detection Tests ───────────────────────────────────

class TestRTLDetection:
    """Tests for RTL/LTR direction auto-detection."""

    def test_detect_rtl_for_arabic(self):
        """Test RTL detection for Arabic text."""
        reconstructor = TextReconstructor()
        words = [{"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20}]
        direction = reconstructor._detect_direction(words, "auto")
        assert direction == "rtl"

    def test_detect_ltr_for_english(self):
        """Test LTR detection for English text."""
        reconstructor = TextReconstructor()
        words = [{"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20}]
        direction = reconstructor._detect_direction(words, "auto")
        assert direction == "ltr"

    def test_detect_rtl_for_mixed_majority_arabic(self):
        """Test RTL detection for majority Arabic text."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20},
            {"text": "بالعالم", "x": 70, "y": 10, "w": 60, "h": 20},
            {"text": "Hello", "x": 10, "y": 40, "w": 40, "h": 20},
        ]
        direction = reconstructor._detect_direction(words, "auto")
        assert direction == "rtl"

    def test_detect_ltr_for_mixed_majority_english(self):
        """Test LTR detection for majority English text."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20},
            {"text": "World", "x": 70, "y": 10, "w": 50, "h": 20},
            {"text": "مرحبا", "x": 10, "y": 40, "w": 50, "h": 20},
        ]
        direction = reconstructor._detect_direction(words, "auto")
        assert direction == "ltr"

    def test_explicit_rtl(self):
        """Test explicit RTL direction."""
        reconstructor = TextReconstructor()
        words = [{"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20}]
        direction = reconstructor._detect_direction(words, "rtl")
        assert direction == "rtl"

    def test_explicit_ltr(self):
        """Test explicit LTR direction."""
        reconstructor = TextReconstructor()
        words = [{"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20}]
        direction = reconstructor._detect_direction(words, "ltr")
        assert direction == "ltr"

    def test_empty_words_defaults_ltr(self):
        """Test empty word list defaults to LTR."""
        reconstructor = TextReconstructor()
        direction = reconstructor._detect_direction([], "auto")
        assert direction == "ltr"


# ─── RTL Reading Order Tests ─────────────────────────────────────────

class TestRTLReadingOrder:
    """Tests for correct RTL reading order reconstruction."""

    def test_rtl_single_word(self):
        """Test RTL reconstruction of single Arabic word."""
        reconstructor = TextReconstructor()
        words = [{"text": "مرحبا", "x": 100, "y": 10, "w": 50, "h": 20}]
        result = reconstructor.reconstruct(words, direction="rtl")
        assert "مرحبا" in result

    def test_rtl_multiple_words(self):
        """Test RTL reconstruction of multiple Arabic words."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "مرحبا", "x": 100, "y": 10, "w": 50, "h": 20},
            {"text": "بالعالم", "x": 40, "y": 10, "w": 60, "h": 20},
        ]
        result = reconstructor.reconstruct(words, direction="rtl")
        assert "مرحبا" in result
        assert "بالعالم" in result

    def test_rtl_multiple_lines(self):
        """Test RTL reconstruction of multiple lines."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "السطر الأول", "x": 100, "y": 10, "w": 80, "h": 20},
            {"text": "السطر الثاني", "x": 100, "y": 50, "w": 80, "h": 20},
        ]
        result = reconstructor.reconstruct(words, direction="rtl")
        lines = result.split("\n")
        assert len(lines) == 2

    def test_ltr_ordering(self):
        """Test LTR reconstruction preserves left-to-right order."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20},
            {"text": "World", "x": 70, "y": 10, "w": 50, "h": 20},
        ]
        result = reconstructor.reconstruct(words, direction="ltr")
        assert "Hello" in result
        assert "World" in result

    def test_rtl_words_sorted_right_to_left(self):
        """Test that RTL words are ordered from right to left (high X to low X)."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "كلمة", "x": 100, "y": 100, "w": 50, "h": 20},
            {"text": "الكلمة", "x": 300, "y": 100, "w": 60, "h": 20},
            {"text": "السطر التالي", "x": 50, "y": 200, "w": 100, "h": 20},
        ]
        result = reconstructor.reconstruct(words, direction="rtl")
        # The word with x=300 (الكلمة) should appear first in the RTL result
        idx_right = result.find("الكلمة")
        idx_left = result.find("كلمة")
        assert idx_right < idx_left, "Rightmost word should appear first in RTL"


# ─── Mixed Text Processing Tests ─────────────────────────────────────

class TestMixedTextProcessing:
    """Tests for mixed Arabic/Latin text processing."""

    def test_mixed_paragraph_reconstruction(self):
        """Test reconstruction of mixed Arabic/Latin paragraph."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "Hello", "x": 10, "y": 10, "w": 40, "h": 20},
            {"text": "مرحبا", "x": 60, "y": 10, "w": 50, "h": 20},
        ]
        result = reconstructor.reconstruct_mixed_paragraph(words)
        assert len(result) > 0
        assert "Hello" in result or "مرحبا" in result

    def test_statistics_mixed(self):
        """Test statistics for mixed text."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20},
            {"text": "Hello", "x": 10, "y": 40, "w": 50, "h": 20},
            {"text": "بالعالم", "x": 10, "y": 70, "w": 60, "h": 20},
        ]
        stats = reconstructor.get_statistics(words)
        assert stats["total_words"] == 3
        assert stats["arabic_words"] == 2
        assert stats["english_words"] == 1
        assert stats["arabic_ratio"] == pytest.approx(2/3, abs=0.01)


# ─── Arabic Reshaping Tests ──────────────────────────────────────────

class TestArabicReshaping:
    """Tests for Arabic text reshaping and bidi."""

    def test_reshaping_with_libraries(self):
        """Test that reshaping works if libraries are available."""
        reconstructor = TextReconstructor()
        if reconstructor._has_reshaper and reconstructor._has_bidi:
            result = reconstructor._apply_arabic_reshaping("مرحبا")
            assert isinstance(result, str)
            assert len(result) > 0

    def test_reshaping_without_libraries(self):
        """Test that text is returned unchanged if libraries missing."""
        reconstructor = TextReconstructor()
        if not reconstructor._has_reshaper or not reconstructor._has_bidi:
            result = reconstructor._apply_arabic_reshaping("مرحبا")
            assert result == "مرحبا"

    def test_reshaping_empty(self):
        """Test reshaping empty text."""
        reconstructor = TextReconstructor()
        result = reconstructor._apply_arabic_reshaping("")
        assert result == ""

    def test_reconstruct_with_direction_rtl(self):
        """Test reconstruct_with_direction for RTL."""
        reconstructor = TextReconstructor()
        words = [{"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20}]
        result = reconstructor.reconstruct_with_direction(words, direction="rtl")
        assert "مرحبا" in result

    def test_reconstruct_with_direction_ltr(self):
        """Test reconstruct_with_direction for LTR."""
        reconstructor = TextReconstructor()
        words = [{"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20}]
        result = reconstructor.reconstruct_with_direction(words, direction="ltr")
        assert "Hello" in result

    def test_invalid_direction_falls_back(self):
        """Test invalid direction falls back to auto."""
        reconstructor = TextReconstructor()
        words = [{"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20}]
        result = reconstructor.reconstruct_with_direction(words, direction="invalid")
        assert "Hello" in result


# ─── Gap Calculation Tests ───────────────────────────────────────────

class TestGapCalculation:
    """Tests for word gap calculation."""

    def test_gap_rtl(self):
        """Test gap calculation for RTL text."""
        gap = TextReconstructor._calculate_gap(
            {"x": 100, "w": 50}, {"x": 40, "w": 50}, "rtl"
        )
        assert gap >= 0

    def test_gap_ltr(self):
        """Test gap calculation for LTR text."""
        gap = TextReconstructor._calculate_gap(
            {"x": 10, "w": 50}, {"x": 70, "w": 50}, "ltr"
        )
        assert gap >= 0

    def test_gap_overlapping(self):
        """Test gap for overlapping words."""
        gap = TextReconstructor._calculate_gap(
            {"x": 10, "w": 100}, {"x": 50, "w": 100}, "ltr"
        )
        assert gap == 0


# ─── Line Grouping Tests ─────────────────────────────────────────────

class TestRTLLineGrouping:
    """Tests for line grouping with RTL consideration."""

    def test_group_arabic_lines(self):
        """Test grouping Arabic words into lines."""
        reconstructor = TextReconstructor(line_threshold=15.0)
        words = [
            {"text": "مرحبا", "x": 200, "y": 10, "w": 50, "h": 20},
            {"text": "بالعالم", "x": 140, "y": 12, "w": 60, "h": 20},
            {"text": "في", "x": 100, "y": 50, "w": 30, "h": 20},
        ]
        lines = reconstructor._group_into_lines(words)
        assert len(lines) == 2
        assert len(lines[0]) == 2
        assert len(lines[1]) == 1


# ─── Run Tests ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
