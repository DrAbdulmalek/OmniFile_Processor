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
- progress_tracker: نظام تتبّع التقدّم مع الاستدعاءات الراجعة
- parallel_processor: المعالجة المتوازية للصفحات والدفعات
- model_manager: إدارة ذاكرة النماذج وتخزينها المؤقت

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
from modules.core.engine_router import EngineRouter
from modules.core.corrections_manager import CorrectionsDictManager
from modules.core.word_trainer import WordCorrectionDB
from modules.core.spell_checker import HybridSpellChecker
from modules.core.log_manager import AppLogger, get_app_logger
from modules.core.base_db import BaseDB
from modules.core.user_manager import UserManager
from modules.core.parallel_processor import ParallelProcessor
from modules.core.model_manager import ModelCache
from modules.core.progress_tracker import (
    ProgressCallback,
    ProgressTracker,
    ProgressRenderer,
    PipelineStep,
    ProcessingPipeline,
    StepProgress,
    create_progress_callback,
    progress_to_logger,
    GradioProgressAdapter,
    StreamlitProgressAdapter,
)

__all__ = [
    "BBox", "BlockType", "OCRToken", "DocumentBlock",
    "DocumentPage", "DocumentMetadata", "Document",
    "EngineRouter", "CorrectionsDictManager",
    "WordCorrectionDB", "HybridSpellChecker",
    "AppLogger", "get_app_logger",
    "BaseDB", "UserManager",
    "ParallelProcessor", "ModelCache",
    "ProgressCallback",
    "ProgressTracker",
    "ProgressRenderer",
    "PipelineStep",
    "ProcessingPipeline",
    "StepProgress",
    "create_progress_callback",
    "progress_to_logger",
    "GradioProgressAdapter",
    "StreamlitProgressAdapter",
]
