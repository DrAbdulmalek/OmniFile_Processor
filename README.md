---
title: OmniFile AI Processor
emoji: 🧠
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# 🧠 OmniFile AI Processor v3.0

نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص والخط اليدوي.
مدمج من ستة مشاريع: **OmniFile_Processor** + **HandwrittenOCR** + **handwriting-ocr** + **arabic-ocr-pro** + **advanced-ocr** + **OCR-Enhancer**

## 🌟 المميزات الرئيسية

### وحدة الرؤية الحاسوبية والخط اليدوي (CV & OCR)
- **4 محركات OCR:** TrOCR + EasyOCR + Tesseract + PaddleOCR مع ذكاء اختيار المحرك
- **دمج النتائج:** 4 استراتيجيات - أعلى ثقة، متوسط مرجح، تصويت، أطول نص
- **معالجة متقدمة:** CLAHE + إزالة الميل + إزالة التشويش + Otsu Threshold
- **تجزئة ذكية:** EasyOCR-first + Contour fallback + IoU matching
- **تحليل التخطيط:** كشف الجداول والعناوين والتذييلات (Layout Analysis)
- **استخراج الجداول:** خطوط Hough + تحليل المحيطات (Table Extraction)
- **إعادة بناء الجمل:** دعم RTL/LTR مع كشف اللغة التلقائي
- **معالجة PDF:** PyMuPDF (خفيف) + pdf2image (fallback)
- **ONNX Runtime:** تسريع الاستدلال + Quantization INT8
- **تخزين مؤقت:** نتائج OCR مع صلاحية قابلة للتعديل

### وحدة معالجة اللغة الطبيعية (NLP)
- **تصحيح إملائي:** عربي + إنجليزي + ألماني مع حماية كلمات Python
- **قاموس عربي:** 186 تصحيح شائع + التعلم من المستخدم
- **معالجة RTL:** arabic_reshaper + python-bidi + 40+ خريطة تطبيع
- **نصوص مختلطة:** عربي/إنجليزي/أرقام مع حماية المصطلحات الطبية
- **ترجمة تقنية:** Helsinki-NLP/opus-mt (6 أزواج لغوية)
- **تلخيص:** BART (facebook/bart-large-cnn)
- **استخراج الكيانات:** BERT-based NER
- **تصنيف النصوص:** 6 فئات
- **كشف اللغة:** دعم عربي، إنجليزي، ألماني

### وحدة الذكاء الاصطناعي المتقدم (AI Enhancement)
- **تصحيح GPT:** تحسين نصوص OCR باستخدام OpenAI GPT
- **تحسين Gemini:** تحسين السياق مع محددات حسب نوع الكتلة
- **SSIM Pattern Matching:** تعلم ذاتي من صور الكلمات المصححة
- **قاعدة أنماط SQLite:** تخزين واسترجاع الأنماط البصرية

### وحدة التصدير (Multi-Format Export)
- **DOCX:** مع دعم RTL (right-aligned + bidi)
- **HTML:** مع `dir="rtl"` + خطوط عربية
- **PDF قابل للبحث:** نص غير مرئي فوق صور الصفحات
- **Excel:** مع محاذاة RTL + عرض أعمدة تلقائي
- **JSON:** هيكل كامل مع BBox والثقة والبيانات الوصفية
- **TXT:** UTF-8 مع BOM

### وحدة الأمان والحماية (Security)
- **فحص أمان:** Presidio PII + detect-secrets
- **حماية الأكواد:** منع التصحيح داخل كتل البرمجة
- **تنظيم تلقائي:** فرز الملفات حسب النوع والمحتوى
- **إدارة الأرشيفات:** ضغط وفك ضغط مع فحص السلامة
- **نسخ احتياطي:** تلقائي ويدوي
- **معالجة آمنة:** منع path traversal + tempfile

### التقييم والأداء (Evaluation)
- **CER/WER:** تقييم دقة OCR مع تطبيع عربي
- **تقدير الجودة:** A+ إلى F مع توصيات
- **Levenshtein:** مدمج بدون مكتبات خارجية

### واجهة المستخدم (UI)
- **Streamlit:** واجهة رئيسية مع 6 تبويبات
- **Gradio:** واجهة متقدمة مع 7 تبويبات
- **React + shadcn/ui:** واجهة ويب حديثة (وضع فاتح/داكن)
- **CLI:** سطر الأوامر مع argparse
- **PyQt6:** واجهة سطح مكتب (من arabic-ocr-pro)

## 📁 هيكل المشروع

