#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/__init__.py
===============

طبقة توافق متقدمة للترحيل من src/ إلى modules/.

كل استيراد من src/ يتم توجيهه تلقائياً إلى modules/ المقابل
مع تحذير DeprecationWarning.

DEPRECATED: سيتم إزالة هذا الملف في v6.0
استخدم modules/ مباشرة بدلاً من src/

الجدول الكامل للتوجيه:
    src.recognition.OCREngine          → modules.vision.ocr_engine.OCREngine
    src.preprocessing.preprocess_image → modules.vision.preprocessing.preprocess_image
    src.pdf_processor.PDFProcessor      → modules.vision.pdf_processor.PDFProcessor
    src.reconstruction.*                → modules.nlp.reconstruction.*
    src.correction.*                    → modules.nlp.correction.* + modules.nlp.feedback.*
    src.study_guide.*                   → modules.nlp.study_guide.* + modules.export.study_guide.*
    src.gradio_ui.*                     → modules.ui.gradio_app.*
    src.review_ui.ReviewUI              → modules.ui.review_ui.ReviewUI
    src.database.HandwritingDB          → modules.core.handwriting_db.HandwritingDB
    src.export.*                        → modules.export.exporter.*
    src.finetuning.*                    → modules.ai.finetuning.*
    src.metrics.*                       → modules.evaluation.metrics.*
