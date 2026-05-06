## 🧩 أولاً: دعم النصوص المختلطة (عدة لغات في نفس المستند)

### 🎯 المشكلة الحالية
- يحدد المستخدم لغة واحدة فقط (`--lang ar`) مما قد يُفقد أجزاءً إنجليزية أو فرنسية.
- التصحيح الإملائي مُصمم للغة واحدة، مما قد يُفسد الكلمات الأجنبية.
- محركات OCR قد تُخطئ في التعرف إذا لم تُضبط اللغة المناسبة لكل منطقة.

### ✅ الحل: معالجة ذكية متعددة اللغات على مستوى الكتلة والكلمة

#### ملف جديد: `modules/nlp/mixed_language.py`

```python
"""
وحدة معالجة النصوص المختلطة (عربي/إنجليزي/فرنسي/ألماني...)
تقوم بـ:
- كشف اللغة لكل كلمة/كتلة.
- تصحيح إملائي متعدد اللغات.
- إعادة تجميع النص مع الاحتفاظ بالاتجاهات.
"""
import re
from langdetect import detect, DetectorFactory
from spellchecker import SpellChecker  # مكتبة pyspellchecker

# لجعل النتائج مستقرة
DetectorFactory.seed = 0

# قواميس تصحيح خاصة بالعربية (يمكن تحميلها من ملف)
ARABIC_CORRECTIONS = {
    'السلام': 'السلام',
    'مرحبا': 'مرحباً',
    # ... القائمة الطويلة موجودة في المشروع
}

class MixedLanguageHandler:
    def __init__(self, languages=['ar', 'en', 'fr', 'de']):
        """
        languages: قائمة رموز اللغات المدعومة
        """
        self.languages = languages
        self.spell_checkers = {}
        for lang in languages:
            if lang != 'ar':  # العربية نستخدم قاموسنا الخاص
                try:
                    self.spell_checkers[lang] = SpellChecker(language=lang)
                except:
                    print(f"تحذير: لم يتم تحميل المدقق الإملائي للغة {lang}")

    def detect_language(self, text):
        """كشف اللغة الغالبة في النص"""
        if not text or not text.strip():
            return 'ar'
        try:
            return detect(text)
        except:
            # fallback: إذا كان النص يحتوي على حروف عربية نعتبره عربي
            if re.search(r'[\u0600-\u06FF]', text):
                return 'ar'
            return 'en'

    def split_by_language(self, text):
        """
        تقطيع النص إلى أجزاء حسب اللغة على مستوى الكلمة تقريباً.
        تعيد قائمة من (language, substring)
        """
        # تقسيم بسيط: كل كلمة لوحدها مع الحفاظ على المسافات والترقيم
        tokens = re.findall(r'\S+|\s+', text)
        segments = []
        current_lang = None
        current_segment = ''
        for token in tokens:
            if token.isspace():
                current_segment += token
                continue
            lang = self.detect_language(token)
            if lang != current_lang:
                if current_segment:
                    segments.append((current_lang, current_segment))
                current_lang = lang
                current_segment = token
            else:
                current_segment += token
        if current_segment:
            segments.append((current_lang, current_segment))
        return segments

    def correct_text_mixed(self, text):
        """
        تصحيح إملائي مع الحفاظ على تعدد اللغات.
        """
        segments = self.split_by_language(text)
        corrected_parts = []
        for lang, segment in segments:
            if lang == 'ar':
                corrected = self._correct_arabic(segment)
            elif lang in self.spell_checkers:
                corrected = self._correct_with_spellchecker(lang, segment)
            else:
                corrected = segment
            corrected_parts.append(corrected)
        return ''.join(corrected_parts)

    def _correct_arabic(self, text):
        # استخدام قاموس التصحيحات المضمن
        words = re.findall(r'\S+', text)
        corrected_words = []
        for w in words:
            if w in ARABIC_CORRECTIONS:
                corrected_words.append(ARABIC_CORRECTIONS[w])
            else:
                corrected_words.append(w)
        # إعادة بناء النص مع المسافات (تقريبي)
        return ' '.join(corrected_words)

    def _correct_with_spellchecker(self, lang, text):
        checker = self.spell_checkers[lang]
        words = re.findall(r'\S+', text)
        corrected = [checker.correction(w) if checker.correction(w) else w for w in words]
        return ' '.join(corrected)

    def get_ocr_language_params(self, full_text):
        """
        يعيد قائمة لغات مناسبة لإرسالها لمحرك OCR (مثلاً لـ EasyOCR أو Tesseract)
        بناءً على تحليل سريع لعينة من النص.
        """
        langs_detected = set()
        words = full_text.split()[:50]  # عينة أول 50 كلمة
        for w in words:
            langs_detected.add(self.detect_language(w))
        # تحويل الرموز إلى الصيغة المطلوبة (مثلاً 'ar', 'en')
        return list(langs_detected)
```

### 🔗 الدمج مع سير العمل الحالي

في `modules/vision/ocr.py` (أو حيث يتم استدعاء التصحيح بعد OCR)، يمكننا استبدال استدعاءات المصحح القديم:

```python
# بدلاً من ذلك:
from modules.nlp.mixed_language import MixedLanguageHandler
mixed_handler = MixedLanguageHandler()

# داخل دالة معالجة نص OCR:
text = ocr_raw_text
corrected_text = mixed_handler.correct_text_mixed(text)
```

وأيضاً عند استخراج النص الأولي يمكننا طلب من EasyOCR أو Tesseract التعرف بعدة لغات:

