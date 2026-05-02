"""
HandwrittenOCR - نظام المزامنة v5.0
=====================================
وحدة متكاملة تدعم:
- قفل الملفات (File Locking) لمنع التعارضات بين الأجهزة
- إدارة حالة المزامنة (Sync Status)
- تكامل مع Syncthing للمزامنة التلقائية أوفلاين/أونلاين
- دعم العمل المتزامن من جهازين (جوال + حاسوب)
"""

import os
import json
import time
import logging
import platform
import socket
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger("HandwrittenOCR.Sync")


# =========================================================================
# 1. نظام قفل الملفات (File Locking)
# =========================================================================

class FileLock:
    """
    قفل ملفات لمنع التعارضات عند العمل من عدة أجهزة متزامنة.
    يستخدم fcntl على Linux/macOS و msvcrt على Windows.

    الاستخدام:
        lock = FileLock(config.lock_file_path, timeout=30)
        with lock:
            # عمليات قاعدة البيانات هنا
            db.insert_word(...)
    """

    def __init__(self, lock_path: str, timeout: int = 30):
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self._lock_file = None
        self._system = platform.system()

    def acquire(self) -> bool:
        """الحصول على القفل مع مهلة محددة"""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_file = open(self.lock_path, "w")
        start = time.time()

        while True:
            try:
                if self._system == "Windows":
                    import msvcrt
                    msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                # كتابة معلومات القفل
                lock_info = {
                    "pid": os.getpid(),
                    "hostname": socket.gethostname(),
                    "timestamp": datetime.now().isoformat(),
                    "user": os.environ.get("USER", "unknown"),
                }
                self._lock_file.seek(0)
                self._lock_file.truncate()
                self._lock_file.write(json.dumps(lock_info, indent=2))
                self._lock_file.flush()

                logger.debug(f"تم الحصول على القفل: {self.lock_path}")
                return True

            except (BlockingIOError, OSError, ImportError):
                if time.time() - start > self.timeout:
                    self._lock_file.close()
                    self._lock_file = None
                    raise TimeoutError(
                        "تعذر الحصول على قفل الملف - جهاز آخر يعمل حالياً. "
                        "حاول بعد قليل أو تحقق من أن الجهاز الآخر أوقف المعالجة."
                    )
                time.sleep(0.5)

    def release(self) -> None:
        """تحرير القفل"""
        if self._lock_file is None:
            return

        try:
            if self._system == "Windows":
                import msvcrt
                self._lock_file.seek(0)
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.debug(f"خطأ في تحرير القفل: {e}")
        finally:
            try:
                self._lock_file.close()
            except Exception:
                pass
            self._lock_file = None

    def get_lock_info(self) -> Optional[dict]:
        """قراءة معلومات القفل الحالي (من جهاز آخر)"""
        if not self.lock_path.exists():
            return None
        try:
            with open(self.lock_path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def is_locked(self) -> bool:
        """التحقق مما إذا كان القفل مفعلاً بواسطة عملية أخرى"""
        info = self.get_lock_info()
        if info is None:
            return False

        # التحقق مما إذا كانت العملية لا تزال نشطة
        pid = info.get("pid")
        if pid is None:
            return False

        try:
            os.kill(pid, 0)  # لا يرسل إشارة، فقط يتحقق
            return True
        except (ProcessLookupError, PermissionError):
            # العملية غير موجودة - القفل قديم
            try:
                self.lock_path.unlink()
            except Exception:
                pass
            return False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


# =========================================================================
# 2. إدارة حالة المزامنة (Sync Status)
# =========================================================================

class SyncManager:
    """
    مدير المزامنة الشامل - يتتبع حالة التزامن بين الأجهزة.
    يدعم Syncthing ويمكن تمديد لدعم خدمات أخرى.
    """

    # الملفات والمجلدات التي يجب مزامنتها
    SYNC_PATTERNS = [
        "database/handwriting_data.db",
        "logs/user_corrections_feedback.csv",
        "artifacts/correction_dict.json",
        "exports/",
        "input_pdfs/",
        "sync_status.json",
        "artifacts/ocr_checkpoint.json",
        "logs/processing_stats.json",
        "logs/runs_history.csv",
    ]

    # المجلدات التي لا يجب مزامنتها (كبيرة جداً)
    NO_SYNC_PATTERNS = [
        "models_cache/",
        "runs/",          # TensorBoard logs
        ".EasyOCR/",
        "backups/",
    ]

    def __init__(self, config):
        """
        Args:
            config: كائن Config من config.py
        """
        self.config = config
        self.status_path = config.sync_status_path
        self.lock = FileLock(config.lock_file_path, timeout=config.sync_lock_timeout)
        self._device_id = self._generate_device_id()

    def _generate_device_id(self) -> str:
        """إنشاء معرف فريد للجهاز الحالي"""
        import uuid
        try:
            mac = uuid.getnode()
            return f"{socket.gethostname()}-{mac:012x}"
        except Exception:
            return f"device-{uuid.uuid4().hex[:8]}"

    @property
    def device_id(self) -> str:
        """معرف الجهاز الحالي"""
        return self._device_id

    def get_status(self) -> dict:
        """
        قراءة حالة المزامنة الحالية.
        يُرجع dict يحتوي على آخر تحديث من كل جهاز.
        """
        if not os.path.exists(self.status_path):
            return {
                "last_sync": None,
                "devices": {},
                "current_device": self._device_id,
                "conflicts": [],
            }

        try:
            with open(self.status_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return {
                "last_sync": None,
                "devices": {},
                "current_device": self._device_id,
                "conflicts": [],
            }

    def update_device_status(self, action: str = "process", details: dict = None) -> None:
        """
        تحديث حالة الجهاز الحالي بعد كل عملية مهمة.
        يُكتب تلقائياً عند: معالجة PDF، مراجعة كلمات، تصحيح، تصدير.

        Args:
            action: نوع العملية (process, review, correct, export, sync)
            details: تفاصيل إضافية اختيارية
        """
        status = self.get_status()
        now = datetime.now().isoformat()

        if "devices" not in status:
            status["devices"] = {}

        device_info = status["devices"].get(self._device_id, {})
        device_info.update({
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "last_action": action,
            "last_update": now,
            "details": details or {},
        })
        status["devices"][self._device_id] = device_info
        status["current_device"] = self._device_id
        status["last_sync"] = now

        # حفظ الحالة
        os.makedirs(os.path.dirname(self.status_path), exist_ok=True)
        with open(self.status_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2, ensure_ascii=False)

        logger.debug(f"تم تحديث حالة الجهاز: {action}")

    def detect_conflicts(self) -> list:
        """
        كشف التعارضات بين الأجهزة.
        يتحقق مما إذا كان أكثر من جهاز قد عدّل نفس البيانات.
        """
        status = self.get_status()
        conflicts = []

        if not status.get("devices"):
            return conflicts

        devices = status["devices"]
        device_ids = list(devices.keys())

        # التحقق من تعارضات المعالجة
        for i, d1 in enumerate(device_ids):
            for d2 in device_ids[i + 1:]:
                dev1 = devices[d1]
                dev2 = devices[d2]

                # إذا كلاهما عملا على نفس الملف في وقت قريب
                if (dev1.get("last_action") == "process" and
                        dev2.get("last_action") == "process"):
                    t1 = dev1.get("last_update", "")
                    t2 = dev2.get("last_update", "")
                    if t1 and t2:
                        try:
                            dt1 = datetime.fromisoformat(t1)
                            dt2 = datetime.fromisoformat(t2)
                            diff = abs((dt1 - dt2).total_seconds())
                            if diff < 300:  # أقل من 5 دقائق
                                conflicts.append({
                                    "type": "concurrent_processing",
                                    "devices": [d1, d2],
                                    "time_diff_sec": diff,
                                    "message": (
                                        "كلا الجهازين عالجا نفس الملف في وقت قريب. "
                                        "قد تحتاج لإعادة المعالجة."
                                    ),
                                })
                        except (ValueError, TypeError):
                            pass

        status["conflicts"] = conflicts
        return conflicts

    def get_syncthing_config(self) -> dict:
        """
        توليد إعدادات Syncthing للمشروع.
        يُرجع JSON جاهز للاستخدام أو العرض.
        """
        root = Path(self.config.project_root)

        sync_folders = []
        for pattern in self.SYNC_PATTERNS:
            full_path = root / pattern
            if full_path.exists() or pattern.endswith("/"):
                sync_folders.append({
                    "path": pattern,
                    "exists": full_path.exists(),
                    "type": "folder" if pattern.endswith("/") else "file",
                })

        ignore_folders = []
        for pattern in self.NO_SYNC_PATTERNS:
            ignore_folders.append({
                "path": pattern,
                "reason": "large_files" if "models" in pattern or "runs" in pattern else "cache",
            })

        return {
            "project_name": "HandwrittenOCR",
            "project_root": str(root),
            "sync_folders": sync_folders,
            "ignore_folders": ignore_folders,
            "setup_instructions": {
                "linux": (
                    "sudo pacman -S syncthing  # Manjaro/Arch\n"
                    "systemctl --user enable --now syncthing\n"
                    f"# ثم أضف المجلد: {root}\n"
                    "# افتح الواجهة: http://127.0.0.1:8384"
                ),
                "android": (
                    "1. نزّل Syncthing من F-Droid أو Google Play\n"
                    "2. امنح صلاحية الوصول لمجلد المشروع\n"
                    "3. اقترن مع الحاسوب عبر QR Code\n"
                    "4. فعّل 'Sync when on Wi-Fi only'"
                ),
            },
        }

    def generate_syncthing_stignore(self) -> str:
        """توليد محتوى ملف .stignore لـ Syncthing"""
        lines = ["# HandwrittenOCR - Syncthing ignore patterns", ""]
        for pattern in self.NO_SYNC_PATTERNS:
            lines.append(pattern)
        lines.append("")
        lines.append("// temp files")
        lines.append("*.pyc")
        lines.append("__pycache__/")
        lines.append(".git/")
        lines.append("*.lock")
        lines.append("ocr_env/")
        return "\n".join(lines)

    def get_network_info(self) -> dict:
        """الحصول على معلومات الشبكة المحلية (للوصول من الجوال)"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            # محاولة الحصول على IP الشبكة المحلية بشكل أدق
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            finally:
                s.close()

            return {
                "hostname": hostname,
                "local_ip": local_ip,
                "server_url": f"http://{local_ip}:{self.config.gradio_port}",
                "api_url": f"http://{local_ip}:8000",
            }
        except Exception as e:
            return {
                "hostname": socket.gethostname(),
                "local_ip": "127.0.0.1",
                "server_url": f"http://127.0.0.1:{self.config.gradio_port}",
                "api_url": "http://127.0.0.1:8000",
                "error": str(e),
            }


# =========================================================================
# 3. Context Manager مريح للاستخدام
# =========================================================================

@contextmanager
def sync_lock(config, action: str = "process", details: dict = None):
    """
    Context Manager يجمع بين القفل وتحديث حالة المزامنة.

    الاستخدام:
        with sync_lock(config, action="process", details={"words": 150}):
            processor.process()
    """
    sync_mgr = SyncManager(config)

    # كشف التعارضات قبل البدء
    conflicts = sync_mgr.detect_conflicts()
    if conflicts:
        for conflict in conflicts:
            logger.warning(f"تعارض مزامنة: {conflict['message']}")

    # الحصول على القفل
    lock = FileLock(config.lock_file_path, timeout=config.sync_lock_timeout)
    lock.acquire()

    try:
        yield sync_mgr
        # تحديث حالة المزامنة بنجاح
        sync_mgr.update_device_status(action=action, details=details)
    except Exception as e:
        # تحديث حالة المزامنة بالفشل
        sync_mgr.update_device_status(
            action=f"{action}_failed",
            details={"error": str(e)}
        )
        raise
    finally:
        lock.release()
