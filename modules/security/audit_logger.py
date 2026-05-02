"""
وحدة سجل التدقيق (Audit Logger Module)
=========================================
تسجيل جميع العمليات المهمة في النظام (من قام بماذا ومتى).
يدعم: تسجيل في ملف، قاعدة بيانات، و Redis.

Audit logging module for tracking all important system operations.
Supports: file logging, database logging, and Redis logging.

OmniFile AI Processor v3.0
المصدر: اقتراح من مراجعة Mistral - 2026-05-03
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """أنواع العمليات المدققة / Types of audited actions."""
    # OCR Operations
    OCR_PROCESS = "ocr_process"
    OCR_CORRECT = "ocr_correct"
    OCR_FUSION = "ocr_fusion"

    # NLP Operations
    NLP_TRANSLATE = "nlp_translate"
    NLP_SUMMARIZE = "nlp_summarize"
    NLP_SPELL_CHECK = "nlp_spell_check"
    NLP_NER = "nlp_ner"
    NLP_CLASSIFY = "nlp_classify"

    # Security Operations
    SECURITY_ENCRYPT = "security_encrypt"
    SECURITY_DECRYPT = "security_decrypt"
    SECURITY_SCAN = "security_scan"
    SECURITY_PII_DETECT = "security_pii_detect"

    # File Operations
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETE = "file_delete"
    FILE_EXPORT = "file_export"

    # System Operations
    SYSTEM_LOGIN = "system_login"
    SYSTEM_LOGOUT = "system_logout"
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    SYSTEM_ERROR = "system_error"

    # AI Operations
    AI_CORRECT = "ai_correct"
    AI_REFINE = "ai_refine"


class AuditLevel(str, Enum):
    """مستوى أهمية العملية / Operation severity level."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SECURITY = "security"


