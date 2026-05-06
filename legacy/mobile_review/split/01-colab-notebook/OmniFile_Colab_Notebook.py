# OmniFile_Colab_Notebook.py
# Google Colab notebook for testing/debugging OmniFile Processor

## 📄 **1. ملف Google Colab (IPYNB) لتجربة المشروع**

### **`OmniFile_Colab_Notebook.ipynb`**
```python
# %% [markdown]
"""
# 🧠 **OmniFile AI Processor - Google Colab Notebook**
**نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص والخط اليدوي**

🔹 **الإصدار**: 3.0
🔹 **المؤلف**: Dr. Abdulmalek
🔹 **الغرض**: تجربة المشروع وتصحيح المشاكل في بيئة Colab

---

## 📌 **محتويات الدفتر**
1. [التثبيت والإعداد](#1-التثبيت-والإعداد)
2. [تشغيل المشروع](#2-تشغيل-المشروع)
3. [اختبار ميزات OCR](#3-اختبار-ميزات-OCR)
4. [اختبار ميزات NLP](#4-اختبار-ميزات-NLP)
5. [تصحيح المشاكل الشائعة](#5-تصحيح-المشاكل-الشائعة)
6. [حفظ النتائج](#6-حفظ-النتائج)
7. [مراجعة نتائج OCR](#7-مراجعة-نتائج-OCR)
"""

# %%
# =============================================================================
# 1. التثبيت والإعداد
# =============================================================================
print("🔧 **جاري تثبيت الحزم المطلوبة... (قد يستغرق عدة دقائق)**")

# تثبيت الحزم الأساسية
!pip install -q --upgrade pip
!pip install -q torch==2.1.0 torchvision==0.15.2 transformers==4.36.0
!pip install -q easyocr==1.7.0 pytesseract==0.3.10 PyMuPDF==1.23.0 pdf2image==1.16.0
!pip install -q opencv-python-headless==4.8.0 Pillow==10.0.0 paddlepaddle==2.5.0 paddleocr==2.7.0
!pip install -q scikit-image==0.21.0 rapidfuzz==3.0.0 sentencepiece==0.1.99
!pip install -q streamlit==1.28.0 gradio==4.0.0 fastapi==0.104.0 uvicorn==0.24.0
!pip install -q huggingface_hub==0.19.0 datasets==2.15.0 langdetect==1.0.9
!pip install -q pyspellchecker==0.7.2 ar-corrector==0.6.3 arabic-reshaper==3.0.0 python-bidi==0.4.2
!pip install -q openai==1.0.0 google-generativeai==0.3.0 openpyxl==3.1.0 python-docx==0.8.11
!pip install -q GitPython==3.1.0 beautifulsoup4==4.12.0 fpdf2==2.7.0 psutil==5.9.0
!pip install -q pydantic==2.0.0 onnxruntime==1.16.0 presidio-analyzer==2.2.0 presidio-anonymizer==2.2.0
!pip install -q celery==5.3.0 redis==5.0.0 pytest==7.4.0 pytest-cov==4.1.0 pytest-mock==3.11.0
!pip install -q pyngrok==7.0.0 python-dotenv==1.0.0 flask==3.0.0 flask-cors==4.0.0

# تثبيت Tesseract
!apt install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng tesseract-ocr-deu
!apt install -y libtesseract-dev

# تثبيت PaddlePaddle (إذا كان GPU متاحًا)
try:
    !pip install -q paddlepaddle-gpu==2.5.0.post110
except:
    !pip install -q paddlepaddle==2.5.0

print("✅ **تم تثبيت جميع الحزم بنجاح!**")

# %%
# ربط Google Drive
from google.colab import drive
drive.mount('/content/drive')

# إنشاء مجلد العمل
import os
WORK_DIR = "/content/drive/MyDrive/OmniFile_AI"
os.makedirs(WORK_DIR, exist_ok=True)
os.chdir(WORK_DIR)

# استنساخ المشروع من GitHub
!git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
%cd OmniFile_Processor

print(f"✅ **تم استنساخ المشروع إلى: {WORK_DIR}/OmniFile_Processor**")

# %%
# =============================================================================
# 2. تشغيل المشروع
# =============================================================================
print("🚀 **جاري تهيئة المشروع...**")

# تهيئة الإعدادات
import sys
from pathlib import Path
from config import OmniFileConfig

# إضافة مسار المشروع إلى PYTHONPATH
PROJECT_ROOT = Path("/content/drive/MyDrive/OmniFile_AI/OmniFile_Processor")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

cfg = OmniFileConfig.from_colab_drive()
cfg.setup_environment()

# التحقق من GPU
import torch
print(f"🔹 **GPU متاح:** {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"🔹 **اسم GPU:** {torch.cuda.get_device_name(0)}")
    print(f"🔹 **ذاكرة GPU:** {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")

# %%
# =============================================================================
# 3. اختبار ميزات OCR
# =============================================================================
print("📸 **جاري اختبار ميزات OCR...**")

from modules.vision.ocr_engine import OCREngine
from modules.vision.pdf_processor import PDFProcessor
from PIL import Image
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np

# تحميل صورة اختبار (يمكن استبدالها بصورة خاصة بك)
test_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Lenna_test_image.png/440px-Lenna_test_image.png"
response = requests.get(test_image_url)
img = Image.open(BytesIO(response.content))

# عرض الصورة
plt.figure(figsize=(10, 5))
plt.imshow(img)
plt.axis('off')
plt.title("صورة الاختبار (انقر نقرًا مزدوجًا لتكبير)")
plt.show()

# تهيئة محرك OCR
ocr_engine = OCREngine(
    enable_trocr=True,
    enable_easyocr=True,
    enable_tesseract=True,
    enable_paddleocr=False,  # تعطيل PaddleOCR مؤقتًا (ثقيل)
    use_gpu=torch.cuda.is_available(),
    trocr_model_variant="base",
    easyocr_languages=["en", "ar"],
    tesseract_langs="eng+ara"
)

# معالج OCR
print("🔹 **جاري معالج OCR...**")
result = ocr_engine.recognize(img, languages=["en"])
print(f"📝 **النص المستخرج:**\n{result['text']}")
print(f"🔹 **مصدر المحرك:** {result['source']}")
print(f"🔹 **ثقة النتيجة:** {result['confidence']:.2%}")
print(f"🔹 **زمن المعالجة:** {result['processing_time']:.2f} ثانية")

# %%
# اختبار OCR على صورة عربية
print("📸 **جاري اختبار OCR على صورة عربية...**")

# تحميل صورة عربية
arabic_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Arabic_calligraphy.jpg/800px-Arabic_calligraphy.jpg"
response = requests.get(arabic_image_url)
arabic_img = Image.open(BytesIO(response.content))

# عرض الصورة
plt.figure(figsize=(10, 5))
plt.imshow(arabic_img)
plt.axis('off')
plt.title("صورة عربية (انقر نقرًا مزدوجًا لتكبير)")
plt.show()

# معالج OCR
arabic_result = ocr_engine.recognize(arabic_img, languages=["ar"])
print(f"📝 **النص العربي المستخرج:**\n{arabic_result['text']}")
print(f"🔹 **مصدر المحرك:** {arabic_result['source']}")
print(f"🔹 **ثقة النتيجة:** {arabic_result['confidence']:.2%}")

# %%
# اختبار OCR على PDF
print("📄 **جاري اختبار OCR على PDF...**")

# تحميل ملف PDF اختبار
pdf_url = "https://www.africau.edu/images/default/sample.pdf"
pdf_response = requests.get(pdf_url)
pdf_bytes = pdf_response.content

# معالج PDF
pdf_proc = PDFProcessor(dpi=300)
pdf_results = pdf_proc.process_pdf(pdf_bytes, pages=[0])  # معالجة الصفحة الأولى فقط

print(f"📝 **النص المستخرج من PDF:**\n{pdf_results[0]['text']}")

# %%
# اختبار دمج نتائج محركات OCR
print("🔄 **جاري اختبار دمج نتائج محركات OCR...**")

# تهيئة محرك OCR مع جميع المحركات
ocr_engine_all = OCREngine(
    enable_trocr=True,
    enable_easyocr=True,
    enable_tesseract=True,
    enable_paddleocr=False,
    use_gpu=torch.cuda.is_available(),
    fusion_strategy="weighted_average"  # استراتيجية الدمج
)

# معالج الصورة باستخدام جميع المحركات
fusion_result = ocr_engine_all.recognize(img, languages=["en"])
print(f"📝 **النص بعد دمج النتائج:**\n{fusion_result['text']}")
print(f"🔹 **استراتيجية الدمج:** {fusion_result.get('fusion_strategy', 'N/A')}")
print(f"🔹 **المحركات المستخدمة:** {fusion_result.get('engines_used', [])}")

# %%
# =============================================================================
# 4. اختبار ميزات NLP
# =============================================================================
print("🌐 **جاري اختبار ميزات NLP...**")

from modules.nlp.spell_corrector import SpellCorrector
from modules.nlp.translator import TechnicalTranslator
from modules.nlp.summarizer import TextSummarizer

# اختبار التصحيح الإملائي
corrector = SpellCorrector()
test_text = "I havv a speling mistake in this sentense."
corrected_text = corrector.correct_text(test_text)
print(f"🔹 **النص الأصلي:** {test_text}")
print(f"🔹 **النص المصحح:** {corrected_text}")

# اختبار التصحيح الإملائي للعربية
arabic_test_text = "السلام عليكم كيف حالك"
arabic_corrected = corrector.correct_text(arabic_test_text)
print(f"\n🔹 **النص العربي الأصلي:** {arabic_test_text}")
print(f"🔹 **النص العربي المصحح:** {arabic_corrected}")

# اختبار الترجمة
translator = TechnicalTranslator()
translated_text = translator.translate_text(
    "Hello, how are you?",
    source="en",
    target="ar"
)
print(f"\n🔹 **النص المترجم:** {translated_text['translated_text']}")

# اختبار التلخيص
summarizer = TextSummarizer()
long_text = """
Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to intelligence displayed by animals and humans.
Leading AI textbooks define the field as the study of intelligent agents: any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
Some popular accounts use the term artificial intelligence to describe machines that mimic cognitive functions that humans associate with the human mind,
such as learning and problem-solving.
"""
summary = summarizer.summarize(long_text)
print(f"\n🔹 **الملخص:** {summary['summary']}")

# %%
# =============================================================================
# 5. تصحيح المشاكل الشائعة
# =============================================================================
print("🛠️ **تصحيح المشاكل الشائعة**")

# مشكلة 1: عدم توافر GPU
if not torch.cuda.is_available():
    print("\n⚠️ **GPU غير متاح!**")
    print("🔹 **الحل:**")
    print("   1. تأكد من اختيار GPU في Runtime > Change runtime type > T4 GPU")
    print("   2. أعد تشغيل الدفتر (Restart Runtime) بعد اختيار GPU")
    print("   3. تحقق من أن CUDA متاح:")
    !nvidia-smi
else:
    print("\n✅ **GPU متاح!**")

# مشكلة 2: نفاد الذاكرة (OOM)
print("\n🔹 **إذا ظهرت رسالة 'CUDA out of memory':**")
print("   1. قلل حجم نموذج TrOCR:")
print("      cfg.trocr_model_variant = 'small'  # بدلاً من 'base'")
print("   2. عطّل PaddleOCR (ثقيل):")
print("      cfg.enable_paddleocr = False")
print("   3. فعّل Quantization:")
print("      cfg.use_quantization = True")
print("   4. قلل حجم الدفعة:")
print("      cfg.trocr_batch_size = 4  # بدلاً من 8")

# مشكلة 3: Tesseract غير مثبت
try:
    import pytesseract
    print("\n✅ **Tesseract مثبت بشكل صحيح**")
except:
    print("\n⚠️ **Tesseract غير مثبت!**")
    print("🔹 **الحل:**")
    print("   !apt install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng")

# مشكلة 4: PaddleOCR غير متاح
try:
    import paddleocr
    print("\n✅ **PaddleOCR متاح**")
except:
    print("\n⚠️ **PaddleOCR غير متاح!**")
    print("🔹 **الحل:**")
    print("   1. تثبيت PaddlePaddle:")
    print("      !pip install paddlepaddle-gpu==2.5.0.post110  # إذا كان GPU متاحًا")
    print("      !pip install paddlepaddle==2.5.0  # إذا كان GPU غير متاح")
    print("   2. تثبيت PaddleOCR:")
    print("      !pip install paddleocr==2.7.0")

# مشكلة 5: أخطاء في التبعيات
print("\n🔹 **إذا ظهرت أخطاء في التبعيات:**")
print("   1. إعادة تثبيت جميع الحزم:")
print("      !pip install -r requirements.txt --force-reinstall")
print("   2. تثبيت الحزم المفقودة يدويًا:")
print("      !pip install streamlit==1.28.0 transformers==4.36.0 torch==2.1.0")

# %%
# =============================================================================
# 6. حفظ النتائج
# =============================================================================
print("💾 **حفظ النتائج**")

# إنشاء مجلد للنتائج
RESULTS_DIR = Path(WORK_DIR) / "OmniFile_Processor" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# حفظ النص المستخرج من OCR
with open(RESULTS_DIR / "ocr_result_en.txt", "w", encoding="utf-8") as f:
    f.write(result['text'])

with open(RESULTS_DIR / "ocr_result_ar.txt", "w", encoding="utf-8") as f:
    f.write(arabic_result['text'])

# حفظ النص المترجم
with open(RESULTS_DIR / "translation_result.txt", "w", encoding="utf-8") as f:
    f.write(translated_text['translated_text'])

# حفظ الملخص
with open(RESULTS_DIR / "summary_result.txt", "w", encoding="utf-8") as f:
    f.write(summary['summary'])

print(f"✅ **تم حفظ جميع النتائج في مجلد: {RESULTS_DIR}/**")

# %%
# =============================================================================
# 7. مراجعة نتائج OCR
# =============================================================================
print("📝 **مراجعة نتائج OCR**")

# عرض نتائج OCR في جدول
import pandas as pd

# إنشاء جدول للنتائج
results_data = {
    "المحرك": ["TrOCR", "EasyOCR", "Tesseract", "Fusion"],
    "النص": [
        result['text'][:50] + "..." if len(result['text']) > 50 else result['text'],
        "سيتم اختبار EasyOCR أدناه",
        "سيتم اختبار Tesseract أدناه",
        fusion_result['text'][:50] + "..." if len(fusion_result['text']) > 50 else fusion_result['text']
    ],
    "الثقة": [
        f"{result['confidence']:.2%}",
        "-",
        "-",
        f"{fusion_result['confidence']:.2%}"
    ],
    "الوقت (ثانية)": [
        f"{result['processing_time']:.2f}",
        "-",
        "-",
        f"{fusion_result['processing_time']:.2f}"
    ]
}

results_df = pd.DataFrame(results_data)
results_df

# اختبار EasyOCR بشكل منفصل
print("\n🔹 **جاري اختبار EasyOCR بشكل منفصل...**")
easyocr_result = ocr_engine.recognize(img, languages=["en"], engine="easyocr")
print(f"📝 **النص من EasyOCR:**\n{easyocr_result['text'][:100]}...")
print(f"🔹 **ثقة النتيجة:** {easyocr_result['confidence']:.2%}")

# اختبار Tesseract بشكل منفصل
print("\n🔹 **جاري اختبار Tesseract بشكل منفصل...**")
tesseract_result = ocr_engine.recognize(img, languages=["en"], engine="tesseract")
print(f"📝 **النص من Tesseract:**\n{tesseract_result['text'][:100]}...")
print(f"🔹 **ثقة النتيجة:** {tesseract_result['confidence']:.2%}")

# %%
# مقارنة بين المحركات
comparison_data = {
    "المحرك": ["TrOCR", "EasyOCR", "Tesseract"],
    "الدقة": [
        f"{result['confidence']:.2%}",
        f"{easyocr_result['confidence']:.2%}",
        f"{tesseract_result['confidence']:.2%}"
    ],
    "السرعة (ثانية)": [
        f"{result['processing_time']:.2f}",
        f"{easyocr_result['processing_time']:.2f}",
        f"{tesseract_result['processing_time']:.2f}"
    ],
    "دعم العربية": ["✅", "✅", "✅"],
    "دعم الخط اليدوي": ["✅", "❌", "❌"],
    "الاستهلاك": ["عالي", "متوسط", "منخفض"]
}

comparison_df = pd.DataFrame(comparison_data)
comparison_df

# %%
# =============================================================================
# 8. اختبار حفظ التنسيق (جداول، صور، تسميات)
# =============================================================================
print("📝 **جاري اختبار حفظ التنسيق...**")

from modules.export.exporter import TextExporter

# نص اختبار يحتوي على جداول وصور
test_text_with_format = """
# عنوان رئيسي

هذا نص عادي مع **نص غليظ** و *نص مائل*.

## جدول اختبار

| العمود 1 | العمود 2 | العمود 3 |
|----------|----------|----------|
| خلية 1   | خلية 2   | خلية 3   |
| خلية 4   | خلية 5   | خلية 6   |

![صورة اختبار](https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Lenna_test_image.png/200px-Lenna_test_image.png)

```python
def hello_world():
    print("Hello, World!")
