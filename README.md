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

# 🧠 OmniFile AI Processor v2.0

نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص والخط اليدوي.
مدمج من ثلاثة مشاريع: **OmniFile_Processor** + **HandwrittenOCR** + **handwriting-ocr**

## 🌟 المميزات الرئيسية

### وحدة الرؤية الحاسوبية والخط اليدوي (CV & OCR)
- **Ensemble OCR:** TrOCR + EasyOCR + Tesseract مع ذكاء اختيار المحرك
- **معالجة متقدمة:** CLAHE + إزالة الميل + إزالة التشويش + Otsu Threshold
- **تجزئة ذكية:** EasyOCR-first + Contour fallback + IoU matching
- **إعادة بناء الجمل:** دعم RTL/LTR مع كشف اللغة التلقائي
- **معالجة PDF:** PyMuPDF (خفيف) + pdf2image (fallback)
- **نموذج TrOCR:** `microsoft/trocr-base-handwritten` + دعم LoRA fine-tuning
- **Active Learning:** إعادة معالجة الكلمات منخفضة الثقة تلقائياً
- **مقاييس الأداء:** WER و CER مع رسم بياني

### وحدة معالجة اللغة الطبيعية (NLP & Translation)
- **تصحيح إملائي:** عربي + إنجليزي + ألماني مع حماية كلمات Python
- **قاموس تصحيح ذكي:** يتعلم من تعديلات المستخدم (self-learning)
- **ترجمة تقنية:** Helsinki-NLP/opus-mt-en-ar
- **استخراج الكيانات:** BERT-based NER
- **تصنيف النصوص:** 6 فئات
- **كشف اللغة:** دعم عربي، إنجليزي، فرنسي، ألماني، تركي

### وحدة تنظيم الملفات والحماية (Security)
- **تنظيم تلقائي:** فرز الملفات حسب النوع والمحتوى
- **حماية الأكواد:** منع التصحيح الإملائي داخل كتل البرمجة
- **فحص أمان:** كشف البيانات الحساسة في الملفات
- **إدارة الأرشيفات:** ضغط وفك ضغط مع فحص السلامة
- **نسخ احتياطي:** تلقائي يدوي مع إدارة النسخ

### أدوات متقدمة
- **LoRA Fine-tuning:** ضبط دقيق لنموذج TrOCR على بياناتك
- **Study Guide Generator:** Markdown + HTML + Mermaid diagrams + Anki flashcards
- **تصدير متعدد:** CSV + XLSX + JSONL + PDF reports
- **Dashboard:** إحصائيات شاملة مع رسوم بيانية
- **Multi-device Sync:** FileLock + Syncthing
- **Comprehensive Logging:** ملف + stdout + HTML reports
- **Data Migration:** استيراد من إصدارات سابقة

## 📁 هيكل المشروع

```
OmniFile_Processor/
├── app.py                          # Streamlit UI الرئيسية (6 تبويبات)
├── config.py                       # الإعدادات المركزية
├── database.py                     # قاعدة بيانات SQLite (6 جداول)
├── __init__.py                     # Package init
├── main.py                         # Local/CLI entry point
│
├── modules/
│   ├── nlp/                        # وحدة معالجة اللغة الطبيعية
│   │   ├── language_detector.py    # كشف اللغة
│   │   ├── text_classifier.py      # تصنيف النصوص
│   │   ├── entity_extractor.py     # استخراج الكيانات
│   │   ├── translator.py           # الترجمة التقنية
│   │   ├── spell_corrector.py      # التصحيح الإملائي
│   │   └── correction_dict.json    # قاموس التصحيح
│   │
│   ├── vision/                     # وحدة الرؤية الحاسوبية
│   │   ├── image_preprocessor.py   # معالجة الصور
│   │   ├── ocr_engine.py           # محرك OCR
│   │   ├── pdf_processor.py        # معالج PDF
│   │   └── text_reconstructor.py   # إعادة بناء الجمل
│   │
│   └── security/                   # وحدة الأمان والحماية
│       ├── file_organizer.py       # تنظيم الملفات
│       ├── code_protector.py       # حماية الأكواد
│       ├── archive_handler.py      # إدارة الأرشيفات
│       ├── file_scanner.py         # فحص الأمان
│       └── backup_manager.py       # النسخ الاحتياطي
│
├── src/                            # HandwrittenOCR Engine (Advanced OCR)
│   ├── __init__.py                 # Package init + API exports
│   ├── main.py                     # Local entry point
│   ├── preprocessing.py            # معالجة الصور المتقدمة
│   ├── recognition.py              # TrOCR + EasyOCR Ensemble Engine
│   ├── correction.py               # تصحيح متعدد اللغات + قاموس ذكي
│   ├── pdf_processor.py            # PDF pipeline مع checkpoint
│   ├── reconstruction.py           # إعادة بناء الجمل RTL/LTR
│   ├── database.py                 # SQLite v3 (HandwritingDB)
│   ├── review_ui.py                # Jupyter + CLI review
│   ├── gradio_ui.py                # Gradio 7-tab UI
│   ├── export.py                   # تصدير + HF Hub upload
│   ├── finetuning.py               # LoRA fine-tuning
│   ├── metrics.py                  # WER/CER computation
│   ├── study_guide.py              # Study guide + Anki flashcards
│   ├── migration.py                # Data migration tool
│   ├── sync.py                     # Multi-device sync + FileLock
│   └── logger.py                   # Comprehensive logging v7
│
├── artifacts/                      # بيانات مرجعية
│   └── correction_dict.json        # قاموس تصحيح مبدئي
├── data_seed/                      # بيانات البذرة
│   └── correction_dict_seed.json
├── notebooks/                      # Jupyter Notebooks
│   ├── OmniFile_Complete.ipynb     # Colab notebook (OmniFile)
│   ├── HandwrittenOCR_Colab.ipynb  # Colab notebook (HF Spaces)
│   └── HandwrittenOCR_Ultimate.ipynb # Ultimate v4.0 monolithic notebook
│
├── Dockerfile                      # Docker for HuggingFace Spaces
├── requirements.txt                # Python dependencies
├── LICENSE                         # MIT License
└── README.md                       # هذا الملف
```

## 🚀 التشغيل

### HuggingFace Spaces (Docker)
```bash
# تم النشر تلقائياً عبر Dockerfile
# app_port: 7860
```

### Google Colab
```python
# استخدم أحد Notebooks في مجلد notebooks/
# أو:
!git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
%cd OmniFile_Processor
!pip install -r requirements.txt
!streamlit run app.py --server.port 7860
```

### محلي (Manjaro/Arch/Linux/macOS/Windows)
```bash
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor
pip install -r requirements.txt

# Streamlit UI
streamlit run app.py

# Gradio UI (advanced)
python -m src.gradio_ui

# CLI mode
python main.py
```

## 🌍 اللغات المدعومة
- 🇸🇦 العربية (Arabic)
- 🇬🇧 الإنجليزية (English)
- 🇩🇪 الألمانية (German)
- 🇫🇷 الفرنسية (French)
- 🇹🇷 التركية (Turkish)

## 📜 الترخيص
MIT License - Copyright (c) 2026
