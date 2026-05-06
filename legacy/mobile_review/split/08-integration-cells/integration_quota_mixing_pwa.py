# integration_quota_mixing_pwa.py
# Expert quota + data mixing + PWA

## 🔗 خلية التكامل الشاملة (Colab-Ready)

```python
# 🔄 دمج المكونات الثلاثة في سير عمل واحد متسلسل
import os, json
import asyncio
import nest_asyncio
nest_asyncio.apply()

from ui.review_dashboard import build_review_dashboard
from train.unsloth_pipeline import train_with_unsloth
from core.decay_tracker import DynamicDecayManager
from core.voting_tracker import CorrectionVoter
from models.inference_corrector import ArabicSpellCorrector

# 1️⃣ تهيئة النظام
voter = CorrectionVoter(storage_path="voting_cache.json")
decay_mgr = DynamicDecayManager()
corrector = ArabicSpellCorrector("qwen2.5-0.5b-ar-corrector")

# 2️⃣ واجهة المراجعة التفاعلية (تشغيل مباشر في Colab)
app = build_review_dashboard("voting_cache.json", "qwen2.5-0.5b-ar-corrector")
app.launch(share=True, height=600)  # share=True يعطيك رابطاً عاماً للمراجعة من الموبايل

# 3️⃣ تدريب النموذج (يعمل في الخلفية بعد جمع 50+ تصحيحاً)
if len(voter.export_approved_corrections()) >= 50:
    print("🏋️ بدء تدريب Unsloth على التصحيحات المعتمدة...")
    # تصدير بيانات التدريب أولاً
    from core.training_export import export_instruction_data
    data_path = export_instruction_data("voting_cache.json", "train_data.json", min_samples=50)

    model_path = train_with_unsloth(
        data_path="train_data.json",
        output_dir="qwen2.5-0.5b-unsloth-ar-v2",
        epochs=3
    )
    print(f"✅ اكتمل التدريب وحُفظ في: {model_path}")

# 4️⃣ تحديث اضمحلال الثقة تلقائياً
def update_decay_feedback():
    # محاكاة تغذية راجعة: قارن مخرجات النموذج مع الإجماع البشري
    approved = voter.export_approved_corrections()
    for orig, corr in list(approved.items())[:10]:
        ai_out = corrector.correct(orig)
        decay_mgr.record_ai_feedback(ai_out == corr)

    report = decay_mgr.export_decay_report()
    print("📊 تقرير اضمحلال الثقة الحالي:")
    print(json.dumps(report, ensure_ascii=False, indent=2))

update_decay_feedback()
```

---

