"""
ماسح أمان الملفات (File Security Scanner)
============================================
يفحص الملفات بحثاً عن بيانات حساسة وأنماط أمنية مشبوهة.

القدرات:
- كشف أنماط البيانات الحساسة (كلمات مرور، مفاتيح API، رموز، بريد إلكتروني)
- تصنيف النتائج حسب الخطورة (منخفض، متوسط، عالٍ، حرج)
- فحص ملفات فردية أو مجلدات كاملة
- تجاهل الملفات حسب أنماط .gitignore
- دعم أنماط مخصصة
- عرض آمن للتقارير
"""

import fnmatch
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileScanner:
    """
    ماسح أمان الملفات — يفحص الملفات بحثاً عن بيانات حساسة.

    الاستخدام:
        scanner = FileScanner()
        report = scanner.scan_file("config.py")
        report = scanner.scan_directory("/path/to/project")
    """

    # ======== أنماط الفحص الافتراضية ========
    DEFAULT_PATTERNS: list[dict[str, str]] = [
        # === CRITICAL: مفاتيح ومصادقة ===
        {
            "name": "AWS Access Key",
            "pattern": r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}",
            "severity": "critical",
            "description": "مفتاح وصول AWS",
        },
        {
            "name": "AWS Secret Key",
            "pattern": r"(?i)aws[_\-]?secret[_\-]?(?:access[_\-]?)?key\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
            "severity": "critical",
            "description": "مفتاح سري AWS",
        },
        {
            "name": "Private Key (RSA/DSA/EC)",
            "pattern": r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
            "severity": "critical",
            "description": "مفتاح خاص (RSA/DSA/EC)",
        },
        {
            "name": "SSH Private Key",
            "pattern": r"ssh-rsa\s+[A-Za-z0-9+/=]+",
            "severity": "critical",
            "description": "مفتاح SSH خاص",
        },
        {
            "name": "Google API Key",
            "pattern": r"(?:AIza)[0-9A-Za-z\-_]{35}",
            "severity": "critical",
            "description": "مفتاح Google API",
        },
        {
            "name": "GitHub Token",
            "pattern": r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}",
            "severity": "critical",
            "description": "رمز GitHub",
        },
        {
            "name": "Slack Token",
            "pattern": r"xox[bpors]-[A-Za-z0-9\-]{10,}",
            "severity": "critical",
            "description": "رمز Slack",
        },
        {
            "name": "Stripe API Key",
            "pattern": r"(?:sk|pk)_(?:test|live)_[A-Za-z0-9]{24,}",
            "severity": "critical",
            "description": "مفتاح Stripe API",
        },
        {
            "name": "JWT Token",
            "pattern": r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
            "severity": "critical",
            "description": "رمز JWT",
        },

        # === HIGH: كلمات مرور وبيانات حساسة ===
        {
            "name": "Password Assignment",
            "pattern": r"(?i)(?:password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]{4,})['\"]",
            "severity": "high",
            "description": "كلمة مرور صريحة في الكود",
        },
        {
            "name": "Database Connection String",
            "pattern": r"(?i)(?:mongodb|postgres|mysql|redis|amqp)://[^\s'\"]+:[^\s'\"]+@[^\s'\"]+",
            "severity": "high",
            "description": "سلسلة اتصال قاعدة بيانات",
        },
        {
            "name": "API Key in URL",
            "pattern": r"(?i)api[_\-]?key\s*=\s*[A-Za-z0-9\-_]{20,}",
            "severity": "high",
            "description": "مفتاح API في رابط",
        },
        {
            "name": "Authorization Header",
            "pattern": r"(?i)Authorization\s*:\s*(?:Bearer|Basic|Token)\s+[A-Za-z0-9\-._~+/]+=*",
            "severity": "high",
            "description": "رأس مصادقة صريح",
        },
        {
            "name": "Secret/Token Assignment",
            "pattern": r"(?i)(?:secret|token|auth[_\-]?token|access[_\-]?token)\s*[=:]\s*['\"]([A-Za-z0-9\-_\.]{20,})['\"]",
            "severity": "high",
            "description": "سر أو رمز صريح",
        },

        # === MEDIUM: بيانات شخصية ومعلومات ===
        {
            "name": "Email Address",
            "pattern": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
            "severity": "medium",
            "description": "عنوان بريد إلكتروني",
        },
        {
            "name": "Phone Number (International)",
            "pattern": r"(?:\+|00)[\d\s\-]{8,15}",
            "severity": "medium",
            "description": "رقم هاتف دولي",
        },
        {
            "name": "IP Address",
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "severity": "medium",
            "description": "عنوان IP",
        },
        {
            "name": "Internal URL",
            "pattern": r"(?i)(?:https?://)(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+)",
            "severity": "medium",
            "description": "رابط داخلي (localhost/شبكة داخلية)",
        },

        # === LOW: معلومات عامة ===
        {
            "name": "URL",
            "pattern": r"https?://[^\s<>\"]+",
            "severity": "low",
            "description": "رابط URL",
        },
        {
            "name": "Credit Card (Basic)",
            "pattern": r"\b(?:\d[ \-]*?){13,19}\b",
            "severity": "low",
            "description": "رقم بطاقة ائتمان (محتمل)",
        },
    ]

    # ======== الامتدادات التي لا يتم فحصها ========
    SKIP_EXTENSIONS: set[str] = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif",
        ".webp", ".ico", ".svg", ".heic", ".heif", ".avif", ".jxl",
        ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv",
        ".wav", ".ogg", ".flac", ".aac",
        ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
        ".exe", ".dll", ".so", ".dylib", ".bin",
        ".pyc", ".pyo", ".class", ".o", ".obj",
        ".woff", ".woff2", ".ttf", ".otf", ".eot",
    }

    # ======== المجلدات التي لا يتم فحصها ========
    SKIP_DIRECTORIES: set[str] = {
        "__pycache__", ".git", ".svn", ".hg", "node_modules",
        ".tox", ".venv", "venv", "env", ".env",
        ".mypy_cache", ".pytest_cache", ".ruff_cache",
        "dist", "build", ".eggs", "*.egg-info",
    }

    def __init__(
        self,
        custom_patterns: Optional[list[dict[str, str]]] = None,
        min_severity: str = "low",
        max_file_size: int = 10 * 1024 * 1024,  # 10 ميغابايت
        ignore_patterns: Optional[list[str]] = None,
    ) -> None:
        """
        تهيئة ماسح الأمان.

        المعاملات:
            custom_patterns: أنماط مخصصة إضافية
            min_severity: أدنى مستوى خطورة يتم الإبلاغ عنه
            max_file_size: أقصى حجم ملف (بايت) للفحص
            ignore_patterns: أنماط glob لتجاهل الملفات (مثل .gitignore)
        """
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if min_severity not in severity_order:
            raise ValueError(f"مستوى خطورة غير صالح: {min_severity}")

        self.min_severity: str = min_severity
        self.max_file_size: int = max_file_size
        self.ignore_patterns: list[str] = ignore_patterns or []

        # دمج الأنماط
        self.patterns: list[dict[str, str]] = list(self.DEFAULT_PATTERNS)
        if custom_patterns:
            self.patterns.extend(custom_patterns)

        # تجميع الأنماط في كائنات regex مجمّعة
        self._compiled_patterns: list[dict] = []
        for pat_info in self.patterns:
            try:
                compiled = re.compile(pat_info["pattern"])
                self._compiled_patterns.append({
                    "name": pat_info["name"],
                    "pattern": compiled,
                    "severity": pat_info.get("severity", "medium"),
                    "description": pat_info.get("description", ""),
                })
            except re.error as exc:
                logger.warning("نمط regex غير صالح '%s': %s", pat_info["name"], exc)

        # تحميل أنماط .gitignore إذا وُجدت
        self._gitignore_patterns: list[str] = []
        if not self.ignore_patterns:
            self._load_gitignore()

        logger.info(
            "تم تهيئة ماسح الأمان — الأنماط: %d | الحد الأدنى للخطورة: %s",
            len(self._compiled_patterns), min_severity,
        )

    # ===================================================================
    #  تحميل .gitignore
    # ===================================================================

    def _load_gitignore(self, directory: Optional[Path] = None) -> None:
        """
        يحمل أنماط التجاهل من ملف .gitignore.

        المعاملات:
            directory: المجلد الذي يحتوي على .gitignore
        """
        search_dirs = [directory] if directory else [Path.cwd()]
        if not any(search_dirs):
            return

        for d in search_dirs:
            gitignore_path = d / ".gitignore"
            if gitignore_path.is_file():
                try:
                    content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
                    patterns = [
                        line.strip()
                        for line in content.splitlines()
                        if line.strip() and not line.strip().startswith("#")
                    ]
                    self._gitignore_patterns.extend(patterns)
                    self.ignore_patterns.extend(patterns)
                    logger.info("تم تحميل %d نمط من .gitignore", len(patterns))
                except PermissionError:
                    logger.warning("لا صلاحية لقراءة .gitignore")

    def _should_ignore(self, file_path: Path, base_dir: Path) -> bool:
        """
        يتحقق مما إذا كان يجب تجاهل الملف.

        المعاملات:
            file_path: مسار الملف
            base_dir: المجلد الأساسي

        المعاد:
            True إذا كان يجب تجاهل الملف
        """
        rel_path = file_path.relative_to(base_dir)

        # فحص المجلدات الممنوعة
        for part in rel_path.parts:
            for skip_dir in self.SKIP_DIRECTORIES:
                if fnmatch.fnmatch(part, skip_dir):
                    return True

        # فحص الامتدادات الممنوعة
        if file_path.suffix.lower() in self.SKIP_EXTENSIONS:
            return True

        # فحص أنماط .gitignore
        for pattern in self.ignore_patterns:
            try:
                if fnmatch.fnmatch(str(rel_path), pattern):
                    return True
                if fnmatch.fnmatch(rel_path.name, pattern):
                    return True
            except Exception:
                continue

        # فحص حجم الملف
        try:
            if file_path.stat().st_size > self.max_file_size:
                logger.debug("تجاهل %s (حجم كبير: %d)", file_path.name, file_path.stat().st_size)
                return True
        except OSError:
            pass

        return False

    # ===================================================================
    #  فحص ملف واحد
    # ===================================================================

    def scan_file(self, file_path: str | Path) -> dict:
        """
        يفحص ملفاً واحداً بحثاً عن بيانات حساسة.

        المعاملات:
            file_path: مسار الملف

        المعاد:
            تقرير الفحص:
            {
                "file": str,
                "size": int,
                "findings": [
                    {
                        "type": str,
                        "severity": str,
                        "description": str,
                        "line": int,
                        "column": int,
                        "match": str,
                        "context": str,
                    }, ...
                ],
                "summary": {
                    "critical": int,
                    "high": int,
                    "medium": int,
                    "low": int,
                },
                "status": "clean" | "issues_found" | "error"
            }
        """
        path = Path(file_path)
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_order[self.min_severity]

        report: dict = {
            "file": str(path.resolve()),
            "size": 0,
            "findings": [],
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "status": "clean",
        }

        # التحقق من وجود الملف
        if not path.is_file():
            logger.warning("الملف غير موجود: %s", path)
            report["status"] = "error"
            report["error"] = "الملف غير موجود"
            return report

        # قراءة الملف
        try:
            file_size = path.stat().st_size
            report["size"] = file_size
        except PermissionError as exc:
            logger.warning("لا صلاحية لقراءة: %s", path)
            report["status"] = "error"
            report["error"] = f"لا صلاحية: {exc}"
            return report
        except OSError as exc:
            logger.warning("خطأ في الملف %s: %s", path, exc)
            report["status"] = "error"
            report["error"] = f"خطأ: {exc}"
            return report

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except PermissionError as exc:
            report["status"] = "error"
            report["error"] = f"لا صلاحية للقراءة: {exc}"
            return report
        except OSError as exc:
            report["status"] = "error"
            report["error"] = f"خطأ أثناء القراءة: {exc}"
            return report

        lines = content.splitlines()

        # فحص كل سطر بكل نمط
        for line_num, line in enumerate(lines, 1):
            for pat_info in self._compiled_patterns:
                pattern_severity = severity_order.get(pat_info["severity"], 0)
                if pattern_severity < min_level:
                    continue

                match = pat_info["pattern"].search(line)
                if match:
                    finding = {
                        "type": pat_info["name"],
                        "severity": pat_info["severity"],
                        "description": pat_info["description"],
                        "line": line_num,
                        "column": match.start() + 1,
                        "match": match.group(),
                        "context": self._extract_context(line, match.start(), match.end()),
                    }
                    report["findings"].append(finding)
                    report["summary"][pat_info["severity"]] += 1

        # تحديد الحالة
        total_findings = sum(report["summary"].values())
        report["status"] = "issues_found" if total_findings > 0 else "clean"

        if total_findings > 0:
            logger.warning(
                "تم اكتشاف %d مشكلة أمنية في %s",
                total_findings, path.name,
            )
        else:
            logger.debug("الملف آمن: %s", path.name)

        return report

    def _extract_context(self, line: str, start: int, end: int, context_chars: int = 30) -> str:
        """
        يستخرج السياق المحيط بالنتيجة المطابقة.

        المعاملات:
            line: السطر الكامل
            start: بداية المطابقة
            end: نهاية المطابقة
            context_chars: عدد الأحرف في كل اتجاه

        المعاد:
            النص مع السياق المحيط (القيم الحساسة تُحجب)
        """
        ctx_start = max(0, start - context_chars)
        ctx_end = min(len(line), end + context_chars)

        before = line[ctx_start:start]
        matched = line[start:end]
        after = line[end:ctx_end]

        # حجب القيمة الحساسة — إظهار أول 4 أحرف فقط
        if len(matched) > 8:
            masked = matched[:4] + "****"
        else:
            masked = matched[:2] + "****"

        return f"...{before}{masked}{after}..."

    # ===================================================================
    #  فحص مجلد
    # ===================================================================

    def scan_directory(self, directory: str | Path) -> dict:
        """
        يفحص جميع الملفات في مجلد ومجلداته الفرعية.

        المعاملات:
            directory: مسار المجلد

        المعاد:
            تقرير شامل:
            {
                "directory": str,
                "total_files_scanned": int,
                "files_with_issues": int,
                "total_findings": int,
                "summary": {...},
                "file_reports": [report, ...],
                "top_issues": [finding, ...],
            }
        """
        dir_path = Path(directory).resolve()

        if not dir_path.is_dir():
            raise FileNotFoundError(f"المجلد غير موجود: {dir_path}")

        # تحميل .gitignore من المجلد
        self._load_gitignore(dir_path)

        report: dict = {
            "directory": str(dir_path),
            "total_files_scanned": 0,
            "files_with_issues": 0,
            "total_findings": 0,
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "file_reports": [],
            "top_issues": [],
        }

        logger.info("بدء فحص المجلد: %s", dir_path)

        # جمع الملفات
        try:
            all_files = sorted([
                f for f in dir_path.rglob("*")
                if f.is_file() and not self._should_ignore(f, dir_path)
            ])
        except PermissionError as exc:
            logger.error("لا صلاحية لقراءة المجلد: %s", exc)
            raise

        report["total_files_scanned"] = len(all_files)

        # فحص كل ملف
        for file_path in all_files:
            try:
                file_report = self.scan_file(file_path)
                report["file_reports"].append(file_report)

                if file_report["status"] == "issues_found":
                    report["files_with_issues"] += 1
                    report["total_findings"] += len(file_report["findings"])

                    for sev in ("critical", "high", "medium", "low"):
                        report["summary"][sev] += file_report["summary"][sev]

                    # إضافة إلى أعلى المشاكل
                    for finding in file_report["findings"]:
                        if finding["severity"] in ("critical", "high"):
                            report["top_issues"].append({
                                "file": file_report["file"],
                                **finding,
                            })

            except Exception as exc:
                logger.error("خطأ أثناء فحص %s: %s", file_path, exc)

        # ترتيب أعلى المشاكل حسب الخطورة
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        report["top_issues"].sort(
            key=lambda x: severity_order.get(x["severity"], 4)
        )

        # الحد الأقصى لعرض أعلى المشاكل
        report["top_issues"] = report["top_issues"][:50]

        logger.info(
            "اكتمل فحص المجلد — ملفات: %d | مشاكل: %d | حرجة: %d | عالية: %d",
            report["total_files_scanned"],
            report["total_findings"],
            report["summary"]["critical"],
            report["summary"]["high"],
        )

        return report

    # ===================================================================
    #  عرض آمن للتقرير
    # ===================================================================

    def sanitize_report(self, report: dict) -> dict:
        """
        ينظّف التقرير لإخفاء القيم الحساسة قبل العرض.

        المعاملات:
            report: تقرير الفحص (ملف أو مجلد)

        المعاد:
            تقرير منقّح مع حجب القيم الحساسة
        """
        import copy
        safe_report = copy.deepcopy(report)

        # تنظيف نتائج الملفات
        if "findings" in safe_report:
            for finding in safe_report["findings"]:
                match = finding.get("match", "")
                if len(match) > 8:
                    finding["match"] = match[:4] + "****"
                else:
                    finding["match"] = match[:2] + "****"

                # حجب السياق
                if "context" in finding:
                    finding["context"] = self._sanitize_context(finding["context"])

        # تنظيف تقارير الملفات الفرعية
        if "file_reports" in safe_report:
            for file_report in safe_report["file_reports"]:
                if "findings" in file_report:
                    for finding in file_report["findings"]:
                        match = finding.get("match", "")
                        if len(match) > 8:
                            finding["match"] = match[:4] + "****"
                        else:
                            finding["match"] = match[:2] + "****"
                        if "context" in finding:
                            finding["context"] = self._sanitize_context(finding["context"])

        logger.debug("تم تنظيف التقرير لإخفاء القيم الحساسة")
        return safe_report

    def _sanitize_context(self, context: str, max_reveal: int = 3) -> str:
        """
        يحجب الأجزاء الحساسة من السياق.

        المعاملات:
            context: النص الأصلي
            max_reveal: أقصى عدد أحرف مكشوفة

        المعاد:
            النص المنظّف
        """
        # إبقاء أول 3 أحرف فقط من كل كلمة طويلة
        words = context.split()
        sanitized = []
        for word in words:
            if len(word) > 8:
                sanitized.append(word[:max_reveal] + "****")
            else:
                sanitized.append(word)
        return " ".join(sanitized)

    # ===================================================================
    #  أدوات مساعدة
    # ===================================================================

    def add_pattern(
        self,
        name: str,
        pattern: str,
        severity: str = "medium",
        description: str = "",
    ) -> None:
        """
        يضيف نمط فحص مخصص.

        المعاملات:
            name: اسم النمط
            pattern: تعبير regex
            severity: مستوى الخطورة
            description: وصف مختصر
        """
        try:
            compiled = re.compile(pattern)
            self._compiled_patterns.append({
                "name": name,
                "pattern": compiled,
                "severity": severity,
                "description": description,
            })
            logger.info("تم إضافة نمط مخصص: %s (الخطورة: %s)", name, severity)
        except re.error as exc:
            logger.error("نمط regex غير صالح: %s — %s", name, exc)
            raise ValueError(f"نمط regex غير صالح: {exc}") from exc

    def remove_pattern(self, name: str) -> bool:
        """
        يزيل نمط فحص بالاسم.

        المعاملات:
            name: اسم النمط

        المعاد:
            True إذا تم الحذف، False إذا لم يُعثر عليه
        """
        original_len = len(self._compiled_patterns)
        self._compiled_patterns = [
            p for p in self._compiled_patterns if p["name"] != name
        ]
        removed = len(self._compiled_patterns) < original_len
        if removed:
            logger.info("تم إزالة النمط: %s", name)
        return removed

    def get_patterns(self) -> list[dict[str, str]]:
        """
        يعرض قائمة بجميع أنماط الفحص النشطة.

        المعاد:
            قائمة بالأنماط مع معلوماتها
        """
        return [
            {
                "name": p["name"],
                "severity": p["severity"],
                "description": p["description"],
                "pattern": p["pattern"].pattern,
            }
            for p in self._compiled_patterns
        ]
