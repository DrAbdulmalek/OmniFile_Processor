"""
منظّم الملفات التلقائي (File Organizer)
=========================================
يُفرّق الملفات تلقائياً إلى فئات بناءً على تحليل المحتوى والامتداد.

الفئات المدعومة:
    - code: ملفات البرمجة
    - documents: المستندات والنصوص
    - images: الصور والرسومات
    - archives: الأرشيفات المضغوطة
    - data: ملفات البيانات المهيكلة
    - notebooks: دفاتر الملاحظات
    - configs: ملفات الإعدادات والتهيئة
"""

import logging
import shutil
from pathlib import Path
from typing import Optional, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


class FileOrganizer:
    """
    منظم الملفات التلقائي — يفرّق الملفات إلى فئات بناءً على الامتداد
    ومحتوى الملف (أول بضعة بايتات).

    الاستخدام:
        organizer = FileOrganizer()
        report = organizer.organize_directory(
            source_dir="/path/to/messy",
            target_dir="/path/to/organized"
        )
    """

    # ======== تعريف الفئات والامتدادات ========

    # خريطة الامتدادات → فئة
    EXTENSION_MAP: dict[str, str] = {
        # --- ملفات البرمجة (code) ---
        ".py": "code", ".pyw": "code", ".pyi": "code",
        ".js": "code", ".jsx": "code", ".mjs": "code", ".cjs": "code",
        ".ts": "code", ".tsx": "code",
        ".java": "code", ".kt": "code", ".kts": "code", ".scala": "code",
        ".c": "code", ".h": "code", ".cpp": "code", ".hpp": "code", ".cc": "code",
        ".cs": "code", ".vb": "code",
        ".go": "code", ".rs": "code", ".swift": "code",
        ".rb": "code", ".rake": "code",
        ".php": "code",
        ".pl": "code", ".pm": "code", ".r": "code",
        ".lua": "code", ".vim": "code",
        ".sh": "code", ".bash": "code", ".zsh": "code", ".fish": "code",
        ".ps1": "code", ".bat": "code", ".cmd": "code",
        ".sql": "code",
        ".dart": "code", ".clj": "code", ".ex": "code", ".exs": "code",
        ".hs": "code", ".ml": "code", ".lisp": "code",
        ".m": "code", ".mm": "code",
        ".dart": "code",
        ".proto": "code", ".thrift": "code",
        ".dockerfile": "code",
        ".cmake": "code", ".makefile": "code",
        ".gradle": "code", ".sbt": "code",
        ".vue": "code", ".svelte": "code", ".html": "code", ".htm": "code",
        ".css": "code", ".scss": "code", ".sass": "code", ".less": "code",
        ".xml": "code", ".xsl": "code", ".xslt": "code", ".xsd": "code",
        ".json": "code", ".yaml": "code", ".yml": "code", ".toml": "code",
        ".graphql": "code", ".gql": "code",

        # --- المستندات (documents) ---
        ".pdf": "documents", ".doc": "documents", ".docx": "documents",
        ".odt": "documents", ".rtf": "documents",
        ".txt": "documents", ".md": "documents", ".rst": "documents",
        ".tex": "documents", ".latex": "documents",
        ".pptx": "documents", ".ppt": "documents", ".odp": "documents",
        ".xls": "documents", ".xlsx": "documents", ".ods": "documents",
        ".csv": "documents",
        ".epub": "documents", ".mobi": "documents",
        ".pages": "documents", ".numbers": "documents",

        # --- الصور (images) ---
        ".png": "images", ".jpg": "images", ".jpeg": "images",
        ".gif": "images", ".bmp": "images", ".tiff": "images", ".tif": "images",
        ".webp": "images", ".svg": "images", ".ico": "images", ".cur": "images",
        ".psd": "images", ".ai": "images", ".eps": "images",
        ".raw": "images", ".cr2": "images", ".nef": "images",
        ".heic": "images", ".heif": "images",
        ".avif": "images", ".jxl": "images",

        # --- الأرشيفات (archives) ---
        ".zip": "archives", ".tar": "archives",
        ".gz": "archives", ".bz2": "archives", ".xz": "archives",
        ".7z": "archives", ".rar": "archives",
        ".tar.gz": "archives", ".tgz": "archives",
        ".tar.bz2": "archives", ".tbz2": "archives",
        ".tar.xz": "archives", ".txz": "archives",
        ".lzma": "archives", ".lz4": "archives",
        ".dmg": "archives", ".iso": "archives",

        # --- ملفات البيانات (data) ---
        ".json": "data", ".xml": "data",
        ".parquet": "data", ".arrow": "data",
        ".hdf5": "data", ".h5": "data",
        ".npy": "data", ".npz": "data",
        ".pkl": "data", ".pickle": "data",
        ".db": "data", ".sqlite": "data", ".sqlite3": "data",
        ".mdb": "data", ".accdb": "data",

        # --- دفاتر الملاحظات (notebooks) ---
        ".ipynb": "notebooks",
        ".pynb": "notebooks",

        # --- ملفات الإعدادات (configs) ---
        ".ini": "configs", ".cfg": "configs", ".conf": "configs",
        ".env": "configs", ".properties": "configs",
        ".editorconfig": "configs", ".gitignore": "configs",
        ".gitattributes": "configs",
        ".npmrc": "configs", ".nvmrc": "configs",
        ".dockerignore": "configs",
    }

    # --- توقيعات الملفات السحرية (Magic Bytes) ---
    MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
        # صور
        (b"\x89PNG\r\n\x1a\n", "images"),
        (b"\xff\xd8\xff", "images"),
        (b"GIF87a", "images"),
        (b"GIF89a", "images"),
        (b"BM", "images"),
        (b"II*\x00", "images"),      # TIFF (little-endian)
        (b"MM\x00*", "images"),      # TIFF (big-endian)
        (b"RIFF", "images"),          # WebP
        (b"<svg", "images"),
        # PDF
        (b"%PDF", "documents"),
        # أرشيفات
        (b"PK\x03\x04", "archives"),  # ZIP
        (b"\x1f\x8b", "archives"),    # GZIP
        (b"7z\xbc\xaf\x27\x1c", "archives"),
        (b"Rar!\x1a\x07", "archives"),
        # مستندات Office (ZIP-based)
        (b"PK\x03\x04", "documents"),  # يتم التعامل معها عبر الامتداد
    ]

    def __init__(
        self,
        mode: str = "move",
        dry_run: bool = False,
        overwrite: bool = False,
        skip_hidden: bool = True,
        skip_symlinks: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        """
        تهيئة المنظم.

        المعاملات:
            mode: وضع النقل — 'move' (نقل) أو 'copy' (نسخ)
            dry_run: إذا كان True، يعرض التقرير فقط بدون نقل أي ملف
            overwrite: إذا كان True، يستبدل الملفات الموجودة
            skip_hidden: تخطي الملفات المخفية (تبدأ بنقطة)
            skip_symlinks: تخطي الروابط الرمزية
            progress_callback: دالة تُستدعى مع كل ملف (اسم_الملف، المكتمل، الإجمالي)
        """
        if mode not in ("move", "copy"):
            raise ValueError(f"الوضع غير مدعوم: {mode}. استخدم 'move' أو 'copy'")

        self.mode: str = mode
        self.dry_run: bool = dry_run
        self.overwrite: bool = overwrite
        self.skip_hidden: bool = skip_hidden
        self.skip_symlinks: bool = skip_symlinks
        self.progress_callback: Optional[Callable[[str, int, int], None]] = progress_callback

        logger.info(
            "تم تهيئة المنظم — الوضع: %s | محاكاة: %s | الكتابة فوق: %s",
            mode, dry_run, overwrite,
        )

    # ===================================================================
    #  التصنيف
    # ===================================================================

    def classify_file(self, file_path: str | Path) -> str:
        """
        يُصنّف ملفاً واحداً إلى فئة بناءً على الامتداد ومحتواه.

        المعاملات:
            file_path: مسار الملف

        المعاد:
            اسم الفئة (str) — واحدة من: code, documents, images,
            archives, data, notebooks, configs, other
        """
        path = Path(file_path)
        if not path.is_file():
            logger.warning("الملف غير موجود أو ليس ملفاً عادياً: %s", path)
            return "other"

        # 1) التصنيف بالامتداد
        suffix = path.suffix.lower()
        # التعامل مع الامتدادات المركبة مثل .tar.gz
        if suffix in (".gz", ".bz2", ".xz"):
            stem_suffix = path.stem.split(".")[-1].lower() if "." in path.stem else ""
            if stem_suffix in ("tar",):
                compound = f".tar{suffix}"
                if compound in self.EXTENSION_MAP:
                    category = self.EXTENSION_MAP[compound]
                    logger.debug("تصنيف %s -> %s (امتداد مركب)", path.name, category)
                    return category

        if suffix in self.EXTENSION_MAP:
            category = self.EXTENSION_MAP[suffix]
            logger.debug("تصنيف %s -> %s (بالامتداد)", path.name, category)
            return category

        # 2) التصنيف بالتوقيع السحري (Magic Bytes)
        try:
            with open(path, "rb") as f:
                header = f.read(32)

            for magic, cat in self.MAGIC_SIGNATURES:
                if header.startswith(magic):
                    logger.debug("تصنيف %s -> %s (بالتوقيع السحري)", path.name, cat)
                    return cat
        except PermissionError:
            logger.warning("لا صلاحية لقراءة الملف: %s", path)
        except OSError as exc:
            logger.warning("خطأ أثناء قراءة الملف %s: %s", path, exc)

        # 3) التصنيف بالاسم (ملفات بدون امتداد)
        name_lower = path.name.lower()
        special_names: dict[str, str] = {
            "makefile": "code",
            "dockerfile": "code",
            "rakefile": "code",
            "gemfile": "code",
            ".gitignore": "configs",
            ".env": "configs",
            ".editorconfig": "configs",
            "license": "documents",
            "readme": "documents",
        }
        for special, cat in special_names.items():
            if name_lower == special or name_lower.startswith(special + "."):
                logger.debug("تصنيف %s -> %s (بالاسم الخاص)", path.name, cat)
                return cat

        # 4) فئة افتراضية
        logger.debug("تصنيف %s -> other (غير معروف)", path.name)
        return "other"

    # ===================================================================
    #  التنظيم الرئيسي
    # ===================================================================

    def organize_directory(
        self,
        source_dir: str | Path,
        target_dir: str | Path,
    ) -> dict:
        """
        يُنظّم جميع الملفات في المجلد المصدر ويفرزها حسب الفئات.

        المعاملات:
            source_dir: مجلد المصدر الذي يحتوي على الملفات
            target_dir: مجلد الهدف الذي سيتم إنشاء الفئات الفرعية فيه

        المعاد:
            تقرير مفصّل:
            {
                "moved": [{"file": ..., "category": ..., "destination": ...}, ...],
                "copied": [...],
                "skipped": [{"file": ..., "reason": ...}, ...],
                "stats": {
                    "total_files": int,
                    "processed": int,
                    "moved": int,
                    "copied": int,
                    "skipped": int,
                    "categories": {"code": int, "images": int, ...}
                }
            }
        """
        src = Path(source_dir).resolve()
        tgt = Path(target_dir).resolve()

        if not src.is_dir():
            raise FileNotFoundError(f"مجلد المصدر غير موجود: {src}")

        if not tgt.exists():
            try:
                tgt.mkdir(parents=True, exist_ok=True)
                logger.info("تم إنشاء مجلد الهدف: %s", tgt)
            except PermissionError as exc:
                raise PermissionError(f"لا صلاحية لإنشاء المجلد {tgt}: {exc}") from exc

        report: dict = {
            "moved": [],
            "copied": [],
            "skipped": [],
            "stats": {
                "total_files": 0,
                "processed": 0,
                "moved": 0,
                "copied": 0,
                "skipped": 0,
                "categories": defaultdict(int),
            },
        }

        # جمع جميع الملفات العادية
        try:
            all_files = sorted([
                f for f in src.rglob("*")
                if f.is_file()
            ])
        except PermissionError as exc:
            logger.error("لا صلاحية لقراءة المجلد %s: %s", src, exc)
            raise

        report["stats"]["total_files"] = len(all_files)
        total = len(all_files)
        processed = 0

        for file_path in all_files:
            processed += 1

            # إبلاغ التقدم
            if self.progress_callback:
                try:
                    self.progress_callback(str(file_path), processed, total)
                except Exception as exc:
                    logger.warning("خطأ في دالة التقدم: %s", exc)

            # تخطي الملفات المخفية
            if self.skip_hidden and any(
                part.startswith(".") for part in file_path.relative_to(src).parts
            ):
                report["skipped"].append({"file": str(file_path), "reason": "ملف مخفي"})
                report["stats"]["skipped"] += 1
                continue

            # تخطي الروابط الرمزية
            if self.skip_symlinks and file_path.is_symlink():
                report["skipped"].append({"file": str(file_path), "reason": "رابط رمزي"})
                report["stats"]["skipped"] += 1
                continue

            # التصنيف
            category = self.classify_file(file_path)

            # إنشاء مجلد الفئة الفرعي
            category_dir = tgt / category
            if not self.dry_run:
                try:
                    category_dir.mkdir(parents=True, exist_ok=True)
                except PermissionError as exc:
                    logger.error("لا صلاحية لإنشاء %s: %s", category_dir, exc)
                    report["skipped"].append({"file": str(file_path), "reason": f"خطأ إنشاء المجلد: {exc}"})
                    report["stats"]["skipped"] += 1
                    continue

            # تحديد مسار الوجهة مع تجنب التعارض
            dest_path = self._resolve_destination(file_path, category_dir)

            if self.dry_run:
                # وضع المحاكاة — لا ننقل شيئاً
                action_key = "moved" if self.mode == "move" else "copied"
                report[action_key].append({
                    "file": str(file_path),
                    "category": category,
                    "destination": str(dest_path),
                })
                report["stats"][self.mode + "d" if self.mode == "move" else "copied"] += 1
            else:
                try:
                    if self.mode == "move":
                        shutil.move(str(file_path), str(dest_path))
                        report["moved"].append({
                            "file": str(file_path),
                            "category": category,
                            "destination": str(dest_path),
                        })
                        report["stats"]["moved"] += 1
                    else:
                        shutil.copy2(str(file_path), str(dest_path))
                        report["copied"].append({
                            "file": str(file_path),
                            "category": category,
                            "destination": str(dest_path),
                        })
                        report["stats"]["copied"] += 1

                    logger.info(
                        "%s %s -> %s/%s/%s",
                        "نقل" if self.mode == "move" else "نسخ",
                        file_path.name,
                        tgt.name,
                        category,
                        dest_path.name,
                    )
                except PermissionError as exc:
                    logger.error("لا صلاحية: %s -> %s: %s", file_path, dest_path, exc)
                    report["skipped"].append({"file": str(file_path), "reason": f"خطأ صلاحية: {exc}"})
                    report["stats"]["skipped"] += 1
                except shutil.SameFileError:
                    report["skipped"].append({"file": str(file_path), "reason": "المصدر والوجهة متطابقان"})
                    report["stats"]["skipped"] += 1
                except OSError as exc:
                    logger.error("خطأ أثناء %s %s: %s", self.mode, file_path, exc)
                    report["skipped"].append({"file": str(file_path), "reason": f"خطأ: {exc}"})
                    report["stats"]["skipped"] += 1

            report["stats"]["processed"] += 1
            report["stats"]["categories"][category] += 1

        # تحويل defaultdict إلى dict عادي للعرض
        report["stats"]["categories"] = dict(report["stats"]["categories"])

        logger.info(
            "اكتمل التنظيم — إجمالي: %d | مُعالَج: %d | منقول: %d | منسوخ: %d | متخطّى: %d",
            report["stats"]["total_files"],
            report["stats"]["processed"],
            report["stats"]["moved"],
            report["stats"]["copied"],
            report["stats"]["skipped"],
        )

        return report

    # ===================================================================
    #  أدوات مساعدة
    # ===================================================================

    def _resolve_destination(self, source: Path, dest_dir: Path) -> Path:
        """
        يحلّ تعارض الأسماء بإضافة رقم تزايدي.

        المعاملات:
            source: مسار الملف المصدر
            dest_dir: مجلد الوجهة

        المعاد:
            مسار الوجهة النهائي (بدون تعارض)
        """
        dest = dest_dir / source.name
        if not dest.exists() or self.overwrite:
            return dest

        stem = source.stem
        suffix = source.suffix
        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_dest = dest_dir / new_name
            if not new_dest.exists():
                return new_dest
            counter += 1
            # حماية من حلقة لا نهائية
            if counter > 10000:
                logger.warning("تم تجاوز الحد الأقصى لتعارض الأسماء لـ %s", source.name)
                return dest_dir / f"{stem}_{hash(source)}{suffix}"

    def get_categories(self) -> dict[str, list[str]]:
        """
        يعرض جميع الفئات المدعومة مع الامتدادات التابعة لكل فئة.

        المعاد:
            قاموس: {فئة: [امتداد, ...]}
        """
        cats: dict[str, list[str]] = defaultdict(list)
        for ext, cat in self.EXTENSION_MAP.items():
            cats[cat].append(ext)
        return dict(cats)
