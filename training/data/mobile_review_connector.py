#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mobile_review_connector.py
==========================

ربط mobile_review مباشرة بـ pipeline التدريب.

الاستخدام:
    from training.data.mobile_review_connector import MobileReviewConnector
    
    connector = MobileReviewConnector("http://localhost:5000")
    
    # جلب التصحيحات
    corrections = connector.get_corrections_for_training()
    
    # تحويل لبيانات تدريب
    dataset = connector.export_to_training_format(
        min_confidence=0.7,
        auto_include_high_confidence=True
    )

المؤلف: Dr. Abdulmalek Al-husseini
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from PIL import Image

# ============================================================================
# إعدادات التسجيل
# ============================================================================

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# هياكل البيانات
# ============================================================================

@dataclass
class ReviewedCorrection:
    """تصحيح مراجع من mobile_review."""
    id: str
    image_path: Path
    original_ocr: str
    corrected_text: str
    confidence: float
    reviewer_agreement: float
    reviewer_id: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Optional[Dict] = None
    
    @property
    def is_reliable(self) -> bool:
        """هل التصحيح موثوق؟"""
        return (
            self.reviewer_agreement > 0.9 and 
            self.confidence > 0.7
        )
    
    @property
    def needs_review(self) -> bool:
        """هل يحتاج مراجعة إضافية؟"""
        return (
            self.reviewer_agreement < 0.7 or
            self.confidence < 0.5
        )
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'image_path': str(self.image_path),
            'original_ocr': self.original_ocr,
            'corrected_text': self.corrected_text,
            'confidence': self.confidence,
            'reviewer_agreement': self.reviewer_agreement,
            'reviewer_id': self.reviewer_id,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


