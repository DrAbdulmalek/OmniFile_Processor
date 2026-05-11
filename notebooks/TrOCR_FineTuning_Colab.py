# ╔══════════════════════════════════════════════════════════════════════╗
# ║  TrOCR Fine-Tuning — Medical Handwriting Colab Edition              ║
# ║  تدريب مخصص على بيانات الملاحظات الطبية + تصدير Offline          ║
# ║                                                                      ║
# ║  الاستخدام:                                                          ║
# ║    1. شغّل Cell 1 (التثبيت)                                         ║
# ║    2. شغّل Cell 2 (تحميل البيانات والنموذج)                        ║
# ║    3. شغّل Cell 3 (التدريب)                                         ║
# ║    4. شغّل Cell 4 (التصدير)                                         ║
# ║    5. شغّل Cell 5 (التقييم)                                         ║
# ║                                                                      ║
# ║  المؤلف: Dr. Abdulmalek Tamer Al-husseini                           ║
# ║  الرخصة: MIT                                                        ║
# ╚══════════════════════════════════════════════════════════════════════╝

# =============================================================================
# Cell 1: تثبيت الاعتماديات
# =============================================================================
"""
تثبيت الحزم اللازمة للتدريب على TrOCR.
في Colab، أزل التعليق من الأسطر التالية:

    # !pip install -q transformers datasets accelerate peft jiwer \
    #     pillow opencv-python-headless albumentations
"""

import sys
import subprocess

def _install_training_deps():
    """تثبيت اعتماديات التدريب مع التحقق المسبق."""
    required = {
        "transformers": "transformers",
        "datasets": "datasets",
        "accelerate": "accelerate",
        "peft": "peft",
        "jiwer": "jiwer",
        "Pillow": "PIL",
        "opencv-python-headless": "cv2",
        "numpy": "numpy",
    }
    missing = []
    for pkg, module in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"📦 جاري تثبيت الحزم المفقودة: {missing}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q"] + missing
        )
        print("✅ تمّ التثبيت بنجاح!")
    else:
        print("✅ جميع الحزم مثبتة مسبقًا.")

_install_training_deps()

# =============================================================================
# Cell 2: تحميل البيانات والنموذج
# =============================================================================
"""
تحميل النموذج الأساسي (microsoft/trocr-base-handwritten)
وإعداد مجموعة البيانات للتدريب.

إذا كنت تملك بيانات ملاحظات طبية، ارفعها كملف ZIP أو استخدم
المجموعة التوليدية المتوفرة أدناه.
"""

import os
import gc
import json
import time
import random
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np

import torch
from torch.utils.data import Dataset

# ── إعداد التسجيل ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("TrOCR_FineTune")

# ── إعداد الجهاز ──
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info("🖥️  الجهاز: %s", DEVICE)
if DEVICE == "cuda":
    logger.info(
        "GPU: %s | VRAM: %.1f GB",
        torch.cuda.get_device_name(0),
        torch.cuda.get_device_properties(0).total_mem / 1e9,
    )


# =============================================================================
# Dataset — مجموعة بيانات الملاحظات الطبية
# =============================================================================

