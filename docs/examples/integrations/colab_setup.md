# إعداد سريع على Google Colab

## نظرة عامة

تعليمات سريعة لتشغيل OmniFile Processor على Google Colab مع دعم GPU.

## الخطوات

```python
# 1. استنساخ المشروع
!git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
%cd OmniFile_Processor

# 2. التثبيت السريع (لـ Colab)
!pip install -q -r requirements-colab.txt

# 3. التحقق من GPU
import torch
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

# 4. تشغيل الواجهة
from modules.ui.gradio_app import create_gradio_interface
app = create_gradio_interface()
app.launch(share=True)  # إنشاء رابط عام

# 5. معالجة صورة
from modules.vision.ocr_engine import OCREngine
from PIL import Image
import numpy as np

ocr = OCREngine(engine="trocr")
image = Image.open("sample.png")
result = ocr.recognize(image, language="ar")
print(result.text)
```
