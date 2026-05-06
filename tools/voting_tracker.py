# voting_tracker.py - Majority voting for character-level corrections

"""
🗳️ نظام تصويت ذكي للتصحيحات الحرفية والنصية
يعتمد على: تطبيع عربي موحد، عدادات زمنية، وعتبة إجماع قابلة للضبط
"""

import json, time, re, hashlib
from pathlib import Path
from collections import Counter, defaultdict
from typing import Optional, Tuple, Dict, List
from datetime import datetime, timedelta

class ArabicNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        if not text: return ""
        text = re.sub(r'[\u064B-\u065B\u0670]', '', text)  # تشكيل
        text = re.sub(r'[أإآٱ]', 'ا', text)
        text = re.sub(r'ة', 'ه', text)
        text = re.sub(r'[ى]', 'ي', text)
        return text.strip()

class CorrectionVoter:
    def __init__(
        self,
        min_votes: int = 3,
        agreement_threshold: float = 0.65,
        max_age_days: int = 30,
        storage_path: Optional[str] = None
    ):
        self.min_votes = min_votes
        self.agreement_threshold = agreement_threshold
        self.max_age = timedelta(days=max_age_days)
        self.storage_path = Path(storage_path) if storage_path else Path("voting_cache.json")

        # الهيكل: {normalized_original: {corrected_text: [{"voter": str, "timestamp": iso, "confidence": float}]}}
        self.votes: Dict[str, Dict[str, List[dict]]] = self._load_or_init()
        self._normalizer = ArabicNormalizer()

    def _load_or_init(self) -> Dict:
        if self.storage_path.exists():
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return defaultdict(lambda: defaultdict(list))

    def add_vote(
        self,
        original: str,
        correction: str,
        voter_id: str = "anonymous",
        confidence: float = 1.0
    ) -> bool:
        norm_orig = self._normalizer.normalize(original)
        norm_corr = self._normalizer.normalize(correction)

        if not norm_orig or not norm_corr:
            return False

        # إضافة التصويت مع ختم زمني
        self.votes[norm_orig][norm_corr].append({
            "voter": voter_id,
            "timestamp": datetime.now().isoformat(),
            "confidence": min(max(confidence, 0.0), 1.0)
        })
        self._save()
        return True

    def get_consensus(self, original: str) -> Optional[Tuple[str, float]]:
        """إرجاع (النص المتفق عليه، نسبة التوافق) أو None إذا لم تُحقق العتبة"""
        norm_orig = self._normalizer.normalize(original)
        if norm_orig not in self.votes:
            return None

        corrections = self.votes[norm_orig]
        total_votes = 0
        weighted_counts = Counter()

        # حساب الأصوات مع مراعاة العمر والثقة
        for corr, vote_list in corrections.items():
            valid_votes = [
                v for v in vote_list
                if datetime.fromisoformat(v["timestamp"]) > datetime.now() - self.max_age
            ]
            weight = sum(v["confidence"] for v in valid_votes)
            if valid_votes:
                weighted_counts[corr] = weight
                total_votes += weight

        if total_votes < self.min_votes:
            return None

        best_corr, best_weight = weighted_counts.most_common(1)[0]
        agreement = best_weight / total_votes

        if agreement >= self.agreement_threshold:
            return best_corr, agreement
        return None

    def export_approved_corrections(self) -> Dict[str, str]:
        """تصدير التصحيحات المعتمدة فقط إلى قاموس قابل للاستخدام"""
        approved = {}
        for norm_orig, corrections in self.votes.items():
            consensus = self.get_consensus(norm_orig)
            if consensus:
                approved[norm_orig] = consensus[0]
        return approved

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(dict(self.votes), f, ensure_ascii=False, indent=2)

    def prune_old_votes(self):
        """تنظيف التصويتات القديمة لتوفير الذاكرة"""
        cutoff = datetime.now() - self.max_age
        pruned = 0
        for orig in list(self.votes.keys()):
            for corr in list(self.votes[orig].keys()):
                self.votes[orig][corr] = [
                    v for v in self.votes[orig][corr]
                    if datetime.fromisoformat(v["timestamp"]) > cutoff
                ]
                if not self.votes[orig][corr]:
                    del self.votes[orig][corr]
            if not self.votes[orig]:
                del self.votes[orig]
                pruned += 1
        self._save()
        return pruned
