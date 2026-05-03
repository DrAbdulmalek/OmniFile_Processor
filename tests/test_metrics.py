"""
Tests for OCR Evaluation Metrics (CER/WER)
============================================
Tests the Character Error Rate and Word Error Rate calculation module.

Based on the evaluation module from advanced-ocr/evaluation/metrics.py,
adapted for OmniFile_Processor's structure.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ─── Implementation from evaluation/metrics.py for testing ────────────

@dataclass
class EvaluationResult:
    """Result of OCR accuracy evaluation."""
    reference: str
    hypothesis: str
    cer: float = 0.0
    wer: float = 0.0
    character_errors: int = 0
    character_total: int = 0
    word_errors: int = 0
    word_total: int = 0
    details: dict = field(default_factory=dict)

    @property
    def accuracy_percent(self) -> float:
        """Overall accuracy as percentage."""
        return (1.0 - self.cer) * 100

    @property
    def quality_grade(self) -> str:
        """Grade the OCR quality."""
        if self.cer <= 0.02:
            return "A+ (Near Perfect)"
        elif self.cer <= 0.05:
            return "A (Excellent)"
        elif self.cer < 0.10:
            return "B (Good)"
        elif self.cer <= 0.20:
            return "C (Acceptable)"
        elif self.cer <= 0.40:
            return "D (Poor)"
        else:
            return "F (Unusable)"

    def summary(self) -> str:
        """Generate a human-readable summary."""
        return (
            f"OCR Evaluation Results\n"
            f"{'=' * 40}\n"
            f"CER (Character Error Rate): {self.cer:.2%}\n"
            f"WER (Word Error Rate): {self.wer:.2%}\n"
            f"Character Accuracy: {self.accuracy_percent:.1f}%\n"
            f"Characters: {self.character_total} total, {self.character_errors} errors\n"
            f"Words: {self.word_total} total, {self.word_errors} errors\n"
            f"Quality Grade: {self.quality_grade}"
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "cer": round(self.cer, 4),
            "wer": round(self.wer, 4),
            "accuracy_percent": round(self.accuracy_percent, 2),
            "character_errors": self.character_errors,
            "character_total": self.character_total,
            "word_errors": self.word_errors,
            "word_total": self.word_total,
            "quality_grade": self.quality_grade,
        }


def _normalize_arabic(text: str) -> str:
    """Normalize Arabic text for comparison."""
    if not text:
        return ""
    diacritics = r"[\u064B-\u065F\u0670]"
    text = re.sub(diacritics, "", text)
    text = text.replace("إ", "ا").replace("أ", "ا").replace("ٱ", "ا")
    text = text.replace("ى", "ي")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _levenshtein_distance(s1, s2) -> tuple[int, int, int]:
    """Calculate Levenshtein edit distance."""
    len1, len2 = len(s1), len(s2)
    if len1 == 0:
        return (len2, 0, len2)
    if len2 == 0:
        return (len1, 0, len1)

    d = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        d[i][0] = i
    for j in range(len2 + 1):
        d[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost,
            )

    return (d[len1][len2], 0, 0)


def calculate_cer(reference: str, hypothesis: str) -> tuple[float, int, int]:
    """
    Calculate Character Error Rate (CER).

    Returns:
        (cer, errors, total_chars) tuple
    """
    ref = _normalize_arabic(reference)
    hyp = _normalize_arabic(hypothesis)

    if not ref:
        return (0.0 if not hyp else 1.0, len(hyp), 0)

    edits, _, _ = _levenshtein_distance(ref, hyp)
    cer = edits / len(ref)
    return (cer, edits, len(ref))


def calculate_wer(reference: str, hypothesis: str) -> tuple[float, int, int]:
    """
    Calculate Word Error Rate (WER).

    Returns:
        (wer, errors, total_words) tuple
    """
    ref = _normalize_arabic(reference)
    hyp = _normalize_arabic(hypothesis)

    ref_words = ref.split()
    hyp_words = hyp.split()

    if not ref_words:
        return (0.0 if not hyp_words else 1.0, len(hyp_words), 0)

    edits, _, _ = _levenshtein_distance(ref_words, hyp_words)
    wer = edits / len(ref_words)
    return (wer, edits, len(ref_words))


def evaluate(reference: str, hypothesis: str) -> EvaluationResult:
    """
    Perform comprehensive OCR evaluation.

    Returns:
        EvaluationResult with CER, WER, and quality assessment
    """
    cer, char_errors, char_total = calculate_cer(reference, hypothesis)
    wer, word_errors, word_total = calculate_wer(reference, hypothesis)

    return EvaluationResult(
        reference=reference,
        hypothesis=hypothesis,
        cer=cer,
        wer=wer,
        character_errors=char_errors,
        character_total=char_total,
        word_errors=word_errors,
        word_total=word_total,
    )


# ─── Test Classes ────────────────────────────────────────────────────

class TestArabicNormalization:
    """Tests for Arabic text normalization."""

    def test_remove_diacritics(self):
        """Test that diacritics are removed."""
        text = "مَرْحَبًا"
        normalized = _normalize_arabic(text)
        assert "َ" not in normalized
        assert "ْ" not in normalized
        assert "ً" not in normalized

    def test_normalize_alef_variants(self):
        """Test Alef variant normalization."""
        assert _normalize_arabic("إسلام") == "اسلام"
        assert _normalize_arabic("أحمد") == "احمد"
        assert _normalize_arabic("ٱلسلام") == "السلام"

    def test_normalize_alef_maksura(self):
        """Test Alef Maksura normalization."""
        assert _normalize_arabic("موسى") == "موسي"

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        assert _normalize_arabic("مرحبا  بالعالم") == "مرحبا بالعالم"

    def test_empty_string(self):
        assert _normalize_arabic("") == ""
        assert _normalize_arabic(None) == ""

    def test_no_change_latin(self):
        """Test Latin text is unchanged."""
        assert _normalize_arabic("Hello World") == "Hello World"


class TestLevenshteinDistance:
    """Tests for Levenshtein edit distance."""

    def test_identical_strings(self):
        edits, _, _ = _levenshtein_distance("hello", "hello")
        assert edits == 0

    def test_empty_strings(self):
        edits, _, _ = _levenshtein_distance("", "")
        assert edits == 0

    def test_one_empty(self):
        edits, _, _ = _levenshtein_distance("abc", "")
        assert edits == 3

    def test_single_substitution(self):
        edits, _, _ = _levenshtein_distance("cat", "bat")
        assert edits == 1

    def test_single_insertion(self):
        edits, _, _ = _levenshtein_distance("cat", "cats")
        assert edits == 1

    def test_single_deletion(self):
        edits, _, _ = _levenshtein_distance("cats", "cat")
        assert edits == 1

    def test_arabic_strings(self):
        edits, _, _ = _levenshtein_distance("مرحبا", "مرحبا")
        assert edits == 0

    def test_arabic_with_error(self):
        edits, _, _ = _levenshtein_distance("مرحبا", "مرحبا ")
        assert edits == 1


class TestCER:
    """Tests for Character Error Rate."""

    def test_perfect_match(self):
        cer, errors, total = calculate_cer("مرحبا", "مرحبا")
        assert cer == 0.0
        assert errors == 0
        assert total == 5

    def test_cer_with_errors(self):
        cer, errors, total = calculate_cer("مرحبا", "محبا")
        assert cer > 0
        assert errors > 0

    def test_cer_complete_wrong(self):
        cer, errors, total = calculate_cer("مرحبا", "xxxxx")
        assert cer == 1.0
        assert errors == 5

    def test_empty_reference(self):
        cer, errors, total = calculate_cer("", "مرحبا")
        assert cer == 1.0
        assert errors == 5
        assert total == 0

    def test_empty_hypothesis(self):
        cer, errors, total = calculate_cer("مرحبا", "")
        assert cer == 1.0
        assert errors == 5
        assert total == 5

    def test_both_empty(self):
        cer, errors, total = calculate_cer("", "")
        assert cer == 0.0
        assert errors == 0

    def test_cer_english(self):
        cer, errors, total = calculate_cer("hello world", "hello world")
        assert cer == 0.0

    def test_cer_with_diacritics(self):
        """Test that diacritics don't inflate CER."""
        cer1, _, _ = calculate_cer("مرحبا", "مرحبا")
        cer2, _, _ = calculate_cer("مَرْحَبًا", "مرحبا")
        assert cer1 == cer2 == 0.0


