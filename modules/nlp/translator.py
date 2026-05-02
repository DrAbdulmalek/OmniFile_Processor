"""
المترجم التقني (Technical Translator)
========================================
يترجم النصوص التقنية من الإنجليزية إلى العربية.
يحمي المقاطع البرمجية والمتغيرات وأسماء الدوال من الترجمة.
يدعم الترجمة الدفعية والتخزين المؤقت.
"""

import hashlib
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


class TechnicalTranslator:
    """
    مترجم تقني — يترجم النصوص التقنية مع حماية المصطلحات البرمجية.

    الخصائص:
        model_name (str): اسم نموذج الترجمة.
        device (str): الجهاز المستخدم.
        cache_file (str): مسار ملف التخزين المؤقت.
    """

    # ------------------------------------------------------------------
    # قاموس المصطلحات التقنية
    # ------------------------------------------------------------------
    _DEFAULT_GLOSSARY: dict[str, str] = {
        "machine learning": "التعلم الآلي",
        "deep learning": "التعلم العميق",
        "neural network": "الشبكة العصبية",
        "natural language processing": "معالجة اللغة الطبيعية",
        "computer vision": "الرؤية الحاسوبية",
        "artificial intelligence": "الذكاء الاصطناعي",
        "data science": "علم البيانات",
        "big data": "البيانات الضخمة",
        "cloud computing": "الحوسبة السحابية",
        "blockchain": "سلسلة الكتل",
        "cryptocurrency": "العملة الرقمية",
        "database": "قاعدة البيانات",
        "algorithm": "خوارزمية",
        "API": "API",
        "framework": "إطار عمل",
        "library": "مكتبة",
        "repository": "مستودع",
        "version control": "التحكم بالإصدارات",
        "software engineering": "هندسة البرمجيات",
        "operating system": "نظام التشغيل",
        "web development": "تطوير الويب",
        "front-end": "واجهة أمامية",
        "back-end": "واجهة خلفية",
        "full-stack": "تطوير شامل",
        "user interface": "واجهة المستخدم",
        "user experience": "تجربة المستخدم",
        "responsive design": "تصميم متجاوب",
        "unit test": "اختبار الوحدة",
        "integration test": "اختبار التكامل",
        "continuous integration": "التكامل المستمر",
        "continuous deployment": "النشر المستمر",
        "container": "حاوية",
        "microservice": "خدمة مصغرة",
        "load balancer": "موازن الأحمال",
        "firewall": "جدار حماية",
        "encryption": "تشفير",
        "authentication": "مصادقة",
        "authorization": "تفويض",
        "token": "رمز",
        "open source": "مفتوح المصدر",
        "pull request": "طلب سحب",
        "code review": "مراجعة الكود",
        "debugging": "تصحيح الأخطاء",
        "compilation": "ترجمة برمجية",
        "runtime": "وقت التشغيل",
        "middleware": "برمجية وسيطة",
        "scalability": "قابلية التوسع",
        "throughput": "معدل الإنتاجية",
        "latency": "زمن الاستجابة",
        "bandwidth": "عرض النطاق",
        "server": "خادم",
        "client": "عميل",
        "endpoint": "نقطة نهاية",
        "payload": "حمولة البيانات",
        "middleware": "برمجية وسيطة",
        "dependency": "تبعية",
        "package": "حزمة",
        "module": "وحدة",
        "class": "فئة",
        "object": "كائن",
        "function": "دالة",
        "variable": "متغير",
        "parameter": "معامل",
        "argument": "وسيط",
        "return value": "قيمة مرجعة",
        "exception": "استثناء",
        "thread": "خيط",
        "process": "عملية",
        "memory leak": "تسرب الذاكرة",
        "garbage collection": "جمع القمامة",
        "recursion": "تكرار",
        "iteration": "تكرار حلقي",
        "array": "مصفوفة",
        "linked list": "قائمة مرتبطة",
        "stack": "مكدس",
        "queue": "طابور",
        "tree": "شجرة",
        "graph": "رسم بياني",
        "hash table": "جدول التجزئة",
        "binary search": "بحث ثنائي",
        "sorting algorithm": "خوارزمية فرز",
    }

    # أنماط الحماية — لا تترجم
    _PROTECTION_PATTERNS: list[tuple[str, re.Pattern]] = []

    def __init__(
        self,
        model_name: str = "Helsinki-NLP/opus-mt-en-ar",
        device: str = "cpu",
        cache_file: Optional[str] = None,
    ) -> None:
        """
        تهيئة المترجم التقني.

        المعاملات:
            model_name: اسم نموذج الترجمة من HuggingFace.
            device: الجهاز المستخدم ('cpu' أو 'cuda').
            cache_file: مسار ملف التخزين المؤقت.
        """
        self.model_name = model_name
        self.device = device
        self._tokenizer = None
        self._model = None
        self._model_available = False

        # التخزين المؤقت
        if cache_file:
            self._cache_file = cache_file
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self._cache_file = os.path.join(base_dir, "translation_cache.json")
        self._cache: dict[str, str] = {}
        self._load_cache()

        # القاموس المخصص (يمكن للمن المستخدم التعديل)
        self._glossary: dict[str, str] = dict(self._DEFAULT_GLOSSARY)

        # إعداد أنماط الحماية
        self._setup_protection_patterns()

    def _setup_protection_patterns(self) -> None:
        """إعداد أنماط regex لحماية المقاطع البرمجية."""
        self._PROTECTION_PATTERNS = [
            # مقاطع الكود (```)
            ("code_block_triple", re.compile(r"```[\s\S]*?```", re.DOTALL)),
            # مقاطع الكود (السطر الواحد `)
            ("code_inline", re.compile(r"`[^`]+`")),
            # أسماء المتغيرات snake_case
            ("snake_case", re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")),
            # أسماء الدوال camelCase
            ("camel_case", re.compile(r"\b[a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b")),
            # أسماء الفئات PascalCase
            ("pascal_case", re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b")),
            # المتغيرات بأسماء قصيرة (x, y, z, i, j, k)
            ("single_letter", re.compile(r"\b[a-zA-Z]\b(?![a-zA-Z])")),
            # أسماء الملفات
            ("file_path", re.compile(r"\b[\w.-]+\.(?:py|js|ts|java|cpp|c|h|md|json|xml|yaml|yml|toml|cfg|ini|sh|bat)\b")),
            # عناوين URL
            ("url", re.compile(r"https?://\S+")),
            # عناوين البريد الإلكتروني
            ("email", re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b")),
            # الأرقام والأرقام العشرية
            ("numbers", re.compile(r"\b\d+(?:\.\d+)?\b")),
            # أنواع بيانات Python
            ("python_types", re.compile(r"\b(?:int|float|str|bool|list|dict|set|tuple|None|True|False)\b")),
            # كلمات Python المحجوزة
            ("python_keywords", re.compile(
                r"\b(?:def|class|import|from|return|if|else|elif|for|while|"
                r"try|except|finally|raise|with|as|lambda|yield|pass|"
                r"break|continue|and|or|not|in|is|async|await|global|"
                r"nonlocal|del|assert)\b"
            )),
            # أسماء وحدات بايثون
            ("python_modules", re.compile(
                r"\b(?:os|sys|json|re|math|random|datetime|collections|"
                r"itertools|functools|pathlib|typing|logging|abc|dataclasses|"
                r"numpy|pandas|matplotlib|scipy|sklearn|torch|tensorflow|"
                r"requests|flask|django|fastapi|pytest)\b"
            )),
            # تعليقات الكود
            ("comments", re.compile(r"#[^\n]*")),
            # JSON keys
            ("json_keys", re.compile(r'"[\w]+"\s*:')),
        ]

    def _load_cache(self) -> None:
        """تحميل التخزين المؤقت من الملف."""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info("تم تحميل التخزين المؤقت: %d مدخل", len(self._cache))
        except Exception as e:
            logger.warning("فشل تحميل التخزين المؤقت: %s", e)
            self._cache = {}

    def _save_cache(self) -> None:
        """حفظ التخزين المؤقت إلى الملف."""
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("فشل حفظ التخزين المؤقت: %s", e)

    @staticmethod
    def _text_hash(text: str) -> str:
        """حساب تجزئة النص للتخزين المؤقت."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _protect_code(self, text: str) -> tuple[str, dict[str, str]]:
        """
        حماية المقاطع البرمجية من الترجمة باستخدام العناصر النائبة.

        المعاملات:
            text: النص المراد معالجته.

        العائد:
            tuple: (النص المحمي، قاموس العناصر النائبة)
        """
        protected = text
        placeholders: dict[str, str] = {}
        counter = 0

        for pattern_name, pattern in self._PROTECTION_PATTERNS:
            matches = list(pattern.finditer(protected))
            for match in reversed(matches):  # عكسي لتجنب إزاحة المواضع
                placeholder = f"__PROTECTED_{counter}__"
                placeholders[placeholder] = match.group()
                protected = protected[:match.start()] + placeholder + protected[match.end():]
                counter += 1

        return protected, placeholders

    def _restore_code(self, text: str, placeholders: dict[str, str]) -> str:
        """
        استعادة المقاطع البرمجية المحمية.

        المعاملات:
            text: النص الذي تمت ترجمته.
            placeholders: قاموس العناصر النائبة.

        العائد:
            النص المستعاد مع المقاطع البرمجية.
        """
        restored = text
        for placeholder, original in placeholders.items():
            restored = restored.replace(placeholder, original)
        return restored

    def _apply_glossary(self, text: str) -> str:
        """
        تطبيق القاموس على النص قبل الترجمة.

        المعاملات:
            text: النص المراد معالجته.

        العائد:
            النص بعد تطبيق القاموس.
        """
        result = text
        for en_term, ar_term in self._glossary.items():
            result = result.replace(en_term, ar_term)
        return result

    # ------------------------------------------------------------------
    # تحميل النموذج (كسول)
    # ------------------------------------------------------------------
    def _load_model(self) -> bool:
        """تحميل نموذج الترجمة (يتم مرة واحدة فقط)."""
        if self._model_available:
            return True

        try:
            from transformers import MarianMTModel, MarianTokenizer  # type: ignore

            logger.info("جاري تحميل نموذج الترجمة: %s ...", self.model_name)
            self._tokenizer = MarianTokenizer.from_pretrained(self.model_name)
            self._model = MarianMTModel.from_pretrained(self.model_name)

            # نقل إلى GPU إذا طُلب
            if self.device != "cpu":
                try:
                    self._model = self._model.to(self.device)  # type: ignore
                except Exception as e:
                    logger.warning("فشل نقل النموذج إلى %s: %s", self.device, e)

            self._model_available = True
            self._model.eval()  # type: ignore
            logger.info("تم تحميل نموذج الترجمة بنجاح")
            return True
        except ImportError:
            logger.warning(
                "مكتبة transformers غير مثبتة. الترجمة التلقائية غير متوفرة. "
                "pip install transformers torch sentencepiece"
            )
            return False
        except Exception as e:
            logger.error("فشل تحميل نموذج الترجمة '%s': %s", self.model_name, e)
            return False

    # ------------------------------------------------------------------
    # الترجمة الأساسية
    # ------------------------------------------------------------------
    def _model_translate(self, text: str) -> str:
        """
        ترجمة النص باستخدام النموذج.

        المعاملات:
            text: النص المراد ترجمته.

        العائد:
            النص المترجم.
        """
        try:
            inputs = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=512)  # type: ignore
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}  # type: ignore

            translated = self._model.generate(**inputs)  # type: ignore
            result = self._tokenizer.decode(translated[0], skip_special_tokens=True)  # type: ignore
            return result
        except Exception as e:
            logger.error("خطأ في الترجمة بالنموذج: %s", e)
            return text

    # ------------------------------------------------------------------
    # الواجهة العامة
    # ------------------------------------------------------------------
    def translate_text(
        self,
        text: str,
        source: str = "en",
        target: str = "ar",
    ) -> dict:
        """
        ترجمة النص.

        المعاملات:
            text: النص المراد ترجمته.
            source: لغة المصدر ('en').
            target: لغة الهدف ('ar').

        العائد:
            قاموس يحتوي على:
                - translated_text: النص المترجم
                - source: لغة المصدر
                - target: لغة الهدف
                - method: طريقة الترجمة (model/glossary/unavailable)
                - cached: هل كانت النتيجة من التخزين المؤقت؟
        """
        if not text or not text.strip():
            return {
                "translated_text": "",
                "source": source,
                "target": target,
                "method": "empty",
                "cached": False,
            }

        cleaned = text.strip()

        # التحقق من التخزين المؤقت
        cache_key = self._text_hash(f"{source}:{target}:{cleaned}")
        if cache_key in self._cache:
            logger.debug("تم العثور على النص في التخزين المؤقت")
            return {
                "translated_text": self._cache[cache_key],
                "source": source,
                "target": target,
                "method": "cached",
                "cached": True,
            }

        # إذا كان المصدر عربياً والهدف إنجليزياً → نحتاج نموذج مختلف
        if source == "ar" and target == "en":
            return {
                "translated_text": cleaned + " [ترجمة عربي→إنجليزي غير مدعومة حالياً]",
                "source": source,
                "target": target,
                "method": "unsupported",
                "cached": False,
            }

        # حماية المقاطع البرمجية
        protected_text, placeholders = self._protect_code(cleaned)

        # تحميل النموذج (كسول)
        model_loaded = self._load_model()

        translated = ""

        if model_loaded:
            # ترجمة بالنموذج
            translated = self._model_translate(protected_text)
            method = "model"
        else:
            # تطبيق القاموس فقط كحل بديل
            translated = self._apply_glossary(protected_text)
            if translated == protected_text:
                translated = protected_text + "\n\n[ترجمة غير متوفرة — النموذج غير محمل]"
            method = "glossary_fallback"

        # استعادة المقاطع المحمية
        translated = self._restore_code(translated, placeholders)

        # حفظ في التخزين المؤقت
        self._cache[cache_key] = translated
        self._save_cache()

        return {
            "translated_text": translated,
            "source": source,
            "target": target,
            "method": method,
            "cached": False,
        }

    def translate_document(
        self,
        text: str,
        chunk_size: int = 500,
        source: str = "en",
        target: str = "ar",
    ) -> dict:
        """
        ترجمة مستند كامل بتقسيمه إلى أجزاء.

        المعاملات:
            text: نص المستند.
            chunk_size: حجم كل جزء بالأحرف.
            source: لغة المصدر.
            target: لغة الهدف.

        العائد:
            قاموس يحتوي على:
                - translated_text: النص المترجم الكامل
                - chunks: قائمة نتائج الأجزاء
                - total_chunks: عدد الأجزاء
                - method: 'document'
        """
        if not text or not text.strip():
            return {
                "translated_text": "",
                "chunks": [],
                "total_chunks": 0,
                "method": "document",
            }

        # تقسيم النص حسب الفقرات مع الحفاظ على حدود الجمل
        paragraphs = re.split(r"\n\s*\n", text.strip())
        chunks: list[str] = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # إذا كانت الفقرة أطول من chunk_size → تقسيمها
                if len(para) > chunk_size:
                    # تقسيم عند الجمل
                    sentences = re.split(r'(?<=[.!?؟。])\s+', para)
                    sub_chunk = ""
                    for sent in sentences:
                        if len(sub_chunk) + len(sent) + 1 <= chunk_size:
                            sub_chunk += (" " if sub_chunk else "") + sent
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = sent
                    if sub_chunk:
                        current_chunk = sub_chunk
                    else:
                        current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        # ترجمة كل جزء
        translated_chunks: list[str] = []
        chunk_results: list[dict] = []

        for i, chunk in enumerate(chunks):
            result = self.translate_text(chunk, source=source, target=target)
            translated_chunks.append(result["translated_text"])
            chunk_results.append({
                "chunk_index": i,
                "method": result["method"],
                "length": len(chunk),
            })
            logger.debug("تمت ترجمة الجزء %d/%d", i + 1, len(chunks))

        full_translation = "\n\n".join(translated_chunks)

        return {
            "translated_text": full_translation,
            "chunks": chunk_results,
            "total_chunks": len(chunks),
            "method": "document",
        }

    def add_to_glossary(self, term_en: str, term_ar: str) -> None:
        """
        إضافة مصطلح إلى القاموس المخصص.

        المعاملات:
            term_en: المصطلح بالإنجليزية.
            term_ar: الترجمة بالعربية.
        """
        self._glossary[term_en] = term_ar
        logger.info("تم إضافة '%s' → '%s' إلى القاموس", term_en, term_ar)

    def remove_from_glossary(self, term_en: str) -> bool:
        """
        إزالة مصطلح من القاموس المخصص.

        المعاملات:
            term_en: المصطلح المراد إزالته.

        العائد:
            True إذا تمت الإزالة بنجاح.
        """
        if term_en in self._glossary:
            del self._glossary[term_en]
            logger.info("تم إزالة '%s' من القاموس", term_en)
            return True
        return False

    def clear_cache(self) -> None:
        """مسح التخزين المؤقت."""
        self._cache = {}
        try:
            if os.path.exists(self._cache_file):
                os.remove(self._cache_file)
        except Exception as e:
            logger.warning("فشل حذف ملف التخزين المؤقت: %s", e)
        logger.info("تم مسح التخزين المؤقت")

    def get_glossary(self) -> dict[str, str]:
        """
        عرض القاموس الحالي.

        العائد:
            نسخة من القاموس.
        """
        return dict(self._glossary)
