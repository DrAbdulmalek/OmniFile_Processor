"""
نظام الكلمات المحمية — Protected Words Module
==================================================
حماية المصطلحات المتخصصة من التصحيح الإملائي التلقائي.

القدرات:
- مجموعات محددة مسبقاً: تقنية (~60)، بايثون (~60)، طبية (~40)
- دعم مصطلحات مخصصة: إضافة/إزالة/فحص
- تكامل مع المصحح الإملائي: فلترة الكلمات المحمية
- فئات شاملة: برمجة، طبية، علمية، أسماء، اختصارات
- حفظ/تحميل المصطلحات المخصصة بصيغة JSON
- البحث بأحرف مطابقة (case-insensitive)

مثال الاستخدام:
    >>> manager = ProtectedWordsManager()
    >>> manager.add_words(["React", "Kubernetes", "TrOCR"], category="custom")
    >>> if manager.is_protected("React"):
    ...     print("محمي!")
    >>> to_skip = manager.filter_protected(["hello", "React", "numpy", "word"])
    >>> # to_skip == ["React", "numpy"]
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ======================================================================
# مجموعات الكلمات المحددة مسبقاً
# ======================================================================

TECHNICAL_KEYWORDS: set[str] = {
    # مصطلحات برمجية عامة
    "python", "pythonistas", "scraping", "parsing", "ocr",
    "batch", "programming", "script", "database", "configure",
    "setup", "env", "immutable", "concatenation", "tuples",
    "dictionaries", "debugging", "programmatically", "spreadsheet",
    "integers", "boolean", "syntax", "web",
    "etl", "dataframe", "json", "csv", "yaml", "markdown",
    "mermaid", "repository", "clone", "commit", "push",
    # اختصارات تقنية
    "repl", "dpi", "api", "gpu", "cpu", "ram", "rom",
    "lora", "huggingface", "transformers", "pytorch", "tensorboard",
    # مفاهيم تقنية
    "comprehensions", "replication", "precedence", "modulo",
    "exponent", "traceback", "overriding",
    # مكتبات بايثون شائعة
    "numpy", "pandas", "matplotlib", "scipy", "sklearn",
    "opencv", "pillow", "tqdm", "requests", "beautifulsoup",
    # DevOps و بنية
    "docker", "kubernetes", "git", "npm", "pip", "conda",
    "ci", "cd", "devops", "ansible", "terraform", "jenkins",
    # أطر عمل
    "flask", "django", "fastapi", "uvicorn", "gradio",
    "react", "vue", "angular", "nextjs", "express",
    # قواعد بيانات
    "mongodb", "postgresql", "mysql", "sqlite", "redis",
    "sqlalchemy", "pymysql", "psycopg2",
    # تعلم آلي
    "machinelearning", "deeplearning", "neuralnetwork",
    "tensorflow", "keras", "pytorch", "sklearn", "xgboost",
    "randomforest", "gradientboost", "sigmoid", "relu",
    "softmax", "backpropagation", "overfitting", "underfitting",
    "huggingface", "transformers", "datasets", "tokenizers",
    # سحابة
    "aws", "gcp", "azure", "heroku", "vercel", "netlify",
}

PYTHON_KEYWORDS: set[str] = {
    # كلمات محجوزة رسمياً
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
    # دوال مدمجة (builtins)
    "print", "input", "len", "range", "type", "int", "str", "float",
    "list", "dict", "set", "tuple", "bool", "open", "file", "super",
    "self", "cls", "repr", "main", "name", "args", "kwargs",
    "append", "extend", "pop", "sort", "join", "split", "strip",
    "format", "replace", "lower", "upper", "title", "capitalize",
    "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "isinstance", "issubclass", "hasattr", "getattr", "setattr",
    "module", "package", "staticmethod", "classmethod", "property",
    "abs", "all", "any", "bin", "chr", "dir", "eval", "exec",
    "getattr", "hex", "id", "max", "min", "oct", "ord", "pow",
    "repr", "round", "sum", "vars", "iter", "next",
    # استثناءات
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "AttributeError", "RuntimeError", "StopIteration",
    "NotImplementedError", "IOError", "OSError", "ImportError",
    "ModuleNotFoundError", "FileNotFoundError", "PermissionError",
    "ZeroDivisionError", "NameError", "UnicodeDecodeError",
}

MEDICAL_TERMS: set[str] = {
    # تشريح
    "cardiology", "neurology", "dermatology", "ophthalmology",
    "orthopedics", "pulmonology", "gastroenterology", "endocrinology",
    "hematology", "oncology", "nephrology", "rheumatology",
    "pathology", "radiology", "anesthesiology", "psychiatry",
    # مصطلحات طبية
    "hypertension", "diabetes", "cholesterol", "antibiotic",
    "inflammation", "metabolism", "symptom", "diagnosis",
    "prognosis", "biopsy", "palliative", "prophylactic",
    "benign", "malignant", "chronic", "acute", "subacute",
    "congenital", "hereditary", "idiopathic", "iatrogenic",
    # أدوية
    "ibuprofen", "acetaminophen", "amoxicillin", "metformin",
    "atorvastatin", "omeprazole", "lisinopril", "aspirin",
    "prednisone", "morphine", "insulin", "penicillin",
    # إجراءات
    "laparoscopy", "endoscopy", "biopsy", "transplant",
    "angioplasty", "arthroscopy", "colonoscopy", "mammography",
    # مختبر
    "hemoglobin", "leukocyte", "erythrocyte", "thrombocyte",
    "electrolyte", "bilirubin", "creatinine", "glucose",
    "potassium", "sodium", "calcium", "phosphate",
}

SCIENTIFIC_TERMS: set[str] = {
    # فيزياء
    "quantum", "relativity", "entropy", "enthalpy",
    "wavelength", "frequency", "amplitude", "velocity",
    "acceleration", "momentum", "thermodynamics", "electromagnetic",
    # كيمياء
    "catalyst", "polymer", "isotope", "electrolyte",
    "oxidation", "reduction", "synthesis", "titration",
    "covalent", "ionic", "molecular", "stoichiometry",
    # أحياء
    "mitosis", "meiosis", "photosynthesis", "respiration",
    "chromosome", "genotype", "phenotype", "mutation",
    "biodiversity", "ecosystem", "symbiosis", "homeostasis",
    # رياضيات
    "algorithm", "polynomial", "derivative", "integral",
    "correlation", "regression", "variance", "deviation",
    "hypothesis", "probability", "permutation", "combination",
}

ABBREVIATIONS: set[str] = {
    # تقنية
    "HTML", "CSS", "JS", "TS", "XML", "HTTP", "HTTPS", "FTP",
    "SSH", "SSL", "TLS", "TCP", "UDP", "DNS", "DHCP",
    "REST", "SOAP", "GraphQL", "JSON", "YAML", "TOML",
    "IDE", "CLI", "GUI", "API", "SDK", "SDKs",
    "SQL", "NoSQL", "ORM", "ODM",
    # عامة
    "NASA", "IEEE", "ISO", "UTF", "ASCII", "Unicode",
    "URL", "URI", "URN", "PDF", "CSV", "JSONL",
    "GPU", "TPU", "NPU", "SSD", "HDD", "RAM", "ROM",
    "LAN", "WAN", "VPN", "IoT", "SaaS", "PaaS", "IaaS",
    # أوائل كلمات طبية وعلمية
    "CT", "MRI", "PET", "ECG", "EEG", "EMG",
    "DNA", "RNA", "mRNA", "tRNA", "rRNA",
    "WHO", "CDC", "FDA", "NIH", "AMA",
}


# ======================================================================
# فئة مدير الكلمات المحمية
# ======================================================================

class ProtectedWordsManager:
    """مدير شامل للكلمات المحمية من التصحيح الإملائي.

    يوفر واجهة موحدة لإدارة المصطلحات المتخصصة وتكاملها
    مع المصحح الإملائي.

    Attributes:
        categories: قاموس الفئات ومصطلحاتها.
        custom_vocabulary: المصطلحات المخصصة.
    """

    # الفئات المدعومة مع مجموعاتها الافتراضية
    DEFAULT_CATEGORIES: dict[str, set[str]] = {
        "programming": TECHNICAL_KEYWORDS,
        "python": PYTHON_KEYWORDS,
        "medical": MEDICAL_TERMS,
        "scientific": SCIENTIFIC_TERMS,
        "abbreviations": ABBREVIATIONS,
    }

    def __init__(
        self,
        custom_vocabulary_path: Optional[str | Path] = None,
        additional_categories: Optional[dict[str, set[str]]] = None,
    ) -> None:
        """تهيئة مدير الكلمات المحمية.

        Args:
            custom_vocabulary_path: مسار ملف المصطلحات المخصصة (JSON).
            additional_categories: فئات إضافية مخصصة.
        """
        # نسخ المجموعات الافتراضية
        self.categories: dict[str, set[str]] = {
            name: set(words) for name, words in self.DEFAULT_CATEGORIES.items()
        }

        # إضافة فئات مخصصة
        if additional_categories:
            for cat_name, words in additional_categories.items():
                if cat_name in self.categories:
                    self.categories[cat_name].update(words)
                else:
                    self.categories[cat_name] = set(words)

        # المصطلحات المخصصة
        self.custom_vocabulary: dict[str, str] = {}  # word -> category

        # تحميل المصطلحات المخصصة من ملف
        if custom_vocabulary_path:
            self.load_custom_vocabulary(custom_vocabulary_path)

        # إعادة بناء الفهرس
        self._protected_index: set[str] = set()
        self._rebuild_index()

        logger.info(
            "تم تهيئة مدير الكلمات المحمية: %d فئة, %d كلمة إجمالي",
            len(self.categories), len(self._protected_index),
        )

    def _rebuild_index(self) -> None:
        """إعادة بناء الفهرس الموحد للبحث السريع (case-insensitive)."""
        self._protected_index = set()

        for words in self.categories.values():
            self._protected_index.update(w.lower() for w in words)

        self._protected_index.update(w.lower() for w in self.custom_vocabulary)

    # ------------------------------------------------------------------
    # فحص الحماية
    # ------------------------------------------------------------------

    def is_protected(self, word: str) -> bool:
        """فحص هل الكلمة محمية من التصحيح.

        البحث بأحرف مطابقة (case-insensitive).

        Args:
            word: الكلمة المراد فحصها.

        Returns:
            True إذا كانت محمية.

        Example:
            >>> manager.is_protected("React")  # True
            >>> manager.is_protected("hello")  # False
        """
        return word.lower() in self._protected_index

    def get_category(self, word: str) -> Optional[str]:
        """الحصول على فئة الكلمة المحمية.

        Args:
            word: الكلمة المراد فحصها.

        Returns:
            اسم الفئة أو None إذا لم تكن محمية.
        """
        word_lower = word.lower()

        # فحص الفئات المحددة
        for cat_name, words in self.categories.items():
            if word_lower in {w.lower() for w in words}:
                return cat_name

        # فحص المصطلحات المخصصة
        if word_lower in {w.lower() for w in self.custom_vocabulary}:
            return self.custom_vocabulary.get(word, "custom")

        return None

    # ------------------------------------------------------------------
    # إدارة المصطلحات المخصصة
    # ------------------------------------------------------------------

    def add_words(
        self,
        words: list[str],
        category: str = "custom",
    ) -> int:
        """إضافة كلمات إلى القائمة المحمية.

        Args:
            words: قائمة الكلمات المطلوب حمايتها.
            category: الفئة (مثل "custom", "names", "domain_specific").

        Returns:
            عدد الكلمات المُضافة فعلياً (تجاهل التكرار).

        Example:
            >>> manager.add_words(["TrOCR", "Surya", "Kitab"], category="ocr")
        """
        added = 0
        for word in words:
            word = word.strip()
            if not word:
                continue

            word_lower = word.lower()
            if word_lower in self._protected_index:
                logger.debug("كلمة محمية بالفعل: '%s'", word)
                continue

            self.custom_vocabulary[word] = category
            self._protected_index.add(word_lower)
            added += 1

        # إضافة الفئة إذا لم تكن موجودة
        if category != "custom" and category not in self.categories:
            self.categories[category] = set()

        if added > 0:
            logger.info(
                "تمت إضافة %d كلمة محمية (الفئة: '%s')",
                added, category,
            )

        return added

    def remove_words(self, words: list[str]) -> int:
        """إزالة كلمات من القائمة المحمية (المخصصة فقط).

        لا يمكن إزالة كلمات من المجموعات الافتراضية المحددة مسبقاً.

        Args:
            words: قائمة الكلمات المراد إزالتها.

        Returns:
            عدد الكلمات المُزالة فعلياً.

        Example:
            >>> manager.remove_words(["old_term", "deprecated_word"])
        """
        removed = 0

        for word in words:
            word = word.strip()
            if not word:
                continue

            # إزالة من المصطلحات المخصصة فقط
            if word in self.custom_vocabulary:
                del self.custom_vocabulary[word]
                self._protected_index.discard(word.lower())
                removed += 1
                logger.debug("تمت إزالة: '%s'", word)
            else:
                # فحص هل الكلمة من المجموعات الافتراضية
                in_default = False
                for cat_words in self.DEFAULT_CATEGORIES.values():
                    if word.lower() in {w.lower() for w in cat_words}:
                        in_default = True
                        break

                if in_default:
                    logger.debug(
                        "لا يمكن إزالة '%s' — من مجموعة محددة مسبقاً",
                        word,
                    )
                else:
                    # ليست محمية أصلاً
                    pass

        if removed > 0:
            self._rebuild_index()

        return removed

    # ------------------------------------------------------------------
    # تكامل مع المصحح الإملائي
    # ------------------------------------------------------------------

    def filter_protected(
        self,
        words: list[str],
        include_category: bool = False,
    ) -> list[str | dict[str, str]]:
        """فلترة الكلمات المحمية من قائمة كلمات.

        يُستخدم لتحديد الكلمات التي يجب تخطيها أثناء التصحيح الإملائي.

        Args:
            words: قائمة الكلمات المراد فحصها.
            include_category: تضمين الفئة في النتيجة.

        Returns:
            قائمة الكلمات المحمية (أو قواميس مع الفئة).

        Example:
            >>> to_skip = manager.filter_protected(["hello", "numpy", "world"])
            >>> # to_skip == ["numpy"]
            >>> detailed = manager.filter_protected(["hello", "numpy"], include_category=True)
            >>> # detailed == [{"word": "numpy", "category": "programming"}]
        """
        protected = []

        for word in words:
            if self.is_protected(word):
                if include_category:
                    cat = self.get_category(word) or "unknown"
                    protected.append({"word": word, "category": cat})
                else:
                    protected.append(word)

        return protected

    def get_safe_words(
        self,
        words: list[str],
    ) -> list[str]:
        """الحصول على الكلمات غير المحمية (الآمنة للتصحيح).

        Args:
            words: قائمة الكلمات.

        Returns:
            قائمة الكلمات غير المحمية.

        Example:
            >>> safe = manager.get_safe_words(["hello", "numpy", "world"])
            >>> # safe == ["hello", "world"]
        """
        return [w for w in words if not self.is_protected(w)]

    def protect_text(self, text: str, placeholder: str = "█") -> tuple[str, dict[str, str]]:
        """حماية المصطلحات في نص عن طريق استبدالها بعناصر نائبة.

        مفيد لتصحيح نص دون المساس بالمصطلحات.

        Args:
            text: النص الأصلي.
            placeholder: العنصر النائب (الافتراضي: █).

        Returns:
            tuple (النص المحمي، قاموس {عنصر_نائب: كلمة_أصلية}).

        Example:
            >>> protected_text, mapping = manager.protect_text("using numpy and pandas")
            >>> # protected_text ≈ "using █ and █"
            >>> # mapping = {"█_0": "numpy", "█_1": "pandas"}
        """
        import re

        # تجزئة النص إلى كلمات مع الفواصل
        tokens: list[tuple[str, str]] = []
        pattern = re.compile(r"(\S+)(\s*)")
        for match in pattern.finditer(text):
            tokens.append((match.group(1), match.group(2)))

        mapping: dict[str, str] = {}
        result_tokens: list[str] = []
        placeholder_counter = 0

        for word, separator in tokens:
            if self.is_protected(word):
                placeholder_key = f"{placeholder}_{placeholder_counter}"
                mapping[placeholder_key] = word
                result_tokens.append(placeholder_key)
                placeholder_counter += 1
            else:
                result_tokens.append(word)

            result_tokens.append(separator)

        protected_text = "".join(result_tokens)
        return protected_text, mapping

    def restore_text(self, text: str, mapping: dict[str, str]) -> str:
        """استعادة الكلمات المحمية في نص بعد التصحيح.

        Args:
            text: النص بعد التصحيح (مع العناصر النائبة).
            mapping: القاموس من protect_text().

        Returns:
            النص المُستعاد.
        """
        result = text
        for placeholder, original in mapping.items():
            result = result.replace(placeholder, original)
        return result

    # ------------------------------------------------------------------
    # إحصائيات ومعلومات
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """الحصول على إحصائيات عن الكلمات المحمية.

        Returns:
            قاموس يحتوي:
            - total_protected: العدد الإجمالي
            - by_category: التوزيع حسب الفئة
            - custom_count: عدد المصطلحات المخصصة
        """
        by_category: dict[str, int] = {}
        for cat_name, words in self.categories.items():
            by_category[cat_name] = len(words)

        if self.custom_vocabulary:
            by_category["custom_user"] = len(self.custom_vocabulary)

        return {
            "total_protected": len(self._protected_index),
            "by_category": by_category,
            "custom_count": len(self.custom_vocabulary),
        }

    def get_words_by_category(self, category: str) -> list[str]:
        """الحصول على الكلمات في فئة معينة.

        Args:
            category: اسم الفئة.

        Returns:
            قائمة الكلمات (مرتبة).
        """
        if category in self.categories:
            return sorted(self.categories[category])
        elif category == "custom_user":
            return sorted(self.custom_vocabulary.keys())
        return []

    def search(self, query: str, max_results: int = 20) -> list[dict[str, str]]:
        """البحث في الكلمات المحمية.

        Args:
            query: نص البحث (يبحث في البداية — prefix search).
            max_results: أقصى عدد نتائج.

        Returns:
            قائمة قواميس {"word": ..., "category": ...}.
        """
        query_lower = query.lower()
        results: list[dict[str, str]] = []

        for cat_name, words in self.categories.items():
            for word in words:
                if word.lower().startswith(query_lower):
                    results.append({"word": word, "category": cat_name})
                    if len(results) >= max_results:
                        return results

        for word, cat in self.custom_vocabulary.items():
            if word.lower().startswith(query_lower):
                results.append({"word": word, "category": cat})
                if len(results) >= max_results:
                    return results

        return results

    # ------------------------------------------------------------------
    # حفظ وتحميل المصطلحات المخصصة
    # ------------------------------------------------------------------

    def save_custom_vocabulary(self, path: str | Path) -> str:
        """حفظ المصطلحات المخصصة في ملف JSON.

        Args:
            path: مسار ملف الحفظ.

        Returns:
            مسار الملف المحفوظ.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "custom_vocabulary": dict(self.custom_vocabulary),
            "metadata": {
                "total_words": len(self.custom_vocabulary),
                "saved_at": self._get_timestamp(),
            },
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("تم حفظ %d مصطلح مخصص في: %s", len(self.custom_vocabulary), path)
        return str(path)

    def load_custom_vocabulary(self, path: str | Path) -> int:
        """تحميل المصطلحات المخصصة من ملف JSON.

        Args:
            path: مسار ملف التحميل.

        Returns:
            عدد المصطلحات المُحمَّلة.
        """
        path = Path(path)
        if not path.exists():
            logger.warning("ملف المصطلحات غير موجود: %s", path)
            return 0

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            vocab = data.get("custom_vocabulary", {})
            if isinstance(vocab, dict):
                count = 0
                for word, category in vocab.items():
                    word = str(word).strip()
                    category = str(category).strip()
                    if word and word.lower() not in self._protected_index:
                        self.custom_vocabulary[word] = category
                        count += 1

                self._rebuild_index()
                logger.info("تم تحميل %d مصطلح مخصص من: %s", count, path)
                return count
            else:
                logger.warning("صيغة ملف المصطلحات غير صحيحة: %s", path)
                return 0

        except json.JSONDecodeError as e:
            logger.error("خطأ في قراءة ملف المصطلحات: %s", e)
            return 0
        except Exception as e:
            logger.error("فشل في تحميل المصطلحات: %s", e)
            return 0

    @staticmethod
    def _get_timestamp() -> str:
        """الحصول على الطابع الزمني الحالي."""
        from datetime import datetime
        return datetime.now().isoformat()

    # ------------------------------------------------------------------
    # تمثيل النص
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ProtectedWordsManager("
            f"total={len(self._protected_index)}, "
            f"categories={len(self.categories)}, "
            f"custom={len(self.custom_vocabulary)})"
        )

    def __len__(self) -> int:
        return len(self._protected_index)
