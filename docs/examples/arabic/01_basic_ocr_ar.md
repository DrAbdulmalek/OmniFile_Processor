# OCR أساسي للنص العربي

## نظرة عامة

يوضح هذا المثال كيفية استخدام محرك OmniFile OCR لاستخراج النص العربي من الصور والمستندات المطبوعة واليدوية. يدعم المشروع 5 محركات OCR مختلفة مع دعم كامل للنصوص العربية بما في ذلك الكلمات المنقطة وغير المنقطة، النصوص المختلطة عربي/إنجليزي، والمستندات متعددة الأعمدة.

## المتطلبات

```bash
pip install -r requirements-core.txt -r requirements-ocr.txt
```

## المثال 1: استخراج نص من صورة

```python
#!/usr/bin/env python3
"""مثال: OCR أساسي لنص عربي."""

from modules.vision.ocr_engine import OCREngine
from PIL import Image

# إنشاء محرك OCR (يستخدم TrOCR افتراضياً)
ocr = OCREngine(engine="trocr")

# تحميل صورة تحتوي على نص عربي
image = Image.open("sample_arabic_text.png")

# استخراج النص
result = ocr.recognize(image, language="ar")

print(f"النص المستخرج: {result.text}")
print(f"مستوى الثقة: {result.confidence:.2%}")
print(f"عدد الكلمات: {result.word_count}")
```

## المثال 2: OCR مع التصحيح الإملائي التلقائي

```python
from modules.vision.ocr_engine import OCREngine
from modules.core.spell_checker import HybridSpellChecker
from PIL import Image

# تهيئة المحرك مع التصحيح
ocr = OCREngine(engine="trocr")
spell_checker = HybridSpellChecker()

# استخراج النص
image = Image.open("handwritten_arabic.png")
result = ocr.recognize(image, language="ar")

# تصحيح إملائي
corrected = spell_checker.correct(result.text)
print(f"قبل التصحيح: {result.text}")
print(f"بعد التصحيح: {corrected}")
```

## المثال 3: مقارنة بين محركات OCR

```python
from modules.vision.ocr_engine import OCREngine

engines = ["trocr", "easyocr", "tesseract", "paddleocr"]
image = Image.open("sample.png")

for engine_name in engines:
    ocr = OCREngine(engine=engine_name)
    result = ocr.recognize(image, language="ar")
    print(f"{engine_name}: {result.text[:50]}... (ثقة: {result.confidence:.2%})")
```

## المثال 4: معالجة ملف PDF كامل

```python
from modules.vision.pdf_processor import PDFProcessor

processor = PDFProcessor()

# استخراج النص من كل صفحة
pages = processor.extract_text("document.pdf", language="ar")

for i, page in enumerate(pages):
    print(f"--- صفحة {i+1} ---")
    print(page.text)
    print(f"الثقة: {page.confidence:.2%}")
```

## ملاحظات

- محرك TrOCR هو الأفضل للنصوص اليدوية العربية
- محرك EasyOCR يوفر توازناً جيداً بين السرعة والدقة
- محرك PaddleOCR هو الأسرع للنصوص المطبوعة
- استخدم `language="multi"` للنصوص المختلطة عربي/إنجليزي
