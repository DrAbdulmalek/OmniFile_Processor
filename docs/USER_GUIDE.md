# دليل المستخدم - OmniFile AI Processor v2.1
# User Guide - OmniFile AI Processor v2.1

> **نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص والخط اليدوي**
> **Integrated AI System for File Processing, Text Analysis, and Handwriting Recognition**

---

## المحتويات / Table of Contents

1. [متطلبات النظام / System Requirements](#1-متطلبات-النظام--system-requirements)
2. [التثبيت / Installation](#2-التثبيت--installation)
3. [التشغيل / Running](#3-التشغيل--running)
4. [الميزات الرئيسية / Key Features](#4-الميزات-الرئيسية--key-features)
5. [اختصارات لوحة المفاتيح / Keyboard Shortcuts](#5-اختصارات-لوحة-المفاتيح--keyboard-shortcuts)
6. [حل المشكلات / Troubleshooting](#6-حل-المشكلات--troubleshooting)
7. [أسئلة شائعة / FAQ](#7-أسئلة-شائعة--faq)

---

## 1. متطلبات النظام / System Requirements

### المتطلبات الأساسية / Core Requirements

| المتطلب / Requirement | الحد الأدنى / Minimum | الموصى به / Recommended |
|---|---|---|
| **Python** / Python Version | 3.8+ | 3.11+ |
| **الذاكرة (RAM)** / Memory | 4 GB | 8 GB+ |
| **مساحة القرص** / Disk Space | 5 GB (للنماذج) | 10 GB+ |
| **نظام التشغيل** / OS | Linux / Windows / macOS | Ubuntu 22.04+ / Manjaro / Arch |
| **المعالج** / CPU | x86_64 dual-core | x86_64 quad-core+ |

### متطلبات GPU (اختياري) / GPU Requirements (Optional)

| المتطلب / Requirement | المواصفات / Specification |
|---|---|
| **كرت الشاشة** / GPU | NVIDIA GPU (CUDA Compute Capability 6.0+) |
| **CUDA** / CUDA Toolkit | 11.8+ (12.1+ موصى به) |
| **VRAM** / Video Memory | 4 GB (لـ TrOCR-base) |
| **cuDNN** / cuDNN | 8.x+ |

> **ملاحظة / Note:** يعمل النظام بالكامل على CPU بدون أي مشكلة، لكن GPU يسرّع عمليات TrOCR و EasyOCR بشكل كبير.
> **Note:** The system works fully on CPU without issues. GPU significantly accelerates TrOCR and EasyOCR processing.

### المتطلبات الاختيارية / Optional Dependencies

| المكتبة / Library | الغرض / Purpose | التثبيت / Install |
|---|---|---|
| **Tesseract OCR** | محرك OCR احتياطي خفيف | `apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng` |
| **Redis** | المعالجة غير المتزامنة (Celery) | `apt install redis-server` |
| **ONNX Runtime** | تسريع الاستدلال | `pip install onnxruntime` أو `onnxruntime-gpu` |
| **Presidio** | فحص البيانات الحساسة المتقدم | `pip install presidio-analyzer presidio-anonymizer` |

---

## 2. التثبيت / Installation

### 2.1 التثبيت المحلي / Local Installation

```bash
# 1. استنساخ المشروع / Clone the repository
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor

# 2. إنشاء بيئة افتراضية (موصى به) / Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# 3. تثبيت الحزم / Install dependencies
pip install -r requirements.txt

# 4. تثبيت Tesseract (اختياري) / Install Tesseract (optional)
# Ubuntu/Debian:
sudo apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng
# macOS:
brew install tesseract
```

### 2.2 التثبيت على Google Colab / Google Colab Installation

```python
# 1. استنساخ المشروع / Clone the project
!git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
%cd OmniFile_Processor

# 2. تثبيت الحزم / Install packages
!pip install -q -r requirements.txt

# 3. تثبيت Tesseract / Install Tesseract
!apt install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng

# 4. تشغيل التطبيق / Run the application
!streamlit run app.py --server.port 7860
```

<details>
<summary>📖 إعداد Google Colab المتقدم / Advanced Colab Setup</summary>

```python
# ربط Google Drive للحفظ المستمر
from google.colab import drive
drive.mount('/content/drive')

# إنشاء مجلد العمل
import os
WORK_DIR = '/content/drive/MyDrive/OmniFile_AI'
os.makedirs(WORK_DIR, exist_ok=True)

# نسخ المشروع إلى Drive
!cp -r /content/OmniFile_Processor/* {WORK_DIR}/

# إعداد الإعدادات
from config import OmniFileConfig
cfg = OmniFileConfig.from_colab_drive()
cfg.setup_environment()
```

</details>

### 2.3 التثبيت مع GPU Support / GPU Installation

```bash
# 1. تثبيت PyTorch مع دعم CUDA / Install PyTorch with CUDA support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 2. تثبيت ONNX Runtime مع دعم GPU (اختياري)
pip install onnxruntime-gpu

# 3. تثبيت بقية الحزم / Install remaining packages
pip install -r requirements.txt

# 4. التحقق من GPU / Verify GPU
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

### 2.4 التثبيت باستخدام Docker / Docker Installation

```bash
# بناء الصورة / Build the image
docker build -t omnifile-processor .

# تشغيل الحاوية / Run the container
docker run -d \
  --name omnifile \
  -p 7860:7860 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/models_cache:/app/models_cache \
  --gpus all \
  omnifile-processor
```

### 2.5 التثبيت على HuggingFace Spaces / HuggingFace Spaces

```bash
# المشروع يحتوي Dockerfile جاهز / Project includes a ready Dockerfile
# 1. أنشئ Space جديد من نوع Docker
# 2. ارفع ملفات المشروع
# 3. سيتم البناء تلقائياً

# أو استخدم git:
git clone https://huggingface.co/spaces/<your-username>/OmniFile_Processor
cd OmniFile_Processor
# انسخ ملفات المشروع ثم ارفع
git add .
git commit -m "Deploy OmniFile AI Processor"
git push
```

---

## 3. التشغيل / Running

### 3.1 واجهة Streamlit (الواجهة الرئيسية) / Streamlit UI (Main Interface)

```bash
# تشغيل عادي / Normal run
streamlit run app.py

# تشغيل بمنفذ محدد / Run on specific port
streamlit run app.py --server.port 8501

# تشغيل للوصول العام / Run for public access
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# إعداد Google Colab / Colab setup
streamlit run app.py --server.port 7860
```

> **ملاحظة / Note:** واجهة Streamlit هي الواجهة الأساسية والموصى بها لمعظم المستخدمين. توفر جميع الميزات في شكل تبويبات منظمة.
> **Note:** Streamlit UI is the primary and recommended interface for most users. It provides all features in organized tabs.

### 3.2 واجهة Gradio (واجهة متقدمة) / Gradio UI (Advanced Interface)

```bash
# تشغيل واجهة Gradio / Run Gradio interface
python -m src.gradio_ui
```

> **ملاحظة / Note:** واجهة Gradio توفر تجربة تفاعلية متقدمة مع دعم أفضل لمعالجة الصور والمعاينة الفورية.
> **Note:** Gradio UI provides an advanced interactive experience with better image processing and instant preview support.

### 3.3 وضع سطر الأوامر / CLI Mode

```bash
# تشغيل وضع CLI / Run in CLI mode
python main.py --cli

# عرض معلومات الإصدار / Show version info
python main.py --version
```

### 3.4 إعداد بيئة Google Colab / Colab Setup

```bash
# إعداد تلقائي لبيئة Colab / Automatic Colab setup
python main.py --colab
```

يقوم هذا الأمر تلقائياً بـ:
- ربط Google Drive
- تثبيت جميع الحزم
- إعداد مسارات التخزين المؤقت

This command automatically:
- Mounts Google Drive
- Installs all packages
- Sets up cache paths

### 3.5 المعالجة غير المتزامنة (Celery) / Async Processing (Celery)

```bash
# 1. تشغيل Redis / Start Redis
redis-server &

# 2. تشغيل عامل Celery / Start Celery worker
celery -A tasks worker --loglevel=info

# 3. تشغيل التطبيق / Run the app
streamlit run app.py
```

> **ملاحظة / Note:** المعالجة غير المتزامنة مفيدة لمعالجة ملفات PDF الكبيرة أو الدفعات الكبيرة من الصور.
> **Note:** Async processing is useful for large PDF files or large batches of images.

---

## 4. الميزات الرئيسية / Key Features

### 4.1 معالجة OCR / OCR Processing

يتضمن النظام ثلاث محركات OCR متكاملة تعمل معاً لتحقيق أفضل دقة:
The system includes three integrated OCR engines working together for maximum accuracy:

#### محرك TrOCR (من Microsoft) / TrOCR Engine (Microsoft)

| الخاصية / Feature | التفاصيل / Details |
|---|---|
| **الأفضل لـ** / Best for | الخط اليدوي، الكلمات المعزولة، الملاحظات |
| **النماذج** / Models | `small` (خفيف), `base` (متوازن), `large` (أدق) |
| **GPU** | يدعم CUDA لتسريع كبير |
| **ONNX** | يمكن تحويله لـ ONNX Runtime |
| **Quantization** | يدعم INT8 لتقليل الذاكرة |

#### محرك EasyOCR / EasyOCR Engine

| الخاصية / Feature | التفاصيل / Details |
|---|---|
| **الأفضل لـ** / Best for | النصوص المطبوعة، النصوص متعددة اللغات |
| **السرعة** / Speed | الأسرع بين المحركات الثلاثة |
| **اللغات** / Languages | 80+ لغة (بما فيها العربية والإنجليزية والألمانية) |
| **GPU** | يدعم CUDA |
| **Batch** | يدعم المعالجة الدفعية |

#### محرك Tesseract / Tesseract Engine

| الخاصية / Feature | التفاصيل / Details |
|---|---|
| **الأفضل لـ** / Best for | النصوص المطبوعة الواضحة، الاستخدام الخفيف |
| **الوزن** / Weight | خفيف جداً، لا يحتاج GPU |
| **اللغات** / Languages | 100+ لغة (تحتاج تثبيت حزم اللغة) |
| **التثبيت** / Install | يحتاج تثبيت على النظام (apt/brew) |

#### إعدادات المحركات / Engine Settings

يمكن التحكم بكل محرك من خلال `OmniFileConfig`:
Each engine can be controlled through `OmniFileConfig`:

```python
from config import OmniFileConfig

cfg = OmniFileConfig()

# تفعيل/تعطيل المحركات / Enable/disable engines
cfg.enable_trocr = True       # تفعيل TrOCR
cfg.enable_easyocr = True     # تفعيل EasyOCR
cfg.enable_tesseract = True   # تفعيل Tesseract

# حجم نموذج TrOCR / TrOCR model size
cfg.trocr_model_variant = "base"  # "small" | "base" | "large"

# التخزين المؤقت / Caching
cfg.ocr_cache_enabled = True     # تفعيل كاش OCR
cfg.ocr_cache_ttl = 3600         # مدة صلاحية الكاش (ثانية)

# تحسين الأداء / Performance optimization
cfg.use_onnx = False            # تسريع ONNX Runtime
cfg.use_quantization = False    # تخفيف دقة INT8
cfg.low_memory = False          # وضع الذاكرة المنخفضة

# معالجات إضافية / Additional settings
cfg.dpi = 300                   # دقة تحويل PDF
cfg.trocr_batch_size = 8       # حجم الدفعة
cfg.num_beams = 4              # عدد أشعة البحث
cfg.easy_conf_threshold = 0.80 # حد الثقة لـ EasyOCR
```

---

### 4.2 التصحيح الإملائي / Spell Correction

المصحح الإملائي الذكي يدعم ثلاث لغات مع حماية المصطلحات التقنية:
The smart spell corrector supports three languages with protection for technical terms:

#### اللغات المدعومة / Supported Languages

| اللغة / Language | المكتبة / Library | ملاحظات / Notes |
|---|---|---|
| **الإنجليزية** / English | `pyspellchecker` | دقة عالية للمصطلحات العامة |
| **العربية** / Arabic | `ar-corrector` | تصحيح متقدم للعربية |
| **الألمانية** / German | `pyspellchecker` | يدعم الأحرف الخاصة (ä, ö, ü, ß) |

#### حماية المصطلحات / Term Protection

يحمي المصحح تلقائياً:
The corrector automatically protects:

- **كلمات Python المحجوزة:** `def`, `class`, `import`, `return`, `if`, `for`, `while` ...
- **أسماء المكتبات:** `numpy`, `pandas`, `torch`, `transformers`, `fastapi` ...
- **المتغيرات:** `snake_case`, `camelCase`, `PascalCase`
- **الأرقام والرموز:** لا يتم تصحيحها أبداً
- **المصطلحات المخصصة:** يمكن إضافة مصطلحات محمية إضافية

#### التعلم من المستخدم / Learning from User

يتعلم المصحح من تصحيحات المستخدم ويحفظها:
The corrector learns from user corrections and saves them:

```python
from modules.nlp.spell_corrector import SpellCorrector

corrector = SpellCorrector()

# تعليم المصحح / Teach the corrector
corrector.learn_correction("omnifle", "omnifile")
corrector.learn_correction("hendwritng", "handwriting")

# التصحيح يحتاج 2 تصحيحات متطابقة ليُفعّل / Corrections need 2 identical votes to activate
# يمكن تغيير الحد بـ min_votes=1 / Can change threshold with min_votes=1
```

---

### 4.3 الترجمة / Translation

المترجم التقني يدعم الترجمة بين ثلاث لغات مع حماية الكود البرمجي:
The technical translator supports translation between three languages with code protection:

#### اتجاهات الترجمة / Translation Directions

| من إلى / From to | النموذج / Model |
|---|---|
| **EN to AR** | `Helsinki-NLP/opus-mt-en-ar` |
| **AR to EN** | `Helsinki-NLP/opus-mt-ar-en` |
| **EN to DE** | `Helsinki-NLP/opus-mt-en-de` |
| **DE to EN** | `Helsinki-NLP/opus-mt-de-en` |
| **DE to AR** | `Helsinki-NLP/opus-mt-de-ar` |
| **AR to DE** | `Helsinki-NLP/opus-mt-ar-de` |

> **ملاحظة / Note:** عند عدم توفر نموذج مباشر، يستخدم النظام الإنجليزية كلغة وسيطة تلقائياً.
> **Note:** When a direct model is unavailable, the system automatically uses English as a pivot language.

#### حماية الكود البرمجي / Code Protection

يحافظ المترجم على المقاطع التالية بدون ترجمة:
The translator preserves the following without translation:

- مقاطع الكود (`` ```python ... ``` `` و `` `inline` ``)
- أسماء المتغيرات (`snake_case`, `camelCase`)
- أسماء الفئات (`PascalCase`)
- أنواع البيانات (`int`, `str`, `bool`, `list`, `dict`)
- كلمات Python المحجوزة
- عناوين URL والبريد الإلكتروني
- الأرقام

#### القاموس التقني / Technical Glossary

يحتوي المترجم على قاموس مدمج لأكثر من 80 مصطلح تقني:
The translator includes a built-in glossary of 80+ technical terms:

| الإنجليزية / English | العربية / Arabic |
|---|---|
| Machine Learning | التعلم الآلي |
| Deep Learning | التعلم العميق |
| Neural Network | الشبكة العصبية |
| Natural Language Processing | معالجة اللغة الطبيعية |
| Computer Vision | الرؤية الحاسوبية |
| Artificial Intelligence | الذكاء الاصطناعي |

```python
from modules.nlp.translator import TechnicalTranslator

translator = TechnicalTranslator()

# ترجمة نص / Translate text
result = translator.translate_text(
    "Machine learning is a subset of artificial intelligence",
    source="en",
    target="ar"
)
print(result["translated_text"])

# ترجمة مستند كامل / Translate a full document
doc_result = translator.translate_document(
    long_text, source="en", target="ar", chunk_size=500
)

# إضافة مصطلح للقاموس / Add term to glossary
translator.add_to_glossary("fine-tuning", "الضبط الدقيق")
```

---

### 4.4 التلخيص / Summarization (جديد v2.1)

ميزة جديدة في v2.1 لتلخيص النصوص الطويلة باستخدام نماذج BART:
New feature in v2.1 for summarizing long texts using BART models:

#### النماذج المدعومة / Supported Models

| اللغة / Language | النموذج / Model | النوع / Type |
|---|---|---|
| **الإنجليزية** / English | `facebook/bart-large-cnn` | تلخيص أخبار |
| **الإنجليزية** / English | `facebook/bart-large-xsum` | تلخيص عام |
| **الإنجليزية** / English | `google/pegasus-xsum` | تلخيص BBC |
| **العربية** / Arabic | `UAE-Code/mbart-summarization-ar` | تلخيص عربي |

#### الميزات / Features

- **كشف اللغة تلقائياً:** يكشف اللغة من النص ويختار النموذج المناسب
- **نموذج احتياطي:** عند فشل النموذج الأساسي، يجرب النموذج الاحتياطي تلقائياً
- **تخزين مؤقت:** يحفظ نتائج التلخيص لتسريع الطلبات المتكررة
- **انحطاط سلس:** إذا تعذر التلخيص، يعيد أول 200 حرف كملخص
- **معالجة دفعية:** يدعم تلخيص مجموعة نصوص مع تتبع التقدم

```python
from modules.nlp.summarizer import TextSummarizer

summarizer = TextSummarizer(
    max_length=130,
    min_length=30,
    enable_cache=True
)

# تلخيص نص / Summarize text
result = summarizer.summarize(long_article)
print(result["summary"])
print(f"نسبة الضغط: {result['compression_ratio']:.1%}")
print(f"اللغة: {result['language']}")
print(f"النموذج: {result['model']}")
print(f"وقت المعالجة: {result['processing_time']:.2f}s")
```

---

### 4.5 فحص البيانات الحساسة / Sensitive Data Scanning (جديد v2.1)

ميزة جديدة في v2.1 لكشف البيانات الحساسة وإخفائها:
New feature in v2.1 for detecting and redacting sensitive data:

#### الأنماط المدعومة / Supported Patterns

| النمط / Pattern | الوصف / Description | مستوى الخطورة / Risk |
|---|---|---|
| **CREDIT_CARD** | بطاقات ائتمانية | عالي / High |
| **EMAIL_ADDRESS** | بريد إلكتروني | متوسط / Medium |
| **PHONE_NUMBER** | أرقام هواتف | متوسط / Medium |
| **IP_ADDRESS** | عناوين IP | منخفض / Low |
| **SSN** | رقم ضمان اجتماعي | عالي / High |
| **API_KEY** | مفاتيح API | عالي / High |
| **JWT_TOKEN** | رموز JWT | عالي / High |
| **AWS_KEY** | مفاتيح AWS | عالي / High |
| **PRIVATE_KEY** | مفاتيح خاصة (RSA, EC, DSA) | حرج / Critical |
| **IBAN** | أرقام IBAN | عالي / High |

#### طرق الفحص / Detection Methods

1. **Presidio (متقدم):** أكثر دقة، يستخدم NLP لتحليل السياق
2. **Regex (احتياطي):** يعمل دائماً بدون مكتبات إضافية

```python
from modules.security.sensitive_data_scanner import SensitiveDataScanner

scanner = SensitiveDataScanner(use_presidio=True)

# فحص نص / Scan text
result = scanner.scan_text("Contact: john@email.com, Card: 4111-1111-1111-1111")
print(f"بيانات حساسة: {result['sensitive_data_found']}")
print(f"مستوى الخطورة: {result['risk_level']}")
print(f"عدد الكيانات: {result['total_entities']}")

# إخفاء البيانات الحساسة / Redact sensitive data
safe_text = scanner.anonymize_text(
    "Card: 4111-1111-1111-1111, Email: john@email.com",
    mask_char="[REDACTED]"
)
print(safe_text)  # Card: [REDACTED], Email: [REDACTED]

# إضافة نمط مخصص / Add custom pattern
scanner.add_custom_pattern(
    name="NATIONAL_ID_SA",
    label="هوية وطنية سعودية",
    regex=r"\b\d{10}\b",
    risk="high"
)
```

---

### 4.6 تنظيم الملفات / File Organization

#### فرز تلقائي حسب النوع / Automatic Sorting by Type

الملفات المعتمدة للتقسيم:
Supported file categories:

| التصنيف / Category | الامتدادات / Extensions |
|---|---|
| **الصور** / Images | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.webp` |
| **المستندات** / Documents | `.pdf`, `.docx`, `.txt`, `.md`, `.rtf` |
| **البيانات** / Data | `.csv`, `.json`, `.xlsx`, `.xml`, `.yaml` |
| **الكود** / Code | `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.h`, `.ipynb` |
| **الأرشيفات** / Archives | `.zip`, `.tar.gz`, `.7z`, `.rar` |

#### فحص أمني للملفات / Security File Scanning

- فحص الامتدادات المعتمدة
- كشف الأنماط المحظورة (passwords, secrets, api_key, token)
- تحديد حجم الملفات
- تسجيل سجل المعالجة

#### النسخ الاحتياطي / Backup

```python
from modules.security.backup_manager import BackupManager

# إنشاء نسخة احتياطية / Create backup
backup = BackupManager.create_backup(source_dir="./data")

# استعادة نسخة / Restore backup
BackupManager.restore_backup(backup_path="./backups/backup_2024.zip")
```

---

### 4.7 استخراج الكيانات المسماة / Named Entity Recognition (NER)

استخراج الأسماء والأماكن والمنظمات من النصوص العربية والإنجليزية:
Extract names, locations, and organizations from Arabic and English texts:

| نوع الكيان / Entity Type | النموذج / Model |
|---|---|
| **PERSON** (أشخاص) | `aubmindlab/bert-base-arabertv02-ner` |
| **ORG** (منظمات) | `aubmindlab/bert-base-arabertv02-ner` |
| **LOC** (أماكن) | `aubmindlab/bert-base-arabertv02-ner` |

### 4.8 تصنيف النصوص / Text Classification

تصنيف المستندات تلقائياً إلى فئات:
Automatic document classification into categories:

```python
from modules.nlp.text_classifier import TextClassifier

classifier = TextClassifier()
result = classifier.classify("This is a research paper about neural networks")
print(result["category"])    # "research"
print(result["confidence"])  # 0.95
```

### 4.9 كشف اللغة / Language Detection

```python
from modules.nlp.language_detector import LanguageDetector

detector = LanguageDetector()
result = detector.detect("هذا نص عربي")
print(result["language"])    # "ar"
print(result["confidence"])  # 0.99
```

---

## 5. اختصارات لوحة المفاتيح / Keyboard Shortcuts

### واجهة Streamlit / Streamlit Interface

| العملية / Action | الاختصار / Shortcut | الوصف / Description |
|---|---|---|
| **رفع ملف** / Upload file | Drag and Drop | سحب وإفلات الملف في منطقة الرفع |
| **تشغيل معالجة** / Run processing | Enter | في حقول الإدخال النصية |
| **حفظ النتائج** / Save results | Ctrl+S | حفظ النص المُعالج (إن توفر) |
| **توسيع تبويب** / Expand tab | الضغط على العنوان | توسيع/طي تبويب في الشريط الجانبي |
| **تحديث الصفحة** / Refresh page | R | إعادة تشغيل التطبيق |
| **إيقاف مؤقت** / Pause | Ctrl+C | إيقاف التطبيق في الطرفية |
| **بحث** / Search | Ctrl+F | بحث في النصوص المعروضة |

### واجهة Gradio / Gradio Interface

| العملية / Action | الاختصار / Shortcut |
|---|---|
| **رفع صورة** / Upload image | Drag and Drop أو النقر على منطقة الرفع |
| **مسح المدخلات** / Clear inputs | زر Clear |
| **إرسال** / Submit | زر Submit أو Enter |

---

## 6. حل المشكلات / Troubleshooting

### 6.1 مشكلة: OCR بطيء / Issue: OCR is Slow

**الأعراض / Symptoms:** المعالجة تستغرق وقتاً طويلاً (> 10 ثوانٍ للصورة الواحدة)

**الحلول / Solutions:**

```python
# 1. فعّل GPU / Enable GPU
cfg.use_gpu = True

# 2. استخدم نموذج TrOCR أصغر / Use a smaller TrOCR model
cfg.trocr_model_variant = "small"  # بدلاً من "base" أو "large"

# 3. فعّل ONNX Runtime لتسريع الاستدلال / Enable ONNX Runtime
cfg.use_onnx = True
# تأكد من تثبيت: pip install onnxruntime

# 4. فعّل Quantization (INT8) لتقليل الذاكرة / Enable Quantization
cfg.use_quantization = True

# 5. عطّل المحركات غير المستخدمة / Disable unused engines
cfg.enable_trocr = False  # إذا كنت تحتاج EasyOCR فقط
# أو استخدم محرك واحد فقط:
cfg.enable_easyocr = True
cfg.enable_tesseract = False

# 6. فعّل التخزين المؤقت / Enable caching
cfg.ocr_cache_enabled = True
cfg.ocr_cache_ttl = 3600  # ساعة واحدة

# 7. قلل دقة تحويل PDF / Reduce PDF conversion DPI
cfg.dpi = 200  # بدلاً من 300
```

---

### 6.2 مشكلة: نفاد الذاكرة (OOM) / Issue: Out of Memory

**الأعراض / Symptoms:** `RuntimeError: CUDA out of memory` أو تجمد النظام

**الحلول / Solutions:**

```python
# 1. فعّل وضع الذاكرة المنخفضة / Enable low memory mode
cfg.low_memory = True

# 2. استخدم نموذج TrOCR-small / Use TrOCR-small model
cfg.trocr_model_variant = "small"

# 3. فعّل Quantization (INT8) / Enable Quantization
cfg.use_quantization = True

# 4. قلل حجم الدفعة / Reduce batch size
cfg.trocr_batch_size = 4  # بدلاً من 8

# 5. عطّل TrOCR واستخدم EasyOCR فقط / Disable TrOCR, use EasyOCR only
cfg.enable_trocr = False
cfg.enable_easyocr = True

# 6. أضف تنظيف الذاكرة / Add memory cleanup
import gc
import torch
torch.cuda.empty_cache()
gc.collect()
```

---

### 6.3 مشكلة: TrOCR لا يعمل / Issue: TrOCR Not Working

**الأعراض / Symptoms:** خطأ عند محاولة استخدام TrOCR، أو النتيجة دائماً من EasyOCR

**الحلول / Solutions:**

```bash
# 1. تأكد من تثبيت المكتبات المطلوبة
pip install transformers torch

# 2. تأكد من إصدار transformers
pip install --upgrade transformers>=4.36.0

# 3. جرب التشغيل على CPU
```

```python
cfg.use_gpu = False  # قسّم المشكلة: هل هي مشكلة GPU؟

# 4. تحقق من توفر المحرك
from modules.vision.ocr_engine import OCREngine
engine = OCREngine()
engines = engine.get_available_engines()
for e in engines:
    print(f"{e['name']}: available={e['available']}, enabled={e['enabled']}")
```

---

### 6.4 مشكلة: الترجمة لا تعمل / Issue: Translation Not Working

**الأعراض / Symptoms:** لا يظهر النص المترجم، أو يظهر رسالة "الترجمة غير متوفرة"

**الحلول / Solutions:**

```bash
# 1. تأكد من اتصال الإنترنت (لتحميل النموذج أول مرة)

# 2. تأكد من تثبيت المكتبات
pip install transformers sentencepiece

# 3. تأكد من إصدار sentencepiece
pip install --upgrade sentencepiece
```

```python
# 4. تحقق من التخزين المؤقت (قد يكون تالفاً)
from modules.nlp.translator import TechnicalTranslator
translator = TechnicalTranslator()
translator.clear_cache()

# 5. تأكد من اللغات المدعومة
print(TechnicalTranslator.SUPPORTED_LANGUAGES)  # ['en', 'ar', 'de']
print(TechnicalTranslator.TRANSLATION_MODELS)
```

---

### 6.5 مشكلة: التلخيص لا يعمل / Issue: Summarization Not Working

**الحلول / Solutions:**

```bash
# تأكد من تثبيت المكتبات
pip install transformers torch

# إذا كنت تواجه مشكلة في نموذج عربي
pip install --upgrade transformers sentencepiece
```

```python
# تحقق من توفر الملخص
from modules.nlp.summarizer import TextSummarizer
summarizer = TextSummarizer()
print(f"متاح: {summarizer.is_available()}")

# تأكد من أن النص طويل بما يكفي (30 كلمة على الأقل)
result = summarizer.summarize("نص قصير جداً")
print(result.get("reason"))  # "text_too_short"
```

---

### 6.6 مشكلة: خطأ في Tesseract / Issue: Tesseract Error

**الأعراض / Symptoms:** `TesseractNotFoundError` أو نتائج فارغة

**الحلول / Solutions:**

```bash
# Ubuntu/Debian:
sudo apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng

# macOS:
brew install tesseract
brew install tesseract-lang  # لغات إضافية

# Windows:
# حمّل من: https://github.com/UB-Mannheim/tesseract/wiki
# أضف مسار Tesseract لمتغيرات البيئة PATH

# التحقق من التثبيت:
tesseract --version
tesseract --list-langs
```

```python
# أو ببساطة عطّل Tesseract واستخدم المحركات الأخرى
cfg.enable_tesseract = False
```

---

### 6.7 مشكلة: أخطاء التبعيات / Issue: Dependency Errors

```bash
# إعادة تثبيت جميع الحزم
pip install -r requirements.txt --force-reinstall

# أو تثبيت الحزم المفقودة فقط:
pip install streamlit>=1.28.0
pip install transformers>=4.36.0
pip install torch>=2.1.0
pip install easyocr>=1.7.0
pip install PyMuPDF>=1.23.0

# تحقق من الحزم المفقودة تلقائياً:
python main.py  # سيظهر تحذير بالحزم المفقودة
```

---

## 7. أسئلة شائعة / FAQ

### Q1: هل يعمل النظام بدون اتصال بالإنترنت؟ / Does the system work offline?

**A:** نعم، بعد تحميل النماذج لأول مرة (يحتاج إنترنت)، يعمل النظام بالكامل بدون اتصال. النماذج تُحفظ في مجلد `models_cache/`.
**A:** Yes, after downloading models for the first time (requires internet), the system works fully offline. Models are cached in `models_cache/`.

### Q2: ما هو أفضل محرك OCR للاستخدام؟ / What is the best OCR engine?

**A:** يعتمد على الاستخدام:
**A:** It depends on the use case:
- **الخط اليدوي:** TrOCR (الأفضل)
- **النصوص المطبوعة متعددة اللغات:** EasyOCR (الأسرع)
- **الاستخدام الخفيف بدون GPU:** Tesseract (الأخف)
- **لأفضل نتيجة:** استخدم الثلاثة معاً (الافتراضي)

### Q3: هل يمكن إضافة لغة جديدة؟ / Can I add a new language?

**A:** نعم، راجع `دليل المطور / Developer Guide` لخطوات إضافة لغة جديدة. باختصار:
**A:** Yes, see the Developer Guide for steps to add a new language. Briefly:
1. أضف الرمز في `supported_languages` في `config.py`
2. أضف مصحح في `spell_corrector.py`
3. أضف نموذج ترجمة في `translator.py`

### Q4: كم يحتاج تحميل النماذج من الوقت؟ / How long does model download take?

**A:** يعتمد على سرعة الإنترنت وحجم النموذج:
**A:** Depends on internet speed and model size:
- **TrOCR-small:** ~400 MB (~2 دقائق)
- **TrOCR-base:** ~800 MB (~4 دقائق)
- **TrOCR-large:** ~1.5 GB (~8 دقائق)
- **EasyOCR (EN+AR):** ~200 MB
- **نماذج الترجمة:** ~300 MB لكل اتجاه

### Q5: كيف أستخدم النظام مع GPU على Google Colab؟ / How to use GPU on Colab?

**A:**
```python
# 1. تأكد من اختيار GPU في Runtime > Change runtime type > T4 GPU
# 2. تحقق:
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")

# 3. الإعدادات ستكشف GPU تلقائياً:
from config import OmniFileConfig
cfg = OmniFileConfig.from_colab_drive()
# cfg.use_gpu سيكون True تلقائياً إذا توفر CUDA
```

### Q6: هل يمكن معالجة ملفات PDF؟ / Can PDF files be processed?

**A:** نعم! النظام يدعم:
**A:** Yes! The system supports:
- استخراج النص المباشر من PDF
- تحويل صفحات PDF إلى صور ومعالجتها بـ OCR
- معالجة PDF متعدد الصفحات مع تتبع التقدم
- دعم PDF الممسوح ضوئياً (scanned PDFs)

### Q7: كيف أحمي كلمة معينة من التصحيح الإملائي؟ / How to protect a word from spell correction?

**A:**
```python
from modules.nlp.spell_corrector import SpellCorrector

corrector = SpellCorrector()

# حماية مؤقتة / Temporary protection
result = corrector.correct_with_protection(
    "my custom term numpy pandas",
    protected_terms=["custom", "term"]
)

# حماية دائمة / Permanent protection
corrector.add_protected_term("OmniFile")
corrector.add_protected_term("TrOCR")
```

### Q8: كيف أنشر النظام على الخادم؟ / How to deploy on a server?

**A:** هناك عدة خيارات:
**A:** Several options available:
1. **Docker:** `docker build -t omnifile . && docker run -p 7860:7860 omnifile`
2. **HuggingFace Spaces:** ارفع المشروع مع Dockerfile
3. **Manual:** `streamlit run app.py --server.port 7860 --server.address 0.0.0.0`
4. **مع Celery:** لتسريع المعالجة غير المتزامنة

### Q9: ما هو الفرق بين v2.0 و v2.1؟ / What's new in v2.1?

**A:**

| الميزة / Feature | v2.0 | v2.1 |
|---|---|---|
| **محركات OCR** | مفعّلة دائماً | قابلة للتفعيل/التعطيل |
| **ONNX Runtime** | غير مدعوم | مدعوم - تسريع الاستدلال |
| **Quantization** | غير مدعوم | مدعوم - INT8 لتقليل الذاكرة |
| **OCR Cache** | غير مدعوم | مدعوم - تخزين مؤقت |
| **Summarization** | غير مدعوم | مدعوم - تلخيص BART |
| **Sensitive Scan** | غير مدعوم | مدعوم - Presidio + Regex |
| **Celery** | غير مدعوم | مدعوم - معالجة غير متزامنة |
| **الوضع الداكن** | غير مدعوم | مدعوم - تخصيص |

### Q10: كيف أساهم في المشروع؟ / How to contribute?

**A:** اتبع الخطوات التالية:
**A:** Follow these steps:
1. Fork المشروع من [GitHub](https://github.com/DrAbdulmalek/OmniFile_Processor)
2. أنشئ branch جديد: `git checkout -b feature/my-feature`
3. اتبع معايير الكود في `دليل المطور / Developer Guide`
4. أضف اختبارات للميزة الجديدة
5. ارفع Pull Request مع وصف واضح

---

> **المؤلف / Author:** Dr. Abdulmalek Tamer Al-husseini
> **الإصدار / Version:** 2.1
> **الترخيص / License:** راجع ملف `LICENSE`
