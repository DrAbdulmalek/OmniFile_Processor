"""
وحدة المعالجة النصية واللغوية (NLP & Translation)
===================================================
القدرات:
- تصنيف النصوص العربية والإنجليزية
- استخراج الكيانات المسماة (NER)
- الترجمة التقنية EN→AR
- التصحيح الإملائي الذكي (عربي + إنجليزي)
- كشف اللغة تلقائياً
- حماية المصطلحات التقنية من التصحيح
"""
from modules.nlp.text_classifier import TextClassifier
from modules.nlp.entity_extractor import EntityExtractor
from modules.nlp.translator import TechnicalTranslator
from modules.nlp.spell_corrector import SpellCorrector
from modules.nlp.language_detector import LanguageDetector

__all__ = [
    "TextClassifier", "EntityExtractor", "TechnicalTranslator",
    "SpellCorrector", "LanguageDetector"
]
