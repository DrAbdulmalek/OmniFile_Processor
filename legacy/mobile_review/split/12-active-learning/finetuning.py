# finetuning.py - Fine-tuning module for TrOCR
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments
)
from datasets import Dataset
import torch
from peft import LoraConfig, get_peft_model, TaskType
from pathlib import Path
import logging
from typing import Optional, List, Union
import os

logger = logging.getLogger(__name__)

class TrOCRFineTuner:
    """ضبط نماذج TrOCR على بيانات عربية."""

    def __init__(
        self,
        model_name: str = "microsoft/trocr-base-handwritten",
        output_dir: Union[str, Path] = "./fine_tuned_models",
        use_lora: bool = True,
        lora_r: int = 8,
        lora_alpha: int = 16,
        device: str = "auto"
    ):
        """
        تهيئة المدرب.

        Args:
            model_name: اسم النموذج الأساسي.
            output_dir: مجلد حفظ النماذج المدربة.
            use_lora: استخدام LoRA (افتراضي: True).
            lora_r: رتبة LoRA (افتراضي: 8).
            lora_alpha: ألفا LoRA (افتراضي: 16).
            device: الجهاز (auto, cuda, cpu).
        """
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_lora = use_lora
        self.lora_r = lora_r
        self.lora_alpha = lora_alpha
        self.device = device if device != "auto" else (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.processor = None
        self.model = None

    def load_model(self):
        """تحميل النموذج والمعالج."""
        if self.processor is None or self.model is None:
            try:
                self.processor = TrOCRProcessor.from_pretrained(self.model_name)
                self.model = VisionEncoderDecoderModel.from_pretrained(self.model_name)

                # نقل النموذج إلى الجهاز
                self.model.to(self.device)

                logger.info(f"تم تحميل النموذج: {self.model_name} على الجهاز {self.device}")
            except Exception as e:
                logger.error(f"فشل تحميل النموذج {self.model_name}: {e}")
                raise

    def apply_lora(self):
        """تطبيق LoRA على النموذج."""
        if not self.use_lora or self.model is None:
            return

        try:
            peft_config = LoraConfig(
                task_type=TaskType.SEQ_2_SEQ_LM,
                inference_mode=False,
                r=self.lora_r,
                lora_alpha=self.lora_alpha,
                lora_dropout=0.1,
                target_modules=["encoder.layer.0.attention.query_key_value"],
            )

            self.model = get_peft_model(self.model, peft_config)
            logger.info("تم تطبيق LoRA على النموذج")
        except Exception as e:
            logger.error(f"فشل تطبيق LoRA: {e}")
            raise

    def prepare_dataset(
        self,
        images: List[Union[str, Path]],
        texts: List[str]
    ) -> Dataset:
        """
        إعداد مجموعة البيانات للتدريب.

        Args:
            images: قائمة مسارات الصور.
            texts: قائمة النصوص.

        Returns:
            Dataset: مجموعة البيانات الجاهزة.
        """
        if self.processor is None:
            self.load_model()

        # معالج الصور
        from PIL import Image
        processed_images = []
        for img_path in images:
            try:
                img = Image.open(img_path)
                processed_images.append(img)
            except Exception as e:
                logger.error(f"فشل تحميل الصورة {img_path}: {e}")

        if not processed_images:
            raise ValueError("لا توجد صور صالحة")

        pixel_values = self.processor(processed_images, return_tensors="pt").pixel_values

        # معالج النصوص
        labels = self.processor(texts, return_tensors="pt").input_ids

        # إنشاء Dataset
        dataset = Dataset.from_dict({
            "pixel_values": pixel_values,
            "labels": labels,
        })

        return dataset

    def train(
        self,
        train_images: List[Union[str, Path]],
        train_texts: List[str],
        val_images: Optional[List[Union[str, Path]]] = None,
        val_texts: Optional[List[str]] = None,
        epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 5e-5,
        model_name: str = "trocr_ar_finetuned",
        save_model: bool = True
    ) -> Path:
        """
        تدريب النموذج على بيانات مدخلة.

        Args:
            train_images: قائمة الصور التدريبية.
            train_texts: قائمة النصوص التدريبية.
            val_images: قائمة الصور التحققية (اختياري).
            val_texts: قائمة النصوص التحققية (اختياري).
            epochs: عدد العصور.
            batch_size: حجم الدفعة.
            learning_rate: معدل التعلم.
            model_name: اسم النموذج المخرج.
            save_model: حفظ النموذج (افتراضي: True).

        Returns:
            Path: مسار النموذج المدرب.
        """
        self.load_model()
        self.apply_lora()

        # إعداد مجموعة البيانات
        train_dataset = self.prepare_dataset(train_images, train_texts)
        val_dataset = None
        if val_images and val_texts:
            val_dataset = self.prepare_dataset(val_images, val_texts)

        # إعداد معلمات التدريب
        training_args = Seq2SeqTrainingArguments(
            output_dir=self.output_dir / model_name,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            num_train_epochs=epochs,
            evaluation_strategy="epoch" if val_dataset else "no",
            save_strategy="epoch",
            logging_dir=self.output_dir / "logs" / model_name,
            logging_steps=10,
            learning_rate=learning_rate,
            warmup_steps=500,
            weight_decay=0.01,
            fp16=torch.cuda.is_available(),
            report_to="none",
            save_total_limit=2,
        )

        # إعداد المدرب
        trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            processor=self.processor,
        )

        # تدريب النموذج
        logger.info("جاري تدريب النموذج...")
        trainer.train()

        # حفظ النموذج
        if save_model:
            output_path = self.output_dir / model_name
            self.model.save_pretrained(str(output_path))
            self.processor.save_pretrained(str(output_path))
            logger.info(f"تم حفظ النموذج المدرب في: {output_path}")
            return output_path

        return self.output_dir / model_name

    def fine_tune_from_directory(
        self,
        train_dir: Union[str, Path],
        val_dir: Optional[Union[str, Path]] = None,
        epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 5e-5,
        model_name: str = "trocr_ar_finetuned",
        image_extensions: List[str] = [".png", ".jpg", ".jpeg"],
        text_extension: str = ".txt"
    ) -> Path:
        """
        تدريب النموذج على بيانات من مجلد.

        Args:
            train_dir: مجلد يحتوي على صور ونصوص تدريبية.
            val_dir: مجلد يحتوي على صور ونصوص تحققية (اختياري).
            epochs: عدد العصور.
            batch_size: حجم الدفعة.
            learning_rate: معدل التعلم.
            model_name: اسم النموذج المخرج.
            image_extensions: امتدادات الصور المدعومة.
            text_extension: امتداد ملفات النصوص.

        Returns:
            Path: مسار النموذج المدرب.
        """
        train_dir = Path(train_dir)
        train_images = []
        train_texts = []

        # تحميل بيانات التدريب
        for ext in image_extensions:
            for img_path in train_dir.glob(f"*{ext}"):
                txt_path = img_path.with_suffix(text_extension)
                if txt_path.exists():
                    try:
                        train_images.append(img_path)
                        with open(txt_path, "r", encoding="utf-8") as f:
                            train_texts.append(f.read().strip())
                    except Exception as e:
                        logger.error(f"فشل تحميل الصورة {img_path}: {e}")

        # تحميل بيانات التحقق (إذا كانت متاحة)
        val_images = []
        val_texts = []
        if val_dir:
            val_dir = Path(val_dir)
            for ext in image_extensions:
                for img_path in val_dir.glob(f"*{ext}"):
                    txt_path = img_path.with_suffix(text_extension)
                    if txt_path.exists():
                        try:
                            val_images.append(img_path)
                            with open(txt_path, "r", encoding="utf-8") as f:
                                val_texts.append(f.read().strip())
                        except Exception as e:
                            logger.error(f"فشل تحميل الصورة {img_path}: {e}")

        return self.train(
            train_images=train_images,
            train_texts=train_texts,
            val_images=val_images,
            val_texts=val_texts,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            model_name=model_name,
        )

    def fine_tune_from_database(
        self,
        db_path: Union[str, Path],
        language: str = "ar",
        limit: int = 1000,
        epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 5e-5,
        model_name: str = "trocr_ar_finetuned"
    ) -> Path:
        """
        تدريب النموذج على بيانات من قاعدة بيانات Active Learning.

        Args:
            db_path: مسار قاعدة البيانات.
            language: لغة البيانات.
            limit: الحد الأقصى لعدد البيانات.
            epochs: عدد العصور.
            batch_size: حجم الدفعة.
            learning_rate: معدل التعلم.
            model_name: اسم النموذج المخرج.

        Returns:
            Path: مسار النموذج المدرب.
        """
        from .active_learning import ActiveLearningDB

        db = ActiveLearningDB(db_path)
        training_data = db.get_training_data(
            language=language,
            limit=limit,
            min_confidence=0.7
        )

        if not training_data:
            raise ValueError(f"لا توجد بيانات تدريب للغة {language}")

        train_images = []
        train_texts = []

        for data in training_data:
            if "image_path" in data and data["image_path"]:
                train_images.append(data["image_path"])
                train_texts.append(data["corrected_text"])

        return self.train(
            train_images=train_images,
            train_texts=train_texts,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            model_name=model_name,
        )

    def evaluate(
        self,
        test_images: List[Union[str, Path]],
        test_texts: List[str],
        batch_size: int = 4
    ) -> Dict:
        """
        تقييم النموذج على بيانات اختبار.

        Args:
            test_images: قائمة الصور الاختبارية.
            test_texts: قائمة النصوص الاختبارية.
            batch_size: حجم الدفعة.

        Returns:
            Dict: نتائج التقييم.
        """
        self.load_model()

        try:
            from datasets import Dataset
            from evaluate import evaluator

            # إعداد مجموعة البيانات
            test_dataset = self.prepare_dataset(test_images, test_texts)

            # التقييم
            eval_result = evaluator("rouge")(model=self.model, dataset=test_dataset)

            return {
                "rouge1": eval_result["rouge1"],
                "rouge2": eval_result["rouge2"],
                "rougeL": eval_result["rougeL"],
                "rougeLsum": eval_result["rougeLsum"],
            }
        except Exception as e:
            logger.error(f"فشل التقييم: {e}")
            return {"error": str(e)}
