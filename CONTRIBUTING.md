# دليل المساهمة الشامل — OmniFile AI Processor
# Comprehensive Contributing Guide

---

## نبذة عن المشروع — Project Overview

**OmniFile AI Processor** هو نظام متكامل لمعالجة الملفات والتعرف الضوئي على الحروف (OCR) مع تركيز خاص على اللغة العربية والنصوص المختلطة. يجمع المشروع بين خمسة محركات OCR ووحدات NLP متقدمة ومعالجة RTL عربية شاملة.

The project integrates multiple OCR engines (TrOCR, EasyOCR, Tesseract, PaddleOCR, Surya) with Arabic NLP, spell correction, layout-preserving export, and AI-powered refinement.

### البنية المعمارية — Architecture Summary

```
omnifile_processor/
├── modules/                  # الوحدات الأساسية (Core Modules)
│   ├── core/                 # القاعدة المشتركة، DB، Router، Spell Checker
│   ├── vision/               # محركات OCR، HTR، Preprocessing
│   ├── nlp/                  # معالجة اللغة، التصحيح، RTL، الترجمة
│   ├── security/             # التشفير، فحص PII، حماية الأكواد
│   ├── export/               # تصدير DOCX، HTML، Markdown، PDF
│   ├── ai/                   # التعلم الذكي، Active Learning، AI Gateway
│   ├── audit/                # مراجعة الجودة، تقرير النتائج
│   ├── medical/              # وحدة الطب والمراجعات الطبية
│   ├── training/             # تصدير بيانات التدريب
│   ├── ui/                   # واجهات Gradio
│   ├── config/               # إعدادات HTR والتدريب
│   ├── evaluation/           # مقاييس التقييم (CER/WER)
│   ├── segmentation/         # تقسيم النصوص والأعمدة
│   ├── learning/             # قاعدة أنماط التعلم
│   └── ocr/                  # محرك مختلط متقدم
├── backend/                  # واجهة API (FastAPI + Celery)
├── frontend/                 # واجهة React + shadcn/ui
├── training/                 # سكريبتات التدريب و Fine-tuning
├── tests/                    # الاختبارات (pytest)
├── tools/                    # أدوات مساعدة
├── examples/                 # أمثلة استخدام
├── docs/                     # التوثيق
└── config.py                 # الإعدادات المركزية (OmniFileConfig)
```

---

## إعداد بيئة التطوير — Development Environment Setup

### المتطلبات الأساسية — Prerequisites

- **Python 3.10+** (يدعم union types و match/case)
- **Git** مع إعداد `user.name` و `user.email`
- **CUDA** (اختياري) لتسريع GPU

### خطوات الإعداد — Setup Steps

```bash
# 1. استنساخ المشروع
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor

# 2. إنشاء بيئة افتراضية
python -m venv .venv
source .venv/bin/activate      # لينكس/ماك
# .venv\Scripts\activate       # ويندوز

# 3. تثبيت الاعتماديات الأساسية
pip install -r requirements-core.txt

# 4. تثبيت أدوات التطوير (ruff, pytest, etc.)
pip install -r requirements-dev.txt

# 5. تثبيت محركات OCR (اختياري — حسب الحاجة)
pip install -r requirements-ocr-basic.txt    # EasyOCR + Tesseract
pip install -r requirements-ocr-advanced.txt # + TrOCR + PaddleOCR

# 6. التحقق من التثبيت
python -c "from modules.vision.ocr_engine import OCREngine; print('OK')"
pytest tests/ -x -q --co  # عرض قائمة الاختبارات
```

---

## سير العمل — Development Workflow

### 1. Fork و Branch

```bash
# Fork المشروع على GitHub، ثم:
git clone https://github.com/<YOUR_USERNAME>/OmniFile_Processor.git
cd OmniFile_Processor
git remote add upstream https://github.com/DrAbdulmalek/OmniFile_Processor.git
```

### 2. إنشاء Branch

```bash
git checkout -b feat/اسم-الميزة        # ميزة جديدة
git checkout -b fix/اسم-الإصلاح        # إصلاح خطأ
git checkout -b docs/اسم-التعديل       # تحديث توثيق
git checkout -b refactor/اسم-إعادة-الهيكلة
```

### 3. التطوير والاختبار

```bash
# كتابة الكود...
# تشغيل فحص الأنماط
ruff check modules/
ruff format modules/

# تشغيل الاختبارات
pytest tests/ -x -q
```

### 4. إرسال Pull Request

```bash
git add -A
git commit -m "feat: وصف الميزة"
git push origin feat/اسم-الميزة
# ثم افتح PR على GitHub
```

---

## معايير الكود — Code Style Guidelines

