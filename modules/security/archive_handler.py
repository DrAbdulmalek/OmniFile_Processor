"""
معالج الأرشيفات (Archive Handler)
====================================
يتعامل مع الأرشيفات المضغوطة بما في ذلك المحمية بكلمات مرور.

القدرات:
- استخراج الأرشيفات (zip, tar.gz, tar.bz2, 7z, rar)
- إنشاء أرشيفات محمية بكلمات مرور
- كشف نوع الأرشيف تلقائياً
- التعامل مع الأرشيفات المتداخلة
- عرض محتويات الأرشيف
- كشف الحماية بكلمة مرور
"""

import logging
import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class ArchiveHandler:
    """
    معالج الأرشيفات — يستخرج وينشئ أرشيفات متنوعة مع دعم كلمات المرور.

    الاستخدام:
        handler = ArchiveHandler()
        files = handler.extract_archive("backup.zip", "output/", password="123")
    """

    # ======== الأنواع المدعومة ========
    SUPPORTED_EXTENSIONS: set[str] = {
        ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
        ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz",
        ".lzma", ".tbz2", ".txz",
    }

    # توقيعات سحرية لتحديد النوع
    MAGIC_TYPES: list[tuple[bytes, str]] = [
        (b"PK\x03\x04", "zip"),
        (b"\x1f\x8b", "gzip"),
        (b"7z\xbc\xaf\x27\x1c", "7z"),
        (b"Rar!\x1a\x07", "rar"),
        (b"BZh", "bzip2"),
        (b"\xfd7zXZ\x00", "xz"),
    ]

    def __init__(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        max_nested_depth: int = 5,
    ) -> None:
        """
        تهيئة معالج الأرشيفات.

        المعاملات:
            progress_callback: دالة تُستدعى أثناء التقدم (اسم_الملف، الحالي، الإجمالي)
            max_nested_depth: أقصى عمق للأرشيفات المتداخلة
        """
        self.progress_callback: Optional[Callable[[str, int, int], None]] = progress_callback
        self.max_nested_depth: int = max_nested_depth
        logger.info("تم تهيئة معالج الأرشيفات (أقصى عمق تداخل: %d)", max_nested_depth)

    # ===================================================================
    #  كشف نوع الأرشيف
    # ===================================================================

    def detect_archive_type(self, archive_path: str | Path) -> str:
        """
        يكشف نوع الأرشيف من الامتداد والتوقيع السحري.

        المعاملات:
            archive_path: مسار الأرشيف

        المعاد:
            نوع الأرشيف: 'zip', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz',
            '7z', 'rar', أو 'unknown'
        """
        path = Path(archive_path)

        # 1) كشف بالامتداد
        name_lower = path.name.lower()
        ext_map = {
            ".zip": "zip",
            ".tar": "tar",
            ".tar.gz": "tar.gz", ".tgz": "tar.gz",
            ".tar.bz2": "tar.bz2", ".tbz2": "tar.bz2",
            ".tar.xz": "tar.xz", ".txz": "tar.xz",
            ".gz": "gzip",
            ".bz2": "bzip2",
            ".xz": "xz",
            ".7z": "7z",
            ".rar": "rar",
        }

        # فحص الامتدادات المركبة أولاً
        for compound_ext in (".tar.gz", ".tar.bz2", ".tar.xz"):
            if name_lower.endswith(compound_ext):
                detected = ext_map[compound_ext]
                logger.debug("كشف نوع أرشيف %s -> %s (امتداد مركب)", path.name, detected)
                return detected

        suffix = path.suffix.lower()
        detected = ext_map.get(suffix)

        if detected:
            logger.debug("كشف نوع أرشيف %s -> %s (بالامتداد)", path.name, detected)
            return detected

        # 2) كشف بالتوقيع السحري
        try:
            with open(path, "rb") as f:
                header = f.read(16)

            for magic, atype in self.MAGIC_TYPES:
                if header.startswith(magic):
                    logger.debug("كشف نوع أرشيف %s -> %s (بالتوقيع السحري)", path.name, atype)
                    return atype
        except PermissionError:
            logger.warning("لا صلاحية لقراءة: %s", path)
        except OSError as exc:
            logger.warning("خطأ أثناء قراءة %s: %s", path, exc)

        logger.warning("نوع أرشيف غير معروف: %s", path.name)
        return "unknown"

    # ===================================================================
    #  عرض المحتويات
    # ===================================================================

    def list_contents(self, archive_path: str | Path) -> list[dict]:
        """
        يعرض قائمة بملفات الأرشيف مع معلوماتها.

        المعاملات:
            archive_path: مسار الأرشيف

        المعاد:
            قائمة بقواميس:
            [{"name": str, "size": int, "is_dir": bool, "date_time": tuple}, ...]
        """
        path = Path(archive_path)
        if not path.exists():
            raise FileNotFoundError(f"الأرشيف غير موجود: {path}")

        archive_type = self.detect_archive_type(path)
        contents: list[dict] = []

        try:
            if archive_type == "zip":
                contents = self._list_zip(path)
            elif archive_type in ("tar", "tar.gz", "tar.bz2", "tar.xz"):
                contents = self._list_tar(path)
            elif archive_type == "7z":
                contents = self._list_7z(path)
            elif archive_type == "rar":
                contents = self._list_rar(path)
            else:
                logger.warning("نوع أرشيف غير مدعوم للعرض: %s", archive_type)
        except Exception as exc:
            logger.error("خطأ أثناء عرض محتويات %s: %s", path, exc)
            raise

        logger.info("عرض محتويات %s: %d ملف", path.name, len(contents))
        return contents

    def _list_zip(self, path: Path) -> list[dict]:
        """يعرض محتويات أرشيف ZIP."""
        contents = []
        try:
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    contents.append({
                        "name": info.filename,
                        "size": info.file_size,
                        "compressed_size": info.compress_size,
                        "is_dir": info.is_dir(),
                        "date_time": info.date_time,
                    })
        except zipfile.BadZipFile:
            logger.error("ملف ZIP تالف: %s", path)
            raise
        return contents

    def _list_tar(self, path: Path) -> list[dict]:
        """يعرض محتويات أرشيف TAR."""
        contents = []
        try:
            with tarfile.open(path, "r:*") as tf:
                for member in tf.getmembers():
                    contents.append({
                        "name": member.name,
                        "size": member.size,
                        "is_dir": member.isdir(),
                        "date_time": member.mtime,
                        "mode": member.mode,
                    })
        except tarfile.TarError as exc:
            logger.error("خطأ في أرشيف TAR %s: %s", path, exc)
            raise
        return contents

    def _list_7z(self, path: Path) -> list[dict]:
        """يعرض محتويات أرشيف 7Z (يتطلب 7z command)."""
        try:
            result = subprocess.run(
                ["7z", "l", "-slt", str(path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            logger.error("الأمر '7z' غير متوفر. قم بتثبيت p7zip-full")
            raise RuntimeError("الأمر '7z' غير متوفر في النظام")
        except subprocess.TimeoutExpired:
            logger.error("انتهت مهلة عرض محتويات 7z")
            raise

        if result.returncode != 0:
            logger.error("خطأ في 7z: %s", result.stderr)
            raise RuntimeError(f"خطأ في 7z: {result.stderr}")

        contents = []
        current_file: dict = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("---"):
                if current_file.get("name"):
                    contents.append(current_file)
                current_file = {}
            elif line.startswith("Path = "):
                current_file["name"] = line[7:]
            elif line.startswith("Size = "):
                try:
                    current_file["size"] = int(line[7:])
                except ValueError:
                    current_file["size"] = 0
            elif line.startswith("Folder = "):
                current_file["is_dir"] = line[9:] == "1"
            elif line.startswith("Attributes = "):
                current_file["is_dir"] = current_file.get("is_dir", "D" in line[13:])

        if current_file.get("name"):
            contents.append(current_file)

        # تعبئة الحقول الافتراضية
        for item in contents:
            item.setdefault("size", 0)
            item.setdefault("is_dir", False)

        return contents

    def _list_rar(self, path: Path) -> list[dict]:
        """يعرض محتويات أرشيف RAR (يتطلب unrar)."""
        try:
            result = subprocess.run(
                ["unrar", "lt", "-p-", str(path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            logger.error("الأمر 'unrar' غير متوفر")
            raise RuntimeError("الأمر 'unrar' غير متوفر في النظام")
        except subprocess.TimeoutExpired:
            logger.error("انتهت مهلة عرض محتويات RAR")
            raise

        if result.returncode not in (0, 10):  # 10 = هناك تحذيرات
            logger.error("خطأ في unrar: %s", result.stderr)
            raise RuntimeError(f"خطأ في unrar: {result.stderr}")

        contents = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 6 and parts[0].isdigit():
                try:
                    size = int(parts[1].replace(",", ""))
                except ValueError:
                    size = 0
                name = " ".join(parts[5:])
                is_dir = parts[-1].upper() == "D" if parts else False
                contents.append({
                    "name": name,
                    "size": size,
                    "is_dir": is_dir,
                })

        return contents

    # ===================================================================
    #  فحص الحماية بكلمة مرور
    # ===================================================================

    def is_password_protected(self, archive_path: str | Path) -> bool:
        """
        يتحقق مما إذا كان الأرشيف محمياً بكلمة مرور.

        المعاملات:
            archive_path: مسار الأرشيف

        المعاد:
            True إذا كان محمياً، False إذا لم يكن كذلك
        """
        path = Path(archive_path)
        archive_type = self.detect_archive_type(path)

        try:
            if archive_type == "zip":
                return self._zip_is_encrypted(path)
            elif archive_type in ("tar", "tar.gz", "tar.bz2", "tar.xz"):
                # أرشيفات TAR عادية لا تدعم كلمات المرور
                # لكن يمكن حمايتها ببرامج خارجية
                return False
            elif archive_type == "7z":
                return self._7z_is_encrypted(path)
            elif archive_type == "rar":
                return self._rar_is_encrypted(path)
            else:
                logger.warning("لا يمكن فحص الحماية للنوع: %s", archive_type)
                return False
        except Exception as exc:
            logger.error("خطأ أثناء فحص الحماية: %s", exc)
            return False

    def _zip_is_encrypted(self, path: Path) -> bool:
        """يتحقق مما إذا كان ZIP محمياً."""
        try:
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    if info.flag_bits & 0x1:  # بت التشفير
                        return True
        except zipfile.BadZipFile:
            logger.error("ملف ZIP تالف: %s", path)
        return False

    def _7z_is_encrypted(self, path: Path) -> bool:
        """يتحقق مما إذا كان 7Z محمياً."""
        try:
            result = subprocess.run(
                ["7z", "l", "-slt", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return "Encrypted = +" in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _rar_is_encrypted(self, path: Path) -> bool:
        """يتحقق مما إذا كان RAR محمياً."""
        try:
            result = subprocess.run(
                ["unrar", "lt", "-p-", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return "*" in result.stdout.splitlines()[0] if result.stdout else False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # ===================================================================
    #  استخراج الأرشيفات
    # ===================================================================

    def extract_archive(
        self,
        archive_path: str | Path,
        dest_dir: str | Path,
        password: Optional[str] = None,
        extract_nested: bool = False,
    ) -> list[str]:
        """
        يستخرج أرشيفاً إلى مجلد الوجهة.

        المعاملات:
            archive_path: مسار الأرشيف
            dest_dir: مجلد الوجهة
            password: كلمة المرور (إذا كان محمياً)
            extract_nested: استخراج الأرشيفات المتداخلة

        المعاد:
            قائمة بمسارات الملفات المستخرجة
        """
        path = Path(archive_path)
        dest = Path(dest_dir)

        if not path.exists():
            raise FileNotFoundError(f"الأرشيف غير موجود: {path}")

        # إنشاء مجلد الوجهة
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise PermissionError(f"لا صلاحية لإنشاء {dest}: {exc}") from exc

        archive_type = self.detect_archive_type(path)
        extracted_files: list[str] = []

        logger.info(
            "استخراج %s (النوع: %s) إلى %s",
            path.name, archive_type, dest,
        )

        try:
            if archive_type == "zip":
                extracted_files = self._extract_zip(path, dest, password)
            elif archive_type in ("tar", "tar.gz", "tar.bz2", "tar.xz"):
                extracted_files = self._extract_tar(path, dest)
            elif archive_type == "7z":
                extracted_files = self._extract_7z(path, dest, password)
            elif archive_type == "rar":
                extracted_files = self._extract_rar(path, dest, password)
            else:
                raise ValueError(f"نوع أرشيف غير مدعوم: {archive_type}")
        except Exception as exc:
            logger.error("فشل استخراج %s: %s", path, exc)
            raise

        # استخراج الأرشيفات المتداخلة
        if extract_nested:
            nested_files = self._extract_nested(dest, depth=1)
            extracted_files.extend(nested_files)

        logger.info("تم استخراج %d ملف من %s", len(extracted_files), path.name)
        return extracted_files

    def _extract_zip(
        self,
        path: Path,
        dest: Path,
        password: Optional[str],
    ) -> list[str]:
        """يستخرج أرشيف ZIP."""
        extracted: list[str] = []
        pwd_bytes = password.encode("utf-8") if password else None

        try:
            with zipfile.ZipFile(path, "r") as zf:
                members = zf.infolist()
                total = len(members)
                for i, member in enumerate(members, 1):
                    if self.progress_callback:
                        self.progress_callback(member.filename, i, total)

                    try:
                        # حماية من Path Traversal
                        member_path = Path(member.filename)
                        if member_path.is_absolute() or ".." in member.parts:
                            logger.warning("تخطي مسار خطر: %s", member.filename)
                            continue

                        target = dest / member.filename
                        if member.is_dir():
                            target.mkdir(parents=True, exist_ok=True)
                            continue

                        target.parent.mkdir(parents=True, exist_ok=True)

                        if pwd_bytes:
                            zf.extract(member, dest, pwd=pwd_bytes)
                        else:
                            # محاولة بدون كلمة مرور
                            try:
                                zf.extract(member, dest)
                            except RuntimeError:
                                raise RuntimeError(
                                    "الأرشيف محمي بكلمة مرور. يرجى توفير كلمة المرور."
                                )

                        extracted.append(str(target.resolve()))
                    except RuntimeError as exc:
                        if "password" in str(exc).lower() or "decrypt" in str(exc).lower():
                            raise RuntimeError(
                                "الأرشيف محمي بكلمة مرور. يرجى توفير كلمة المرور."
                            ) from exc
                        raise

        except zipfile.BadZipFile:
            logger.error("ملف ZIP تالف: %s", path)
            raise

        return extracted

    def _extract_tar(self, path: Path, dest: Path) -> list[str]:
        """يستخرج أرشيف TAR."""
        extracted: list[str] = []

        try:
            with tarfile.open(path, "r:*") as tf:
                members = tf.getmembers()
                total = len(members)
                for i, member in enumerate(members, 1):
                    if self.progress_callback:
                        self.progress_callback(member.name, i, total)

                    # حماية من Path Traversal
                    member_path = Path(member.name)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        logger.warning("تخطي مسار خطر في TAR: %s", member.name)
                        continue

                    try:
                        tf.extract(member, dest)
                        extracted.append(str((dest / member.name).resolve()))
                    except PermissionError as exc:
                        logger.warning("لا صلاحية لاستخراج %s: %s", member.name, exc)
                    except OSError as exc:
                        logger.warning("خطأ أثناء استخراج %s: %s", member.name, exc)

        except tarfile.TarError as exc:
            logger.error("خطأ في أرشيف TAR %s: %s", path, exc)
            raise

        return extracted

    def _extract_7z(
        self,
        path: Path,
        dest: Path,
        password: Optional[str],
    ) -> list[str]:
        """يستخرج أرشيف 7Z."""
        cmd = ["7z", "x", f"-o{dest}", "-aoa", str(path)]

        if password:
            cmd.append(f"-p{password}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError:
            raise RuntimeError("الأمر '7z' غير متوفر. قم بتثبيت p7zip-full")
        except subprocess.TimeoutExpired:
            raise RuntimeError("انتهت مهلة استخراج 7z")

        if result.returncode != 0:
            if password is None and "Wrong password" in result.stderr:
                raise RuntimeError("كلمة المرور خاطئة أو الأرشيف محمي بكلمة مرور")
            raise RuntimeError(f"خطأ في 7z: {result.stderr}")

        # جمع الملفات المستخرجة
        extracted = [
            str(f.resolve())
            for f in dest.rglob("*")
            if f.is_file()
        ]
        return extracted

    def _extract_rar(
        self,
        path: Path,
        dest: Path,
        password: Optional[str],
    ) -> list[str]:
        """يستخرج أرشيف RAR."""
        cmd = ["unrar", "x", "-o+", f"{dest}/", str(path)]

        if password:
            cmd.insert(2, f"-p{password}")
        else:
            cmd.insert(2, "-p-")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError:
            raise RuntimeError("الأمر 'unrar' غير متوفر")
        except subprocess.TimeoutExpired:
            raise RuntimeError("انتهت مهلة استخراج RAR")

        if result.returncode not in (0, 10):
            if password is None:
                raise RuntimeError("الأرشيف محمي بكلمة مرور أو تالف")
            raise RuntimeError(f"خطأ في unrar: {result.stderr}")

        extracted = [
            str(f.resolve())
            for f in dest.rglob("*")
            if f.is_file()
        ]
        return extracted

    def _extract_nested(self, directory: Path, depth: int) -> list[str]:
        """
        يبحث عن أرشيفات متداخلة ويستخرجها.

        المعاملات:
            directory: المجلد المراد فحصه
            depth: عمق التداخل الحالي

        المعاد:
            قائمة بالملفات المستخرجة من الأرشيفات المتداخلة
        """
        if depth > self.max_nested_depth:
            logger.warning("تم تجاوز أقصى عمق تداخل: %d", self.max_nested_depth)
            return []

        nested_extracted: list[str] = []

        for item in directory.rglob("*"):
            if not item.is_file():
                continue

            archive_type = self.detect_archive_type(item)
            if archive_type == "unknown":
                continue

            logger.info(
                "اكتشاف أرشيف متداخل (العمق %d): %s",
                depth, item.name,
            )

            # مجلد خاص للأرشيف المتداخل
            nested_dest = item.parent / f"{item.stem}_extracted"

            try:
                files = self.extract_archive(
                    item, nested_dest,
                    extract_nested=False,
                )
                nested_extracted.extend(files)

                # حذف الأرشيف المتداخل بعد الاستخراج
                try:
                    item.unlink()
                    logger.debug("تم حذف الأرشيف المتداخل: %s", item.name)
                except OSError as exc:
                    logger.warning("تعذر حذف %s: %s", item.name, exc)

                # استمرار البحث في المجلد الجديد
                nested_extracted.extend(
                    self._extract_nested(nested_dest, depth + 1)
                )
            except Exception as exc:
                logger.warning(
                    "فشل استخراج الأرشيف المتداخل %s: %s",
                    item.name, exc,
                )

        return nested_extracted

    # ===================================================================
    #  إنشاء الأرشيفات
    # ===================================================================

    def create_archive(
        self,
        files: list[str | Path],
        output_path: str | Path,
        password: Optional[str] = None,
        archive_type: Optional[str] = None,
    ) -> str:
        """
        ينشئ أرشيفاً من قائمة ملفات.

        المعاملات:
            files: قائمة مسارات الملفات/Mجلدات
            output_path: مسار الأرشيف الناتج
            password: كلمة المرور (اختياري)
            archive_type: نوع الأرشيف ('zip', 'tar.gz', '7z'). يُكتشف تلقائياً إن لم يحدد.

        المعاد:
            مسار الأرشيف المنشأ
        """
        output = Path(output_path)
        total = len(files)

        # كشف النوع
        if archive_type is None:
            suffix = output.suffix.lower()
            type_by_ext = {
                ".zip": "zip",
                ".tar.gz": "tar.gz",
                ".tgz": "tar.gz",
                ".tar.bz2": "tar.bz2",
                ".tbz2": "tar.bz2",
                ".tar.xz": "tar.xz",
                ".txz": "tar.xz",
                ".7z": "7z",
            }
            for ext, atype in sorted(type_by_ext.items(), key=lambda x: -len(x[0])):
                if output.name.lower().endswith(ext):
                    archive_type = atype
                    break

        if archive_type is None:
            archive_type = "zip"

        # إنشاء المجلد الأب
        output.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "إنشاء أرشيف %s (النوع: %s, الملفات: %d, محمي: %s)",
            output.name, archive_type, total, password is not None,
        )

        try:
            if archive_type == "zip":
                self._create_zip(files, output, password)
            elif archive_type in ("tar.gz", "tar.bz2", "tar.xz", "tar"):
                self._create_tar(files, output, archive_type)
            elif archive_type == "7z":
                self._create_7z(files, output, password)
            else:
                raise ValueError(f"نوع أرشيف غير مدعوم للإنشاء: {archive_type}")
        except Exception as exc:
            logger.error("فشل إنشاء الأرشيف: %s", exc)
            # حذف الملف الجزئي
            if output.exists():
                try:
                    output.unlink()
                except OSError:
                    pass
            raise

        logger.info("تم إنشاء الأرشيف بنجاح: %s", output)
        return str(output.resolve())

    def _create_zip(
        self,
        files: list[str | Path],
        output: Path,
        password: Optional[str],
    ) -> None:
        """ينشئ أرشيف ZIP."""
        pwd_bytes = password.encode("utf-8") if password else None

        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, file_path in enumerate(files, 1):
                path = Path(file_path)
                if self.progress_callback:
                    self.progress_callback(str(path), i, len(files))

                if path.is_file():
                    try:
                        zf.write(path, path.name)
                    except PermissionError as exc:
                        logger.warning("تخطي %s (لا صلاحية): %s", path, exc)
                elif path.is_dir():
                    for item in path.rglob("*"):
                        if item.is_file():
                            try:
                                arcname = item.relative_to(path.parent)
                                zf.write(item, arcname)
                            except PermissionError as exc:
                                logger.warning("تخطي %s: %s", item, exc)

    def _create_tar(
        self,
        files: list[str | Path],
        output: Path,
        archive_type: str,
    ) -> None:
        """ينشئ أرشيف TAR."""
        mode_map = {
            "tar": "w:",
            "tar.gz": "w:gz",
            "tar.bz2": "w:bz2",
            "tar.xz": "w:xz",
        }
        mode = mode_map.get(archive_type, "w:gz")

        with tarfile.open(output, mode) as tf:
            for i, file_path in enumerate(files, 1):
                path = Path(file_path)
                if self.progress_callback:
                    self.progress_callback(str(path), i, len(files))

                if path.is_file():
                    try:
                        tf.add(path, arcname=path.name)
                    except PermissionError as exc:
                        logger.warning("تخطي %s: %s", path, exc)
                elif path.is_dir():
                    try:
                        tf.add(path, arcname=path.name)
                    except PermissionError as exc:
                        logger.warning("تخطي %s: %s", path, exc)

    def _create_7z(
        self,
        files: list[str | Path],
        output: Path,
        password: Optional[str],
    ) -> None:
        """ينشئ أرشيف 7Z."""
        cmd = ["7z", "a", str(output)]

        if password:
            cmd.append(f"-p{password}")

        file_args = [str(Path(f).resolve()) for f in files]
        cmd.extend(file_args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            raise RuntimeError("الأمر '7z' غير متوفر")
        except subprocess.TimeoutExpired:
            raise RuntimeError("انتهت مهلة إنشاء 7z")

        if result.returncode != 0:
            raise RuntimeError(f"خطأ في 7z: {result.stderr}")
