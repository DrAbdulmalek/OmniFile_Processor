# دليل حل المشاكل — HandwrittenOCR v5.3

> هذا الدليل يغطي أكثر المشاكل شيوعاً وكيفية حلها خطوة بخطوة.

---

## جدول المحتووى

1. [مشكلة OOM Kill (نفاد الذاكرة)](#1-مشكلة-oom-kill-نفاد-الذاكرة)
2. [فشل تحميل النماذج بدون إنترنت](#2-فشل-تحميل-النماذج-بدون-إنترنت)
3. [مجلد المشروع ليس مستودع Git](#3-مجلد-المشروع-ليس-مستودع-git)
4. [مشكلة مسار النموذج عند التحديث](#4-مشكلة-مسار-النموذج-عند-التحديث)
5. [خطأ libGL.so / OpenCV](#5-خطأ-libglso--opencv)
6. [خطأ XDG_RUNTIME_DIR](#6-خطأ-xdg_runtime_dir)
7. [مشكلة مساحة القرص](#7-مشكلة-مساحة-القرص)
8. [أداء بطيء جداً](#8-أداء-بطيء-جدا)
9. [استكشاف الأخطاء المتقدم](#9-استكشاف-الأخطاء-المتقدم)

---

## 1. مشكلة OOM Kill (نفاد الذاكرة)

### الأعراض
```
zsh: killed     python run.py --local --pdf "..."
```
أو تظهر الرسالة ثم ينتهي البرنامج فجأة بدون أي خطأ.

### السبب
نظام التشغيل (Linux) يقتل العملية لأنها تستهلك كل الذاكرة RAM. يحدث هذا في مرحلتين:

| المرحلة | الاستهلاك | الحد الأدنى للذاكرة المطلوبة |
|---------|-----------|-------------------------------|
| تحميل المدققات الإملائية | ~100 MB | 512 MB |
| تحميل TrOCR | ~600 MB | 1 GB |
| تحميل EasyOCR (en+ar) | **~1.5 GB** | **2.5 GB** |
| معالجة صفحة (300 DPI) | ~80 MB/صفحة | 3 GB+ |

### الحل 1: وضع خفيف (الأسهل) ⭐

استخدم الوضع الخفيف الذي يقلل استهلاك الذاكرة بشكل كبير:

```bash
python run.py --local --pdf "input.pdf" --low-memory
```

ما يفعله الوضع الخفيف:
- يُقلل DPI من 300 إلى 200 (يوفّر 44% من ذاكرة الصور)
- يُستخدم فقط EasyOCR الإنجليزي (يوفّر ~800 MB من ذاكرة النموذج)
- يُقلل حجم الدفعة من 16 إلى 4
- يُعطّل deskew (يوفّر ذاكرة المعالجة)

### الحل 2: تقليل عدد لغات EasyOCR

النموذج العربي لـ EasyOCR وحده يستهلك ~800 MB. إذا كانت ملاحظاتك بالإنجليزية فقط:

```bash
# تعديل يدوي في config.py
# غيّر السطر التالي من:
ocr_languages: list = field(default_factory=lambda: ["en", "ar"])
# إلى:
ocr_languages: list = field(default_factory=lambda: ["en"])
```

أو عبر سطر الأوامر (بعد تحديث المشروع):

```bash
python run.py --local --pdf "input.pdf" --lang en
```

### الحل 3: تقليل DPI

```bash
python run.py --local --pdf "input.pdf" --dpi 200
```

| DPI | حجم صفحة A4 (بكسل) | الذاكرة لكل صفحة | الجودة |
|-----|---------------------|-------------------|--------|
| 300 | 3500 × 2480 | ~26 MB | عالية جداً |
| 250 | 2917 × 2067 | ~18 MB | عالية |
| 200 | 2338 × 1654 | **~12 MB** | متوسطة-عالية |
| 150 | 1754 × 1240 | ~7 MB | مقبولة |

### الحل 4: معالجة صفحة بصفحة

بدلاً من معالجة كل الصفحات دفعة واحدة:

```bash
# صفحة 1 فقط أولاً
python run.py --local --pdf "input.pdf" --pages 1 1

# ثم صفحة 2
python run.py --local --pdf "input.pdf" --pages 2 2
```

### الحل 5: زيادة مساحة Swap (Manjaro/Linux)

إذا كان RAM أقل من 4 GB:

```bash
# التحقق من المساحة الحالية
free -h
swapon --show

# إنشاء ملف swap بحجم 4 GB
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# التأكد
free -h

# لجعلها دائمة (اختياري)
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### الحل 6: إغلاق البرامج الأخرى

قبل التشغيل، أغلق المتصفح والتطبيقات الثقيلة:

```bash
# التحقق من الذاكرة المستخدمة
free -h
# أو
htop
```

### التحقق من سبب القتل

```bash
#查看 OOM سجل
sudo journalctl -k | grep -i "oom\|killed\|out of memory" | tail -20

# أو
dmesg | grep -i "oom\|killed" | tail -10
```

---

## 2. فشل تحميل النماذج بدون إنترنت

### الأعراض
```
OSError: David-Magdy/TR_OCR_LARGE does not appear to have a file named pytorch_model.bin
```

### السبب
مشروعك يعمل أوفلاين لكن `config.py` يشير إلى اسم النموذج على HuggingFace بدلاً من المسار المحلي.

### الحل خطوة بخطوة:

**الخطوة 1:** تأكد من وجود النموذج محلياً:
```bash
ls ~/Handwritten_OCR_Ultimate/models_cache/models--David-Magdy--TR_OCR_LARGE/snapshots/main/
```
يجب أن ترى ملفات مثل `pytorch_model.bin` أو `model.safetensors`.

**الخطوة 2:** عدّل `config.py` ليشير للمسار المحلي:
```bash
sed -i 's|trocr_model_name: str = "David-Magdy/TR_OCR_LARGE"|trocr_model_name: str = "/home/$(whoami)/Handwritten_OCR_Ultimate/models_cache/models--David-Magdy--TR_OCR_LARGE/snapshots/main"|' ~/Handwritten_OCR_Ultimate/config.py
```

**الخطوة 3:** تأكد من تعيين متغيرات الأوفلاين:
```bash
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
```

**ملاحظة مهمة:** كل مرة تُحدّث المشروع (git pull أو نسخ ملفات جديدة)، يجب إعادة الخطوة 2 لأن `config.py` سيُستبدل بالنسخة الجديدة التي تحتوي المسار الافتراضي.

---

## 3. مجلد المشروع ليس مستودع Git

### الأعراض
```
fatal: not a git repository (or any parent up to mount point /)
```

### السبب
نسختك الأصلية من المشروع ليست مستودع Git — ربما نُسخت يدوياً أو من ملف مضغوط.

### الحل: نسخ الملفات المحدّثة يدوياً

```bash
# 1. نسخ المستودع مؤقتاً
cd /tmp
git clone https://github.com/DrAbdulmalek/HandwrittenOCR.git HandwrittenOCR_update

# 2. نسخ الملفات المحدّثة (مع الحفاظ على بياناتك)
SRC=/tmp/HandwrittenOCR_update
DST=~/Handwritten_OCR_Ultimate

cp $SRC/src/study_guide.py $DST/src/study_guide.py
cp $SRC/src/recognition.py $DST/src/recognition.py
cp $SRC/src/__init__.py $DST/src/__init__.py
cp $SRC/src/pdf_processor.py $DST/src/pdf_processor.py
cp $SRC/src/main.py $DST/src/main.py
cp $SRC/config.py $DST/config.py
cp $SRC/backend/app.py $DST/backend/app.py
cp $SRC/run.py $DST/run.py

# 3. تنظيف
rm -rf /tmp/HandwrittenOCR_update

# 4. التحقق من النسخة
grep "__version__" $DST/src/__init__.py
```

**تحذير:** لا تنسخ مجلدات: `database/`, `models_cache/`, `logs/`, `exports/`, `artifacts/` — هذه تحتوي بياناتك.

---

## 4. مشكلة مسار النموذج عند التحديث

### الأعراض
بعد التحديث، يظهر خطأ `does not appear to have a file named pytorch_model.bin`.

### السبب
كل تحديث لـ `config.py` يُعيد `trocr_model_name` إلى القيمة الافتراضية (HuggingFace URL).

### الحل الدائم: إنشاء ملف تعديل محلي

أنشئ ملف `local_config.py` لا يُستبدل بالتحديثات:

```python
# ~/Handwritten_OCR_Ultimate/local_config.py
# هذا الملف لا يُستبدل بالتحديثات — ضع تعديلاتك المحلية هنا

LOCAL_OVERRIDES = {
    "trocr_model_name": "/home/xorthomson/Handwritten_OCR_Ultimate/models_cache/models--David-Magdy--TR_OCR_LARGE/snapshots/main",
    "ocr_languages": ["en"],  # استخدم الإنجليزية فقط لتوفير الذاكرة
    "dpi": 200,                # تقليل DPI لتوفير الذاكرة
}
```

ثم عدّل سطر واحد في `run.py` بعد كل تحديث:
```bash
sed -i '/config = Config/i import local_config' ~/Handwritten_OCR_Ultimate/run.py
```

---

## 5. خطأ libGL.so / OpenCV

### الأعراض
```
error while loading shared libraries: libGL.so.1: cannot open shared object file
```

### الحل (Manjaro/Arch):
```bash
sudo pacman -S opencv
# أو فقط الرأس الخفيف:
sudo pacman -S opencv-headless
```

---

## 6. خطأ XDG_RUNTIME_DIR

### الأعراض
```
Qt: Could not find the Qt platform plugin "xcb" in ""
```

### الحل:
```bash
export XDG_RUNTIME_DIR=/tmp/runtime-$(whoami)
mkdir -p $XDG_RUNTIME_DIR
```

---

## 7. مشكلة مساحة القرص

### الأعراض
أخطاء `No space left on device` أو تبطؤ شديد.

### فحص المساحة:
```bash
# المساحة المتاحة
df -h ~

# أكبر المجلدات
du -sh ~/Handwritten_OCR_UCR_Ultimate/*/ | sort -rh | head -10
```

### تنظيف آمن:
```bash
# حذف نماذج EasyOCR المؤقتة (ست تُحمَّل مجدداً عند الحاجة)
rm -rf ~/.EasyOCR/*.tmp

# حذف سجلات قديمة
find ~/Handwritten_OCR_Ultimate/logs/ -name "*.log" -mtime +30 -delete

# حذف النسخ الاحتياطية القديمة
ls -lh ~/Handwritten_OCR_Ultimate/backups/
```

---

## 8. أداء بطيء جداً

### الحلول:

**1. استخدم GPU إذا متاح:**
```bash
# التحقق
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# إذا ظهر False، ثبّت CUDA:
# Manjaro: sudo pacman -S cuda cudnn
```

**2. قلل DPI:**
```bash
python run.py --local --pdf "input.pdf" --dpi 200
```

**3. استخدم وضع خفيف:**
```bash
python run.py --local --pdf "input.pdf" --low-memory
```

**4. استخدم batch size أصغر إذا الذاكرة ضيقة:**
```bash
# عدّل في config.py:
trocr_batch_size: int = 4   # بدلاً من 16
```

---

## 9. استكشاف الأخطاء المتقدم

### التحقق من البيئة:

```bash
# نسخة Python
python --version

# تفعيل البيئة
conda activate ocr_env   # أو: source ~/ocr_env/bin/activate

# المكتبات المطلوبة
pip list | grep -i "transformers\|easyocr\|torch\|opencv\|pdf2image"

# ذاكرة النظام
free -h

# معلومات المعالج
lscpu | grep "Model name"

# GPU
nvidia-smi 2>/dev/null || echo "لا يوجد NVIDIA GPU"
```

### تتبع استهلاك الذاكرة أثناء التشغيل:

```bash
# في نافذة طرفية أخرى أثناء التشغيل:
watch -n 1 free -h

# أو تتبع العملية:
python run.py --local --pdf "input.pdf" &
PID=$!
while kill -0 $PID 2>/dev/null; do
    ps -p $PID -o rss=,vsz=,cmd= 2>/dev/null
    sleep 2
done
```

### تشغيل بوضوح التصحيح:

```bash
python -u run.py --local --pdf "input.pdf" --pages 1 1 2>&1 | tee debug.log
```

### الحد الأدنى من المتطلبات:

| المكون | الحد الأدنى | الموصى به |
|--------|-----------|----------|
| RAM | 4 GB + 2 GB Swap | 8 GB |
| القرص | 5 GB | 10 GB |
| المعالج | أي معالج ثنائي النواة | 4 أنوية |
| GPU | غير مطلوب | NVIDIA (CUDA) |
| نظام التشغيل | Manjaro/Ubuntu 20+ | أي Linux |

---

## المساعدة

إذا لم يجدِ حل مشكلتك هنا، افتح Issue على:
https://github.com/DrAbdulmalek/HandwrittenOCR/issues

مع إرفاق:
- ناتج `free -h`
- ناتج `python --version`
- آخر 20 سطر من سجل الأخطاء
- مواصفات جهازك
