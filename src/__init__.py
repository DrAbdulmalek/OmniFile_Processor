#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/__init__.py
===============

طبقة توافق للترحيل من src/ إلى modules/.

DEPRECATED: سيتم إزالة هذا الملف في الإصدار 6.0
استخدم modules/ مباشرة بدلاً من src/
"""

import warnings
import sys
from pathlib import Path

# ============================================================================
# تحذير الاستخدام
# ============================================================================

warnings.warn(
    "src/ is deprecated and will be removed in v6.0. "
    "Use modules/ instead. "
    "See: https://github.com/DrAbdulmalek/OmniFile_Processor/blob/main/MIGRATION.md",
    DeprecationWarning,
    stacklevel=2
)

# ============================================================================
# إعادة التوجيه إلى modules/
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# === المكونات المُرحَّلة — تُعاد تصديرها من modules/ ===

# HandwritingDB: src.database -> modules.core.handwriting_db
try:
    from modules.core.handwriting_db import HandwritingDB
except ImportError:
    try:
        from src.database import HandwritingDB
    except ImportError:
        pass

# reconstruct_sentences: src.reconstruction -> modules.nlp.reconstruction
try:
    from modules.nlp.reconstruction import (
        reconstruct_sentences,
        reconstruct_sentences_direct,
        extract_bilingual_vocab,
        derive_word_corrections,
    )
except ImportError:
    try:
        from src.reconstruction import (
            reconstruct_sentences,
            reconstruct_sentences_direct,
            extract_bilingual_vocab,
            derive_word_corrections,
        )
    except ImportError:
        pass

# append_feedback: src.correction -> modules.nlp.feedback
try:
    from modules.nlp.feedback import (
        append_feedback,
        build_correction_dict,
        build_correction_dict_v2,
        load_correction_dict,
        apply_correction_dict,
        CorrectionRule,
    )
except ImportError:
    try:
        from src.correction import (
            append_feedback,
            build_correction_dict,
            apply_correction_dict,
            CorrectionRule,
        )
    except ImportError:
        pass

# === المكونات التي لم تُرحَّل بعد — تستورد من src/ مباشرة ===
try:
    from src.preprocessing import preprocess_image, smart_segmentation
except ImportError:
    pass

try:
    from src.recognition import OCREngine
except ImportError:
    pass

try:
    from src.correction import correct_text, init_correctors
except ImportError:
    pass

try:
    from src.study_guide import (
        generate_study_guide, generate_study_guide_full,
        table_to_markdown, generate_mermaid_diagram,
        generate_flashcards, export_flashcards_anki,
    )
except ImportError:
    pass

try:
    from src.pdf_processor import PDFProcessor
except ImportError:
    pass

try:
    from src.review_ui import ReviewUI
except ImportError:
    pass

try:
    from src.export import export_finetuning_dataset, push_to_huggingface
except ImportError:
    pass

try:
    from src.finetuning import finetune_trocr_lora
except ImportError:
    pass

# === إعادة تصدير من modules/ (الجديد) ===
try:
    from modules.ui.gradio_app import OmniFileProcessor, create_gradio_interface
    from modules.vision.ocr_engine import OCREngine as ModernOCREngine
    from modules.vision.htr import ArabicHandwrittenHTR
    from modules.core.structure import FileStructureAnalyzer
except ImportError:
    pass

try:
    from config import Config
except ImportError:
    pass

__version__ = "5.0.0"
