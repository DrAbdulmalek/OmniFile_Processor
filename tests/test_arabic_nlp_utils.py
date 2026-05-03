"""
اختبارات وحدة الأدوات اللغوية العربية — arabic_nlp_utils.py
==============================================================
تختبر الدوال الأساسية:
- normalize_for_comparison(): إزالة التشكيل وتوحيد الأحرف
- arabic_normalized_similarity(): مقارنة نصوص عربية مع normalized
- similarity_report(): تقرير تشابه مفصّل مع توصيات
"""

import pytest
from modules.nlp.arabic_nlp_utils import (
    normalize_for_comparison,
    arabic_normalized_similarity,
    similarity_report,
)


class TestNormalizeForComparison:
    """اختبارات دالة التطبيع normalize_for_comparison()"""

    def test_normalize_removes_diacritics(self):
        """التحقق من إزالة التشكيل (فتحة، ضمة، كسرة، شدة، تنوين)"""
        assert normalize_for_comparison("الطَّبيب") == normalize_for_comparison("الطبيب")
        assert normalize_for_comparison("كِتابٌ") == normalize_for_comparison("كتاب")

    def test_normalize_unifies_alef(self):
        """التحقق من توحيد أشكال الألف (أ، إ، ا)"""
        assert normalize_for_comparison("أحمد") == normalize_for_comparison("احمد")
        assert normalize_for_comparison("إسلام") == normalize_for_comparison("اسلام")

    def test_normalize_unifies_taa_marbuta(self):
        """التحقق من توحيد التاء المربوطة والهاء"""
        assert normalize_for_comparison("فاطمة") == normalize_for_comparison("فاطمه")

    def test_normalize_empty(self):
        """التحقق من معالجة السلاسل الفارغة"""
        assert normalize_for_comparison("") == ""

    def test_normalize_none(self):
        """التحقق من معالجة القيم الفارغة None"""
        assert normalize_for_comparison(None) == ""

    def test_normalize_whitespace(self):
        """التحقق من معالجة المسافات الزائدة"""
        result = normalize_for_comparison("  مرحبا   بالعالم  ")
        assert "  " not in result

    def test_normalize_numbers_unchanged(self):
        """التحقق من أن الأرقام تبقى كما هي"""
        assert normalize_for_comparison("123") == "123"
        assert normalize_for_comparison("العام 2026") == normalize_for_comparison("العام 2026")


class TestArabicNormalizedSimilarity:
    """اختبارات دالة التشابه arabic_normalized_similarity()"""

    def test_similarity_identical(self):
        """نصوص متطابقة = تشابه 100%"""
        assert arabic_normalized_similarity("مرحبا", "مرحبا") == 1.0

    def test_similarity_diacritics(self):
        """نصوص مختلفة بالتشكيل فقط = تشابه عالٍ جداً"""
        sim = arabic_normalized_similarity("الطَّبيبُ", "الطبيب")
        assert sim >= 0.95, f"Expected >= 0.95, got {sim}"

    def test_similarity_completely_different(self):
        """نصوص مختلفة تماماً = تشابه منخفض"""
        sim = arabic_normalized_similarity("مرحبا بالعالم", "السماء زرقاء جميلة")
        assert sim < 0.5, f"Expected < 0.5, got {sim}"

    def test_similarity_empty_strings(self):
        """سلاسل فارغة = تشابه 1.0 أو 0.0 حسب التعريف"""
        result = arabic_normalized_similarity("", "")
        assert result in (0.0, 1.0)

    def test_similarity_case_insensitive_latin(self):
        """التحقق من عدم تأثر النصوص اللاتينية بحالة الأحرف"""
        sim = arabic_normalized_similarity("Hello World", "hello world")
        assert sim >= 0.95, f"Expected >= 0.95 for case-insensitive Latin, got {sim}"


class TestSimilarityReport:
    """اختبارات دالة التقرير similarity_report()"""

    def test_report_structure(self):
        """التحقق من هيكل التقرير المُعاد"""
        r = similarity_report("النص الأول", "النص الثاني")
        assert "raw_similarity" in r
        assert "normalized_similarity" in r
        assert "approved" in r
        assert "recommendation" in r

    def test_report_normalized_range(self):
        """التحقق من أن التشابه المُطبع في النطاق [0, 1]"""
        r = similarity_report("النص الأول", "النص الثاني")
        assert 0.0 <= r["normalized_similarity"] <= 1.0

    def test_report_threshold_approved(self):
        """نصوص متطابقة مع عتبة 0.9 = موافقة"""
        r = similarity_report("مرحبا", "مرحبا", threshold=0.9)
        assert r["approved"] is True

    def test_report_threshold_rejected(self):
        """نصوص مختلفة جداً مع عتبة عالية = رفض"""
        r = similarity_report("مرحبا", "السماء زرقاء جميلة اليوم والطقس رائع", threshold=0.9)
        assert r["approved"] is False

    def test_report_custom_threshold(self):
        """التحقق من احترام عتبة مخصصة"""
        r_low = similarity_report("مرحبا", "مرحبا بك", threshold=0.5)
        r_high = similarity_report("مرحبا", "مرحبا بك", threshold=0.99)
        # العتبة المنخفضة أسهل في الموافقة
        assert r_low["approved"] is True or r_low["normalized_similarity"] >= 0.5
        # العتبة العالية أصعب
        assert r_high["approved"] is r_high["normalized_similarity"] >= 0.99

    def test_report_has_recommendation_text(self):
        """التحقق من أن التوصية تحتوي على نص مفيد"""
        r = similarity_report("نص قصير", "نص آخر مختلف تماماً")
        assert isinstance(r["recommendation"], str)
        assert len(r["recommendation"]) > 0