| المعيار | القيمة |
|---------|--------|
| Python | 3.10+ |
| Type Hints | إلزامي لكل الدوال العامة |
| Docstrings | عربية أو إنجليزية (Google style) |
| طول السطر | **120 حرف كحد أقصى** |
| الفاحص | `ruff` (بديل black + flake8 + isort) |
| التنسيق | `ruff format modules/` |
| الترميز | UTF-8 |

### مثال على كود نموذجي

```python
def process_image(
    image_path: str,
    languages: list[str] | None = None,
    confidence_threshold: float = 0.5,
) -> dict[str, Any]:
    """
    معالجة صورة واستخراج النص باستخدام محرك OCR.

    Args:
        image_path: مسار ملف الصورة.
        languages: لغات التعرف (الافتراضي: ["ar", "en"]).
        confidence_threshold: حد الثقة الأدنى (0.0–1.0).

    Returns:
        قاموس يحتوي text, confidence, source.

    Raises:
        FileNotFoundError: إذا لم يكن الملف موجوداً.
    """
    languages = languages or ["ar", "en"]
    # ... implementation
```

### تشغيل Ruff

```bash
ruff check modules/          # فحص الأخطاء
ruff check --fix modules/    # إصلاح تلقائي
ruff format modules/         # تنسيق الكود
```

---

## إضافة محرك OCR جديد — Adding a New OCR Engine

### الخطوات

1. **إنشاء ملف المحرك:** `modules/vision/engines/new_engine.py`
   ```python
   class NewOCR:
       """محرك OCR جديد."""

       def recognize(self, image, **kwargs) -> dict:
           """التعرف على النص في صورة."""
           # ...
           return {"text": "...", "confidence": 0.9, "source": "new_engine"}
   ```

2. **التسجيل في OCREngine:** أضف دعم المحرك في `modules/vision/ocr_engine.py`:
   - إضافة `enable_newengine: bool = False` في `__init__`
   - إضافة `_load_newengine()` و `_recognize_newengine()`
   - إضافة المحرك في `_get_active_engines()` و `_select_best_result()`

3. **التسجيل في EngineRouter:** أضف المحرك في `modules/core/engine_router.py`:
   ```python
   ENGINE_NEW = "NewEngine"
   ENGINE_RAM_REQUIREMENTS[ENGINE_NEW] = 2.0
   PROFILE_ENGINES["high"].append(ENGINE_NEW)
   ```

4. **التسجيل في OmniFileConfig:** أضف `enable_newengine: bool = False` في `config.py`

5. **كتابة الاختبارات:** أنشئ `tests/test_new_engine.py` مع اختبارات الوحدة والتكامل

6. **تحديث التوثيق:** أضف المحرك في `README.md` و `docs/API_DOCS.md`

---

## إضافة وحدة NLP جديدة — Adding a New NLP Module

1. أنشئ ملفاً جديداً في `modules/nlp/new_module.py` مع docstring عربية
2. أضف دالة/كلاس عامة مع type hints كاملة
3. سجّل الوحدة في `modules/nlp/__init__.py`
4. اكتب اختبارات في `tests/test_new_module.py`
5. إذا كانت الوحدة تتطلب نماذج ML، أضفها في ملف `requirements-nlp-arabic.txt` أو `requirements-nlp.txt`

---

## إرشادات الاختبار — Testing Guidelines

### الأدوات

- **pytest** كإطار اختبار رئيسي
- **pytest-cov** لتقرير التغطية
- **conftest.py** للـ fixtures المشتركة

### الأوامر

```bash
# تشغيل كل الاختبارات
pytest tests/ -x -q

# مع تقرير التغطية
pytest tests/ --cov=modules --cov-report=term-missing

# تشغيل اختبار محدد
pytest tests/test_ocr_engine.py -x -q

# تشغيل اختبارات فئة معينة
pytest tests/test_spell_corrector.py::TestSpellCorrector -x
```

### التغطية المتوقعة — Coverage Expectations

- الوحدات الجديدة يجب أن تحقق تغطية **≥ 70%** كحد أدنى
- الدوال الحرجة (الأمان، DB، التصدير) يجب أن تحقق **≥ 90%**
- أضف اختبار واحد على الأقل لكل دالة عامة جديدة

### أنماط الاختبار

```python
import pytest

class TestNewFeature:
    """اختبارات الميزة الجديدة."""

    def test_basic_functionality(self):
        """اختبار الوظيفة الأساسية."""
        result = my_function(input_data)
        assert result is not None
        assert result["text"] != ""

    def test_edge_case_empty_input(self):
        """اختبار حالة المدخلات الفارغة."""
        with pytest.raises(ValueError):
            my_function("")

    def test_arabic_text(self):
        """اختبار النصوص العربية."""
        result = my_function("مرحبا بالعالم")
        assert "مرحبا" in result["text"] or result["confidence"] > 0.5
```

---

## اصطلاحات رسائل Commit — Commit Message Conventions

