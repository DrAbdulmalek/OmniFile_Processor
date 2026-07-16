"""
وحدة التقييم والقياس (Evaluation & Metrics Module)
====================================================
أدوات تقييم دقة التعرف على النصوص وقياس جودة النتائج.
Tools for evaluating OCR accuracy and measuring result quality.

OmniFile AI Processor - وحدة معالجة الملفات الذكية
"""

from modules.evaluation.metrics import (
    EvaluationResult,
    calculate_cer,
    calculate_wer,
    evaluate,
    evaluate_file,
)

__all__ = [
    "EvaluationResult",
    "calculate_cer",
    "calculate_wer",
    "evaluate",
    "evaluate_file",
]
