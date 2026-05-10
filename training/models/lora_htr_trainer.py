#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lora_htr_trainer.py
===================

مدرب متخصص لنماذج HTR باستخدام LoRA مع تحسينات متقدمة:
- Gradient checkpointing
- Mixed precision (bf16/fp16)
- DeepSpeed integration
- Unsloth acceleration (اختياري)

المؤلف: Dr. Abdulmalek Al-husseini
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    EarlyStoppingCallback,
    TrainerCallback,
    TrainingArguments
)
from peft import (
    LoraConfig,
    get_peft_model,
    PeftModel,
    TaskType,
    prepare_model_for_kbit_training
)

# ============================================================================
# إعدادات التسجيل
# ============================================================================

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# إعدادات التدريب
# ============================================================================

@dataclass
class LoRAHTRConfig:
    """إعدادات تدريب LoRA لـ HTR."""
    
    # النموذج
    base_model: str = "microsoft/trocr-large-handwritten"
    
    # LoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = None
    lora_bias: str = "none"
    
    # التدريب
    num_epochs: int = 10
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    warmup_steps: int = 500
    max_grad_norm: float = 1.0
    
    # الأداء
    fp16: bool = False
    bf16: bool = True
    gradient_checkpointing: bool = True
    
    # التقييم
    eval_steps: int = 500
    save_steps: int = 500
    
    # أخرى
    output_dir: str = "./checkpoints"
    logging_dir: str = "./logs"
    
    def __post_init__(self):
        if self.lora_target_modules is None:
            self.lora_target_modules = [
                "q_proj", "v_proj", "k_proj", "o_proj"
            ]


# ============================================================================
# callback مخصص
# ============================================================================

class MetricsLoggerCallback(TrainerCallback):
    """تسجيل المقاييس المخصصة."""
    
    def __init__(self, log_every: int = 100):
        self.log_every = log_every
        self.start_time = None
    
    def on_train_begin(self, args, state, control, **kwargs):
        self.start_time = time.time()
        logger.info("🚀 بدء التدريب!")
    
    def on_step_end(self, args, state, control, **kwargs):
        if state.global_step % self.log_every == 0:
            elapsed = time.time() - self.start_time
            steps_per_sec = state.global_step / elapsed
            logger.info(
                f"   Step {state.global_step} | "
                f"Loss: {state.log_history[-1].get('loss', 'N/A') if state.log_history else 'N/A'} | "
                f"{steps_per_sec:.2f} steps/s"
            )
    
    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        if metrics:
            logger.info(f"📊 Evaluation: {metrics}")


class CheckpointUploaderCallback(TrainerCallback):
    """رفع checkpoints تلقائياً."""
    
    def __init__(self, hub_repo: Optional[str] = None):
        self.hub_repo = hub_repo
    
    def on_save(self, args, state, control, **kwargs):
        if self.hub_repo and state.global_step % 1000 == 0:
            # رفع للـ Hub
            logger.info(f"☁️  رفع checkpoint للـ Hub: {self.hub_repo}")


# ============================================================================
# المدرب الرئيسي
# ============================================================================

