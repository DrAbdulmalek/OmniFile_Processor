"""
وحدة الرؤية الحاسوبية والتعرف على الملفات (CV & OCR)
======================================================
القدرات:
- استخراج النصوص من PDF والصور (TrOCR + EasyOCR + Tesseract + PaddleOCR)
- معالجة المخطوطات العربية اليدوية
- تحليل تخطيط المستندات واكتشاف الجداول
- تجزئة الصور إلى كلمات
- المعالجة المسبقة (CLAHE, denoise, deskew)
- إعادة تجميع النصوص RTL
- دمج نتائج عدة محركات OCR
- استخراج النصوص من الفيديو (Video OCR)
- توسيع بيانات التدريب للكتابة اليدوية (Data Augmentation)

OmniFile AI Processor - وحدة معالجة الملفات الذكية
"""
from modules.vision.ocr_engine import OCREngine
from modules.vision.pdf_processor import PDFProcessor
from modules.vision.image_preprocessor import ImagePreprocessor
from modules.vision.text_reconstructor import TextReconstructor
from modules.vision.result_fusion import ResultFusion, FusionStrategy
from modules.vision.layout_analyzer import LayoutAnalyzer
from modules.vision.table_extractor import TableExtractor
from modules.vision.video_ocr import VideoOCR, FrameResult, VideoTimeline
from modules.vision.data_augmentation import DataAugmentor
from modules.vision.dual_ocr_verifier import DualOCRVerifier
from modules.vision.batch_ocr import BatchMedicalOCR
from modules.vision.dataset_builder import DatasetBuilder
from modules.vision.medical_ocr import MedicalOCRProcessor, process_medical_pdf
from modules.vision.medical_ocr_gradio import create_medical_ocr_tab

__all__ = [
    "OCREngine",
    "PDFProcessor",
    "ImagePreprocessor",
    "TextReconstructor",
    "ResultFusion",
    "FusionStrategy",
    "LayoutAnalyzer",
    "TableExtractor",
    "VideoOCR",
    "FrameResult",
    "VideoTimeline",
    "DataAugmentor",
    "DualOCRVerifier",
    "BatchMedicalOCR",
    "DatasetBuilder",
    "MedicalOCRProcessor",
    "process_medical_pdf",
    "create_medical_ocr_tab",
]
