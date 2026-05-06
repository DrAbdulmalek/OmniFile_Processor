# HandwrittenOCR — مشروع استخراج نصوص الخط اليدوي

> **الغرض من هذا الملف:** عرض شامل للمشروع ليعمل عليه Claude AI لتطويره على Google Colab و Manjaro Linux

---

## 1. نظرة عامة

**HandwrittenOCR** هو مشروع Python مفتوح المصدر (MIT) لاستخراج وتصحيح نصوص الخط اليدوي من ملفات PDF. يدعم العربية والإنجليزية، ويعتمد على محركين للتعرف: **TrOCR** و **EasyOCR** مع نظام Ensemble ذكي. المشروع في الإصدار v5.3/v5.4 ويتضمن نظام تحسين مستمر عبر LoRA fine-tuning.

- **الرابط:** https://github.com/DrAbdulmalek/HandwrittenOCR
- **اللغة:** الكود بالإنجليزية، التعليقات والرسائل بالعربية
- **الترخيص:** MIT

---

## 2. البنية التقنية

### 2.1 هيكل الملفات

```
HandwrittenOCR/
├── config.py              # إعدادات مركزية (Config dataclass مع 50+ حقل)
├── run.py                 # نقطة الدخول CLI مع argparse
├── requirements.txt       # الاعتماديات
├── TROUBLESHOOTING.md     # دليل حل المشاكل
├── dev_log.ipynb          # سجل التطوير التفاعلي
│
├── src/
│   ├── __init__.py         # __version__ = "5.3.0"
│   ├── main.py            # نقطة الدخول الرئيسية - تنظيم كل المكونات
│   ├── preprocessing.py   # معالجة الصور + تجزئة ذكية + كشف أعمدة
│   ├── recognition.py     # OCREngine: TrOCR + EasyOCR ensemble + batch + LoRA
│   ├── correction.py      # تصحيح إملائي (ar-corrector + pyspellchecker)
│   ├── database.py        # SQLite v3 مع ترقية تلقائية (v1→v2→v3)
│   ├── pdf_processor.py   # معالج PDF (PyMuPDF + pdf2image fallback)
│   ├── review_ui.py       # واجهة المراجعة (Jupyter ipywidgets + CLI)
│   ├── export.py          # تصدير CSV/XLSX/JSONL + رفع HuggingFace
│   ├── finetuning.py      # LoRA fine-tuning على TrOCR
│   ├── reconstruction.py  # تجميع الجمل RTL + قاموس ثنائي اللغة
│   ├── study_guide.py     # مولّد المرجع الدراسي (Markdown + HTML + Anki)
│   ├── sync.py            # Syncthing + قفل ملفات
│   ├── migration.py       # ترحيل من نسخ قديمة
│   ├── metrics.py         # WER/CER
│   └── logger.py          # RotatingFileHandler
│
├── backend/
│   ├── app.py             # FastAPI REST API (42 endpoint)
│   └── start_server.py    # uvicorn launcher
│
├── notebooks/
│   └── handwritten_ocr_colab.ipynb  # (قالب فارغ حالياً)
│
├── HandwrittenOCR.ipynb   # دفتر Colab الأصلي (قديم، أحادي)
└── tests/
    └── __init__.py         # (فارغ - لا توجد اختبارات بعد)
```

### 2.2 المكونات الأساسية

#### Config (`config.py`)
- **Dataclass** مع 50+ حقل: مسارات، نماذج، أداء، preprocessing، تصحيح، تدريب، LoRA، تصدير، مزامنة
- **طرق المصنع:**
  - `Config.from_colab_drive(pdf_name, hf_token, hf_repo)` — لبيئة Google Colab
  - `Config.from_local(pdf_path, project_root)` — للتشغيل المحلي (يكتشف GPU تلقائياً)
  - `Config.from_dict(data)` — من قاموس
- **خصائص:** `root`, `db_path`, `logs_dir`, `cache_dir`, `is_colab` (كشف تلقائي)
- **`apply_low_memory()`:** يقلل DPI إلى 150، EasyOCR=[en] فقط، batch=4، deskew=off، skip_trocr=True، skip_spellcheck=True

#### OCREngine (`src/recognition.py`)
- يحمّل TrOCR (`David-Magdy/TR_OCR_LARGE`) + EasyOCR
- **`skip_trocr`** parameter: يمنع تحميل TrOCR بالكامل (توفير ~600 MB)
- **`batch_predict(crops)`:** Batch TrOCR inference مع beam search (num_beams=5)
- **`recognize_word_ensemble(img, easyocr_raw)`:** Ensemble ذكي — يخطي TrOCR إذا ثقة EasyOCR ≥ 0.80
- **LoRA auto-loading** عبر PEFT

