#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
train_trocr_lora.py
==================

تدريب TrOCR مع LoRA للتعرف على النصوص اليدوية العربية.

الاستخدام:
    python train_trocr_lora.py --config configs/trocr_lora_arabic.yaml
    python train_trocr_lora.py --model-name microsoft/trocr-large-handwritten --dataset ./dataset

المؤلف: Dr. Abdulmalek Al-husseini
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch
import yaml
from PIL import Image
from torch.utils.data import Dataset, DataLoader

# Transformers & PEFT
from transformers import (
    TrOCRProcessor, 
    VisionEncoderDecoderModel,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    default_data_collator,
    EarlyStoppingCallback
)
from peft import LoraConfig, get_peft_model, TaskType

# التقييم
from datasets import load_metric

# ============================================================================
# إعدادات التسجيل
# ============================================================================

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# فئة البيانات المخصصة
# ============================================================================

class HTRDataset(Dataset):
    """مجموعة بيانات HTR المخصصة."""
    
    def __init__(
        self,
        data_path: Path,
        processor: TrOCRProcessor,
        max_target_length: int = 128,
        split: str = 'train'
    ):
        self.processor = processor
        self.max_target_length = max_target_length
        self.split = split
        
        # تحميل البيانات
        self.samples = self._load_data(data_path)
        logger.info(f"📊 {split}: {len(self.samples)} عينة")
    
    def _load_data(self, data_path: Path) -> List[Dict]:
        """تحميل البيانات من التنسيق المختلف."""
        samples = []
        
        if data_path.suffix == '.lmdb':
            # LMDB format
            import lmdb
            import pickle
            
            env = lmdb.open(str(data_path), readonly=True)
            with env.begin() as txn:
                n = int(txn.get(b'__len__'))
                for i in range(n):
                    key = f"{i:08d}".encode()
                    value = txn.get(key)
                    data = pickle.loads(value)
                    samples.append(data)
            env.close()
            
        elif data_path.suffix == '.jsonl':
            # JSON Lines
            with open(data_path, 'r', encoding='utf-8') as f:
                for line in f:
                    samples.append(json.loads(line))
                    
        elif data_path.suffix in ['.tsv', '.txt']:
            # TSV
            with open(data_path, 'r', encoding='utf-8') as f:
                next(f)  # تخطي العنوان
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) == 2:
                        samples.append({
                            'image_path': parts[0],
                            'text': parts[1]
                        })
        else:
            # HuggingFace Dataset
            from datasets import load_from_disk
            dataset = load_from_disk(str(data_path))
            for item in dataset:
                samples.append({
                    'image': item['image'],
                    'text': item['text']
                })
        
        return samples
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # قراءة الصورة
        if 'image' in sample:
            image = sample['image']
            if not isinstance(image, Image.Image):
                image = Image.fromarray(image).convert('RGB')
        else:
            image = Image.open(sample['image_path']).convert('RGB')
        
        # معالجة الصورة
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        
        # معالجة النص
        labels = self.processor.tokenizer(
            sample['text'],
            padding="max_length",
            max_length=self.max_target_length,
            truncation=True,
            return_tensors="pt"
        ).input_ids
        
        # استبدال padding token بـ -100 للتجاهل في الخسارة
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        
        return {
            "pixel_values": pixel_values.squeeze(),
            "labels": labels.squeeze()
        }


# ============================================================================
# دوال التقييم
# ============================================================================

def compute_metrics(pred, processor, config):
    """حساب مقاييس CER و WER."""
    labels_ids = pred.label_ids
    pred_ids = pred.predictions
    
    # فك التشفير
    pred_str = processor.batch_decode(pred_ids, skip_special_tokens=True)
    labels_ids[labels_ids == -100] = processor.tokenizer.pad_token_id
    label_str = processor.batch_decode(labels_ids, skip_special_tokens=True)
    
    # حساب CER
    cer_metric = load_metric("cer")
    cer = cer_metric.compute(predictions=pred_str, references=label_str)
    
    # حساب WER
    wer_metric = load_metric("wer")
    wer = wer_metric.compute(predictions=pred_str, references=label_str)
    
    # دقة الحرف
    correct_chars = sum(p == r for p, r in zip(pred_str, label_str))
    accuracy = correct_chars / len(pred_str) if pred_str else 0
    
    return {
        "cer": cer,
        "wer": wer,
        "accuracy": accuracy,
        "pred_samples": pred_str[:3] if pred_str else [],
        "label_samples": label_str[:3] if label_str else []
    }


# ============================================================================
# توسيع المفردات
# ============================================================================

