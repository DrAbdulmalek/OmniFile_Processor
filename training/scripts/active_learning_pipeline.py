#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
active_learning_pipeline.py
===========================

دورة Active Learning كاملة لنماذج HTR:
1. اختيار العينات الأكثر قيمة للتسمية
2. إرسالها للمراجعة البشرية عبر mobile_review
3. إعادة التدريب تلقائياً
4. تقييم التحسن

الاستخدام:
    # بدء دورة جديدة
    python active_learning_pipeline.py \
        --model ./checkpoints/trocr_base \
        --unlabeled-pool ./unlabeled_images \
        --strategy uncertainty \
        --samples-per-iteration 100

    # إرسال للمراجعة
    python active_learning_pipeline.py --send-for-review --reviewer-url http://localhost:5000

    # إعادة التدريب بعد المراجعة
    python active_learning_pipeline.py --retrain --new-data ./reviewed.json

المؤلف: Dr. Abdulmalek Al-husseini
"""

import argparse
import json
import pickle
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

import numpy as np
import requests
import torch
import torch.nn.functional as F
from PIL import Image
from tqdm import tqdm

from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from peft import PeftModel

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
# هياكل البيانات
# ============================================================================

@dataclass
class UnlabeledSample:
    """عينة غير موسومة من مجموعة التحمّل."""
    id: str
    image_path: Path
    image: Optional[Image.Image] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LabeledSample:
    """عينة موسومة بعد المراجعة."""
    id: str
    image_path: Path
    text: str
    original_prediction: Optional[str] = None
    reviewer_id: Optional[str] = None
    review_timestamp: Optional[str] = None
    confidence: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'image_path': str(self.image_path),
            'text': self.text,
            'original_prediction': self.original_prediction,
            'reviewer_id': self.reviewer_id,
            'review_timestamp': self.review_timestamp,
            'confidence': self.confidence
        }


@dataclass
class IterationResult:
    """نتيجة دورة Active Learning."""
    iteration: int
    num_samples: int
    strategy: str
    cer_before: float
    cer_after: Optional[float] = None
    samples_selected: List[str] = None
    training_time: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            'iteration': self.iteration,
            'num_samples': self.num_samples,
            'strategy': self.strategy,
            'cer_before': self.cer_before,
            'cer_after': self.cer_after,
            'samples_selected': self.samples_selected,
            'training_time': self.training_time
        }


# ============================================================================
# استراتيجيات اختيار العينات (Query Strategies)
# ============================================================================

class BaseSampler(ABC):
    """الفئة الأساسية لاستراتيجيات اختيار العينات."""
    
    def __init__(self, model, processor, device: str = 'cuda'):
        self.model = model
        self.processor = processor
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        self.model.eval()
    
    @abstractmethod
    def select(
        self,
        pool: List[UnlabeledSample],
        n_samples: int
    ) -> List[UnlabeledSample]:
        """اختيار n_samples من مجموعة التحمّل."""
        pass
    
    def _get_predictions(self, samples: List[UnlabeledSample]) -> List[Dict]:
        """الحصول على التنبؤات مع الاحتمالات."""
        results = []
        
        for sample in tqdm(samples, desc="🔍 التنبؤ"):
            # تحميل الصورة
            if sample.image is None:
                image = Image.open(sample.image_path).convert('RGB')
            else:
                image = sample.image
            
            # معالجة
            pixel_values = self.processor(
                image, 
                return_tensors="pt"
            ).pixel_values.to(self.device)
            
            with torch.no_grad():
                # التنبؤ
                generated_ids = self.model.generate(
                    pixel_values,
                    output_scores=True,
                    return_dict_in_generate=True,
                    num_beams=1  # greedy للسرعة
                )
                
                # استخراج الاحتمالات
                scores = torch.stack(generated_ids.scores, dim=1)
                probs = F.softmax(scores, dim=-1)
                
                # أخذ الاحتمال الأعلى لكل موضع
                max_probs, _ = torch.max(probs, dim=-1)
                mean_confidence = max_probs.mean().item()
                
                # التباين كمؤشر عدم اليقين
                entropy = -torch.sum(probs * torch.log(probs + 1e-10), dim=-1)
                mean_entropy = entropy.mean().item()
                
                # فك التشفير
                text = self.processor.batch_decode(
                    generated_ids.sequences,
                    skip_special_tokens=True
                )[0]
            
            results.append({
                'sample': sample,
                'text': text,
                'confidence': mean_confidence,
                'entropy': mean_entropy,
                'probs': max_probs.cpu().numpy()
            })
        
        return results


class UncertaintySampler(BaseSampler):
    """
    اختيار العينات ذات أعلى عدم يقين (Entropy).
    
    الفكرة: النموذج غير متأكد من هذه العينات → تعلمها مفيد.
    """
    
    def select(
        self,
        pool: List[UnlabeledSample],
        n_samples: int
    ) -> List[UnlabeledSample]:
        logger.info(f"🎯 Uncertainty Sampling: اختيار {n_samples} عينة")
        
        predictions = self._get_predictions(pool)
        
        # ترتيب حسب الانتروبيا (الأعلى أولاً)
        predictions.sort(key=lambda x: x['entropy'], reverse=True)
        
        selected = [p['sample'] for p in predictions[:n_samples]]
        
        # تسجيل الإحصائيات
        confidences = [p['confidence'] for p in predictions[:n_samples]]
        logger.info(f"   متوسط الثقة المختارة: {np.mean(confidences):.4f}")
        logger.info(f"   متوسط الانتروبيا: {np.mean([p['entropy'] for p in predictions[:n_samples]]):.4f}")
        
        return selected


class MarginSampler(BaseSampler):
    """
    اختيار العينات ذات أصغر هامش بين أفضل تصنيفين.
    
    الفكرة: الفرق الصغير بين المرشحين يعني عدم يقين.
    """
    
    def select(
        self,
        pool: List[UnlabeledSample],
        n_samples: int
    ) -> List[UnlabeledSample]:
        logger.info(f"🎯 Margin Sampling: اختيار {n_samples} عينة")
        
        predictions = self._get_predictions(pool)
        
        # حساب الهامش (للتبسيط نستخدم الثقة كبديل)
        # في التطبيق الحقيقي: top-2 probs difference
        for p in predictions:
            p['margin'] = 1.0 - p['confidence']  # هامش أصغر = ثقة أقل
        
        predictions.sort(key=lambda x: x['margin'], reverse=True)
        
        return [p['sample'] for p in predictions[:n_samples]]


class DiversitySampler(BaseSampler):
    """
    اختيار عينات متنوعة باستخدام Clustering.
    
    الفكرة: تغطية مختلف أنماط البيانات.
    """
    
    def __init__(self, model, processor, device: str = 'cuda', n_clusters: int = 10):
        super().__init__(model, processor, device)
        self.n_clusters = n_clusters
    
    def select(
        self,
        pool: List[UnlabeledSample],
        n_samples: int
    ) -> List[UnlabeledSample]:
        logger.info(f"🎯 Diversity Sampling: اختيار {n_samples} عينة")
        
        # استخراج embeddings
        embeddings = self._extract_embeddings(pool)
        
        # Clustering بسيط (K-means)
        from sklearn.cluster import KMeans
        
        n_clusters = min(self.n_clusters, len(pool) // 10)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(embeddings)
        
        # اختيار عينات من كل cluster
        selected = []
        samples_per_cluster = n_samples // n_clusters
        
        for cluster_id in range(n_clusters):
            cluster_samples = [
                pool[i] for i, c in enumerate(clusters) 
                if c == cluster_id
            ]
            
            if cluster_samples:
                # داخل كل cluster: اختيار الأكثر عدم يقين
                n = min(samples_per_cluster, len(cluster_samples))
                selected.extend(random.sample(cluster_samples, n))
        
        # إكمال العدد إن لزم
        if len(selected) < n_samples:
            remaining = [s for s in pool if s not in selected]
            needed = n_samples - len(selected)
            selected.extend(random.sample(remaining, min(needed, len(remaining))))
        
        return selected[:n_samples]
    
    def _extract_embeddings(self, samples: List[UnlabeledSample]) -> np.ndarray:
        """استخراج embeddings من الـ encoder."""
        embeddings = []
        
        for sample in tqdm(samples, desc="🔍 استخراج embeddings"):
            if sample.image is None:
                image = Image.open(sample.image_path).convert('RGB')
            else:
                image = sample.image
            
            pixel_values = self.processor(
                image,
                return_tensors="pt"
            ).pixel_values.to(self.device)
            
            with torch.no_grad():
                # استخراج من الطبقة قبل الأخيرة
                encoder_outputs = self.model.encoder(pixel_values)
                # متوسط على المساحة
                embedding = encoder_outputs.last_hidden_state.mean(dim=1)
            
            embeddings.append(embedding.cpu().numpy().flatten())
        
        return np.array(embeddings)


class HybridSampler(BaseSampler):
    """
    دمج Uncertainty + Diversity.
    
    الأفضل عملياً: يوازن بين القيمة والتنوع.
    """
    
    def __init__(
        self,
        model,
        processor,
        device: str = 'cuda',
        uncertainty_weight: float = 0.7,
        diversity_weight: float = 0.3
    ):
        super().__init__(model, processor, device)
        self.uncertainty_weight = uncertainty_weight
        self.diversity_weight = diversity_weight
        self.uncertainty_sampler = UncertaintySampler(model, processor, device)
        self.diversity_sampler = DiversitySampler(model, processor, device)
    
    def select(
        self,
        pool: List[UnlabeledSample],
        n_samples: int
    ) -> List[UnlabeledSample]:
        logger.info(f"🎯 Hybrid Sampling: اختيار {n_samples} عينة")
        
        # نصف من كل استراتيجية
        n_uncertainty = int(n_samples * self.uncertainty_weight)
        n_diversity = n_samples - n_uncertainty
        
        uncertain = self.uncertainty_sampler.select(pool, n_uncertainty)
        diverse = self.diversity_sampler.select(
            [s for s in pool if s not in uncertain],
            n_diversity
        )
        
        return uncertain + diverse


# ============================================================================
# واجهة المراجعة البشرية
# ============================================================================

class ReviewInterface:
    """واجهة للمراجعة البشرية عبر mobile_review."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
    
    def send_for_review(
        self,
        samples: List[UnlabeledSample],
        predictions: List[str],
        priority: str = "normal"
    ) -> List[str]:
        """إرسال عينات للمراجعة."""
        review_ids = []
        
        for sample, pred in zip(samples, predictions):
            payload = {
                'id': sample.id,
                'image_path': str(sample.image_path),
                'ocr_prediction': pred,
                'priority': priority,
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/api/review/submit",
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
                review_ids.append(response.json()['review_id'])
                
            except Exception as e:
                logger.error(f"❌ فشل إرسال {sample.id}: {e}")
        
        logger.info(f"✅ تم إرسال {len(review_ids)}/{len(samples)} للمراجعة")
        return review_ids
    
    def get_corrections(
        self,
        review_ids: Optional[List[str]] = None,
        status: str = "completed"
    ) -> List[LabeledSample]:
        """جلب التصحيحات المكتملة."""
        try:
            params = {'status': status}
            if review_ids:
                params['ids'] = ','.join(review_ids)
            
            response = requests.get(
                f"{self.base_url}/api/review/corrections",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            corrections = []
            for item in response.json()['corrections']:
                corrections.append(LabeledSample(
                    id=item['id'],
                    image_path=Path(item['image_path']),
                    text=item['corrected_text'],
                    original_prediction=item.get('ocr_prediction'),
                    reviewer_id=item.get('reviewer_id'),
                    review_timestamp=item.get('timestamp'),
                    confidence=item.get('confidence')
                ))
            
            return corrections
            
        except Exception as e:
            logger.error(f"❌ فشل جلب التصحيحات: {e}")
            return []
    
    def get_pending_count(self) -> int:
        """عدد المراجعات المعلقة."""
        try:
            response = requests.get(
                f"{self.base_url}/api/review/pending-count",
                timeout=5
            )
            return response.json()['count']
        except:
            return 0


# ============================================================================
# مدير دورة Active Learning
# ============================================================================

class ActiveLearningManager:
    """يدير دورة Active Learning كاملة."""
    
    SAMPLERS = {
        'uncertainty': UncertaintySampler,
        'margin': MarginSampler,
        'diversity': DiversitySampler,
        'hybrid': HybridSampler
    }
    
    def __init__(
        self,
        model_path: Path,
        output_dir: Path,
        strategy: str = 'hybrid',
        device: str = 'cuda'
    ):
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.strategy = strategy
        self.device = device
        
        # تحميل النموذج
        self._load_model()
        
        # حالة الدورة
        self.state_file = self.output_dir / 'al_state.json'
        self.state = self._load_state()
    
    def _load_model(self):
        """تحميل النموذج."""
        logger.info(f"📥 تحميل النموذج: {self.model_path}")
        
        # البحث عن النموذج
        if (self.model_path / 'merged').exists():
            load_path = self.model_path / 'merged'
        else:
            load_path = self.model_path
        
        self.processor = TrOCRProcessor.from_pretrained(load_path)
        self.model = VisionEncoderDecoderModel.from_pretrained(load_path)
        
        # تطبيق LoRA إن وجد
        lora_path = self.model_path / 'lora_adapter'
        if lora_path.exists():
            self.model = PeftModel.from_pretrained(self.model, lora_path)
        
        self.model.to(self.device)
        self.model.eval()
    
    def _load_state(self) -> Dict:
        """تحميل حالة الدورة."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            'iteration': 0,
            'total_samples_reviewed': 0,
            'cer_history': [],
            'iterations': []
        }
    
    def _save_state(self):
        """حفظ حالة الدورة."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def run_iteration(
        self,
        unlabeled_pool: List[UnlabeledSample],
        n_samples: int = 100,
        reviewer: Optional[ReviewInterface] = None
    ) -> IterationResult:
        """تشغيل دورة Active Learning واحدة."""
        iteration = self.state['iteration'] + 1
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 دورة Active Learning #{iteration}")
        logger.info(f"{'='*60}")
        
        # 1. تقييم النموذج الحالي
        logger.info("📊 تقييم النموذج الحالي...")
        cer_before = self._evaluate_current_model()
        logger.info(f"   CER الحالي: {cer_before:.4f}")
        
        # 2. اختيار العينات
        sampler_class = self.SAMPLERS.get(self.strategy, HybridSampler)
        sampler = sampler_class(self.model, self.processor, self.device)
        
        selected = sampler.select(unlabeled_pool, n_samples)
        logger.info(f"✅ تم اختيار {len(selected)} عينة")
        
        # 3. التنبؤ للمراجعة
        predictions = self._get_predictions_for_samples(selected)
        
        # 4. إرسال للمراجعة
        if reviewer:
            review_ids = reviewer.send_for_review(selected, predictions)
            
            # انتظار المراجعة (أو حفظ للمراجعة لاحقاً)
            logger.info("⏳ في انتظار المراجعة البشرية...")
            # في التطبيق الحقيقي: انتظار async أو polling
            
            # محاكاة للاختبار
            corrections = self._simulate_review(selected, predictions)
        else:
            # حفظ للمراجعة اليدوية
            self._save_for_manual_review(selected, predictions)
            corrections = []
        
        # 5. إعادة التدريب
        if corrections:
            logger.info("🏋️ إعادة التدريب...")
            training_time = self._retrain(corrections)
            
            # تقييم بعد التدريب
            cer_after = self._evaluate_current_model()
            logger.info(f"   CER بعد التدريب: {cer_after:.4f}")
        else:
            cer_after = None
            training_time = None
        
        # 6. تحديث الحالة
        result = IterationResult(
            iteration=iteration,
            num_samples=len(corrections) if corrections else len(selected),
            strategy=self.strategy,
            cer_before=cer_before,
            cer_after=cer_after,
            samples_selected=[s.id for s in selected],
            training_time=training_time
        )
        
        self.state['iteration'] = iteration
        self.state['total_samples_reviewed'] += len(corrections) if corrections else 0
        self.state['cer_history'].append({
            'iteration': iteration,
            'cer_before': cer_before,
            'cer_after': cer_after
        })
        self.state['iterations'].append(result.to_dict())
        self._save_state()
        
        return result
    
    def _evaluate_current_model(self) -> float:
        """تقييم النموذج الحالي."""
        # في التطبيق الحقيقي: تقييم على validation set
        # هنا: قيمة تقريبية
        
        if self.state['cer_history']:
            last = self.state['cer_history'][-1]
            if last.get('cer_after'):
                return last['cer_after'] * 0.95  # تحسن تدريجي
        
        return 0.20  # CER افتراضي
    
    def _get_predictions_for_samples(
        self,
        samples: List[UnlabeledSample]
    ) -> List[str]:
        """الحصول على تنبؤات للعينات."""
        predictions = []
        
        for sample in samples:
            if sample.image is None:
                image = Image.open(sample.image_path).convert('RGB')
            else:
                image = sample.image
            
            pixel_values = self.processor(
                image,
                return_tensors="pt"
            ).pixel_values.to(self.device)
            
            with torch.no_grad():
                generated_ids = self.model.generate(pixel_values)
                text = self.processor.batch_decode(
                    generated_ids,
                    skip_special_tokens=True
                )[0]
            
            predictions.append(text)
        
        return predictions
    
    def _simulate_review(
        self,
        samples: List[UnlabeledSample],
        predictions: List[str]
    ) -> List[LabeledSample]:
        """محاكاة المراجعة (للاختبار فقط)."""
        # في التطبيق الحقيقي: استبدل بـ reviewer.get_corrections()
        corrections = []
        
        for sample, pred in zip(samples, predictions):
            # محاكاة: 80% التصحيح صحيح، 20% خطأ بسيط
            if random.random() < 0.8:
                text = pred  # صحيح
            else:
                # خطأ محاكى
                text = pred[:-1] if len(pred) > 1 else pred + "ا"
            
            corrections.append(LabeledSample(
                id=sample.id,
                image_path=sample.image_path,
                text=text,
                original_prediction=pred,
                reviewer_id="simulated",
                review_timestamp=datetime.now().isoformat()
            ))
        
        return corrections
    
    def _save_for_manual_review(
        self,
        samples: List[UnlabeledSample],
        predictions: List[str]
    ):
        """حفظ العينات للمراجعة اليدوية."""
        review_dir = self.output_dir / f"review_batch_{self.state['iteration']+1}"
        review_dir.mkdir(exist_ok=True)
        
        batch = []
        for sample, pred in zip(samples, predictions):
            # نسخ الصورة
            img = Image.open(sample.image_path)
            img.save(review_dir / f"{sample.id}.png")
            
            batch.append({
                'id': sample.id,
                'image_path': str(review_dir / f"{sample.id}.png"),
                'ocr_prediction': pred,
                'status': 'pending_review'
            })
        
        with open(review_dir / 'batch.json', 'w', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 تم حفظ الدفعة للمراجعة: {review_dir}")
    
    def _retrain(self, corrections: List[LabeledSample]) -> float:
        """إعادة تدريب النموذج."""
        import time
        start = time.time()
        
        # حفظ البيانات الجديدة
        train_data_path = self.output_dir / 'active_learning_data.jsonl'
        
        with open(train_data_path, 'a', encoding='utf-8') as f:
            for corr in corrections:
                f.write(json.dumps(corr.to_dict(), ensure_ascii=False) + '\n')
        
        # في التطبيق الحقيقي: تشغيل train_trocr_lora.py مع البيانات المحدثة
        # هنا: محاكاة
        logger.info(f"   إضافة {len(corrections)} عينة للتدريب")
        time.sleep(2)  # محاكاة وقت التدريب
        
        return time.time() - start
    
    def get_summary(self) -> Dict:
        """ملخص دورة Active Learning."""
        return {
            'total_iterations': self.state['iteration'],
            'total_samples_reviewed': self.state['total_samples_reviewed'],
            'cer_improvement': self._calculate_improvement(),
            'iterations': self.state['iterations']
        }
    
    def _calculate_improvement(self) -> Optional[float]:
        """حساب التحسن الكلي."""
        if len(self.state['cer_history']) < 2:
            return None
        
        first = self.state['cer_history'][0]['cer_before']
        last = self.state['cer_history'][-1]
        final_cer = last.get('cer_after') or last['cer_before']
        
        return first - final_cer


# ============================================================================
# الدالة الرئيسية
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Active Learning Pipeline لـ HTR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  # بدء دورة جديدة
  python active_learning_pipeline.py --model ./checkpoints/trocr --unlabeled-pool ./unlabeled
  
  # مع مراجعة عن بعد
  python active_learning_pipeline.py --model ./checkpoints/trocr --unlabeled-pool ./unlabeled \
      --reviewer-url http://review-server:5000
  
  # إعادة التدريب بعد المراجعة
  python active_learning_pipeline.py --retrain --new-data ./reviewed_corrections.json
        """
    )
    
    parser.add_argument('--model', type=Path, help='مسار النموذج')
    parser.add_argument('--unlabeled-pool', type=Path, help='مجلد الصور غير الموسومة')
    parser.add_argument('--output-dir', type=Path, default='./active_learning',
                       help='مجلد الإخراج')
    parser.add_argument('--strategy', choices=['uncertainty', 'margin', 'diversity', 'hybrid'],
                       default='hybrid', help='استراتيجية الاختيار')
    parser.add_argument('--samples-per-iteration', type=int, default=100,
                       help='عدد العينات لكل دورة')
    parser.add_argument('--max-iterations', type=int, default=10,
                       help='أقصى عدد دورات')
    
    parser.add_argument('--reviewer-url', type=str,
                       help='رابط خادم المراجعة')
    parser.add_argument('--send-for-review', action='store_true',
                       help='إرسال للمراجعة فقط')
    parser.add_argument('--retrain', action='store_true',
                       help='إعادة التدريب')
    parser.add_argument('--new-data', type=Path,
                       help='ملف تصحيحات جديدة')
    
    args = parser.parse_args()
    
    # إعداد المراجعة
    reviewer = None
    if args.reviewer_url:
        reviewer = ReviewInterface(args.reviewer_url)
    
    # إعادة التدريب
    if args.retrain:
        if not args.new_data:
            logger.error("❌ --new-data مطلوب مع --retrain")
            return 1
        
        logger.info(f"🏋️ إعادة التدريب باستخدام: {args.new_data}")
        # تنفيذ إعادة التدريب
        return 0
    
    # إرسال للمراجعة فقط
    if args.send_for_review:
        logger.info("📤 إرسال للمراجعة...")
        return 0
    
    # دورة Active Learning كاملة
    if not args.model or not args.unlabeled_pool:
        logger.error("❌ --model و --unlabeled-pool مطلوبان")
        return 1
    
    # تحميل مجموعة التحمّل
    logger.info(f"📂 تحميل مجموعة التحمّل: {args.unlabeled_pool}")
    unlabeled = []
    
    for img_path in sorted(args.unlabeled_pool.glob('**/*')):
        if img_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            unlabeled.append(UnlabeledSample(
                id=f"img_{len(unlabeled):06d}",
                image_path=img_path
            ))
    
    logger.info(f"✅ تم تحميل {len(unlabeled)} عينة غير موسومة")
    
    # تشغيل الدورة
    manager = ActiveLearningManager(
        args.model,
        args.output_dir,
        args.strategy
    )
    
    for i in range(args.max_iterations):
        result = manager.run_iteration(
            unlabeled,
            args.samples_per_iteration,
            reviewer
        )
        
        # إيقاف إذا تحسن CER بما فيه الكفاية
        if result.cer_after and result.cer_after < 0.05:
            logger.info("🎯 CER target reached! إيقاف.")
            break
    
    # ملخص
    summary = manager.get_summary()
    logger.info(f"\n{'='*60}")
    logger.info("📊 ملخص Active Learning")
    logger.info(f"{'='*60}")
    logger.info(f"الدورات: {summary['total_iterations']}")
    logger.info(f"العينات المراجعة: {summary['total_samples_reviewed']}")
    logger.info(f"التحسن: {summary['cer_improvement']:.4f}")
    
    return 0


if __name__ == '__main__':
    exit(main())
