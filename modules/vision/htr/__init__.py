"""
وحدة التعرف على النصوص اليدوية (HTR) المتخصصة.
توفر: ArabicHandwrittenHTR, LineSegmenter, WordSegmenter, DottedRecovery
"""

from .arabic_htr import ArabicHandwrittenHTR, HTRResult
from .line_segmenter import ProjectionProfileSegmenter, UNetLineSegmenter, ContourLineSegmenter
from .word_segmenter import ArabicWordSegmenter
from .dotted_recovery import ArabicDottedRecovery
from .trocr_finetuned import FineTunedTrOCR

__all__ = [
    'ArabicHandwrittenHTR',
    'HTRResult',
    'ProjectionProfileSegmenter',
    'UNetLineSegmenter',
    'ContourLineSegmenter',
    'ArabicWordSegmenter',
    'ArabicDottedRecovery',
    'FineTunedTrOCR',
]