def extend_vocabulary(model, processor, additional_chars: str):
    """إضافة أحرف عربية للمفردات."""
    tokenizer = processor.tokenizer
    
    # الحصول على المفردات الحالية
    vocab = tokenizer.get_vocab()
    new_tokens = []
    
    for char in additional_chars:
        if char not in vocab:
            new_tokens.append(char)
    
    if new_tokens:
        logger.info(f"➕ إضافة {len(new_tokens)} رمز جديد: {new_tokens[:10]}...")
        tokenizer.add_tokens(new_tokens)
        model.decoder.resize_token_embeddings(len(tokenizer))
    
    return model, processor


# ============================================================================
# الدالة الرئيسية للتدريب
# ============================================================================

def train(config_path: Optional[Path] = None, **kwargs):
    """التدريب الرئيسي."""
    
    # تحميل الإعدادات
    if config_path:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = _build_config_from_args(kwargs)
    
    # إعداد الجهاز
    device = torch.device(config.get('hardware', {}).get('device', 'cuda') if torch.cuda.is_available() else 'cpu')
    logger.info(f"🖥️  الجهاز: {device}")
    
    # تحميل المعالج والنموذج
    model_name = config['model']['base_model']
    logger.info(f"📥 تحميل النموذج: {model_name}")
    
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    
    # توسيع المفردات إن لزم
    if config['model'].get('extend_vocabulary', False):
        additional = config['model'].get('additional_chars', '')
        model, processor = extend_vocabulary(model, processor, additional)
    
    # إعداد LoRA
    if config['lora']['enabled']:
        logger.info("🔧 إعداد LoRA...")
        lora_config = LoraConfig(
            r=config['lora']['r'],
            lora_alpha=config['lora']['alpha'],
            target_modules=config['lora']['target_modules'],
            lora_dropout=config['lora']['dropout'],
            bias=config['lora']['bias'],
            task_type=TaskType(config['lora']['task_type'])
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
    
    # إعدادات التدريب
    training_args = Seq2SeqTrainingArguments(
        output_dir=config['export'].get('push_to_hub', {}).get('repo_id', './checkpoints').replace('/', '_'),
        num_train_epochs=config['training']['num_epochs'],
        per_device_train_batch_size=config['training']['per_device_batch_size'],
        per_device_eval_batch_size=config['training']['per_device_batch_size'],
        gradient_accumulation_steps=config['training']['gradient_accumulation_steps'],
        learning_rate=config['training']['learning_rate'],
        lr_scheduler_type=config['training']['lr_scheduler'],
        warmup_steps=config['training']['warmup_steps'],
        weight_decay=config['training']['weight_decay'],
        max_grad_norm=config['training']['max_grad_norm'],
        
        # التقييم
        eval_strategy=config['training']['eval_strategy'],
        eval_steps=config['training']['eval_steps'],
        
        # الحفظ
        save_strategy=config['training']['save_strategy'],
        save_steps=config['training']['save_steps'],
        save_total_limit=config['training']['save_total_limit'],
        load_best_model_at_end=config['training']['load_best_model_at_end'],
        metric_for_best_model=config['training']['metric_for_best_model'],
        greater_is_better=config['training']['greater_is_better'],
        
        # الأداء
        fp16=config['training']['fp16'],
        bf16=config['training']['bf16'],
        gradient_checkpointing=config['training']['gradient_checkpointing'],
        
        # التسجيل
        logging_steps=config['training']['logging_steps'],
        report_to=config['training']['report_to'],
        
        # أخرى
        remove_unused_columns=config['training']['remove_unused_columns'],
        predict_with_generate=True,
        generation_max_length=config['model']['generation']['max_length'],
        generation_num_beams=config['model']['generation']['num_beams'],
    )
    
    # تحميل البيانات
    data_config = config['data']
    train_dataset = HTRDataset(
        Path(data_config['train_path']), 
        processor,
        split='train'
    )
    eval_dataset = HTRDataset(
        Path(data_config['val_path']), 
        processor,
        split='val'
    )
    
    # إعداد المدرب
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=default_data_collator,
        compute_metrics=lambda p: compute_metrics(p, processor, config),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
    )
    
    # التدريب
    logger.info("🚀 بدء التدريب...")
    trainer.train()
    
    # التقييم النهائي
    logger.info("📊 التقييم النهائي...")
    metrics = trainer.evaluate()
    logger.info(f"📈 النتائج: {metrics}")
    
    # الحفظ
    output_dir = Path(training_args.output_dir) / 'final'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # حفظ النموذج
    if config['lora']['enabled']:
        model.save_pretrained(output_dir / 'lora_adapter')
        # دمج اختياري
        if config['export'].get('merge_and_unload', False):
            merged_model = model.merge_and_unload()
            merged_model.save_pretrained(output_dir / 'merged')
            processor.save_pretrained(output_dir / 'merged')
    
    processor.save_pretrained(output_dir)
    
    # تصدير ONNX
    if config['export'].get('export_onnx', False):
        _export_onnx(model, processor, output_dir, config)
    
    # دفع لـ Hub
    hub_config = config['export'].get('push_to_hub', {})
    if hub_config.get('enabled', False):
        model.push_to_hub(hub_config['repo_id'], private=hub_config.get('private', False))
        processor.push_to_hub(hub_config['repo_id'], private=hub_config.get('private', False))
    
    logger.info(f"✅ تم الحفظ في: {output_dir}")
    return metrics


