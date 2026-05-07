# integration_roles_pwa_mixing.py
# Roles + PWA + data mixing + Unsloth

## 🔗 خلية تكامل شاملة لـ Colab (جاهزة للنسخ والتشغيل)

```python
# 🔄 تشغيل متكامل: أدوار + PWA + خلط بيانات + تدريب Unsloth
import json, os
from pathlib import Path
from core.user_manager import UserManager, UserRole
from train.data_mixing import DataMixingManager
from ui.pwa_generator import generate_pwa_assets
from train.unsloth_pipeline import train_with_unsloth
from ui.gradio_pwa_wrapper import launch_pwa_dashboard

# 1️⃣ تهيئة الأرشيف والأدوار
mixer = DataMixingManager("data_archive")
users = UserManager("users_registry.json")
users.register_or_get("dev_001", UserRole.LINGUIST)
users.register_or_get("mobile_user_01", UserRole.EXPERT)

# 2️⃣ توليد أصول PWA
generate_pwa_assets("pwa_static")

# 3️⃣ محاكاة دورة بيانات جديدة وخلطها تلقائياً
new_path = "data/new_cycle_v3.json"
new_data = [{"input": "النص الجديد", "output": "المصحح", "block_type": "paragraph"} for _ in range(50)]
Path(new_path).write_text(json.dumps(new_data, ensure_ascii=False, indent=2))
new_dist = {"paragraph": 40, "caption": 10}

mixed_data = mixer.mix_iterative(new_path, new_dist)
mixer.save_mixed(mixed_data, "data/mixed_for_training.json")

# 4️⃣ أرشفة الدورة الحالية قبل التدريب
mixer.archive_version(new_path, "v3_raw")

# 5️⃣ تدريب Unsloth على البيانات المخلوطة (يمنع النسيان الكارثي تلقائياً)
if len(mixed_data) >= 30:
    print("🏋️ بدء تدريب Unsloth على بيانات مخلوطة...")
    train_with_unsloth("data/mixed_for_training.json", output_dir="qwen2.5-0.5b-unsloth-v4")

# 6️⃣ إطلاق واجهة المراجعة كـ PWA
def run_pwa():
    from ui.review_dashboard import build_review_dashboard
    launch_pwa_dashboard(build_review_dashboard, share=True)

# run_pwa()  # فعّل هذا السطر عند الرغبة في تشغيل الواجهة
```

---

> 🤔 *أسئلة تأملية معمارية قبل النشر:*
> 1. إذا كان `expert_flag` يرفع وزن التصويت بنسبة 25%، فكيف نمنع "تضخم السلطة" عندما يوافق خبير على خطأ متكرر؟
>    → *حل مقترح*: إضافة `expert_review_quota` أسبوعي، ومطابقة تصحيحاته مع عينة عشوائية يختارها مدقق لغوي ثانٍ.
> 2. هل خدمة الـ `Service Worker` تخزن نصوصاً حساسة على جهاز المراجع؟
>    → *ضمان أمان*: الـ SW يخزن فقط الأصول الثابتة (HTML/CSS/JS/Icons). النصوص تبقى في `sessionStorage` وتُحذف عند إغلاق التبويب.
> 3. إذا كان الانزياح `drift` كبيراً فجأة (مثلاً: إضافة وثائق قانونية بعد طبية)، هل النسبة 35% كافية؟
>    → *تحسين ديناميكي*: استبدال `drift * 1.5` بدالة `logistic(x)` تحد من القفزات المفاجئة وتضمن استقرار التدريب.

---
إليك الحزمة المتكاملة والجاهزة للإنتاج، مصممة لتعمل بتناغم مع البنية الحالية، مع ضمان الشفافية، الأمان، والاستقرار الرياضي في التدريب.

---