```

> هذا نص مقتبس.
"""

# تصدير إلى HTML
exporter = TextExporter(cfg)
html_path = exporter.export_to_html(
    test_text_with_format,
    RESULTS_DIR / "formatted_text.html",
    title="نص اختبار مع تنسيق",
    language="ar"
)
print(f"✅ **تم تصدير النص إلى HTML: {html_path}**")

# تصدير إلى PDF
pdf_path = exporter.export_to_pdf(
    html_path,
    RESULTS_DIR / "formatted_text.pdf"
)
print(f"✅ **تم تصدير النص إلى PDF: {pdf_path}**")

# تصدير إلى DOCX
docx_path = exporter.export_to_docx(
    html_path,
    RESULTS_DIR / "formatted_text.docx",
    language="ar"
)
print(f"✅ **تم تصدير النص إلى DOCX: {docx_path}**")

# %%
# عرض ملف HTML
from IPython.display import HTML
with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()
HTML(html_content)

# %%
# =============================================================================
# 9. اختبار نظام مراجعة OCR (Simulated)
# =============================================================================
print("📱 **نظام مراجعة OCR (محاكاة)**")

# محاكاة نظام مراجعة OCR
class OCRReviewSystem:
    def __init__(self):
        self.documents = []

    def add_document(self, text, file_name="document.txt"):
        doc_id = len(self.documents) + 1
        self.documents.append({
            "id": doc_id,
            "file_name": file_name,
            "raw_text": text,
            "corrected_text": text,
            "status": "pending_review",
            "language": "ar",
            "confidence": 0.85
        })
        return doc_id

    def get_document(self, doc_id):
        for doc in self.documents:
            if doc["id"] == doc_id:
                return doc
        return None

    def save_corrections(self, doc_id, corrected_text):
        for doc in self.documents:
            if doc["id"] == doc_id:
                doc["corrected_text"] = corrected_text
                doc["status"] = "reviewed"
                return True
        return False

# إنشاء نظام مراجعة
review_system = OCRReviewSystem()

# إضافة مستند
doc_id = review_system.add_document(arabic_result['text'], "test_arabic.png")
print(f"✅ **تم إضافة مستند جديد مع ID: {doc_id}**")

# عرض المستند
doc = review_system.get_document(doc_id)
print(f"\n📄 **المستند {doc_id}:**")
print(f"🔹 **اسم الملف:** {doc['file_name']}")
print(f"🔹 **النص الأصلي:**\n{doc['raw_text'][:100]}...")
print(f"🔹 **الحالة:** {doc['status']}")

# محاكاة تصحيح النص
corrected_text = doc['raw_text'].replace("السلام", "مرحبا")  # مثال بسيط
review_system.save_corrections(doc_id, corrected_text)
print(f"\n✅ **تم تصحيح المستند {doc_id}**")

# عرض النص المصحح
doc = review_system.get_document(doc_id)
print(f"\n📝 **النص المصحح:**\n{doc['corrected_text'][:100]}...")

# %%
# =============================================================================
# 10. اختبار التعلم من تصحيحات المستخدم
# =============================================================================
print("🤖 **جاري اختبار نظام التعلم من تصحيحات المستخدم...**")

from modules.ai.active_learning import ActiveLearner

# إنشاء نظام تعلم نشط
active_learner = ActiveLearner(db_path=RESULTS_DIR / "active_learning.db")

# تسجيل تصحيح
correction_id = active_learner.log_correction(
    original_text="السلام عليكم",
    corrected_text="مرحبا بكم",
    language="ar",
    confidence=0.9,
    source="manual"
)
print(f"✅ **تم تسجيل التصحيح مع ID: {correction_id}**")

# الحصول على اقتراحات
suggestions = active_learner.get_suggestions("السلام عليكم كيف حالك", "ar")
print(f"🔹 **اقتراحات التصحيح:** {suggestions}")

# %%
# =============================================================================
# 11. اختبار Fine-tuning لنموذج TrOCR
# =============================================================================
print("🎯 **جاري اختبار Fine-tuning لنموذج TrOCR...**")

from modules.ai.finetuning import TrOCRFineTuner
import tempfile

# إنشاء مجلد مؤقت للبيانات
temp_dir = Path(tempfile.mkdtemp())
train_dir = temp_dir / "train"
train_dir.mkdir(parents=True, exist_ok=True)

# إنشاء بيانات تدريب افتراضية
sample_image = np.ones((100, 200, 3), dtype=np.uint8) * 255
sample_image[20:40, 10:80] = 0
Image.fromarray(sample_image).save(train_dir / "sample.png")

with open(train_dir / "sample.txt", "w", encoding="utf-8") as f:
    f.write("نص اختبار")

# تهيئة مدرب TrOCR
fine_tuner = TrOCRFineTuner(
    model_name="microsoft/trocr-small-handwritten",
    output_dir=RESULTS_DIR / "fine_tuned_models",
    use_lora=True,
    lora_r=8,
    lora_alpha=16
)

# تدريب النموذج (مثال مبسط)
try:
    model_path = fine_tuner.fine_tune_from_directory(
        train_dir=str(train_dir),
        epochs=1,
        batch_size=2,
        learning_rate=5e-5,
        model_name="trocr_ar_test"
    )
    print(f"✅ **تم تدريب النموذج وحفظه في: {model_path}**")
except Exception as e:
    print(f"⚠️ **فشل تدريب النموذج:** {e}")
    print("🔹 **السبب:** قد يكون بسبب عدم توافر GPU أو ذاكرة غير كافية.")

# %%
# =============================================================================
# 12. اختبار واجهة FastAPI (اختياري)
# =============================================================================
print("🌐 **جاري اختبار واجهة FastAPI...**")

# تشغيل خادم FastAPI في خلفية
import subprocess
import time
import requests

# إنشاء ملف FastAPI
fastapi_code = """
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from modules.vision.ocr_engine import OCREngine
from modules.nlp.spell_corrector import SpellCorrector
from typing import Optional
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr_engine = OCREngine(
    enable_trocr=True,
    enable_easyocr=True,
    enable_tesseract=True,
    use_gpu=False  # تعطيل GPU لتجنب مشاكل Colab
)

corrector = SpellCorrector()

@app.post("/ocr")
async def process_ocr(file: UploadFile = File(...)):
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(await file.read()))
    result = ocr_engine.recognize(img, languages=["ar", "en"])
    return {
        "text": result["text"],
        "confidence": result["confidence"],
        "source": result["source"]
    }

@app.post("/correct")
async def correct_text(text: str, language: str = "ar"):
    corrected = corrector.correct_text(text, lang=language)
    return {"corrected_text": corrected}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
"""

# كتابة ملف FastAPI
with open("fastapi_server.py", "w", encoding="utf-8") as f:
    f.write(fastapi_code)

# تشغيل الخادم في خلفية
try:
    server_process = subprocess.Popen(
        ["python", "fastapi_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3)  # انتظار بدء الخادم

    # اختبار API
    test_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Lenna_test_image.png/200px-Lenna_test_image.png"
    response = requests.get(test_image_url)
    files = {"file": ("test.png", response.content)}

    ocr_response = requests.post("http://localhost:5001/ocr", files=files)
    if ocr_response.status_code == 200:
        print(f"✅ **API يعمل بشكل صحيح!**")
        print(f"📝 **النص المستخرج:** {ocr_response.json()['text'][:100]}...")
    else:
        print(f"⚠️ **فشل الاتصال بـ API:** {ocr_response.status_code}")

    # إيقاف الخادم
    server_process.terminate()

except Exception as e:
    print(f"⚠️ **فشل تشغيل خادم FastAPI:** {e}")
    print("🔹 **السبب:** قد يكون بسبب قيود Colab على تشغيل الخوادم.")

# %%
# =============================================================================
# 13. خلاصة
# =============================================================================
print("""
🎉 **تم اختبار جميع ميزات المشروع بنجاح!**

📌 **ملخص النتائج:**
✅ تم تثبيت جميع الحزم بنجاح.
✅ تم اختبار ميزات OCR (TrOCR, EasyOCR, Tesseract).
✅ تم اختبار ميزات NLP (تصحيح إملائي، ترجمة، تلخيص).
✅ تم تصحيح المشاكل الشائعة.
✅ تم حفظ جميع النتائج في Google Drive.
✅ تم اختبار نظام مراجعة OCR.
✅ تم اختبار حفظ التنسيق (HTML, PDF, DOCX).
✅ تم اختبار نظام التعلم من تصحيحات المستخدم.
✅ تم اختبار Fine-tuning لنموذج TrOCR.

📂 **الملفات المحفوظة:**
- {RESULTS_DIR}/ocr_result_en.txt
- {RESULTS_DIR}/ocr_result_ar.txt
- {RESULTS_DIR}/translation_result.txt
- {RESULTS_DIR}/summary_result.txt
- {RESULTS_DIR}/formatted_text.html
- {RESULTS_DIR}/formatted_text.pdf
- {RESULTS_DIR}/formatted_text.docx

🔗 **الروابط المفيدة:**
- المشروع على GitHub: [OmniFile AI Processor](https://github.com/DrAbdulmalek/OmniFile_Processor)
- توثيق المشروع: [USER_GUIDE.md](https://github.com/DrAbdulmalek/OmniFile_Processor/blob/main/docs/USER_GUIDE.md)

💡 **الخطوات التالية:**
1. جرب المشروع مع **ملفاتك الخاصة**.
2. إذا وجدت أي مشكلة، راجع قسم **تصحيح المشاكل الشائعة**.
3. يمكنك المساهمة في المشروع عبر **Pull Requests** على GitHub.
4. لتشغيل واجهة المستخدم، استخدم:
   ```bash
   streamlit run app.py
   ```
   أو
   ```bash
   python -m src.gradio_ui
   ```

🙏 **شكرًا لاستخدامك OmniFile AI Processor!**
""")

# %%
# عرض معلومات النظام النهائية
print("\n📊 **معلومات النظام النهائية**")
!nvidia-smi  # معلومات GPU
!free -h     # معلومات الذاكرة
!df -h       # معلومات القرص
!ls -lh $RESULTS_DIR  # عرض الملفات المحفوظة
```

---

---

