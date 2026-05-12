# وحدة OCR الطبي (Medical OCR Module)

## نظرة عامة

وحدة متخصصة لاستخراج النصوص المكتوبة بخط اليد من الملفات الطبية (عربي/إنجليزي)، مع تصحيح تلقائي باستخدام قاموس طبي مخصص، وتصدير نتائج قابلة للمراجعة بتنسيق HTML تفاعلي.

## القدرات

- استخراج النصوص من ملفات PDF (عبر PyMuPDF) والصور
- معالجة مسبقة متقدمة: CLAHE + Otsu Binarization + تقسيم الأسطر
- تصحيح تلقائي باستخدام قاموس طبي مخصص (قابل للتوسيع)
- تصدير JSON (نتائج منظمة) + HTML (صفحة مراجعة تفاعلية)
- دعم GPU اختياري
- تكامل مع واجهة Gradio

## المتطلبات

```bash
pip install easyocr opencv-python PyMuPDF pillow numpy
```

## الاستخدام الأساسي

### من الكود

```python
from modules.vision.medical_ocr import MedicalOCRProcessor

# إنشاء المعالج
ocr = MedicalOCRProcessor(use_gpu=False)

# معالجة ملف PDF
results = ocr.process_pdf("notes.pdf", max_pages=10)

# أو معالجة صورة واحدة
lines = ocr.process_image("handwritten_note.jpg")

# حفظ النتائج
ocr.save_results(results, "./output")
ocr.generate_html_review(results, "./output/review.html")
```

### من سطر الأوامر

```bash
python -m modules.vision.medical_ocr notes.pdf -o ./output --max-pages 10
```

### من واجهة Gradio

```python
from modules.vision.medical_ocr_gradio import create_medical_ocr_tab

# إضافة التبويب إلى واجهة Gradio الحالية
medical_tab = create_medical_ocr_tab()
```

## المخرجات

| الملف | الوصف |
|-------|-------|
| `ocr_results.json` | نص خام ومصحح لكل سطر مع الإحداثيات |
| `review.html` | واجهة تفاعلية لمراجعة وتصحيح النصوص |

## دمج وحدة OCR الطبي في مشروع OmniFile_Processor

### الهيكل

```
OmniFile_Processor/
├── modules/vision/
│   ├── medical_ocr.py           # الكود الأساسي
│   └── medical_ocr_gradio.py    # تكامل مع Gradio
├── config/
│   └── medical_dict.json        # القاموس الطبي
└── docs/
    └── medical_ocr_readme.md    # هذا الملف
```

### تكامل مع FastAPI + Celery

تتوفر نقاط نهاية REST API لمعالجة الملفات بشكل غير متزامن عبر Celery + Redis:

```bash
# رفع ملف
curl -X POST http://localhost:5001/medical-ocr/upload -F "file=@notes.pdf"

# بدء مهمة OCR
curl -X POST http://localhost:5001/medical-ocr/start \
  -H "Content-Type: application/json" \
  -d '{"file_path":"uploads/notes.pdf","max_pages":10}'

# الاستعلام عن الحالة
curl http://localhost:5001/medical-ocr/status/<task_id>
```

## توسيع القاموس الطبي

أضف أزواج (خطأ -> صواب) إلى `config/medical_dict.json`:

```json
{
    "خطأ OCR": "التصحيح الصحيح",
    "Abbreviation": "Full Term"
}
```

سيتم تطبيق التصحيحات تلقائياً عند المعالجة.

## المراقبة (Prometheus + Grafana)

يوفر المشروع إعداداً كاملاً للمراقبة عبر Prometheus و Grafana و Alertmanager:

- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3000` (admin/admin)
- **Flower**: `http://localhost:5555` (مراقبة Celery)
- **Alertmanager**: `http://localhost:9093`

## Docker

```bash
# تشغيل كل الخدمات (FastAPI + Celery + Redis + Monitoring)
docker-compose up -d --build
```
