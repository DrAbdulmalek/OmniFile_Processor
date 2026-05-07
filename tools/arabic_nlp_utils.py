# arabic_nlp_utils.py - Arabic NLP utilities for review comparison

"""
📐 أدوات معالجة النص العربي لمقارنة المعنى (وليس الشكل الحرفي)
مُحسّنة خصيصاً لبيئات OCR والمراجعة البشرية
"""
import re
from typing import Tuple

def normalize_for_comparison(text: str) -> str:
    if not text or not isinstance(text, str): return ""

    # 1. إزالة التشكيل الزائد والعلامات الخاصة
    text = re.sub(r'[\u064B-\u065F\u0670\u0651\u0640]', '', text)
    # 2. توحيد أشكال الألف والهمزة
    text = re.sub(r'[أإآٱ]', 'ا', text)
    # 3. توحيد الياء والألف المقصورة
    text = re.sub(r'[ى]', 'ي', text)
    # 4. توحيد التاء المربوطة (اختياري، يُفعّل للـ OCR الطبي/العام)
    text = re.sub(r'ة', 'ه', text)
    # 5. تنظيف الفراغات والرموز غير الهجائية/رقمية
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def arabic_normalized_similarity(text1: str, text2: str) -> float:
    """حساب نسبة التشابه الدلالي/الهيكلي مع تجاهل أخطاء الـ OCR الشائعة"""
    n1, n2 = normalize_for_comparison(text1), normalize_for_comparison(text2)
    if not n1 or not n2: return 0.0

    import difflib
    # SequenceMatcher حساس للترتيب، مناسب للعربية بسبب RTL المنطقي
    return difflib.SequenceMatcher(None, n1, n2).ratio()