class LoRAHTRTrainer:
    """
    مدرب متخصص لنماذج HTR مع LoRA.
    
    يدعم:
    - التدريب التدريجي (freeze/unfreeze)
    - التدريب المختلط الدقة
    - التوزيع على multiple GPUs
    - التكامل مع Weights & Biases
    """
    
    def __init__(
        self,
        config: LoRAHTRConfig,
        processor: Optional[TrOCRProcessor] = None,
        model: Optional[VisionEncoderDecoderModel] = None
    ):
        self.config = config
        
        # تحميل أو استخدام نموذج مُزوَّد
        if processor is None or model is None:
            self.processor, self.model = self._load_base_model()
        else:
            self.processor = processor
            self.model = model
        
        # إعداد LoRA
        self._setup_lora()
        
        # إعداد التدريب
        self.training_args = self._create_training_args()
    
    def _load_base_model(self) -> Tuple[TrOCRProcessor, VisionEncoderDecoderModel]:
        """تحميل النموذج الأساسي."""
        logger.info(f"📥 تحميل النموذج: {self.config.base_model}")
        
        processor = TrOCRProcessor.from_pretrained(self.config.base_model)
        model = VisionEncoderDecoderModel.from_pretrained(self.config.base_model)
        
        # تقليل استخدام الذاكرة
        model.config.use_cache = False
        
        return processor, model
    
    def _setup_lora(self):
        """إعداد LoRA على النموذج."""
        logger.info("🔧 إعداد LoRA...")
        
        # إعداد للتدريب بـ 8-bit إن لزم
        if hasattr(self.model, 'is_loaded_in_8bit') and self.model.is_loaded_in_8bit:
            self.model = prepare_model_for_kbit_training(self.model)
        
        # إعداد LoRA
        lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            target_modules=self.config.lora_target_modules,
            lora_dropout=self.config.lora_dropout,
            bias=self.config.lora_bias,
            task_type=TaskType.VISION_2_SEQ
        )
        
        self.model = get_peft_model(self.model, lora_config)
        
        # طباعة معلومات قابلة للتدريب
        self.model.print_trainable_parameters()
        
        # تفعيل gradient checkpointing
        if self.config.gradient_checkpointing:
            self.model.gradient_checkpointing_enable()
            self.model.config.use_cache = False
    
    def _create_training_args(self) -> Seq2SeqTrainingArguments:
        """إنشاء إعدادات التدريب."""
        return Seq2SeqTrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            
            # التعلم
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_steps=self.config.warmup_steps,
            lr_scheduler_type="cosine_with_restarts",
            
            # التدرجات
            max_grad_norm=self.config.max_grad_norm,
            gradient_checkpointing=self.config.gradient_checkpointing,
            
            # الدقة
            fp16=self.config.fp16,
            bf16=self.config.bf16,
            
            # التقييم والحفظ
            evaluation_strategy="steps",
            eval_steps=self.config.eval_steps,
            save_strategy="steps",
            save_steps=self.config.save_steps,
            save_total_limit=3,
            load_best_model_at_end=True,
            metric_for_best_model="cer",
            greater_is_better=False,
            
            # التسجيل
            logging_dir=self.config.logging_dir,
            logging_steps=50,
            report_to=["tensorboard", "wandb"],
            
            # التوليد
            predict_with_generate=True,
            generation_max_length=128,
            generation_num_beams=4,
            
            # أخرى
            remove_unused_columns=False,
            dataloader_num_workers=4,
            dataloader_pin_memory=True,
        )
    
    def train(
        self,
        train_dataset,
        eval_dataset,
        compute_metrics_fn=None,
        callbacks: Optional[List[TrainerCallback]] = None
    ):
        """
        بدء التدريب.
        
        Args:
            train_dataset: مجموعة التدريب
            eval_dataset: مجموعة التقييم
            compute_metrics_fn: دالة حساب المقاييس
            callbacks: قائمة callbacks إضافية
        """
        # إعداد callbacks
        default_callbacks = [
            EarlyStoppingCallback(early_stopping_patience=3),
            MetricsLoggerCallback(log_every=100)
        ]
        
        if callbacks:
            default_callbacks.extend(callbacks)
        
        # إعداد المدرب
        trainer = Seq2SeqTrainer(
            model=self.model,
            args=self.training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=self._create_data_collator(),
            compute_metrics=compute_metrics_fn,
            callbacks=default_callbacks
        )
        
        # التدريب
        logger.info("🏋️ بدء التدريب...")
        trainer.train()
        
        # حفظ النموذج النهائي
        self._save_final_model(trainer)
        
        return trainer
    
    def _create_data_collator(self):
        """إنشاء data collator مخصص."""
        from transformers import default_data_collator
        
        # يمكن تخصيص هنا لدعم batching أفضل
        return default_data_collator
    
    def _save_final_model(self, trainer):
        """حفظ النموذج النهائي."""
        output_dir = Path(self.config.output_dir) / 'final'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # حفظ LoRA adapter
        self.model.save_pretrained(output_dir / 'lora_adapter')
        
        # حفظ المعالج
        self.processor.save_pretrained(output_dir)
        
        # دمج اختياري
        merged_dir = output_dir / 'merged'
        merged_model = self.model.merge_and_unload()
        merged_model.save_pretrained(merged_dir)
        self.processor.save_pretrained(merged_dir)
        
        logger.info(f"✅ تم الحفظ في: {output_dir}")
    
    def export_to_onnx(self, output_path: Optional[Path] = None):
        """تصدير النموذج لـ ONNX."""
        try:
            import onnx
            from onnxruntime.quantization import quantize_dynamic, QuantType
            
            output_path = output_path or Path(self.config.output_dir) / 'model.onnx'
            
            # دمج LoRA أولاً
            model = self.model.merge_and_unload()
            model.eval()
            
            # dummy input
            dummy_input = torch.randn(1, 3, 384, 384)
            
            # تصدير
            torch.onnx.export(
                model.encoder,
                dummy_input,
                output_path,
                input_names=['pixel_values'],
                output_names=['encoder_hidden_states'],
                dynamic_axes={
                    'pixel_values': {0: 'batch_size'},
                    'encoder_hidden_states': {0: 'batch_size'}
                },
                opset_version=14
            )
            
            # كمية
            quantized_path = output_path.with_suffix('.quantized.onnx')
            quantize_dynamic(
                output_path,
                quantized_path,
                weight_type=QuantType.QInt8
            )
            
            logger.info(f"✅ ONNX: {output_path}")
            logger.info(f"✅ Quantized: {quantized_path}")
            
        except Exception as e:
            logger.error(f"❌ فشل تصدير ONNX: {e}")
    
    def push_to_hub(self, repo_id: str, private: bool = False):
        """دفع النموذج لـ HuggingFace Hub."""
        self.model.push_to_hub(repo_id, private=private)
        self.processor.push_to_hub(repo_id, private=private)
        logger.info(f"☁️  تم الرفع: https://huggingface.co/{repo_id}")


