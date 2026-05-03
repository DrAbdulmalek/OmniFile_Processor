"""
OmniFile AI Processor v4.0
============================
نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص والخط اليدوي.

مدمج من مشاريع متعددة:
- OmniFile_Processor (الواجهة والبنية الأساسية)
- HandwrittenOCR (محرك OCR المتقدم - TrOCR + EasyOCR)
- handwriting-ocr (Notebooks والتصحيح والتدريب)
- Arabic AI Omni Processor (NLP والترجمة)
- IntelliFile (التنظيم والحماية)

الوحدات الأساسية:
1. وحدة المعالجة النصية واللغوية (NLP & Translation)
   - الترجمة التقنية (EN↔AR↔DE)
   - تصحيح إملائي عربي + إنجليزي
   - استخراج الكيانات المسماة (NER)
   - تصنيف النصوص
   - كشف اللغة
   - التلخيص

2. وحدة الرؤية الحاسوبية والتعرف (CV & OCR)
   - 4 محركات OCR: TrOCR, EasyOCR, Tesseract, PaddleOCR
   - دمج نتائج متعدد المحركات (4 استراتيجيات)
   - تحليل التخطيط والجداول
   - معالجة RTL عربية شاملة
   - معالجة النصوص المختلطة

3. وحدة التنظيم والحماية (File Management & Security)
   - تنظيم تلقائي للملفات
   - تشفير AES-128
   - حماية الأكواد البرمجية
   - فحص البيانات الحساسة
   - سجل التدقيق

4. محرك HandwrittenOCR المتقدم (src/)
   - Batch TrOCR + Beam Search + FP16
   - Smart Ensemble
   - LoRA Fine-tuning
   - Active Learning
   - Study Guide Generator

5. أدوات التصدير والتدريب
   - تصدير HuggingFace Hub
   - LoRA fine-tuning
   - CER/WER metrics

6. واجهات المستخدم
   - Streamlit (5 تبويبات)
   - Gradio (7 تبويبات)
   - React + Vite + shadcn/ui
   - FastAPI Backend (20+ endpoint)
   - PWA Mobile
   - HuggingFace Spaces

الترخيص: MIT
المؤلف: Dr. Abdulmalek
"""

__version__ = "4.0.0"
__project_name__ = "OmniFile AI Processor"
