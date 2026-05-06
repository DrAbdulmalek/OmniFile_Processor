"""
نظام تصحيح الترجمات العربية ثنائية اللغة
Bilingual Arabic Translation Correction System

المصدر: OmniFile-Previous-Versions/01-arabic-translation-corrector/
الإصدار: 2.0.0 (مدمج من الأرشيف)
"""

from .arabic_translation_processor import (
    TranslationRule,
    ArabicTranslationProcessor,
)

__all__ = [
    "TranslationRule",
    "ArabicTranslationProcessor",
]
