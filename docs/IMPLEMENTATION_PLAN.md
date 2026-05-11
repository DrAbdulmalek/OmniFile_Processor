# خطة التنفيذ الشاملة — OmniFile Processor v5.0

> **الإصدار:** 5.0 | **التاريخ:** يونيو 2025 | **الحالة:** مسودة قيد المراجعة  
> **المؤلف:** Dr. Abdulmalek Tamer Al-husseini

---

## جدول المحتويات

1. [توحيد الطبقة التنفيذية — src/ إلى modules/](#1-توحيد-الطبقة-التنفيذية--src-إلى-modules)
2. [تحسين التوثيق — docs/examples/arabic/](#2-تحسين-التوثيق--docsexamplesarabic)
3. [تقليل الاعتماديات — ملفات requirements متخصصة](#3-تقليل-الاعتماديات--ملفات-requirements-متخصصة)
4. [واجهة إدارة المعالجة الجماعية — Batch Dashboard](#4-واجهة-إدارة-المعالجة-الجماعية--batch-dashboard)
5. [نظام OCR للخط اليدوي — Handwriting Recognition](#5-نظام-ocr-للخط-اليدوي--handwriting-recognition)
6. [نظام التقسيم الذكي — Arabic Segmentation](#6-نظام-التقسيم-الذكي--arabic-segmentation)
7. [محرك OCR المختلط — MixedLanguageOCR](#7-محرك-ocr-المختلط--mixedlanguageocr)
8. [التدريب والتعلم — Training & Learning Loop](#8-التدريب-والتعلم--training--learning-loop)
9. [معالجة الملاحظات الطبية — AdvancedMedicalOCR](#9-معالجة-الملاحظات-الطبية--advancedmedicalocr)
10. [الجدول الزمني — Timeline (7 أسابيع)](#10-الجدول-الزمني--timeline-7-أسابيع)

---

## هيكل المشروع المستهدف

```
OmniFile_Processor/
├── modules/                          # الطبقة التنفيذية الموحدة
│   ├── core/                         # الوظائف الأساسية
│   │   ├── engine_router.py          # توجيه المحركات
│   │   ├── database_manager.py       # إدارة قواعد البيانات
│   │   ├── spell_checker.py          # التصحيح الإملائي
│   │   ├── classifier.py             # تصنيف المستندات
│   │   ├── handwriting_db.py         # قاعدة بيانات الخطوط
│   │   └── migration/                # أدوات الترحيل
│   ├── vision/                       # معالجة الصور و OCR
│   │   ├── ocr_engine.py             # محرك OCR الرئيسي
│   │   ├── pdf_processor.py          # معالجة PDF
│   │   ├── image_preprocessor.py     # تجهيز الصور
│   │   ├── layout_analyzer.py        # تحليل التخطيط
│   │   ├── table_extractor.py        # استخراج الجداول
│   │   ├── data_augmentation.py      # تعزيز البيانات
│   │   └── htr/                      # التعرف على الخط اليدوي
│   │       ├── arabic_htr.py         # الأنبوب الرئيسي
│   │       ├── line_segmenter.py     # تجزئة الأسطر
│   │       ├── word_segmenter.py     # تجزئة الكلمات
│   │       ├── trocr_finetuned.py    # TrOCR المُضبَط
│   │       └── dotted_recovery.py    # استرداد النقاط
│   ├── medical/                      # معالجة الملاحظات الطبية (جديد)
│   │   ├── medical_ocr_reviewer.py   # المراجعة الطبية
│   │   ├── terminology_guard.py      # حماية المصطلحات
│   │   └── medical_patterns.json     # أنماط طبية
│   ├── nlp/                          # معالجة اللغة
│   │   ├── language_detector.py      # كشف اللغة
│   │   ├── translator.py             # الترجمة
│   │   ├── spell_corrector.py        # التصحيح الإملائي
│   │   ├── mixed_language.py         # المعالجة ثنائية اللغة
│   │   ├── arabic_rtl.py             # معالجة RTL
│   │   └── protected_words.py        # الكلمات المحمية
│   ├── ai/                           # الذكاء الاصطناعي
│   │   ├── pattern_db.py             # قاعدة أنماط SQLite
│   │   ├── pattern_matcher.py        # مطابقة الأنماط
│   │   ├── active_learning.py        # التعلم النشط
│   │   ├── finetuning.py             # الضبط الدقيق
│   │   └── gateway/                  # بوابة AI
│   │       ├── server.py             # خادم API
│   │       ├── api/                  # نقاط النهاية
│   │       ├── providers/            # مزودو الخدمة
│   │       └── pool/                 # إدارة المجمعات
│   ├── export/                       # التصدير
│   ├── security/                     # الأمان
│   ├── ui/                           # واجهات المستخدم
│   └── config/                       # الإعدادات
├── src/                              # طبقة التوافق العكسي (deprecated)
│   ├── __init__.py                   # إعادة تصدير من modules/
│   ├── main.py                       # → modules.core.engine_router
│   ├── recognition.py                # → modules.vision.ocr_engine
│   ├── preprocessing.py              # → modules.vision.image_preprocessor
│   ├── export.py                     # → modules.export.exporter
│   └── ...
├── backend/                          # واجهة Batch Dashboard
│   ├── main.py                       # FastAPI server
│   ├── batch_manager.py              # إدارة الدفعات
│   └── api/
│       ├── batch_api.py              # WebSocket + REST
│       └── training.py               # API التدريب
├── frontend/                         # React Dashboard
│   ├── src/
│   │   ├── components/dashboard/     # مكونات الداشبورد
│   │   └── hooks/useWebSocket.js     # WebSocket hook
│   └── package.json
├── notebooks/                        # دفاتر Colab التفاعلية
│   ├── Medical_OCR_Review_Colab.py
│   └── TrOCR_FineTuning_Colab.py
├── training/                         # أدوات التدريب
│   ├── configs/trocr_lora_arabic.yaml
│   ├── models/lora_htr_trainer.py
│   └── scripts/
├── docs/                             # التوثيق
│   ├── examples/arabic/              # أمثلة عربية
│   ├── guides/                       # أدلة متخصصة
│   └── IMPLEMENTATION_PLAN.md        # هذا الملف
├── requirements-base.txt             # الاعتماديات الأساسية
├── requirements-ocr-basic.txt        # OCR أساسي
├── requirements-ocr-advanced.txt     # OCR متقدم
├── requirements-nlp-arabic.txt       # NLP عربي
├── requirements-ai-gateway.txt       # AI Gateway
├── requirements-deployment.txt       # النشر
└── pyproject.toml                    # إعدادات المشروع
```

---

## 1. توحيد الطبقة التنفيذية — src/ إلى modules/

### المشكلة الحالية

المشروع يحتوي على طبقتين تنفيذيتين:
- `src/` — الطبقة القديمة (monolithic)، تحتوي 16 ملفًا
- `modules/` — الطبقة الجديدة (modular)، منظمة في 12 حزمة فرعية

هذا التكرار يسبب:
1. **تناقض في السلوك** عند استدعاء نفس الوظيفة من مسارين مختلفين
2. **صعوبة الصيانة** — كل تعديل يتطلب تحديث ملفين
3. **عدم وضوح** للمساهمين الجدد حول أي طبقة يجب استخدامها

### خطة النقل

#### المرحلة 1: طبقة التوافق العكسي (Backward Compatibility)

تحويل `src/__init__.py` إلى طبقة إعادة تصدير (re-export shim):

```python
# src/__init__.py — طبقة التوافق العكسي
"""
هذه الطبقة موجودة لأغراض التوافق فقط.
جميع الوظائف انتقلت إلى modules/.
لا تضف كودًا جديدًا هنا.
"""
import warnings

def __getattr__(name):
    """إعادة توجيه الواردات إلى modules/ مع تحذير."""
    _COMPAT_MAP = {
        "OCREngine": ("modules.vision.ocr_engine", "OCREngine"),
        "ImagePreprocessor": ("modules.vision.image_preprocessor", "ImagePreprocessor"),
        "PDFProcessor": ("modules.vision.pdf_processor", "PDFProcessor"),
        "BatchManager": ("backend.batch_manager", "BatchManager"),
        "HybridSpellChecker": ("modules.core.spell_checker", "HybridSpellChecker"),
        "LanguageDetector": ("modules.nlp.language_detector", "LanguageDetector"),
        "Translator": ("modules.nlp.translator", "Translator"),
        "PatternDatabase": ("modules.ai.pattern_db", "PatternDatabase"),
        "Exporter": ("modules.export.exporter", "Exporter"),
    }
    if name in _COMPAT_MAP:
        module_path, attr = _COMPAT_MAP[name]
        warnings.warn(
            f"استيراد {name} من src/ مُهمَل. استخدم: from {module_path} import {attr}",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    raise AttributeError(f"الوحدة 'src' ليس لها خاصية '{name}'")
```

#### المرحلة 2: ترحيل الوظائف المفقودة

تحديد الوظائف الموجودة في `src/` لكنها غير موجودة في `modules/` ونقلها:

| ملف src/ | الوظيفة | الوجهة في modules/ |
|-----------|---------|-------------------|
| `src/recognition.py` | `recognize_from_image()` | `modules.vision.ocr_engine` |
| `src/preprocessing.py` | `enhance_handwriting()` | `modules.vision.image_preprocessor` |
| `src/correction.py` | `auto_correct_arabic()` | `modules.nlp.spell_corrector` |
| `src/gradio_ui.py` | واجهة Gradio | `modules.ui.gradio_app` |
| `src/review_ui.py` | واجهة المراجعة | `modules.ui.review_app` (جديد) |

#### المرحلة 3: تحديث الاختبارات

```python
# tests/test_migration_compat.py — اختبار التوافق العكسي
import pytest
import warnings

def test_src_imports_redirect_to_modules():
    """التحقق من أن استيراد src/ يعمل ويعطي تحذير الإهمال."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from src import OCREngine
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
    
    # التحقق من أن النتيجة هي نفس الكائن
    from modules.vision.ocr_engine import OCREngine as DirectOCREngine
    assert OCREngine is DirectOCREngine
```

#### معايير النجاح

- [ ] جميع الواردات من `src/` تعمل مع تحذير `DeprecationWarning`
- [ ] لا يوجد كود مكرر بين `src/` و `modules/`
- [ ] جميع الاختبارات تمر باستخدام الواردات الجديدة فقط
- [ ] تحديث `pyproject.toml` entry points ليشير إلى `modules/`

---

## 2. تحسين التوثيق — docs/examples/arabic/

### الهيكل المقترح

```
docs/examples/arabic/
├── 01_basic_ocr_ar.md           # أساسيات OCR
├── 02_mixed_text_handling.md    # معالجة النصوص المختلطة
├── 03_rtl_export_docx.md        # تصدير RTL إلى DOCX
├── 04_spell_correction_ar.md    # التصحيح الإملائي
├── 05_finetuning_trocr_ar.md    # ضبط TrOCR
├── 06_medical_notes_ar.md       # الملاحظات الطبية (جديد)
├── 07_batch_processing_ar.md    # المعالجة الجماعية (جديد)
└── 08_api_usage_ar.md           # استخدام API (جديد)
```

### مثال توثيقي — `06_medical_notes_ar.md`

```markdown
# معالجة الملاحظات الطبية — دليل عملي

## المتطلبات
pip install -r requirements-ocr-advanced.txt

## الاستخدام الأساسي
\```python
from modules.medical.medical_ocr_reviewer import AdvancedMedicalOCR

# تهيئة مع حماية المصطلحات
medical_ocr = AdvancedMedicalOCR(
    protect_terminology=True,
    language="ar",
    ocr_engine="trocr"
)

# معالجة صورة ملاحظة طبية
result = medical_ocr.process_image("note_handwriting.jpg")
print(result.text)
print(f"المصطلحات المحمية: {result.protected_terms}")
\```

## المراجعة التفاعلية
\```python
# المراجعة مع Gradio
medical_ocr.launch_review_ui()
\```
```

### نظام التحقق التلقائي

إضافة `mkdocs.yml` plugin للتحقق من صحة الأمثلة:

```yaml
# mkdocs.yml
plugins:
  - mkdocs-examples:
      examples_dir: docs/examples/arabic
      validator: python -c "exec(open('$file').read())"
```

---

## 3. تقليل الاعتماديات — ملفات requirements متخصصة

### استراتيجية التقسيم

بدلاً من ملف `requirements.txt` واحد ضخم، نستخدم 6 ملفات متخصصة:

```
requirements-base.txt       (~500 MB)   — الواجهات + الأدوات الأساسية
requirements-ocr-basic.txt  (~2 GB)     — EasyOCR + Tesseract + PaddleOCR
requirements-ocr-advanced.txt (~4 GB)   — + TrOCR + SuryaOCR + onnxruntime
requirements-nlp-arabic.txt (~1.5 GB)   — Transformers + ar-corrector + CAMeL
requirements-ai-gateway.txt (~800 MB)   — FastAPI + httpx + tiktoken
requirements-deployment.txt (~200 MB)   — Docker + gunicorn + nginx configs
```

### مخطط التبعيات

```
base ◄───── ocr-basic ◄───── ocr-advanced
  │                               │
  ├── nlp-arabic ◄────────────────┤
  │                               │
  └── ai-gateway                  │
      │                           │
      └── deployment ◄────────────┘
```

### ملف requirements-base.txt

```ini
# =============================================================================
# OmniFile AI Processor — Base Layer (~500 MB)
# =============================================================================
# الواجهات + الأدوات الأساسية (بدون OCR أو NLP)
# التثبيت: pip install -r requirements-base.txt
# =============================================================================

# === Web Interfaces ===
streamlit>=1.29.0
gradio>=4.0.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6

# === Data Processing ===
pandas>=2.1.0
numpy>=1.24.0
pydantic>=2.5.0

# === Utilities ===
python-dotenv>=1.0.0
filelock>=3.13.0
tqdm>=4.66.0
requests>=2.31.0
Pillow>=10.0.0

# === Logging & Monitoring ===
structlog>=23.2.0

# === API Framework ===
httpx>=0.25.0
tenacity>=8.2.0
```

### ملف requirements-ocr-advanced.txt (جديد)

```ini
# =============================================================================
# OmniFile AI Processor — Advanced OCR (~4 GB additional)
# =============================================================================
# محركات OCR متقدمة + TrOCR + Surya + التعرف اليدوي
# التثبيت: pip install -r requirements-base.txt -r requirements-ocr-basic.txt -r requirements-ocr-advanced.txt
# =============================================================================

# === Deep Learning OCR ===
transformers>=4.35.0
torch>=2.0.0
torchvision>=0.15.0
accelerate>=0.21.0

# === TrOCR Fine-tuning ===
peft>=0.5.0          # LoRA adapter
datasets>=2.14.0
jiwer>=3.0.0         # CER/WER metrics

# === Surya OCR ===
surya-ocr>=0.4.0

# === ONNX Runtime ===
onnxruntime>=1.16.0
onnxruntime-gpu>=1.16.0  # optional

# === Advanced Image Processing ===
scikit-image>=0.21.0
albumentations>=1.3.0    # data augmentation

# === Line/Word Segmentation ===
# (يستخدم cv2 من requirements-ocr-basic.txt)
```

### ملف requirements-nlp-arabic.txt (جديد)

```ini
# =============================================================================
# OmniFile AI Processor — Arabic NLP (~1.5 GB additional)
# =============================================================================
# معالجة اللغة العربية + التصحيح الإملائي + RTL
# التثبيت: pip install -r requirements-base.txt -r requirements-nlp-arabic.txt
# =============================================================================

# === Arabic Language Tools ===
camel-tools>=1.5.0
ar-corrector>=0.6.0
farasapy>=0.1.0
arabic-reshaper>=3.0.0
python-bidi>=0.4.2

# === Translation ===
deep-translator>=1.11.0

# === Spell Checking ===
pyspellchecker>=0.7.0
jamspell>=1.0.0  # optional, C++ based

# === Text Processing ===
nltk>=3.8.0
langdetect>=1.0.9
regex>=2023.6.0

# === Document Export ===
python-docx>=0.8.11
openpyxl>=3.1.0
reportlab>=4.0.0

# === RTL Support ===
bidi.algorithm>=0.4.2
```

---

## 4. واجهة إدارة المعالجة الجماعية — Batch Dashboard

### البنية التقنية

```
┌──────────────────┐     WebSocket      ┌──────────────────┐
│  React Frontend   │ ◄══════════════► │  FastAPI Backend   │
│  (Vite + shadcn)  │     REST API      │  + WebSocket      │
│                   │                   │  + Celery Worker  │
└──────────────────┘                   └────────┬─────────┘
                                                │
                                       ┌────────▼─────────┐
                                       │  BatchManager     │
                                       │  - process_batch  │
                                       │  - retry_failed   │
                                       │  - export_results │
                                       └────────┬─────────┘
                                                │
                                    ┌───────────┼───────────┐
                                    ▼           ▼           ▼
                              ┌──────────┐ ┌────────┐ ┌────────┐
                              │  EasyOCR │ │ TrOCR  │ │ Tesseract│
                              └──────────┘ └────────┘ └────────┘
```

### واجهة REST API

```python
# backend/api/batch_api.py — نقاط النهاية الرئيسية

from fastapi import APIRouter, WebSocket, UploadFile, File
from backend.batch_manager import BatchManager, BatchConfig, check_permission

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])

@router.post("/create")
async def create_batch(
    name: str,
    ocr_engine: str = "trocr",
    language: str = "ar",
    role: str = "operator"
):
    """إنشاء دفعة معالجة جديدة."""
    if not check_permission(role, "upload_batch"):
        raise HTTPException(403, "صلاحية غير كافية")
    
    manager = BatchManager()
    config = BatchConfig(ocr_engine=ocr_engine, language=language)
    batch = manager.create_batch(name=name, config=config)
    return batch.to_dict()


@router.post("/{batch_id}/files")
async def upload_files(batch_id: str, files: List[UploadFile] = File(...)):
    """رفع ملفات إلى دفعة محددة."""
    manager = BatchManager()
    saved_paths = []
    for file in files:
        path = await save_upload(file)
        saved_paths.append(path)
    count = manager.add_files(batch_id, saved_paths)
    return {"added": count}


@router.websocket("/ws/{batch_id}/progress")
async def batch_progress(websocket: WebSocket, batch_id: str):
    """بث التقدم عبر WebSocket."""
    await websocket.accept()
    manager = BatchManager()
    
    async def on_progress(file_id, progress, message):
        await websocket.send_json({
            "file_id": file_id,
            "progress": progress,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    
    # تشغيل المعالجة في خلفية
    asyncio.create_task(
        manager.process_batch(batch_id, progress_callback=on_progress)
    )
    
    # الاستمرار في الاستماع
    while True:
        data = await websocket.receive_text()
        if data == "stop":
            break
```

### واجهة React — Batch Dashboard

```jsx
// frontend/src/components/dashboard/BatchDashboard.jsx
// لوحة التحكم الرئيسية للمعالجة الجماعية

import { useEffect, useState, useRef } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';

export default function BatchDashboard({ batchId }) {
  const { messages, connected } = useWebSocket(
    `/api/v1/batch/ws/${batchId}/progress`
  );
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    if (lastMsg) {
      setStats(prev => ({
        ...prev,
        [lastMsg.file_id]: {
          progress: lastMsg.progress,
          message: lastMsg.message,
        }
      }));
    }
  }, [messages]);

  return (
    <div className="grid grid-cols-4 gap-4">
      <StatusCards stats={stats} />
      <FileTable batchId={batchId} />
      <GlobalProgress stats={stats} />
      <BatchSettings batchId={batchId} />
    </div>
  );
}
```

---

## 5. نظام OCR للخط اليدوي — Handwriting Recognition

### البنية المكونة من ثلاث طبقات

```
┌─────────────────────────────────────────────────────┐
│                  EasyOCR + Tesseract                 │  ← الطبقة 1: الفحص السريع
│            (مطبوع + يدوي بسيط)                      │
├─────────────────────────────────────────────────────┤
│                    TrOCR Fine-Tuned                  │  ← الطبقة 2: التعرف الدقيق
│              (نموذج مُضبَط على الخط العربي)          │
├─────────────────────────────────────────────────────┤
│                    PatternDB                         │  ← الطبقة 3: التصحيح الذكي
│         (قاعدة أنماط + تصحيحات المستخدم)             │
└─────────────────────────────────────────────────────┘
```

### الأنبوب الرئيسي — ArabicHandwrittenHTR

```python
# modules/vision/htr/arabic_htr.py — استخدام مبسّط

from modules.vision.htr.arabic_htr import ArabicHandwrittenHTR

# تهيئة الأنبوب
htr = ArabicHandwrittenHTR(
    model_path="./models/trocr_arabic_medical",  # نموذج مُضبَط
    device="cuda",                                # GPU
    line_segmentation=True,
    word_segmentation=True,
    dotted_recovery=True,
    line_segmenter_type="projection"
)

# التعرف على صورة واحدة
result = htr.recognize("handwritten_note.jpg")
print(f"النص: {result.text}")
print(f"الثقة: {result.confidence:.1%}")
print(f"عدد الأسطر: {len(result.lines)}")
print(f"عدد الكلمات: {len(result.words)}")

# لكل كلمة: النص، الثقة، الموقع
for word in result.words:
    print(f"  [{word.text}] ثقة={word.confidence:.1%} "
          f"سطر={word.line_index}")
```

### التعرف على مستوى الكلمة مع PatternDB

```python
from modules.ai.pattern_db import PatternDatabase

# التهيئة
pattern_db = PatternDatabase("data/corrections.db")

# البحث عن تصحيح معروف
correction = pattern_db.find_correction("بسال")
# → {"corrected_text": "بايسال", "use_count": 5}

# إضافة تصحيح جديد من مراجعة المستخدم
pattern_db.add_correction(
    original_text="بسال",
    corrected_text="بايسال",
    engine="trocr",
    confidence=0.72
)
```

---

## 6. نظام التقسيم الذكي — Arabic Segmentation

### ArabicWordSegmenter

يعالج التحديات الخاصة بالكتابة العربية المتصلة:

```python
# modules/vision/htr/word_segmenter.py

class ArabicWordSegmenter:
    """مُجزِّئ الكلمات العربية — يتعامل مع:
    
    1. الكلمات المتصلة (حروف التعلق: ا ب ت ث)
    2. الفواصل والنقاط
    3. الأرقام المختلطة
    4. الحركات (التشكيل)
    """
    
    def segment(self, line_image) -> List[PIL.Image]:
        """تجزئة سطر إلى كلمات.
        
        الخوارزمية:
        1. كشف الأعمدة الفارغة بالـ Projection Profile
        2. دمج الكلمات المتصلة القريبة
        3. فصل الأرقام عن الحروف
        4. اقتصاص الكلمات بحواف مرنة
        """
        ...
```

### VocabularyColumnSplitter

مُجزِّذ ذكي يستخدم معجمًا عربيًا:

```python
class VocabularyColumnSplitter:
    """فصل النصوص المطبوعة متعددة الأعمدة.
    
    يستخدم:
    - Projection Profile عمودي
    - فحص العرض المتوسط للكلمات العربية (5-12 حرفًا)
    - قاعدة: المسافة > 2× متوسط عرض الكلمة = فاصل أعمدة
    """
    
    def split(self, image: PIL.Image) -> List[PIL.Image]:
        """فصل الصورة إلى أعمدة."""
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        col_projection = np.sum(gray < 128, axis=0)
        
        # حساب عتبة الفصل
        word_widths = self._estimate_word_widths(col_projection)
        threshold = np.median(word_widths) * 2.0 if word_widths else 30
        
        # تحديد مواقع الفواصل
        gaps = self._find_significant_gaps(col_projection, threshold)
        columns = self._extract_columns(image, gaps)
        return columns
```

---

## 7. محرك OCR المختلط — MixedLanguageOCR

### المشكلة

الملاحظات الطبية غالبًا تحتوي نصًا عربيًا وإنجليزيًا مختلطًا:
- "المريض يعاني من Diabetes Type 2 مع hypertension"
- "Dr. Ahmed — جراحة عظم 2/3/2025"

### الحل — المحرك المختلط

```python
# modules/nlp/mixed_language.py (موسّع)

class MixedLanguageOCR:
    """محرك OCR ثنائي اللغة (عربي/إنجليزي).
    
    الاستراتيجية:
    1. كشف اللغة على مستوى السطر
    2. تطبيق محرك OCR المناسب لكل سطر
    3. دمج النتائج مع الحفاظ على الترتيب البصري
    4. معالجة الكلمات المختلطة ضمن السطر الواحد
    """
    
    def __init__(self):
        from modules.nlp.language_detector import LanguageDetector
        from modules.vision.ocr_engine import OCREngine
        
        self.detector = LanguageDetector()
        self.ocr_ar = OCREngine(engine="easyocr", languages=["ar"])
        self.ocr_en = OCREngine(engine="easyocr", languages=["en"])
        self.ocr_mixed = OCREngine(engine="easyocr", languages=["ar", "en"])
    
    def process_page(self, image) -> MixedResult:
        """معالجة صفحة كاملة تحتوي نصًا مختلطًا."""
        lines = self._segment_lines(image)
        results = []
        
        for line_img in lines:
            lang = self.detector.detect_line(line_img)
            
            if lang == "ar":
                text = self.ocr_ar.recognize(line_img)
            elif lang == "en":
                text = self.ocr_en.recognize(line_img)
            else:  # mixed
                text, segments = self._process_mixed_line(line_img)
            
            results.append(LineResult(text=text, language=lang))
        
        return MixedResult(lines=results)
    
    def _process_mixed_line(self, line_img) -> Tuple[str, List[Segment]]:
        """معالجة سطر مختلط — تحليل كل كلمة."""
        words = self._segment_words(line_img)
        segments = []
        
        for word_img in words:
            lang = self.detector.detect_word(word_img)
            if lang == "ar":
                text = self.ocr_ar.recognize(word_img)
            else:
                text = self.ocr_en.recognize(word_img)
            segments.append(Segment(text=text, language=lang))
        
        full_text = " ".join(s.text for s in segments)
        return full_text, segments
```

---

## 8. التدريب والتعلم — Training & Learning Loop

### ArabicTrOCRTrainer

```python
# training/models/lora_htr_trainer.py

class ArabicTrOCRTrainer:
    """مُدرِّب TrOCR مع LoRA للخط العربي.
    
    الميزات:
    - LoRA (Low-Rank Adaptation) لتوفير VRAM
    - تقييم CER (Character Error Rate)
    - Data Augmentation مخصص للخط العربي
    - تصدير النموذج للاستخدام offline
    """
    
    def __init__(self, config_path: str = "training/configs/trocr_lora_arabic.yaml"):
        import yaml
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
    
    def train(self, train_data, eval_data=None):
        """بدء التدريب."""
        from transformers import (
            VisionEncoderDecoderModel,
            TrOCRProcessor,
            Seq2SeqTrainer,
            Seq2SeqTrainingArguments
        )
        from peft import LoraConfig, get_peft_model
        
        # تحميل النموذج الأساسي
        model = VisionEncoderDecoderModel.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        processor = TrOCRProcessor.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        
        # تطبيق LoRA
        lora_config = LoraConfig(
            r=self.config["lora_r"],
            lora_alpha=self.config["lora_alpha"],
            lora_dropout=0.05,
            target_modules=["query", "value"],
            bias="none",
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
        
        # إعداد التدريب
        training_args = Seq2SeqTrainingArguments(
            output_dir=self.config["output_dir"],
            num_train_epochs=self.config["num_epochs"],
            per_device_train_batch_size=self.config["batch_size"],
            learning_rate=self.config["learning_rate"],
            predict_with_generate=True,
            generation_max_length=128,
            fp16=self.config.get("fp16", True),
            save_strategy="epoch",
            evaluation_strategy="epoch" if eval_data else "no",
            logging_steps=25,
            report_to="none",
        )
        
        trainer = Seq2SeqTrainer(
            model=model,
            args=training_args,
            train_dataset=train_data,
            eval_dataset=eval_data,
            data_collator=lambda batch: self._collate_fn(batch, processor),
        )
        
        trainer.train()
        trainer.save_model(self.config["output_dir"])
        return trainer
```

### حلقة التعلم — PatternDB Learning Loop

```
┌────────────┐     تعديل المستخدم      ┌────────────┐
│  نتيجة OCR  │ ───────────────────► │  المراجعة   │
└──────┬─────┘                       └──────┬─────┘
       │                                    │
       │  تصحيح + صورة الكلمة              │
       ▼                                    ▼
┌────────────┐                       ┌────────────┐
│  PatternDB  │ ◄── إضافة تصحيح ─── │  المراجع   │
│  (SQLite)   │                       └────────────┘
└──────┬─────┘
       │
       │  بعد N تصحيح (≥ 50)
       ▼
┌────────────┐     نموذج جديد       ┌────────────┐
│  التدريب    │ ───────────────────► │  النموذج   │
│  (LoRA)     │                      │  المُحدَّث  │
└────────────┘                       └────────────┘
```

---

## 9. معالجة الملاحظات الطبية — AdvancedMedicalOCR

### المتطلبات الخاصة

1. **حماية المصطلحات الطبية** — منع التصحيح الإملائي من تعديلها
2. **معالجة الأدوية** — أسماء تجارية + مواد فعالة
3. **الأرقام الطبية** — الجرعات، التواريخ، الضغط، السكر
4. **الخصوصية** — لا يتم إرسال البيانات إلى خوادم خارجية

### AdvancedMedicalOCR

```python
# modules/medical/medical_ocr_reviewer.py

class AdvancedMedicalOCR:
    """معالج الملاحظات الطبية بخط اليد.
    
    يوفّر:
    - OCR مخصّص للخط اليدوي الطبي
    - حماية المصطلحات الطبية من التصحيح
    - مراجعة تفاعلية مع Gradio
    - تصدير النتائج بصيغ متعددة
    """
    
    # قاموس المصطلحات المحمية
    PROTECTED_TERMS = {
        # أدوية
        "paracetamol", "ibuprofen", "amoxicillin", "metformin",
        "insulin", "aspirin", "omeprazole", "lisinopril",
        "بايريكسامول", "أموكسيسيلين", "ميتفورمين", "أنسولين",
        # تشخيصات
        "diabetes", "hypertension", "asthma", "arrhythmia",
        "السكري", "ارتفاع الضغط", "الربو", "اضطراب نظم القلب",
        # إجراءات
        "CBC", "ESR", "HbA1c", "ECG", "X-ray", "MRI", "CT scan",
        "صورة دم", "تخطيط قلب", "أشعة سينية",
    }
    
    def __init__(self, protect_terminology=True, language="ar", ocr_engine="trocr"):
        from modules.vision.htr.arabic_htr import ArabicHandwrittenHTR
        from modules.ai.pattern_db import PatternDatabase
        
        self.protect = protect_terminology
        self.htr = ArabicHandwrittenHTR(device="cuda" if self._has_gpu() else "cpu")
        self.pattern_db = PatternDatabase()
    
    def process_image(self, image_path: str) -> MedicalOCRResult:
        """معالجة صورة ملاحظة طبية كاملة.
        
        خطوات المعالجة:
        1. تحميل الصورة
        2. التعرف على الخط اليدوي (HTR)
        3. كشف المصطلحات الطبية
        4. تطبيق التصحيح مع الحماية
        5. حفظ النتائج في PatternDB
        """
        result = self.htr.recognize(image_path)
        
        # كشف المصطلحات المحمية
        protected = self._find_protected_terms(result.text)
        
        # تصحيح النص مع حماية المصطلحات
        if self.protect:
            corrected = self._correct_with_protection(result.text, protected)
        else:
            corrected = result.text
        
        return MedicalOCRResult(
            text=corrected,
            original_text=result.text,
            confidence=result.confidence,
            protected_terms=protected,
            lines=result.lines,
            words=result.words,
        )
    
    def _correct_with_protection(self, text: str, protected: List[str]) -> str:
        """تصحيح النص مع حماية المصطلحات الطبية."""
        # استبدال المصطلحات المحمية بعلامات مؤقتة
        placeholders = {}
        for i, term in enumerate(protected):
            placeholder = f"__MED_TERM_{i}__"
            placeholders[placeholder] = term
            text = text.replace(term, placeholder)
        
        # تطبيق التصحيح الإملائي
        try:
            from modules.core.spell_checker import HybridSpellChecker
            checker = HybridSpellChecker()
            text = checker.correct(text)
        except ImportError:
            pass
        
        # إعادة المصطلحات المحمية
        for placeholder, term in placeholders.items():
            text = text.replace(placeholder, term)
        
        return text
    
    def _find_protected_terms(self, text: str) -> List[str]:
        """كشف المصطلحات الطبية في النص."""
        import re
        found = []
        text_lower = text.lower()
        for term in self.PROTECTED_TERMS:
            if term.lower() in text_lower:
                found.append(term)
        return list(set(found))
```

### TerminologyGuard — حارس المصطلحات

```python
# modules/medical/terminology_guard.py

class TerminologyGuard:
    """حماية المصطلحات الطبية أثناء التصحيح.
    
    آلية العمل:
    1. مسح النص قبل التصحيح
    2. استبدال المصطلحات بعلامات مؤقتة
    3. إعادة المصطلحات بعد التصحيح
    """
    
    def __init__(self, custom_terms: List[str] = None):
        self.terms = set(AdvancedMedicalOCR.PROTECTED_TERMS)
        if custom_terms:
            self.terms.update(t.lower() for t in custom_terms)
    
    def protect(self, text: str) -> Tuple[str, dict]:
        """حماية المصطلحات في النص.
        
        Returns:
            (النص المحمي، خريطة العلامات)
        """
        import re
        mapping = {}
        counter = [0]
        
        def replacer(match):
            placeholder = f"\x00TERM{counter[0]}\x00"
            mapping[placeholder] = match.group()
            counter[0] += 1
            return placeholder
        
        # ترتيب حسب الطول (الأطول أولاً)
        sorted_terms = sorted(self.terms, key=len, reverse=True)
        pattern = "|".join(re.escape(t) for t in sorted_terms)
        
        protected_text = re.sub(pattern, replacer, text, flags=re.IGNORECASE)
        return protected_text, mapping
    
    def restore(self, text: str, mapping: dict) -> str:
        """إعادة المصطلحات المحمية."""
        for placeholder, original in mapping.items():
            text = text.replace(placeholder, original)
        return text
```

---

## 10. الجدول الزمني — Timeline (7 أسابيع)

### الأسبوع 1–2: الأساسيات

| اليوم | المهمة | المخرجات |
|-------|--------|----------|
| 1–2 | طبقة التوافق العكسي لـ `src/` | `src/__init__.py` يُعاد التوجيه مع DeprecationWarning |
| 3–4 | ترحيل الوظائف المفقودة | جميع الواردات تعمل من `modules/` |
| 5 | اختبارات التوافق | `tests/test_migration_compat.py` — 100% pass |
| 6–7 | ملفات requirements متخصصة | 6 ملفات requirements موثقة |
| 8–10 | هيكل التوثيق الجديد | 4 أمثلة عربية جديدة في `docs/examples/arabic/` |
| 14 | مراجعة أسبوعية | CI green, docs build passes |

### الأسبوع 3–4: Batch Dashboard

| اليوم | المهمة | المخرجات |
|-------|--------|----------|
| 15–16 | WebSocket endpoints | بث التقدم في الوقت الحقيقي |
| 17–18 | REST API كامل | CRUD + إعادة المحاولة + التصدير |
| 19–21 | واجهة React | StatusCards + FileTable + GlobalProgress |
| 22–24 | اختبار شامل | E2E test: رفع → معالجة → تصدير |
| 28 | مراجعة أسبوعية | Dashboard يعمل مع 50+ ملف |

### الأسبوع 5: OCR اليدوي + التقسيم

| اليوم | المهمة | المخرجات |
|-------|--------|----------|
| 29–30 | تحسين ArabicWordSegmenter | دقة تجزئة الكلمات > 90% |
| 31–32 | VocabularyColumnSplitter | فصل الأعمدة في الملاحظات المطبوعة |
| 33–35 | MixedLanguageOCR | معالجة النصوص عربي/إنجليزي المختلطة |
| 35 | مراجعة | Benchmark على 100 صورة طبية |

### الأسبوع 6: التدريب + التعلم

| اليوم | المهمة | المخرجات |
|-------|--------|----------|
| 36–38 | ArabicTrOCRTrainer + LoRA | CER < 15% على البيانات الطبية |
| 39–40 | PatternDB Learning Loop | تصحيحات المستخدم → تدريب تلقائي |
| 41–42 | دفاتر Colab | `Medical_OCR_Review_Colab.py` + `TrOCR_FineTuning_Colab.py` |

### الأسبوع 7: المعالجة الطبية + الإصدار

| اليوم | المهمة | المخرجات |
|-------|--------|----------|
| 43–45 | AdvancedMedicalOCR | معالجة كاملة مع حماية المصطلحات |
| 46–47 | TerminologyGuard | اختبار عدم تعديل المصطلحات |
| 48–49 | التكامل + اختبارات E2E | جميع المكونات تعمل معًا |
| 50 | التحديثات الأخيرة + التوثيق | README, CHANGELOG, docs |
| 51 | إصدار v5.0.0 | Tag release على GitHub |

---

## ملخص معايير النجاح

| المعيار | المستهدف | الطريقة |
|---------|---------|---------|
| CER (Character Error Rate) | < 15% | تقييم على 500 صورة طبية |
| دقة تجزئة الكلمات | > 90% | مقارنة يدوية على 100 سطر |
| ثبات المصطلحات الطبية | 100% | اختبار عدم تعديل المصطلحات المحمية |
| أداء Batch Dashboard | < 3 ثوانٍ/ملف | قياس على 50 ملف PDF |
| غطاء الاختبارات | > 80% | `pytest --cov` |
| التوافق العكسي | 100% | جميع الواردات من `src/` تعمل |
| حجم base install | < 500 MB | `pip install -r requirements-base.txt` |

---

## المراجع

- [TrOCR: Transformer-based Optical Character Recognition](https://arxiv.org/abs/2109.10282)
- [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [Surya OCR — Multilingual OCR](https://github.com/VikParuchuri/surya)
- [EasyOCR — Ready-to-use OCR](https://github.com/JaidedAI/EasyOCR)
- [CAMeL Tools — Arabic NLP](https://camel-tools.readthedocs.io/)

---

*آخر تحديث: يونيو 2025 — هذا المستند يعكس حالة المشروع v4.2.0 والخطة للوصول إلى v5.0.0*
