# 🤝 دليل المساهمة
# Contributing Guide

شكراً لاهتمامك بالمساهمة في **نظام معالجة الترجمات العربية**! 

نرحب بجميع أنواع المساهمات - سواء كانت:
- 🐛 الإبلاغ عن الأخطاء
- 💡 اقتراح ميزات جديدة
- 📝 تحسين التوثيق
- 🔧 إصلاح الأخطاء
- ✨ إضافة ميزات جديدة
- 📖 إضافة قواعد ترجمة جديدة

---

## 📋 جدول المحتويات

1. [قواعد السلوك](#قواعد-السلوك)
2. [كيف أساهم؟](#كيف-أساهم)
3. [إضافة قواعد ترجمة](#إضافة-قواعد-ترجمة)
4. [معايير الكود](#معايير-الكود)
5. [عملية المراجعة](#عملية-المراجعة)

---

## قواعد السلوك

### القيم الأساسية

- 🤝 **الاحترام**: نحترم جميع المساهمين بغض النظر عن مستوى خبرتهم
- 🌍 **الشمولية**: نرحب بالجميع من جميع الخلفيات
- 📚 **التعلم**: نشجع التعلم والأسئلة
- 🎯 **الجودة**: نسعى لأفضل جودة ممكنة

### السلوكيات المقبولة

✅ استخدام لغة ترحيبية وشاملة
✅ احترام وجهات النظر المختلفة
✅ قبول النقد البناء بكل رحابة صدر
✅ التركيز على ما هو أفضل للمجتمع
✅ إظهار التعاطف مع الآخرين

### السلوكيات غير المقبولة

❌ استخدام لغة أو صور جنسية
❌ التعليقات المسيئة أو الهجومية
❌ المضايقة العامة أو الخاصة
❌ نشر معلومات خاصة دون إذن
❌ أي سلوك غير احترافي

---

## كيف أساهم؟

### 1. الإبلاغ عن الأخطاء

إذا وجدت خطأ، افتح [Issue جديد](https://github.com/DrAbdulmalek/arabic-translation-unified/issues/new) مع:

**القالب:**
```markdown
## وصف الخطأ
وصف واضح ومختصر للمشكلة

## خطوات إعادة الإنتاج
1. اذهب إلى '...'
2. انقر على '...'
3. انزل إلى '...'
4. شاهد الخطأ

## السلوك المتوقع
وصف واضح لما كنت تتوقع حدوثه

## السلوك الفعلي
ماذا حدث بالفعل؟

## لقطات الشاشة
إن وجدت، أضف لقطات شاشة

## البيئة
- نظام التشغيل: [مثال: Ubuntu 22.04]
- إصدار Python: [مثال: 3.9.7]
- إصدار Gradio: [مثال: 4.44.0]

## معلومات إضافية
أي سياق آخر مفيد
```

### 2. اقتراح ميزة جديدة

افتح [Issue](https://github.com/DrAbdulmalek/arabic-translation-unified/issues/new) مع:

**القالب:**
```markdown
## وصف الميزة
وصف واضح للميزة المقترحة

## المشكلة التي تحلها
ما المشكلة التي تحلها هذه الميزة؟

## الحل المقترح
كيف ترى تنفيذ هذه الميزة؟

## البدائل المحتملة
هل فكرت في حلول بديلة؟

## السياق الإضافي
أي معلومات أخرى مفيدة
```

### 3. المساهمة بالكود

#### أ) Fork المشروع

```bash
# 1. Fork المستودع على GitHub
# 2. استنساخ Fork الخاص بك
git clone https://github.com/YOUR_USERNAME/arabic-translation-unified.git
cd arabic-translation-unified

# 3. إضافة المستودع الأصلي كـ upstream
git remote add upstream https://github.com/DrAbdulmalek/arabic-translation-unified.git
```

#### ب) إنشاء فرع جديد

```bash
# تحديث main من upstream
git checkout main
git pull upstream main

# إنشاء فرع للميزة
git checkout -b feature/amazing-feature

# أو لإصلاح خطأ
git checkout -b fix/bug-description
```

#### ج) إجراء التغييرات

```bash
# اعمل على التغييرات...
# اختبر التغييرات...

# Commit التغييرات
git add .
git commit -m "feat: إضافة ميزة رائعة"

# أو
git commit -m "fix: إصلاح خطأ في المعالجة"
```

**تنسيق رسائل Commit:**

استخدم [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - ميزة جديدة
- `fix:` - إصلاح خطأ
- `docs:` - تحديث التوثيق
- `style:` - تنسيق الكود (لا يؤثر على الوظيفة)
- `refactor:` - إعادة هيكلة الكود
- `test:` - إضافة أو تعديل الاختبارات
- `chore:` - مهام صيانة

**أمثلة:**
```bash
git commit -m "feat: إضافة دعم لقواعد جديدة"
git commit -m "fix: إصلاح خطأ في معالجة الأرقام"
git commit -m "docs: تحديث README بأمثلة جديدة"
```

#### د) Push ورفع Pull Request

```bash
# Push للفرع
git push origin feature/amazing-feature

# اذهب إلى GitHub وافتح Pull Request
```

**قالب Pull Request:**
```markdown
## الوصف
وصف واضح للتغييرات

## نوع التغيير
- [ ] إصلاح خطأ (تغيير لا يكسر التوافق)
- [ ] ميزة جديدة (تغيير يضيف وظيفة)
- [ ] تغيير يكسر التوافق (يتطلب تحديث major version)
- [ ] تحديث التوثيق

## كيف تم الاختبار؟
وصف الاختبارات التي أجريتها

## Checklist
- [ ] الكود يتبع معايير المشروع
- [ ] أجريت مراجعة ذاتية للكود
- [ ] أضفت تعليقات للأجزاء المعقدة
- [ ] حدثت التوثيق
- [ ] لا توجد تحذيرات جديدة
- [ ] أضفت اختبارات للتغييرات
- [ ] جميع الاختبارات تمر بنجاح
```

---

## إضافة قواعد ترجمة

### البنية المطلوبة

أضف قاعدة جديدة في `translation_rules.json`:

```json
{
  "rule_id": "CATEGORY_NNN",
  "category": "structural|grammatical|lexical|stylistic|cultural|punctuation",
  "english_pattern": "النمط الإنجليزي (بالأحرف الصغيرة)",
  "wrong_arabic": "الترجمة الخاطئة",
  "correct_arabic": "الترجمة الصحيحة",
  "rule_description": "وصف واضح للقاعدة",
  "priority": 1-3,
  "examples": [
    {
      "en": "مثال إنجليزي",
      "ar_wrong": "ترجمة خاطئة",
      "ar_correct": "ترجمة صحيحة"
    }
  ]
}
```

### معايير القواعد

**قاعدة جيدة يجب أن تكون:**

✅ **واضحة**: وصف دقيق للتصحيح
✅ **قابلة للتطبيق**: تطبق على أنماط محددة
✅ **موثقة**: أمثلة واضحة
✅ **مبررة**: سبب لغوي واضح

### الأولويات

- **Priority 1**: تصحيحات أساسية (أخطاء فادحة)
- **Priority 2**: تحسينات مهمة
- **Priority 3**: تحسينات أسلوبية اختيارية

### مثال كامل

```json
{
  "rule_id": "GRAM_010",
  "category": "grammatical",
  "english_pattern": "according to",
  "wrong_arabic": "طبقاً ل",
  "correct_arabic": "وفقاً ل",
  "rule_description": "استخدام 'وفقاً' بدلاً من 'طبقاً' للتعبير عن الإسناد",
  "priority": 2,
  "examples": [
    {
      "en": "According to the report",
      "ar_wrong": "طبقاً للتقرير",
      "ar_correct": "وفقاً للتقرير"
    },
    {
      "en": "According to experts",
      "ar_wrong": "طبقاً للخبراء",
      "ar_correct": "وفقاً للخبراء"
    }
  ]
}
```

---

## معايير الكود

### أسلوب Python

نتبع [PEP 8](https://pep8.org/) مع بعض الاستثناءات:

```python
# ✅ جيد
def process_translation(
    english_text: str,
    arabic_text: str,
    apply_rules: bool = True
) -> Dict:
    """معالجة ترجمة واحدة"""
    result = {
        "original": arabic_text,
        "corrected": corrected_text
    }
    return result


# ❌ سيء
def ProcessTranslation(EnglishText,ArabicText):
    result={"original":ArabicText}
    return result
```

### التعليقات والتوثيق

```python
# ✅ استخدم docstrings للدوال
def apply_rule(self, text: str, rule: TranslationRule) -> str:
    """
    تطبيق قاعدة واحدة على النص
    
    Args:
        text: النص العربي المراد تصحيحه
        rule: القاعدة المراد تطبيقها
        
    Returns:
        النص بعد التصحيح
    """
    return text.replace(rule.wrong_arabic, rule.correct_arabic)

# ✅ علق على الأجزاء المعقدة
# معالجة خاصة للمبني للمجهول مع by
if 'by' in english_text and 'بواسطة' in arabic_text:
    # تحويل للمبني للمعلوم
    ...
```

### التسمية

```python
# ✅ أسماء واضحة وذات معنى
processor = ArabicTranslationProcessor()
corrected_text = processor.process_translation(...)
rule_ids = ["GRAM_001", "STYLE_002"]

# ❌ أسماء غامضة
p = ATP()
ct = p.pt(...)
r = ["G1", "S2"]
```

### التنسيق

استخدم [Black](https://black.readthedocs.io/) للتنسيق التلقائي:

```bash
pip install black
black app.py
```

---

## عملية المراجعة

### ما نراجعه

1. **الوظيفة**: هل يعمل الكود كما هو متوقع؟
2. **جودة الكود**: هل الكود واضح وقابل للصيانة؟
3. **التوثيق**: هل التوثيق كافٍ وواضح؟
4. **الاختبارات**: هل هناك اختبارات كافية؟
5. **الأداء**: هل هناك مشاكل أداء واضحة؟

### الجدول الزمني

- **المراجعة الأولية**: خلال 2-3 أيام
- **المراجعة الشاملة**: خلال أسبوع
- **الدمج**: بعد الموافقة من maintainer واحد على الأقل

### التعامل مع التعليقات

- كن متقبلاً للنقد البناء
- اطرح أسئلة إذا لم تفهم شيئاً
- حدّث الكود بناءً على التعليقات
- ردّ على التعليقات عند إجراء التعديلات

---

## الأسئلة الشائعة

### س: أنا مبتدئ، هل يمكنني المساهمة؟

**ج:** بالطبع! نرحب بجميع المستويات. ابدأ بـ:
- تحسين التوثيق
- إضافة أمثلة
- إصلاح أخطاء إملائية
- إضافة قواعد ترجمة بسيطة

### س: كم يستغرق دمج PR الخاص بي؟

**ج:** عادة 2-7 أيام. يعتمد على:
- حجم التغييرات
- جودة الكود
- وضوح الوصف
- توفر المراجعين

### س: ماذا لو رُفض PR الخاص بي؟

**ج:** لا تقلق! الرفض نادر وعادة يكون مع تفسير واضح. يمكنك:
- فهم سبب الرفض
- إجراء التعديلات اللازمة
- فتح PR جديد

### س: هل أحتاج لمعرفة عميقة باللغة العربية؟

**ج:** يعتمد على نوع المساهمة:
- **إضافة قواعد**: نعم، معرفة جيدة مطلوبة
- **تحسين الكود**: معرفة برمجية كافية
- **التوثيق**: معرفة أساسية تكفي

---

## الموارد المفيدة

### تعلم Git & GitHub
- [Git Handbook](https://guides.github.com/introduction/git-handbook/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [فهم Pull Requests](https://docs.github.com/en/pull-requests)

### تعلم Python
- [Python Tutorial](https://docs.python.org/3/tutorial/)
- [Real Python](https://realpython.com/)
- [Python للمبتدئين (بالعربية)](https://www.youtube.com/results?search_query=python+%D8%A8%D8%A7%D9%84%D8%B9%D8%B1%D8%A8%D9%8A)

### قواعد الترجمة
- كتب أسس الترجمة
- [جامعة الملك عبد العزيز - الترجمة](https://units.imamu.edu.sa/colleges/cl/ts/Pages/default.aspx)

---

## شكراً! ❤️

شكراً لمساهمتك في تحسين معالجة الترجمات العربية!

كل سطر كود، كل تعليق، كل قاعدة - كلها تساهم في جعل الترجمة العربية أفضل.

---

<div align="center">

**معاً نصنع فرقاً في معالجة اللغة العربية**

[📖 التوثيق](https://github.com/DrAbdulmalek/arabic-translation-unified) |
[💬 النقاشات](https://github.com/DrAbdulmalek/arabic-translation-unified/discussions) |
[🐛 الأخطاء](https://github.com/DrAbdulmalek/arabic-translation-unified/issues)

</div>
