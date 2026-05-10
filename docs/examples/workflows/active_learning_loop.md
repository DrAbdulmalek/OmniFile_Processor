# حلقة التعلم النشط مع التصحيحات

## نظرة عامة

يوضح هذا المثال كيفية بناء حلقة تعلم نشط (Active Learning Loop) حيث يقوم النموذج بتحديد العينات الأكثر فائدة للتصحيح البشري ثم يعاد تدريبه على التصحيحات الجديدة.

## المثال 1: حلقة تعلم نشط كاملة

```python
from interactive_learning import InteractiveLearningSystem
import numpy as np
from PIL import Image

# إنشاء النظام
system = InteractiveLearningSystem(config={
    "model_name": "trocr-base-handwritten",
    "device": "cuda"
})

# الخطوة 1: التعرف على مجموعة صور
images = [Image.open(f) for f in ["page1.png", "page2.png", "page3.png"]]

for img in images:
    result = system.recognize_page(np.array(img))
    print(f"تم التعرف: {result['text'][:50]}... (ثقة: {result['confidence']:.2%})")

# الخطوة 2: تطبيق تصحيحات المستخدم
system.apply_correction(
    word_id="w_001",
    original_text="فم",
    corrected_text="في",
    user_id="reviewer_1",
    image=word_image_1,
    confidence=0.65
)

system.apply_correction(
    word_id="w_002",
    original_text="العلم نور",
    corrected_text="العلم نور والجهل ظلام",
    user_id="reviewer_1",
    image=word_image_2,
    confidence=0.45
)

# الخطوة 3: التدريب على التصحيحات
metrics = system.train_from_corrections(epochs=3, batch_size=4)
print(f"النتيجة: خسارة={metrics['avg_loss']:.4f}, عينات={metrics['num_samples']}")

# الخطوة 4: التحقق من التحسن
result_after = system.recognize_page(np.array(images[0]))
print(f"بعد التدريب: {result_after['confidence']:.2%}")
```

## المثال 2: المراقبة والإحصائيات

```python
stats = system.get_stats()
print(f"التصحيحات المعلقة: {stats['corrections_pending']}")
print(f"حجم الكاش: {stats['learner_cache_size']:.2f} MB")
print(f"سجل التدقيق: {stats['audit_stats']}")
```
