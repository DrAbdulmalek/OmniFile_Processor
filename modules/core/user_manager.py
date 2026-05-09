"""
modules/core/user_manager.py
══════════════════════════════
مدير المستخدمين البسيط — Simple User Manager
=============================================
يُستخدم من: tools/double_blind_reviewer.py
يدعم: أدوار المراجعة (reviewer / admin / curator)

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

USERS_FILE = Path("artifacts/users.json")

ROLES = {"admin", "curator", "reviewer", "viewer"}


class UserManager:
    """
    مدير مستخدمين خفيف الوزن للمراجعة المزدوجة.

    مثال:
        um = UserManager()
        um.add_user("dr_abdulmalek", role="admin")
        role = um.get_role("dr_abdulmalek")    # "admin"
        can  = um.can_escalate("dr_abdulmalek")  # True
    """

    def __init__(self, users_file: str = str(USERS_FILE)) -> None:
        self._path  = Path(users_file)
        self._users: dict = {}
        self._load()

    # ── تحميل وحفظ ──────────────────────────────────────────────

    def _load(self) -> None:
        try:
            if self._path.exists():
                self._users = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("UserManager load: %s", e)
            self._users = {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._users, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("UserManager save: %s", e)

    # ── إدارة المستخدمين ─────────────────────────────────────────

    def add_user(self, user_id: str, role: str = "reviewer", name: str = "") -> bool:
        """إضافة مستخدم جديد."""
        if role not in ROLES:
            logger.warning("UserManager: role '%s' غير معروف", role)
            return False
        self._users[user_id] = {"role": role, "name": name or user_id, "active": True}
        self._save()
        return True

    def get_role(self, user_id: str) -> Optional[str]:
        """دور المستخدم أو None إذا لم يكن موجوداً."""
        return self._users.get(user_id, {}).get("role")

    def is_active(self, user_id: str) -> bool:
        """هل المستخدم نشط؟"""
        return self._users.get(user_id, {}).get("active", False)

    def can_escalate(self, user_id: str) -> bool:
        """هل يملك المستخدم صلاحية تصعيد المراجعة؟"""
        return self.get_role(user_id) in {"admin", "curator"}

    def can_review(self, user_id: str) -> bool:
        """هل يملك المستخدم صلاحية المراجعة؟"""
        return self.get_role(user_id) in {"admin", "curator", "reviewer"}

    def list_reviewers(self) -> list:
        """قائمة المراجعين النشطين."""
        return [
            uid for uid, info in self._users.items()
            if info.get("active") and info.get("role") in {"admin","curator","reviewer"}
        ]

    def deactivate(self, user_id: str) -> bool:
        """تعطيل مستخدم."""
        if user_id in self._users:
            self._users[user_id]["active"] = False
            self._save()
            return True
        return False

    def all_users(self) -> dict:
        """كل المستخدمين."""
        return dict(self._users)