def _export_onnx(model, processor, output_dir: Path, config: dict):
    """تصدير النموذج لـ ONNX."""
    try:
        import onnx
        from onnxruntime.quantization import quantize_dynamic, QuantType
        
        dummy_input = torch.randn(1, 3, 384, 384)
        onnx_path = output_dir / 'model.onnx'
        
        torch.onnx.export(
            model.encoder,
            dummy_input,
            onnx_path,
            input_names=['pixel_values'],
            output_names=['encoder_hidden_states'],
            dynamic_axes={
                'pixel_values': {0: 'batch_size'},
                'encoder_hidden_states': {0: 'batch_size'}
            },
            opset_version=config['export'].get('onnx_opset', 14)
        )
        
        # كمية
        if config['export'].get('quantize', {}).get('enabled', False):
            quantized_path = output_dir / 'model_quantized.onnx'
            quantize_dynamic(
                onnx_path,
                quantized_path,
                weight_type=QuantType.QInt8
            )
            logger.info(f"✅ ONNX Quantized: {quantized_path}")
        
    except Exception as e:
        logger.warning(f"⚠️  فشل تصدير ONNX: {e}")


def _build_config_from_args(kwargs: dict) -> dict:
    """بناء إعدادات من المعاملات."""
    return {
        'model': {
            'base_model': kwargs.get('model_name', 'microsoft/trocr-large-handwritten'),
            'generation': {'max_length': 128, 'num_beams': 4, 'early_stopping': True},
            'extend_vocabulary': kwargs.get('lang') == 'ar',
            'additional_chars': "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
        },
        'lora': {
            'enabled': True,
            'r': kwargs.get('lora_r', 16),
            'alpha': kwargs.get('lora_alpha', 32),
            'dropout': 0.05,
            'target_modules': ["q_proj", "v_proj", "k_proj", "o_proj"],
            'bias': "none",
            'task_type': "VISION_2_SEQ"
        },
        'training': {
            'num_epochs': kwargs.get('epochs', 10),
            'per_device_batch_size': kwargs.get('batch_size', 4),
            'gradient_accumulation_steps': 4,
            'learning_rate': kwargs.get('learning_rate', 1e-4),
            'lr_scheduler': 'cosine_with_restarts',
            'warmup_steps': 500,
            'weight_decay': 0.01,
            'max_grad_norm': 1.0,
            'optimizer': 'adamw_torch_fused',
            'eval_strategy': 'steps',
            'eval_steps': 500,
            'save_strategy': 'steps',
            'save_steps': 500,
            'save_total_limit': 3,
            'load_best_model_at_end': True,
            'metric_for_best_model': 'cer',
            'greater_is_better': False,
            'fp16': False,
            'bf16': True,
            'gradient_checkpointing': True,
            'logging_steps': 50,
            'report_to': ['tensorboard'],
            'remove_unused_columns': False
        },
        'data': {
            'train_path': kwargs.get('dataset', './dataset_prepared/train.lmdb'),
            'val_path': kwargs.get('dataset', './dataset_prepared/val.lmdb').replace('train', 'val'),
            'test_path': kwargs.get('dataset', './dataset_prepared/test.lmdb').replace('train', 'test'),
            'format': 'lmdb'
        },
        'export': {
            'merge_and_unload': True,
            'export_onnx': False,
            'push_to_hub': {'enabled': False}
        },
        'hardware': {
            'device': 'cuda',
            'dataloader_num_workers': 4
        }
    }


# ============================================================================
# الدالة الرئيسية
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="تدريب TrOCR مع LoRA")
    parser.add_argument('--config', type=Path, help='مسار ملف الإعدادات')
    parser.add_argument('--model-name', type=str, help='اسم النموذج الأساسي')
    parser.add_argument('--dataset', type=Path, help='مسار البيانات')
    parser.add_argument('--output-dir', type=Path, help='مجلد الإخراج')
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--lora-r', type=int, default=16)
    parser.add_argument('--lora-alpha', type=int, default=32)
    parser.add_argument('--lang', type=str, default='ar')
    
    args = parser.parse_args()
    
    # التدريب
    kwargs = {k: v for k, v in vars(args).items() if v is not None}
    metrics = train(config_path=args.config, **kwargs)
    
    print("\n" + "=" * 60)
    print("✅ تم الانتهاء من التدريب!")
    print(f"📈 CER: {metrics.get('eval_cer', 'N/A')}")
    print(f"📈 WER: {metrics.get('eval_wer', 'N/A')}")
    print("=" * 60)


if __name__ == '__main__':
    main()
