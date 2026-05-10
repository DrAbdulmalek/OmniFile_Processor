#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/learning/online_learner.py
==============================================

نظام تعلم فوري من تصحيحات المستخدم.
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from typing import List, Dict, Optional, Callable
import json
import time
from collections import deque

import numpy as np
import cv2
from PIL import Image
from transformers import (
    TrOCRProcessor, 
    VisionEncoderDecoderModel,
    get_linear_schedule_with_warmup
)


class CorrectionDataset(Dataset):
    """مجموعة بيانات التصحيحات."""
    
    def __init__(
        self,
        corrections: List[Dict],
        processor: TrOCRProcessor,
        max_length: int = 128
    ):
        self.corrections = corrections
        self.processor = processor
        self.max_length = max_length
    
    def __len__(self):
        return len(self.corrections)
    
    def __getitem__(self, idx):
        item = self.corrections[idx]
        
        # تحميل الصورة
        image = item['image']
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # معالجة
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze()
        
        # معالجة النص
        labels = self.processor.tokenizer(
            item['corrected_text'],
            padding="max_length",
            max_length=self.max_length,
            truncation=True,
            return_tensors="pt"
        ).input_ids.squeeze()
        
        # استبدال padding بـ -100 للتجاهل
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        
        return {
            'pixel_values': pixel_values,
            'labels': labels,
            'original_text': item['original_text'],
            'corrected_text': item['corrected_text']
        }


