"""
TrOCR Arabic/English Fine-tuning Pipeline
ضبط دقيق لـ TrOCR على الخط اليدوي العربي/الإنجليزي
"""
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Trainer, TrainingArguments
from datasets import Dataset
from typing import List, Optional
import torch
from PIL import Image


class ArabicTrOCRTrainer:
    """ضبط دقيق لـ TrOCR على الخط اليدوي العربي/الإنجليزي"""

    def __init__(self, model_name: str = "microsoft/trocr-base-handwritten",
                 output_dir: str = "models/trocr-arabic-custom"):
        self.processor = TrOCRProcessor.from_pretrained(model_name)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
        self.output_dir = output_dir
        self._setup_arabic_tokenizer()

    def _setup_arabic_tokenizer(self):
        """إضافة حروف عربية خاصة للـ tokenizer إذا لزم"""
        medical_tokens = ['<mg>', '<ml>', '<dose>', '<drug>', '<dx>']
        self.processor.tokenizer.add_special_tokens({'additional_special_tokens': medical_tokens})
        self.model.config.decoder_start_token_id = self.processor.tokenizer.cls_token_id
        self.model.config.pad_token_id = self.processor.tokenizer.pad_token_id
        # Resize embeddings for new tokens
        self.model.resize_token_embeddings(len(self.processor.tokenizer))

    def prepare_dataset(self, samples: List[dict]) -> Dataset:
        """تحويل عينات (صورة، نص) إلى Dataset جاهز للتدريب"""
        import cv2

        def preprocess(example):
            image = example['image']
            if isinstance(image, str):
                image = cv2.imread(image)
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            image_pil = Image.fromarray(image)

            encoding = self.processor(
                images=image_pil,
                text=example['label'],
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            return {
                'pixel_values': encoding['pixel_values'].squeeze(),
                'labels': encoding['labels'].squeeze()
            }

        return Dataset.from_list(samples).map(preprocess, remove_columns=['image', 'label'])

    def train(self, train_samples: List[dict], eval_samples: Optional[List[dict]] = None,
              epochs: int = 20, batch_size: int = 8, learning_rate: float = 5e-5):
        """تدريب النموذج على عينات المستخدم المصححة"""
        from pathlib import Path
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        train_dataset = self.prepare_dataset(train_samples)
        eval_dataset = self.prepare_dataset(eval_samples) if eval_samples else None

        training_args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            learning_rate=learning_rate,
            weight_decay=0.01,
            save_steps=500,
            eval_steps=200,
            logging_steps=50,
            load_best_model_at_end=True,
            metric_for_best_model='cer',
            push_to_hub=False,
            fp16=torch.cuda.is_available(),
            report_to='none'
        )

        def compute_metrics(eval_pred):
            from jiwer import cer
            logits, labels = eval_pred
            predictions = self.processor.batch_decode(logits, skip_special_tokens=True)
            references = self.processor.batch_decode(labels, skip_special_tokens=True)
            return {'cer': cer(references, predictions)}

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            compute_metrics=compute_metrics,
            tokenizer=self.processor.feature_extractor
        )

        trainer.train()
        trainer.save_model(self.output_dir)
        self.processor.save_pretrained(self.output_dir)

        return trainer.state.metrics if hasattr(trainer.state, 'metrics') else {}


# Singleton instance
_trainer_instance = None

def get_trainer(output_dir: str = "models/trocr-arabic-custom") -> ArabicTrOCRTrainer:
    """Get or create trainer singleton"""
    global _trainer_instance
    if _trainer_instance is None:
        _trainer_instance = ArabicTrOCRTrainer(output_dir=output_dir)
    return _trainer_instance
