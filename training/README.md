# 🏋️ دليل التدريب الكامل | Training Guide

## 📋 جدول المحتويات
1. [نظرة عامة](#نظرة-عامة)
2. [متطلبات النظام](#متطلبات-النظام)
3. [إعداد بيانات التدريب](#إعداد-بيانات-التدريب)
4. [التدريب باستخدام LoRA](#التدريب-باستخدام-lora)
5. [التدريب من الصفر](#التدريب-من-الصفر)
6. [التعلم النشط (Active Learning)](#التعلم-النشط)
7. [تقييم النموذج](#تقييم-النموذج)
8. [استكشاف الأخطاء](#استكشاف-الأخطاء)

---

## نظرة عامة

يوفر هذا الدليل خطوات تدريب نماذج التعرف على النصوص اليدوية (HTR) والمطبوعة (OCR) 
باستخدام OmniFile Processor.

### النماذج المدعومة

| النموذج | الاستخدام | VRAM المطلوب | الأولوية |
|---------|-----------|-------------|----------|
| **TrOCR-Large-Handwritten** | خط يدوي عام | 8-16 GB | ⭐⭐⭐⭐⭐ |
| **TrOCR-Base-Handwritten** | خط يدوي سريع | 4-8 GB | ⭐⭐⭐⭐☆ |
| **TrOCR-Base-Printed** | مطبوع | 4-8 GB | ⭐⭐⭐☆☆ |
| **PARSeq** | Scene Text | 6-12 GB | ⭐⭐⭐⭐☆ |
| **Qwen2.5-VL-3B (4-bit)** | عربي يدوي | 6-10 GB | ⭐⭐⭐⭐⭐ |
| **PaddleOCR Arabic v5** | عربي مطبوع | 2-4 GB | ⭐⭐⭐☆☆ |

---

## متطلبات النظام

### الحد الأدنى
```bash
# CPU: 4 أنوية
# RAM: 16 GB
# GPU: اختياري (CPU training بطيء جداً)
# Disk: 50 GB
```

الموصى به للتدريب

```bash
# CPU: 8+ أنوية
# RAM: 32+ GB
# GPU: NVIDIA RTX 3090 / A100 / H100 (24+ GB VRAM)
# Disk: 100+ GB SSD
```

التثبيت

```bash
# 1. التثبيت الأساسي
pip install -e ".[training]"

# 2. أو تثبيت يدوي
pip install transformers>=4.40.0 accelerate peft bitsandbytes
pip install datasets wandb tensorboard
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 3. للتدريب السريع (اختياري)
pip install unsloth  # تسريع 2-5x
pip install flash-attn --no-build-isolation  # فلاش أتنشن
```

---

إعداد بيانات التدريب

📁 هياكل البيانات المدعومة

1. صور منفصلة + ملف نصي (الأسهل)

```
dataset/
├── images/
│   ├── img_001.jpg
│   ├── img_002.png
│   └── ...
└── labels.txt  # صورة_001.jpg \t النص
```

2. تنسيق LMDB (الأسرع للتدريب)

```
dataset.lmdb/
├── data.mdb
└── lock.mdb
```

3. تنسيق HuggingFace Dataset

```python
from datasets import Dataset

dataset = Dataset.from_dict({
    "image": [PIL.Image, ...],
    "text": ["السلام عليكم", ...]
})
```

4. تصدير mobile_review

```bash
python -m mobile_review.server --export-dataset --export-output ./review_dataset
```

---

🛠️ إعداد البيانات

من صور منفصلة

```bash
python training/scripts/prepare_htr_dataset.py \
    --input-dir ./raw_images \
    --labels ./labels.txt \
    --output-dir ./dataset_prepared \
    --format lmdb \
    --train-split 0.8 \
    --val-split 0.1 \
    --test-split 0.1
```

من PDF مع نصوص

```bash
python training/scripts/prepare_htr_dataset.py \
    --pdf ./document.pdf \
    --output-dir ./dataset_from_pdf \
    --dpi 300 \
    --lang ar
```

من mobile_review

```bash
python training/scripts/prepare_htr_dataset.py \
    --mobile-review ./mobile_review/ocr_corrected.json \
    --output-dir ./dataset_reviewed \
    --min-confidence 0.7 \
    --auto-include-high-confidence
```

توليد بيانات صناعية

```bash
python training/scripts/generate_synthetic_data.py \
    --corpus ./corpus_arabic.txt \
    --fonts-dir ./fonts/arabic/ \
    --output-dir ./synthetic_dataset \
    --num-samples 100000 \
    --augmentations all \
    --lang ar
```

---

التدريب باستخدام LoRA

⚡ لماذا LoRA؟

        التدريب الكامل  LoRA    
VRAM    16-24 GB        4-8 GB  
وقت التدريب     10 ساعات        2-4 ساعات       
حجم Checkpoint  1.5 GB  10-50 MB        
الدقة   100%    95-99%  
التبديل بين النماذج     بطيء    فوري    

🚀 تدريب TrOCR مع LoRA

```bash
# تدريب سريع (الافتراضي)
python training/scripts/train_trocr_lora.py \
    --model-name microsoft/trocr-large-handwritten \
    --dataset ./dataset_prepared \
    --output-dir ./checkpoints/trocr_arabic_lora \
    --lang ar \
    --epochs 10 \
    --batch-size 4 \
    --lora-r 16 \
    --lora-alpha 32

# تدريب عالي الجودة
python training/scripts/train_trocr_lora.py \
    --model-name microsoft/trocr-large-handwritten \
    --dataset ./dataset_prepared \
    --output-dir ./checkpoints/trocr_arabic_lora_v2 \
    --lang ar \
    --epochs 20 \
    --batch-size 2 \
    --gradient-accumulation 8 \
    --lora-r 32 \
    --lora-alpha 64 \
    --learning-rate 1e-4 \
    --warmup-steps 500
```

🧠 تدريب Qwen2.5-VL للعربي (الأحدث)

```bash
python training/scripts/train_qwen_vl.py \
    --model-name Qwen/Qwen2.5-VL-3B-Instruct \
    --dataset ./dataset_prepared \
    --output-dir ./checkpoints/qwen_arabic_ocr \
    --load-in-4bit \
    --epochs 5 \
    --batch-size 1 \
    --gradient-accumulation 16
```

---

التدريب من الصفر

⚠️ تحذير: يتطلب بيانات ضخمة (1M+ صورة)

```bash
python training/scripts/train_from_scratch.py \
    --config training/configs/crnn_from_scratch.yaml \
    --dataset ./massive_dataset \
    --output-dir ./checkpoints/crnn_custom
```

---

التعلم النشط (Active Learning)

الدورة الكاملة

```bash
# 1. بدء دورة Active Learning
python training/scripts/active_learning_pipeline.py \
    --model ./checkpoints/trocr_arabic_lora \
    --unlabeled-pool ./unlabeled_images \
    --output-dir ./active_learning_run \
    --strategy uncertainty \
    --samples-per-iteration 100 \
    --max-iterations 10

# 2. إرسال للمراجعة البشرية
python training/scripts/active_learning_pipeline.py \
    --send-for-review \
    --reviewer-url http://mobile-review-server:5000

# 3. إعادة التدريب بعد المراجعة
python training/scripts/active_learning_pipeline.py \
    --retrain \
    --new-data ./reviewed_corrections.json
```

---

تقييم النموذج

```bash
# تقييم أساسي
python training/scripts/evaluate_checkpoint.py \
    --checkpoint ./checkpoints/trocr_arabic_lora \
    --test-dataset ./dataset_prepared/test \
    --metrics cer wer accuracy

# تقييم مفصل مع تصدير الأخطاء
python training/scripts/evaluate_checkpoint.py \
    --checkpoint ./checkpoints/trocr_arabic_lora \
    --test-dataset ./dataset_prepared/test \
    --metrics all \
    --export-errors ./error_analysis.json \
    --visualize
```

---

استكشاف الأخطاء

مشكلة: نفاد VRAM

```bash
# الحل 1: تقليل batch size
--batch-size 1 --gradient-accumulation 16

# الحل 2: تفعيل gradient checkpointing
--gradient-checkpointing

# الحل 3: استخدام 4-bit quantization
--load-in-4bit

# الحل 4: تقليل دقة الصور
--max-image-size 384
```

مشكلة: CER مرتفع (>20%)

```bash
# الحل 1: زيادة البيانات
--epochs 20 --augmentation aggressive

# الحل 2: تعديل learning rate
--learning-rate 5e-5 --warmup-steps 1000

# الحل 3: فك تجميد المزيد من الطبقات
--unfreeze-encoder-layers 6

# الحل 4: فحص جودة البيانات
python training/scripts/analyze_dataset.py --dataset ./dataset_prepared
```

مشكلة: النموذج لا يتعرف على العربي

```bash
# تأكد من:
# 1. tokenizer يدعم العربي
python -c "from transformers import TrOCRProcessor; p = TrOCRProcessor.from_pretrained('microsoft/trocr-large-handwritten'); print('Arabic chars:', any('\u0600' <= c <= '\u06FF' for c in p.tokenizer.get_vocab()))"

# 2. إضافة أحرف عربية للـ vocabulary
python training/scripts/extend_vocabulary.py \
    --model ./checkpoints/trocr_arabic_lora \
    --chars "ابتثجحخدذرزسشصضطظعغفقكلمنهوي ءآأؤإئةى"
```

---

📚 مراجع إضافية

- [TrOCR Paper](https://arxiv.org/abs/2109.10282)
- [PARSeq Paper](https://arxiv.org/abs/2207.06966)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)
- [Qwen2.5-VL Documentation](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct)
- [KHATT Dataset](https://khatt.ideas2serve.net/)
- [SynthDoG-RTL](https://github.com/aiviewz/Synthdog-RTL)

---

💬 دعم

- GitHub Issues: [OmniFile_Processor/issues](https://github.com/DrAbdulmalek/OmniFile_Processor/issues)
- HuggingFace Discussions: [DrAbdulmalek](https://huggingface.co/DrAbdulmalek)