نستخدم [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <وصف قصير بالعربية أو الإنجليزية>

[جسم اختياري يشرح التفاصيل]

[footer اختياري: refs #issue]
```

### الأنواع المدعومة — Types

| النوع | الاستخدام | مثال |
|-------|-----------|------|
| `feat` | ميزة جديدة | `feat(ocr): إضافة محرك Surya` |
| `fix` | إصلاح خطأ | `fix(nlp): إصلاح تقسيم النص المختلط` |
| `docs` | توثيق | `docs: تحديث دليل المساهمة` |
| `style` | تنسيق (لا يؤثر على المنطق) | `style: تنسيق بـ ruff` |
| `refactor` | إعادة هيكلة | `refactor(core): توحيد BaseDB` |
| `test` | اختبارات | `test(security): اختبارات فحص PII` |
| `chore` | صيانة | `chore: تحديث المتطلبات` |
| `perf` | أداء | `perf(vision): تحسين batch processing` |
| `ci` | CI/CD | `ci: إضافة Snyk scan` |

---

## قالب Pull Request — Pull Request Template

عند فتح PR، استخدم هذا القالب:

```markdown
## الوصف
[وصف موجز للتغييرات — بالعربية أو الإنجليزية]

## نوع التغيير
- [ ] feat (ميزة جديدة)
- [ ] fix (إصلاح خطأ)
- [ ] docs (توثيق)
- [ ] refactor (إعادة هيكلة)
- [ ] test (اختبارات)
- [ ] chore (صيانة)

## الاختبارات
- [ ] أضفت اختبارات جديدة
- [ ] كل الاختبارات تجتاز: `pytest tests/ -x -q`
- [ ] التغطية ≥ 70%

## المرتبط بـ
Fixes #<رقم Issue>
```

---

## قالب الإبلاغ عن مشكلة — Issue Reporting Template

```markdown
## وصف المشكلة
[وصف واضح للمشكلة]

## خطوات إعادة الإنتاج
1. [الخطوة الأولى]
2. [الخطوة الثانية]
3. [الخطوة الثالثة]

## النتائج المتوقعة
[ما كان يجب أن يحدث]

## النتائج الفعلية
[ما حدث فعلاً]

## البيئة
- Python: [النسخة]
- OS: [نظام التشغيل]
- GPU: [نعم/لا — النوع]
- إصدار المشروع: [v5.x]
- ملف السجل (log): [إن وجد]

## لقطات الشاشة
[إن وجدت]
```

---

## تنظيم الوحدات — Module Organization

كل وحدة في `modules/` تتبع هذا النمط:

```
modules/<category>/
├── __init__.py          # تصدير الواجهات العامة
├── main_module.py       # الملف الرئيسي
└── sub_module.py        # وحدات فرعية
```

### القواعد

- كل وحدة لها `__init__.py` يصدّر الواجهات العامة فقط
- الوظائف الداخلية تبدأ بـ `_` (underscore)
- الثوابت تُكتب بـ `UPPER_SNAKE_CASE`
- الأصناف بـ `PascalCase`
- الدوال والمتغيرات بـ `snake_case`

---

## إرشادات التوثيق — Documentation Guidelines

- **Docstrings:** كل دالة عامة وكل صنف يجب أن يكون لها docstring
- **اللغة:** عربية أو إنجليزية — كن متسقاً داخل نفس الملف
- **الأسلوب:** استخدم Google-style docstrings:
  ```python
  def function(arg: str) -> bool:
      """وصف مختصر.

      وصف تفصيلي إن لزم الأمر.

      Args:
          arg: شرح المعامل.

      Returns:
          شرح القيمة المعادة.
      """
  ```
- **الأمثلة:** أضف أمثلة استخدام في docstring الدوال المهمة
- **README:** حدّث `README.md` إذا أضفت ميزة رئيسية جديدة

---

## عملية المراجعة — Review Process

1. **المراجعة التلقائية:** CI يتحقق من:
   - فحص Ruff (`ruff check`)
   - اختبارات pytest
   - فحص Snyk للأمان
2. **المراجعة البشرية:** مُطوِّر واحد على الأقل يجب أن يراجع الكود
3. **المعايير:** يُقبل PR إذا:
   - جميع الاختبارات تجتاز
   - لا أخطاء Ruff
   - تغطية الاختبارات كافية
   - التوثيق محدّث

---

## التواصل — Contact Information

**المطور الرئيسي:** Dr. Abdulmalek Tamer Al-husseini
**البريد الإلكتروني:** Abdulmalek.husseini@gmail.com
**الموقع:** Homs, Syria
**GitHub:** [DrAbdulmalek](https://github.com/DrAbdulmalek)

---

شكراً لاهتمامك بالمساهمة في تطوير OmniFile AI Processor!
نحن نرحّب بكل مساهمة — صغيرة كانت أم كبيرة.

OmniFile AI Processor v5.0
