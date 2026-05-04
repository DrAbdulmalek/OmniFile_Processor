"""
خدمة مراقبة المجلدات (Folder Watchdog Service)
================================================
مراقبة مجلد الإدخال تلقائياً ومعالجة الملفات الجديدة فور إضافتها.

الوظائف:
- مراقبة مجلد الإدخال في الخلفية
- معالجة تلقائية عند إضافة ملفات جديدة
- دعم فلاتر الامتدادات
- إدارة دورة حياة المراقب (بدء/إيقاف/إعادة تشغيل)
- سجل عمليات مفصل

الاستخدام:
    from modules.core.watchdog_service import FolderWatchdog
    watchdog = FolderWatchdog(
        watch_dir="/path/to/input",
        callback=my_processing_function,
        extensions=['.pdf', '.png', '.jpg']
    )
    watchdog.start()  # يبدأ المراقبة في الخلفية
    # ...
    watchdog.stop()   # إيقاف المراقبة
"""

import logging
import os
import threading
import time
from datetime import datetime
from typing import Callable, List, Optional, Dict, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class FolderWatchdog:
    """
    مراقب المجلدات — يعمل كخدمة خلفية لمعالجة الملفات تلقائياً.

    يمكن استخدام مكتبة watchdog إذا كانت متوفرة، مع السقوط التلقائي
    إلى نظام استطلاع (polling) في حال عدم توفرها.
    """

    SUPPORTED_EXTENSIONS = [
        '.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif',
        '.bmp', '.gif', '.webp', '.docx', '.doc', '.txt'
    ]

    def __init__(
        self,
        watch_dir: str,
        callback: Callable[[str], Any],
        extensions: Optional[List[str]] = None,
        recursive: bool = False,
        poll_interval: float = 2.0,
        debounce_seconds: float = 1.0,
        log_file: Optional[str] = None,
    ):
        """
        تهيئة مراقب المجلدات.

        Args:
            watch_dir: مسار المجلد المراقب
            callback: دالة المعالجة التي تُستدعى لكل ملف جديد
                      يجب أن تقبل مسار الملف كمعامل أول
            extensions: قائمة الامتدادات المقبولة (None = الكل)
            recursive: مراقبة المجلدات الفرعية أيضاً
            poll_interval: فترة الاستطلاع بالثواني (لنظام polling)
            debounce_seconds: مهلة الانتظار قبل معالجة الملف (ثواني)
            log_file: مسار ملف السجل (اختياري)
        """
        self.watch_dir = os.path.abspath(watch_dir)
        self.callback = callback
        self.extensions = set(
            ext.lower() for ext in (extensions or self.SUPPORTED_EXTENSIONS)
        )
        self.recursive = recursive
        self.poll_interval = poll_interval
        self.debounce_seconds = debounce_seconds

        # حالة المراقب
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._seen_files: Set[str] = set()
        self._pending_files: Dict[str, float] = {}

        # إحصائيات
        self._stats = {
            "files_processed": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "start_time": None,
            "last_activity": None,
        }

        # سجل العمليات
        self._operation_log: List[Dict[str, Any]] = []
        self.log_file = log_file

        # محاولة استخدام watchdog
        self._use_watchdog = False
        self._watchdog_observer = None
        self._try_import_watchdog()

        # التأكد من وجود المجلد
        os.makedirs(self.watch_dir, exist_ok=True)

        # مسح الملفات الموجودة مسبقاً (لا نعالجها)
        self._scan_existing_files()

        logger.info(
            "تم تهيئة مراقب المجلدات: %s (watchdog=%s, recursive=%s)",
            self.watch_dir, self._use_watchdog, self.recursive
        )

    def _try_import_watchdog(self):
        """محاولة استيراد مكتبة watchdog."""
        try:
            from watchdog.observers import Observer  # type: ignore
            from watchdog.events import FileSystemEventHandler  # type: ignore
            self._watchdog_observer_cls = Observer
            self._watchdog_handler_cls = FileSystemEventHandler
            self._use_watchdog = True
            logger.info("تم تحميل مكتبة watchdog بنجاح")
        except ImportError:
            self._use_watchdog = False
            logger.info(
                "مكتبة watchdog غير متوفرة. سيتم استخدام نظام الاستطلاع (polling). "
                "pip install watchdog"
            )

    def _scan_existing_files(self):
        """مسح الملفات الموجودة في المجلد لتسجيلها (لا تُعالج)."""
        for root, _, files in os.walk(self.watch_dir):
            for filename in files:
                filepath = os.path.join(root, filename)
                self._seen_files.add(filepath)
            if not self.recursive:
                break
        logger.info(
            "تم تسجيل %d ملف موجود في %s",
            len(self._seen_files), self.watch_dir
        )

    def _is_valid_file(self, filepath: str) -> bool:
        """التحقق من أن الملف يطابق فلاتر الامتدادات."""
        ext = os.path.splitext(filepath)[1].lower()
        if self.extensions and ext not in self.extensions:
            return False
        return True

    def _is_file_ready(self, filepath: str) -> bool:
        """
        التحقق من أن الملف جاهز للمعالجة (لم يعد يُكتب إليه).

        هذا يمنع محاولة معالجة ملف لا يزال قيد النسخ.
        """
        try:
            # فحص حجم الملف مرتين
            size1 = os.path.getsize(filepath)
            time.sleep(0.5)
            size2 = os.path.getsize(filepath)

            # إذا كان الملف لا يزال ينمو، فهو ليس جاهزاً
            if size1 != size2:
                return False

            # محاولة فتح الملف حصرياً
            try:
                with open(filepath, 'rb') as f:
                    f.seek(0, 2)  # الذهاب للنهاية
                return True
            except (IOError, OSError):
                return False
        except (OSError, IOError):
            return False

    def _process_file(self, filepath: str):
        """معالجة ملف جديد."""
        try:
            self._log_operation("processing", filepath)
            self.callback(filepath)
            self._stats["files_processed"] += 1
            self._stats["last_activity"] = datetime.now().isoformat()
            self._log_operation("completed", filepath)
            logger.info("تمت معالجة: %s", os.path.basename(filepath))
        except Exception as e:
            self._stats["files_failed"] += 1
            self._log_operation("failed", filepath, str(e))
            logger.error("فشلت معالجة %s: %s", filepath, e)

    def _poll_loop(self):
        """حلقة الاستطلاع للكشف عن الملفات الجديدة."""
        logger.info("بدء حلقة الاستطلاع: %s (فاصل: %.1fs)", self.watch_dir, self.poll_interval)

        while not self._stop_event.is_set():
            try:
                for root, _, files in os.walk(self.watch_dir):
                    for filename in files:
                        filepath = os.path.join(root, filename)

                        if filepath in self._seen_files:
                            continue

                        if not self._is_valid_file(filepath):
                            self._seen_files.add(filepath)
                            self._stats["files_skipped"] += 1
                            continue

                        # نظام debounce — انتظار حتى ينتهي الكتابة
                        now = time.time()
                        if filepath not in self._pending_files:
                            self._pending_files[filepath] = now
                            continue

                        elapsed = now - self._pending_files[filepath]
                        if elapsed < self.debounce_seconds:
                            continue

                        del self._pending_files[filepath]

                        if self._is_file_ready(filepath):
                            self._seen_files.add(filepath)
                            # المعالجة في خيط منفصل لعدم حظر المراقبة
                            thread = threading.Thread(
                                target=self._process_file,
                                args=(filepath,),
                                daemon=True
                            )
                            thread.start()

                    if not self.recursive:
                        break

            except Exception as e:
                logger.error("خطأ في حلقة الاستطلاع: %s", e)

            self._stop_event.wait(self.poll_interval)

    def _start_watchdog(self):
        """بدء المراقبة باستخدام مكتبة watchdog."""
        from watchdog.observers import Observer  # type: ignore
        from watchdog.events import FileSystemEventHandler  # type: ignore

        class Handler(FileSystemEventHandler):
            def __init__(self, watchdog_instance):
                self.wd = watchdog_instance

            def on_created(self, event):
                if event.is_directory:
                    return
                filepath = event.src_path
                if not self.wd._is_valid_file(filepath):
                    return
                if filepath not in self.wd._seen_files:
                    self.wd._seen_files.add(filepath)
                    # تأخير بسيط لضمان اكتمال الكتابة
                    threading.Timer(
                        self.wd.debounce_seconds,
                        self.wd._process_file,
                        args=(filepath,)
                    ).start()

            def on_moved(self, event):
                """معالجة الملفات المنقولة إلى المجلد المراقب."""
                if event.is_directory:
                    return
                dest = event.dest_path
                if os.path.dirname(dest) == self.wd.watch_dir:
                    if not self.wd._is_valid_file(dest):
                        return
                    if dest not in self.wd._seen_files:
                        self.wd._seen_files.add(dest)
                        threading.Timer(
                            self.wd.debounce_seconds,
                            self.wd._process_file,
                            args=(dest,)
                        ).start()

        handler = Handler(self)
        self._watchdog_observer = self._watchdog_observer_cls()
        self._watchdog_observer.schedule(
            handler, self.watch_dir, recursive=self.recursive
        )
        self._watchdog_observer.start()
        logger.info("بدأ مراقب watchdog: %s", self.watch_dir)

    def start(self):
        """
        بدء مراقبة المجلد في الخلفية.

        يعمل في خيط منفصل ولا يحظر الخيط الرئيسي.
        """
        if self._running:
            logger.warning("المراقب يعمل بالفعل")
            return

        self._running = True
        self._stop_event.clear()
        self._stats["start_time"] = datetime.now().isoformat()

        if self._use_watchdog:
            self._start_watchdog()
            # مراقب watchdog لا يحتاج خيط إضافي
        else:
            self._thread = threading.Thread(
                target=self._poll_loop, daemon=True
            )
            self._thread.start()

        logger.info(
            "بدأ مراقب المجلدات: %s (طريقة: %s)",
            self.watch_dir,
            "watchdog" if self._use_watchdog else "polling"
        )

    def stop(self):
        """
        إيقاف مراقبة المجلد.

        ينتظر انتهاء المعالجة الجارية ثم يوقف المراقب.
        """
        if not self._running:
            return

        logger.info("جاري إيقاف مراقب المجلدات...")
        self._stop_event.set()
        self._running = False

        if self._watchdog_observer:
            self._watchdog_observer.stop()
            self._watchdog_observer.join(timeout=5)
            self._watchdog_observer = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            self._thread = None

        logger.info("تم إيقاف مراقب المجلدات")

    def get_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات المراقب."""
        stats = dict(self._stats)
        stats["watch_dir"] = self.watch_dir
        stats["running"] = self._running
        stats["method"] = "watchdog" if self._use_watchdog else "polling"
        stats["extensions"] = list(self.extensions)
        stats["total_seen"] = len(self._seen_files)
        stats["pending"] = len(self._pending_files)
        return stats

    def _log_operation(self, action: str, filepath: str, detail: str = ""):
        """تسجيل عملية في السجل."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "file": os.path.basename(filepath),
            "path": filepath,
            "detail": detail,
        }
        self._operation_log.append(entry)

        # حفظ في ملف إذا تم تحديده
        if self.log_file:
            try:
                import json
                os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("خطأ في كتابة سجل العمليات: %s", e)

    def get_operation_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """الحصول على سجل العمليات."""
        return self._operation_log[-limit:]

    def force_rescan(self):
        """إعادة مسح المجلد ومعالجة أي ملفات جديدة."""
        logger.info("إعادة مسح مجبرة: %s", self.watch_dir)
        self._scan_existing_files()

        for root, _, files in os.walk(self.watch_dir):
            for filename in files:
                filepath = os.path.join(root, filename)
                if filepath not in self._seen_files and self._is_valid_file(filepath):
                    if self._is_file_ready(filepath):
                        self._seen_files.add(filepath)
                        self._process_file(filepath)
            if not self.recursive:
                break

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __repr__(self):
        status = "running" if self._running else "stopped"
        return (
            f"FolderWatchdog(dir='{self.watch_dir}', "
            f"status={status}, method={'watchdog' if self._use_watchdog else 'polling'})"
        )