class OnlineLearner:
    """
    متعلم فوري يتحسن من كل تصحيح.
    
    يستخدم تقنيات:
    - Gradient Accumulation للتحديثات الصغيرة
    - Experience Replay للاستمرار
    - EWC (Elastic Weight Consolidation) لعدم نسيان القديم
    """
    
    def __init__(
        self,
        base_model: str = "microsoft/trocr-large-handwritten",
        device: str = "auto",
        learning_rate: float = 5e-5,
        batch_size: int = 4,
        memory_size: int = 1000,
        ewc_lambda: float = 100.0
    ):
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() and device == "auto" else device
        )
        
        # النموذج الأساسي
        self.processor = TrOCRProcessor.from_pretrained(base_model)
        self.model = VisionEncoderDecoderModel.from_pretrained(base_model)
        self.model.to(self.device)
        
        # إعدادات التدريب
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        
        # ذاكرة التجارب
        self.memory = deque(maxlen=memory_size)
        self.ewc_lambda = ewc_lambda
        
        # حالة EWC
        self.ewc_params = {}  # {param_name: (mean, fisher)}
        self.previous_tasks = []
        
        # إحصائيات
        self.total_corrections = 0
        self.training_steps = 0
    
    def add_correction(self, correction: Dict):
        """
        إضافة تصحيح للذاكرة.
        
        Args:
            correction: {
                'image': np.ndarray أو PIL.Image,
                'original_text': str,
                'corrected_text': str,
                'confidence_before': float,
                'timestamp': str (optional)
            }
        """
        self.memory.append(correction)
        self.total_corrections += 1
        
        # حفظ فوري للذاكرة
        self._save_memory()
    
    def learn_from_corrections(
        self,
        corrections: Optional[List[Dict]] = None,
        epochs: int = 3,
        gradient_accumulation_steps: int = 4
    ) -> Dict:
        """
        تدريب فوري على التصحيحات.
        
        Args:
            corrections: قائمة تصحيحات (None = استخدم الذاكرة)
            epochs: عدد epochs
            gradient_accumulation_steps: خطوات تجميع gradient
        
        Returns:
            إحصائيات التدريب
        """
        corrections = corrections or list(self.memory)
        
        if len(corrections) < 2:
            return {'status': 'insufficient_data', 'count': len(corrections)}
        
        # إعداد البيانات
        dataset = CorrectionDataset(corrections, self.processor)
        dataloader = DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=0  # لتجنب مشاكل multiprocessing
        )
        
        # إعداد الأمثلية
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.learning_rate,
            weight_decay=0.01
        )
        
        total_steps = len(dataloader) * epochs // gradient_accumulation_steps
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=10,
            num_training_steps=total_steps
        )
        
        # تدريب
        self.model.train()
        total_loss = 0
        best_loss = float('inf')
        
        for epoch in range(epochs):
            epoch_loss = 0
            optimizer.zero_grad()
            
            for step, batch in enumerate(dataloader):
                # نقل للجهاز
                pixel_values = batch['pixel_values'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                # Forward
                outputs = self.model(
                    pixel_values=pixel_values,
                    labels=labels
                )
                
                loss = outputs.loss / gradient_accumulation_steps
                loss.backward()
                
                epoch_loss += loss.item() * gradient_accumulation_steps
                
                # تحديث weights
                if (step + 1) % gradient_accumulation_steps == 0:
                    # تطبيق EWC
                    if self.ewc_params:
                        ewc_loss = self._compute_ewc_loss()
                        ewc_loss.backward()
                    
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad()
                    
                    self.training_steps += 1
            
            avg_loss = epoch_loss / len(dataloader)
            total_loss += avg_loss
            
            print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")
            
            if avg_loss < best_loss:
                best_loss = avg_loss
        
        # تحديث EWC بعد التدريب
        self._update_ewc()
        
        # حفظ checkpoint
        self._save_checkpoint()
        
        return {
            'status': 'success',
            'epochs': epochs,
            'final_loss': best_loss,
            'total_corrections': self.total_corrections,
            'training_steps': self.training_steps
        }
    
    def _compute_ewc_loss(self) -> torch.Tensor:
        """حساب خسارة Elastic Weight Consolidation."""
        if not self.ewc_params:
            return torch.tensor(0.0).to(self.device)
        
        loss = 0.0
        for name, param in self.model.named_parameters():
            if name in self.ewc_params and param.requires_grad:
                mean, fisher = self.ewc_params[name]
                loss += (fisher * (param - mean) ** 2).sum()
        
        return self.ewc_lambda * loss
    
    def _update_ewc(self):
        """تحديث معاملات EWC."""
        self.model.eval()
        
        # حساب Fisher Information
        fisher_dict = {}
        mean_dict = {}
        
        # عينة من الذاكرة
        sample_size = min(100, len(self.memory))
        samples = list(self.memory)[-sample_size:]
        
        dataset = CorrectionDataset(samples, self.processor)
        dataloader = DataLoader(dataset, batch_size=4)
        
        for batch in dataloader:
            pixel_values = batch['pixel_values'].to(self.device)
            labels = batch['labels'].to(self.device)
            
            self.model.zero_grad()
            outputs = self.model(pixel_values=pixel_values, labels=labels)
            loss = outputs.loss
            loss.backward()
            
            for name, param in self.model.named_parameters():
                if param.grad is not None:
                    if name not in fisher_dict:
                        fisher_dict[name] = torch.zeros_like(param)
                        mean_dict[name] = param.data.clone()
                    
                    fisher_dict[name] += param.grad.data ** 2 / len(dataloader)
        
        # تحديث المخزن
        for name in fisher_dict:
            if name not in self.ewc_params:
                self.ewc_params[name] = (mean_dict[name], fisher_dict[name])
            else:
                # دمج مع القديم
                old_mean, old_fisher = self.ewc_params[name]
                self.ewc_params[name] = (
                    0.9 * old_mean + 0.1 * mean_dict[name],
                    0.9 * old_fisher + 0.1 * fisher_dict[name]
                )
    
    def predict_with_confidence(
        self,
        image: np.ndarray
    ) -> Dict:
        """
        التنبؤ مع حساب الثقة المحسّن.
        
        Args:
            image: صورة الكلمة
        
        Returns:
            {
                'text': str,
                'confidence': float,
                'is_reliable': bool
            }
        """
        self.model.eval()
        
        # معالجة
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)
        
        with torch.no_grad():
            # التوليد مع احتمالات
            outputs = self.model.generate(
                pixel_values,
                return_dict_in_generate=True,
                output_scores=True,
                max_length=128
            )
            
            # فك التشفير
            generated_text = self.processor.batch_decode(
                outputs.sequences,
                skip_special_tokens=True
            )[0]
            
            # حساب الثقة من الاحتمالات
            scores = torch.stack(outputs.scores, dim=1).softmax(-1)
            max_probs = scores.max(dim=-1).values
            
            # متوسط الثقة للرموز المولدة
            confidence = max_probs.mean().item()
            
            # تعديل الثقة بناءً على عدد التصحيحات
            # كلما زاد التعلم، زادت الثقة في التنبؤات
            experience_bonus = min(0.1, self.total_corrections / 10000)
            adjusted_confidence = min(1.0, confidence + experience_bonus)
        
        return {
            'text': generated_text.strip(),
            'confidence': adjusted_confidence,
            'is_reliable': adjusted_confidence > 0.85
        }
    
    def _save_memory(self, path: Optional[Path] = None):
        """حفظ ذاكرة التصحيحات."""
        path = path or Path("./correction_memory.jsonl")
        
        with open(path, 'w', encoding='utf-8') as f:
            for item in self.memory:
                # حفظ الصور كمسارات أو base64
                item_copy = item.copy()
                if isinstance(item_copy['image'], np.ndarray):
                    # حفظ مؤقت
                    img_path = Path(f"./correction_images/{item_copy.get('id', 'img')}.png")
                    img_path.parent.mkdir(exist_ok=True)
                    cv2.imwrite(str(img_path), item_copy['image'])
                    item_copy['image_path'] = str(img_path)
                    del item_copy['image']
                
                f.write(json.dumps(item_copy, ensure_ascii=False) + '\n')
    
    def load_memory(self, path: Path):
        """تحميل ذاكرة التصحيحات."""
        self.memory.clear()
        
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)
                
                # إعادة تحميل الصورة
                if 'image_path' in item:
                    item['image'] = cv2.imread(item['image_path'])
                
                self.memory.append(item)
                self.total_corrections += 1
    
    def _save_checkpoint(self, path: Optional[Path] = None):
        """حفظ checkpoint للنموذج."""
        path = path or Path(f"./checkpoints/online_learner_step_{self.training_steps}.pt")
        path.parent.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'processor_config': self.processor.to_json_string(),
            'ewc_params': self.ewc_params,
            'training_steps': self.training_steps,
            'total_corrections': self.total_corrections
        }, path)
        
        print(f"✅ Checkpoint saved: {path}")
    
    def load_checkpoint(self, path: Path):
        """تحميل checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.ewc_params = checkpoint.get('ewc_params', {})
        self.training_steps = checkpoint.get('training_steps', 0)
        self.total_corrections = checkpoint.get('total_corrections', 0)
        
        print(f"✅ Checkpoint loaded: {path}")
    
    def export_model(self, output_dir: Path):
        """تصدير النموذج المدرب."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # حفظ النموذج والمعالج
        self.model.save_pretrained(output_dir)
        self.processor.save_pretrained(output_dir)
        
        # حفظ الإحصائيات
        stats = {
            'training_steps': self.training_steps,
            'total_corrections': self.total_corrections,
            'memory_size': len(self.memory),
            'export_date': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(output_dir / 'training_stats.json', 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"✅ Model exported to: {output_dir}")
        
        return output_dir


class AdaptiveLearningPipeline:
    """
    خط أنابيب تعلم تكيفي كامل.
    
    يجمع بين:
    - جمع التصحيحات
    - التدريب الدوري
    - التقييم المستمر
    - النشر التلقائي
    """
    
    def __init__(
        self,
        segmenter,
        learner: OnlineLearner,
        min_corrections_for_training: int = 10,
        training_interval_minutes: int = 30
    ):
        self.segmenter = segmenter
        self.learner = learner
        self.min_corrections = min_corrections_for_training
        self.interval = training_interval_minutes
        
        self.pending_corrections = []
        self.last_training_time = time.time()
        self.is_training = False
        
        # Callbacks
        self.on_training_complete: Optional[Callable] = None
        self.on_model_updated: Optional[Callable] = None
    
    def process_user_correction(
        self,
        original_word,
        corrected_text: str,
        word_image: np.ndarray
    ):
        """
        معالجة تصحيح من المستخدم.
        
        Args:
            original_word: الكلمة الأصلية
            corrected_text: النص المصحح
            word_image: صورة الكلمة
        """
        # تجاهل إذا كان التصحيح مطابقاً
        original_text = original_word.text if hasattr(original_word, 'text') else str(original_word)
        
        if original_text == corrected_text:
            return
        
        correction = {
            'id': f"corr_{int(time.time() * 1000)}",
            'image': word_image,
            'original_text': original_text,
            'corrected_text': corrected_text,
            'confidence_before': original_word.confidence if hasattr(original_word, 'confidence') else 0,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # إضافة للمتعلم
        self.learner.add_correction(correction)
        self.pending_corrections.append(correction)
        
        # التحقق من الحاجة للتدريب
        self._check_and_trigger_training()
    
    def _check_and_trigger_training(self):
        """التحقق وبدء التدريب إذا لزم الأمر."""
        if self.is_training:
            return
        
        # عدد التصحيحات الكافي
        enough_corrections = len(self.pending_corrections) >= self.min_corrections
        
        # الوقت الكافي
        time_elapsed = (time.time() - self.last_training_time) / 60
        enough_time = time_elapsed >= self.interval
        
        if enough_corrections or (enough_time and self.pending_corrections):
            self._start_training()
    
    def _start_training(self):
        """بدء جلسة تدريب."""
        self.is_training = True
        print(f"🚀 Starting training with {len(self.pending_corrections)} corrections...")
        
        try:
            # تدريب
            stats = self.learner.learn_from_corrections(
                corrections=self.pending_corrections,
                epochs=3
            )
            
            # مسح القائمة المعلقة
            self.pending_corrections = []
            self.last_training_time = time.time()
            
            # استدعاء callback
            if self.on_training_complete:
                self.on_training_complete(stats)
            
            # نشر النموذج المحدث
            self._deploy_updated_model()
            
        except Exception as e:
            print(f"❌ Training failed: {e}")
        
        finally:
            self.is_training = False
    
    def _deploy_updated_model(self):
        """نشر النموذج المحدث."""
        # حفظ checkpoint
        checkpoint_dir = Path("./models/adaptive")
        self.learner.export_model(checkpoint_dir)
        
        # استدعاء callback
        if self.on_model_updated:
            self.on_model_updated(checkpoint_dir)
        
        print(f"✅ Model deployed: {checkpoint_dir}")
    
    def get_learning_stats(self) -> Dict:
        """الحصول على إحصائيات التعلم."""
        return {
            'total_corrections': self.learner.total_corrections,
            'pending_corrections': len(self.pending_corrections),
            'training_steps': self.learner.training_steps,
            'is_training': self.is_training,
            'last_training': time.strftime(
                '%Y-%m-%d %H:%M:%S',
                time.localtime(self.last_training_time)
            ),
            'memory_size': len(self.learner.memory)
        }
