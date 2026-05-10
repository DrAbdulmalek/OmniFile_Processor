# التصحيح الإملائي للعربية

## نظرة عامة

يوضح هذا المثال كيفية استخدام نظام التصحيح الإملائي المتقدم في OmniFile لتصحيح الأخطاء الشائعة في نصوص OCR العربية. يدعم النظام تصحيح أخطاء التعرف على النقاط، الحروف المتشابهة، الكلمات المقصورة والمنقوصة، والعديد من أنماط الأخطاء الأخرى.

## المتطلبات

```bash
pip install -r requirements-core.txt -r requirements-nlp.txt
```

## المثال 1: تصحيح أساسي

```python
from modules.core.spell_checker import HybridSpellChecker

checker = HybridSpellChecker()

# نص به أخطاء شائعة من OCR
text = "العلم نور والجهل ظلام ومن جد ووجد"
corrected = checker.correct(text)

print(f"قبل: {text}")
print(f"بعد: {corrected}")
# "العلم نور والجهل ظلام ومن جد ووجد"
```

## المثال 2: تصحيح مع اقتراحات بديلة

```python
from modules.core.spell_checker import HybridSpellChecker

checker = HybridSpellChecker()

text = "الطالب يدرس في الجامعه"
result = checker.correct_with_suggestions(text)

for word_result in result.word_results:
    if word_result.was_corrected:
        print(f"  {word_result.original} → {word_result.corrected}")
        print(f"  الاقتراحات: {word_result.suggestions[:3]}")
```

## المثال 3: التصحيح التكيفي (يتعلم من تصحيحاتك)

```python
from modules.nlp.feedback import append_feedback, apply_correction_dict

# إضافة تصحيح مخصص
append_feedback(
    original="فم",
    corrected="في",
    context="الدرس في الفصل"
)

# بناء قاموس التصحيح
correction_dict = build_correction_dict()

# تطبيق القاموس
text = "الكتاب فم المكتبه"
corrected = apply_correction_dict(text, correction_dict)
# "الكتاب في المكتبة"
```

## المثال 4: معالجة النقاط العربية

```python
from modules.nlp.arabic_nlp_utils import ArabicTextNormalizer

normalizer = ArabicTextNormalizer()

samples = [
    "هل هذا صحيح",      # غير منقطة
    "الولد ذهب الى المدرسة",
    "البحث العلمي يتطلب دقه"
]

for text in samples:
    normalized = normalizer.normalize_diacritics(text)
    dots_restored = normalizer.restore_dots(text)
    print(f"الأصل:    {text}")
    print(f"مُوَحَّد:  {normalized}")
    print(f"مع النقاط: {dots_restored}")
    print("---")
```

## ملاحظات

- نظام التصحيح يدعم اللهجات العربية الخليجية والمصرية والشامية
- يمكن إضافة قواميس مخصصة للمصطلحات المتخصصة
- التصحيح التكيفي يحفظ تصحيحاتك ويتعلم منها
