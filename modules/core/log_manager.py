"""
modules/core/log_manager.py
════════════════════════════
مدير السجلات الخاصة — Private App Logger
==========================================
يسجّل أحداث التطبيق محلياً ثم يرفعها إلى GitHub Gist خاص
(لا يمكن قراءته إلا لمن يملك الـ token).

الميزات:
  ✅ سجل محلي في logs/app_YYYYMMDD.log
  ✅ رفع تلقائي إلى Private GitHub Gist عند كل جلسة
  ✅ تسجيل: بدء التطبيق، OCR، تصحيحات، أخطاء، إحصائيات
  ✅ لا يُكشف Gist ID علناً — فقط من يملك التوكن يراه

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import json
import logging
import os
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LOGS_DIR       = Path("logs")
GIST_ID_FILE   = Path("logs/.gist_id")   # يُخزَّن locally، لا يُرفع لـ GitHub


class AppLogger:
    """
    مدير السجلات الخاصة.

    مثال:
        log = AppLogger(github_token="ghp_xxx")
        log.session_start()
        log.log("ocr_run", {"engine": "EasyOCR", "words": 12})
        log.log_error(e)
        log.push()   # رفع إلى GitHub Gist خاص
    """

    def __init__(
        self,
        github_token: str = "",
        app_name: str = "OmniFile",
        version: str = "5.0",
    ) -> None:
        self.token    = github_token or os.environ.get("GITHUB_TOKEN", "")
        self.app_name = app_name
        self.version  = version
        self._events: list[dict] = []
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # ── تسجيل الأحداث ────────────────────────────────────────────────

    def session_start(self) -> None:
        """تسجيل بداية جلسة جديدة."""
        self.log("session_start", {
            "version":  self.version,
            "python":   sys.version.split()[0],
            "platform": platform.system(),
            "hostname": platform.node(),
        })

    def log(self, event: str, data: Optional[dict] = None) -> None:
        """تسجيل حدث."""
        entry = {
            "ts":    datetime.now().isoformat(),
            "event": event,
            "data":  data or {},
        }
        self._events.append(entry)
        self._append_local(entry)
        logger.debug("AppLog: %s %s", event, data)

    def log_error(self, exc: Exception, context: str = "") -> None:
        """تسجيل خطأ مع stack trace كامل."""
        self.log("error", {
            "context": context,
            "type":    type(exc).__name__,
            "message": str(exc),
            "trace":   traceback.format_exc()[-800:],
        })

    def log_ocr(self, engine: str, lang: str, word_count: int, elapsed: float) -> None:
        self.log("ocr_run", {
            "engine":     engine,
            "lang":       lang,
            "words":      word_count,
            "elapsed_s":  round(elapsed, 2),
        })

    def log_correction(self, predicted: str, corrected: str, lang: str) -> None:
        self.log("correction", {
            "predicted": predicted,
            "corrected": corrected,
            "lang":      lang,
            "improved":  predicted != corrected,
        })

    def log_stats(self, stats: dict) -> None:
        self.log("db_stats", stats)

    # ── الحفظ المحلي ─────────────────────────────────────────────────

    def _append_local(self, entry: dict) -> None:
        """إضافة سطر للملف المحلي."""
        try:
            log_file = LOGS_DIR / f"app_{datetime.now():%Y%m%d}.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_local_log_path(self) -> Optional[str]:
        log_file = LOGS_DIR / f"app_{datetime.now():%Y%m%d}.log"
        return str(log_file) if log_file.exists() else None

    # ── الرفع إلى GitHub Gist الخاص ─────────────────────────────────

    def push(self) -> dict:
        """
        رفع السجلات إلى GitHub Gist خاص.

        - إذا كان Gist موجوداً مسبقاً (مخزَّن في logs/.gist_id) → يُحدَّث
        - إذا لم يكن موجوداً → يُنشأ جديد (private=True)

        Returns:
            {"gist_id": str, "url": str, "status": str}
        """
        if not self.token:
            logger.warning("AppLogger.push: no GitHub token — skipping")
            return {"status": "skipped", "reason": "no_token"}

        try:
            import urllib.request
            content  = self._build_log_content()
            gist_id  = self._load_gist_id()
            filename = f"omnifile_log_{datetime.now():%Y%m}.txt"

            if gist_id:
                result = self._update_gist(gist_id, filename, content)
            else:
                result = self._create_gist(filename, content)
                if result.get("gist_id"):
                    self._save_gist_id(result["gist_id"])

            logger.info("AppLogger.push: %s", result)
            return result

        except Exception as e:
            logger.error("AppLogger.push failed: %s", e)
            return {"status": "error", "reason": str(e)}

    def _build_log_content(self) -> str:
        """بناء محتوى السجل كنص."""
        lines = [
            f"OmniFile App Log — {self.app_name} v{self.version}",
            f"Session: {self._session_id}",
            f"Generated: {datetime.now().isoformat()}",
            "=" * 60,
        ]
        for e in self._events:
            lines.append(
                f"[{e['ts']}] {e['event']:20s}  {json.dumps(e['data'], ensure_ascii=False)[:120]}"
            )
        return "\n".join(lines)

    def _api_call(self, method: str, url: str, data: dict) -> dict:
        """استدعاء GitHub API."""
        import urllib.request, urllib.error
        body = json.dumps(data).encode("utf-8")
        req  = urllib.request.Request(
            url, data=body, method=method,
            headers={
                "Authorization": f"token {self.token}",
                "Content-Type":  "application/json",
                "Accept":        "application/vnd.github.v3+json",
                "User-Agent":    "OmniFile/5.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def _create_gist(self, filename: str, content: str) -> dict:
        resp = self._api_call("POST", "https://api.github.com/gists", {
            "description": f"OmniFile App Logs — {self.app_name}",
            "public":      False,
            "files":       {filename: {"content": content or "empty"}},
        })
        return {
            "status":   "created",
            "gist_id":  resp.get("id", ""),
            "url":      resp.get("html_url", ""),
        }

    def _update_gist(self, gist_id: str, filename: str, content: str) -> dict:
        resp = self._api_call("PATCH", f"https://api.github.com/gists/{gist_id}", {
            "files": {filename: {"content": content or "empty"}},
        })
        return {
            "status":  "updated",
            "gist_id": resp.get("id", gist_id),
            "url":     resp.get("html_url", ""),
        }

    def _load_gist_id(self) -> Optional[str]:
        try:
            if GIST_ID_FILE.exists():
                return GIST_ID_FILE.read_text().strip()
        except Exception:
            pass
        return None

    def _save_gist_id(self, gist_id: str) -> None:
        try:
            GIST_ID_FILE.write_text(gist_id)
        except Exception:
            pass


# ── Singleton للاستخدام المباشر ────────────────────────────────────

_default_logger: Optional[AppLogger] = None


def get_app_logger(token: str = "") -> AppLogger:
    """الحصول على logger موحَّد للتطبيق."""
    global _default_logger
    if _default_logger is None:
        _default_logger = AppLogger(
            github_token=token or os.environ.get("GITHUB_TOKEN", ""),
        )
    return _default_logger
