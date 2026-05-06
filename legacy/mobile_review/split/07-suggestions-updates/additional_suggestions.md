## 1. إضافة محرك OCR خامس (Surya) إلى دفتر Colab والمشروع

**Surya** هو محرك OCR حديث (من مطور Marker) يدعم 90+ لغة، ويتميز بدقة عالية في التعرف على النصوص متعددة اللغات، وكشف الأسطر، وتحليل التخطيط. سنضيفه مع إمكانية توحيد المخرجات وفق الهيكل القياسي (البند التالي).

### تثبيت Surya في خلية Colab
```python
!pip install -q surya-ocr
```

### دالة للتعرف باستخدام Surya (لتوضع في `modules/vision/surya_ocr.py`)
```python
import os
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
from PIL import Image

class SuryaOCREngine:
    def __init__(self, langs=["ar", "en"]):
        self.langs = langs
        self.det_model = load_det_model()
        self.det_processor = load_det_processor()
        self.rec_model = load_rec_model()
        self.rec_processor = load_rec_processor()

    def extract_text(self, image_path):
        image = Image.open(image_path)
        predictions = run_ocr(
            [image],
            [self.langs],
            self.det_model,
            self.det_processor,
            self.rec_model,
            self.rec_processor
        )
        # predictions[0] يحتوي على قائمة TextLine بكل سطر
        lines = predictions[0]
        blocks = []
        for line in lines:
            blocks.append({
                "bbox": [line.bbox[0]/image.width, line.bbox[1]/image.height,
                         line.bbox[2]/image.width, line.bbox[3]/image.height],
                "text": line.text,
                "confidence": line.confidence
            })
        full_text = "\n".join([line.text for line in lines])
        return full_text, blocks
```

### استدعاؤها ضمن `modules/vision/ocr.py`
```python
from modules.vision.surya_ocr import SuryaOCREngine

if engine_name == "surya":
    engine = SuryaOCREngine(langs=lang_list)
    full_text, blocks = engine.extract_text(image_path)
```

### في دفتر Colab أضف خلية لتجربة سريعة
```python
from modules.vision.surya_ocr import SuryaOCREngine
s = SuryaOCREngine(langs=["ar","en"])
text, blocks = s.extract_text("/content/test_arabic.jpg")
print(text[:500])
```

---

## 2. تصميم هيكل JSON قياسي موحد للمشروع

لتوحيد النتائج بين المحركات المختلفة وسهولة التصدير والمراجعة، أقترح هذا الهيكل (مبني على تجارب المشروع):

```json
{
  "metadata": {
    "source_file": "document.pdf",
    "processing_date": "2026-05-03T12:34:56",
    "engine": "surya",
    "languages_detected": ["ar", "en"],
    "page_count": 5,
    "version": "1.0"
  },
  "pages": [
    {
      "page_index": 0,
      "width": 2480,
      "height": 3508,
      "image_path": "page_0.jpg",
      "blocks": [
        {
          "id": "block_1",
          "type": "paragraph",
          "bbox": [0.1, 0.15, 0.9, 0.25],
          "text": "النص المستخرج كاملاً ...",
          "confidence": 0.96,
          "language": "ar",
          "direction": "rtl"
        },
        {
          "id": "block_2",
          "type": "table",
          "bbox": [0.05, 0.3, 0.95, 0.7],
          "confidence": 0.88,
          "structure": {
            "rows": 5,
            "cols": 4,
            "cells": [
              {"row": 0, "col": 0, "text": "الاسم", "bbox": [0.1,0.31,0.25,0.33], "confidence": 0.99},
              ...
            ]
          }
        },
        {
          "id": "block_3",
          "type": "image",
          "bbox": [0.1, 0.72, 0.4, 0.85],
          "image_file": "extracted_img_3.png",
          "caption": {
            "text": "شكل 1: توزيع البيانات",
            "bbox": [0.1, 0.86, 0.4, 0.88]
          }
        }
      ]
    }
  ]
}
```

