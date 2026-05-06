# user_manager.py - User role management with expert badges

"""
👥 مدير المستخدمين والأدوار مع دعم expert_flag
يُستخدم لوزن التصويتات، تتبع السمعة، ومنع تحيز المبتدئين أو تضخم الخبراء
"""

import json
from pathlib import Path
from typing import Optional, Literal
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    BEGINNER = "beginner"
    EXPERT = "expert"
    LINGUIST = "linguist"
    CURATOR = "curator"

class UserManager:
    def __init__(self, storage_path: str = "users_registry.json"):
        self.path = Path(storage_path)
        self.users = self._load()
        self._role_base_conf = {
            UserRole.BEGINNER: 0.60,
            UserRole.EXPERT: 0.85,
            UserRole.LINGUIST: 0.95,
            UserRole.CURATOR: 1.00
        }

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def _save(self):
        self.path.write_text(json.dumps(self.users, ensure_ascii=False, indent=2), encoding="utf-8")

    def register_or_get(self, user_id: str, role: UserRole = UserRole.BEGINNER) -> dict:
        if user_id not in self.users:
            self.users[user_id] = {
                "role": role.value,
                "initial_confidence": self._role_base_conf[role],
                "reputation": 1.0,
                "total_votes": 0,
                "alignment_score": 0.5,  # EMA: 0..1
                "joined_at": datetime.now().isoformat(),
                "expert_flags_issued": 0
            }
            self._save()
        return self.users[user_id]

    def compute_vote_weight(self, user_id: str, is_expert_flagged: bool = False) -> float:
        u = self.users.get(user_id, {})
        base = u.get("initial_confidence", 0.6) * u.get("reputation", 1.0)
        if is_expert_flagged and u.get("role") in ["expert", "linguist", "curator"]:
            base = min(base * 1.25, 0.98)  # تعزيز الخبير مع سقف أمان
        return base

    def update_reputation(self, user_id: str, aligned: bool, alpha: float = 0.1):
        if user_id not in self.users: return
        u = self.users[user_id]
        u["total_votes"] += 1
        # متوسط متحرك أسي للتوافق مع الإجماع
        u["alignment_score"] = alpha * float(aligned) + (1 - alpha) * u["alignment_score"]
        # تحديث السمعة تدريجياً
        delta = 0.02 if aligned else -0.04
        u["reputation"] = max(0.3, min(1.0, u["reputation"] + delta))
        self._save()

    def promote_user(self, user_id: str, new_role: UserRole):
        if user_id in self.users:
            self.users[user_id]["role"] = new_role.value
            self.users[user_id]["initial_confidence"] = self._role_base_conf[new_role]
            self._save()

    def get_audit_log(self) -> dict:
        """تقرير شفاف عن توزيع الأدوار والسمعة"""
        return {
            u: {"role": v["role"], "rep": round(v["reputation"], 3), "votes": v["total_votes"]}
            for u, v in self.users.items()
        }
