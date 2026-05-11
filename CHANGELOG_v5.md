# OmniFile AI Processor — Changelog v5.0

## الميزات الجديدة في v5.0

### 🤖 Engine Router (`modules/core/engine_router.py`)
- اختيار ذكي لمحركات OCR بناءً على جودة الصورة + اللغة + نوع الكتلة
- يوفر ~60% من الذاكرة بتشغيل محركين بدلاً من الكل
- بروفايلات: `low` / `balanced` / `high`

### ✏️ Word Trainer (`modules/core/word_trainer.py`)
- قاعدة بيانات SQLite لتصحيحات المستخدم (كلمة + ثقة + لغة + طابع زمني)
- `save_batch()` + `undo_last_batch()` + `delete_correction()`
- `get_best_correction()` — يتعلم ويقترح بعد تصحيحين متكررين
- `update_arabic_fixes()` — يُغني القاموس العربي تلقائياً

### 🔤 HybridSpellChecker (`modules/core/spell_checker.py`)
- **يكتشف اللغة تلقائياً** من النص — لا اختيار يدوي
- مصادر متدرجة: `arabic_fixes.json` → `WordCorrectionDB` → `pyspellchecker`
- يدعم: العربية 🇸🇦 / الإنجليزية 🇬🇧 / الألمانية 🇩🇪 / المختلطة 🌐

### 📝 AppLogger (`modules/core/log_manager.py`)
- سجل محلي يومي في `logs/app_YYYYMMDD.log`
- رفع تلقائي إلى **Private GitHub Gist** (لا يُقرأ إلا بالـ token)
- يُخزَّن `gist_id` محلياً في `logs/.gist_id` (مُستثنى من .gitignore)

### 📦 Corrections Manager (`modules/core/corrections_manager.py`)
- تصدير/استيراد قاموس التصحيحات بين الأجهزة والمستخدمين
- نسخ احتياطية تلقائية قبل كل دمج

### 🖥️ واجهة Word Trainer (`src/correction_trainer_ui.py`)
**تبويبات:**
- **✏️ Word Trainer** — بطاقة تفاعلية لكل كلمة:
  - `Predicted` (OCR) + `Confidence` + `Lang` (تلقائي) + `Correction`
  - [📋 نسخ] [💾 حفظ هذه] [🗑️ حذف] لكل كلمة
  - [← السابق] [التالي →] للتنقل
  - [↩️ تراجع] عن آخر دفعة بالكامل
  - [✨ تصحيح إملائي للكل] يملأ تلقائياً
- **📚 Review DB** — استعراض + حذف + إحصائيات
- **📤 Sync** — رفع GitHub + تحميل JSON للـ Drive

### ⚙️ config.py
- `from_profile("low" | "balanced" | "high")` — إعدادات جاهزة للجهاز
- `auto_profile(ram_gb)` — يختار البروفايل تلقائياً

### 📊 metrics.py
- `compute_cer(ref, hyp)` — دالة مستوى الوحدة
- `compute_wer(ref, hyp)` — دالة مستوى الوحدة
- `quick_grade(ref, hyp)` — تقييم سريع مع درجة

## بنية المشروع v5.0

```
OmniFile_Processor/
├── config.py                    ← إعدادات مركزية + بروفايلات
├── hf_app.py                    ← تطبيق HuggingFace Spaces (1991L)
├── modules/
│   ├── core/
│   │   ├── engine_router.py     ← الموجّه الذكي للمحركات
│   │   ├── word_trainer.py      ← محرك التعلم من التصحيحات
│   │   ├── spell_checker.py     ← المدقق الإملائي الهجين
│   │   ├── log_manager.py       ← مدير السجلات الخاصة
│   │   └── corrections_manager.py
│   ├── vision/                  ← OCR + Layout + Normalize
│   ├── nlp/                     ← Arabic NLP + SpellCorrector + Mixed
│   ├── export/                  ← DOCX + Markdown + Layout-Preserving
│   ├── evaluation/              ← CER/WER + Metrics
│   └── security/                ← Encryption + Audit + PII
├── src/
│   └── correction_trainer_ui.py ← واجهة Word Trainer Gradio
├── notebooks/
│   └── OmniFile_v500_Colab.ipynb ← 59 خلية اختبار شاملة
├── data/
│   └── arabic_fixes.json        ← قاموس إصلاحات OCR العربية
├── artifacts/
│   ├── correction_dict.json     ← قاموس التصحيحات
│   └── corrections_db_export.json
├── logs/                        ← سجلات محلية (.gitignore)
├── requirements.txt
└── requirements-colab.txt       ← حزم Colab المُحسَّنة
```

## استخدام الميزات الجديدة

### HybridSpellChecker
```python
from modules.core.spell_checker import HybridSpellChecker
sc = HybridSpellChecker()

# اكتشاف اللغة تلقائياً
lang = sc.detect_language("مرحبا World")  # "mixed"

# اقتراحات
sugg = sc.get_suggestions("مرحبا", n=5)

# تصحيح تلقائي
corrected, lang = sc.auto_correct("recieve")  # ("receive", "en")
```

### WordCorrectionDB
```python
from modules.core.word_trainer import WordCorrectionDB
db = WordCorrectionDB()

# حفظ دفعة تصحيحات
db.save_batch([
    {"idx":0, "predicted":"مرحبا", "corrected":"مرحباً", "lang":"ar", "confidence":0.72},
])

# تراجع
db.undo_last_batch()

# أفضل تصحيح متعلَّم
best = db.get_best_correction("مرحبا", lang="ar")
```

### AppLogger (سجلات خاصة)
```python
from modules.core.log_manager import AppLogger
log = AppLogger(github_token="ghp_xxx")
log.session_start()
log.log_ocr("EasyOCR", "ar", 12, 1.5)
result = log.push()  # يرفع إلى Private Gist
print(result["url"])  # الرابط الخاص
```

### Engine Router
```python
from modules.core.engine_router import EngineRouter
router = EngineRouter(profile="balanced", use_gpu=True)
engines, reasons = router.select(image_quality=0.85, language="ar", block_type="paragraph")
# engines = ["EasyOCR"]
# reasons = ["Arabic/mixed language (ar)"]
```

---
*OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini | Homs, Syria*
