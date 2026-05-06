# Dependency Profiles — OmniFile AI Processor

هذا الدليل يشرح الفرق بين ملفات الاعتماديات في المشروع، ومتى تستخدم كل طبقة.

## الملفات الأساسية

### `requirements-core.txt`
الحد الأدنى المناسب للتشغيل المحلي السريع أو للتطوير الأساسي.

**يشمل:**
- Streamlit / Gradio / FastAPI
- أدوات التصدير الأساسية
- نماذج البيانات والاختبارات

**استخدمه عندما:**
- تريد تشغيل الواجهات فقط
- تريد مساهمة سريعة في الكود
- تريد بيئة CI خفيفة

---

### `requirements-ocr.txt`
طبقة محركات OCR ومعالجة الصور.

**يشمل:**
- EasyOCR
- Tesseract bindings
- PaddleOCR / PaddlePaddle
- OpenCV / PyMuPDF / pdf2image
- onnxruntime

**استخدمه عندما:**
- تريد OCR فعلي على الصور وPDF
- تحتاج قياسات أداء أو Benchmarks
- تريد تفعيل أكثر من محرك OCR

---

### `requirements-nlp.txt`
طبقة معالجة اللغة والترجمة.

**يشمل:**
- Transformers
- langdetect
- pyspellchecker
- ar-corrector
- أدوات RTL العربية

**استخدمه عندما:**
- تحتاج الترجمة أو التلخيص
- تريد التصحيح الإملائي متعدد اللغات
- ستستخدم وحدات NER / classification

---

### `requirements-full.txt`
كل المكونات في بيئة واحدة.

**استخدمه عندما:**
- تريد كل ميزات المشروع محلياً
- تعمل على بيئة قوية أو سيرفر GPU
- تريد محاكاة بيئة الإنتاج تقريباً

---

### `requirements-hf.txt`
نسخة خفيفة مناسبة لـ Hugging Face Spaces.

**استخدمه عندما:**
- تريد مساحة تجريبية سريعة
- تحتاج نسخة Gradio أخف من النسخة الكاملة

---

### `requirements-colab.txt`
نسخة محسنة للدفاتر التفاعلية وGoogle Colab.

**يشمل إضافياً:**
- `requirements-core.txt`
- `requirements-hf.txt`
- أدوات PDF/OCR الشائعة في Colab
- `ipywidgets`
- `pyngrok`
- `python-dotenv`

**استخدمه عندما:**
- تريد تجربة سريعة على Colab
- تحتاج مشاركة رابط مؤقت عبر ngrok
- تريد تشغيل notebook التصحيح والتجربة

---

## وصفات تثبيت جاهزة

### 1) تشغيل خفيف
```bash
pip install -r requirements-core.txt
```

### 2) تشغيل OCR كامل بدون NLP ثقيل
```bash
pip install -r requirements-core.txt -r requirements-ocr.txt
```

### 3) تشغيل NLP فوق البيئة الأساسية
```bash
pip install -r requirements-core.txt -r requirements-nlp.txt
```

### 4) تشغيل كل شيء
```bash
pip install -r requirements-full.txt
```

### 5) تشغيل Colab / Notebook
```bash
pip install -r requirements-colab.txt
```

## ملاحظات عملية
- لو هدفك هو CI والاستقرار: ابدأ بـ `requirements-core.txt`.
- لو هدفك هو دقة OCR: أضف `requirements-ocr.txt`.
- لو هدفك هو مراجعة النصوص والترجمة: أضف `requirements-nlp.txt`.
- لو هدفك هو Demo عام: استخدم `requirements-hf.txt` أو Space المختبر.