#### PDFProcessor (`src/pdf_processor.py`)
- v5.4: يستخدم **PyMuPDF (fitz)** أولاً (أخف 10x من pdf2image)، مع fallback لـ pdf2image
- تحميل صفحة بصفحة (OOM prevention)
- `gc.collect()` + `torch.cuda.empty_cache()` بعد كل صفحة
- تتبع الذاكرة التفصيلي (`[ذاكرة: XXX MB]`)
- Batch TrOCR inference
- Spell correction + correction dict
- Checkpointing/resume
- File locking للمزامنة
- run_id tracking + processing_runs table

#### HandwritingDB (`src/database.py`)
- SQLite v3 مع auto-migration من v1/v2
- Tables: `handwriting_data` (14 column مع raw_text, run_id, timestamps), `processing_runs`, `review_events`
- 4 indexes

#### Review UI (`src/review_ui.py`)
- `ReviewUI` — مراجعة كلمات (Jupyter ipywidgets أو CLI)
- `SentenceReviewUI` — مراجعة جمل (Jupyter فقط)
- `CorrectionDictUI` — تحرير قاموس التصحيح يدوياً

#### Study Guide (`src/study_guide.py`)
- `generate_study_guide()` — Markdown مع جداول + terms
- `generate_study_guide_full()` — مع Mermaid diagrams + flashcards
- `generate_flashcards()` — 3 أنواع: bilingual, concept, fill_blank
- `export_flashcards_anki()` — Anki CSV
- `export_study_guide_html()` — HTML مع CSS احترافي RTL للطباعة

### 2.3 نظام التحسين المستمر

```
PDF → OCR (TrOCR+EasyOCR) → مراجعة المستخدم → تصحيحات CSV → قاموس تصحيح
                                                              ↓
                                    JSONL train/val → LoRA fine-tuning → تحديث النموذج
                                                              ↓
                                              رفع HuggingFace + WER/CER metrics
```

---

## 3. الاعتماديات

### requirements.txt
```
Pillow>=10.0.0, opencv-python-headless>=4.8.0, numpy>=1.24.0
pdf2image>=1.16.0
easyocr>=1.7.0, pytesseract>=0.3.10, transformers>=4.36.0, torch>=2.0.0, torchvision>=0.15.0
pyspellchecker>=0.7.0, ar-corrector>=0.6.0, langdetect>=1.0.9
ipywidgets>=8.0.0, gradio>=4.0
pandas>=2.0.0, openpyxl>=3.1.0, scikit-learn>=1.3.0
peft>=0.7.0, huggingface_hub>=0.19.0, datasets>=2.14.0
jiwer>=3.0.0, matplotlib>=3.7.0, tqdm>=4.65.0
uvicorn>=0.24.0, fastapi>=0.104.0, pydantic>=2.0.0, pyngrok>=5.0.0
```

### اعتماديات نظام Manjaro
```bash
sudo pacman -S tesseract tesseract-data-ara poppler python python-pip base-devel opencv
```

### v5.4 إضافة مهمة
```bash
pip install PyMuPDF   # بديل أخف لـ pdf2image
```

---

## 4. بيئات التشغيل

### 4.1 Manjaro Linux (جهاز المستخدم الحالي)
- **RAM:** ~600-700 MB فعلي (محدود جداً)
- **Swap:** ~4 GB
- **المشكلة الأساسية:** OOM Kill متكرر — Linux يقتل العملية بدون traceback

### 4.2 Google Colab (الحل المطلوب)
- **RAM:** 12-13 GB
- **GPU:** T4 (16 GB VRAM)
- **مميزات:** لا OOM، يمكن تشغيل كل النماذج بالكامل (TrOCR + EasyOCR en+ar + SpellCheck)

---

## 5. المشاكل التي تم حلها (التاريخ)

### المشكلة 1: NameError في config.py
- **السبب:** `logging` غير مستورد في `apply_low_memory()`
- **الحل:** إضافة `import logging` لقسم الاستيرادات

### المشكلة 2: OOM Kill #1 و #2 (TrOCR + EasyOCR العربي)
- **السبب:** تحميل كل النماذج معاً يستهلك >3 GB
- **الحل:** إضافة `skip_trocr=True` و `ocr_languages=["en"]` في الوضع الخفيف

### المشكلة 3: OOM Kill #3 (pdf2image)
- **السبب:** `pdf2image` يشغّل `pdftoppm` كـ subprocess ثقيل
- **الحل (v5.4):** استبدال بـ **PyMuPDF (fitz)** — أخف 10x، لا subprocess

### المشكلة 4: Spell Checkers تستهلك ~200 MB
- **السبب:** ar-corrector يحمل نموذج لغة عربي ثقيل
- **الحل:** إضافة `skip_spellcheck=True` في الوضع الخفيف

