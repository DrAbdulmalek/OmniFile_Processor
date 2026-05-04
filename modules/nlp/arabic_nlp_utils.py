"""
📐 arabic_nlp_utils.py — أدوات المقارنة الدلالية للنصوص العربية
مُحسَّنة لبيئات OCR حيث يكون التشكيل والهمزات مصدرَ خطأ متكرر.
"""
import re
import difflib
from typing import Tuple


def normalize_for_comparison(text: str) -> str:
    """تطبيع النص العربي لأغراض المقارنة فقط (لا يُعدّل المخرج)."""
    if not text or not isinstance(text, str):
        return ""
    # 1. إزالة التشكيل والعلامات الخاصة
    text = re.sub(r'[\u064B-\u065F\u0670\u0651\u0640]', '', text)
    # 2. توحيد أشكال الألف والهمزة
    text = re.sub(r'[أإآٱ]', 'ا', text)
    # 3. توحيد الياء والألف المقصورة
    text = re.sub(r'[ى]', 'ي', text)
    # 4. توحيد التاء المربوطة (مفيد لـ OCR الطبي والعام)
    text = re.sub(r'ة', 'ه', text)
    # 5. حذف الرموز غير الحرفية وتنظيف الفراغات
    text = re.sub(r'[^\w\s]', '', text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def arabic_normalized_similarity(text1: str, text2: str) -> float:
    """
    نسبة التشابه بين نصين عربيين مع تجاهل أخطاء OCR الشائعة.
    يُرجع قيمة بين 0.0 و 1.0.
    """
    n1 = normalize_for_comparison(text1)
    n2 = normalize_for_comparison(text2)
    if not n1 or not n2:
        return 0.0
    return difflib.SequenceMatcher(None, n1, n2).ratio()


def similarity_report(text1: str, text2: str, threshold: float = 0.88) -> dict:
    """
    تقرير تشابه كامل يشمل القيمة الخام والمُطبَّعة وتوصية القبول.
    """
    raw = difflib.SequenceMatcher(None, text1.strip(), text2.strip()).ratio()
    normalized = arabic_normalized_similarity(text1, text2)
    approved = normalized >= threshold
    return {
        "raw_similarity": round(raw, 4),
        "normalized_similarity": round(normalized, 4),
        "threshold": threshold,
        "approved": approved,
        "needs_structural_review": (normalized > 0.85 and raw < 0.70),
        "recommendation": "مقبول" if approved else f"يحتاج مراجعة (تشابه {normalized:.1%})",
    }
