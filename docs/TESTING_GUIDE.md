# 🧠 دليل الاختبار والتطوير — OmniFile AI Processor

مشروع **OmniFile_Processor** هو نظام متكامل يجمع بين قوة المعالجة اللغوية (NLP) وتقنيات التعرف الضوئي على الحروف (OCR) مع التركيز على المحتوى العربي. إليك الدليل العملي لاختبار المشروع وتطويره باستخدام "غراديو" (Gradio) على مختلف المنصات.

---

## أولاً: اختبار المشروع على الحاسوب (Manjaro Linux)

بما أنك تستخدم توزيعة Manjaro، فالبيئة مثالية لتشغيل المشروع محلياً:

### 1. إعداد البيئة الافتراضية:

افتح Terminal وقم بإنشاء بيئة معزولة لتجنب تضارب المكتبات:

```bash
git clone https://github.com/DrAbdulmalek/OmniFile_Processor
cd OmniFile_Processor
python -m venv venv
source venv/bin/activate

# التثبيت المتدرج — اختر المستوى المناسب:
pip install -r requirements-core.txt                          # الأساسي فقط (~1.5 GB, ~3 min)
pip install -r requirements-core.txt -r requirements-ocr.txt   # + محركات OCR
pip install -r requirements-core.txt -r requirements-nlp.txt   # + معالجة لغة
pip install -r requirements-full.txt          # الكامل (~6-8 GB, ~15-30 min)
```

### 2. التشغيل المحلي:

يمكنك تشغيل واجهة Streamlit (الموجودة مسبقاً) أو ملف Gradio الموجود في `notebooks/OmniFile_Gradio_Debugger.ipynb`.

---

## ثانياً: اختبار المشروع على الجوال

بسبب حجم نماذج الذكاء الاصطناعي (مثل TrOCR)، لا يُنصح بالتشغيل البرمجي الكامل داخل الجوال، بل الاعتماد على **واجهة ويب**:

### 1. عن طريق الحاسوب:
قم بتشغيل واجهة Gradio على حاسوبك مع تفعيل خاصية `share=True` وسيعطيك رابطاً (gradio.live) يمكنك فتحه من متصفح الجوال.

### 2. عن طريق كولاب:
تشغيل النوت بوك الموجود في `notebooks/OmniFile_Gradio_Debugger.ipynb` من متصفح الجوال (Chrome/Safari) سيمنحك واجهة تحكم كاملة.

---

## ثالثاً: ملف Jupyter Notebook (.ipynb) لـ Google Colab مع واجهة Gradio

👉 **الملفات الجاهزة:**
- [`notebooks/OmniFile_Diagnostic.ipynb`](../notebooks/OmniFile_Diagnostic.ipynb) — فحص شامل + واجهة Gradio (25 خلية)
- [`notebooks/OmniFile_Gradio_Debugger.ipynb`](../notebooks/OmniFile_Gradio_Debugger.ipynb) — معالجة + بحث + إحصائيات

### الخلية الأولى: تثبيت المتطلبات (Setup)

```python
# 1. تنزيل المشروع من GitHub
!git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
%cd OmniFile_Processor

# 2. تثبيت المكتبات (متدرج)
!pip install -r requirements-core.txt          # الأساسيات
!pip install -r requirements-core.txt -r requirements-ocr.txt   # + OCR
# للحصول على كل شيء (NLP ثقيل):
# !pip install -r requirements-full.txt
```

### الخلية الثانية: كود واجهة Gradio للتجربة والتصحيح

هذا الكود مصمم ليعمل كـ "غلاف" (Wrapper) لوظائف مشروعك الأساسية. راجع الملف الكامل في النوت بوك أعلاه.

---

## رابعاً: مراجعة المشروع (Review) ومقترحات التطوير

من خلال بنية المشروع "OmniFile" كونه يدمج **IntelliFile** و **Arabic AI**:

### 1. إدارة الذاكرة (Memory Management)

بما أنك تستخدم نماذج ثقيلة مثل TrOCR، يفضل في كود كولاب إضافة فحص للـ GPU:
```python
device = "cuda" if torch.cuda.is_available() else "cpu"
```

استخدم `torch.cuda.empty_cache()` بعد كل عملية معالجة ملف كبير لتجنب انهيار الجلسة (Crash).

### 2. تحسين الـ OCR العربي (Hybrid Logic)

بما أنك تدمج **EasyOCR** و **TrOCR**، اقترح عمل "منطق هجين" (Hybrid Logic):
- **EasyOCR** → لتحديد مناطق النص (Detection)
- **TrOCR** → لقراءة النص (Recognition)

هذا يعطي **دقة أعلى** في الوثائق الطبية المعقدة.

### 3. التصحيح اللغوي (SymSpell)

تأكد من بناء معجم (Dictionary) طبي متخصص يعتمد على مصطلحات الجراحة العظمية التي تملكها، لأن القواميس العامة قد "تصحح" مصطلحات طبية لاتينية/عربية بشكل خاطئ.

### 4. هيكلية البيانات (Data Architecture)

في مشروع "Ultimate Classifier"، تأكد من فصل منطق "فرز الملفات" عن منطق "تحليل المحتوى" لتقليل زمن المعالجة:
- ابدأ بفرز الملفات حسب النوع (Extension) أولاً
- ثم انتقل للتحليل العميق (Deep Analysis) للملفات غير المعروفة فقط

### 5. التتبع (Debugging)

استخدام `debug=True` في `demo.launch()` داخل كولاب سيظهر لك الأخطاء (Traceback) مباشرة في واجهة المتصفح، مما يسهل عليك معرفة أي "دالة" برمجية فشلت في معالجة الملف دون الحاجة للعودة للـ Terminal.

---

بهذه الطريقة، يمكنك رفع ملفات من جوالك مباشرة إلى الواجهة أثناء تشغيل الكولاب، ومراقبة النتائج وتعديل الكود في الخلية البرمجية وإعادة التشغيل بسرعة.
