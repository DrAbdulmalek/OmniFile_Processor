"""
src/ — Backward-Compatibility Layer
====================================
⚠️  هذه الطبقة مُرحَّلة تدريجياً إلى modules/.
    سيتم حذف src/ بالكامل في v5.0.

خطة الترحيل (v4.2.0):
- src/database.py::HandwritingDB      → modules.core.handwriting_db
- src/reconstruction.py::reconstruct  → modules.nlp.reconstruction
- src/correction.py::append_feedback  → modules.nlp.feedback

الاستيرادات التالية تبقى صالحة للتوافق العكسي.
المكونات التي لم تُرحَّل بعد تستورد من src/ مباشرة.
"""

# === المكونات المُرحَّلة — تُعاد تصديرها من modules/ ===

# HandwritingDB: src.database → modules.core.handwriting_db
try:
    from modules.core.handwriting_db import HandwritingDB
except ImportError:
    from src.database import HandwritingDB

# reconstruct_sentences: src.reconstruction → modules.nlp.reconstruction
try:
    from modules.nlp.reconstruction import (
        reconstruct_sentences,
        reconstruct_sentences_direct,
        extract_bilingual_vocab,
        derive_word_corrections,
    )
except ImportError:
    from src.reconstruction import (
        reconstruct_sentences,
        reconstruct_sentences_direct,
        extract_bilingual_vocab,
        derive_word_corrections,
    )

# append_feedback: src.correction → modules.nlp.feedback
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
    from src.correction import (
        append_feedback,
        build_correction_dict,
        apply_correction_dict,
        CorrectionRule,
    )

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

try:
    from config import Config
except ImportError:
    pass

__version__ = "4.2.0"