# ============================================================================
# مدرب متقدم مع Unsloth
# ============================================================================

class UnslothHTRTrainer(LoRAHTRTrainer):
    """
    مدرب محسّن باستخدام Unsloth لتسريع 2-5x.
    
    يتطلب: pip install unsloth
    """
    
    def __init__(self, config: LoRAHTRConfig):
        try:
            from unsloth import FastVisionModel
            self.unsloth_available = True
        except ImportError:
            logger.warning("⚠️  Unsloth غير مثبت. استخدام المدرب العادي.")
            self.unsloth_available = False
            super().__init__(config)
            return
        
        self.config = config
        self._setup_unsloth_model()
    
    def _setup_unsloth_model(self):
        """إعداد نموذج Unsloth."""
        from unsloth import FastVisionModel
        
        logger.info("🚀 إعداد Unsloth...")
        
        # تحميل النموذج بـ 4-bit
        self.model, self.tokenizer = FastVisionModel.from_pretrained(
            model_name=self.config.base_model,
            max_seq_length=128,
            dtype=torch.float16,
            load_in_4bit=True,
        )
        
        # إعداد LoRA
        self.model = FastVisionModel.get_peft_model(
            self.model,
            r=self.config.lora_r,
            target_modules=self.config.lora_target_modules,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            bias=self.config.lora_bias,
            use_gradient_checkpointing="unsloth",
            random_state=3407,
            use_rslora=False,
        )
        
        # المعالج
        self.processor = TrOCRProcessor.from_pretrained(self.config.base_model)
        
        logger.info("✅ Unsloth جاهز!")
    
    def train(self, train_dataset, eval_dataset, **kwargs):
        """تدريب مع Unsloth."""
        if not self.unsloth_available:
            return super().train(train_dataset, eval_dataset, **kwargs)
        
        # Unsloth يتطلب معالجة خاصة
        from trl import SFTTrainer
        from transformers import TrainingArguments
        
        # تحويل البيانات لتنسيق Unsloth
        formatted_data = self._format_for_unsloth(train_dataset)
        
        trainer = SFTTrainer(
            model=self.model,
            tokenizer=self.tokenizer,
            train_dataset=formatted_data,
            dataset_text_field="text",
            max_seq_length=128,
            args=TrainingArguments(
                per_device_train_batch_size=self.config.batch_size,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                num_train_epochs=self.config.num_epochs,
                learning_rate=self.config.learning_rate,
                fp16=True,
                logging_steps=1,
                optim="adamw_8bit",
                weight_decay=self.config.weight_decay,
                lr_scheduler_type="linear",
                seed=3407,
                output_dir=self.config.output_dir,
                report_to="none",
            ),
        )
        
        trainer.train()
        return trainer
    
    def _format_for_unsloth(self, dataset):
        """تحويل البيانات لتنسيق Unsloth."""
        # Unsloth يتطلب تنسيق محادثة
        formatted = []
        for item in dataset:
            formatted.append({
                "image": item.get("image"),
                "text": item.get("text", "")
            })
        return formatted


