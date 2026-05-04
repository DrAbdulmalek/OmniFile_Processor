"""
src/reconstruction.py — Backward Compatibility Layer
═══════════════════════════════════════════════════
⚠️  هذا الملف يُبقى للتوافق مع الكود القديم فقط.
سيتم حذفه في v5.0.

الموقع الجديد: modules/nlp/reconstruction.py
"""

from modules.nlp.reconstruction import (
    reconstruct_sentences,
    reconstruct_sentences_direct,
    extract_bilingual_vocab,
    derive_word_corrections,
)

__all__ = [
    "reconstruct_sentences",
    "reconstruct_sentences_direct",
    "extract_bilingual_vocab",
    "derive_word_corrections",
]
