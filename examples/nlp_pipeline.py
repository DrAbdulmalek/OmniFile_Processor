"""
مثال: خط أنابيب NLP
=====================
OCR → تصحيح إملائي → تلخيص.
"""

from modules.vision.ocr_engine import OCREngine
from modules.nlp.spell_corrector import SpellCorrector
from modules.nlp.summarizer import TextSummarizer

# 1. استخراج النص
engine = OCREngine(enable_easyocr=True)
ocr_result = engine.recognize("handwritten_note.png")
raw_text = ocr_result["text"]

# 2. تصحيح إملائي
corrector = SpellCorrector()
correction = corrector.correct_text(raw_text)
corrected_text = correction["corrected_text"]

print(f"التصحيحات: {correction['total_corrections']}")
for c in correction["corrections"]:
    print(f"  {c['original']} → {c['corrected']}")

# 3. تلخيص
summarizer = TextSummarizer()
summary = summarizer.summarize(corrected_text, lang="auto")

print(f"\nالملخص:\n{summary}")
