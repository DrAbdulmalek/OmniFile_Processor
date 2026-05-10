# دليل التدريب الشامل — OmniFile Processor

## فهرس المحتويات

1. [مقدمة](#مقدمة)
2. [الإعداد الأولي](#الإعداد-الأولي)
3. [إعداد البيانات](#إعداد-البيانات)
4. [التدريب الأساسي](#التدريب-الأساسي)
5. [التدريب المتقدم](#التدريب-المتقدم)
6. [التعلم النشط (Active Learning)](#التعلم-النشط-active-learning)
7. [التقييم](#التقييم)
8. [نشر النموذج](#نشر-النموذج)
9. [استكشاف الأخطاء وإصلاحها](#استكشاف-الأخطاء-وإصلاحها)

---

## مقدمة

### ما هو HTR؟
**التعرف على الخطوط اليدوية (Handwritten Text Recognition - HTR)** هو فرع من معالجة الصور واللغة الطبيعية يهدف إلى تحويل الصور المكتوبة بخط اليد إلى نصوص رقمية. يختلف HTR عن OCR التقليدي بأنه يتعامل مع التنوع الكبير في أشكال الحروف اليدوية.

### OmniFile Processor HTR
نظامنا يدعم التعرف على الخطوط العربية اليدوية مع:
- **تقسيم الأسطر والكلمات**: خوارزميات متقدمة للتعامل مع النصوص متعددة الأسطر
- **استعادة النقاط**: تصحيح النقاط والحركات العربية المفقودة
- **تدريب مخصص**: إمكانية ضبط النموذج على خطوط يدوية محددة
- **التعلم النشط**: تحسين مستمر من خلال مراجعات المستخدمين

---

## الإعداد الأولي

### المتطلبات النظامية

#### الحد الأدنى
| المكون | المواصفة |
|--------|----------|
| المعالج | 4 أنوية |
| الذاكرة RAM | 16 جيجابايت |
| بطاقة الرسوميات | NVIDIA GPU بـ 8 جيجابايت VRAM (مثل GTX 1070) |
| مساحة التخزين | 50 جيجابايت |
| نظام التشغيل | Ubuntu 22.04 / Windows 11 / macOS 13+ |

#### الموصى بها
| المكون | المواصفة |
|--------|----------|
| المعالج | 8 أنوية أو أكثر |
| الذاكرة RAM | 32 جيجابايت |
| بطاقة الرسوميات | NVIDIA RTX 3090 / 4090 (24 جيجابايت VRAM) |
| مساحة التخزين | 100 جيجابايت SSD |
| نظام التشغيل | Ubuntu 22.04 LTS |

#### المثالية (للتدريب الكامل)
| المكون | المواصفة |
|--------|----------|
| المعالج | 16 نواة أو أكثر |
| الذاكرة RAM | 64 جيجابايت |
| بطاقة الرسوميات | NVIDIA A100 80GB (أو عدة بطاقات) |
| مساحة التخزين | 500 جيجابايت NVMe SSD |
| نظام التشغيل | Ubuntu 22.04 LTS |

### التثبيت

#### التثبيت المحلي (Linux/macOS)

```bash
# 1. استنساخ المشروع
git clone https://github.com/your-org/OmniFile_Processor.git
cd OmniFile_Processor

# 2. إنشاء بيئة افتراضية
python3.10 -m venv venv
source venv/bin/activate

# 3. تثبيت المتطلبات الأساسية
pip install -r requirements.txt

# 4. تثبيت متطلبات التدريب
pip install -r requirements-training.txt

# 5. التحقق من التثبيت
make info
```

#### التثبيت عبر Docker

```bash
# 1. بناء صورة التدريب
make docker-build-training

# 2. تشغيل حاوية التدريب
docker run --gpus all -it --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/checkpoints:/app/checkpoints \
  omnifile-train bash

# 3. داخل الحاوية، تحقق من البيئة
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

#### التثبيت على Google Colab

```python
# 1. استنساخ المشروع
!git clone https://github.com/your-org/OmniFile_Processor.git
%cd OmniFile_Processor

# 2. تثبيت المتطلبات
!pip install -r requirements-training.txt -q

# 3. التحقق من GPU
import torch
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB")
```

---

## إعداد البيانات

### الصيغ المدعومة

| الصيغة | الوصف | مثال |
|--------|-------|------|
| **ImageFolder** | مجلد صور + ملف تصنيفات | `data/images/` + `labels.txt` |
| **OCR Dataset** | تنسيق HuggingFace datasets | `dataset/` مع `metadata.json` |
| **Khodok/SynthText** | تنسيق مجموعات البيانات العربية | ملفات `.lmdb` أو `.hdf5` |
| **PDF + Ground Truth** | مستندات PDF مع نصوص مرجعية | `data/pdfs/` + `data/gt/` |

### إعداد البيانات من صور فردية

```bash
# هيكل المجلد المطلوب:
# data/
# ├── images/
# │   ├── page_001.png
# │   ├── page_002.png
# │   └── ...
# └── labels.txt    # Tab-separated: filename\ttext

# إنشاء labels.txt
python tools/build_training_data.py \
  --input-dir data/raw \
  --output-dir data/processed \
  --format imagefolder
```

### إعداد البيانات من ملفات PDF

```bash
# تحويل PDF إلى صور قطاعية مع نصوص مرجعية
python tools/build_training_data.py \
  --input-dir data/pdfs \
  --gt-dir data/gt \
  --output-dir data/processed \
  --format imagefolder \
  --segment-lines
```

### توليد بيانات اصطناعية

```bash
# إنشاء صور نصية عربية اصطناعية للتدريب الأولي
make synthetic-data

# أو يدوياً:
python training/generate_synthetic.py \
  --output-dir data/synthetic \
  --num-samples 5000 \
  --fonts-dir data/fonts \
  --augmentation
```

### تحضير بيانات المراجعات المحمولة

```bash
# تصدير مراجعات المستخدمين كبيانات تدريب
make prepare-data-mobile
```

### التحقق من البيانات

```bash
# فحص صحة البيانات قبل التدريب
python -c "
from training.data_loader import ImageFolderLoader
loader = ImageFolderLoader('data/processed/images', 'data/processed/labels.txt')
data = loader.load()
errors = loader.validate()
print(f'Total samples: {len(data)}')
print(f'Errors: {len(errors)}')
for err in errors[:10]:
    print(f'  - {err}')
"
```

---

## التدريب الأساسي

### اختبار سريع (1 حقبة)

```bash
# تدريب سريع للتحقق من أن كل شيء يعمل
make train-lora-fast

# أو يدوياً:
python training/train_lora.py \
  --data-dir data/processed \
  --output-dir checkpoints/test-run \
  --epochs 1 \
  --batch-size 2 \
  --max-samples 100
```

### التدريب الكامل

```bash
# تدريب LoRA كامل (موصى به للبدء)
make train-lora

# أو مع معلمات مخصصة:
python training/train_lora.py \
  --data-dir data/processed \
  --output-dir checkpoints/my-model \
  --epochs 10 \
  --batch-size 8 \
  --lr 5e-4 \
  --lora-r 8 \
  --lora-alpha 16 \
  --warmup-steps 500 \
  --fp16
```

### مراقبة التدريب

#### باستخدام TensorBoard

```bash
# تشغيل TensorBoard
tensorboard --logdir logs/

# أو عبر Makefile
python training/train_lora.py --log-to tensorboard
tensorboard --logdir checkpoints/my-model/logs/
```

ثم افتح `http://localhost:6006` في المتصفح.

#### باستخدام Weights & Biases (WandB)

```bash
# تسجيل الدخول
wandb login

# تشغيل التدريب مع WandB
python training/train_lora.py \
  --log-to wandb \
  --wandb-project omnifile-htr \
  --wandb-entity your-team
```

### التوقف المبكر (Early Stopping)

```bash
python training/train_lora.py \
  --early-stopping \
  --early-stopping-patience 3 \
  --early-stopping-metric cer \
  --early-stopping-direction minimize
```

المعلمات:
- `--early-stopping-patience`: عدد الحقب بدون تحسن قبل التوقف (الافتراضي: 3)
- `--early-stopping-metric`: المقياس المراقب (`cer` أو `wer` أو `loss`)
- `--early-stopping-direction`: `minimize` لـ CER/WER، `maximize` للدقة

---

## التدريب المتقدم

### تسريع التدريب مع Unsloth

```bash
# تثبيت Unsloth
pip install unsloth

# تدريب مع Unsloth (أسرع 2x)
python training/train_lora.py \
  --accelerator unsloth \
  --data-dir data/processed \
  --output-dir checkpoints/unsloth-model \
  --epochs 10
```

> **ملاحظة**: Unsloth يدعم حالياً نماذج محددة. راجع [توثيق Unsloth](https://github.com/unslothai/unsloth) للتفاصيل.

### التدريب على عدة بطاقات رسوميات

```bash
# باستخدام accelerate
accelerate launch training/train_lora.py \
  --data-dir data/processed \
  --output-dir checkpoints/multi-gpu \
  --epochs 10 \
  --batch-size 16

# مع ملف إعدادات مخصص
accelerate launch \
  --config_file accelerate_config.yaml \
  training/train_lora.py \
  --epochs 10
```

ملف `accelerate_config.yaml` مثالي:
```yaml
compute_environment: LOCAL_MACHINE
distributed_type: MULTI_GPU
num_machines: 1
num_processes: 4  # عدد GPUs
mixed_precision: fp16
```

### تدريب Qwen2.5-VL (نموذج بصري-لغوي)

```bash
# تدريب Qwen2.5-VL للتعرف على المستندات العربية
make train-qwen

# أو يدوياً:
python training/train_qwen.py \
  --data-dir data/processed \
  --output-dir checkpoints/qwen-vl \
  --epochs 5 \
  --batch-size 4 \
  --lr 2e-5 \
  --max-length 512
```

#### مزايا Qwen2.5-VL:
- فهم أعمق لسياق الصفحة
- تعامل أفضل مع التخطيطات المعقدة
- دعم اللغات متعدد الاتجاهات (RTL)
- قدرة على فهم الجداول والرسوم

### استئناف التدريب

```bash
# استئناف من آخر نقطة حفظ
python training/train_lora.py \
  --resume-from checkpoints/my-model/checkpoint-last \
  --output-dir checkpoints/my-model \
  --epochs 15  # زيادة عدد الحقب
```

---

## التعلم النشط (Active Learning)

### المفهوم
التعلم النشط هو دورة iterective حيث:
1. **التدريب**: تدريب النموذج على البيانات المتاحة
2. **التنبؤ**: تطبيق النموذج على بيانات جديدة غير موسومة
3. **الاختيار**: اختيار العينات التي يحتارها النموذج أكثر (أعلى عدم يقين)
4. **المراجعة**: عرض العينات المختارة للمراجع البشري
5. **الإضافة**: إضافة المراجعات للبيانات وإعادة التدريب

### بدء دورة تعلم نشط

```bash
# بدء دورة تعلم نشط كاملة
make active-learning

# أو يدوياً مع معلمات محددة:
python -m modules.ai.active_learning \
  --cycle-id cycle-001 \
  --checkpoint checkpoints/my-model/best \
  --data-dir data/unlabeled \
  --strategy uncertainty \
  --num-samples 50 \
  --review-tool mobile
```

### مقارنة استراتيجيات الاختيار

| الاستراتيجية | الوصف | الأفضل لـ |
|-------------|-------|----------|
| `uncertainty` | أعلى تباين في التنبؤات | تحسين الدقة العامة |
| `margin` | أقل فرق بين أعلى توقعين | تحسين التصنيف |
| `entropy` | أعلى إنتروبيا التوزيع | تحسين التغطية |
| `diversity` | تنوع العينات المختارة | تغطية أنماط جديدة |
| `hard-examples` | أعلى خطأ (CER) | تحسين الحالات الصعبة |

```bash
# مثال: استراتيجية التنوع
python -m modules.ai.active_learning \
  --strategy diversity \
  --num-samples 100 \
  --embedding-model all-MiniLM-L6-v2
```

### تكامل مع نظام المراجعة المحمولة

```bash
# بدء دورة مع إرسال العينات لتطبيق المراجعة المحمولة
python -m modules.ai.active_learning \
  --cycle-id mobile-review-cycle \
  --strategy uncertainty \
  --num-samples 30 \
  --review-tool mobile \
  --mobile-server-port 5001

# بعد اكتمال المراجعات:
python -m modules.ai.active_learning \
  --collect-reviews \
  --review-server http://localhost:5001 \
  --output data/new-corrections.json
```

---

## التقييم

### التقييم الأساسي

```bash
# تقييم النموذج
make evaluate

# أو يدوياً:
python -m src.metrics \
  --checkpoint checkpoints/my-model/best \
  --data-dir data/test \
  --output results/evaluation.json
```

### التقييم المفصل مع التصور

```bash
# تقييم مفصل مع صور توضيحية
make evaluate-visualize

# النتائج ستكون في:
# results/
# ├── evaluation.json      # مقاييس CER/WER
# └── visualizations/      # صور مقارنة
#     ├── page_001.png
#     ├── page_002.png
#     └── ...
```

### فهم مقاييس CER و WER

#### معدل خطأ الأحرف (CER - Character Error Rate)

```
CER = (S + D + I) / N

حيث:
S = عدد الاستبدالات (Substitutions)
D = عدد الحذوفات (Deletions)
I = عدد الإضافات (Insertions)
N = إجمالي عدد الأحرف في النص المرجعي
```

**مثال:**
```
النص المرجعي:    "بسم الله الرحمن الرحيم"
النص المتوقع:    "بسم ا لله الرحمن الرحيم"
CER = 0 + 1 + 1 / 19 = 10.5%
```

#### معدل خطأ الكلمات (WER - Word Error Rate)

```
WER = (S + D + I) / W

حيث:
S = عدد استبدالات الكلمات
D = عدد حذوفات الكلمات
I = عدد إضافات الكلمات
W = إجمالي عدد الكلمات في النص المرجعي
```

### المستهدفات الموصى بها

| المقياس | مقبول | جيد | ممتاز |
|--------|--------|-----|-------|
| CER | < 15% | < 8% | < 3% |
| WER | < 30% | < 15% | < 5% |

### تحليل الأخطاء

```bash
# تحليل مفصل للأخطاء
python -m src.metrics \
  --checkpoint checkpoints/my-model/best \
  --data-dir data/test \
  --error-analysis \
  --output results/error_analysis.json

# النتيجة ستشمل:
# - أكثر الأخطاء شيوعاً (حروف/كلمات)
# - توزيع الأخطاء حسب النوع (استبدال/حذف/إضافة)
# - أمثلة على الحالات الصعبة
```

---

## نشر النموذج

### تصدير ONNX

```bash
# تصدير النموذج لصيغة ONNX
python src/export.py \
  --checkpoint checkpoints/my-model/best \
  --format onnx \
  --output exports/onnx-model

# تصدير مع تحسينات الأداء
python src/export.py \
  --checkpoint checkpoints/my-model/best \
  --format onnx \
  --optimize \
  --quantize \
  --output exports/onnx-optimized
```

### دمج أوزان LoRA

```bash
# دمج أوزان LoRA مع النموذج الأساسي
python src/export.py \
  --checkpoint checkpoints/my-model/best \
  --format merged \
  --output exports/merged-model

# النتيجة: نموذج كامل قابل للاستخدام بدون PEFT
```

### رفع إلى HuggingFace Hub

```bash
# تسجيل الدخول
huggingface-cli login

# رفع النموذج
python src/export.py \
  --checkpoint checkpoints/my-model/best \
  --format merged \
  --push-to-hub \
  --repo-id your-username/omnifile-arabic-htr \
  --commit-message "Initial trained model"

# أو رفع مباشرة مع LoRA
python -c "
from huggingface_hub import HfApi
api = HfApi()
api.upload_folder(
    folder_path='checkpoints/my-model/best',
    repo_id='your-username/omnifile-arabic-htr-lora',
    commit_message='Upload LoRA adapter'
)
"
```

### استخدام النموذج المنشور

```python
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# تحميل النموذج المنشور
processor = TrOCRProcessor.from_pretrained("your-username/omnifile-arabic-htr")
model = VisionEncoderDecoderModel.from_pretrained("your-username/omnifile-arabic-htr")

# التعرف على صورة
from PIL import Image
image = Image.open("handwritten_page.png")
pixel_values = processor(image, return_tensors="pt").pixel_values
generated_ids = model.generate(pixel_values)
text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
print(text)
```

---

## استكشاف الأخطاء وإصلاحها

### مشاكل VRAM (نفاد ذاكرة بطاقة الرسوميات)

**الأعراض**: `CUDA out of memory` أثناء التدريب

**الحلول**:
```bash
# 1. تقليل حجم الدفعة
--batch-size 2  # بدلاً من 8

# 2. تفعيل تجميع التدرجات
--gradient-accumulation-steps 4  # فعلياً batch_size=8

# 3. استخدام quantization (4-bit)
--load-in-4bit

# 4. تقليل أبعاد LoRA
--lora-r 4  # بدلاً من 8

# 5. تفعيل fp16 (توفير ~50% VRAM)
--fp16

# 6. تقليل طول التسلسل
--max-length 64  # بدلاً من 128
```

**التحقق من استخدام VRAM**:
```bash
watch -n 1 nvidia-smi
```

### معدل CER مرتفع

**الأسباب المحتملة والحلول**:

| السبب | الحل |
|-------|------|
| بيانات تدريب قليلة | زيادة البيانات (≥ 1000 عينة)، أو استخدام augmentation |
| بيانات غير متوازنة | استخدام `data_mixing` لخلط مصادر مختلفة |
| معدل تعلم خاطئ | تقليل LR إلى `1e-5` أو زيادته إلى `1e-3` |
| overfitting | تقليل epochs، إضافة dropout، أو زيادة البيانات |
| نص مرجعي غير دقيق | مراجعة وتصحيح labels.txt |

```bash
# فحص overfitting: مقارنة CER على التدريب والتحقق
python -m src.metrics \
  --checkpoint checkpoints/my-model/best \
  --data-dir data/train \
  --output results/train_eval.json

python -m src.metrics \
  --checkpoint checkpoints/my-model/best \
  --data-dir data/test \
  --output results/test_eval.json
```

### مشاكل التعرف على العربية

**الأعراض**: حروف عربية مفقودة أو خاطئة، مشاكل في RTL

**الحلول**:
```bash
# 1. تفعيل استعادة النقاط
python src/main.py --enable-dotted-recovery

# 2. تحديث قاموس النقاط
python -c "
from modules.nlp.arabic_rtl import ArabicDottedRecovery
rec = ArabicDottedRecovery()
rec.add_to_dictionary('السلام')
rec.add_to_dictionary('عليكم')
rec.save_dictionary('artifacts/correction_dict.json')
"

# 3. التحقق من اتجاه النص
python -c "
import arabic_reshaper
from bidi.algorithm import get_display
text = 'بسم الله الرحمن الرحيم'
reshaped = arabic_reshaper.reshape(text)
display = get_display(reshaped)
print(display)
"
```

### التدريب بطيء

**الحلول**:
```bash
# 1. تفعيل التدريب المختلط (fp16/bf16)
--fp16                    # لـ GPUs سلسلة 20xx و 30xx
--bf16                    # لـ GPUs سلسلة 40xx و A100

# 2. زيادة num_workers في dataloader
--num-workers 4

# 3. تفعيل تسريع Unsloth
--accelerator unsloth

# 4. استخدام gradient checkpointing
--gradient-checkpointing

# 5. استخدم_cache=False لـ النموذج
--no-cache

# 6. تحقق من أن البيانات على SSD وليس HDD
```

### أخطاء شائعة أثناء التثبيت

```
# خطأ: CUDA version mismatch
# الحل: تطابق إصدارات CUDA
pip install torch==2.3.0+cu121 --index-url https://download.pytorch.org/whl/cu121

# خطأ: bitsandbytes not compiled for this platform
# الحل:
pip install bitsandbytes --no-cache-dir --force-reinstall

# خطأ: ModuleNotFoundError: No module named 'training'
# الحل: ضبط PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## المراجع والموارد الإضافية

- [توثيق Transformers](https://huggingface.co/docs/transformers/)
- [توثيق PEFT/LoRA](https://huggingface.co/docs/peft/)
- [توثيق Unsloth](https://github.com/unslothai/unsloth)
- [مجموعة بيانات Khodok](https://github.com/khodok/khodok)
- [دليل التطوير](./DEVELOPER_GUIDE.md)
- [دليل الاختبارات](./TESTING_GUIDE.md)

---

*آخر تحديث: يونيو 2025 | OmniFile Processor v5.0*
