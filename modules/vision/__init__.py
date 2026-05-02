"""
وحدة الرؤية الحاسوبية والتعرف على الملفات (CV & OCR)
======================================================
القدرات:
- استخراج النصوص من PDF والصور (TrOCR + EasyOCR + Tesseract)
- معالجة المخطوطات العربية اليدوية
- تجزئة الصور إلى كلمات
- المعالجة المسبقة (CLAHE, denoise, deskew)
- إعادة تجميع النصوص RTL
"""
from modules.vision.ocr_engine import OCREngine
from modules.vision.pdf_processor import PDFProcessor
from modules.vision.image_preprocessor import ImagePreprocessor
from modules.vision.text_reconstructor import TextReconstructor

__all__ = [
    "OCREngine", "PDFProcessor", "ImagePreprocessor", "TextReconstructor"
]
