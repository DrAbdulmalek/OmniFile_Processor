"""
مدير النسخ الاحتياطية (Backup Manager)
=========================================
ينشئ نسخاً احتياطية مُرقّمة لمشروع البيانات مع دعم النسخ التزايدي
والاستعادة والتنظيف.

القدرات:
- إنشاء نسخ احتياطية مرقّمة بالتاريخ والوقت
- إنشاء نسخ مضغوطة (ZIP)
- دعم النسخ التزايدي (الملفات المعدّلة فقط)
- استعادة من نسخة احتياطية
- عرض قائمة النسخ الاحتياطية
- تنظيف النسخ القديمة
- تسجيل جميع العمليات
"""

import hashlib
import json
import logging
import shutil
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BackupManager:
    """
    مدير النسخ الاحتياطية — ينشئ ويستعيد النسخ الاحتياطية المرقّمة.

    الاستخدام:
        manager = BackupManager()
        backup_path = manager.create_backup("/my/project", "/backups")
        manager.restore_backup(backup_path, "/restore/target")
    """

    # ======== ثوابت ========
    MANIFEST_FILENAME: str = ".backup_manifest.json"
    HASH_ALGORITHM: str = "sha256"
    BACKUP_TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"
    DEFAULT_MAX_SIZE_ZIP: int = 4 * 1024 * 1024 * 1024  # 4 جيجابايت

    def __init__(
        self,
        compress: bool = True,
        incremental: bool = False,
        exclude_patterns: Optional[list[str]] = None,
        log_file: Optional[str] = None,
    ) -> None:
        """
        تهيئة مدير النسخ الاحتياطية.

        المعاملات:
            compress: ضغط النسخة الاحتياطية كـ ZIP
            incremental: تفعيل النسخ التزايدي (الملفات المعدّلة فقط)
            exclude_patterns: أنماط glob لاستبعاد ملفات معينة
            log_file: مسار ملف سجل العمليات (اختياري)
        """
        self.compress: bool = compress
        self.incremental: bool = incremental
        self.exclude_patterns: list[str] = exclude_patterns or []

        # إعداد تسجيل مخصص
        self._operation_log: list[dict] = []
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                file_handler.setLevel(logging.INFO)
                file_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s | %(levelname)s | %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )
                logger.addHandler(file_handler)
                logger.info("تم تفعيل تسجيل العمليات في: %s", log_file)
            except PermissionError as exc:
                logger.warning("لا صلاحية لإنشاء ملف السجل: %s", exc)

        # تخزين التجزئات للنسخ التزايدي
        self._file_hashes: dict[str, str] = {}

        logger.info(
            "تم تهيئة مدير النسخ الاحتياطية — ضغط: %s | تزايدي: %s",
            compress, incremental,
        )

    # ===================================================================
    #  إنشاء نسخة احتياطية
    # ===================================================================

    def create_backup(
        self,
        source_dir: str | Path,
        backup_dir: str | Path,
        label: Optional[str] = None,
    ) -> str:
        """
        ينشئ نسخة احتياطية كاملة لمجلد المصدر.

        المعاملات:
            source_dir: مجلد المصدر المراد نسخه
            backup_dir: مجلد حفظ النسخ الاحتياطية
            label: تسمية اختيارية للنسخة

        المعاد:
            مسار النسخة الاحتياطية المنشأة
        """
        source = Path(source_dir).resolve()
        dest = Path(backup_dir).resolve()

        if not source.is_dir():
            raise FileNotFoundError(f"مجلد المصدر غير موجود: {source}")

        # إنشاء مجلد النسخ الاحتياطية
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise PermissionError(f"لا صلاحية لإنشاء {dest}: {exc}") from exc

        # اسم النسخة الاحتياطية
        timestamp = datetime.now().strftime(self.BACKUP_TIMESTAMP_FORMAT)
        source_name = source.name
        label_suffix = f"_{label}" if label else ""

        if self.compress:
            backup_filename = f"{source_name}_backup_{timestamp}{label_suffix}.zip"
            backup_path = dest / backup_filename
        else:
            backup_filename = f"{source_name}_backup_{timestamp}{label_suffix}"
            backup_path = dest / backup_filename

        logger.info("بدء إنشاء نسخة احتياطية: %s", backup_path.name)

        start_time = datetime.now()
        total_files = 0
        total_size = 0
        skipped = 0

        try:
            if self.compress:
                total_files, total_size, skipped = self._create_zip_backup(
                    source, backup_path,
                )
            else:
                total_files, total_size, skipped = self._create_dir_backup(
                    source, backup_path,
                )
        except Exception as exc:
            logger.error("فشل إنشاء النسخة الاحتياطية: %s", exc)
            # حذف الملف الجزئي
            if backup_path.exists():
                try:
                    if backup_path.is_dir():
                        shutil.rmtree(backup_path)
                    else:
                        backup_path.unlink()
                except OSError:
                    pass
            raise

        elapsed = (datetime.now() - start_time).total_seconds()

        # تسجيل العملية
        operation = {
            "timestamp": start_time.isoformat(),
            "action": "create_backup",
            "source": str(source),
            "backup_path": str(backup_path.resolve()),
            "total_files": total_files,
            "total_size": total_size,
            "skipped": skipped,
            "elapsed_seconds": round(elapsed, 2),
            "compressed": self.compress,
            "incremental": self.incremental,
            "label": label,
        }
        self._operation_log.append(operation)
        self._save_manifest(backup_path, operation)

        logger.info(
            "تم إنشاء نسخة احتياطية بنجاح — المسار: %s | الملفات: %d | الحجم: %s | الوقت: %.1f ثانية",
            backup_path, total_files, self._format_size(total_size), elapsed,
        )

        return str(backup_path.resolve())

    def _create_zip_backup(
        self,
        source: Path,
        backup_path: Path,
    ) -> tuple[int, int, int]:
        """
        ينشئ نسخة احتياطية مضغوطة كـ ZIP.

        المعاد:
            (عدد_الملفات، الحجم_الإجمالي، عدد_المتخطّى)
        """
        total_files = 0
        total_size = 0
        skipped = 0

        # جمع الملفات المراد نسخها
        files_to_backup: list[Path] = []
        for item in source.rglob("*"):
            if not item.is_file():
                continue
            if self._should_exclude(item, source):
                skipped += 1
                continue
            if self.incremental and not self._is_file_changed(item, source):
                skipped += 1
                continue
            files_to_backup.append(item)

        # إنشاء أرشيف ZIP
        try:
            with zipfile.ZipFile(
                backup_path, "w",
                zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as zf:
                for file_path in files_to_backup:
                    try:
                        arcname = file_path.relative_to(source)
                        zf.write(file_path, arcname)
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        total_files += 1

                        # تحديث التجزئة
                        if self.incremental:
                            rel = str(arcname)
                            self._file_hashes[rel] = self._hash_file(file_path)

                    except PermissionError as exc:
                        logger.warning("تخطي %s (لا صلاحية): %s", file_path, exc)
                        skipped += 1
                    except OSError as exc:
                        logger.warning("تخطي %s (خطأ): %s", file_path, exc)
                        skipped += 1

        except PermissionError as exc:
            raise PermissionError(f"لا صلاحية لإنشاء {backup_path}: {exc}") from exc

        return total_files, total_size, skipped

    def _create_dir_backup(
        self,
        source: Path,
        backup_path: Path,
    ) -> tuple[int, int, int]:
        """
        ينشئ نسخة احتياطية كمجلد (بدون ضغط).

        المعاد:
            (عدد_الملفات، الحجم_الإجمالي، عدد_المتخطّى)
        """
        total_files = 0
        total_size = 0
        skipped = 0

        try:
            backup_path.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise PermissionError(f"لا صلاحية لإنشاء {backup_path}: {exc}") from exc

        for item in source.rglob("*"):
            if self._should_exclude(item, source):
                skipped += 1
                continue

            rel = item.relative_to(source)
            target = backup_path / rel

            try:
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                elif item.is_file():
                    if self.incremental and not self._is_file_changed(item, source):
                        skipped += 1
                        continue

                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)

                    file_size = item.stat().st_size
                    total_size += file_size
                    total_files += 1

                    if self.incremental:
                        self._file_hashes[str(rel)] = self._hash_file(item)

            except PermissionError as exc:
                logger.warning("تخطي %s (لا صلاحية): %s", item, exc)
                skipped += 1
            except OSError as exc:
                logger.warning("تخطي %s (خطأ): %s", item, exc)
                skipped += 1

        return total_files, total_size, skipped

    # ===================================================================
    #  استعادة نسخة احتياطية
    # ===================================================================

    def restore_backup(
        self,
        backup_path: str | Path,
        target_dir: str | Path,
        overwrite: bool = False,
    ) -> dict:
        """
        يستعيد نسخة احتياطية إلى مجلد الهدف.

        المعاملات:
            backup_path: مسار النسخة الاحتياطية
            target_dir: مجلد الاستعادة
            overwrite: الكتابة فوق الملفات الموجودة

        المعاد:
            تقرير الاستعادة:
            {"restored_files": int, "skipped": int, "errors": list}
        """
        backup = Path(backup_path).resolve()
        target = Path(target_dir).resolve()

        if not backup.exists():
            raise FileNotFoundError(f"النسخة الاحتياطية غير موجودة: {backup}")

        # إنشاء مجلد الهدف
        try:
            target.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise PermissionError(f"لا صلاحية لإنشاء {target}: {exc}") from exc

        report: dict = {
            "restored_files": 0,
            "skipped": 0,
            "errors": [],
        }

        start_time = datetime.now()
        logger.info("بدء استعادة من: %s إلى %s", backup.name, target)

        try:
            if backup.is_file() and backup.suffix.lower() == ".zip":
                self._restore_from_zip(backup, target, overwrite, report)
            elif backup.is_dir():
                self._restore_from_dir(backup, target, overwrite, report)
            else:
                raise ValueError(f"نوع نسخة احتياطية غير معروف: {backup}")

        except Exception as exc:
            logger.error("فشل استعادة النسخة الاحتياطية: %s", exc)
            raise

        elapsed = (datetime.now() - start_time).total_seconds()

        # تسجيل العملية
        operation = {
            "timestamp": start_time.isoformat(),
            "action": "restore_backup",
            "backup_path": str(backup),
            "target": str(target),
            "restored_files": report["restored_files"],
            "skipped": report["skipped"],
            "errors_count": len(report["errors"]),
            "elapsed_seconds": round(elapsed, 2),
        }
        self._operation_log.append(operation)

        logger.info(
            "اكتملت الاستعادة — مستعادة: %d | متخطاة: %d | أخطاء: %d | الوقت: %.1f ثانية",
            report["restored_files"], report["skipped"],
            len(report["errors"]), elapsed,
        )

        return report

    def _restore_from_zip(
        self,
        backup: Path,
        target: Path,
        overwrite: bool,
        report: dict,
    ) -> None:
        """يستعيد من أرشيف ZIP."""
        try:
            with zipfile.ZipFile(backup, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        (target / info.filename).mkdir(parents=True, exist_ok=True)
                        continue

                    # حماية من Path Traversal
                    member_path = Path(info.filename)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        report["errors"].append({"file": info.filename, "error": "مسار خطر"})
                        continue

                    dest_file = target / info.filename

                    if dest_file.exists() and not overwrite:
                        report["skipped"] += 1
                        continue

                    try:
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(info) as src, open(dest_file, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        report["restored_files"] += 1
                    except PermissionError as exc:
                        report["errors"].append({"file": info.filename, "error": str(exc)})
                    except OSError as exc:
                        report["errors"].append({"file": info.filename, "error": str(exc)})

        except zipfile.BadZipFile:
            raise ValueError(f"ملف ZIP تالف: {backup}")

    def _restore_from_dir(
        self,
        backup: Path,
        target: Path,
        overwrite: bool,
        report: dict,
    ) -> None:
        """يستعيذ من مجلد نسخة احتياطية."""
        for item in backup.rglob("*"):
            rel = item.relative_to(backup)
            dest = target / rel

            try:
                if item.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                elif item.is_file():
                    if dest.exists() and not overwrite:
                        report["skipped"] += 1
                        continue

                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
                    report["restored_files"] += 1
            except PermissionError as exc:
                report["errors"].append({"file": str(item), "error": str(exc)})
            except OSError as exc:
                report["errors"].append({"file": str(item), "error": str(exc)})

    # ===================================================================
    #  عرض النسخ الاحتياطية
    # ===================================================================

    def list_backups(self, backup_dir: str | Path) -> list[dict]:
        """
        يعرض قائمة بجميع النسخ الاحتياطية في مجلد.

        المعاملات:
            backup_dir: مجلد النسخ الاحتياطية

        المعاد:
            قائمة بمعلومات النسخ الاحتياطية:
            [{"name": str, "path": str, "size": int, "created": str, "type": str}, ...]
        """
        dir_path = Path(backup_dir).resolve()

        if not dir_path.is_dir():
            raise FileNotFoundError(f"مجلد النسخ الاحتياطية غير موجود: {dir_path}")

        backups: list[dict] = []

        for item in sorted(dir_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                if item.is_file() and item.suffix.lower() == ".zip":
                    size = item.stat().st_size
                    created = datetime.fromtimestamp(item.stat().st_ctime).isoformat()

                    # محاولة قراءة البيانات الوصفية من ملف ZIP
                    manifest = self._read_manifest_from_zip(item)
                    extra_info = {}
                    if manifest:
                        extra_info = {
                            "source": manifest.get("source", ""),
                            "total_files": manifest.get("total_files", 0),
                            "label": manifest.get("label", ""),
                        }

                    backups.append({
                        "name": item.name,
                        "path": str(item.resolve()),
                        "size": size,
                        "size_formatted": self._format_size(size),
                        "created": created,
                        "type": "zip",
                        **extra_info,
                    })

                elif item.is_dir() and "backup_" in item.name.lower():
                    # حساب حجم المجلد
                    size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    created = datetime.fromtimestamp(item.stat().st_ctime).isoformat()

                    backups.append({
                        "name": item.name,
                        "path": str(item.resolve()),
                        "size": size,
                        "size_formatted": self._format_size(size),
                        "created": created,
                        "type": "directory",
                    })

            except PermissionError as exc:
                logger.warning("لا صلاحية لقراءة %s: %s", item, exc)
            except OSError as exc:
                logger.warning("خطأ في %s: %s", item, exc)

        logger.info("عرض %d نسخة احتياطية في %s", len(backups), dir_path)
        return backups

    # ===================================================================
    #  تنظيف النسخ القديمة
    # ===================================================================

    def cleanup_old_backups(
        self,
        backup_dir: str | Path,
        keep_last: int = 5,
        dry_run: bool = False,
    ) -> dict:
        """
        يحذف النسخ الاحتياطية القديمة مع الاحتفاظ بأحدثها.

        المعاملات:
            backup_dir: مجلد النسخ الاحتياطية
            keep_last: عدد النسخ المراد الاحتفاظ بها
            dry_run: عرض ما سيُحذف بدون حذف فعلًا

        المعاد:
            تقرير التنظيف:
            {"kept": [str, ...], "deleted": [str, ...], "freed_space": int}
        """
        dir_path = Path(backup_dir).resolve()

        if not dir_path.is_dir():
            raise FileNotFoundError(f"مجلد النسخ الاحتياطية غير موجود: {dir_path}")

        all_backups = self.list_backups(dir_path)
        report: dict = {
            "kept": [],
            "deleted": [],
            "freed_space": 0,
        }

        if len(all_backups) <= keep_last:
            report["kept"] = [b["path"] for b in all_backups]
            logger.info("لا حاجة للتنظيف — النسخ (%d) ≤ الحد المطلوب (%d)", len(all_backups), keep_last)
            return report

        # النسخ المراد حذفها (الأقدم)
        to_delete = all_backups[keep_last:]
        to_keep = all_backups[:keep_last]

        for backup_info in to_delete:
            backup_path = Path(backup_info["path"])
            report["deleted"].append(str(backup_path))
            report["freed_space"] += backup_info["size"]

            if not dry_run:
                try:
                    if backup_path.is_dir():
                        shutil.rmtree(backup_path)
                    elif backup_path.is_file():
                        backup_path.unlink()
                    logger.info("تم حذف: %s", backup_path.name)
                except PermissionError as exc:
                    logger.error("لا صلاحية لحذف %s: %s", backup_path, exc)
                except OSError as exc:
                    logger.error("خطأ أثناء حذف %s: %s", backup_path, exc)
            else:
                logger.info("[محاكاة] سيتم حذف: %s", backup_path.name)

        report["kept"] = [b["path"] for b in to_keep]

        # تسجيل العملية
        operation = {
            "timestamp": datetime.now().isoformat(),
            "action": "cleanup_old_backups",
            "backup_dir": str(dir_path),
            "keep_last": keep_last,
            "deleted_count": len(report["deleted"]),
            "freed_space": report["freed_space"],
            "dry_run": dry_run,
        }
        self._operation_log.append(operation)

        logger.info(
            "اكتمل التنظيف — محذوف: %d | محفوظ: %d | مساحة محررة: %s",
            len(report["deleted"]), len(report["kept"]),
            self._format_size(report["freed_space"]),
        )

        return report

    # ===================================================================
    #  حجم النسخة الاحتياطية
    # ===================================================================

    def get_backup_size(self, backup_path: str | Path) -> dict:
        """
        يعرض معلومات الحجم لنسخة احتياطية.

        المعاملات:
            backup_path: مسار النسخة الاحتياطية

        المعاد:
            {"path": str, "size_bytes": int, "size_formatted": str, "type": str}
        """
        path = Path(backup_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"النسخة الاحتياطية غير موجودة: {path}")

        try:
            if path.is_file():
                size = path.stat().st_size
                btype = "zip"
            elif path.is_dir():
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                btype = "directory"
            else:
                return {"path": str(path), "size_bytes": 0, "size_formatted": "0 B", "type": "unknown"}
        except PermissionError as exc:
            logger.error("لا صلاحية لقراءة: %s", path)
            raise

        return {
            "path": str(path),
            "size_bytes": size,
            "size_formatted": self._format_size(size),
            "type": btype,
        }

    # ===================================================================
    #  بيانات التجزئة (للنسخ التزايدي)
    # ===================================================================

    def _hash_file(self, file_path: Path) -> str:
        """
        يحسب تجزئة SHA-256 لملف.

        المعاملات:
            file_path: مسار الملف

        المعاد:
            سلسلة التجزئة السداسية عشرية
        """
        hasher = hashlib.new(self.HASH_ALGORITHM)
        try:
            with open(file_path, "rb") as f:
                # قراءة بأجزاء للمفاتيح الكبيرة
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except PermissionError:
            logger.warning("لا صلاحية لتجزئة: %s", file_path)
            return ""
        except OSError as exc:
            logger.warning("خطأ أثناء تجزئة %s: %s", file_path, exc)
            return ""

    def _is_file_changed(self, file_path: Path, source: Path) -> bool:
        """
        يتحقق مما إذا كان الملف قد تغيّر منذ آخر نسخة احتياطية.

        المعاملات:
            file_path: مسار الملف الحالي
            source: مجلد المصدر

        المعاد:
            True إذا كان الملف جديداً أو معدّلاً
        """
        rel = str(file_path.relative_to(source))
        current_hash = self._hash_file(file_path)

        if not current_hash:
            return True  # في حالة الخطأ، نأخذ الاحتياط

        stored_hash = self._file_hashes.get(rel)
        if stored_hash is None or stored_hash != current_hash:
            return True

        return False

    def load_hashes(self, backup_dir: str | Path) -> None:
        """
        يحمّل تجزئات الملفات من آخر نسخة احتياطية لتمكين النسخ التزايدي.

        المعاملات:
            backup_dir: مجلد النسخ الاحتياطية
        """
        dir_path = Path(backup_dir).resolve()
        if not dir_path.is_dir():
            return

        # البحث عن أحدث نسخة احتياطية
        backups = self.list_backups(dir_path)
        if not backups:
            logger.info("لا توجد نسخ احتياطية سابقة لتحميل التجزئات")
            return

        latest = backups[0]
        latest_path = Path(latest["path"])

        if latest["type"] == "zip":
            hashes = self._read_hashes_from_zip(latest_path)
        elif latest["type"] == "directory":
            hashes = self._read_hashes_from_dir(latest_path)
        else:
            return

        if hashes:
            self._file_hashes = hashes
            logger.info("تم تحميل %d تجزئة من النسخة السابقة", len(hashes))

    def _read_hashes_from_zip(self, zip_path: Path) -> dict[str, str]:
        """يقرأ تجزئات الملفات من أرشيف ZIP."""
        hashes: dict[str, str] = {}
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                manifest_name = self.MANIFEST_FILENAME
                if manifest_name in zf.namelist():
                    data = json.loads(zf.read(manifest_name))
                    hashes = data.get("file_hashes", {})
        except (zipfile.BadZipFile, json.JSONDecodeError, KeyError) as exc:
            logger.warning("تعذرت قراءة التجزئات من ZIP: %s", exc)
        return hashes

    def _read_hashes_from_dir(self, dir_path: Path) -> dict[str, str]:
        """يقرأ تجزئات الملفات من مجلد نسخة احتياطية."""
        manifest_path = dir_path / self.MANIFEST_FILENAME
        if manifest_path.is_file():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                return data.get("file_hashes", {})
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("تعذرت قراءة التجزئات من المجلد: %s", exc)
        return {}

    # ===================================================================
    #  البيانات الوصفية (Manifest)
    # ===================================================================

    def _save_manifest(self, backup_path: Path, info: dict) -> None:
        """يحفظ بيانات وصفية للنسخة الاحتياطية."""
        manifest = {
            "version": "1.0",
            "created": info["timestamp"],
            "source": info["source"],
            "total_files": info["total_files"],
            "total_size": info["total_size"],
            "compressed": info["compressed"],
            "incremental": info["incremental"],
            "label": info.get("label", ""),
            "file_hashes": dict(self._file_hashes) if self.incremental else {},
        }

        manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)

        try:
            if backup_path.is_file() and backup_path.suffix.lower() == ".zip":
                # إضافة البيانات الوصفية إلى أرشيف ZIP
                with zipfile.ZipFile(backup_path, "a") as zf:
                    zf.writestr(self.MANIFEST_FILENAME, manifest_json)
            else:
                # حفظ كملف في مجلد النسخة الاحتياطية
                manifest_file = backup_path / self.MANIFEST_FILENAME
                manifest_file.write_text(manifest_json, encoding="utf-8")
        except Exception as exc:
            logger.warning("تعذر حفظ البيانات الوصفية: %s", exc)

    def _read_manifest_from_zip(self, zip_path: Path) -> Optional[dict]:
        """يقرأ البيانات الوصفية من أرشيف ZIP."""
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                if self.MANIFEST_FILENAME in zf.namelist():
                    data = json.loads(zf.read(self.MANIFEST_FILENAME))
                    return data
        except (zipfile.BadZipFile, json.JSONDecodeError, OSError) as exc:
            logger.debug("تعذرت قراءة البيانات الوصفية: %s", exc)
        return None

    # ===================================================================
    #  أدوات مساعدة
    # ===================================================================

    def _should_exclude(self, path: Path, base: Path) -> bool:
        """
        يتحقق مما إذا كان يجب استبعاد الملف/المجلد.

        المعاملات:
            path: مسار الملف
            base: مجلد المصدر الأساسي

        المعاد:
            True إذا كان يجب الاستبعاد
        """
        import fnmatch

        # استبعاد مجلدات معينة
        skip_dirs = {
            "__pycache__", ".git", ".svn", ".hg", "node_modules",
            ".tox", ".venv", "venv", "env",
            ".mypy_cache", ".pytest_cache", ".ruff_cache",
            "dist", "build", ".eggs",
        }

        rel = path.relative_to(base)
        for part in rel.parts:
            if part in skip_dirs:
                return True

        # استبعاد الملف المخفي للنسخ الاحتياطية
        if path.name == self.MANIFEST_FILENAME:
            return True

        # فحص أنماط الاستبعاد
        for pattern in self.exclude_patterns:
            try:
                if fnmatch.fnmatch(str(rel), pattern) or fnmatch.fnmatch(path.name, pattern):
                    return True
            except Exception:
                continue

        return False

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """
        يحوّل الحجم بالبايت إلى صيغة مقروءة.

        المعاملات:
            size_bytes: الحجم بالبايت

        المعاد:
            الحجم بصيغة مقروءة (مثل "15.3 MB")
        """
        if size_bytes < 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"

    def get_operation_log(self) -> list[dict]:
        """
        يعرض سجل جميع عمليات النسخ الاحتياطي.

        المعاد:
            قائمة بعمليات النسخ والاستعادة
        """
        return list(self._operation_log)

    def clear_operation_log(self) -> None:
        """يمسح سجل العمليات."""
        self._operation_log.clear()
        logger.info("تم مسح سجل العمليات")
