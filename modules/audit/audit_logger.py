# ══════════════════════════════════════════════════════════╗
#  Medical Audit Logger & Dual-OCR Integration - v6.0
#  Decision Logging | Performance Tracking | Analytical Reports
# ══════════════════════════════════════════════════════════╝

import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional


class AuditLogger:
    """
    سجل التدقيق الطبي - يوثق كل قرار بشكل كامل:
    من، متى، ماذا، لماذا، وبأي إصدار نموذج.

    السجل يُخزن بصيغة JSONL (append-only) لضمان النزاهة وعدم التعديل.
    """

    def __init__(self, log_dir: Optional[str] = None, reviewer_id: str = "DrUser"):
        if log_dir is None:
            log_dir = str(Path(__file__).parent.parent.parent / 'data' / 'audit_logs')

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True, parents=True)
        self.log_file = self.log_dir / "audit_log.jsonl"
        self.reviewer_id = reviewer_id

    # ────────────────────────────────────────────────────────
    # Core Logging
    # ────────────────────────────────────────────────────────

    def log_decision(
        self,
        page_id: str,
        line_idx: int,
        trocr_text: str,
        easyocr_text: str,
        similarity: float,
        recommendation: str,
        critical_alerts: List[str],
        final_text: str,
        action: str,
        confidence: str,
        model_version: str,
    ):
        """
        تسجيل قرار واحد في السجل.

        Args:
            page_id: Identifier of the source page/image.
            line_idx: Line index on the page.
            trocr_text: Text produced by TrOCR.
            easyocr_text: Text produced by EasyOCR.
            similarity: Similarity ratio between both texts.
            recommendation: AUTO_ACCEPT, MANUAL_REVIEW_REQUIRED, or QUICK_CHECK.
            critical_alerts: List of critical mismatch warnings.
            final_text: The text that was finally accepted.
            action: AUTO_ACCEPT, USER_CONFIRM, USER_OVERRIDE, USER_CORRECT.
            confidence: HIGH, MEDIUM, or LOW.
            model_version: Version/identifier of the TrOCR model used.
        """
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "reviewer_id": self.reviewer_id,
            "page_id": page_id,
            "line_idx": line_idx,
            "model_version": model_version,
            "trocr_text": trocr_text,
            "easyocr_text": easyocr_text,
            "similarity": round(similarity, 4),
            "recommendation": recommendation,
            "critical_alerts": critical_alerts,
            "final_accepted_text": final_text,
            "action": action,
            "confidence": confidence,
            "decision_reason": self._generate_reason(recommendation, critical_alerts, action),
        }

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ────────────────────────────────────────────────────────
    # Reason Generation
    # ────────────────────────────────────────────────────────

    @staticmethod
    def _generate_reason(rec: str, alerts: List[str], action: str) -> str:
        """توليد سبب القرار بناءً على المعطيات."""
        if action == "AUTO_ACCEPT":
            return f"High similarity ({rec}) without critical contradictions"
        elif alerts:
            return f"Critical contradiction resolved manually: {'; '.join(alerts)}"
        elif action == "USER_OVERRIDE":
            return "Human intervention to correct model error"
        return "Routine review"

    # ────────────────────────────────────────────────────────
    # Read / Query Logs
    # ────────────────────────────────────────────────────────

    def read_logs(self, limit: Optional[int] = None) -> List[Dict]:
        """قراءة جميع السجلات (أو عدد محدود آخرها)."""
        logs = []
        if not self.log_file.exists():
            return logs

        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))

        if limit is not None:
            logs = logs[-limit:]

        return logs

    def get_stats(self) -> Dict:
        """
        حساب إحصائيات سريعة من السجل.
        Returns dict with: total, auto_rate, manual_rate, critical_rate, etc.
        """
        logs = self.read_logs()
        if not logs:
            return {
                "total": 0,
                "auto_rate": 0.0,
                "manual_rate": 0.0,
                "critical_rate": 0.0,
                "action_distribution": {},
            }

        total = len(logs)
        auto_count = sum(1 for l in logs if l.get('action') == 'AUTO_ACCEPT')
        critical_count = sum(1 for l in logs if len(l.get('critical_alerts', [])) > 0)

        action_dist: Dict[str, int] = {}
        for l in logs:
            act = l.get('action', 'UNKNOWN')
            action_dist[act] = action_dist.get(act, 0) + 1

        return {
            "total": total,
            "auto_rate": (auto_count / total) * 100 if total else 0,
            "manual_rate": ((total - auto_count) / total) * 100 if total else 0,
            "critical_rate": (critical_count / total) * 100 if total else 0,
            "action_distribution": action_dist,
        }

    # ────────────────────────────────────────────────────────
    # Log Rotation / Backup
    # ────────────────────────────────────────────────────────

    def rotate_log(self, backup_suffix: Optional[str] = None):
        """
        تدوير السجل: ينقل السجل الحالي إلى ملف نسخ احتياطي ويبدأ سجل جديد.
        """
        if not self.log_file.exists():
            return

        if backup_suffix is None:
            backup_suffix = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        backup_path = self.log_dir / f"audit_log_{backup_suffix}.jsonl.bak"
        self.log_file.rename(backup_path)
        print(f"✅ Log rotated to: {backup_path}")
