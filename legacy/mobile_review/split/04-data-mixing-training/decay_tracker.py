# decay_tracker.py - Confidence decay tracker

"""
📉 نظام اضمحلال الثقة الديناماميكي
يقلل وزن الأصوات القديمة تلقائياً بناءً على:
1. الزمن المنقضي (اضمحلال طبيعي)
2. دقة النموذج الحالي على أنماط مشابهة (تعديل تكيفي)
"""

import math
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

class DynamicDecayManager:
    def __init__(
        self,
        base_lambda: float = 0.04,      # معدل الاضمحلال الأساسي (يومي)
        half_life_days: float = 17.3,   # ~ln(2)/0.04
        min_confidence: float = 0.15,
        model_feedback_window: int = 100 # عدد التصحيحات الأخيرة لتقييم دقة النموذج
    ):
        self.base_lambda = base_lambda
        self.min_confidence = min_confidence
        self.feedback_window = model_feedback_window
        self.model_feedback: List[bool] = [] # True = AI صحح بنجاح، False = أخطأ

    def calculate_effective_weight(self, vote: Dict, current_time: Optional[datetime] = None) -> float:
        """حساب الوزن الفعال للتصويت مع مراعاة الزمن ودقة النموذج"""
        if current_time is None:
            current_time = datetime.now()

        vote_time = datetime.fromisoformat(vote["timestamp"])
        days_elapsed = (current_time - vote_time).total_seconds() / 86400.0

        # 1. الاضمحلال الزمني الطبيعي
        time_decay = math.exp(-self.base_lambda * days_elapsed)

        # 2. عامل ضبط دقة النموذج (Model Alignment Factor)
        model_factor = self._compute_model_alignment(vote.get("pattern_hash"))

        effective = vote["initial_confidence"] * time_decay * model_factor
        return max(effective, self.min_confidence)

    def _compute_model_alignment(self, pattern_hash: Optional[str] = None) -> float:
        """إذا كان النموذج دقيقاً على أنماط مشابهة، نثق أقل بالتصويت البشري القديم والعكس"""
        if not self.model_feedback:
            return 1.0

        recent = self.model_feedback[-self.feedback_window:]
        ai_accuracy = sum(recent) / len(recent)

        # إذا كان النموذج دقيقاً (>0.8)، نخفض وزن التصويتات القديمة بنسبة 20%
        # إذا كان النموذج ضعيفاً (<0.6)، نرفع وزن التصويتات البشرية كنسخة احتياطية
        if ai_accuracy > 0.85:
            return 0.80
        elif ai_accuracy < 0.65:
            return 1.25
        return 1.0

    def record_ai_feedback(self, was_correct: bool):
        """تغذية راجعة من نموذج التصحيح بعد كل عملية"""
        self.model_feedback.append(was_correct)
        if len(self.model_feedback) > self.feedback_window * 2:
            self.model_feedback = self.model_feedback[-self.feedback_window:]

    def get_weighted_consensus(self, votes_dict: Dict[str, List[Dict]]) -> Optional[Tuple[str, float]]:
        """إرجاع الإجماع المرجح بعد تطبيق الاضمحلال الديناماميكي"""
        if not votes_dict:
            return None

        weighted_totals = {}
        for corrected_text, vote_list in votes_dict.items():
            total_weight = sum(self.calculate_effective_weight(v) for v in vote_list)
            if total_weight > 0:
                weighted_totals[corrected_text] = total_weight

        if not weighted_totals:
            return None

        best_text, best_weight = max(weighted_totals.items(), key=lambda x: x[1])
        total_weight = sum(weighted_totals.values())
        agreement = best_weight / total_weight

        return best_text, agreement

    def export_decay_report(self) -> Dict:
        """تقرير شفاف عن تأثير الاضمحلال على الأصوات الحالية"""
        return {
            "active_model_accuracy": sum(self.model_feedback[-self.feedback_window:]) / max(len(self.model_feedback), 1),
            "current_model_factor": self._compute_model_alignment(),
            "half_life_days": self.base_lambda and round(math.log(2) / self.base_lambda, 2),
            "min_confidence_floor": self.min_confidence
        }