@dataclass
class TrainingBatch:
    """دفعة بيانات تدريب."""
    auto_train: List[ReviewedCorrection]
    needs_review: List[ReviewedCorrection]
    discarded: List[ReviewedCorrection]
    
    @property
    def total(self) -> int:
        return len(self.auto_train) + len(self.needs_review) + len(self.discarded)
    
    @property
    def trainable_count(self) -> int:
        return len(self.auto_train)
    
    def save(self, output_dir: Path):
        """حفظ الدفعة."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_dir / 'auto_train.json', 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in self.auto_train], f, ensure_ascii=False, indent=2)
        
        with open(output_dir / 'needs_review.json', 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in self.needs_review], f, ensure_ascii=False, indent=2)
        
        with open(output_dir / 'discarded.json', 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in self.discarded], f, ensure_ascii=False, indent=2)
        
        # ملخص
        summary = {
            'total': self.total,
            'auto_train': len(self.auto_train),
            'needs_review': len(self.needs_review),
            'discarded': len(self.discarded),
            'trainable_ratio': len(self.auto_train) / self.total if self.total > 0 else 0
        }
        
        with open(output_dir / 'summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"💾 تم حفظ الدفعة: {output_dir}")
        return output_dir


# ============================================================================
# الموصل الرئيسي
# ============================================================================

class MobileReviewConnector:
    """
    ربط mobile_review بـ pipeline التدريب.
    
    يدعم:
    - جلب التصحيحات تلقائياً
    - تصنيفها حسب الجودة
    - تحويلها لبيانات تدريب
    - التكامل مع Active Learning
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    # -------------------------------------------------------------------------
    # جلب البيانات
    # -------------------------------------------------------------------------
    
    def get_corrections(
        self,
        since: Optional[datetime] = None,
        status: str = "completed",
        limit: Optional[int] = None
    ) -> List[ReviewedCorrection]:
        """
        جلب التصحيحات من mobile_review.
        
        Args:
            since: جلب التصحيحات منذ تاريخ معين
            status: حالة المراجعة (completed, pending, rejected)
            limit: أقصى عدد
        
        Returns:
            قائمة تصحيحات
        """
        params = {'status': status}
        if since:
            params['since'] = since.isoformat()
        if limit:
            params['limit'] = limit
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/review/corrections",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            corrections = []
            for item in response.json().get('corrections', []):
                corrections.append(self._parse_correction(item))
            
            logger.info(f"📥 تم جلب {len(corrections)} تصحيح")
            return corrections
            
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ لا يمكن الاتصال بـ {self.base_url}")
            return []
        except Exception as e:
            logger.error(f"❌ خطأ في جلب التصحيحات: {e}")
            return []
    
    def get_corrections_for_training(
        self,
        min_agreement: float = 0.8,
        min_confidence: float = 0.6,
        exclude_used: bool = True
    ) -> List[ReviewedCorrection]:
        """
        جلب تصحيحات مناسبة للتدريب.
        
        Args:
            min_agreement: الحد الأدنى للاتفاق
            min_confidence: الحد الأدنى للثقة
            exclude_used: استبعاد المستخدمة سابقاً
        
        Returns:
            تصحيحات مناسبة
        """
        corrections = self.get_corrections(status="completed")
        
        # تصفية
        suitable = [
            c for c in corrections
            if c.reviewer_agreement >= min_agreement
            and c.confidence >= min_confidence
            and not (exclude_used and self._is_used(c.id))
        ]
        
        logger.info(f"✅ {len(suitable)}/{len(corrections)} مناسبة للتدريب")
        return suitable
    
    def poll_for_new_corrections(
        self,
        interval: int = 300,
        callback: Optional[callable] = None
    ):
        """
        مراقبة مستمرة للتصحيحات الجديدة.
        
        Args:
            interval: فترة الفحص بالثواني
            callback: دالة تُستدعى عند وجود تصحيحات جديدة
        """
        last_check = datetime.now() - timedelta(days=1)
        
        logger.info(f"🔍 بدء المراقبة كل {interval} ثانية...")
        
        while True:
            corrections = self.get_corrections(since=last_check)
            
            if corrections:
                logger.info(f"🆕 {len(corrections)} تصحيح جديد!")
                
                if callback:
                    callback(corrections)
                
                last_check = datetime.now()
            
            time.sleep(interval)
    
    # -------------------------------------------------------------------------
    # تصنيف وتحويل
    # -------------------------------------------------------------------------
    
    def export_to_training_format(
        self,
        corrections: Optional[List[ReviewedCorrection]] = None,
        min_confidence: float = 0.7,
        auto_include_high_confidence: bool = True,
        agreement_threshold: float = 0.9
    ) -> TrainingBatch:
        """
        تحويل التصحيحات لبيانات تدريب مصنفة.
        
        Args:
            corrections: قائمة التصحيحات (None = جلب الكل)
            min_confidence: الحد الأدنى للثقة
            auto_include_high_confidence: تضمين عالية الثقة تلقائياً
            agreement_threshold: حد الاتفاق للتدريب التلقائي
        
        Returns:
            دفعة مصنفة
        """
        if corrections is None:
            corrections = self.get_corrections(status="completed")
        
        auto_train = []
        needs_review = []
        discarded = []
        
        for correction in corrections:
            # تصنيف
            if correction.reviewer_agreement >= agreement_threshold:
                if correction.confidence >= min_confidence:
                    if auto_include_high_confidence:
                        auto_train.append(correction)
                    else:
                        needs_review.append(correction)
                else:
                    needs_review.append(correction)
            elif correction.reviewer_agreement >= 0.5:
                needs_review.append(correction)
            else:
                discarded.append(correction)
        
        batch = TrainingBatch(
            auto_train=auto_train,
            needs_review=needs_review,
            discarded=discarded
        )
        
        logger.info(f"📊 تصنيف:")
        logger.info(f"   🟢 تدريب تلقائي: {len(auto_train)}")
        logger.info(f"   🟡 تحتاج مراجعة: {len(needs_review)}")
        logger.info(f"   🔴 مرفوضة: {len(discarded)}")
        
        return batch
    
    def create_dataset_for_lora(
        self,
        output_dir: Path,
        min_samples: int = 100,
        **filters
    ) -> Optional[Path]:
        """
        إنشاء مجموعة بيانات جاهزة لـ LoRA fine-tuning.
        
        Args:
            output_dir: مجلد الإخراج
            min_samples: الحد الأدنى للعينات
            **filters: مرشحات إضافية
        
        Returns:
            مسار المجموعة أو None
        """
        batch = self.export_to_training_format(**filters)
        
        if batch.trainable_count < min_samples:
            logger.warning(f"⚠️  عينات غير كافية: {batch.trainable_count}/{min_samples}")
            return None
        
        # إنشاء بنية المجلد
        dataset_dir = Path(output_dir)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        images_dir = dataset_dir / 'images'
        images_dir.mkdir(exist_ok=True)
        
        # نسخ الصور وكتابة labels
        with open(dataset_dir / 'labels.txt', 'w', encoding='utf-8') as f:
            f.write("image_path\ttext\n")
            
            for i, correction in enumerate(batch.auto_train):
                # نسخ الصورة
                src = correction.image_path
                dst = images_dir / f"train_{i:06d}.png"
                
                try:
                    if src.exists():
                        import shutil
                        shutil.copy2(src, dst)
                    else:
                        # جلب من URL إن لزم
                        self._download_image(correction.metadata.get('url'), dst)
                    
                    f.write(f"{dst.name}\t{correction.corrected_text}\n")
                    
                except Exception as e:
                    logger.warning(f"⚠️  تخطي {correction.id}: {e}")
        
        # حفظ الإعدادات
        config = {
            'source': 'mobile_review',
            'num_samples': batch.trainable_count,
            'filters': filters,
            'created_at': datetime.now().isoformat()
        }
        
        with open(dataset_dir / 'dataset_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"✅ مجموعة بيانات جاهزة: {dataset_dir}")
        return dataset_dir
    
    # -------------------------------------------------------------------------
    # التكامل مع Active Learning
    # -------------------------------------------------------------------------
    
    def submit_for_human_review(
        self,
        samples: List[Dict],
        priority: str = "normal"
    ) -> List[str]:
        """
        إرسال عينات للمراجعة البشرية.
        
        Args:
            samples: عينات غير موسومة مع تنبؤات
            priority: أولوية المراجعة (low, normal, high, critical)
        
        Returns:
            معرفات المراجعة
        """
        review_ids = []
        
        for sample in samples:
            payload = {
                'image_path': sample.get('image_path'),
                'ocr_prediction': sample.get('prediction', ''),
                'model_confidence': sample.get('confidence', 0),
                'priority': priority,
                'requested_at': datetime.now().isoformat()
            }
            
            try:
                response = self.session.post(
                    f"{self.base_url}/api/review/request",
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
                review_ids.append(response.json().get('review_id'))
                
            except Exception as e:
                logger.error(f"❌ فشل إرسال {sample.get('id')}: {e}")
        
        logger.info(f"📤 تم إرسال {len(review_ids)} للمراجعة البشرية")
        return review_ids
    
    def get_review_statistics(self) -> Dict:
        """إحصائيات المراجعة."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/review/statistics",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ فشل جلب الإحصائيات: {e}")
            return {}
    
    # -------------------------------------------------------------------------
    # دوال داخلية
    # -------------------------------------------------------------------------
    
    def _parse_correction(self, item: Dict) -> ReviewedCorrection:
        """تحليل عنصر JSON."""
        return ReviewedCorrection(
            id=item.get('id', ''),
            image_path=Path(item.get('image_path', '')),
            original_ocr=item.get('ocr_result', ''),
            corrected_text=item.get('corrected_text', ''),
            confidence=item.get('confidence', 0),
            reviewer_agreement=item.get('reviewer_agreement', 0),
            reviewer_id=item.get('reviewer_id'),
            timestamp=item.get('timestamp'),
            metadata=item.get('metadata', {})
        )
    
    def _is_used(self, correction_id: str) -> bool:
        """التحقق إن كانت التصحيح مستخدمة سابقاً."""
        # يمكن تخزينها في قاعدة بيانات محلية
        used_file = Path('./used_corrections.json')
        if used_file.exists():
            with open(used_file, 'r') as f:
                used = json.load(f)
            return correction_id in used
        return False
    
    def _mark_as_used(self, correction_id: str):
        """وضع علامة مستخدم."""
        used_file = Path('./used_corrections.json')
        used = []
        
        if used_file.exists():
            with open(used_file, 'r') as f:
                used = json.load(f)
        
        used.append(correction_id)
        
        with open(used_file, 'w') as f:
            json.dump(used, f)
    
    def _download_image(self, url: Optional[str], dst: Path) -> bool:
        """تحميل صورة من URL."""
        if not url:
            return False
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(dst, 'wb') as f:
                f.write(response.content)
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️  فشل تحميل {url}: {e}")
            return False


# ============================================================================
# دوال مساعدة
# ============================================================================

def create_training_pipeline(
    review_url: str,
    output_dir: Path,
    min_samples_per_batch: int = 100,
    check_interval: int = 3600
):
    """
    إنشاء pipeline تلقائي للتدريب.
    
    Args:
        review_url: رابط mobile_review
        output_dir: مجلد الإخراج
        min_samples_per_batch: الحد الأدنى للدفعة
        check_interval: فترة الفحص بالثواني
    """
    connector = MobileReviewConnector(review_url)
    
    def on_new_corrections(corrections):
        """معالجة تصحيحات جديدة."""
        logger.info(f"🔄 معالجة {len(corrections)} تصحيح جديد...")
        
        batch = connector.export_to_training_format(corrections)
        
        if batch.trainable_count >= min_samples_per_batch:
            # إنشاء مجموعة تدريب
            dataset_dir = output_dir / f"batch_{datetime.now():%Y%m%d_%H%M%S}"
            batch.save(dataset_dir)
            
            # يمكن تشغيل التدريب تلقائياً هنا
            logger.info(f"🚀 جاهز للتدريب: {dataset_dir}")
    
    # بدء المراقبة
    connector.poll_for_new_corrections(
        interval=check_interval,
        callback=on_new_corrections
    )


# ============================================================================
# اختبار
# ============================================================================

if __name__ == '__main__':
    # اختبار محلي
    connector = MobileReviewConnector("http://localhost:5000")
    
    # جلب إحصائيات
    stats = connector.get_review_statistics()
    print(f"Statistics: {stats}")
