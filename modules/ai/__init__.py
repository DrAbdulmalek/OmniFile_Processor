"""
OmniFile AI Processor — AI Module (Self-Learning & AI Refinement)
===================================================================
القدرات:
- مطابقة الأنماط البصرية باستخدام SSIM (Pattern Matching)
- قاعدة بيانات التصحيحات الذاتية (Pattern Database)
- تحسين النصوص عبر Google Gemini API (Gemini Refiner)
"""
from modules.ai.pattern_db import PatternDatabase
from modules.ai.pattern_matcher import PatternMatcher, PatternMatch
from modules.ai.gemini_refiner import GeminiRefiner

__all__ = [
    "PatternDatabase",
    "PatternMatcher",
    "PatternMatch",
    "GeminiRefiner",
]
