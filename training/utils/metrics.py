"""مقاييس تقييم HTR/OCR"""
import editdistance
from typing import List

def compute_cer(prediction: str, reference: str) -> float:
    """حساب Character Error Rate."""
    if not reference:
        return 0.0
    return editdistance.eval(prediction, reference) / len(reference)

def compute_wer(prediction: str, reference: str) -> float:
    """حساب Word Error Rate."""
    pred_words = prediction.split()
    ref_words = reference.split()
    if not ref_words:
        return 0.0
    return editdistance.eval(pred_words, ref_words) / len(ref_words)

def compute_accuracy(prediction: str, reference: str) -> float:
    """حساب الدقة الحرفية."""
    if len(prediction) != len(reference):
        return 0.0
    correct = sum(p == r for p, r in zip(prediction, reference))
    return correct / len(prediction) if prediction else 0.0

def compute_batch_metrics(predictions: List[str], references: List[str]) -> dict:
    """حساب مقاييس متعددة لدفعة."""
    total_cer = sum(compute_cer(p, r) for p, r in zip(predictions, references))
    total_wer = sum(compute_wer(p, r) for p, r in zip(predictions, references))
    correct = sum(p == r for p, r in zip(predictions, references))
    n = len(predictions)
    return {
        "cer": total_cer / n if n > 0 else 0.0,
        "wer": total_wer / n if n > 0 else 0.0,
        "accuracy": correct / n if n > 0 else 0.0,
        "num_samples": n,
    }
