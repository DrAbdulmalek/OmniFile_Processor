# HandwrittenOCR Unified Pack

مشروع OCR عربي/إنجليزي موحّد ومجهّز للتشغيل على **Google Colab** و **Manjaro/Arch Linux**.

النسخة دي مبنية على أحدث بنية منظمة موجودة داخل الملفات المرفوعة (`HandwrittenOCR-main.5.zip`) مع دمج المواد الإضافية الموجودة في الأرشيف الأصلي داخل مجلدات منظمة، بحيث يبقى عندك:

- **نواة تشغيل نظيفة**: `run.py`, `config.py`, `src/`, `backend/`
- **جاهزية لـ Colab**: Notebook جاهز + سكربت bootstrap
- **جاهزية لـ Manjaro**: سكربت إعداد تلقائي + بيئة افتراضية
- **الحفاظ على كل الملفات الأصلية**: داخل `archive/original_upload/`
- **دفعة بيانات أولية Legacy**: داخل `legacy_seed/Handwriting_Dataset/`
- **قاموس تصحيح أولي**: داخل `artifacts/correction_dict.json` و `data_seed/correction_dict_seed.json`
- **أداة Streamlit إضافية** لتجهيز وتقسيم الكلمات: `tools/streamlit_segmentation_app.py`

## 1) هيكل المشروع

```text
HandwrittenOCR/
├── config.py
├── run.py
├── requirements.txt
├── requirements-colab.txt
├── requirements-manjaro.txt
├── src/
├── backend/
├── notebooks/
│   ├── handwritten_ocr_colab.ipynb
│   ├── HandwrittenOCR_Colab_Ready.ipynb
│   └── legacy_notebooks/
├── scripts/
│   ├── bootstrap_colab.sh
│   ├── setup_manjaro.sh
│   ├── launch_local.sh
│   └── import_legacy_seed.py
├── tools/
│   └── streamlit_segmentation_app.py
├── artifacts/
│   └── correction_dict.json
├── data_seed/
│   └── correction_dict_seed.json
├── legacy_seed/
│   └── Handwriting_Dataset/
└── archive/
    └── original_upload/
```

## 2) التشغيل على Manjaro / Arch

من داخل مجلد المشروع:

```bash
bash scripts/setup_manjaro.sh ~/Handwritten_OCR_Ultimate
cd ~/Handwritten_OCR_Ultimate
source .venv/bin/activate
python run.py --local --pdf /path/to/input.pdf
```

تشغيل الواجهة على الشبكة المحلية:

```bash
python run.py --local --pdf /path/to/input.pdf --host 0.0.0.0 --port 7860
```

استيراد البيانات القديمة المرفقة داخل المشروع:

```bash
python scripts/import_legacy_seed.py --base-path legacy_seed
```

## 3) التشغيل على Google Colab

### الطريقة الأسرع
1. ارفع المشروع إلى GitHub أو Google Drive بعد فك الضغط.
2. افتح `notebooks/HandwrittenOCR_Colab_Ready.ipynb` في Colab.
3. شغّل الخلايا بالترتيب.
4. أضف `HF_TOKEN` داخل Colab Secrets لو محتاج الوصول للنموذج من Hugging Face.

### لو المشروع موجود بالفعل داخل بيئة Colab
```bash
bash scripts/bootstrap_colab.sh
python run.py --colab --pdf /content/drive/MyDrive/input.pdf
```

## 4) الملفات المدمجة من الأرشيف الأصلي

- كل الملفات الأصلية محفوظة كما هي داخل `archive/original_upload/`
- ملفات الـ notebooks القديمة تم تجميعها داخل `notebooks/legacy_notebooks/`
- ملفات البيانات القديمة تم تجهيزها داخل `legacy_seed/Handwriting_Dataset/`
- أداة الـ Streamlit القديمة تم نقلها إلى `tools/streamlit_segmentation_app.py`

## 5) ملاحظات مهمة

- أول تشغيل قد يحتاج وقت لتنزيل النماذج.
- إذا كانت الذاكرة محدودة، شغّل:

```bash
python run.py --local --pdf /path/to/input.pdf --low-memory
```

- لتخطي TrOCR واستخدام EasyOCR فقط:

```bash
python run.py --local --pdf /path/to/input.pdf --skip-trocr
```

## 6) ما الذي تم دمجه فعلياً

1. اعتماد **أحدث نسخة منظمة وقابلة للتشغيل** كأساس للمشروع.
2. الاحتفاظ بجميع الملفات الأصلية بدون حذف أو فقد.
3. تجهيز مسارات واضحة للتشغيل على Colab وManjaro.
4. إضافة قاموس تصحيح أولي ودفعة بيانات قديمة قابلة للترحيل.
5. تنظيم الملفات التجريبية والقديمة بدل تركها متناثرة في الجذر.

## 7) فحص سريع بعد فك الضغط

```bash
python -m py_compile run.py config.py src/*.py backend/*.py
```

لو حبيت تبدأ مباشرة من البيانات القديمة المرفقة داخل المشروع، نفّذ أولاً:

```bash
python scripts/import_legacy_seed.py --base-path legacy_seed
```
