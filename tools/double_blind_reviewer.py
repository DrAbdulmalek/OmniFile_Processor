# double_blind_reviewer.py - Double-blind review for sensitive docs

"""
👁️ نظام المراجعة المزدوجة العمياء (Double-Blind Review)
مخصص للوثائق الطبية/القانونية/المالية الحساسة
"""

import json, difflib, random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# المسار الصحيح — tools/ وليس core/
try:
    from tools.user_manager import UserManager
except ImportError:
    UserManager = None  # fallback: سمعة المراجعين لن تُتتبع

class DoubleBlindReviewer:
    def __init__(
        self,
        storage_path: str = "double_blind_registry.json",
        agreement_threshold: float = 0.92,
        max_escalation_age_days: int = 7
    ):
        self.path = Path(storage_path)
        self.threshold = agreement_threshold
        self.max_age = max_escalation_age_days
        self.registry = self._load()

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"tasks": [], "audit_log": []}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.registry, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_task(self, doc_id: str, block_id: str, original: str, sensitivity: str = "high") -> str:
        task_id = f"{doc_id}_{block_id}_{datetime.now().strftime('%H%M%S%f')}"
        task = {
            "id": task_id, "doc_id": doc_id, "block_id": block_id,
            "original": original, "sensitivity": sensitivity,
            "status": "pending", "assigned": [], "reviews": [],
            "created_at": datetime.now().isoformat()
        }
        self.registry["tasks"].append(task)
        self._save()
        return task_id

    def assign_reviewers(self, task_id: str, reviewers: List[str]):
        task = next((t for t in self.registry["tasks"] if t["id"] == task_id), None)
        if not task: return False
        # تعيين عشوائي متوازن
        available = [r for r in reviewers if r not in task["assigned"]]
        if len(available) >= 2:
            task["assigned"] = available[:2]
            task["status"] = "in_progress"
            self._save()
            return True
        return False

    def submit_review(self, task_id: str, reviewer_id: str, corrected: str, notes: str = ""):
        task = next((t for t in self.registry["tasks"] if t["id"] == task_id), None)
        if not task or reviewer_id not in task["assigned"]: return False

        task["reviews"].append({
            "reviewer": reviewer_id, "text": corrected,
            "notes": notes, "submitted_at": datetime.now().isoformat()
        })

        if len(task["reviews"]) >= 2:
            self._evaluate(task)
        self._save()
        return True

    def _evaluate(self, task: dict):
        t1, t2 = task["reviews"][0]["text"], task["reviews"][1]["text"]
        sim = difflib.SequenceMatcher(None, t1.strip(), t2.strip()).ratio()
        task["agreement_score"] = sim

        if sim >= self.threshold:
            task["status"] = "approved"
            task["consensus"] = t1 if sim == 1.0 else (t1 if len(t1) >= len(t2) else t2)
            # مكافأة السمعة للمراجعتين المتطابقتين
            if UserManager is not None:
                um = UserManager()
                um.update_reputation(task["reviews"][0]["reviewer"], aligned=True, alpha=0.15)
                um.update_reputation(task["reviews"][1]["reviewer"], aligned=True, alpha=0.15)
        else:
            task["status"] = "escalated"
            task["reason"] = f"توافق منخفض: {sim:.2%}"
            self.registry["audit_log"].append({
                "task_id": task["id"], "action": "escalated",
                "score": sim, "timestamp": datetime.now().isoformat()
            })

    def get_pending_tasks(self, limit: int = 10) -> List[Dict]:
        return [t for t in self.registry["tasks"] if t["status"] in ["pending", "in_progress"]][:limit]

    def cleanup_old_escalations(self):
        """تنظيف المهام المتأخرة تلقائياً"""
        cutoff = datetime.now() - timedelta(days=self.max_age)
        for t in self.registry["tasks"]:
            if t["status"] == "escalated":
                created = datetime.fromisoformat(t["created_at"])
                if created < cutoff:
                    t["status"] = "auto_rejected"
        self._save()
