# معالجة النصوص المختلطة (عربي/إنجليزي)

## نظرة عامة

يعالج هذا المثال المستندات التي تحتوي على نصوص عربية وإنجليزية مختلطة، مثل المستندات الطبية، الأكاديمية، والتقنية. يوفر OmniFile أدوات متقدمة لتجزئة النص، حماية المصطلحات المتخصصة، والحفاظ على اتجاه الكتابة (RTL/LTR).

## المتطلبات

```bash
pip install -r requirements-core.txt -r requirements-ocr.txt -r requirements-nlp.txt
```

## المثال 1: تجزئة النص المختلط

```python
from modules.nlp.mixed_text import MixedTextProcessor

processor = MixedTextProcessor(
    preserve_medical_terms=True,
    protect_code_blocks=True
)

text = "الجرعة الموصى بها: 500mg من Paracetamol كل 6 ساعات"
result = processor.process(text)

print(result)
# الناتج:
# {
#   'original': "الجرعة الموصى بها: 500mg من Paracetamol كل 6 ساعات",
#   'segments': [
#     {'text': "الجرعة الموصى بها: ", 'lang': 'ar', 'dir': 'rtl'},
#     {'text': "500mg", 'lang': 'en', 'dir': 'ltr', 'type': 'measurement'},
#     {'text': " من ", 'lang': 'ar', 'dir': 'rtl'},
#     {'text': "Paracetamol", 'lang': 'en', 'dir': 'ltr', 'type': 'medical_term'},
#     {'text': " كل 6 ساعات", 'lang': 'ar', 'dir': 'rtl'}
#   ],
#   'protected_terms': ['Paracetamol', '500mg']
# }
```

## المثال 2: كشف اللغة تلقائياً

```python
from modules.nlp.language_detector import LanguageDetector

detector = LanguageDetector()

samples = [
    "بسم الله الرحمن الرحيم",
    "Hello World",
    "المريض يحتاج إلى MRI scan",
    "The algorithm uses O(n log n) complexity",
]

for text in samples:
    result = detector.detect(text)
    print(f"'{text}' → {result['language']} (ثقة: {result['confidence']:.2%})")
```

## المثال 3: تصدير نص مختلط مع الحفاظ على RTL

```python
from modules.export.layout_preserving import LayoutPreservingExporter
from modules.nlp.mixed_text import MixedTextProcessor

processor = MixedTextProcessor()
exporter = LayoutPreservingExporter()

text = "العنوان: Introduction to Machine Learning"
segments = processor.process(text)

# تصدير إلى DOCX مع الحفاظ على اتجاه كل مقطع
exporter.export_to_docx(
    segments=segments['segments'],
    output_path="output_mixed.docx",
    rtl_support=True
)
```

## المثال 4: حماية المصطلحات أثناء التصحيح

```python
from modules.core.spell_checker import HybridSpellChecker
from modules.nlp.protected_words import ProtectedWordsManager

# إعداد كلمات محمية
protected = ProtectedWordsManager()
protected.add_terms([
    "Paracetamol", "Ibuprofen", "Amoxicillin",
    "MRI", "CT scan", "ECG",
    "500mg", "250ml", "10cm"
])

checker = HybridSpellChecker(protected_words=protected)

text = "يحتاج المريض الى Paracetamol بجرعة 500mg"
corrected = checker.correct(text)
# "يحتاج المريض إلى Paracetamol بجرعة 500mg"
# ↑ تم تصحيح "الى" إلى "ألى" لكن المصطلحات الإنجليزية حُميت
```

## ملاحظات مهمة

- المصطلحات الطبية تُحمى تلقائياً من التصحيح الإملائي الخاطئ
- اتجاه النص (RTL/LTR) يُحفظ لكل مقطع لضمان عرض صحيح في DOCX
- الأرقام والوحدات تُعالج ككيانات مستقلة للحفاظ على دقتها
- استخدم `preserve_medical_terms=True` لحماية المصطلحات الطبية تلقائياً
