"""
حامي الأكواد البرمجية (Code Protector)
========================================
يحمي ملفات وأجزاء الأكواد البرمجية من التعديل العرضي أثناء المعالجة
النصية (مثل فحص الإملاء أو تحويل النصوص).

القدرات:
- كشف ملفات الأكواد من خلال الامتداد والمحتوى
- استخراج أجزاء الأكواد من المستندات المختلطة
- لف أجزاء الأكواد بعلامات حماية لمنع تعديلها
- كشف لغة البرمجة من الملف أو النص
- إزالة علامات الحماية عند الحاجة
"""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CodeProtector:
    """
    حامي الأكواد البرمجية — يمنع تعديل الأكواد أثناء معالجة النصوص.

    الاستخدام:
        protector = CodeProtector()
        protected = protector.protect_text(mixed_text)
        # ... معالجة نصية ...
        restored = protector.strip_protection(protected)
    """

    # ======== علامات الحماية ========
    MARKER_START: str = "«CODE_PROTECT_START»"
    MARKER_END: str = "«CODE_PROTECT_END»"
    LANG_TAG_START: str = "«LANG:"
    LANG_TAG_END: str = "»"

    # ======== الامتدادات المدعومة ========
    CODE_EXTENSIONS: set[str] = {
        ".py", ".pyw", ".pyi",
        ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
        ".java", ".kt", ".kts", ".scala",
        ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
        ".cs", ".vb",
        ".go", ".rs", ".swift",
        ".rb", ".rake",
        ".php",
        ".pl", ".pm", ".r",
        ".lua", ".vim",
        ".sh", ".bash", ".zsh", ".fish",
        ".ps1", ".bat", ".cmd",
        ".sql",
        ".dart", ".clj", ".ex", ".exs",
        ".hs", ".ml", ".lisp",
        ".m", ".mm",
        ".proto", ".thrift",
        ".cmake",
        ".vue", ".svelte", ".html", ".htm",
        ".css", ".scss", ".sass", ".less",
        ".xml", ".xsl", ".xsd",
        ".json", ".yaml", ".yml", ".toml",
        ".graphql", ".gql",
        ".dockerfile",
    }

    # ======== كلمات محجوزة حسب اللغة ========
    RESERVED_KEYWORDS: dict[str, set[str]] = {
        "python": {
            "def", "class", "import", "from", "return", "if", "elif", "else",
            "for", "while", "try", "except", "finally", "with", "as", "lambda",
            "yield", "async", "await", "pass", "break", "continue", "raise",
            "global", "nonlocal", "assert", "del", "in", "not", "and", "or",
            "is", "None", "True", "False", "self", "print", "range", "type",
            "super", "property", "staticmethod", "classmethod", "enumerate",
            "__init__", "__name__", "__main__",
        },
        "javascript": {
            "function", "const", "let", "var", "return", "if", "else",
            "for", "while", "do", "switch", "case", "break", "continue",
            "try", "catch", "finally", "throw", "new", "this", "class",
            "extends", "super", "import", "export", "default", "from",
            "async", "await", "yield", "of", "in", "typeof", "instanceof",
            "null", "undefined", "true", "false", "console", "require",
            "module", "exports", "document", "window",
            "function", "arrow", "=>",
        },
        "java": {
            "public", "private", "protected", "static", "final", "abstract",
            "class", "interface", "extends", "implements", "import", "package",
            "return", "if", "else", "for", "while", "do", "switch", "case",
            "break", "continue", "try", "catch", "finally", "throw", "throws",
            "new", "this", "super", "void", "int", "long", "double", "float",
            "boolean", "char", "byte", "short", "String", "null", "true", "false",
            "System", "Override",
        },
        "cpp": {
            "include", "define", "ifdef", "ifndef", "endif", "pragma",
            "class", "struct", "enum", "union", "namespace", "using",
            "template", "typename", "virtual", "override", "const",
            "static", "extern", "inline", "explicit", "friend",
            "public", "private", "protected", "return", "if", "else",
            "for", "while", "do", "switch", "case", "break", "continue",
            "try", "catch", "throw", "new", "delete", "this", "auto",
            "int", "long", "double", "float", "bool", "char", "void",
            "std", "cout", "cin", "endl", "nullptr", "sizeof",
        },
        "go": {
            "package", "import", "func", "var", "const", "type",
            "struct", "interface", "map", "chan", "go", "select",
            "range", "for", "if", "else", "switch", "case", "default",
            "break", "continue", "return", "defer", "fallthrough",
            "nil", "true", "false", "make", "append", "len", "cap",
            "fmt", "Println", "Printf", "Errorf",
        },
        "rust": {
            "fn", "let", "mut", "const", "static", "struct", "enum",
            "impl", "trait", "pub", "use", "mod", "crate", "self",
            "super", "return", "if", "else", "for", "while", "loop",
            "match", "break", "continue", "where", "as", "in", "ref",
            "true", "false", "None", "Some", "Ok", "Err", "Vec",
            "String", "println", "eprintln", "format", "macro_rules",
            "derive", "async", "await", "move", "unsafe",
        },
        "sql": {
            "SELECT", "FROM", "WHERE", "INSERT", "INTO", "UPDATE",
            "DELETE", "CREATE", "ALTER", "DROP", "TABLE", "INDEX",
            "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AND",
            "OR", "NOT", "NULL", "IS", "IN", "LIKE", "BETWEEN",
            "ORDER", "BY", "GROUP", "HAVING", "LIMIT", "OFFSET",
            "AS", "DISTINCT", "UNION", "ALL", "EXISTS", "COUNT",
            "SUM", "AVG", "MIN", "MAX", "PRIMARY", "KEY", "FOREIGN",
            "REFERENCES", "CASCADE", "SET", "VALUES", "BEGIN",
            "COMMIT", "ROLLBACK", "TRANSACTION",
        },
    }

    # ======== أنماط كشف أجزاء الأكواد في النصوص ========
    # أنماط Markdown code blocks
    MD_CODE_BLOCK_PATTERN: re.Pattern = re.compile(
        r"(```[\w]*\n)(.*?)(```)",
        re.DOTALL,
    )
    # أنماط HTML/PHP code blocks
    HTML_CODE_BLOCK_PATTERN: re.Pattern = re.compile(
        r"<(code|pre)[^>]*>(.*?)</\1>",
        re.DOTALL | re.IGNORECASE,
    )

    def __init__(self) -> None:
        """تهيئة حامي الأكواد."""
        self._protected_sections: list[dict] = []  # لتخزين الأجزاء المحمية مؤقتاً
        logger.info("تم تهيئة حامي الأكواد البرمجية")

    # ===================================================================
    #  كشف ملفات الأكواد
    # ===================================================================

    def is_code_file(self, file_path: str | Path) -> bool:
        """
        يتحقق مما إذا كان الملف ملف أكواد برمجية.

        المعاملات:
            file_path: مسار الملف

        المعاد:
            True إذا كان الملف ملف أكواد، وإلا False
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        # فحص الامتداد
        if suffix in self.CODE_EXTENSIONS:
            logger.debug("كشف ملف أكواد بالامتداد: %s", path.name)
            return True

        # فحص الاسم الخاص
        name_lower = path.name.lower()
        special_code_names = {
            "makefile", "dockerfile", "rakefile", "gemfile",
            "cmakelists.txt",
        }
        if name_lower in special_code_names:
            return True

        # فحص المحتوى — إذا كان يحتوي على عدد كبير من الكلمات المحجوزة
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:2000]
            if self._count_code_indicators(content) >= 5:
                logger.debug("كشف ملف أكواد بالمحتوى: %s", path.name)
                return True
        except PermissionError:
            logger.warning("لا صلاحية لقراءة: %s", path)
        except OSError as exc:
            logger.warning("خطأ أثناء قراءة %s: %s", path, exc)

        return False

    def _count_code_indicators(self, text: str) -> int:
        """
        يعدّد مؤشرات الأكواد في النص (أقواس، عوامل، كلمات محجوزة).

        المعاملات:
            text: النص المراد فحصه

        المعاد:
            عدد المؤشرات المكتشفة
        """
        count = 0

        # علامات ترقيم برمجية شائعة
        code_symbols = ["{", "}", ";", "=>", "->", "::", "#!", "def ", "func ", "class "]
        for symbol in code_symbols:
            count += text.count(symbol)

        # كلمات محجوزة من جميع اللغات
        all_keywords: set[str] = set()
        for keywords in self.RESERVED_KEYWORDS.values():
            all_keywords.update(keywords)

        words = re.findall(r"\b\w+\b", text)
        for word in words:
            if word in all_keywords:
                count += 1

        return count

    # ===================================================================
    #  كشف اللغة
    # ===================================================================

    def detect_language(self, source: str | Path) -> str:
        """
        يكشف لغة البرمجة من مسار ملف أو نص.

        المعاملات:
            source: مسار الملف أو النص البرمجي

        المعاد:
            اسم اللغة (مثل 'python', 'javascript', ...) أو 'unknown'
        """
        # إذا كان مصدراً هو مسار ملف
        path = Path(source)
        if path.is_file():
            return self._detect_language_by_path(path)

        # إذا كان نصاً
        text = str(source)
        return self._detect_language_by_content(text)

    def _detect_language_by_path(self, path: Path) -> str:
        """يكتشف اللغة من مسار الملف."""
        ext_map: dict[str, str] = {
            ".py": "python", ".pyw": "python", ".pyi": "python",
            ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
            ".ts": "typescript", ".tsx": "typescript",
            ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
            ".scala": "scala",
            ".c": "c", ".h": "c",
            ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
            ".cs": "csharp", ".vb": "vb",
            ".go": "go", ".rs": "rust", ".swift": "swift",
            ".rb": "ruby", ".rake": "ruby",
            ".php": "php",
            ".pl": "perl", ".pm": "perl",
            ".r": "r",
            ".lua": "lua",
            ".sh": "shell", ".bash": "shell", ".zsh": "shell",
            ".ps1": "powershell", ".bat": "batch",
            ".sql": "sql",
            ".dart": "dart",
            ".clj": "clojure",
            ".ex": "elixir", ".exs": "elixir",
            ".hs": "haskell", ".ml": "ocaml",
            ".html": "html", ".htm": "html",
            ".css": "css", ".scss": "scss", ".sass": "scss", ".less": "less",
            ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
            ".xml": "xml", ".xsl": "xsl",
            ".vue": "vue", ".svelte": "svelte",
            ".proto": "protobuf",
            ".ipynb": "python",
            ".dockerfile": "docker",
        }

        suffix = path.suffix.lower()
        lang = ext_map.get(suffix)

        if lang:
            logger.debug("كشف لغة %s بالامتداد: %s", path.name, lang)
            return lang

        # أسماء ملفات خاصة
        name_lower = path.name.lower()
        special: dict[str, str] = {
            "makefile": "makefile", "dockerfile": "docker",
            "rakefile": "ruby", "gemfile": "ruby",
        }
        lang = special.get(name_lower, "unknown")
        logger.debug("كشف لغة %s: %s", path.name, lang)
        return lang

    def _detect_language_by_content(self, text: str) -> str:
        """يكتشف اللغة من خلال تحليل محتوى النص."""
        scores: dict[str, int] = {}

        for lang, keywords in self.RESERVED_KEYWORDS.items():
            score = 0
            for kw in keywords:
                # استخدام حدود الكلمات لضمان الدقة
                pattern = rf"\b{re.escape(kw)}\b"
                matches = re.findall(pattern, text, re.IGNORECASE)
                score += len(matches)
            if score > 0:
                scores[lang] = score

        if not scores:
            return "unknown"

        best_lang = max(scores, key=scores.get)
        logger.debug(
            "كشف لغة بالمحتوى: %s (النتيجة: %d)",
            best_lang, scores[best_lang],
        )
        return best_lang

    # ===================================================================
    #  استخراج أجزاء الأكواد
    # ===================================================================

    def extract_code_blocks(self, text: str) -> list[dict]:
        """
        يستخرج أجزاء الأكواد من النصوص المختلطة.

        يدعم:
        - أجزاء Markdown (```code```)
        - أجزاء HTML (<code>...</code> أو <pre>...</pre>)
        - الأجزاء المُغلفة بعلامات الحماية

        المعاملات:
            text: النص المختلط

        المعاد:
            قائمة بقواميس:
            [{"start": int, "end": int, "language": str, "code": str}, ...]
        """
        blocks: list[dict] = []

        # 1) أجزاء Markdown
        for match in self.MD_CODE_BLOCK_PATTERN.finditer(text):
            lang_tag = match.group(1).strip().lstrip("`").strip()
            language = lang_tag if lang_tag else "unknown"
            blocks.append({
                "start": match.start(),
                "end": match.end(),
                "language": language,
                "code": match.group(2).strip(),
            })

        # 2) أجزاء HTML
        for match in self.HTML_CODE_BLOCK_PATTERN.finditer(text):
            # تجنب التكرار مع أجزاء Markdown
            if any(
                b["start"] <= match.start() <= b["end"]
                for b in blocks
            ):
                continue
            blocks.append({
                "start": match.start(),
                "end": match.end(),
                "language": "html",
                "code": match.group(2).strip(),
            })

        # 3) أجزاء محمية بعلاماتنا
        marker_pattern = re.compile(
            re.escape(self.MARKER_START)
            + re.escape(self.LANG_TAG_START)
            + r"(\w+)" + re.escape(self.LANG_TAG_END)
            + r"(.*?)"
            + re.escape(self.MARKER_END),
            re.DOTALL,
        )
        for match in marker_pattern.finditer(text):
            if any(
                b["start"] <= match.start() <= b["end"]
                for b in blocks
            ):
                continue
            blocks.append({
                "start": match.start(),
                "end": match.end(),
                "language": match.group(1),
                "code": match.group(2).strip(),
            })

        # ترتيب حسب الموضع
        blocks.sort(key=lambda b: b["start"])
        logger.debug("تم استخراج %d جزء أكواد من النص", len(blocks))
        return blocks

    # ===================================================================
    #  حماية النص
    # ===================================================================

    def protect_text(self, text: str) -> str:
        """
        يلف أجزاء الأكواد في النص بعلامات حماية لمنع تعديلها
        أثناء المعالجة النصية.

        المعاملات:
            text: النص المختلط (يحتوي على أكواد ومحتوى عادي)

        المعاد:
            النص المحميّ — أجزاء الأكواد ملفوفة بعلامات الحماية
        """
        self._protected_sections = []

        # 1) حماية أجزاء Markdown
        def protect_md_block(match: re.Match) -> str:
            lang_tag = match.group(1).strip().lstrip("`").strip()
            language = lang_tag if lang_tag else "unknown"
            code = match.group(2).strip()
            return (
                f"{self.MARKER_START}{self.LANG_TAG_START}"
                f"{language}{self.LANG_TAG_END}"
                f"{code}{self.MARKER_END}"
            )

        protected = self.MD_CODE_BLOCK_PATTERN.sub(protect_md_block, text)

        # 2) حماية أجزاء HTML
        def protect_html_block(match: re.Match) -> str:
            code = match.group(2).strip()
            return (
                f"{self.MARKER_START}{self.LANG_TAG_START}"
                f"html{self.LANG_TAG_END}"
                f"{code}{self.MARKER_END}"
            )

        protected = self.HTML_CODE_BLOCK_PATTERN.sub(protect_html_block, protected)

        # 3) تخزين الأجزاء المحمية للرجوع إليها
        self._protected_sections = self.extract_code_blocks(protected)

        logger.info("تم حماية %d جزء أكواد في النص", len(self._protected_sections))
        return protected

    def strip_protection(self, text: str, format_: str = "raw") -> str:
        """
        يزيل علامات الحماية من النص ويعيد الأكواد بصيغتها الأصلية.

        المعاملات:
            text: النص المحميّ
            format_: صيغة الإخراج:
                - 'raw': نص عادي بدون علامات
                - 'markdown': أجزاء Markdown (```)
                - 'html': أجزاء HTML (<code>...</code>)

        المعاد:
            النص بعد إزالة الحماية بالصيغة المطلوبة
        """
        marker_pattern = re.compile(
            re.escape(self.MARKER_START)
            + re.escape(self.LANG_TAG_START)
            + r"(\w+)" + re.escape(self.LANG_TAG_END)
            + r"(.*?)"
            + re.escape(self.MARKER_END),
            re.DOTALL,
        )

        if format_ == "raw":
            # إزالة العلامات فقط — إبقاء الكود كما هو
            result = marker_pattern.sub(r"\2", text)

        elif format_ == "markdown":
            def to_md(match: re.Match) -> str:
                lang = match.group(1)
                code = match.group(2)
                return f"```{lang}\n{code}\n```"
            result = marker_pattern.sub(to_md, text)

        elif format_ == "html":
            def to_html(match: re.Match) -> str:
                code = match.group(2)
                return f"<code>{code}</code>"
            result = marker_pattern.sub(to_html, text)

        else:
            raise ValueError(
                f"صيغة غير مدعومة: {format_}. القيم المقبولة: raw, markdown, html"
            )

        logger.debug("تم إزالة الحماية (الصيغة: %s)", format_)
        return result

    # ===================================================================
    #  منع التدقيق الإملائي على الأكواد
    # ===================================================================

    def is_protected_section(self, text: str, position: int) -> bool:
        """
        يتحقق مما إذا كان الموضع المحدد يقع داخل جزء محمي من الأكواد.

        المعاملات:
            text: النص
            position: الموضع المطلوب فحصه

        المعاد:
            True إذا كان الموضع داخل جزء محمي
        """
        marker_pattern = re.compile(
            re.escape(self.MARKER_START)
            + re.escape(self.LANG_TAG_START)
            + r"\w+" + re.escape(self.LANG_TAG_END)
            + r".*?"
            + re.escape(self.MARKER_END),
            re.DOTALL,
        )

        for match in marker_pattern.finditer(text):
            if match.start() <= position <= match.end():
                return True

        return False

    def get_protected_ranges(self, text: str) -> list[tuple[int, int]]:
        """
        يعرض قائمة بمجالات الأجزاء المحمية في النص.

        المعاملات:
            text: النص المراد فحصه

        المعاد:
            قائمة بالأزواج (بداية، نهاية) لكل جزء محمي
        """
        marker_pattern = re.compile(
            re.escape(self.MARKER_START) + r".*?" + re.escape(self.MARKER_END),
            re.DOTALL,
        )

        ranges = [(m.start(), m.end()) for m in marker_pattern.finditer(text)]
        logger.debug("عدد المجالات المحمية: %d", len(ranges))
        return ranges

    # ===================================================================
    #  أدوات مساعدة
    # ===================================================================

    def get_protected_keywords(self, language: Optional[str] = None) -> dict[str, set[str]]:
        """
        يعرض الكلمات المحجوزة.

        المعاملات:
            language: إذا حددت، يعرض كلمات لغة واحدة فقط

        المعاد:
            قاموس الكلمات المحجوزة (أو مجموعة واحدة إذا حددت لغة)
        """
        if language:
            lang_lower = language.lower()
            if lang_lower in self.RESERVED_KEYWORDS:
                return {lang_lower: self.RESERVED_KEYWORDS[lang_lower]}
            logger.warning("لغة غير مدعومة: %s", language)
            return {}

        return dict(self.RESERVED_KEYWORDS)