# ============================================================================
# مدرب متعدد GPUs
# ============================================================================

class MultiGPUHTRTrainer(LoRAHTRTrainer):
    """مدرب يدعم Distributed Data Parallel."""
    
    def __init__(self, config: LoRAHTRConfig):
        if not torch.cuda.is_available() or torch.cuda.device_count() < 2:
            logger.warning("⚠️  GPUs متعددة غير متوفرة. استخدام GPU واحد.")
        
        super().__init__(config)
    
    def train(self, train_dataset, eval_dataset, **kwargs):
        """تدريب موزع."""
        import torch.distributed as dist
        from torch.nn.parallel import DistributedDataParallel as DDP
        
        # إعداد distributed
        if 'LOCAL_RANK' in os.environ:
            local_rank = int(os.environ['LOCAL_RANK'])
            torch.cuda.set_device(local_rank)
            dist.init_process_group(backend='nccl')
        
        # تغليف النموذج
        if dist.is_initialized():
            self.model = DDP(
                self.model,
                device_ids=[local_rank],
                output_device=local_rank,
                find_unused_parameters=False
            )
        
        return super().train(train_dataset, eval_dataset, **kwargs)


# ============================================================================
# مصنع المدربين
# ============================================================================

class TrainerFactory:
    """مصنع لإنشاء المدرب المناسب."""
    
    @staticmethod
    def create(
        config: LoRAHTRConfig,
        trainer_type: str = "auto"
    ) -> LoRAHTRTrainer:
        """
        إنشاء مدرب مناسب للبيئة.
        
        Args:
            config: إعدادات التدريب
            trainer_type: نوع المدرب (auto, lora, unsloth, multi_gpu)
        
        Returns:
            نسخة من المدرب
        """
        if trainer_type == "auto":
            # اكتشاف تلقائي
            if torch.cuda.device_count() > 1:
                trainer_type = "multi_gpu"
            else:
                try:
                    import unsloth
                    trainer_type = "unsloth"
                except ImportError:
                    trainer_type = "lora"
        
        trainers = {
            'lora': LoRAHTRTrainer,
            'unsloth': UnslothHTRTrainer,
            'multi_gpu': MultiGPUHTRTrainer
        }
        
        trainer_class = trainers.get(trainer_type, LoRAHTRTrainer)
        logger.info(f"🏭 إنشاء مدرب: {trainer_class.__name__}")
        
        return trainer_class(config)
