"""
modules/core/corrections_manager.py
══════════════════════════════════════
مدير قاموس التصحيحات — Corrections Dictionary Manager
=======================================================
يتيح تصدير واستيراد ودمج قاموس تصحيحات OCR بين المستخدمين والأجهزة.

اقتراح من QWEN:
  "أضف export_corrections() لإنشاء حزم تصحيح قابلة للمشاركة بين المستخدمين"

الميزات:
  - تصدير القاموس كـ JSON package قابل للمشاركة
  - استيراد ودمج قاموس خارجي (merge) أو استبدال (replace)
  - إحصائيات وأهم التصحيحات
  - نسخة احتياطية تلقائية قبل كل دمج

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# مسار القاموس الافتراضي
DEFAULT_CORRECTIONS_PATH = "artifacts/correction_dict.json"
DEFAULT_ARABIC_FIXES_PATH = "data/arabic_fixes.json"


class CorrectionsDictManager:
    """
    مدير قاموس التصحيحات.

    مثال:
        manager = CorrectionsDictManager()
        # تصدير
        pkg_path = manager.export("/tmp/my_corrections.json")
        # استيراد ودمج
        count = manager.import_and_merge("/tmp/their_corrections.json")
        # إحصائيات
        stats = manager.stats()
    """

    def __init__(
        self,
        corrections_path: str = DEFAULT_CORRECTIONS_PATH,
        arabic_fixes_path: str = DEFAULT_ARABIC_FIXES_PATH,
        backup_dir: str = "artifacts/backups",
    ) -> None:
        self.corrections_path = Path(corrections_path)
        self.arabic_fixes_path = Path(arabic_fixes_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    # ── القاموس الداخلي ────────────────────────────────────────────

    def load(self) -> dict:
        """تحميل قاموس التصحيحات الحالي."""
        if self.corrections_path.exists():
            with open(self.corrections_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save(self, corrections: dict) -> None:
        """حفظ قاموس التصحيحات."""
        self.corrections_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.corrections_path, "w", encoding="utf-8") as f:
            json.dump(corrections, f, ensure_ascii=False, indent=2)
        logger.info("Corrections saved: %d entries → %s", len(corrections), self.corrections_path)

    def add(self, wrong: str, correct: str) -> None:
        """إضافة تصحيح واحد وحفظه فوراً."""
        corrections = self.load()
        corrections[wrong] = correct
        self.save(corrections)

    def remove(self, wrong: str) -> bool:
        """حذف تصحيح بالكلمة الخاطئة. يُرجع True إذا وُجد وحُذف."""
        corrections = self.load()
        if wrong in corrections:
            del corrections[wrong]
            self.save(corrections)
            return True
        return False

    # ── التصدير ────────────────────────────────────────────────────

    def export(self, output_path: str, include_arabic_fixes: bool = True) -> str:
        """
        تصدير قاموس التصحيحات كحزمة JSON قابلة للمشاركة.
        اقتراح QWEN: "حزم تصحيح قابلة للمشاركة بين المستخدمين".

        Args:
            output_path:          مسار ملف الإخراج (.json)
            include_arabic_fixes: تضمين قاموس الإصلاحات العربية الأساسية

        Returns:
            مسار الملف المُصدَّر
        """
        corrections = self.load()

        # دمج arabic_fixes.json إن طُلب
        if include_arabic_fixes and self.arabic_fixes_path.exists():
            with open(self.arabic_fixes_path, encoding="utf-8") as f:
                arabic_fixes = json.load(f)
            # arabic_fixes لا تطغى على التصحيحات المخصصة
            merged = {**arabic_fixes, **corrections}
        else:
            merged = corrections

        package = {
            "omnifile_corrections_version": "5.0",
            "source":                       "OmniFile_Processor",
            "exported_at":                  datetime.now().isoformat(),
            "total_corrections":            len(merged),
            "includes_arabic_fixes":        include_arabic_fixes,
            "corrections":                  merged,
        }

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(package, f, ensure_ascii=False, indent=2)

        logger.info("Corrections exported: %d entries → %s", len(merged), output)
        return str(output)

    # ── الاستيراد والدمج ────────────────────────────────────────────

    def import_and_merge(self, import_path: str, replace: bool = False) -> int:
        """
        استيراد ودمج قاموس تصحيحات خارجي.

        Args:
            import_path: مسار حزمة JSON المستورَدة
            replace:     True = استبدال كامل | False = دمج (يحتفظ بالقديم)

        Returns:
            إجمالي عدد التصحيحات بعد الدمج
        """
        # نسخة احتياطية قبل أي تعديل
        self._backup()

        with open(import_path, encoding="utf-8") as f:
            package = json.load(f)

        incoming = package.get("corrections", {})

        if replace:
            final = incoming
        else:
            existing = self.load()
            # التصحيحات الواردة تطغى على القديمة
            final = {**existing, **incoming}

        self.save(final)
        logger.info(
            "Corrections imported (%s): %d incoming → %d total",
            "replace" if replace else "merge",
            len(incoming),
            len(final),
        )
        return len(final)

    # ── الإحصائيات ─────────────────────────────────────────────────

    def stats(self, top_n: int = 10) -> dict:
        """
        إحصائيات قاموس التصحيحات.

        Returns:
            dict يحتوي على: count, top_entries, arabic_count, english_count
        """
        corrections = self.load()
        arabic_count  = sum(1 for k in corrections if any('\u0600' <= c <= '\u06ff' for c in k))
        english_count = len(corrections) - arabic_count
        top_entries   = list(corrections.items())[:top_n]

        # arabic_fixes stats
        af_count = 0
        if self.arabic_fixes_path.exists():
            with open(self.arabic_fixes_path, encoding="utf-8") as f:
                af_count = len(json.load(f))

        return {
            "total":          len(corrections),
            "arabic_entries": arabic_count,
            "english_entries": english_count,
            "arabic_fixes":   af_count,
            "top_entries":    top_entries,
            "corrections_path": str(self.corrections_path),
        }

    # ── نسخ احتياطية ───────────────────────────────────────────────

    def _backup(self) -> Optional[str]:
        """نسخة احتياطية تلقائية من القاموس الحالي."""
        if not self.corrections_path.exists():
            return None
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"correction_dict_{ts}.json"
        shutil.copy2(self.corrections_path, backup_path)
        logger.debug("Backup created: %s", backup_path)
        return str(backup_path)

    def list_backups(self) -> list[str]:
        """قائمة النسخ الاحتياطية المتاحة."""
        return sorted(
            str(p) for p in self.backup_dir.glob("correction_dict_*.json")
        )

    def restore_backup(self, backup_path: str) -> bool:
        """استعادة نسخة احتياطية محددة."""
        src = Path(backup_path)
        if not src.exists():
            logger.error("Backup not found: %s", backup_path)
            return False
        shutil.copy2(src, self.corrections_path)
        logger.info("Restored backup: %s", backup_path)
        return True