"""

import warnings
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# خريطة التوجيه الكاملة: src/ → modules/
# ============================================================================

_IMPORT_REDIRECTION_MAP = {
    # src.recognition → modules.vision.ocr_engine
    "OCREngine": ("modules.vision.ocr_engine", "OCREngine"),

    # src.preprocessing → modules.vision.preprocessing
    "preprocess_image": ("modules.vision.image_preprocessor", "preprocess_image"),
    "smart_segmentation": ("modules.vision.image_preprocessor", "smart_segmentation"),
    "ImagePreprocessor": ("modules.vision.image_preprocessor", "ImagePreprocessor"),

    # src.pdf_processor → modules.vision.pdf_processor
    "PDFProcessor": ("modules.vision.pdf_processor", "PDFProcessor"),

    # src.database → modules.core.handwriting_db
    "HandwritingDB": ("modules.core.handwriting_db", "HandwritingDB"),

    # src.reconstruction → modules.nlp.reconstruction
    "reconstruct_sentences": ("modules.nlp.reconstruction", "reconstruct_sentences"),
    "reconstruct_sentences_direct": ("modules.nlp.reconstruction", "reconstruct_sentences_direct"),
    "extract_bilingual_vocab": ("modules.nlp.reconstruction", "extract_bilingual_vocab"),
    "derive_word_corrections": ("modules.nlp.reconstruction", "derive_word_corrections"),

    # src.correction → modules.nlp.feedback
    "append_feedback": ("modules.nlp.feedback", "append_feedback"),
    "build_correction_dict": ("modules.nlp.feedback", "build_correction_dict"),
    "build_correction_dict_v2": ("modules.nlp.feedback", "build_correction_dict_v2"),
    "load_correction_dict": ("modules.nlp.feedback", "load_correction_dict"),
    "apply_correction_dict": ("modules.nlp.feedback", "apply_correction_dict"),
    "CorrectionRule": ("modules.nlp.feedback", "CorrectionRule"),
    "correct_text": ("modules.nlp.spell_corrector", "correct_text"),
    "init_correctors": ("modules.nlp.spell_corrector", "init_correctors"),
    "HybridSpellChecker": ("modules.core.spell_checker", "HybridSpellChecker"),

    # src.study_guide → modules.nlp.study_guide + modules.export.study_guide
    "generate_study_guide": ("modules.nlp.study_guide", "generate_study_guide"),
    "generate_study_guide_full": ("modules.nlp.study_guide", "generate_study_guide_full"),
    "table_to_markdown": ("modules.nlp.study_guide", "table_to_markdown"),
    "generate_mermaid_diagram": ("modules.nlp.study_guide", "generate_mermaid_diagram"),
    "generate_flashcards": ("modules.nlp.study_guide", "generate_flashcards"),
    "export_flashcards_anki": ("modules.nlp.study_guide", "export_flashcards_anki"),

    # src.gradio_ui → modules.ui.gradio_app
    "OmniFileProcessor": ("modules.ui.gradio_app", "OmniFileProcessor"),
    "create_gradio_interface": ("modules.ui.gradio_app", "create_gradio_interface"),
    "OmniFileConfig": ("modules.ui.gradio_app", "OmniFileConfig"),

    # src.review_ui → modules.ui.review_ui (future)
    "ReviewUI": ("src.review_ui", "ReviewUI"),

    # src.export → modules.export.exporter
    "export_finetuning_dataset": ("modules.export.exporter", "export_finetuning_dataset"),
    "push_to_huggingface": ("modules.export.exporter", "push_to_huggingface"),

    # src.finetuning → modules.ai.finetuning
    "finetune_trocr_lora": ("modules.ai.finetuning", "finetune_trocr_lora"),

    # src.metrics → modules.evaluation.metrics
    "calculate_cer": ("modules.evaluation.metrics", "calculate_cer"),
    "calculate_wer": ("modules.evaluation.metrics", "calculate_wer"),

    # src → modules.vision.htr (new)
    "ArabicHandwrittenHTR": ("modules.vision.htr", "ArabicHandwrittenHTR"),

    # src → modules.core.structure
    "FileStructureAnalyzer": ("modules.core.structure", "FileStructureAnalyzer"),
}


def __getattr__(name: str):
    """
    توجيه تلقائي للاستيرادات من src/ إلى modules/.

    عند أي استيراد من src/ (مثل: from src import OCREngine)
    يتم توجيهه تلقائياً إلى الوحدة الصحيحة في modules/
    مع إظهار تحذير إهمال.
    """
    if name in _IMPORT_REDIRECTION_MAP:
        module_path, attr_name = _IMPORT_REDIRECTION_MAP[name]

        # إظهار تحذير الإهمال
        old_path = f"src.{name}"
        new_path = f"{module_path}.{attr_name}"
        warnings.warn(
            f"استيراد '{old_path}' مُهمَل وسيتم إزالته في v6.0. "
            f"استخدم: from {module_path} import {attr_name}",
            DeprecationWarning,
            stacklevel=2
        )

        try:
            import importlib
            mod = importlib.import_module(module_path)
            return getattr(mod, attr_name)
        except (ImportError, AttributeError):
            # Fallback to old src/ module
            try:
                # Map old src submodules
                _FALLBACK_MAP = {
                    "OCREngine": "src.recognition",
                    "preprocess_image": "src.preprocessing",
                    "smart_segmentation": "src.preprocessing",
                    "PDFProcessor": "src.pdf_processor",
                    "HandwritingDB": "src.database",
                    "reconstruct_sentences": "src.reconstruction",
                    "reconstruct_sentences_direct": "src.reconstruction",
                    "extract_bilingual_vocab": "src.reconstruction",
                    "derive_word_corrections": "src.reconstruction",
                    "append_feedback": "src.correction",
                    "build_correction_dict": "src.correction",
                    "apply_correction_dict": "src.correction",
                    "CorrectionRule": "src.correction",
                    "correct_text": "src.correction",
                    "init_correctors": "src.correction",
                    "generate_study_guide": "src.study_guide",
                    "generate_study_guide_full": "src.study_guide",
                    "ReviewUI": "src.review_ui",
                    "export_finetuning_dataset": "src.export",
                    "push_to_huggingface": "src.export",
                    "finetune_trocr_lora": "src.finetuning",
                }
                fallback_module = _FALLBACK_MAP.get(name, "src")
                mod = importlib.import_module(fallback_module)
                return getattr(mod, name)
            except (ImportError, AttributeError):
                raise ImportError(
                    f"Cannot import '{name}' from either modules/ or src/. "
                    f"Module may not be installed."
                )

    raise AttributeError(
        f"module 'src' has no attribute '{name}'. "
        f"Use 'from modules.* import ...' instead."
    )


__version__ = "5.0.0"
__all__ = list(_IMPORT_REDIRECTION_MAP.keys())