```python
# مثال: في دالة run_easyocr
langs = mixed_handler.get_ocr_language_params(sample_text)
# إذا كانت فارغة نعطيها ['ar', 'en'] افتراضياً
reader = easyocr.Reader(langs if langs else ['ar','en'])
result = reader.readtext(image)
```

هذا يضمن أن كل محرك يتعامل مع النص بلغته المناسبة.

---

## 📊 ثانياً: تحسين كشف الجداول من الصور مباشرة (باستخدام Table Transformer)

### 🎯 الهدف
استبدال (أو تحسين) الطرق الحالية المعتمدة على خطوط Hough وتحليل المحيطات، بنموذج Deep Learning حديث هو **Table Transformer (TATR)** من Microsoft، القادر على كشف الجداول وبنيتها (صفوف/أعمدة) من الصور مباشرة.

### 📁 ملف جديد: `modules/vision/table_detection.py`

```python
"""
وحدة كشف الجداول باستخدام نموذج Table Transformer (TATR).
يتطلب تثبيت transformers, torch, timm.
"""
import torch
from transformers import AutoModelForObjectDetection, AutoImageProcessor
from PIL import Image
import numpy as np

class TableDetectionTransformer:
    def __init__(self, model_name="microsoft/table-transformer-detection", device=None):
        """
        نموذج كشف الجداول في الصور.
        يمكن استخدام نموذج detection فقط، أو يمكن لاحقاً استخدام structure recognition.
        """
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModelForObjectDetection.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def detect_tables(self, image_path, threshold=0.8):
        """
        يعيد قائمة بالجداول المكتشفة، كل جدول بصيغة bbox (x1,y1,x2,y2) واحتمالية.
        """
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        # المعالجة اللاحقة (post-processing)
        target_sizes = torch.tensor([image.size[::-1]]).to(self.device)
        results = self.processor.post_process_object_detection(
            outputs, threshold=threshold, target_sizes=target_sizes
        )[0]
        tables = []
        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            box = [round(i) for i in box.tolist()]
            tables.append({
                "bbox": box,  # [x1, y1, x2, y2]
                "score": round(score.item(), 3),
                "label": self.model.config.id2label[label.item()]  # 'table' or 'table rotated'
            })
        return tables

    def detect_structure(self, image, table_bbox):
        """
        (اختياري) لكشف بنية الجدول (صفوف/أعمدة) داخل مربع الجدول.
        يمكن استخدام نموذج structure recognition من Microsoft.
        لكن لتجنب التعقيد، يمكن اقتصار على كشف الجدول فقط ثم استخدام طرق تقليدية لاحقاً.
        مؤقتاً نعيد None.
        """
        # يمكن تنفيذها لاحقاً
        return None
```

### 🧪 دمجها في أنبوب المعالجة (Vision Pipeline)

نضيف دالة في `modules/vision/ocr.py` أو في `main.py` لاستخدام الكاشف الجديد:

```python
from modules.vision.table_detection import TableDetectionTransformer

# تهيئة الكاشف مرة واحدة (يمكن أن يكون ثقيلاً، لذا نحمّله عند الحاجة)
table_detector = TableDetectionTransformer(device='cpu')  # أو 'cuda'

def extract_tables_from_image(image_path):
    tables = table_detector.detect_tables(image_path, threshold=0.7)
    return tables
```

ثم لكل جدول مكتشف، نقوم بقص المنطقة وإرسالها إلى OCR (بنفس محرك النصوص) للحصول على النص. يمكن أيضاً استخدام خوارزميات تقليدية مثل تحليل الخطوط داخل منطقة الجدول لاستخراج الخلايا، لكن نموذج Table Transformer قوي جداً في كشف حدود الجداول حتى في الصور الممسوحة ضوئياً الملتوية.

### 📦 تثبيت الاعتماديات الإضافية
أضف هذه السطور إلى `requirements.txt`:

```
transformers>=4.37.0
torch>=2.0.0
timm>=0.9.0
langdetect>=1.0.9
pyspellchecker>=0.7.0
```

### ⚙️ تعديل ملف التكوين (config.py)
لجعل هذه الميزات اختيارية، يمكن إضافة إعدادات في ملف الإعدادات، مثلاً:

```python
USE_TABLE_TRANSFORMER = True  # لتفعيل الكشف المحسن
MIXED_LANGUAGE_CORRECTION = True
```

---

## 🔄 ملخص التغييرات المطلوبة على المشروع الأصلي

1. **إنشاء الملفين:**
   - `modules/nlp/mixed_language.py` (الكود أعلاه)
   - `modules/vision/table_detection.py` (الكود أعلاه)

2. **في `main.py` أو `modules/vision/ocr.py`:**
   - استيراد `MixedLanguageHandler` واستخدامه بعد استخراج النص لتصحيحه بلغات متعددة.
   - استيراد `TableDetectionTransformer` وإجراء الكشف عن الجداول قبل OCR، ثم قص المناطق وإرسالها للتعرف.

3. **تعديل `requirements.txt`** بإضافة المكتبات الجديدة.

4. **اختبار التكامل:**
   - شغّل الأمر CLI مع `--lang auto` (يمكنك إضافة دعم وضع `auto` الذي يستخدم mixed_handler لتحديد اللغات).
   - أو شغّل Gradio/Streamlit لتجربة الوثائق المختلطة والجداول.

---

## 🧪 مثال على الاستخدام بعد التعديلات
