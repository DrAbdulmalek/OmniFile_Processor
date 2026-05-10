# ضبط دقيق لـ TrOCR على بيانات عربية

## نظرة عامة

يوضح هذا المثال كيفية ضبط نموذج TrOCR (Transformer-based OCR) على بيانات خط يدوي عربية مخصصة باستخدام تقنية LoRA (Low-Rank Adaptation). يتيح لك ذلك تحسين دقة التعرف على الخط اليدوي العربي بشكل كبير مع استخدام موارد حوسبية قليلة.

## المتطلبات

```bash
pip install -r requirements-core.txt -r requirements-ocr.txt -r requirements-training.txt
```

## المثال 1: توليد بيانات تدريب صناعية

```bash
# توليد 5000 صورة عربية يدوية صناعية للتدريب الأولي
python scripts/generate_arabic_htr_dataset.py \
    --output-dir ./data/arabic_htr_synthetic \
    --num-samples 5000 \
    --train-split 0.8 \
    --val-split 0.1 \
    --test-split 0.1
```

## المثال 2: إعداد البيانات للتدريب

```bash
# تحويل الصور والتصنيفات إلى صيغة LMDB
python training/scripts/prepare_htr_dataset.py \
    --input-dir ./data/arabic_htr_synthetic/train/images \
    --labels ./data/arabic_htr_synthetic/train/labels.txt \
    --output-dir ./dataset_prepared \
    --format lmdb
```

## المثال 3: تدريب LoRA

```bash
# تدريب أولي سريع (5 حقب، دفعة 4)
python training/scripts/train_trocr_lora.py \
    --config training/configs/trocr_lora_arabic.yaml \
    --dataset ./dataset_prepared \
    --epochs 10 \
    --batch-size 4 \
    --output-dir ./checkpoints/arabic_htr_v1
```

## المثال 4: التقييم

```python
from training.scripts.evaluate_checkpoint import evaluate

metrics = evaluate(
    checkpoint="./checkpoints/arabic_htr_v1/final",
    test_dataset="./dataset_prepared/test.lmdb"
)

print(f"CER (معدل الخطأ في الحروف): {metrics['cer']:.4f}")
print(f"WER (معدل الخطأ في الكلمات): {metrics['wer']:.4f}")
print(f"Accuracy (الدقة): {metrics['accuracy']:.4f}")
```

## المثال 5: التعلم النشط (Active Learning)

```python
from training.scripts.active_learning_pipeline import ActiveLearningPipeline

pipeline = ActiveLearningPipeline(
    model_path="./checkpoints/arabic_htr_v1/final",
    strategy="uncertainty",  # اختيار العينات الأكثر غموضاً
    num_samples=100
)

# اختيار العينات التي يحتاجها النموذج أكثر
samples = pipeline.select_samples(unlabeled_pool="./data/unlabeled/")

# بعد التصحيح اليدوي
pipeline.add_corrected_samples(samples, corrected_dir="./data/corrected/")

# إعادة التدريب مع العينات الجديدة
pipeline.retrain(output_dir="./checkpoints/arabic_htr_v2")
```

## المتطلبات Hardware

| المكون | الحد الأدنى | الموصى به |
|--------|------------|----------|
| VRAM | 4 GB | 8 GB+ |
| RAM | 8 GB | 16 GB+ |
| القرص | 10 GB | 20 GB+ |

## ملاحظات

- استخدم LoRA لتقليل استهلاك VRAM من 16GB إلى 4GB
- ابدأ بـ 1000-5000 صورة صناعية ثم أضف بيانات حقيقية
- Active Learning يقلل عدد العينات المطلوبة بنسبة 50-70%
