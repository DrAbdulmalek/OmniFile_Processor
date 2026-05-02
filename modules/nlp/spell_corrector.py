"""
المصحح الإملائي الذكي (Smart Spell Corrector) v2.1
==========================================================
تصحيح إملائي متعدد اللغات (عربي + إنجليزي + ألماني) مع حماية المصطلحات التقنية.
يتعلم من تصحيحات المستخدم ويحفظها محلياً.

اللغات المدعومة:
- الإنجليزية (en) - pyspellchecker
- العربية (ar) - ar-corrector
- الألمانية (de) - pyspellchecker (German)
"""

import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


class SpellCorrector:
    """
    مصحح إملائي ذكي — يدعم العربية والإنجليزية مع حماية المصطلحات البرمجية.

    الخصائص:
        correction_file (str): مسار ملف التصحيحات المُتعلمة.
        min_votes (int): الحد الأدنى للأصوات لتفعيل التصحيح المُتعلم.
    """

    # كلمات بايثون المحجوزة — لا تصحح أبداً
    _PYTHON_KEYWORDS: set[str] = {
        "print", "float", "int", "str", "bool", "list", "dict", "set", "tuple",
        "def", "class", "import", "from", "return", "yield",
        "if", "else", "elif", "for", "while", "with", "as",
        "try", "except", "finally", "raise", "assert", "break", "continue",
        "lambda", "pass", "global", "nonlocal", "del",
        "and", "or", "not", "in", "is",
        "True", "False", "None",
        "async", "await",
        "self", "cls", "super",
        "property", "staticmethod", "classmethod",
        "range", "len", "type", "isinstance", "issubclass",
        "enumerate", "zip", "map", "filter", "sorted", "reversed",
        "input", "open", "file", "iter", "next",
        "abs", "all", "any", "bin", "chr", "dir", "eval", "exec",
        "format", "getattr", "hasattr", "hash", "help", "hex", "id",
        "max", "min", "oct", "ord", "pow", "repr", "round", "sum",
        "vars",
        "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
        "AttributeError", "RuntimeError", "StopIteration", "NotImplementedError",
        "IOError", "OSError", "ImportError", "ModuleNotFoundError",
        "FileNotFoundError", "PermissionError",
    }

    # دوال بايثون المضمنة وأسماء وحدات شائعة
    _PROTECTED_NAMES: set[str] = {
        "numpy", "pandas", "matplotlib", "scipy", "sklearn",
        "tensorflow", "torch", "keras", "pytorch",
        "requests", "flask", "django", "fastapi", "uvicorn",
        "pytest", "unittest", "logging", "pathlib", "argparse",
        "datetime", "collections", "itertools", "functools",
        "asyncio", "multiprocessing", "threading", "subprocess",
        "http", "urllib", "json", "csv", "xml", "html",
        "sqlalchemy", "pymysql", "psycopg2", "redis",
        "docker", "kubernetes", "git", "npm", "pip", "conda",
        "JavaScript", "TypeScript", "Python", "Java", "C++",
        "React", "Vue", "Angular", "Node", "Express",
        "MongoDB", "PostgreSQL", "MySQL", "Redis", "SQLite",
        "AWS", "GCP", "Azure", "Linux", "Ubuntu",
    }

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: str = "cpu",
        correction_file: Optional[str] = None,
        min_votes: int = 2,
    ) -> None:
        """
        تهيئة المصحح الإملائي.

        المعاملات:
            model_name: اسم النموذج (محجوز للاستخدام المستقبلي).
            device: الجهاز المستخدم.
            correction_file: مسار ملف التصحيحات المُتعلمة.
            min_votes: الحد الأدنى للأصوات لتفعيل تصحيح مُتعلم.
        """
        self.model_name = model_name
        self.device = device
        self.min_votes = min_votes

        # مسار ملف التصحيحات المُتعلمة
        if correction_file:
            self._correction_file = correction_file
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self._correction_file = os.path.join(base_dir, "correction_dict.json")

        # المصطلحات المحمية (يمكن للمستخدم إضافة المزيد)
        self._protected_terms: set[str] = set(self._PYTHON_KEYWORDS | self._PROTECTED_NAMES)

        # التصحيحات المُتعلمة: {خطأ: {تصحيح: عدد_الأصوات}}
        self._learned_corrections: dict[str, dict[str, int]] = {}
        self._load_corrections()

        # اللغات المدعومة
        self.supported_languages = ["en", "ar", "de"]

        # محاولة تحميل مكتبات التصحيح
        self._en_corrector = None
        self._en_available = False
        self._ar_corrector = None
        self._ar_available = False
        self._de_corrector = None
        self._de_available = False

        self._try_load_english_corrector()
        self._try_load_arabic_corrector()
        self._try_load_german_corrector()

    # ------------------------------------------------------------------
    # تحميل المصححات (كسول)
    # ------------------------------------------------------------------
    def _try_load_english_corrector(self) -> None:
        """محاولة تحميل مصحح الإنجليزية (pyspellchecker)."""
        try:
            from spellchecker import SpellChecker  # type: ignore

            self._en_corrector = SpellChecker(language="en")
            self._en_available = True
            logger.info("تم تحميل مصحح الإنجليزية (pyspellchecker) بنجاح")
        except ImportError:
            logger.warning(
                "مكتبة pyspellchecker غير مثبتة. التصحيح الإنجليزي غير متاح. "
                "pip install pyspellchecker"
            )
        except Exception as e:
            logger.warning("فشل تحميل مصحح الإنجليزية: %s", e)

    def _try_load_arabic_corrector(self) -> None:
        """محاولة تحميل مصحح العربية (ar-corrector)."""
        try:
            from ar_corrector.corrector import Corrector  # type: ignore

            self._ar_corrector = Corrector()
            self._ar_available = True
            logger.info("تم تحميل مصحح العربية (ar-corrector) بنجاح")
        except ImportError:
            logger.warning(
                "مكتبة ar-corrector غير مثبتة. التصحيح العربي غير متاح. "
                "pip install ar-corrector"
            )
        except Exception as e:
            logger.warning("فشل تحميل مصحح العربية: %s", e)

    # ------------------------------------------------------------------
    # إدارة التصحيحات المُتعلمة
    # ------------------------------------------------------------------
    def _load_corrections(self) -> None:
        """تحميل التصحيحات المُتعلمة من الملف."""
        try:
            if os.path.exists(self._correction_file):
                with open(self._correction_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # التحويل: الصيغة القديمة {خطأ: تصحيح} → الجديدة {خطأ: {تصحيح: أصوات}}
                    self._learned_corrections = {}
                    for wrong, correct_or_dict in data.items():
                        if isinstance(correct_or_dict, dict):
                            self._learned_corrections[wrong] = {
                                k: int(v) for k, v in correct_or_dict.items()
                            }
                        else:
                            self._learned_corrections[wrong] = {
                                str(correct_or_dict): 1
                            }
                logger.info(
                    "تم تحميل %d تصحيح مُتعلم", len(self._learned_corrections)
                )
        except Exception as e:
            logger.warning("فشل تحميل التصحيحات المُتعلمة: %s", e)
            self._learned_corrections = {}

    def _save_corrections(self) -> None:
        """حفظ التصحيحات المُتعلمة إلى الملف."""
        try:
            with open(self._correction_file, "w", encoding="utf-8") as f:
                json.dump(self._learned_corrections, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("فشل حفظ التصحيحات المُتعلمة: %s", e)

    def learn_correction(self, wrong_word: str, correct_word: str) -> None:
        """
        تعليم المصحح تصحيحاً جديداً.

        المعاملات:
            wrong_word: الكلمة الخاطئة.
            correct_word: التصحيح الصحيح.
        """
        wrong_word = wrong_word.strip().lower()
        correct_word = correct_word.strip()

        if wrong_word == correct_word:
            return

        if wrong_word not in self._learned_corrections:
            self._learned_corrections[wrong_word] = {}

        if correct_word not in self._learned_corrections[wrong_word]:
            self._learned_corrections[wrong_word][correct_word] = 0

        self._learned_corrections[wrong_word][correct_word] += 1
        self._save_corrections()
        logger.info("تم تعلم التصحيح: '%s' → '%s' (أصوات: %d)",
                     wrong_word, correct_word,
                     self._learned_corrections[wrong_word][correct_word])

    def _get_learned_correction(self, word: str) -> Optional[str]:
        """
        البحث عن تصحيح مُتعلم لكلمة.

        المعاملات:
            word: الكلمة المراد تصحيحها.

        العائد:
            التصحيح إذا وُجد وتجاوز الحد الأدنى للأصوات، وإلا None.
        """
        word_lower = word.lower()
        if word_lower not in self._learned_corrections:
            return None

        corrections = self._learned_corrections[word_lower]
        if not corrections:
            return None

        # اختيار التصحيح الأعلى أصواتاً
        best_correction = max(corrections, key=corrections.get)  # type: ignore
        best_votes = corrections[best_correction]

        if best_votes >= self.min_votes:
            return best_correction
        return None

    # ------------------------------------------------------------------
    # كشف اللغة للكلمة
    # ------------------------------------------------------------------
    @staticmethod
    def _is_arabic_word(word: str) -> bool:
        """هل الكلمة عربية؟"""
        arabic_chars = sum(1 for c in word if "\u0600" <= c <= "\u06FF")
        return arabic_chars > len(word) * 0.5

    @staticmethod
    def _is_english_word(word: str) -> bool:
        """هل الكلمة إنجليزية؟"""
        latin_chars = sum(1 for c in word if c.isalpha() and c.isascii())
        return latin_chars > len(word) * 0.5

    # ------------------------------------------------------------------
    # تصحيح الكلمات الفردية
    # ------------------------------------------------------------------
    def _correct_english_word(self, word: str) -> Optional[str]:
        """
        تصحيح كلمة إنجليزية.

        المعاملات:
            word: الكلمة المراد تصحيحها.

        العائد:
            التصحيح إذا وُجد، وإلا None.
        """
        # التحقق أولاً من المصطلحات المحمية
        if word in self._protected_terms or word.lower() in self._protected_terms:
            return None

        # التحقق من التصحيحات المُتعلمة
        learned = self._get_learned_correction(word)
        if learned:
            return learned

        # التصحيح بـ pyspellchecker
        if self._en_available and self._en_corrector:
            try:
                # تجاهل الكلمات القصيرة جداً
                if len(word) <= 2:
                    return None

                # إذا كانت الكلمة صحيحة بالفعل
                if word.lower() in self._en_corrector.word_frequency:
                    return None

                candidates = self._en_corrector.correction(word)
                if candidates and candidates.lower() != word.lower():
                    # التحقق من أن التصحيح معقول (نفس الطول تقريباً)
                    if abs(len(candidates) - len(word)) <= 3:
                        return candidates
            except Exception as e:
                logger.debug("خطأ في تصحيح '%s': %s", word, e)

        return None

    def _correct_arabic_word(self, word: str) -> Optional[str]:
        """
        تصحيح كلمة عربية.

        المعاملات:
            word: الكلمة المراد تصحيحها.

        العائد:
            التصحيح إذا وُجد، وإلا None.
        """
        # التحقق أولاً من المصطلحات المحمية
        if word in self._protected_terms:
            return None

        # التحقق من التصحيحات المُتعلمة
        learned = self._get_learned_correction(word)
        if learned:
            return learned

        # التصحيح بـ ar-corrector
        if self._ar_available and self._ar_corrector:
            try:
                result = self._ar_corrector.correct_sentence(word)
                if result and result != word and result.strip():
                    return result.strip()
            except Exception as e:
                logger.debug("خطأ في تصحيح '%s': %s", word, e)

        return None

    # ------------------------------------------------------------------
    # حماية المصطلحات
    # ------------------------------------------------------------------
    def _should_skip_word(self, word: str) -> bool:
        """
        هل يجب تخطي تصحيح هذه الكلمة؟

        المعاملات:
            word: الكلمة المراد فحصها.

        العائد:
            True إذا كانت محمية.
        """
        # كلمات فارغة
        if not word.strip():
            return True

        # أرقام
        if word.isdigit() or re.match(r"^[\d.,%]+$", word):
            return True

        # رموز
        if re.match(r"^[^a-zA-Z\u0600-\u06FF]+$", word):
            return True

        # كلمات بايثون محجوزة
        if word in self._PYTHON_KEYWORDS:
            return True

        # مصطلحات محمية
        if word in self._protected_terms or word.lower() in self._protected_terms:
            return True

        # مقاطع الكود (تحتوي على _ أو -)
        if "_" in word or "-" in word:
            return True

        # camelCase أو PascalCase
        if re.match(r"^[a-z]+[A-Z]", word) or re.match(r"^[A-Z][a-z]+[A-Z]", word):
            return True

        # أسماء ملفات
        if re.match(r"^.*\.\w{1,4}$", word) and "." in word:
            return True

        # كلمات قصيرة جداً
        if len(word) <= 1:
            return True

        return False

    # ------------------------------------------------------------------
    # الواجهة العامة
    # ------------------------------------------------------------------
    def correct_word(self, word: str) -> str:
        """
        تصحيح كلمة واحدة.

        المعاملات:
            word: الكلمة المراد تصحيحها.

        العائد:
            الكلمة المصححة (أو الأصلية إذا لم يتم العثور على تصحيح).
        """
        if self._should_skip_word(word):
            return word

        if self._is_arabic_word(word):
            correction = self._correct_arabic_word(word)
        elif self._is_english_word(word):
            correction = self._correct_english_word(word)
        else:
            return word

        return correction if correction else word

    def correct_text(self, text: str) -> dict:
        """
        تصحيح النص بالكامل.

        المعاملات:
            text: النص المراد تصحيحه.

        العائد:
            قاموس يحتوي على:
                - corrected_text: النص المصحح
                - corrections: قائمة التصحيحات التفصيلية
                - total_corrections: عدد التصحيحات
        """
        if not text or not text.strip():
            return {
                "corrected_text": "",
                "corrections": [],
                "total_corrections": 0,
            }

        # تجزئة النص إلى كلمات مع الحفاظ على الفواصل
        tokens: list[tuple[str, str]] = []  # (الكلمة, الفاصل)
        pattern = re.compile(r"(\S+)(\s*)")
        for match in pattern.finditer(text):
            tokens.append((match.group(1), match.group(2)))

        corrected_tokens: list[str] = []
        corrections_list: list[dict] = []
        correction_count = 0

        for word, separator in tokens:
            corrected = self.correct_word(word)
            corrected_tokens.append(corrected + separator)

            if corrected != word:
                corrections_list.append({
                    "original": word,
                    "corrected": corrected,
                    "position": len("".join(corrected_tokens[:-1])),
                })
                correction_count += 1

        corrected_text = "".join(corrected_tokens)

        return {
            "corrected_text": corrected_text,
            "corrections": corrections_list,
            "total_corrections": correction_count,
        }

    def correct_with_protection(
        self,
        text: str,
        protected_terms: Optional[list[str]] = None,
    ) -> dict:
        """
        تصحيح النص مع حماية مصطلحات محددة.

        المعاملات:
            text: النص المراد تصحيحه.
            protected_terms: قائمة المصطلحات الإضافية المحمية.

        العائد:
            قاموس نتيجة التصحيح (مثل correct_text).
        """
        # حفظ المصطلحات المحمية الحالية
        old_protected = set(self._protected_terms)

        # إضافة المصطلحات المؤقتة
        if protected_terms:
            for term in protected_terms:
                self._protected_terms.add(term)

        try:
            result = self.correct_text(text)
            return result
        finally:
            # استعادة المصطلحات المحمية
            self._protected_terms = old_protected

    def add_protected_term(self, term: str) -> None:
        """
        إضافة مصطلح محمي بشكل دائم.

        المعاملات:
            term: المصطلح المراد حمايته.
        """
        self._protected_terms.add(term)
        logger.info("تمت إضافة '%s' إلى المصطلحات المحمية", term)

    def remove_protected_term(self, term: str) -> bool:
        """
        إزالة مصطلح من الحماية (إذا لم يكن من الكلمات المحجوزة).

        المعاملات:
            term: المصطلح المراد إزالته.

        العائد:
            True إذا تمت الإزالة.
        """
        if term in self._PYTHON_KEYWORDS:
            logger.warning("لا يمكن إزالة كلمة بايثون محجوزة: %s", term)
            return False

        if term in self._protected_terms:
            self._protected_terms.discard(term)
            logger.info("تمت إزالة '%s' من المصطلحات المحمية", term)
            return True
        return False

    def get_protected_terms(self) -> set[str]:
        """
        عرض المصطلحات المحمية.

        العائد:
            مجموعة المصطلحات المحمية.
        """
        return set(self._protected_terms)

    def get_learned_corrections(self) -> dict[str, dict[str, int]]:
        """
        عرض التصحيحات المُتعلمة.

        العائد:
            قاموس التصحيحات المُتعلمة.
        """
        return dict(self._learned_corrections)

    def clear_learned_corrections(self) -> None:
        """مسح جميع التصحيحات المُتعلمة."""
        self._learned_corrections = {}
        self._save_corrections()
        logger.info("تم مسح جميع التصحيحات المُتعلمة")

    def _try_load_german_corrector(self) -> None:
        """محاولة تحميل مصحح الألمانية (pyspellchecker - German)."""
        try:
            from spellchecker import SpellChecker  # type: ignore

            self._de_corrector = SpellChecker(language="de")
            self._de_available = True
            logger.info("تم تحميل مصحح الألمانية (pyspellchecker) بنجاح")
        except ImportError:
            logger.warning(
                "مكتبة pyspellchecker غير مثبتة. التصحيح الألماني غير متاح. "
                "pip install pyspellchecker"
            )
        except Exception as e:
            logger.warning("فشل تحميل مصحح الألمانية: %s", e)

    def _correct_german_word(self, word: str) -> Optional[str]:
        """
        تصحيح كلمة ألمانية.

        المعاملات:
            word: الكلمة المراد تصحيحها.

        العائد:
            التصحيح إذا وُجد، وإلا None.
        """
        # التحقق من المصطلحات المحمية
        if word in self._protected_terms or word.lower() in self._protected_terms:
            return None

        # التحقق من التصحيحات المُتعلمة
        learned = self._get_learned_correction(word)
        if learned:
            return learned

        # التصحيح بـ pyspellchecker
        if self._de_available and self._de_corrector:
            try:
                if len(word) <= 2:
                    return None

                if word.lower() in self._de_corrector.word_frequency:
                    return None

                candidates = self._de_corrector.correction(word)
                if candidates and candidates.lower() != word.lower():
                    if abs(len(candidates) - len(word)) <= 3:
                        return candidates
            except Exception as e:
                logger.debug("خطأ في تصحيح ألماني '%s': %s", word, e)

        return None

    @staticmethod
    def _is_german_word(word: str) -> bool:
        """هل الكلمة ألمانية؟"""
        # كشف الأحرف الألمانية الخاصة
        german_chars = sum(1 for c in word if c in "äöüÄÖÜß")
        if german_chars > 0:
            return True
        # كلمات بأحرف لاتينية بدون عربي
        latin_chars = sum(1 for c in word if c.isalpha() and c.isascii())
        arabic_chars = sum(1 for c in word if "\u0600" <= c <= "\u06FF")
        return latin_chars > len(word) * 0.5 and arabic_chars == 0

    def correct_word(self, word: str) -> str:
        """
        تصحيح كلمة واحدة.

        المعاملات:
            word: الكلمة المراد تصحيحها.

        العائد:
            الكلمة المصححة (أو الأصلية إذا لم يتم العثور على تصحيح).
        """
        if self._should_skip_word(word):
            return word

        if self._is_arabic_word(word):
            correction = self._correct_arabic_word(word)
        elif self._is_german_word(word):
            correction = self._correct_german_word(word)
        elif self._is_english_word(word):
            correction = self._correct_english_word(word)
        else:
            return word

        return correction if correction else word

    def is_available(self) -> dict[str, bool]:
        """
        فحص توفر المصححات.
        Check availability of spell correctors.

        العائد / Returns:
            قاموس: {english: bool, arabic: bool, german: bool, learned: bool}
        """
        return {
            "english": self._en_available,
            "arabic": self._ar_available,
            "german": self._de_available,
            "learned": len(self._learned_corrections) > 0,
        }

    def correct_batch(self, texts: list[str], max_workers: int = 4) -> list[dict]:
        """تصحيح مجموعة نصوص بشكل متوازٍ.
        Batch-correct multiple texts in parallel using ThreadPoolExecutor.

        Args:
            texts: قائمة نصوص للتصحيح / List of texts to correct
            max_workers: عدد العمال المتوازيين / Number of parallel workers

        Returns:
            قائمة نتائج التصحيح (نفس تنسيق correct_text)
            List of correction results (same format as correct_text)
        """
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(self.correct_text, texts))
        return results

    def correct_word_batch(self, words: list[str], max_workers: int = 4) -> list[str]:
        """تصحيح مجموعة كلمات بشكل متوازٍ.
        Batch-correct multiple words in parallel using ThreadPoolExecutor.

        Args:
            words: قائمة كلمات / List of words to correct
            max_workers: عدد العمال المتوازيين / Number of parallel workers

        Returns:
            قائمة الكلمات المصححة / List of corrected words
        """
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(self.correct_word, words))
        return results
