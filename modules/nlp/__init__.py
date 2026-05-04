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
- معالجة النصوص العربية من اليمين لليسار (RTL)
- معالجة النصوص المختلطة (عربي + إنجليزي + أرقام)
- تصحيح النصوص باستخدام الذكاء الاصطناعي (GPT)
"""
from modules.nlp.text_classifier import TextClassifier
from modules.nlp.entity_extractor import EntityExtractor
from modules.nlp.translator import TechnicalTranslator
from modules.nlp.spell_corrector import SpellCorrector
from modules.nlp.language_detector import LanguageDetector
from modules.nlp.arabic_rtl import RTLFixer, is_rtl_text, get_text_direction
from modules.nlp.mixed_text import (
    detect_language,
    optimize_mixed_text,
    separate_text_components,
)
try:
    from modules.nlp.ai_corrector import AICorrector
except ImportError:  # تبعيات اختيارية مثل python-dotenv / openai
    AICorrector = None

__all__ = [
    "TextClassifier", "EntityExtractor", "TechnicalTranslator",
    "SpellCorrector", "LanguageDetector",
    "RTLFixer", "is_rtl_text", "get_text_direction",
    "detect_language", "optimize_mixed_text", "separate_text_components",
]

if AICorrector is not None:
    __all__.append("AICorrector")