### المشكلة 5: Model path reset بعد git pull
- **السبب:** `git pull` يستبدل `trocr_model_name` بالقيمة الافتراضية (HuggingFace URL)
- **الحل المقترح:** ملف `local_config.py` منفصل (لا يتأثر بـ git)

---

## 6. المطلوب من Claude

### 6.1 إنشاء `colab_notebook.ipynb` كامل

أحتاج دفتر Google Colab متكامل يحتفظ بـ **كل مميزات المشروع**. يجب أن يكون:

#### Cell 1: التثبيت والإعداد
```python
# تثبيت الاعتماديات
!pip install PyMuPDF easyocr transformers torch torchvision
!pip install pyspellchecker ar-corrector langdetect
!pip install peft huggingface_hub datasets jiwer
!pip install pandas openpyxl matplotlib tqdm ipywidgets
!pip install scikit-learn gradio pyngrok
!apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-ara
```

#### Cell 2: ربط Google Drive
```python
from google.colab import drive
drive.mount('/content/drive')
```

#### Cell 3: استيراد المشروع
- إما `git clone` من GitHub إلى Drive
- أو إذا المشروع موجود مسبقاً على Drive، `cd` إليه مباشرة

#### Cell 4: إعداد Config و HF Token
```python
from google.colab import userdata
from config import Config

config = Config.from_colab_drive(
    pdf_name="python notes.pdf",    # ← يغيّره المستخدم
    hf_token=userdata.get('HF_TOKEN', ''),
)
config.setup()
```

#### Cell 5: تحميل النماذج (TrOCR + EasyOCR كاملين)
- في Colab يمكن تحميل كل شيء — لا قيود ذاكرة
- TrOCR + EasyOCR en+ar + Spell Checkers كلها تعمل
- عرض معلومات GPU والذاكرة

#### Cell 6: معالجة PDF
```python
from src.main import main
main(config)
```

#### Cell 7: واجهة المراجعة التفاعلية (ipywidgets)
- مراجعة الكلمات غير الموثقة
- تصحيح النصوص
- حفظ التصحيحات لقاموس التعلم المستمر

#### Cell 8: إعادة تجميع الجمل + RTL
```python
from src.reconstruction import reconstruct_sentences
```

#### Cell 9: توليد المرجع الدراسي
```python
from src.study_guide import generate_study_guide_full, export_flashcards_anki
```

#### Cell 10: تصدير + LoRA Fine-tuning
```python
from src.export import export_finetuning_dataset
from src.finetuning import finetune_trocr_lora
```

#### Cell 11: WER/CER Metrics
```python
from src.metrics import compute_metrics, plot_metrics_fig
```

**ملاحظات مهمة:**
- يجب ألا يُنشئ الدفتر ملفات جديدة داخل `src/` — يستخدم الكود الموجود كما هو
- يجب أن يعمل الدفتر بـ "Run All" بدون تعديل يدوي (ما عدا اسم ملف PDF و HF Token)
- توفير واجهة Gradio كـ Cell اختياري مع `share=True` للوصول من المتصفح
- حفظ كل شيء على Google Drive (models_cache, database, exports, artifacts)

### 6.2 تحسينات Manjaro

أحتاج أيضاً مساعدة في:

1. **نصيحة حول استراتيجية التطوير المزدوج:**
   - كيف أعمل على Colab (للمعالجة الثقيلة) وأستخدم Manjaro (للتطوير والاختبار السريع) بشكل متزامن؟
   - هل يمكن مزامنة قاعدة البيانات والتصحيحات بين Colab Drive و Manjaro عبر Syncthing؟

2. **تحسين الذاكرة على Manjaro:**
   - حالياً OOM Kill يحدث حتى مع كل التحسينات (skip_trocr, PyMuPDF, low-memory)
   - هل يوجد طريقة أخرى لتقليل الاستهلاك؟
   - هل يمكن تشغيل TrOCR فقط على GPU إذا توفرت؟

3. **نصائح اختبار وحدة (Unit Tests):**
   - دليل `tests/` فارغ حالياً
   - ما هي أهم الوحدات التي يجب اختبارها؟

4. **تحسين Gradio:**
   - config.py يحدد `gradio_port=7860` و `gradio_share=True` لكن لا يوجد كود Gradio فعلي
   - أحتاج واجهة Gradio كاملة للمراجعة والعرض

---

## 7. تفاصيل تقنية مهمة

### 7.1 مسارات Colab (Config.from_colab_drive)
```python
project_root = "/content/drive/MyDrive/Handwritten_OCR_Ultimate"
pdf_path     = "/content/drive/MyDrive/{pdf_name}"
model_cache  = "/content/drive/MyDrive/Handwritten_OCR_Ultimate/models_cache"
db_path      = "/content/drive/MyDrive/Handwritten_OCR_Ultimate/database/handwriting_data.db"
```