class TestWER:
    """Tests for Word Error Rate."""

    def test_perfect_match(self):
        wer, errors, total = calculate_wer("مرحبا بالعالم", "مرحبا بالعالم")
        assert wer == 0.0
        assert errors == 0
        assert total == 2

    def test_wer_with_errors(self):
        wer, errors, total = calculate_wer("مرحبا بالعالم", "مرحبا العالم")
        assert wer > 0
        assert errors > 0

    def test_wer_complete_wrong(self):
        wer, errors, total = calculate_wer("مرحبا بالعالم", "كلمة أخرى")
        assert wer == 1.0
        assert errors == 2

    def test_empty_reference(self):
        wer, errors, total = calculate_wer("", "مرحبا")
        assert wer == 1.0
        assert errors == 1

    def test_empty_hypothesis(self):
        wer, errors, total = calculate_wer("مرحبا", "")
        assert wer == 1.0
        assert errors == 1

    def test_both_empty(self):
        wer, errors, total = calculate_wer("", "")
        assert wer == 0.0
        assert errors == 0

    def test_wer_extra_words(self):
        wer, errors, total = calculate_wer("مرحبا", "مرحبا بالعالم")
        assert wer > 0


class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def test_accuracy_percent(self):
        result = EvaluationResult(reference="test", hypothesis="test", cer=0.1)
        assert result.accuracy_percent == 90.0

    def test_quality_grade_a_plus(self):
        result = EvaluationResult(reference="test", hypothesis="test", cer=0.01)
        assert result.quality_grade == "A+ (Near Perfect)"

    def test_quality_grade_a(self):
        result = EvaluationResult(reference="test", hypothesis="test", cer=0.03)
        assert result.quality_grade == "A (Excellent)"

    def test_quality_grade_b(self):
        result = EvaluationResult(reference="test", hypothesis="test", cer=0.07)
        assert result.quality_grade == "B (Good)"

    def test_quality_grade_c(self):
        result = EvaluationResult(reference="test", hypothesis="test", cer=0.15)
        assert result.quality_grade == "C (Acceptable)"

    def test_quality_grade_d(self):
        result = EvaluationResult(reference="test", hypothesis="test", cer=0.30)
        assert result.quality_grade == "D (Poor)"

    def test_quality_grade_f(self):
        result = EvaluationResult(reference="test", hypothesis="test", cer=0.50)
        assert result.quality_grade == "F (Unusable)"

    def test_to_dict(self):
        result = EvaluationResult(
            reference="test", hypothesis="test",
            cer=0.1, wer=0.2,
            character_errors=1, character_total=10,
            word_errors=1, word_total=5,
        )
        d = result.to_dict()
        assert d["cer"] == 0.1
        assert d["wer"] == 0.2
        assert d["accuracy_percent"] == 90.0
        assert d["quality_grade"] == "C (Acceptable)"

    def test_summary(self):
        result = EvaluationResult(reference="test", hypothesis="test", cer=0.05)
        summary = result.summary()
        assert "CER" in summary
        assert "WER" in summary
        assert "Quality Grade" in summary


class TestEvaluateFunction:
    """Tests for the comprehensive evaluate() function."""

    def test_perfect_match(self):
        result = evaluate("مرحبا بالعالم", "مرحبا بالعالم")
        assert result.cer == 0.0
        assert result.wer == 0.0
        assert result.quality_grade == "A+ (Near Perfect)"

    def test_poor_match(self):
        result = evaluate("مرحبا بالعالم", "م ح ب ا")
        assert result.cer > 0.5
        assert "F" in result.quality_grade

    def test_fields_populated(self):
        result = evaluate("Hello World", "Hello World")
        assert result.character_total == len("Hello World")
        assert result.word_total == 2
        assert result.character_errors == 0
        assert result.word_errors == 0

    def test_mixed_arabic_english(self):
        result = evaluate("Hello مرحبا", "Hello مرحبا")
        assert result.cer == 0.0
        assert result.wer == 0.0


# ─── Run Tests ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
