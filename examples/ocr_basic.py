"""
مثال: OCR أساسي
================
استخدام محرك OCR لاستخراج النص من صورة.
"""

from modules.vision.ocr_engine import OCREngine

# إنشاء المحرك
engine = OCREngine(
    enable_easyocr=True,
    enable_tesseract=True,
    use_gpu=True,
)

# استخراج النص من صورة
result = engine.recognize("document.png", languages=["ar", "en"])

print(f"النص: {result['text']}")
print(f"الثقة: {result['confidence']:.2%}")
print(f"المحرك: {result['source']}")
print(f"الوقت: {result['processing_time']:.2f} ثانية")
