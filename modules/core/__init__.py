"""
وحدة البنية الأساسية (Core Structure Module)
================================================
أنواع البيانات الأساسية المشتركة بين جميع وحدات المعالجة.
Shared data models and type definitions for all processing modules.

OmniFile AI Processor - وحدة معالجة الملفات الذكية
"""

from modules.core.structure import (
    BBox,
    BlockType,
    OCRToken,
    DocumentBlock,
    DocumentPage,
    DocumentMetadata,
    Document,
)

__all__ = [
    "BBox",
    "BlockType",
    "OCRToken",
    "DocumentBlock",
    "DocumentPage",
    "DocumentMetadata",
    "Document",
]