```
OmniFile_Processor/
├── app.py                          # Streamlit UI الرئيسية
├── config.py                       # الإعدادات المركزية v3.0
├── database.py                     # قاعدة بيانات SQLite
├── main.py                         # Local/CLI entry point
├── tasks.py                        # Celery async tasks
│
├── modules/
│   ├── vision/                     # وحدة الرؤية الحاسوبية
│   │   ├── ocr_engine.py           # 4 محركات OCR + ONNX + Quantization
│   │   ├── image_preprocessor.py   # CLAHE + Denoise + Deskew + Otsu
│   │   ├── pdf_processor.py        # معالج PDF متعدد الصيغات
│   │   ├── text_reconstructor.py   # إعادة بناء RTL/LTR
│   │   ├── result_fusion.py        # دمج 4 استراتيجيات
│   │   ├── layout_analyzer.py      # تحليل التخطيط (جداول، عناوين)
│   │   └── table_extractor.py      # استخراج الجداول
│   │
│   ├── nlp/                        # وحدة معالجة اللغة
│   │   ├── spell_corrector.py      # تصحيح 3 لغات + تعلم ذاتي
│   │   ├── translator.py           # ترجمة Helsinki-NLP
│   │   ├── summarizer.py           # تلخيص BART
│   │   ├── entity_extractor.py     # استخراج الكيانات
│   │   ├── language_detector.py    # كشف اللغة
│   │   ├── text_classifier.py      # تصنيف النصوص
│   │   ├── arabic_rtl.py           # معالجة RTL شاملة
│   │   ├── mixed_text.py           # نصوص مختلطة عربي/إنجليزي
│   │   └── ai_corrector.py         # تصحيح GPT
│   │
│   ├── ai/                         # وحدة الذكاء الاصطناعي
│   │   ├── pattern_matcher.py      # SSIM pattern matching
│   │   ├── pattern_db.py           # SQLite pattern database
│   │   └── gemini_refiner.py       # Gemini AI refinement
│   │
│   ├── core/                       # النماذج الأساسية
│   │   └── structure.py            # Pydantic v2 data models
│   │
│   ├── evaluation/                 # وحدة التقييم
│   │   └── metrics.py              # CER/WER + quality grading
│   │
│   ├── export/                     # وحدة التصدير
│   │   └── exporter.py             # DOCX/HTML/PDF/JSON/TXT/Excel
│   │
│   └── security/                   # وحدة الأمان
│       ├── file_organizer.py       # تنظيم الملفات
│       ├── code_protector.py       # حماية الأكواد
│       ├── archive_handler.py      # إدارة الأرشيفات
│       ├── file_scanner.py         # فحص الأمان
│       ├── backup_manager.py       # النسخ الاحتياطي
│       ├── sensitive_data_scanner.py # فحص PII
│       └── secure_file_handler.py  # معالجة آمنة
│
├── frontend/                       # React + shadcn/ui
│   ├── src/
│   │   ├── App.jsx                 # التطبيق الرئيسي
│   │   ├── components/             # مكونات UI
│   │   │   ├── FileUpload.jsx      # رفع الملفات
│   │   │   ├── ProcessingOptions.jsx # خيارات المعالجة
│   │   │   └── ResultsDisplay.jsx  # عرض النتائج
│   │   └── services/api.js         # API client
│   └── package.json
│
├── data/
│   └── arabic_fixes.json           # 186 تصحيح عربي
│
├── tests/                          # اختبارات pytest (13 ملف)
│   ├── test_ocr_engine.py
│   ├── test_fusion.py
│   ├── test_metrics.py
│   ├── test_pattern_matcher.py
│   ├── test_arabic_rtl.py
│   └── ...
│
├── src/                            # محرك HandwrittenOCR
├── notebooks/                      # Jupyter Notebooks
├── docs/                           # التوثيق
│   ├── USER_GUIDE.md
│   └── DEVELOPER_GUIDE.md
├── Dockerfile
├── requirements.txt
└── LICENSE
```

## 📊 إحصائيات المشروع

| المقياس | القيمة |
|---------|--------|
| ملفات Python | 72 |
| أسطر Python | ~28,000 |
| إجمالي الملفات | 152 |
| محركات OCR | 4 (TrOCR, EasyOCR, Tesseract, PaddleOCR) |
| استراتيجيات الدمج | 4 |
| لغات مدعومة | 3 (EN, AR, DE) |
| صيغ التصدير | 6 (DOCX, HTML, PDF, JSON, TXT, Excel) |
| ملفات الاختبار | 13 |
| المشاريع المدمجة | 6 |

## 🚀 التشغيل

### Google Colab
```python
!git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
%cd OmniFile_Processor
!pip install -r requirements.txt
!streamlit run app.py --server.port 7860
```

### محلي (Linux/macOS/Windows)
```bash
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor
pip install -r requirements.txt

# Streamlit UI
streamlit run app.py

# Gradio UI
python -m src.gradio_ui

# CLI
python main.py

# React Frontend
cd frontend && npm install && npm run dev
```

### Docker
```bash
docker build -t omnifile .
docker run -p 7860:7860 omnifile
```

## 🌍 اللغات المدعومة
- 🇸🇦 العربية (Arabic) - RTL كامل
- 🇬🇧 الإنجليزية (English)
- 🇩🇪 الألمانية (German)

## 📜 الترخيص
MIT License - Copyright (c) 2026
