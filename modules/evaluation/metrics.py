"""
وحدة مقاييس تقييم دقة التعرف على النصوص (OCR Accuracy Evaluation Metrics)
=============================================================================
يوفر معدل خطأ الأحرف (CER) ومعدل خطأ الكلمات (WER) لقياس
دقة التعرف على النصوص مقارنة بالنص المرجعي.

Provides CER (Character Error Rate) and WER (Word Error Rate)
for measuring OCR accuracy against ground truth text.

المصدر: دمج من مشروع advanced-ocr
Source: Merged from advanced-ocr project

القدرات:
- دعم خاص للنصوص العربية (إزالة التشكيل، توحيد الأشكال)
- مقارنة بدون مكتبات خارجية (خوارزمية Levenshtein مدمجة)
- تقييم شامل مع درجات جودة

OmniFile AI Processor - وحدة معالجة الملفات الذكية
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """نتيجة تقييم دقة التعرف على النصوص / Result of OCR accuracy evaluation."""
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
        """الدقة الكلية كنسبة مئوية / Overall accuracy as percentage."""
        return (1.0 - self.cer) * 100

    @property
    def quality_grade(self) -> str:
        """تقدير جودة التعرف / Grade the OCR quality.

        حدود التقييم مقصودة بحيث تمثل نسبة 10% CER بداية المستوى
        "المقبول" بدلاً من المستوى "الجيد".
        """
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
        """إنشاء ملخص قابل للقراءة / Generate a human-readable summary."""
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
        """تحويل إلى قاموس / Serialize to dictionary."""
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


def calculate_cer(reference: str, hypothesis: str) -> tuple[float, int, int]:
    """
    حساب معدل خطأ الأحرف (Character Error Rate).

    CER = (S + D + I) / N
    حيث:
    - S = الاستبدالات / Substitutions
    - D = الحذف / Deletions
    - I = الإدراجات / Insertions
    - N = إجمالي الأحرف في المرجع / Total characters in reference

    يستخدم خوارزمية مسافة Levenshtein.
    Uses the Levenshtein distance algorithm.

    Args:
        reference: النص المرجعي / Ground truth text
        hypothesis: نص الناتج من OCR / OCR output text

    Returns:
        (cer, أخطاء, إجمالي_أحرف) / (cer, errors, total_chars)
    """
    # تطبيع النص: إزالة التشكيل، توحيد المسافات
    ref = _normalize_arabic(reference)
    hyp = _normalize_arabic(hypothesis)

    if not ref:
        return (0.0 if not hyp else 1.0, len(hyp), 0)

    edits, _, _ = _levenshtein_distance(ref, hyp)

    cer = edits / len(ref)
    return (cer, edits, len(ref))


def calculate_wer(reference: str, hypothesis: str) -> tuple[float, int, int]:
    """
    حساب معدل خطأ الكلمات (Word Error Rate).

    WER = (S + D + I) / N
    حيث N = إجمالي الكلمات في المرجع

    Args:
        reference: النص المرجعي / Ground truth text
        hypothesis: نص الناتج من OCR / OCR output text

    Returns:
        (wer, أخطاء, إجمالي_كلمات) / (wer, errors, total_words)
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
    تقييم شامل لنتائج التعرف / Comprehensive OCR evaluation.

    Args:
        reference: النص المرجعي / Ground truth text
        hypothesis: نص الناتج من OCR / OCR output text

    Returns:
        EvaluationResult مع CER و WER وتقييم الجودة
    """
    cer, char_errors, char_total = calculate_cer(reference, hypothesis)
    wer, word_errors, word_total = calculate_wer(reference, hypothesis)

    result = EvaluationResult(
        reference=reference,
        hypothesis=hypothesis,
        cer=cer,
        wer=wer,
        character_errors=char_errors,
        character_total=char_total,
        word_errors=word_errors,
        word_total=word_total,
    )

    logger.info(f"Evaluation: CER={cer:.2%}, WER={wer:.2%}, Grade={result.quality_grade}")
    return result


def evaluate_file(reference_path: str, hypothesis_path: str) -> EvaluationResult:
    """
    تقييم نتائج OCR مقابل ملف مرجعي / Evaluate OCR against a reference file.

    Args:
        reference_path: مسار ملف النص المرجعي / Path to ground truth file
        hypothesis_path: مسار ملف النتائج / Path to OCR output file

    Returns:
        EvaluationResult
    """
    with open(reference_path, "r", encoding="utf-8") as f:
        reference = f.read()

    with open(hypothesis_path, "r", encoding="utf-8") as f:
        hypothesis = f.read()

    return evaluate(reference, hypothesis)


def _normalize_arabic(text: Optional[str]) -> str:
    """
    تطبيع النص العربي للمقارنة / Normalize Arabic text for comparison.

    يزيل التشكيل (التاءات) ويوحد المتغيرات الشائعة
    لضمان ألا تضخم اختلافات OCR الطفيفة معدلات الخطأ.
    """
    if text is None:
        return ""

    if not text:
        return ""

    # إزالة التشكيل العربي
    diacritics = r"[\u064B-\u065F\u0670]"
    text = re.sub(diacritics, "", text)

    # توحيد أشكال الألف
    text = text.replace("إ", "ا").replace("أ", "ا").replace("ٱ", "ا")

    # توحيد الألف المقصورة
    text = text.replace("ى", "ي")

    # توحيد المسافات
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _levenshtein_distance(s1, s2) -> tuple[int, int, int]:
    """
    حساب مسافة Levenshtein / Calculate Levenshtein edit distance.

    Returns:
        (إجمالي_التعديلات, استبدالات, إدراجات_وحذف)
    """
    len1, len2 = len(s1), len(s2)

    if len1 == 0:
        return (len2, 0, len2)
    if len2 == 0:
        return (len1, 0, len1)

    # إنشاء مصفوفة المسافات
    d = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    for i in range(len1 + 1):
        d[i][0] = i
    for j in range(len2 + 1):
        d[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,       # حذف / Deletion
                d[i][j - 1] + 1,       # إدراج / Insertion
                d[i - 1][j - 1] + cost  # استبدال / Substitution
            )

    return (d[len1][len2], 0, 0)


# === Compatibility aliases for OmniFile_v500_Colab ===
# Notebook imports compute_cer / compute_wer — our functions return (cer, errors, total)
def compute_cer(reference: str, hypothesis: str) -> float:
    """معدل خطأ الأحرف (CER) — واجهة متوافقة مع الـ notebook."""
    cer, _, _ = calculate_cer(reference, hypothesis)
    return cer

def compute_wer(reference: str, hypothesis: str) -> float:
    """معدل خطأ الكلمات (WER) — واجهة متوافقة مع الـ notebook."""
    wer, _, _ = calculate_wer(reference, hypothesis)
    return wer
