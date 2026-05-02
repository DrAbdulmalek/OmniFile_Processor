# دليل المطور - OmniFile AI Processor v2.1
# Developer Guide - OmniFile AI Processor v2.1

> **دليل شامل للمطورين لبناء وتوسيع النظام**
> **Comprehensive developer guide for building and extending the system**

---

## المحتويات / Table of Contents

1. [هيكل المشروع / Project Structure](#1-هيكل-المشروع--project-structure)
2. [البنية المعمارية / Architecture](#2-البنية-المعمارية--architecture)
3. [إضافة ميزة جديدة / Adding a New Feature](#3-إضافة-ميزة-جديدة--adding-a-new-feature)
4. [إضافة لغة جديدة / Adding a New Language](#4-إضافة-لغة-جديدة--adding-a-new-language)
5. [إضافة محرك OCR جديد / Adding a New OCR Engine](#5-إضافة-محرك-ocr-جديد--adding-a-new-ocr-engine)
6. [الاختبارات / Testing](#6-الاختبارات--testing)
7. [النشر / Deployment](#7-النشر--deployment)
8. [معايير الكود / Code Standards](#8-معايير-الكود--code-standards)
9. [GitHub Actions CI/CD](#9-github-actions-cicd)

---

## 1. هيكل المشروع / Project Structure

```
OmniFile_Processor/
|
|-- app.py                          # واجهة Streamlit الرئيسية / Main Streamlit UI
|-- main.py                         # نقطة الدخول / Entry point (CLI arguments)
|-- config.py                       # الإعدادات المركزية / Central config (OmniFileConfig dataclass)
|-- database.py                     # قاعدة بيانات SQLite / SQLite database (OmniFileDB)
|-- tasks.py                        # مهام Celery / Celery async tasks
|-- requirements.txt                # التبعيات / Dependencies
|-- Dockerfile                      # Docker للنشر / Docker for deployment
|-- LICENSE                         # الترخيص / License
|-- __init__.py                     # إصدار المشروع / Project version
|
|-- modules/                        # الوحدات الفرعية / Sub-modules
|   |-- __init__.py
|   |
|   |-- nlp/                        # معالجة اللغة الطبيعية / NLP
|   |   |-- __init__.py
|   |   |-- spell_corrector.py      # المصحح الإملائي / Spell corrector (EN/AR/DE)
|   |   |-- translator.py           # المترجم التقني / Technical translator
|   |   |-- summarizer.py           # ملخص النصوص / Text summarizer (BART)
|   |   |-- entity_extractor.py     # استخراج الكيانات / NER entity extraction
|   |   |-- text_classifier.py      # تصنيف النصوص / Text classification
|   |   |-- language_detector.py    # كشف اللغة / Language detection
|   |   |-- correction_dict.json    # قاموس التصحيحات المُتعلمة / Learned corrections
|   |
|   |-- vision/                     # الرؤية الحاسوبية / Computer Vision
|   |   |-- __init__.py
|   |   |-- ocr_engine.py           # محرك OCR المتكامل / Integrated OCR engine
|   |   |-- pdf_processor.py        # معالج PDF / PDF processor
|   |   |-- image_preprocessor.py   # معالجة الصور المسبقة / Image preprocessing
|   |   |-- text_reconstructor.py   # إعادة تجميع النصوص / Text reconstruction
|   |
|   |-- security/                   # الأمان والحماية / Security
|       |-- __init__.py
|       |-- sensitive_data_scanner.py # فحص البيانات الحساسة / Sensitive data scanner
|       |-- file_scanner.py         # فحص الملفات / File scanner
|       |-- file_organizer.py       # تنظيم الملفات / File organizer
|       |-- backup_manager.py       # النسخ الاحتياطي / Backup manager
|       |-- archive_handler.py      # معالجة الأرشيفات / Archive handler
|       |-- code_protector.py       # حماية الكود / Code protection
|
|-- src/                            # محرك HandwrittenOCR المتقدم / Advanced HandwrittenOCR
|   |-- __init__.py
|   |-- main.py                     # نقطة دخول المحرك / Engine entry point
|   |-- gradio_ui.py                # واجهة Gradio المتقدمة / Advanced Gradio UI
|   |-- recognition.py              # التعرف المتقدم / Advanced recognition
|   |-- preprocessing.py            # المعالجة المسبقة المتقدمة / Advanced preprocessing
|   |-- reconstruction.py           # إعادة البناء المتقدمة / Advanced reconstruction
|   |-- correction.py               # التصحيح المتقدم / Advanced correction
|   |-- export.py                   # التصدير / Export
|   |-- pdf_processor.py            # معالج PDF متقدم / Advanced PDF processor
|   |-- review_ui.py                # واجهة المراجعة / Review UI
|   |-- study_guide.py              # دليل الدراسة / Study guide
|   |-- finetuning.py               # التدريب الدقيق / Fine-tuning
|   |-- metrics.py                  # مقاييس الأداء / Performance metrics
|   |-- database.py                 # قاعدة بيانات المحرك / Engine database
|   |-- migration.py                # ترحيل البيانات / Data migration
|   |-- sync.py                     # المزامنة / Synchronization
|   |-- logger.py                   # نظام التسجيل / Logging system
|
|-- tests/                          # الاختبارات / Tests
|   |-- __init__.py
|   |-- conftest.py                 # Fixtures المشتركة / Shared fixtures
|   |-- test_spell_corrector.py     # اختبارات المصحح / Spell corrector tests
|   |-- test_summarizer.py          # اختبارات التلخيص / Summarizer tests
|   |-- test_sensitive_scanner.py   # اختبارات فحص البيانات / Sensitive data tests
|
|-- notebooks/                      | # دفاتر Jupyter / Jupyter notebooks
|   |-- OmniFile_Complete.ipynb     # دفتر شامل / Complete notebook
|   |-- HandwrittenOCR_Ultimate.ipynb
|   |-- HandwrittenOCR_Colab.ipynb
|
|-- data_seed/                      | # بيانات أولية / Seed data
|   |-- correction_dict_seed.json   # بذرة قاموس التصحيح / Corrections seed
|
|-- artifacts/                      | # ملفات مُنتجة / Generated artifacts
|   |-- correction_dict.json
|
|-- database/                       | # ملفات قاعدة البيانات / Database files
|-- data/                           | # بيانات المستخدم / User data
|   |-- raw/                        | # ملفات خام / Raw files
|   |   |-- pdfs/
|   |   |-- images/
|   |   |-- archives/
|   |-- processed/                  | # ملفات معالجة / Processed files
|   |-- exports/                    | # ملفات مُصدّرة / Exported files
|-- models_cache/                   | # تخزين النماذج / Model cache
|-- backups/                        | # نسخ احتياطية / Backups
|-- logs/                           | # سجلات / Logs
|-- docs/                           | # التوثيق / Documentation
```

---

## 2. البنية المعمارية / Architecture

### 2.1 نظرة عامة / Overview

يعتمد النظام على بنية **وحدات (Modular)** مع **تحميل بطيء (Lazy Loading)** و**انحطاط سلس (Graceful Degradation)**:

```
┌─────────────────────────────────────────────────────────────┐
│                    واجهة المستخدم / UI                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Streamlit   │  │   Gradio     │  │      CLI         │   │
│  │  (app.py)    │  │ (gradio_ui)  │  │  (main.py)       │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
└─────────┼─────────────────┼───────────────────┼─────────────┘
          │                 │                   │
          v                 v                   v
┌─────────────────────────────────────────────────────────────┐
│                    الإعدادات / Config                        │
│              OmniFileConfig (config.py)                      │
│     إعدادات OCR | NLP | الأمان | النشر | اللغات             │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          v                v                v
┌─────────────┐   ┌──────────────┐  ┌──────────────┐
│ modules/    │   │ modules/     │  │ modules/     │
│  vision/    │   │  nlp/        │  │  security/   │
│             │   │              │  │              │
│ OCR Engine  │   │ SpellCheck   │  │ SensitiveScan│
│ PDF Process │   │ Translator   │  │ FileOrganize │
│ ImgProcess  │   │ Summarizer   │  │ BackupMgr    │
│ TextRecon   │   │ NER          │  │ CodeProtect  │
│             │   │ Classify     │  │ FileScan     │
│             │   │ LangDetect   │  │ ArchiveHand  │
└──────┬──────┘   └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       v                 v                 v
┌─────────────────────────────────────────────────────────────┐
│                    قاعدة البيانات / Database                  │
│                 OmniFileDB (database.py)                      │
│     documents | ocr_results | translations | entities        │
│     corrections_log | processing_history                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 الوحدات الأساسية / Core Modules

#### `config.py` - الإعدادات المركزية / Central Configuration

فئة `OmniFileConfig` هي Dataclass مركزية تحتوي جميع إعدادات النظام:
The `OmniFileConfig` class is a central dataclass containing all system settings:

```python
from config import OmniFileConfig

# إنشاء إعدادات لبيئة مختلفة / Create config for different environments
cfg_local = OmniFileConfig.from_local(project_root="~/OmniFile_AI")
cfg_colab = OmniFileConfig.from_colab_drive()
cfg_custom = OmniFileConfig(
    use_gpu=True,
    enable_trocr=True,
    trocr_model_variant="small",
)

# حفظ وتحميل الإعدادات / Save and load config
cfg.save("config/settings.json")
cfg_loaded = OmniFileConfig.load("config/settings.json")

# إعداد البيئة / Setup environment
cfg.setup_environment()  # ينشئ المجلدات ويضبط المتغيرات

# خصائص مفيدة / Useful properties
cfg.db_path           # مسار قاعدة البيانات
cfg.data_raw_dir      # مجلد الملفات الخام
cfg.models_cache_dir  # مجلد تخزين النماذج
cfg.is_colab          # كشف بيئة Colab
```

#### `database.py` - قاعدة البيانات / Database

فئة `OmniFileDB` تدير قاعدة بيانات SQLite بوضع WAL:
The `OmniFileDB` class manages an SQLite database in WAL mode:

```python
from database import OmniFileDB

db = OmniFileDB("omnifile_data.db")
db.create_tables()

# إدراج مستند / Insert document
doc_id = db.insert_document({
    "file_name": "test.pdf",
    "file_type": "pdf",
    "raw_text": "Hello World",
    "language": "en",
})

# تحديث مستند / Update document
db.update_document(doc_id, {"corrected_text": "Hello World!", "is_reviewed": True})

# جلب مستند / Get document
doc = db.get_document(doc_id)

# بحث / Search
results = db.search_documents("hello")

# إحصائيات / Statistics
stats = db.get_stats()

# تصدير / Export
db.export_to_json("backup.json")
```

**الجداول / Tables:**
| الجدول / Table | الوصف / Description |
|---|---|
| `documents` | المستندات الأساسية (file_name, raw_text, corrected_text, category, ...) |
| `ocr_results` | نتائج OCR التفصيلية (word_text, confidence, model_source, x, y, w, h) |
| `translations` | الترجمات (source_text, translated_text, source_lang, target_lang) |
| `entities` | الكيانات المسماة (entity_text, entity_type, confidence) |
| `corrections_log` | سجل التصحيحات (original_text, corrected_text, auto_or_manual) |
| `processing_history` | سجل المعالجة (action, target, status, duration_sec) |

#### `app.py` - واجهة Streamlit / Streamlit UI

الواجهة الرئيسية مبنية بتبويبات Streamlit:
The main interface is built with Streamlit tabs:

```python
# app.py يستخدم OmniFileConfig و OmniFileDB
# app.py uses OmniFileConfig and OmniFileDB

# الهيكل العام / General structure:
# - شريط جانبي للإعدادات / Sidebar for settings
# - تبويبات للميزات / Tabs for features
# - رفع الملفات / File upload
# - عرض النتائج / Results display
```

### 2.3 الوحدات الفرعية / Sub-modules

#### `modules/nlp/` - معالجة اللغة الطبيعية / NLP

| الملف / File | الفئة / Class | الوصف / Description |
|---|---|---|
| `spell_corrector.py` | `SpellCorrector` | تصحيح إملائي متعدد اللغات (EN/AR/DE) مع حماية المصطلحات |
| `translator.py` | `TechnicalTranslator` | ترجمة تقنية مع حماية الكود وقاموس مدمج |
| `summarizer.py` | `TextSummarizer` | تلخيص بـ BART مع كشف لغة تلقائي وكاش |
| `entity_extractor.py` | - | استخراج الكيانات المسماة (NER) بـ AraBERT |
| `text_classifier.py` | `TextClassifier` | تصنيف المستندات بـ AraBERTv2 |
| `language_detector.py` | `LanguageDetector` | كشف لغة النص تلقائياً |

#### `modules/vision/` - الرؤية الحاسوبية / Computer Vision

| الملف / File | الفئة / Class | الوصف / Description |
|---|---|---|
| `ocr_engine.py` | `OCREngine` | محرك متكامل (TrOCR + EasyOCR + Tesseract) مع كاش و ONNX |
| `pdf_processor.py` | `PDFProcessor` | معالجة PDF (تحويل صفحات لصور، استخراج نص) |
| `image_preprocessor.py` | `ImagePreprocessor` | معالجة مسبقة (CLAHE, denoise, deskew, binarize) |
| `text_reconstructor.py` | `TextReconstructor` | إعادة تجميع النص من مربعات الكلمات |

#### `modules/security/` - الأمان والحماية / Security

| الملف / File | الفئة / Class | الوصف / Description |
|---|---|---|
| `sensitive_data_scanner.py` | `SensitiveDataScanner` | فحص بيانات حساسة (Presidio + Regex) وإخفائها |
| `file_scanner.py` | - | فحص أمني للملفات (امتدادات، أنماط) |
| `file_organizer.py` | `FileOrganizer` | فرز تلقائي حسب النوع |
| `backup_manager.py` | `BackupManager` | نسخ احتياطي واستعادة |
| `archive_handler.py` | - | معالجة الأرشيفات (zip, tar.gz) |
| `code_protector.py` | - | حماية مقاطع الكود من المعالجة |

#### `src/` - محرك HandwrittenOCR المتقدم / Advanced HandwrittenOCR Engine

محرك متقدم للخط اليدوي مع واجهة Gradio:
Advanced handwriting engine with Gradio interface:

| الملف / File | الوصف / Description |
|---|---|
| `main.py` | نقطة دخول المحرك |
| `gradio_ui.py` | واجهة Gradio المتقدمة |
| `recognition.py` | التعرف المتقدم بالدفعات |
| `preprocessing.py` | معالجة مسبقة متقدمة |
| `reconstruction.py` | إعادة بناء النص |
| `correction.py` | التصحيح المتقدم |
| `finetuning.py` | التدريب الدقيق بـ LoRA |
| `metrics.py` | حساب CER/WER |
| `study_guide.py` | إنشاء أدلة دراسة |

---

## 3. إضافة ميزة جديدة / Adding a New Feature

### مثال عملي: إضافة ميزة Question Answering / Practical Example: Adding QA Feature

### الخطوة 1: إنشاء ملف الوحدة / Step 1: Create the Module File

```python
# modules/nlp/qa_engine.py
"""
محرك الأسئلة والأجوبة (Question Answering Engine) v1.0
==========================================================
إجابة على الأسئلة بناءً على سياق نصي.

المؤلف: Your Name
الإصدار: 1.0.0
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class QAEngine:
    """
    محرك الأسئلة والأجوبة — يجيب على أسئلة بناءً على سياق نصي.

    الميزات:
    - تحميل بطيء (Lazy Loading)
    - كشف GPU تلقائي
    - دعم اللغتين العربية والإنجليزية
    - انحطاط سلس عند الفشل
    """

    # النماذج المدعومة حسب اللغة
    MODELS_BY_LANG = {
        "en": "deepset/roberta-base-squad2",
        "ar": "deepset/roberta-base-squad2",  # يمكن تغييره لنموذج عربي
    }

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        max_answer_length: int = 50,
    ) -> None:
        """
        تهيئة محرك QA.

        المعاملات:
            model_name: اسم النموذج (إذا None، يُختار حسب اللغة)
            device: الجهاز ('cuda' أو 'cpu' أو None لتلقائي)
            max_answer_length: أقصى طول للإجابة
        """
        self.model_name = model_name
        self._device = device or self._detect_device()
        self.max_answer_length = max_answer_length

        # النموذج - تُحمّل بشكل بطيء
        self._pipeline = None
        self._loaded_model_name = None

        # فحص توفر المكتبات
        self._has_transformers = self._check_library("transformers")
        self._has_torch = self._check_library("torch")

    @staticmethod
    def _detect_device() -> str:
        """كشف أفضل جهاز متاح."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except (ImportError, Exception):
            pass
        return "cpu"

    @staticmethod
    def _check_library(import_name: str) -> bool:
        """التحقق من توفر مكتبة."""
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False

    def _load_pipeline(self, model_name: str) -> bool:
        """تحميل نموذج QA (يتم مرة واحدة)."""
        if self._loaded_model_name == model_name and self._pipeline is not None:
            return True

        if not (self._has_transformers and self._has_torch):
            logger.warning(
                "مكتبات transformers/torch غير مثبتة. "
                "pip install transformers torch"
            )
            return False

        try:
            from transformers import pipeline

            logger.info("جارٍ تحميل نموذج QA: %s على %s...", model_name, self._device)
            self._pipeline = pipeline(
                "question-answering",
                model=model_name,
                device=self._device,
            )
            self._loaded_model_name = model_name
            logger.info("تم تحميل نموذج QA بنجاح")
            return True

        except Exception as e:
            logger.error("فشل تحميل نموذج QA '%s': %s", model_name, e)
            return False

    def answer(
        self,
        question: str,
        context: str,
        language: Optional[str] = None,
    ) -> dict:
        """
        الإجابة على سؤال بناءً على سياق.

        المعاملات:
            question: السؤال
            context: النص المرجعي
            language: لغة النص (إذا None، يُكشف تلقائياً)

        العائد:
            قاموس يحتوي:
                - answer: الإجابة
                - score: مستوى الثقة
                - start: بداية الإجابة في السياق
                - end: نهاية الإجابة في السياق
                - model: النموذج المستخدم
        """
        if not question or not context:
            return {
                "answer": "",
                "score": 0.0,
                "start": 0,
                "end": 0,
                "model": "none",
                "error": "question_or_context_empty",
            }

        # اختيار النموذج
        lang = language or "en"
        model_name = self.model_name or self.MODELS_BY_LANG.get(lang, self.MODELS_BY_LANG["en"])

        # تحميل النموذج
        if not self._load_pipeline(model_name):
            return {
                "answer": "النموذج غير متاح",
                "score": 0.0,
                "start": 0,
                "end": 0,
                "model": "none",
                "error": "model_not_loaded",
            }

        # الإجابة
        try:
            result = self._pipeline(
                question=question,
                context=context,
                max_answer_length=self.max_answer_length,
            )
            return {
                "answer": result.get("answer", ""),
                "score": result.get("score", 0.0),
                "start": result.get("start", 0),
                "end": result.get("end", 0),
                "model": self._loaded_model_name,
            }
        except Exception as e:
            logger.error("فشل الإجابة: %s", e)
            return {
                "answer": "",
                "score": 0.0,
                "start": 0,
                "end": 0,
                "model": self._loaded_model_name,
                "error": str(e),
            }

    def is_available(self) -> bool:
        """هل المحرك متاح؟"""
        return self._has_transformers and self._has_torch
```

### الخطوة 2: التسجيل في `__init__.py` / Step 2: Register in `__init__.py`

```python
# modules/nlp/__init__.py
from .qa_engine import QAEngine

__all__ = [
    "QAEngine",
    # ... existing exports
]
```

### الخطوة 3: إضافة التبويب في `app.py` / Step 3: Add Tab in `app.py`

```python
# app.py
import streamlit as st
from modules.nlp.qa_engine import QAEngine


def render_qa_tab(cfg, db):
    """تبويب الأسئلة والأجوبة."""
    st.header("❓ الأسئلة والأجوبة / Question Answering")

    # Initialize engine
    if "qa_engine" not in st.session_state:
        st.session_state.qa_engine = QAEngine(
            device="cuda" if cfg.use_gpu else "cpu"
        )

    qa = st.session_state.qa_engine

    # Input
    question = st.text_input("السؤال / Question", placeholder="e.g., What is machine learning?")
    context = st.text_area(
        "السياق / Context",
        placeholder="Paste the reference text here...",
        height=200,
    )

    if st.button("إجابة / Answer") and question and context:
        with st.spinner("جارٍ البحث عن الإجابة..."):
            result = qa.answer(question, context)

        if result.get("answer"):
            st.success(f"**الإجابة / Answer:** {result['answer']}")
            st.info(f"الثقة / Confidence: {result['score']:.1%}")
        else:
            st.error(f"لم يتم العثور على إجابة: {result.get('error', '')}")
```

### الخطوة 4: تحديث `requirements.txt` / Step 4: Update Requirements

```txt
# NLP - Question Answering
datasets>=2.15.0
# (transformers و torch موجودان بالفعل)
```

### الخطوة 5: كتابة الاختبارات / Step 5: Write Tests

```python
# tests/test_qa_engine.py
"""
اختبارات محرك الأسئلة والأجوبة / QA Engine Tests
"""
import pytest
from modules.nlp.qa_engine import QAEngine


class TestQAEngine:
    """اختبارات فئة QAEngine."""

    def test_init(self):
        """اختبار التهيئة."""
        qa = QAEngine()
        assert qa._device in ("cpu", "cuda")
        assert qa._pipeline is None  # لا يُحمّل تلقائياً

    def test_init_with_model(self):
        """اختبار التهيئة بنموذج محدد."""
        qa = QAEngine(model_name="deepset/roberta-base-squad2")
        assert qa.model_name == "deepset/roberta-base-squad2"

    def test_answer_empty_question(self):
        """اختبار: سؤال فارغ."""
        qa = QAEngine()
        result = qa.answer("", "Some context")
        assert result["answer"] == ""
        assert "error" in result

    def test_answer_empty_context(self):
        """اختبار: سياق فارغ."""
        qa = QAEngine()
        result = qa.answer("What?", "")
        assert result["answer"] == ""
        assert "error" in result

    def test_answer_returns_expected_keys(self):
        """اختبار: مفاتيح النتيجة."""
        qa = QAEngine()
        result = qa.answer("Q", "C")
        expected_keys = {"answer", "score", "start", "end", "model"}
        assert expected_keys.issubset(result.keys())

    def test_is_available(self):
        """اختبار: توفر المحرك."""
        qa = QAEngine()
        # يجب أن يعيد True إذا كانت المكتبات مثبتة
        result = qa.is_available()
        assert isinstance(result, bool)
```

### الخطوة 6: إضافة الإعداد في `config.py` / Step 6: Add Config Setting

```python
# config.py - في OmniFileConfig dataclass
# QA Engine
enable_qa: bool = True
qa_model_name: str = "deepset/roberta-base-squad2"
qa_max_answer_length: int = 50
```

---

## 4. إضافة لغة جديدة / Adding a New Language

### مثال: إضافة اللغة الفرنسية (FR) / Example: Adding French (FR)

### الخطوة 1: تحديث `config.py` / Step 1: Update Config

```python
# config.py
@dataclass
class OmniFileConfig:
    # ...
    supported_languages: list = field(
        default_factory=lambda: ["en", "ar", "de", "fr"]  # أضف "fr"
    )
```

### الخطوة 2: إضافة مصحح في `spell_corrector.py` / Step 2: Add Corrector

```python
# modules/nlp/spell_corrector.py

class SpellCorrector:
    def __init__(self, ...):
        # ...
        self.supported_languages = ["en", "ar", "de", "fr"]  # أضف "fr"

        # محاولة تحميل المصحح الفرنسي
        self._fr_corrector = None
        self._fr_available = False
        self._try_load_french_corrector()

    def _try_load_french_corrector(self) -> None:
        """محاولة تحميل مصحح الفرنسية (pyspellchecker)."""
        try:
            from spellchecker import SpellChecker
            self._fr_corrector = SpellChecker(language="fr")
            self._fr_available = True
            logger.info("تم تحميل مصحح الفرنسية (pyspellchecker) بنجاح")
        except ImportError:
            logger.warning("مكتبة pyspellchecker غير مثبتة. pip install pyspellchecker")
        except Exception as e:
            logger.warning("فشل تحميل مصحح الفرنسية: %s", e)

    @staticmethod
    def _is_french_word(word: str) -> bool:
        """هل الكلمة فرنسية؟"""
        french_chars = sum(1 for c in word if c in "àâäéèêëïîôùûüÿçœæÀÂÄÉÈÊËÏÎÔÙÛÜŸÇŒÆ")
        if french_chars > 0:
            return True
        latin_chars = sum(1 for c in word if c.isalpha() and c.isascii())
        arabic_chars = sum(1 for c in word if "\u0600" <= c <= "\u06FF")
        return latin_chars > len(word) * 0.5 and arabic_chars == 0

    def _correct_french_word(self, word: str) -> Optional[str]:
        """تصحيح كلمة فرنسية."""
        if word in self._protected_terms or word.lower() in self._protected_terms:
            return None
        learned = self._get_learned_correction(word)
        if learned:
            return learned
        if self._fr_available and self._fr_corrector:
            try:
                if len(word) <= 2:
                    return None
                if word.lower() in self._fr_corrector.word_frequency:
                    return None
                candidates = self._fr_corrector.correction(word)
                if candidates and candidates.lower() != word.lower():
                    if abs(len(candidates) - len(word)) <= 3:
                        return candidates
            except Exception as e:
                logger.debug("خطأ في تصحيح فرنسي '%s': %s", word, e)
        return None

    def correct_word(self, word: str) -> str:
        """تصحيح كلمة واحدة (محدّث لدعم الفرنسية)."""
        if self._should_skip_word(word):
            return word
        if self._is_arabic_word(word):
            correction = self._correct_arabic_word(word)
        elif self._is_french_word(word):      # <-- أضف هذا الشرط قبل الإنجليزية
            correction = self._correct_french_word(word)
        elif self._is_german_word(word):
            correction = self._correct_german_word(word)
        elif self._is_english_word(word):
            correction = self._correct_english_word(word)
        else:
            return word
        return correction if correction else word

    def is_available(self) -> dict:
        """فحص توفر المصححات (محدّث)."""
        return {
            "english": self._en_available,
            "arabic": self._ar_available,
            "german": self._de_available,
            "french": self._fr_available,  # <-- أضف هذا
            "learned": len(self._learned_corrections) > 0,
        }
```

### الخطوة 3: إضافة نموذج ترجمة في `translator.py` / Step 3: Add Translation Model

```python
# modules/nlp/translator.py

class TechnicalTranslator:
    TRANSLATION_MODELS: dict[str, str] = {
        # ... existing models ...
        # أضف الاتجاهات الجديدة:
        "en-fr": "Helsinki-NLP/opus-mt-en-fr",
        "fr-en": "Helsinki-NLP/opus-mt-fr-en",
        "fr-ar": "Helsinki-NLP/opus-mt-fr-ar",
        "ar-fr": "Helsinki-NLP/opus-mt-ar-fr",
        "fr-de": "Helsinki-NLP/opus-mt-fr-de",
        "de-fr": "Helsinki-NLP/opus-mt-de-fr",
    }

    SUPPORTED_LANGUAGES = ["en", "ar", "de", "fr"]  # أضف "fr"
```

### الخطوة 4: إضافة نموذج تلخيص (اختياري) / Step 4: Add Summarization Model (Optional)

```python
# modules/nlp/summarizer.py

class TextSummarizer:
    MODELS_BY_LANG = {
        # ... existing models ...
        "fr": [
            "mrm8488/camembert2camembert_shared-french-summarization",
        ],
    }

    FALLBACK_MODELS = {
        # ... existing models ...
        "fr": "mrm8488/camembert2camembert_shared-french-summarization",
    }
```

### الخطوة 5: تحديث كشف اللغة / Step 5: Update Language Detection

```python
# modules/nlp/summarizer.py - _detect_language()
@staticmethod
def _detect_language(text: str) -> str:
    """كشف لغة النص."""
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    german_chars = sum(1 for c in text if c in "äöüÄÖÜß")
    french_chars = sum(1 for c in text if c in "àâäéèêëïîôùûüÿçœæÀÂÄÉÈÊËÏÎÔÙÛÜŸÇŒÆ")

    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha == 0:
        return "en"

    if arabic_chars / total_alpha > 0.3:
        return "ar"
    if french_chars / total_alpha > 0.05:   # <-- أضف هذا قبل الألمانية
        return "fr"
    if german_chars / total_alpha > 0.05:
        return "de"
    return "en"
```

### الخطوة 6: اختبارات اللغة الجديدة / Step 6: Tests for New Language

```python
# tests/test_spell_corrector.py
class TestFrenchCorrection:
    """اختبارات التصحيح الفرنسي."""

    def test_correct_french_word(self):
        """اختبار تصحيح كلمة فرنسية."""
        corrector = SpellCorrector()
        if corrector.is_available().get("french"):
            result = corrector.correct_word("bonjor")  # خطأ إملائي
            assert result == "bonjour"

    def test_protect_french_code(self):
        """اختبار حماية الكود مع فرنسية."""
        corrector = SpellCorrector()
        result = corrector.correct_word("numpy")  # لا يُصحح
        assert result == "numpy"
```

---

## 5. إضافة محرك OCR جديد / Adding a New OCR Engine

### واجهة المحرك / Engine Interface

كل محرك OCR جديد يجب أن يوفر الواجهة التالية:
Every new OCR engine must provide the following interface:

```python
from typing import Optional, Union
import numpy as np
from PIL import Image


class NewOCREngine:
    """
    واجهة محرك OCR جديد.
    يجب أن يوفر: recognize, recognize_batch, recognize_pdf, get_available_engines, unload_models
    """

    def __init__(self, **kwargs):
        """تهيئة المحرك."""
        self._model = None
        self._loaded = False

    def recognize(
        self,
        image: Union[np.ndarray, Image.Image],
        languages: Optional[list[str]] = None,
    ) -> dict:
        """
        التعرف على النص في صورة واحدة.

        المعاملات:
            image: صورة PIL أو numpy array
            languages: لغات مطلوبة

        العائد:
            dict: {
                "text": str,           # النص المستخرج
                "confidence": float,   # مستوى الثقة (0-1)
                "source": str,         # اسم المحرك
                "word_count": int,     # عدد الكلمات
                "words": list[dict],   # تفاصيل الكلمات مع الإحداثيات
                "processing_time": float,
                "details": dict,
            }
        """
        raise NotImplementedError

    def recognize_batch(
        self,
        images: list[Union[np.ndarray, Image.Image]],
        languages: Optional[list[str]] = None,
    ) -> list[dict]:
        """التعرف على مجموعة صور."""
        return [self.recognize(img, languages) for img in images]

    def recognize_pdf(
        self,
        pdf_path: str,
        pages: Optional[list[int]] = None,
        languages: Optional[list[str]] = None,
    ) -> list[dict]:
        """استخراج النص من PDF."""
        raise NotImplementedError

    def get_available_engines(self) -> list[dict]:
        """قائمة المحركات المتاحة."""
        return [{"name": "NewOCR", "available": True, "enabled": True}]

    def unload_models(self) -> None:
        """تفريغ النماذج من الذاكرة."""
        self._model = None
        self._loaded = False
```

### التسجيل في `OCREngine` / Register in OCREngine

```python
# modules/vision/ocr_engine.py

class OCREngine:
    def __init__(self, ...):
        # ... existing engines ...
        self._new_ocr_reader = None
        self._new_ocr_loaded = False

    def _recognize_new_ocr(self, image):
        """التعرف باستخدام المحرك الجديد."""
        # ... implementation ...
        pass

    def recognize(self, image, languages=None):
        # ... existing code ...
        # أضف المحرك الجديد في سلسلة المحركات:
        if self.enable_new_ocr:
            new_result = self._recognize_new_ocr(pil_image)
            if new_result:
                results.append(new_result)
        # ... rest of method ...
```

---

## 6. الاختبارات / Testing

### تشغيل الاختبارات / Running Tests

```bash
# تشغيل جميع الاختبارات / Run all tests
pytest tests/ -v

# تشغيل اختبار محدد / Run specific test
pytest tests/test_spell_corrector.py -v

# تشغيل مع تغطية الكود / Run with coverage
pytest tests/ --cov=modules --cov-report=html

# تشغيل اختبارات وحدة محددة / Run specific test class
pytest tests/test_spell_corrector.py::TestSpellCorrector::test_correct_word -v

# عرض الإخراج المطبوع / Show print output
pytest tests/ -v -s
```

### كتابة اختبار جديد / Writing a New Test

```python
# tests/test_qa_engine.py
"""
اختبارات محرك QA / QA Engine Tests

النمط المتبع: Arrange - Act - Assert
"""
import pytest


class TestQAEngine:
    """اختبارات فئة QAEngine."""

    def setup_method(self):
        """إعداد قبل كل اختبار (Arrange)."""
        from modules.nlp.qa_engine import QAEngine
        self.qa = QAEngine()

    # === اختبارات الحالة السعيدة / Happy Path Tests ===

    def test_answer_returns_dict(self):
        """اختبار: answer() يعيد dict."""
        result = self.qa.answer("What?", "Context text")
        assert isinstance(result, dict)

    def test_answer_has_required_keys(self):
        """اختبار: النتيجة تحتوي المفاتيح المطلوبة."""
        result = self.qa.answer("Q", "C")
        for key in ["answer", "score", "start", "end", "model"]:
            assert key in result, f"Missing key: {key}"

    def test_answer_score_is_float(self):
        """اختبار: score هو رقم بين 0 و 1."""
        result = self.qa.answer("Q", "C")
        assert isinstance(result["score"], (int, float))
        assert 0 <= result["score"] <= 1

    # === اختبارات الحالات الخطأ / Error Case Tests ===

    def test_answer_empty_question(self):
        """اختبار: سؤال فارغ يعيد خطأ."""
        result = self.qa.answer("", "Context")
        assert result["answer"] == ""
        assert "error" in result

    def test_answer_empty_context(self):
        """اختبار: سياق فارغ يعيد خطأ."""
        result = self.qa.answer("Question", "")
        assert result["answer"] == ""
        assert "error" in result

    def test_answer_none_inputs(self):
        """اختبار: مدخلات None لا تسبب crash."""
        result = self.qa.answer(None, None)
        assert isinstance(result, dict)

    # === اختبارات التهيئة / Initialization Tests ===

    def test_lazy_loading(self):
        """اختبار: النموذج لا يُحمّل تلقائياً."""
        qa = QAEngine()
        assert qa._pipeline is None

    def test_custom_model_name(self):
        """اختبار: تمرير اسم نموذج مخصص."""
        qa = QAEngine(model_name="custom-model")
        assert qa.model_name == "custom-model"
```

### Fixtures المشتركة / Shared Fixtures

```python
# tests/conftest.py
"""
Fixtures المشتركة لجميع الاختبارات.
"""
import pytest
import numpy as np
from PIL import Image


@pytest.fixture
def sample_text_en():
    """نص إنجليزي بسيط."""
    return "This is a sample text for testing."


@pytest.fixture
def sample_text_ar():
    """نص عربي بسيط."""
    return "هذا نص عربي للاختبار."


@pytest.fixture
def sample_image():
    """صورة اختبار بسيطة."""
    return Image.new("RGB", (200, 100), color="white")


@pytest.fixture
def sample_pdf_path(tmp_path):
    """مسار PDF اختبار مؤقت."""
    pdf_path = tmp_path / "test.pdf"
    return str(pdf_path)


@pytest.fixture
def sample_config():
    """إعدادات اختبار."""
    from config import OmniFileConfig
    return OmniFileConfig(
        use_gpu=False,
        enable_trocr=False,
        enable_easyocr=False,
        enable_tesseract=False,
    )


@pytest.fixture
def sample_db(tmp_path):
    """قاعدة بيانات اختبار مؤقتة."""
    from database import OmniFileDB
    db_path = str(tmp_path / "test.db")
    db = OmniFileDB(db_path)
    db.create_tables()
    yield db
    # cleanup
```

---

## 7. النشر / Deployment

### 7.1 HuggingFace Spaces (Docker) / HuggingFace Spaces

المشروع يحتوي `Dockerfile` جاهز. للنشر:
The project includes a ready `Dockerfile`. To deploy:

```dockerfile
# Dockerfile (موجود بالفعل / already exists)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose Streamlit default port
EXPOSE 7860

# Health check
HEALTHCHECK CMD curl -f http://localhost:7860/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
```

### 7.2 Docker Compose (مع Redis) / Docker Compose (with Redis)

```yaml
# docker-compose.yml
version: '3.8'

services:
  omnifile:
    build: .
    ports:
      - "7860:7860"
    environment:
      - ENABLE_CELERY=true
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - ./models_cache:/app/models_cache
      - ./database:/app/database
    depends_on:
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  celery-worker:
    build: .
    command: celery -A tasks worker --loglevel=info
    environment:
      - ENABLE_CELERY=true
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - ./models_cache:/app/models_cache
    depends_on:
      - redis

volumes:
  redis_data:
```

```bash
# تشغيل / Run
docker-compose up -d

# مشاهدة السجلات / View logs
docker-compose logs -f omnifile

# إيقاف / Stop
docker-compose down
```

### 7.3 Google Colab / Google Colab

```python
# main.py --colab
# أو:
from config import OmniFileConfig
cfg = OmniFileConfig.from_colab_drive()
cfg.setup_environment()

# ثم:
!streamlit run app.py --server.port 7860
```

### 7.4 AWS / Azure / GCP

```bash
# باستخدام Docker / Using Docker
# AWS ECS:
docker build -t omnifile .
aws ecs register-task-definition --family omnifile --container-definitions ...

# Azure Container Apps:
az containerapp create --image omnifile ...

# GCP Cloud Run:
gcloud run deploy omnifile --source . --port 7860
```

### 7.5 Celery Workers (المعالجة غير المتزامنة) / Celery Workers

```bash
# 1. تشغيل Redis
redis-server &

# 2. تشغيل Worker
celery -A tasks worker --loglevel=info --concurrency=4

# 3. تشغيل Worker مع مراقبة
celery -A tasks worker --loglevel=info --concurrency=2 \
  --max-tasks-per-child=1000 \
  --time-limit=300 \
  --soft-time-limit=240

# 4. مراقبة المهام
celery -A tasks inspect active
celery -A tasks inspect reserved
celery -A tasks events --dump
```

---

## 8. معايير الكود / Code Standards

### 8.1 التنسيق / Formatting

```python
# 1. Python 3.8+ type hints
def process_text(text: str, language: str = "en") -> dict:
    ...

# 2. توثيق عربي + إنجليزي
class SpellCorrector:
    """
    مصحح إملائي ذكي — يدعم العربية والإنجليزية مع حماية المصطلحات البرمجية.
    Smart spell corrector — supports Arabic and English with code term protection.

    الميزات / Features:
        - تصحيح متعدد اللغات
        - حماية المصطلحات التقنية
        - تعلم من المستخدم
    """

    def correct_word(self, word: str) -> str:
        """
        تصحيح كلمة واحدة.
        Correct a single word.

        المعاملات:
            word: الكلمة المراد تصحيحها / The word to correct

        العائد:
            الكلمة المصححة / The corrected word
        """
        ...
```

### 8.2 التسجيل / Logging

```python
# استخدم logging بدلاً من print / Use logging instead of print

import logging
logger = logging.getLogger(__name__)

# الصحيح / Correct:
logger.info("تم تحميل النموذج: %s", model_name)
logger.warning("فشل التحميل: %s", error)
logger.error("خطأ حرج: %s", error, exc_info=True)
logger.debug("قيمة متغيرة: %s", value)

# الخاطئ / Wrong:
print("تم التحميل")           # لا تستخدم print في الإنتاج
print(f"Error: {error}")      # لا تستخدم print
```

### 8.3 معالجة الأخطاء / Error Handling

```python
# 1. Graceful Degradation - انحطاط سلس
try:
    from presidio_analyzer import AnalyzerEngine
    self._analyzer = AnalyzerEngine()
    self._presidio_available = True
except ImportError:
    logger.warning("presidio غير مثبت. سيتم استخدام Regex فقط.")
    self._presidio_available = False
except Exception as e:
    logger.warning("فشل تحميل presidio: %s", e)
    self._presidio_available = False

# 2. لا تستخدم except: فارغ / Never use bare except:
try:
    ...
except:  # خاطئ / Wrong
    pass

# 3. حدد نوع الاستثناء / Specify exception type
try:
    ...
except (ValueError, TypeError) as e:  # صحيح / Correct
    logger.error("خطأ: %s", e)
```

### 8.4 تحميل بطيء / Lazy Loading

```python
# النماذج الثقيلة لا تُحمّل في __init__ / Heavy models don't load in __init__

class MyEngine:
    def __init__(self):
        self._model = None        # لا تحميل هنا / Don't load here
        self._loaded = False

    def _load_model(self) -> bool:
        """تحميل النموذج عند أول استخدام / Load model on first use."""
        if self._loaded:
            return True
        try:
            self._model = load_heavy_model()
            self._loaded = True
            return True
        except Exception as e:
            logger.error("فشل التحميل: %s", e)
            return False

    def process(self, data):
        if not self._load_model():  # تحميل عند الحاجة / Load when needed
            return self._fallback(data)
        return self._model.process(data)
```

### 8.5 إدارة الذاكرة / Memory Management

```python
# 1. تنظيف الذاكرة بعد المعالجة
import gc
import torch

def process_batch(images):
    results = []
    for img in images:
        result = process(img)
        results.append(result)
    
    # تنظيف / Cleanup
    torch.cuda.empty_cache()
    gc.collect()
    return results

# 2. تفريغ النماذج عند الحاجة
def unload_models(self):
    """تفريغ النماذج من الذاكرة."""
    self._model = None
    self._loaded = False
    torch.cuda.empty_cache()
    gc.collect()
```

### 8.6 دعم اللغات / Language Support

```python
# كل نص مرئي للمستخدم يجب أن يكون ثنائي اللغة
# All user-visible text must be bilingual

# أسماء المتغيرات والدوال: إنجليزية / Variable and function names: English
def correct_text(text: str) -> dict:

# الرسائل والتوثيق: عربي + إنجليزي / Messages and docs: Arabic + English
logger.info("تم تحميل المصحح بنجاح / Spell corrector loaded successfully")
st.success("تمت المعالجة بنجاح / Processing completed successfully")

# أخطاء: عربي + إنجليزي / Errors: Arabic + English
raise ValueError("حقل file_name مطلوب / file_name field is required")
```

---

## 9. GitHub Actions CI/CD

### 9.1 اختبارات تلقائية / Automated Tests

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y tesseract-ocr tesseract-ocr-ara

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          pytest tests/ -v --cov=modules --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff
      - run: ruff check modules/ src/ tests/
```

### 9.2 بناء Docker / Docker Build

```yaml
# .github/workflows/docker.yml
name: Docker Build

on:
  push:
    tags: ['v*']
  workflow_dispatch:

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to DockerHub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/omnifile-processor:latest
            ${{ secrets.DOCKER_USERNAME }}/omnifile-processor:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 9.3 نشر على HuggingFace Spaces / Deploy to HuggingFace Spaces

```yaml
# .github/workflows/deploy.yml
name: Deploy to HuggingFace

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Push to HuggingFace
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git clone https://DrAbdulmalek:$HF_TOKEN@huggingface.co/spaces/DrAbdulmalek/OmniFile_Processor hf_space
          rsync -av --delete --exclude='.git' ./ hf_space/
          cd hf_space
          git add .
          git commit -m "Deploy from GitHub Actions"
          git push
```

---

> **المؤلف / Author:** Dr. Abdulmalek
> **الإصدار / Version:** 2.1
> **الترخيص / License:** راجع ملف `LICENSE`
> **المساهمة / Contributing:** Pull Requests مرحب بها على branch `develop`
