"""
وحدة البنية الأساسية (Core Structure Module)
================================================
أنواع البيانات الأساسية المشتركة بين جميع وحدات المعالجة.
Shared data models and type definitions for all processing modules.

الوحدات الفرعية:
- structure: أنواع البيانات المشتركة (BBox, DocumentBlock, etc.)
- database_manager: نظام قاعدة البيانات (OmniDatabase) مع بصمة SHA-256
- file_fingerprint: نظام بصمة الملفات (FileFingerprintManager)
- classifier: مصنف المحتوى الطبي والعلمي (MedicalClassifier)
- watchdog_service: مراقب المجلدات (FolderWatchdog)
- dataset_generator: مولد بيانات التدريب الناعم (DatasetGenerator)
- search_engine: محرك البحث الشامل (SearchEngine)
- handwriting_db: قاعدة بيانات الخط اليدوي

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