class AuditLogger:
    """
    سجل تدقيق شامل للنظام.
    Comprehensive system audit logger.

    الميزات / Features:
    - تسجيل كل عملية مع التفاصيل الكاملة
    - دعم إخراج متعدد (ملف، Redis، قاعدة بيانات)
    - تحديد المستخدم وعنوان IP
    - تصفية حسب المستوى والنوع
    - دعم البحث والاستعلام
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        redis_url: Optional[str] = None,
        enable_file: bool = True,
        enable_redis: bool = False,
        enable_db: bool = False,
    ):
        """
        تهيئة سجل التدقيق.

        Args:
            log_file: مسار ملف السجل (الافتراضي: logs/audit.log)
            redis_url: عنوان Redis لتخزين السجلات
            enable_file: تفعيل تسجيل في ملف
            enable_redis: تفعيل تسجيل في Redis
            enable_db: تفعيل تسجيل في قاعدة البيانات
        """
        self.enable_file = enable_file
        self.enable_redis = enable_redis
        self.enable_db = enable_db
        self._redis = None
        self._redis_list = "omnifile:audit_log"

        # إعداد ملف السجل
        self.log_file = log_file or os.path.join("logs", "audit.log")
        if self.enable_file:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # إعداد Redis
        if self.enable_redis and redis_url:
            self._init_redis(redis_url)

    def _init_redis(self, redis_url: str) -> None:
        """تهيئة اتصال Redis."""
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            logger.info("تم الاتصال بـ Redis للسجل التدقيقي")
        except ImportError:
            logger.warning("مكتبة redis غير مثبتة")
            self.enable_redis = False
        except Exception as e:
            logger.warning("فشل الاتصال بـ Redis: %s", e)
            self.enable_redis = False

    def log(
        self,
        action: AuditAction,
        level: AuditLevel = AuditLevel.INFO,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[dict] = None,
        status: str = "success",
        duration_ms: Optional[float] = None,
        resource: Optional[str] = None,
    ) -> dict:
        """
        تسجيل عملية في السجل التدقيقي.

        Args:
            action: نوع العملية
            level: مستوى الأهمية
            user: اسم المستخدم (إن وجد)
            ip_address: عنوان IP
            details: تفاصيل إضافية
            status: حالة العملية (success, failed, pending)
            duration_ms: مدة التنفيذ بالميلي ثانية
            resource: المورد المتعلق (مثلاً: اسم الملف)

        Returns:
            قاموس السجل المدخل
        """
        entry = {
            "id": str(uuid.uuid4())[:12],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action.value,
            "level": level.value,
            "user": user or "anonymous",
            "ip_address": ip_address or "unknown",
            "details": details or {},
            "status": status,
            "duration_ms": round(duration_ms, 2) if duration_ms else None,
            "resource": resource,
            "version": "3.0.0",
        }

        # تسجيل في ملف
        if self.enable_file:
            self._log_to_file(entry)

        # تسجيل في Redis
        if self.enable_redis and self._redis:
            self._log_to_redis(entry)

        # تسجيل في Python logger
        self._log_to_logger(entry)

        return entry

    def _log_to_file(self, entry: dict) -> None:
        """كتابة السجل في ملف."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("فشل كتابة السجل التدقيقي: %s", e)

    def _log_to_redis(self, entry: dict) -> None:
        """كتابة السجل في Redis."""
        try:
            self._redis.lpush(self._redis_list, json.dumps(entry, ensure_ascii=False))
            # الاحتفاظ بآخر 10000 سجل فقط
            self._redis.ltrim(self._redis_list, 0, 9999)
        except Exception as e:
            logger.error("فشل كتابة السجل في Redis: %s", e)

    def _log_to_logger(self, entry: dict) -> None:
        """كتابة السجل في Python logger."""
        msg = (
            f"[AUDIT] {entry['action']} | "
            f"user={entry['user']} | "
            f"ip={entry['ip_address']} | "
            f"status={entry['status']}"
        )
        if entry.get("duration_ms"):
            msg += f" | duration={entry['duration_ms']}ms"
        if entry.get("resource"):
            msg += f" | resource={entry['resource']}"

        if entry["level"] == AuditLevel.CRITICAL.value:
            logger.critical(msg)
        elif entry["level"] == AuditLevel.SECURITY.value:
            logger.warning(msg)
        elif entry["level"] == AuditLevel.WARNING.value:
            logger.warning(msg)
        else:
            logger.info(msg)

    def get_logs(
        self,
        action: Optional[str] = None,
        user: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        استعلام السجلات.

        Args:
            action: تصفية حسب نوع العملية
            user: تصفية حسب المستخدم
            level: تصفية حسب المستوى
            limit: أقصى عدد من السجلات

        Returns:
            قائمة السجلات
        """
        logs = []

        # قراءة من Redis أولاً (أسرع)
        if self.enable_redis and self._redis:
            try:
                raw_logs = self._redis.lrange(self._redis_list, 0, limit - 1)
                logs = [json.loads(log) for log in raw_logs]
            except Exception as e:
                logger.error("فشل قراءة السجلات من Redis: %s", e)

        # قراءة من ملف كاحتياط
        if not logs and self.enable_file:
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-limit:]
                    logs = [json.loads(line.strip()) for line in lines if line.strip()]
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.error("فشل قراءة السجلات من الملف: %s", e)

        # تطبيق التصفية
        if action:
            logs = [l for l in logs if l.get("action") == action]
        if user:
            logs = [l for l in logs if l.get("user") == user]
        if level:
            logs = [l for l in logs if l.get("level") == level]

        return logs

    def get_stats(self) -> dict:
        """إحصائيات السجلات."""
        logs = self.get_logs(limit=10000)

        stats = {
            "total_logs": len(logs),
            "by_action": {},
            "by_level": {},
            "by_status": {},
            "by_user": {},
            "errors_count": 0,
        }

        for log in logs:
            action = log.get("action", "unknown")
            level = log.get("level", "info")
            status = log.get("status", "unknown")
            user = log.get("user", "anonymous")

            stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            stats["by_user"][user] = stats["by_user"].get(user, 0) + 1

            if status == "failed":
                stats["errors_count"] += 1

        return stats

    def clear_logs(self, older_than_days: int = 30) -> int:
        """
        حذف السجلات القديمة.

        Args:
            older_than_days: حذف السجلات الأقدم من هذا العدد من الأيام

        Returns:
            عدد السجلات المحذوفة
        """
        cutoff = time.time() - (older_than_days * 86400)
        deleted = 0

        if self.enable_file and os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                kept_lines = []
                for line in lines:
                    try:
                        entry = json.loads(line.strip())
                        ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
                        if ts >= cutoff:
                            kept_lines.append(line)
                        else:
                            deleted += 1
                    except (json.JSONDecodeError, KeyError):
                        kept_lines.append(line)

                with open(self.log_file, "w", encoding="utf-8") as f:
                    f.writelines(kept_lines)

                logger.info("تم حذف %d سجل تدقيقي قديم", deleted)
            except Exception as e:
                logger.error("فشل حذف السجلات القديمة: %s", e)

        return deleted


# =============================================================================
# Global Audit Logger Instance
# =============================================================================

def get_audit_logger() -> AuditLogger:
    """الحصول على مثيل سجل التدقيق العام."""
    return AuditLogger(
        redis_url=os.getenv("REDIS_URL"),
        enable_redis=bool(os.getenv("REDIS_URL")),
    )
