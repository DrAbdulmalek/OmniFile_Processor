"""
مثال: تقييم دقة OCR
=====================
حساب CER و WER لمقارنة النص المرجعي مع نتيجة OCR.
"""

from modules.evaluation.metrics import evaluate, calculate_cer, calculate_wer

reference = "بسم الله الرحمن الرحيم"
hypothesis = "بسم ا لله الرحمن الرحيم"

# تقييم شامل
result = evaluate(reference, hypothesis)
print(f"CER: {result.cer:.4f}")
print(f"WER: {result.wer:.4f}")
print(f"الدقة: {result.accuracy:.1f}%")
print(f"الجودة: {result.quality_grade}")

# أو حساب منفصل
cer = calculate_cer(reference, hypothesis)
wer = calculate_wer(reference, hypothesis)
print(f"\nCER مباشر: {cer:.4f}")
print(f"WER مباشر: {wer:.4f}")