### 7.2 EasyOCR Symlink على Colab
- `config.setup_easyocr_symlink()` يربط `~/.EasyOCR` → `/content/drive/MyDrive/Handwritten_OCR_Ultimate/.EasyOCR`
- يوفر إعادة تحميل النماذج (~800 MB) في كل جلسة

### 7.3 HuggingFace Token
- يمكن تخزينه في Colab Secrets: `userdata.get('HF_TOKEN')`
- أو تمريره مباشرة: `Config.from_colab_drive(hf_token="hf_xxx")`

### 7.4 الذاكرة — نقاط الاختناق
| المكون | الاستهلاك | ملاحظات |
|--------|-----------|---------|
| EasyOCR English | ~200 MB | ضروري |
| EasyOCR Arabic | ~800 MB | يمكن تخطيه |
| TrOCR (TR_OCR_LARGE) | ~600 MB | يمكن تخطيه |
| ar-corrector | ~150 MB | يمكن تخطيه |
| PyMuPDF (صفحة واحدة) | ~50 MB | بديل pdf2image |
| pdf2image (صفحة واحدة) | ~300-500 MB | subprocess |
| PIL/PDF processing | ~100-200 MB | حسب DPI |
| **المجموع (كامل)** | **~2.5 GB** | |
| **المجموع (خفيف)** | **~500 MB** | بدون TrOCR+Arabic+SpellCheck |

### 7.5 17 تصحيح تم تطبيقهم
1. `!mv`/`!rm`/`!ln` → `shutil.move`/`shutil.rmtree`/`os.symlink`
2. SpellChecker على جمل كاملة → كلمة بكلمة
3. `preprocess_image` → يرجع `(binary, enhanced)`
4. القص من الصورة الثنائية → من `img_bgr` الأصلية
5. EasyOCR أول نتيجة → `max(results, key=r[2])`
6. `cv2_imshow` → `cv2.imwrite`
7. مسارات مرمجة → `Config` dataclass
8. df محلي يخرج عن التزامن → DB مباشرة
9. Status `'yes'/'no'` → `'verified'/'unverified'`
10. DB schema auto-migration v1→v2→v3
11. LoRA auto-loading
12. Review UI df sync fix
13. LoRA auto-loading (تكرار بسيط في التوثيق)
14. DataMigrator
15. حماية 130+ مصطلح تقني
16. كشف أعمدة + ترتيب عمودي
17. مولّد المرجع الدراسي

---

## 8. ما أريده بالضبط

### المخرجات المطلوبة:

1. **`colab_notebook.ipynb`** — دفتر Colab كامل مع كل الخلايا المطلوبة (أعلاه) — يحفظ في جذر المشروع

2. **تحسينات على ملفات المشروع الحالية** (إذا لزم):
   - إضافة واجهة Gradio حقيقية في ملف جديد `src/gradio_ui.py`
   - تحسين `config.py` لدعم Colab بشكل أفضل
   - أي تحسينات أخرى يقترحها Claude

3. **نصائح واستراتيجيات** للعمل المزدوج بين Colab و Manjaro

4. **خطة اختبارات** (unit tests) لأهم الوحدات

### القيود:
- لا تغيّر البنية الحالية للمشروع — أضف فقط
- حافظ على التوافق مع `python run.py --local` على Manjaro
- حافظ على التوافق مع `python run.py --colab`
- كل الملفات الجديدة يجب أن تعمل مع الكود الحالي

---

## 9. معلومات إضافية

### API Endpoints (42 endpoint في backend/app.py)
- Health, Stats, PDF processing, Words CRUD, Sentences, Correction dict
- Export/Fine-tune/HuggingFace, Metrics, Settings
- Sync, Migration, Vocabulary protection, Study guides, Flashcards, Column sort

### نظام المزامنة (Syncthing)
- File locking (fcntl على Linux, msvcrt على Windows)
- Conflict detection بين الأجهزة
- Network info لـ LAN access

### البيانات التي يمكن مزامنتها بين Colab و Manjaro
- `database/handwriting_data.db` — نعم
- `logs/user_corrections_feedback.csv` — نعم
- `artifacts/correction_dict.json` — نعم
- `exports/` — نعم
- `models_cache/` — نعم (عبر Drive)

---

> **ملاحظة:** هذا المشروع متطور ويتضمن 17 تصحيح تم تطبيقها عبر إصدارات متعددة. أرجو قراءة `TROUBLESHOOTING.md` و `dev_log.ipynb` للحصول على السياق الكامل للمشاكل والحلول.
