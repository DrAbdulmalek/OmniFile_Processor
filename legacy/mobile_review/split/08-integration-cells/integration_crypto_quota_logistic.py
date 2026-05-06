# integration_crypto_quota_logistic.py
# Session crypto + quota + logistic mixing

## 🔗 خلية التكامل الموحدة (Colab-Ready)

```python
# 🔄 تشغيل متكامل: حصة خبراء + خلط لوجستي + PWA مشفرة
import json, os
from pathlib import Path
from core.quota_manager import ExpertQuotaManager
from core.user_manager import UserManager, UserRole
from train.data_mixing import DataMixingManager
from ui.pwa_generator import generate_pwa_assets

# 1️⃣ تهيئة الأنظمة
quota_mgr = ExpertQuotaManager(weekly_limit=80, blind_sample_rate=0.12)
users = UserManager()
users.register_or_get("expert_ahmed", UserRole.EXPERT)
users.register_or_get("linguist_sara", UserRole.LINGUIST)

# 2️⃣ محاكاة دورة خلط جديدة مع دالة لوجستية
mixer = DataMixingManager(max_ratio=0.30, k_steepness=10, x0_midpoint=0.35)
new_path = "data/cycle_legal_v2.json"
# ... (توليد بيانات جديدة) ...
new_dist = {"paragraph": 60, "table": 25, "caption": 15}

mixed = mixer.mix_iterative(new_path, new_dist)
mixer.save_mixed(mixed, "data/mixed_legal_v2.json")
mixer.archive_version(new_path, "v2_legal")

# 3️⃣ فحص حصة الخبير وتشغيل عينة عمياء
status = quota_mgr.get_quota_status("expert_ahmed")
print(f"📊 حالة الحصة: {status['used']}/{status['limit']} | متبقي: {status['remaining']}")

if status['remaining'] > 0 and random.random() < 0.2:
    sampled = quota_mgr.trigger_blind_review("expert_ahmed")
    print(f"🎲 عينة عمياء مُسحوبة للمراجعة: {len(sampled)} تصحيح")

# 4️⃣ توليد أصول PWA (تتضمن التشفير تلقائياً)
generate_pwa_assets("pwa_static")
print("✅ جاهز للتشغيل. افتح الرابط على هاتفك وأضفه للشاشة الرئيسية.")
```

---

> 🤔 **أسئلة سقراطية ختامية للمراجعة المعمارية:**
> 1. *إذا كان المفتاح المشفر يُولد في `RAM` فقط، ماذا يحدث إذا أعاد المستخدم تحميل الصفحة قبل الحفظ؟*
>    → **حل عملي**: إضافة `beforeunload` في الـ PWA يحفظ حالة التحرير في `localStorage` مشفر بمفتاح مؤقت، مع تنبيه: "سيتم مسح الجلسة عند الإغلاق. احفظ الآن؟"
> 2. *هل العينة العمياء (`blind_sample`) كافية لكشف التحيز المنهجي، أم نحتاج "مراجعة مزدوجة عمياء" (Double-Blind)؟*
>    → **توصية**: للوثائق الحرجة (طبية/قانونية)، فعّل `blind_sample_rate=0.25` وأضف مطابقة تلقائية مع `linguist` ثانٍ. للنصوص العامة، 10-15% كافٍ.
> 3. *هل الدالة اللوجستية `logistic(x)` تمنع تماماً تدهور الأداء إذا كان الانزياح `drift` مستمراً لأشهر؟*
>    → **ضمان**: أضف `drift_reset_threshold=0.6`. إذا تجاوزه الانزياح 3 دورات متتالية، أعد أرشيفة الأساس (`archive_version("baseline_reset")`) لمنع تراكم الديون التقنية في البيانات.

---

> 🤔 *سؤال معماري تمهيدي: كيف نوازن بين "حماية البيانات من الفقد المفاجئ" و"عدم إرباك المستخدم بتنبيهات متكررة" على شاشات الموبايل الصغيرة؟ وكيف نمنع الانحياز التراكمي في الوثائق الحساسة دون إبطاء سير العمل؟ ومتى نقرر أن "الانزياح في البيانات أصبح جديداً بما يكفي ليعتبر أساساً جديداً"؟*

إليك المكونات الثلاثة جاهزة للإنتاج، مصممة لتتكامل بسلاسة مع البنية السابقة، مع ضمان الأمان، الشفافية، والاستقرار الرياضي.

---

