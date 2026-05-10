# أفضل الممارسات للعربية

## نظرة عامة

دليل شامل لأفضل الممارسات في معالجة اللغة العربية في سياق OCR و NLP.

## 1. تحديات الخط العربي

الخط العربي له خصائص فريدة تؤثر على دقة OCR:

### الربط بين الحروف
الحروف العربية تتصل ببعضها البعض حسب الموضع (بداية، وسط، نهاية، منفصل). هذا يجعل تجزئة الكلمات أصعب من اللغات اللاتينية.

```python
# استخدام التجزئة الذكية بدلاً من التجزئة البسيطة
from modules.vision.htr.word_segmenter import ArabicWordSegmenter

segmenter = ArabicWordSegmenter()
words = segmenter.segment(line_image)  # تأخذ الربط بعين الاعتبار
```

### النقاط والحركات
الحروف العربية تستخدم النقاط (ب، ت، ث، ن، ي) والحركات (فتحة، ضمة، كسرة، سكون) لتغيير المعنى.

```python
# استعادة النقاط المفقودة
from modules.vision.htr.dotted_recovery import DottedRecovery

recovery = DottedRecovery()
text = recovery.restore_dots("الولد ذهب الى المدرسة")
# "الولد ذهب إلى المدرسة"
```

## 2. اتجاه النص (RTL)

```python
# الحفاظ على RTL عند التصدير
from modules.export.layout_preserving import LayoutPreservingExporter

exporter = LayoutPreservingExporter()
exporter.export_to_docx(text, output_path="output.docx", rtl_support=True)
```

## 3. الأشكال المختلفة للحرف الواحد

```python
# التطبيع قبل المقارنة
from modules.nlp.arabic_nlp_utils import ArabicTextNormalizer

normalizer = ArabicTextNormalizer()
text = normalizer.normalize("السلام عليكم")  # إزالة التشكيل، توحيد الألفات
```
