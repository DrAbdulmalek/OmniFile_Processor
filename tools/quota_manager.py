# quota_manager.py - Expert review quota system

"""
📊 مدير حصص المراجعة الخبيرة والعينات العمياء
يضمن المساءلة، يمنع التحيز التراكمي، ويحافظ على جودة الإجماع
"""

import json, random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class ExpertQuotaManager:
    def __init__(
        self,
        storage_path: str = "quota_registry.json",
        weekly_limit: int = 100,
        blind_sample_rate: float = 0.10
    ):
        self.path = Path(storage_path)
        self.weekly_limit = weekly_limit
        self.blind_sample_rate = blind_sample_rate
        self.registry = self._load()
        self._prune_old_weeks()

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.registry, ensure_ascii=False, indent=2), encoding="utf-8")

    def _get_week_key(self) -> str:
        return datetime.now().strftime("%Y-W%U")

    def _prune_old_weeks(self, keep_weeks: int = 4):
        cutoff = datetime.now() - timedelta(weeks=keep_weeks)
        for uid, data in list(self.registry.items()):
            data["weeks"] = {
                wk: v for wk, v in data.get("weeks", {}).items()
                if datetime.strptime(wk.split("-W")[0] + "-01", "%Y-%m-%d") >= cutoff
            }

    def record_approval(self, user_id: str, correction_id: str) -> bool:
        """تسجيل موافقة خبير مع التحقق من الحصة الأسبوعية"""
        week_key = self._get_week_key()
        if user_id not in self.registry:
            self.registry[user_id] = {"approved": [], "weeks": {}}

        if week_key not in self.registry[user_id]["weeks"]:
            self.registry[user_id]["weeks"][week_key] = {"count": 0, "sampled_ids": []}

        week_data = self.registry[user_id]["weeks"][week_key]
        if week_data["count"] >= self.weekly_limit:
            return False  # تجاوز الحصة

        week_data["count"] += 1
        self.registry[user_id]["approved"].append({
            "id": correction_id, "timestamp": datetime.now().isoformat(), "week": week_key
        })
        self._save()
        return True

    def trigger_blind_review(self, user_id: str) -> List[str]:
        """سحب عينة عشوائية للمراجعة العمياء من موافقات الأسبوع الحالي"""
        week_key = self._get_week_key()
        if user_id not in self.registry or week_key not in self.registry[user_id]["weeks"]:
            return []

        week_data = self.registry[user_id]["weeks"][week_key]
        approved_ids = [
            a["id"] for a in self.registry[user_id]["approved"]
            if a["week"] == week_key and a["id"] not in week_data["sampled_ids"]
        ]

        if not approved_ids: return []

        n = max(1, int(len(approved_ids) * self.blind_sample_rate))
        sampled = random.sample(approved_ids, min(n, len(approved_ids)))
        week_data["sampled_ids"].extend(sampled)
        self._save()
        return sampled

    def submit_blind_result(self, expert_id: str, correction_id: str, matches_expert: bool):
        """تحديث السمعة بناءً على نتيجة المراجعة العمياء"""
        from .user_manager import UserManager
        um = UserManager()
        # خفّض تأثير النتيجة المفاجئة (alpha منخفض) لمنع التقلبات
        um.update_reputation(expert_id, aligned=matches_expert, alpha=0.05)
        self._save()

    def get_quota_status(self, user_id: str) -> dict:
        week_key = self._get_week_key()
        data = self.registry.get(user_id, {}).get("weeks", {}).get(week_key, {})
        return {
            "used": data.get("count", 0),
            "limit": self.weekly_limit,
            "remaining": max(0, self.weekly_limit - data.get("count", 0)),
            "sampled_pending": len(data.get("sampled_ids", []))
        }
