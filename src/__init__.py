"""
HandwrittenOCR - مشروع استخراج وتصحيح النصوص من الخط اليدوي
================================================================

v2.0 - نظام التحسين المستمر:
- Ensemble التعرف (TrOCR + EasyOCR)
- قاموس تصحيح يتعلم من مراجعات المستخدم
- تصدير بيانات Fine-tuning + رفع إلى HuggingFace
- تدريب LoRA على TrOCR
- إعادة تجميع الجمل (RTL)
"""

from src.preprocessing import preprocess_image, smart_segmentation
from src.recognition import OCREngine
from src.correction import (
    correct_text, init_correctors,
    build_correction_dict, apply_correction_dict,
)
from src.study_guide import (
    generate_study_guide, generate_study_guide_full,
    table_to_markdown, generate_mermaid_diagram,
    generate_flashcards, export_flashcards_anki,
)
from src.database import HandwritingDB
from src.pdf_processor import PDFProcessor
from src.review_ui import ReviewUI
from src.export import export_finetuning_dataset, push_to_huggingface
from src.finetuning import finetune_trocr_lora
from src.reconstruction import reconstruct_sentences
from config import Config

__version__ = "5.3.0"
