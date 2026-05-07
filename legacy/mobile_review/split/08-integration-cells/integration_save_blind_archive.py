# integration_save_blind_archive.py
# Smart save + double blind + auto-archive

## 🔗 خلية التكامل الموحدة (Colab-Ready)

```python
# 🔄 تشغيل متكامل: حفظ ذكي + مراجعة مزدوجة + إعادة أرشفة تلقائية
import json, random, os
from pathlib import Path
from core.double_blind_reviewer import DoubleBlindReviewer
from core.quota_manager import ExpertQuotaManager
from core.user_manager import UserManager, UserRole
from train.data_mixing import DataMixingManager
from ui.pwa_generator import generate_pwa_assets

# 1️⃣ تهيئة الأنظمة
reviewer = DoubleBlindReviewer()
quota_mgr = ExpertQuotaManager(weekly_limit=60)
users = UserManager()
users.register_or_get("expert_ali", UserRole.EXPERT)
users.register_or_get("linguist_mona", UserRole.LINGUIST)

mixer = DataMixingManager(
    drift_reset_threshold=0.60,
    consecutive_cycles=3,
    k_steepness=10
)

# 2️⃣ محاكاة إنشاء مهمة مراجعة مزدوجة لوثيقة طبية
task_id = reviewer.create_task("doc_med_042", "blk_101", "الجرعه الموصى بها 500 ملغ يومياً", sensitivity="high")
reviewer.assign_reviewers(task_id, ["expert_ali", "linguist_mona"])

# تقديم مراجعتين متطابقتين تقريباً
reviewer.submit_review(task_id, "expert_ali", "الجرعة الموصى بها: 500 ملغ يومياً")
reviewer.submit_review(task_id, "linguist_mona", "الجرعة الموصى بها: 500 ملغ يومياً")
print(f"🔍 حالة المهمة: {next(t for t in reviewer.registry['tasks'] if t['id']==task_id)['status']}")

# 3️⃣ محاكاة انزياح مستمر وتشغيل إعادة الأرشفة
new_dist = {"medical": 90, "legal": 5, "general": 5}
new_path = "data/medical_v3.json"
Path(new_path).parent.mkdir(exist_ok=True)
Path(new_path).write_text(json.dumps([{"input":"ن","output":"ن"}]*100))

# محاكاة 3 دورات متتالية بانزياح عالي
for i in range(3):
    mixer.compute_drift(new_dist)  # يسجل 0.72 افتراضياً في المحاكاة
    mixer.archive_version(new_path, f"cycle_{i}")

# التحقق من تفعيل إعادة الأرشفة
if mixer._check_drift_history():
    print("✅ تم تفعيل إعادة أرشفة الأساس تلقائياً")

# 4️⃣ توليد أصول PWA (تتضمن smart_save_handler.js تلقائياً إذا أضفته للمجلد)
generate_pwa_assets("pwa_static")
print("📱 PWA جاهزة. افتح الرابط على هاتفك وأضفه للشاشة الرئيسية. التعديلات ستُحفظ تلقائياً عند الإغلاق.")
```

---

> 🤔 **أسئلة سقراطية ختامية للتأمل المعماري:**
> 1. *إذا كان `beforeunload` يمنع الفقد المفاجئ، فهل نخزن المسودات في `sessionStorage` المشفر فقط، أم نضيف نسخة احتياطية مؤقتة في `localStorage` مع تاريخ انتهاء صلاحية (TTL)؟*
>    → *توصية*: استخدم `localStorage` مع `expiry_ms=3600000` (ساعة واحدة) كطبقة أمان ضد انقطاع الشبكة المفاجئ، مع مسح تلقائي بعد الاستعادة.
> 2. *هل عتبة الاتفاق `0.92` في المراجعة المزدوجة صارمة جداً للنصوص العربية المعقدة (اختلاف في التشكيل أو صياغة)؟*
>    → *تحسين*: استبدال المطابقة الحرفية بـ `normalized_similarity` (إزالة تشكيل، توحيد ألف/ياء، تجاهل الفراغات الزائدة) قبل الحساب.
> 3. *إذا أعادت الأرشفة تصفير `versions`، كيف نضمن أن النموذج لا يفقد "الذاكرة طويلة المدى" تماماً؟*
>    → *ضمان*: احتفظ بنسخة `baseline_snapshot.json` تحتوي على عينات تمثيلية (10% من كل نوع) تُخلط بنسبة ثابتة `0.05` في كل دورة، كـ "ذاكرة دائمة" للنموذج.

---
إليك الحزمة المتكاملة والجاهزة للإنتاج، مصممة لتعمل بتناغم مع البنية الحالية، مع ضمان **موثوقية التخزين المحلي**، **دقة المقارنة العربية**، و**ذاكرة طويلة الأمد للنموذج**.

---