### لماذا هذا الهيكل؟
- **صفحات متعددة**: يدعم ملفات PDF متعددة الصفحات.
- **إحداثيات نسبية**: تصلح لأي دقة.
- **تعدد اللغات**: خاصية `language` و `direction` لكل كتلة.
- **أنواع متنوعة**: فقرة، جدول، صورة، تسمية، تذييل...
- **قابل للتوسع**: يمكن إضافة حقول `correction` لاحقًا عند المراجعة.

### تحويل مخرجات المحركات المختلفة إلى هذا الهيكل
سننشئ دالة `normalize_output()` في كل محرك (أو في وحدة `vision/ocr.py`) لتصدير النتائج بهذا التنسيق، مما يضمن أن واجهة المراجعة والمُصدر يعملان بشكل موحد.

---

## 3. واجهة المراجعة على الجوال (تعزيز الكود السابق ليدعم الهيكل الجديد)

الواجهة التي قدمتها سابقًا تعمل بكفاءة. سأضيف هنا فقط:
- دعم **التنقل بين الصفحات** (إذا كان المستند متعدد الصفحات).
- توليد **رابط QR تلقائي** من Colab للوصول السهل من الهاتف.
- حقل التصحيح سيُكتب مباشرة في JSON الهيكلي المعدل (تم دمج `ocr_corrected.json` مع `correction` في كل كتلة).

### إضافة إلى `server.py`: دعم ملف JSON متعدد الصفحات
```python
@app.route('/get_page/<int:page_idx>')
def get_page(page_idx):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if page_idx < len(data['pages']):
        page = data['pages'][page_idx]
        return jsonify({'page': page, 'total_pages': len(data['pages'])})
    return jsonify({'error': 'Page not found'}), 404
```

وفي `templates/review.html` أضف أزرار تنقل صفحات أعلى الشاشة، وعند الحفظ يُحفظ التصحيح في خصائص الكتلة (`block.correction`) داخل نفس الكائن.

### تشغيل Colab مع رابط QR
أضف خلية بعد تشغيل الخادم:
```python
!pip install -q pyqrcode
import pyqrcode, socket
from IPython.display import display, HTML
hostname = socket.gethostbyname(socket.gethostname())
url = f"http://{hostname}:5000"
qr = pyqrcode.create(url)
print(f"امسح الكود من هاتفك: {url}")
display(HTML(f'<img src="data:image/png;base64,{qr.png_as_base64_str(scale=5)}">'))
```

---

## 4. تنفيذ التنسيق المطابق (محاكاة الكتابة الحاسوبية) – تكامل كامل

لقد قدمنا `modules/export/layout_preserving.py` سابقًا. سنعززه ليدعم:
- **تصدير HTML** مع اتجاهات مختلطة (`dir="auto"` أو `dir="rtl"` للكتل العربية).
- **تصدير PDF عبر WeasyPrint** من HTML المولد.
- **التعامل مع الهيكل الجديد** (الصفحات المتعددة، الجداول، الصور مع تسمياتها).