class MedicalHandwritingDataset(Dataset):
    """مجموعة بيانات الملاحظات الطبية بخط اليد للتدريب.

    تدعم مصادر متعددة:
    1. مجلد صور + ملف JSON (format: {"image": path, "text": label})
    2. ملف ZIP يحتوي صورًا + annotations.json
    3. بيانات توليدية (Synthetic) للتجربة

    Args:
        data_source: مسار مجلد أو ملف ZIP أو "synthetic".
        processor: TrOCRProcessor لمعالجة الصور والنصوص.
        max_text_length: أقصى طول للنص (حرفًا).
        image_size: حجم الصورة المستهدف (H, W).
    """

    def __init__(
        self,
        data_source: str = "synthetic",
        processor=None,
        max_text_length: int = 128,
        image_size: Tuple[int, int] = (384, 384),
    ):
        self.processor = processor
        self.max_len = max_text_length
        self.img_size = image_size
        self._samples: List[Dict[str, str]] = []

        if data_source == "synthetic":
            self._generate_synthetic_data()
        elif data_source.endswith(".zip"):
            self._load_from_zip(data_source)
        elif os.path.isdir(data_source):
            self._load_from_folder(data_source)
        else:
            raise ValueError(
                f"مصدر البيانات غير مدعوم: {data_source}. "
                "استخدم 'synthetic' أو مسار مجلد أو ملف ZIP."
            )

        logger.info(
            "✅ تمّ تحميل %d عينة بيانات من: %s",
            len(self._samples),
            data_source,
        )

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self._samples[idx]

        # تحميل الصورة
        image = Image.open(sample["image_path"]).convert("RGB")

        # اقتصاص النص إذا كان طويلًا
        text = sample["text"][: self.max_len]

        # معالجة بالـ processor
        if self.processor is not None:
            pixel_values = self.processor(
                image, return_tensors="pt"
            ).pixel_values.squeeze(0)

            labels = self.processor.tokenizer(
                text,
                return_tensors="pt",
                padding="max_length",
                max_length=self.max_len,
                truncation=True,
            ).input_ids.squeeze(0)

            # استبدال pad_token_id بـ -100 (يتجاهلها loss)
            labels[
                labels == self.processor.tokenizer.pad_token_id
            ] = -100

            return {
                "pixel_values": pixel_values,
                "labels": labels,
                "text": text,
            }

        # بدون processor — إرجاع خام
        return {
            "image": np.array(image),
            "text": text,
        }

    # ─────────────────────────────────────────────────────────────────
    # data loading
    # ─────────────────────────────────────────────────────────────────
    def _load_from_folder(self, folder_path: str) -> None:
        """تحميل من مجلد يحتوي صورًا + annotations.json."""
        folder = Path(folder_path)
        ann_file = folder / "annotations.json"

        if not ann_file.exists():
            # البحث عن أي ملف JSON
            json_files = list(folder.glob("*.json"))
            if json_files:
                ann_file = json_files[0]
            else:
                raise FileNotFoundError(
                    f"لم يُعثر على ملف annotations في: {folder_path}"
                )

        with open(ann_file, encoding="utf-8") as f:
            annotations = json.load(f)

        for item in annotations:
            img_path = folder / item["image"]
            if img_path.exists():
                self._samples.append({
                    "image_path": str(img_path),
                    "text": item["text"],
                })

    def _load_from_zip(self, zip_path: str) -> None:
        """تحميل من ملف ZIP."""
        import zipfile

        extract_dir = Path("./_extracted_data")
        extract_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        self._load_from_folder(str(extract_dir))

    # ─────────────────────────────────────────────────────────────────
    # synthetic data generation
    # ─────────────────────────────────────────────────────────────────
    def _generate_synthetic_data(self, num_samples: int = 200) -> None:
        """توليد بيانات تجريبية للخط العربي الطبي.

        يُنشئ صورًا تحتوي نصوصًا عربية طبية بخطوط متنوعة
        مع تأثيرات ضوضاء وتدوير لتحسين التعميم.
        """
        # ── نصوص طبية عربية للنموذج ──
        MEDICAL_TEXTS = [
            # أدوية وجرعات
            "المريض يعاني من ارتفاع ضغط الدم",
            "الجرعة: 500 ملغ مرتين يوميا بعد الأكل",
            "أموكسيسيلين 250 ملغ كل 8 ساعات",
            "ميتفورمين 850 ملغ مع الفطور",
            "أنسولين 10 وحدات قبل كل وجبة",
            "بايريكسامول 500 ملغ عند الحاجة",
            "أوميبرازول 20 ملغ قبل النوم",
            "أسبرين 100 ملغ يوميا",
            "ليزينوبريل 10 ملغ صباحا",
            "آتورفاستاتين 20 ملغ مساء",
            # تشخيصات
            "تشخيص: التهاب الجيوب الأنفية المزمن",
            "المرض: السكري من النوع الثاني",
            "الحالة: ارتفاع ضغط شرياني",
            "يوجد التهاب في المفاصل اليمنى",
            "الربو القصبي — استمرار العلاج",
            "اضطراب في نظم القلب يحتاج متابعة",
            # فحوصات
            "صورة دم كاملة ضرورية",
            "HbA1c يجب أن يكون أقل من 7",
            "تخطيط قلب ECG في الموعد القادم",
            "وظائف الكبد والكلى سليمة",
            "صورة الصدر بالأشعة السينية طبيعية",
            "TSH ضمن الحدود الطبيعية",
            "مستوى السكر الصائم: 180 ملغ/ديسيلتر",
            "ضغط الدم: 140/90 ملم زئبق",
            # تعليمات
            "يجب الإقلاع عن التدخين فورا",
            "نظام غذائي قليل الملح والسكر",
            "ممارسة الرياضة 30 دقيقة يوميا",
            "مراجعة بعد شهر للاطمئنان",
            "لا بد من إجراء الفحوصات المطلوبة",
            "المتابعة مع طبيب الأسنان أسبوعيا",
            "الالتزام بالدواء في مواعيده",
            "تجنب الأكل الدهني والمقلي",
            "شرب الماء بكثرة — 8 أكواب يوميا",
            "النوم مبكرا والاستيقاظ باكرا",
            # ملاحظات عامة
            "Dr. Ahmad — تاريخ: 15/3/2025",
            "القسم: جراحة العظام — غرفة 204",
            "تقرير الفحص السريري الشامل",
            "المريض بحاجة لعملية جراحية",
            "الوضع مستقر تحت المراقبة",
            "تحسن واضح في الحالة العامة",
            "يحتاج نقل لمستشفى أكبر",
            "الأعراض: صداع + دوخة + تعب",
        ]

        # ── خطوط عربية (إذا توفّرت) ──
        ARABIC_FONTS = [
            "arial.ttf",
            "DejaVuSans.ttf",
            "NotoNaskhArabic-Regular.ttf",
            "amiri-regular.ttf",
            "tahoma.ttf",
        ]

        font_path = None
        available_fonts = []
        for font_name in ARABIC_FONTS:
            # البحث في مواقع الخطوط الشائعة
            search_paths = [
                Path(font_name),
                Path("/usr/share/fonts/truetype") / font_name,
                Path("/usr/share/fonts") / font_name,
                Path("/usr/local/share/fonts") / font_name,
                Path("~/.fonts") / font_name,
            ]
            for p in search_paths:
                p = p.expanduser()
                if p.exists():
                    font_path = str(p)
                    break
            if font_path:
                break

        # ── إنشاء مجلد البيانات ──
        output_dir = Path("./_synthetic_data")
        output_dir.mkdir(exist_ok=True)

        count = 0
        for i in range(num_samples):
            text = random.choice(MEDICAL_TEXTS)

            # إضافة تنويع (أرقام، أسماء)
            if random.random() < 0.3:
                text = f"المريض رقم {random.randint(100, 999)} — {text}"
            if random.random() < 0.2:
                text = f"{text} — التاريخ: {random.randint(1,30)}/{random.randint(1,12)}/2025"

            # إنشاء صورة
            img = Image.new("RGB", (640, 128), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            font_size = random.randint(28, 42)
            try:
                if font_path:
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

            # كتابة النص
            draw.text(
                (20, 40),
                text,
                fill=(0, 0, 0),
                font=font,
            )

            # ── تطبيق Augmentation ──
            img_array = np.array(img)

            # إضافة ضوضاء
            if random.random() < 0.5:
                noise = np.random.randint(0, 30, img_array.shape, dtype=np.uint8)
                img_array = np.clip(
                    img_array.astype(np.int16) + noise,
                    0, 255
                ).astype(np.uint8)

            # تحويل إلى PIL
            img_aug = Image.fromarray(img_array)

            # حفظ الصورة
            img_path = output_dir / f"synth_{i:04d}.png"
            img_aug.save(str(img_path))

            self._samples.append({
                "image_path": str(img_path),
                "text": text,
            })
            count += 1

        # حفظ ملف التعليقات التوضيحية
        annotations = [
            {"image": f"synth_{i:04d}.png", "text": s["text"]}
            for i, s in enumerate(self._samples)
        ]
        ann_path = output_dir / "annotations.json"
        ann_path.write_text(
            json.dumps(annotations, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(
            "✅ تمّ توليد %d عينة بيانات في: %s",
            count,
            output_dir,
        )


# =============================================================================
# Cell 3: التدريب مع LoRA
# =============================================================================
"""
ضبط TrOCR باستخدام LoRA (Low-Rank Adaptation).
LoRA يُقلّل عدد المعاملات القابلة للتدريب من ~330M إلى ~4M،
مما يسمح بالتدريب على GPU بسعة 16GB VRAM.
"""

# ── إعدادات التدريب ──
@dataclass
class TrainingConfig:
    """إعدادات التدريب."""
    # النموذج
    model_name: str = "microsoft/trocr-base-handwritten"
    output_dir: str = "./trocr_arabic_medical"

    # LoRA
    lora_r: int = 8              # بُعد LoRA (4, 8, 16)
    lora_alpha: int = 16         # مُعامِل alpha
    lora_dropout: float = 0.05   # dropout

    # التدريب
    num_epochs: int = 5          # عدد الحقب
    batch_size: int = 4          # حجم الدفعة
    learning_rate: float = 5e-5  # معدّل التعلّم
    fp16: bool = True            # تدريب بنصف دقة (GPU فقط)
    max_text_length: int = 128   # أقصى طول للنص

    # البيانات
    data_source: str = "synthetic"
    train_split: float = 0.9     # نسبة التدريب
    random_seed: int = 42

    # التقييم
    eval_steps: int = 50         # تقييم كل N خطوة
    save_steps: int = 100        # حفظ كل N خطوة
    logging_steps: int = 25      # تسجيل كل N خطوة


def create_datasets(
    config: TrainingConfig,
    processor,
) -> Tuple[Dataset, Optional[Dataset]]:
    """إنشاء مجموعات التدريب والاختبار.

    Args:
        config: إعدادات التدريب.
        processor: TrOCRProcessor.

    Returns:
        (train_dataset, eval_dataset)
    """
    full_dataset = MedicalHandwritingDataset(
        data_source=config.data_source,
        processor=processor,
        max_text_length=config.max_text_length,
    )

    # تقسيم التدريب/الاختبار
    random.seed(config.random_seed)
    indices = list(range(len(full_dataset)))
    random.shuffle(indices)

    split_idx = int(len(indices) * config.train_split)
    train_indices = indices[:split_idx]
    eval_indices = indices[split_idx:]

    train_dataset = torch.utils.data.Subset(full_dataset, train_indices)
    eval_dataset = (
        torch.utils.data.Subset(full_dataset, eval_indices)
        if eval_indices else None
    )

    logger.info(
        "📊 التدريب: %d عينة | الاختبار: %d عينة",
        len(train_dataset),
        len(eval_dataset) if eval_dataset else 0,
    )
    return train_dataset, eval_dataset


def train_model(config: TrainingConfig = None) -> dict:
    """تشغيل التدريب الكامل.

    خطوات التدريب:
        1. تحميل النموذج والـ processor
        2. تطبيق LoRA
        3. إعداد Trainer
        4. التدريب
        5. حفظ النتائج

    Returns:
        قاموس يحتوي مسارات النموذج والإحصائيات.
    """
    if config is None:
        config = TrainingConfig()

    from transformers import (
        VisionEncoderDecoderModel,
        TrOCRProcessor,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        EarlyStoppingCallback,
    )
    from peft import LoraConfig, get_peft_model, TaskType

    start_time = time.time()

    # ── 1. تحميل النموذج والـ processor ──
    logger.info("⏳ جاري تحميل النموذج الأساسي: %s", config.model_name)
    processor = TrOCRProcessor.from_pretrained(config.model_name)
    model = VisionEncoderDecoderModel.from_pretrained(config.model_name)

    # ── تكوين معرّفات خاصة ──
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size

    # ── 2. تطبيق LoRA ──
    logger.info("🔧 جاري تطبيق LoRA (r=%d, alpha=%d)...", config.lora_r, config.lora_alpha)
    lora_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=["query", "value"],
        bias="none",
        task_type=TaskType.SEQ_2_SEQ_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── 3. إنشاء البيانات ──
    logger.info("📊 جاري تحميل البيانات من: %s", config.data_source)
    train_dataset, eval_dataset = create_datasets(config, processor)

    # ── 4. إعداد التدريب ──
    training_args = Seq2SeqTrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.num_epochs,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        learning_rate=config.learning_rate,
        predict_with_generate=True,
        generation_max_length=config.max_text_length,
        fp16=config.fp16 and DEVICE == "cuda",
        save_strategy="epoch",
        evaluation_strategy="epoch" if eval_dataset else "no",
        logging_steps=config.logging_steps,
        save_total_limit=2,
        load_best_model_at_end=eval_dataset is not None,
        metric_for_best_model="cer",
        greater_is_better=False,
        report_to="none",
        dataloader_pin_memory=DEVICE == "cuda",
        gradient_accumulation_steps=2,   # توفير VRAM
        warmup_ratio=0.1,
        weight_decay=0.01,
    )

    # ── دالة التقييم: CER ──
    def compute_metrics(pred):
        """حساب Character Error Rate (CER)."""
        from jiwer import cer

        predictions_ids = pred.predictions
        labels_ids = pred.label_ids

        # فك ترميز التنبؤات
        pred_str = processor.tokenizer.batch_decode(
            predictions_ids, skip_special_tokens=True
        )

        # فك ترميز الملصقات (استبدال -1 بـ pad)
        labels_ids = np.where(
            labels_ids != -100, labels_ids, processor.tokenizer.pad_token_id
        )
        label_str = processor.tokenizer.batch_decode(
            labels_ids, skip_special_tokens=True
        )

        # حساب CER
        cer_score = cer(label_str, pred_str)
        return {"cer": cer_score}

    # ── callbacks ──
    callbacks = []
    if eval_dataset is not None:
        callbacks.append(
            EarlyStoppingCallback(early_stopping_patience=3)
        )

    # ── 5. إنشاء Trainer ──
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=processor.tokenizer,
        compute_metrics=compute_metrics if eval_dataset else None,
        callbacks=callbacks,
    )

    # ── 6. التدريب ──
    logger.info("🏋️ بدء التدريب — %d حقب...", config.num_epochs)

    # تحويل eval_dataset إذا كان Subset
    train_result = trainer.train()

    # ── 7. حفظ النموذج ──
    final_dir = os.path.join(config.output_dir, "final")
    trainer.save_model(final_dir)
    processor.save_pretrained(final_dir)

    # حفظ التكوين
    config_dict = {
        "model_name": config.model_name,
        "lora_r": config.lora_r,
        "lora_alpha": config.lora_alpha,
        "num_epochs": config.num_epochs,
        "batch_size": config.batch_size,
        "learning_rate": config.learning_rate,
        "train_samples": len(train_dataset),
        "eval_samples": len(eval_dataset) if eval_dataset else 0,
        "device": DEVICE,
        "trained_at": datetime.now().isoformat(),
        "training_time_seconds": round(time.time() - start_time, 2),
    }

    config_path = os.path.join(final_dir, "training_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=2)

    total_time = round(time.time() - start_time, 2)

    # ── سجل التدريب ──
    if trainer.state.log_history:
        log_path = os.path.join(config.output_dir, "training_log.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(
                trainer.state.log_history, f, ensure_ascii=False, indent=2
            )

    logger.info("✅ تمّ التدريب بنجاح في %.1f ثانية!", total_time)
    logger.info("📁 النموذج محفوظ في: %s", final_dir)

    # ── Tidy up ──
    gc.collect()
    if DEVICE == "cuda":
        torch.cuda.empty_cache()

    return {
        "model_dir": final_dir,
        "training_time": total_time,
        "train_samples": len(train_dataset),
        "config": config_dict,
        "log_history": trainer.state.log_history,
    }


# =============================================================================
# Cell 4: تصدير النموذج للاستخدام Offline
# =============================================================================
"""
تصدير النموذج المُضبَط في ملف ZIP جاهز للاستخدام
بدون اتصال بالإنترنت.
"""

def export_model_for_offline(
    model_dir: str,
    output_zip: str = "trocr_arabic_medical_offline.zip",
) -> str:
    """تصدير النموذج في ملف ZIP للاستخدام offline.

    يحتوي الملف:
    - config.json: إعدادات النموذج
    - adapter_model.bin / adapter_config.json: LoRA adapter
    - tokenizer_config.json + vocab: الـ tokenizer
    - preprocessor_config.json: إعدادات المعالج
    - training_config.json: تكوين التدريب
    - inference_script.py: سكربت الاستدلال

    Args:
        model_dir: مسار النموذج المُضبَط.
        output_zip: مسار ملف ZIP الناتج.

    Returns:
        مسار ملف ZIP.
    """
    import zipfile

    model_path = Path(model_dir)
    if not model_path.exists():
        raise FileNotFoundError(f"مجلد النموذج غير موجود: {model_dir}")

    files_to_include = []
    for pattern in [
        "*.json", "*.bin", "*.safetensors", "*.txt",
        "special_tokens_map.json", "tokenizer_config.json",
        "preprocessor_config.json", "generation_config.json",
    ]:
        files_to_include.extend(model_path.glob(pattern))

    # إنشاء سكربت الاستدلال
    inference_script = '''#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════
# سكربت الاستدلال — TrOCR Arabic Medical (Offline)
# ═══════════════════════════════════════════════════════════
import sys
from PIL import Image
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from peft import PeftModel

MODEL_DIR = "./trocr_arabic_medical/final"

def load_model():
    processor = TrOCRProcessor.from_pretrained(MODEL_DIR)
    base_model = VisionEncoderDecoderModel.from_pretrained(
        "microsoft/trocr-base-handwritten"
    )
    model = PeftModel.from_pretrained(base_model, MODEL_DIR)
    model.eval()
    if torch.cuda.is_available():
        model = model.cuda()
    return model, processor

def recognize(image_path, model=None, processor=None):
    if model is None:
        model, processor = load_model()
    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(image, return_tensors="pt").pixel_values
    if torch.cuda.is_available():
        pixel_values = pixel_values.cuda()
    generated_ids = model.generate(pixel_values)
    text = processor.tokenizer.batch_decode(
        generated_ids, skip_special_tokens=True
    )[0]
    return text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام: python inference_script.py <صورة>")
        sys.exit(1)
    text = recognize(sys.argv[1])
    print(f"النص: {text}")
'''
    inference_path = model_path / "inference_script.py"
    inference_path.write_text(inference_script, encoding="utf-8")
    files_to_include.append(inference_path)

    # إنشاء README
    readme = """# TrOCR Arabic Medical — نموذج مُضبَط للملاحظات الطبية

## الاستخدام السريع
```python
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from peft import PeftModel

processor = TrOCRProcessor.from_pretrained("./")
base = VisionEncoderDecoderModel.from_pretrained(
    "microsoft/trocr-base-handwritten"
)
model = PeftModel.from_pretrained(base, "./")
model.eval()

from PIL import Image
image = Image.open("note.jpg")
pixel_values = processor(image, return_tensors="pt").pixel_values
text = processor.tokenizer.batch_decode(
    model.generate(pixel_values), skip_special_tokens=True
)[0]
```
"""
    readme_path = model_path / "README.md"
    readme_path.write_text(readme, encoding="utf-8")
    files_to_include.append(readme_path)

    # إنشاء ZIP
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files_to_include:
            arcname = f"{model_path.name}/{f.name}"
            zf.write(str(f), arcname)

    zip_size_mb = os.path.getsize(output_zip) / (1024 * 1024)
    logger.info(
        "📦 تمّ تصدير النموذج: %s (%.1f MB)",
        output_zip,
        zip_size_mb,
    )
    return output_zip


# =============================================================================
# Cell 5: التقييم — مقارنة قبل/بعد التدريب
# =============================================================================
"""
مقارنة أداء النموذج الأساسي مع النموذج المُضبَط.
يقيس: CER, WER, وعدد الأمثلة الصحيحة.
"""

@dataclass
class EvalResult:
    """نتيجة التقييم."""
    model_name: str
    cer: float
    wer: float
    exact_match: float
    num_samples: int
    avg_confidence: float = 0.0
    examples: List[Dict] = field(default_factory=list)


def evaluate_model(
    model,
    processor,
    eval_dataset: Dataset,
    model_name: str = "model",
    num_samples: int = 50,
) -> EvalResult:
    """تقييم النموذج على مجموعة الاختبار.

    Args:
        model: نموذج TrOCR (مع أو بدون LoRA).
        processor: TrOCRProcessor.
        eval_dataset: مجموعة الاختبار.
        model_name: اسم النموذج (للعرض).
        num_samples: عدد العينات للتقييم.

    Returns:
        كائن EvalResult.
    """
    from jiwer import cer, wer

    model.eval()
    device = next(model.parameters()).device

    total_cer = 0.0
    total_wer = 0.0
    exact_matches = 0
    examples = []

    n = min(num_samples, len(eval_dataset))
    logger.info("📊 جاري تقييم %s على %d عينة...", model_name, n)

    with torch.no_grad():
        for i in range(n):
            sample = eval_dataset[i]

            # إذا كان Dataset يعيد dict مع pixel_values
            if "pixel_values" in sample:
                pixel_values = sample["pixel_values"].unsqueeze(0).to(device)
            else:
                # معالجة يدوية
                image = Image.open(sample["image_path"]).convert("RGB")
                pixel_values = processor(
                    image, return_tensors="pt"
                ).pixel_values.to(device)

            generated_ids = model.generate(pixel_values)
            pred_text = processor.tokenizer.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]

            gt_text = sample["text"]

            # حساب المقاييس
            sample_cer = cer(gt_text, pred_text)
            sample_wer = wer(gt_text, pred_text)
            total_cer += sample_cer
            total_wer += sample_wer

            if pred_text.strip() == gt_text.strip():
                exact_matches += 1

            examples.append({
                "ground_truth": gt_text,
                "prediction": pred_text,
                "cer": round(sample_cer, 4),
                "exact_match": pred_text.strip() == gt_text.strip(),
            })

    avg_cer = total_cer / n if n > 0 else 0.0
    avg_wer = total_wer / n if n > 0 else 0.0
    exact_match_rate = exact_matches / n if n > 0 else 0.0

    result = EvalResult(
        model_name=model_name,
        cer=round(avg_cer, 4),
        wer=round(avg_wer, 4),
        exact_match=round(exact_match_rate, 4),
        num_samples=n,
        examples=examples,
    )

    logger.info(
        "📊 %s — CER: %.2f%% | WER: %.2f%% | Exact Match: %.1f%%",
        model_name,
        avg_cer * 100,
        avg_wer * 100,
        exact_match_rate * 100,
    )
    return result


def compare_models(
    base_model_path: str = "microsoft/trocr-base-handwritten",
    finetuned_path: str = "./trocr_arabic_medical/final",
    data_source: str = "synthetic",
    max_text_length: int = 128,
) -> Dict:
    """مقارنة النموذج الأساسي مع المُضبَط.

    Args:
        base_model_path: مسار النموذج الأساسي.
        finetuned_path: مسار النموذج المُضبَط.
        data_source: مصدر بيانات التقييم.
        max_text_length: أقصى طول للنص.

    Returns:
        قاموس يحتوي نتائج المقارنة.
    """
    from transformers import (
        VisionEncoderDecoderModel,
        TrOCRProcessor,
    )
    from peft import PeftModel

    # ── تحميل البيانات ──
    processor = TrOCRProcessor.from_pretrained(base_model_path)
    full_dataset = MedicalHandwritingDataset(
        data_source=data_source,
        processor=processor,
        max_text_length=max_text_length,
    )

    # تقسيم: استخدام 20% للاختبار
    random.seed(42)
    n_eval = max(20, len(full_dataset) // 5)
    eval_indices = random.sample(range(len(full_dataset)), min(n_eval, len(full_dataset)))
    eval_dataset = torch.utils.data.Subset(full_dataset, eval_indices)

    # ── تقييم النموذج الأساسي ──
    logger.info("📊 تقييم النموذج الأساسي...")
    base_model = VisionEncoderDecoderModel.from_pretrained(base_model_path)
    base_model.eval()
    if DEVICE == "cuda":
        base_model = base_model.to(DEVICE)

    base_result = evaluate_model(
        base_model, processor, eval_dataset,
        model_name="Base (trocr-base-handwritten)",
    )

    # تحرير الذاكرة
    del base_model
    gc.collect()
    if DEVICE == "cuda":
        torch.cuda.empty_cache()

    # ── تقييم النموذج المُضبَط ──
    if os.path.exists(finetuned_path):
        logger.info("📊 تقييم النموذج المُضبَط...")
        finetuned_base = VisionEncoderDecoderModel.from_pretrained(base_model_path)
        finetuned_model = PeftModel.from_pretrained(finetuned_base, finetuned_path)
        finetuned_model.eval()
        if DEVICE == "cuda":
            finetuned_model = finetuned_model.to(DEVICE)

        finetuned_result = evaluate_model(
            finetuned_model, processor, eval_dataset,
            model_name="Fine-Tuned (Arabic Medical)",
        )
    else:
        logger.warning("⚠️ النموذج المُضبَط غير موجود: %s", finetuned_path)
        finetuned_result = None

    # ── تجميع التقرير ──
    report_lines = [
        "═" * 60,
        "  📊 تقرير المقارنة — قبل وبعد التدريب",
        "═" * 60,
        "",
        f"  عدد عينات الاختبار: {base_result.num_samples}",
        "",
        "  ┌─────────────────────┬──────────────┬──────────────┐",
        "  │ المقياس             │ الأساسي      │ المُضبَط     │",
        "  ├─────────────────────┼──────────────┼──────────────┤",
    ]

    metrics = [
        ("CER", base_result.cer, finetuned_result.cer if finetuned_result else None),
        ("WER", base_result.wer, finetuned_result.wer if finetuned_result else None),
        ("Exact Match", base_result.exact_match, finetuned_result.exact_match if finetuned_result else None),
    ]

    for name, base_val, ft_val in metrics:
        base_str = f"{base_val:.2%}"
        ft_str = f"{ft_val:.2%}" if ft_val is not None else "N/A"
        improvement = ""
        if ft_val is not None:
            if name in ("CER", "WER"):
                diff = base_val - ft_val
                if diff > 0:
                    improvement = f" ↓{diff:.2%}"
            else:
                diff = ft_val - base_val
                if diff > 0:
                    improvement = f" ↑{diff:.2%}"
        report_lines.append(
            f"  │ {name:<19} │ {base_str:<12} │ {ft_str:<12} │ {improvement}"
        )

    report_lines.append(
        "  └─────────────────────┴──────────────┴──────────────┘"
    )

    # أمثلة
    report_lines.extend(["", "📝 أمثلة على التحسن:"])
    if finetuned_result:
        improvements = [
            (b, f) for b, f in zip(base_result.examples, finetuned_result.examples)
            if f["exact_match"] and not b["exact_match"]
        ][:5]
        for base_ex, ft_ex in improvements:
            report_lines.append(f"  ✅ {ft_ex['ground_truth']}")
            report_lines.append(f"     الأساسي:  {base_ex['prediction']}")
            report_lines.append(f"     المُضبَط: {ft_ex['prediction']}")
            report_lines.append("")

    full_report = "\n".join(report_lines)
    print(full_report)

    return {
        "base": {
            "cer": base_result.cer,
            "wer": base_result.wer,
            "exact_match": base_result.exact_match,
        },
        "finetuned": {
            "cer": finetuned_result.cer if finetuned_result else None,
            "wer": finetuned_result.wer if finetuned_result else None,
            "exact_match": finetuned_result.exact_match if finetuned_result else None,
        },
        "report": full_report,
    }


# =============================================================================
# Cell 6: التشغيل — نقطة الدخول الرئيسية
# =============================================================================
"""
شغّل هذا الخلية لتنفيذ التدريب الكامل.
يمكنك تخصيص الإعدادات عبر TrainingConfig.
"""

if __name__ == "__main__":
    print("=" * 65)
    print("  TrOCR Fine-Tuning — Medical Handwriting Colab Edition")
    print("  تدريب مخصص على بيانات الملاحظات الطبية")
    print("=" * 65)

    # ── إعدادات مخصصة ──
    config = TrainingConfig(
        model_name="microsoft/trocr-base-handwritten",
        output_dir="./trocr_arabic_medical",
        lora_r=8,
        lora_alpha=16,
        num_epochs=5,
        batch_size=4,
        learning_rate=5e-5,
        fp16=DEVICE == "cuda",
        data_source="synthetic",  # غيّرها لمسار بياناتك
        train_split=0.9,
    )

    print(f"\n⚙️  الإعدادات:")
    print(f"  - النموذج: {config.model_name}")
    print(f"  - LoRA: r={config.lora_r}, alpha={config.lora_alpha}")
    print(f"  - الحقب: {config.num_epochs}, الدفعة: {config.batch_size}")
    print(f"  - معدّل التعلّم: {config.learning_rate}")
    print(f"  - الجهاز: {DEVICE}")
    print(f"  - البيانات: {config.data_source}")
    print()

    # ── خطوة 1: التدريب ──
    print("🏋️ الخطوة 1: بدء التدريب...")
    train_result = train_model(config)

    # ── خطوة 2: التصدير ──
    print("\n📦 الخطوة 2: تصدير النموذج...")
    zip_path = export_model_for_offline(train_result["model_dir"])
    print(f"  ✓ ملف ZIP: {zip_path}")
    print(f"  ✓ الحجم: {os.path.getsize(zip_path) / (1024*1024):.1f} MB")

    # ── خطوة 3: التقييم ──
    print("\n📊 الخطوة 3: مقارنة الأداء...")
    comparison = compare_models(
        finetuned_path=train_result["model_dir"],
        data_source=config.data_source,
    )

    print("\n" + "=" * 65)
    print("  ✅ اكتمل التدريب بنجاح!")
    print(f"  - النموذج: {train_result['model_dir']}")
    print(f"  - ZIP: {zip_path}")
    print(f"  - وقت التدريب: {train_result['training_time']:.1f} ثانية")
    print("=" * 65)
