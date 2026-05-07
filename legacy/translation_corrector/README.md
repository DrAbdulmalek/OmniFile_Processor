---
title: نظام معالجة الترجمات العربية المتكامل
emoji: 🌍
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.0.0
app_file: app.py
pinned: false
license: mit
tags:
  - arabic
  - translation
  - nlp
  - post-processing
  - correction
  - linguistics
  - huggingface
  - batch-processing
---

# 🚀 نظام معالجة الترجمات العربية المتكامل

**Arabic Translation Processing System – Unified v2.0.0**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Gradio 6.0](https://img.shields.io/badge/Gradio-6.0-orange.svg)](https://gradio.app)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97-Hugging%20Face-FFD21E?logo=huggingface)](https://huggingface.co)

> **نظام متكامل ومتقدم لتحسين جودة الترجمات الآلية من الإنجليزية إلى العربية باستخدام 13+ قاعدة لغوية ذكية وتعبيرات منتظمة متقدمة.**

📅 **آخر تحديث: 9 ديسمبر 2025**

---

## ✨ المميزات الرئيسية

| الميزة | الوصف |
| :--- | :--- |
| **📝 تصحيح ترجمة واحدة** | واجهة فورية مع تحليل مفصل للتصحيحات المطبقة |
| **🗂️ معالجة دفعية** | معالجة آلاف الجمل من Hugging Face Datasets في دقائق |
| **⚙️ قواعس قابلة للتوسع** | 13 قاعدة محددة + 11 نمط regex متقدم (JSON قابل للتعديل) |
| **👁️ معاينة البيانات** | عرض أول 100 صف من أي مجموعة بيانات قبل المعالجة |
| **📊 إحصائيات حية** | تتبع عدد التصحيحات لكل قاعدة وإجمالي الترجمات المحسنة |
| **🤗 تكامل سحابي كامل** | رفع وحفظ النتائج مباشرة إلى Hugging Face Hub |
| **🎨 واجهة احترافية** | 5 تبويبات متكاملة (Gradio 6.0) مع دعم عربي كامل |
| **🔓 مفتوح المصدر** | رخصة MIT – استخدمه، عدّله، وانشره بحرية |

---

## 🎮 جرب الآن

جرب النظام مباشرة:

```bash
# التشغيل المحلي
python app.py
# ثم افتح: http://localhost:7860
```

---

## 📦 التثبيت والتشغيل

### المتطلبات

- **Python 3.9+**
- **Git** (اختياري)

### خطوات التثبيت

```bash
# 1️⃣ استنساخ المستودع
git clone https://github.com/DrAbdulmalek/arabic-translation-unified.git
cd arabic-translation-unified

# 2️⃣ إنشاء البيئة الافتراضية
python -m venv venv

# تفعيل البيئة:
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3️⃣ تثبيت المكتبات
pip install -r requirements.txt

# 4️⃣ تشغيل التطبيق
python app.py
```

**بعد التشغيل:** افتح <http://localhost:7860> في المتصفح

---

## 🏗️ البنية المعمارية

### الملفات الرئيسية

```
arabic-translation-unified/
├── app.py                      # 979 سطر – النظام الكامل
│   ├── TranslationRule         # فئة القاعدة الواحدة
│   ├── ArabicTranslationProcessor  # محرك المعالجة
│   ├── process_dataset()       # معالجة دفعية
│   ├── preview_dataset()       # معاينة البيانات
│   └── create_gradio_interface()  # 5 تبويبات UI
│
├── translation_rules.json      # القواعس (JSON)
├── requirements.txt            # المكتبات
├── .env.example               # مثال البيئة
│
├── README.md                  # هذا الملف
├── DEPLOYMENT_GUIDE.md        # نشر على HF Spaces
├── CONTRIBUTING.md            # دليل المساهمة
├── CHANGELOG.md               # سجل التغييرات
│
├── deploy.py                  # نشر سريع HF Spaces
├── github_deploy.py           # رفع GitHub
│
└── LICENSE                    # رخصة MIT
```

---

## 📚 القواعس اللغوية

### تصنيف القواعس (13 قاعدة رئيسية)

| الفئة | العدد | أمثلة |
|:---:|:---:|:---|
| **Structural** | 2 | `ممنوع التدخين` ← `التدخين ممنوع` |
| **Grammatical** | 5 | حذف "بواسطة"، `التقى بـ` ← `لقي` |
| **Lexical** | 4 | `السيدات والسادة` ← `السادة والسيدات` |
| **Stylistic** | 1 | `لعب دوراً` ← `قام بدور` |
| **Cultural** | 1 | الحساسية الثقافية والدينية |

### أنماط Regex المتقدمة (11 نمط)

- **علامات الترقيم:** الفاصلة العربية `،`، المسافات
- **الأرقام:** حذف المسافات بين الأرقام
- **الحروف الزائدة:** الواو، بـ، وأن
- **تكرار:** حذف الكلمات المكررة
- **المسافات:** تنظيف المسافات الزائدة

---

## 🎯 حالات الاستخدام

### 1️⃣ تصحيح ترجمة واحدة

**التبويب الأول:** `📝 تصحيح ترجمة`

```
الإدخال:
  النص الإنجليزي: "No smoking allowed"
  الترجمة: "ممنوع التدخين مسموح"

الإخراج:
  ✨ المصححة: "التدخين ممنوع"
  📋 التصحيحات: STRUCT_001
  📊 النتيجة: 1 تصحيح تم
```

### 2️⃣ معالجة دفعية من Hub

**التبويب الثاني:** `🗂️ معالجة مجموعة بيانات`

```bash
Dataset ID: "username/my-dataset"
Save Repo: "username/processed"
Batch Size: 64
→ النتائج تُحفظ تلقائياً على Hub
```

### 3️⃣ معاينة البيانات

**التبويب الثالث:** `👁️ معاينة البيانات`

عرض 5-100 صف بدون معالجة:

```bash
Dataset ID: "allenai/wmt14"
Limit: 10
→ جدول مباشر من Hub
```

---

## ⚙️ الإعدادات والبيئة

### ملف `.env`

```bash
# Hugging Face
HF_TOKEN=hf_xxxxxxxxxxxxxx

# اختياري: الخادم
SERVER_HOST=127.0.0.1
SERVER_PORT=7860
```

### الحصول على HF_TOKEN

1. اذهب إلى [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. أنشئ **Write Access Token** جديد
3. انسخه في `.env`

---

## 🚀 النشر على Hugging Face Spaces

### الطريقة السريعة

```bash
python deploy.py
# أدخل HF Token واسم الـ Space
```

### الطريقة اليدوية

1. اذهب إلى [Hugging Face Spaces](https://huggingface.co/spaces)
2. أنشئ Space جديد (Gradio SDK)
3. رفع الملفات:
   - `app.py`
   - `requirements.txt`
   - `translation_rules.json`
   - `.env` (مع HF_TOKEN)
4. سيبدأ التشغيل تلقائياً

---

## 🔧 التخصيص والتطوير

### إضافة قاعدة جديدة

**في `translation_rules.json`:**

```json
{
  "rule_id": "GRAM_006",
  "category": "grammatical",
  "english_pattern": "pattern here",
  "wrong_arabic": "كلمة خطأ",
  "correct_arabic": "كلمة صحيح",
  "rule_description": "الوصف",
  "priority": 1,
  "examples": [
    {
      "en": "example",
      "ar_wrong": "مثال خطأ",
      "ar_correct": "مثال صحيح"
    }
  ]
}
```

ثم أعد التشغيل.

### إضافة نمط Regex

**في الدالة `_compile_regex_patterns()` (السطور 85-119):**

```python
'my_pattern': re.compile(r'your_regex_here'),
```

ثم طبقه في `apply_regex_corrections()`.

---

## 📊 الإحصائيات

### المقاييس المتتبعة

```python
stats = processor.get_statistics()
# {
#   "total_processed": 1000,
#   "total_corrections": 450,
#   "rules_applied": {
#     "STRUCT_001": 120,
#     "GRAM_001": 80,
#     ...
#   }
# }
```

### عرض الإحصائيات

استخدم التبويب `⚙️ إدارة القواعس` → `📊 الإحصائيات`

---

## 🐛 استكشاف الأخطاء

| المشكلة | الحل |
|:---|:---|
| "HF_TOKEN غير موجود" | أضفه في `.env` أو متغيرات البيئة |
| "Column not found" | تحقق من أسماء الأعمدة: `en`, `ar`, `source`, `target` |
| بطء المعالجة | قلل `Batch Size` من الإعدادات |
| "Dataset not found" | تأكد من الوصول إلى المجموعة والتوكن |

---

## 🤝 المساهمة

نرحب بكل المساهمات! اقرأ [CONTRIBUTING.md](CONTRIBUTING.md).

### طرق المساهمة

- إضافة قواعس جديدة
- إصلاح الأخطاء
- تحسين الأداء
- تحسين التوثيق

---

## 📈 خارطة الطريق

| الإصدار | الميزات |
|:---:|:---|
| **2.1** | REST API • Excel Export • 10+ قواعس جديدة |
| **2.2** | CLI • معالجة متوازية • لوحة تحكم متقدمة |
| **3.0** | نموذج DL • تصحيح سياقي • دعم اللهجات |

---

## ⚖️ الترخيص

**MIT License** - مفتوح المصدر للاستخدام التجاري والشخصي.

اقرأ [LICENSE](LICENSE) للتفاصيل.

---

## 👨‍💻 المطور

**د. عبد المالك الحسيني**

- 🏥 اختصاصي جراحة عظمية
- 💻 مطور برامج مفتوح المصدر
- 🌐 متخصص NLP واللغويات

### روابط التواصل

- 🌐 [الموقع الشخصي](https://drabdulmalek.com)
- 🐙 [GitHub](https://github.com/DrAbdulmalek)
- 🤗 [Hugging Face](https://huggingface.co/DrAbdulmalek)
- 𝕏 [X/Twitter](https://twitter.com/DrAbdulmalek)

---

## 📚 المراجع

- [توثيق Gradio](https://gradio.app/docs/)
- [HF Datasets](https://huggingface.co/docs/datasets/)
- [HF Hub API](https://huggingface.co/docs/hub/api)
- [Python Regex](https://docs.python.org/3/library/re.html)

---

<div align="center">

### 💚 مصنوع بـ ❤️ للغة العربية

**v2.0.0 | 9 ديسمبر 2025**

![Stars](https://img.shields.io/github/stars/DrAbdulmalek/arabic-translation-unified?style=social)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**استمتع واساهم في التطوير! 🚀**

</div>