### دالة تصدير HTML محسّنة
```python
def layout_to_html(layout_data, output_html):
    pages = layout_data.get("pages", [])
    html_parts = ['<html><head><meta charset="UTF-8"><style>',
                  'body { font-family: "Arial", sans-serif; }',
                  '.page { margin-bottom: 20px; padding: 20px; border:1px solid #ccc; position:relative; }',
                  'table { border-collapse: collapse; width: auto; }',
                  'td { border: 1px solid black; padding: 5px; }',
                  'img { max-width: 100%; }',
                  '</style></head><body>']
    for page in pages:
        html_parts.append(f'<div class="page" style="width:{page["width"]}px;height:{page["height"]}px;">')
        for block in page["blocks"]:
            b_type = block["type"]
            # تحويل الإحداثيات النسبية إلى موضع مطلق
            left = block["bbox"][0] * page["width"]
            top = block["bbox"][1] * page["height"]
            width = (block["bbox"][2] - block["bbox"][0]) * page["width"]
            height = (block["bbox"][3] - block["bbox"][1]) * page["height"]
            style = f"position:absolute; left:{left}px; top:{top}px; width:{width}px; height:{height}px; overflow:hidden;"
            if b_type == "paragraph":
                dir_attr = 'dir="rtl"' if block.get("direction") == "rtl" else 'dir="ltr"'
                html_parts.append(f'<div style="{style}" {dir_attr}>{block["text"]}</div>')
            elif b_type == "table":
                # بناء جدول
                html_parts.append(f'<div style="{style}"><table>')
                # استخدم structure.cells
                rows = {}
                for cell in block.get("structure", {}).get("cells", []):
                    r, c = cell["row"], cell["col"]
                    rows.setdefault(r, {})[c] = cell["text"]
                for r in sorted(rows.keys()):
                    html_parts.append("<tr>")
                    for c in sorted(rows[r].keys()):
                        html_parts.append(f"<td>{rows[r][c]}</td>")
                    html_parts.append("</tr>")
                html_parts.append("</table></div>")
            elif b_type == "image":
                img_src = block.get("image_file", "")
                html_parts.append(f'<div style="{style}"><img src="{img_src}" style="width:100%;height:100%;object-fit:contain;"></div>')
                if "caption" in block:
                    cap = block["caption"]
                    cap_style = f"position:absolute; left:{cap['bbox'][0]*page['width']}px; top:{cap['bbox'][1]*page['height']}px; width:{(cap['bbox'][2]-cap['bbox'][0])*page['width']}px;"
                    html_parts.append(f'<div style="{cap_style}"><em>{cap["text"]}</em></div>')
        html_parts.append("</div>")
    html_parts.append("</body></html>")
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write("\n".join(html_parts))
```

هذا الإخراج سيضع النص والصور والجداول **في نفس مواقعها الأصلية** على الصفحة، وكأنها أعيدت كتابتها.

### تحويل HTML إلى PDF باستخدام WeasyPrint (داخل Colab)
```python
!pip install -q weasyprint
from weasyprint import HTML
HTML('output_layout.html').write_pdf('output_mimic.pdf')
```

---

## 5. تدريب Table Transformer على بيانات عربية

### الخطوات العملية:

#### أ. تجهيز مجموعة بيانات عربية
- اجمع صور مستندات عربية تحتوي على جداول (فواتير، كشوفات، تقارير).
- قم بتوسيم (labeling) الجداول باستخدام أداة مثل **Label Studio** أو **CVAT**، وصدّر البيانات بصيغة COCO (bounding box لكل جدول مع تصنيف `table`).
- يحتوي COCO على ملف `annotations.json` ومجلد `images`.

#### ب. تحميل النموذج المدرّب مسبقًا وضبطه
```python
from transformers import AutoModelForObjectDetection, TrainingArguments, Trainer
from datasets import load_dataset

# تحميل مجموعة البيانات المحولة إلى تنسيق Hugging Face Dataset
dataset = load_dataset("imagefolder", data_dir="arabic_tables_coco", split="train")

# تحميل معالج الصور والنموذج
model_name = "microsoft/table-transformer-detection"
processor = AutoImageProcessor.from_pretrained(model_name)
model = AutoModelForObjectDetection.from_pretrained(model_name)

# دالة تحويل البيانات لتضمين annotations (هنا مبسطة: يجب تحويل COCO إلى تنسيق 'image' و'objects')
def transform(batch):
    images = [x.convert("RGB") for x in batch["image"]]
    inputs = processor(images=images, return_tensors="pt")
    # ... بناء labels من annotations (تدريب الكشف)
    return inputs
```

نظرًا لأن تحويل COCO إلى تنسيق Hugging Face يتطلب شرحًا طويلًا، يمكن استخدام مكتبة `huggingface_hub` أو سكربت مخصص، لكن الفكرة: **نستخدم نفس معمارية Table Transformer ونجري fine-tuning على الصور العربية المُوسومة**.

#### ج. تشغيل التدريب
```python
training_args = TrainingArguments(
    output_dir="./arabic-table-detector",
    per_device_train_batch_size=4,
    num_train_epochs=10,
    logging_steps=100,
    evaluation_strategy="no",
    save_steps=500,
    remove_unused_columns=False,
)
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    tokenizer=processor,
)
trainer.train()
model.save_pretrained("./arabic-table-detector")
```

#### د. استخدام النموذج المُخصص بعد التدريب
في `modules/vision/table_detection.py` يمكن تحميل النموذج المحفوظ:
```python
self.model = AutoModelForObjectDetection.from_pretrained("./arabic-table-detector")
self.processor = AutoImageProcessor.from_pretrained("./arabic-table-detector")
```

**نصيحة**: إذا كانت البيانات صغيرة، يمكن استخدام تقنيات data augmentation (تشويه بسيط، تدوير، تغيير إضاءة) أثناء التدريب.

---

## 6. ضبط المصحح الإملائي ليدعم لغات أكثر ويتعلم من المستخدم

### توسيع MixedLanguageHandler لدعم لغات جديدة
أضف في `mixed_language.py`:
```python
SUPPORTED_LANGUAGES = {
    'ar': 'arabic',
    'en': 'english',
    'fr': 'french',
    'de': 'german',
    'es': 'spanish',
    'tr': 'turkish',
    'ur': 'urdu',
}
# يمكنك تحميل قواميس pyspellchecker لكل لغة تتوفر.
```
- بالنسبة للعربية، القاموس الحالي 186 كلمة غير كافٍ. يمكن تعزيزه بقاموس خارجي كبير (مثلاً من قائمة الكلمات العربية في مشروع QaSim أو Arramooz).
- استخدم SymSpell للسرعة في التصحيح الإملائي.

### التعلم من التصحيحات (نظام التغذية الراجعة)
كل مرة يُصحح فيها المستخدم نصًا في واجهة المراجعة، تُحفظ التعديلات. يمكن جدولتها لبناء **نموذج تصحيح مخصص**:
1. استخراج الأزواج (الكلمة الخاطئة -> التصحيح).
2. تدريب نموذج Seq2Seq صغير (مثل ByT5) على هذه الأزواج لتصحيح الأخطاء الإملائية العربية بدقة أعلى.
3. أو ببساطة تحديث قاموس `ARABIC_CORRECTIONS` دوريًا.

### مثال: تحويل التصحيحات إلى قاموس
```python
# بعد جمع العديد من الملفات corrected.json
corrections_pairs = set()
for correction_file in glob("corrections/*.json"):
    data = json.load(open(correction_file))
    for page in data["pages"]:
        for block in page["blocks"]:
            if "original_text" in block and "corrected_text" in block:
                # استخرج الكلمات المختلفة (باستخدام difflib)
                ...
                corrections_pairs.add((wrong_word, right_word))

# حفظ القاموس muzawwad.json
```

### دمج SymSpell للعربية
```python
from symspellpy import SymSpell, Verbosity
sym_spell = SymSpell(max_dictionary_edit_distance=2)
sym_spell.load_dictionary("arabic_words.txt", term_index=0, count_index=1)
# لتصحيح كلمة
suggestions = sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
```

---
سأبدأ **بتنفيذ خطة العمل** التي طلبتها، مع **تفاصيل كاملة وكودات جاهزة للتشغيل**. سنقسم العمل إلى **3 مراحل رئيسية** كما طلبت:

---

---

## 📌 **المرحلة 1: تطوير تطبيق الموبايل (Flutter + FastAPI)**
