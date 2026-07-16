"""
مصنف النصوص (Text Classifier)
================================
يصنف النصوص إلى فئات: برمجية، علمية، أدبية، تقنية، دينية، عامة.
يدعم التصنيف بالكلمات المفتاحية (بدون تحميل نموذج) أو بنموذج HuggingFace.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class TextClassifier:
    """
    مصنف النصوص — يدعم تصنيف النصوص العربية والإنجليزية.

    الفئات المدعومة:
        - code: نصوص برمجية
        - scientific: نصوص علمية وأكاديمية
        - literary: نصوص أدبية وشعرية
        - technical: نصوص تقنية وتكنولوجية
        - religious: نصوص دينية
        - general: نصوص عامة

    الخصائص:
        model_name (str, optional): اسم نموذج HuggingFace.
        device (str): الجهاز المستخدم (cpu/cuda).
    """

    # الكلمات المفتاحية لكل فئة (إنجليزي)
    _CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "code": [
            "def ", "class ", "import ", "from ", "return ", "function",
            "print(", "self.", "if __name__", "async ", "await ",
            "var ", "let ", "const ", "console.log", "=> {", "module.exports",
            "#include", "int main(", "public class", "void ",
            "try:", "except ", "finally:", "raise ", "lambda ",
            "SELECT ", "FROM ", "WHERE ", "INSERT INTO", "CREATE TABLE",
            "<html", "<div", "<!DOCTYPE", "<script", "</body>",
            "git ", "npm ", "pip install", "docker", "kubectl",
            "TODO:", "FIXME:", "HACK:", "NOTE:", "XXX:",
        ],
        "scientific": [
            "hypothesis", "experiment", "analysis", "methodology",
            "correlation", "regression", "statistical", "significant",
            "peer-reviewed", "journal", "research", "empirical",
            "abstract:", "introduction:", "methodology:", "results:",
            "discussion:", "conclusion:", "references:", "citation",
            "p-value", "standard deviation", "confidence interval",
            "الفرضية", "التحليل", "المنهجية", "التجربة", "البحث",
            "النتائج", "الاستنتاج", "الإحصائي", "العينة",
        ],
        "literary": [
            "poem", "poetry", "verse", "stanza", "metaphor", "simile",
            "narrative", "prose", "novel", "chapter", "once upon",
            "allegory", "rhythm", "rhyme", "sonnet", "haiku",
            "قال الشاعر", "قصيدة", "شعر", "بيت", "مقطع",
            "كان يا ما كان", "في قديم الزمان", "رواية", "قصة",
            "وغنى", "وأمسى", "فجر", "غروب", "تبسمت",
        ],
        "technical": [
            "algorithm", "architecture", "framework", "protocol",
            "specification", "implementation", "optimization",
            "scalability", "performance", "throughput", "latency",
            "API", "REST", "HTTP", "JSON", "XML", "endpoint",
            "database", "server", "client", "deployment",
            "الخوارزمية", "البنية", "الإطار", "الأداء", "الخادم",
            "قاعدة البيانات", "التطبيق", "البروتوكول", "الشبكة",
        ],
        "religious": [
            "Quran", "Koran", "Bible", "Torah", "hadith", "sunnah",
            "prophet", "revelation", "prayer", "mosque", "church",
            "scripture", "verse", "chapter", "surah", "ayah",
            "القرآن", "الكريم", "الحديث", "النبوي", "الصلاة",
            "مسجد", "سورة", "آية", "الفقه", "التوحيد", "الشريعة",
            "رضي الله عنه", "صلى الله عليه وسلم", "بسم الله",
            "الحمد لله", "سبحان الله", "الله أكبر",
        ],
    }

    # كلمات برمجة بايثون يجب حمايتها من التصنيف الخاطئ
    _PYTHON_KEYWORDS: set[str] = {
        "print", "float", "int", "str", "bool", "list", "dict",
        "def", "class", "import", "from", "return", "yield",
        "if", "else", "elif", "for", "while", "with", "as",
        "try", "except", "finally", "raise", "assert",
        "lambda", "pass", "break", "continue", "global",
        "nonlocal", "async", "await", "True", "False", "None",
        "and", "or", "not", "in", "is", "del",
        "self", "cls", "super", "property", "staticmethod",
        "range", "len", "type", "isinstance", "enumerate",
        "zip", "map", "filter", "sorted", "reversed",
    }

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: str = "cpu",
    ) -> None:
        """
        تهيئة مصنف النصوص.

        المعاملات:
            model_name: اسم نموذج HuggingFace (اختياري).
                       مثال: "facebook/bart-large-mnli"
            device: الجهاز المستخدم ('cpu' أو 'cuda').
        """
        self.model_name = model_name
        self.device = device
        self._pipeline = None
        self._model_available = False

        # إعداد أنماط المطابقة لكل فئة
        self._category_patterns: dict[str, list[re.Pattern]] = {}
        self._compile_patterns()

        # محاولة تحميل النموذج (كسول)
        if model_name:
            self._try_load_model()

    def _compile_patterns(self) -> None:
        """تحويل الكلمات المفتاحية إلى أنماط regex."""
        for category, keywords in self._CATEGORY_KEYWORDS.items():
            patterns: list[re.Pattern] = []
            for kw in keywords:
                try:
                    patterns.append(re.compile(re.escape(kw), re.IGNORECASE))
                except re.error:
                    logger.debug("نمط غير صالح: %s", kw)
            self._category_patterns[category] = patterns

    def _try_load_model(self) -> None:
        """محاولة تحميل نموذج HuggingFace للتصنيف."""
        try:
            from transformers import pipeline  # type: ignore

            logger.info("جاري تحميل نموذج التصنيف: %s ...", self.model_name)
            self._pipeline = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=self.device,
            )
            self._model_available = True
            logger.info("تم تحميل نموذج التصنيف بنجاح")
        except ImportError:
            logger.warning(
                "مكتبة transformers غير مثبتة. سيتم الاعتماد على التصنيف بالكلمات المفتاحية. "
                "pip install transformers torch"
            )
        except Exception as e:
            logger.warning("فشل تحميل النموذج '%s': %s", self.model_name, e)

    # ------------------------------------------------------------------
    # التصنيف بالكلمات المفتاحية (يعمل دائماً)
    # ------------------------------------------------------------------
    def _keyword_classify(self, text: str) -> dict:
        """
        تصنيف النص بناءً على الكلمات المفتاحية.

        المعاملات:
            text: النص المراد تصنيفه.

        العائد:
            قاموس: category, confidence, keywords_found, scores
        """
        scores: dict[str, float] = {}
        found_keywords: dict[str, list[str]] = {}

        for category, patterns in self._category_patterns.items():
            cat_score = 0.0
            cat_keywords: list[str] = []
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    cat_score += len(matches)
                    cat_keywords.append(pattern.pattern)
            if cat_score > 0:
                scores[category] = cat_score
                found_keywords[category] = cat_keywords

        if not scores:
            return {
                "category": "general",
                "confidence": 0.3,
                "keywords_found": {},
                "scores": {},
                "method": "keyword",
            }

        # تطبيع الدرجات
        total_score = sum(scores.values())
        normalized = {k: round(v / total_score, 4) for k, v in scores.items()}

        # اختيار الفئة الأعلى درجة
        top_category = max(normalized, key=normalized.get)  # type: ignore
        top_confidence = normalized[top_category]

        # إذا كانت أعلى درجة منخفضة → عامة
        if top_confidence < 0.15:
            return {
                "category": "general",
                "confidence": round(top_confidence, 4),
                "keywords_found": found_keywords,
                "scores": normalized,
                "method": "keyword",
            }

        return {
            "category": top_category,
            "confidence": round(top_confidence, 4),
            "keywords_found": found_keywords,
            "scores": normalized,
            "method": "keyword",
        }

    # ------------------------------------------------------------------
    # التصنيف بالنموذج (إذا توفر)
    # ------------------------------------------------------------------
    def _model_classify(self, text: str) -> dict:
        """
        تصنيف النص باستخدام نموذج HuggingFace.

        المعاملات:
            text: النص المراد تصنيفه.

        العائد:
            قاموس نتيجة التصنيف.
        """
        candidate_labels = [
            "programming code", "scientific research", "literature poetry",
            "technical documentation", "religious text", "general writing",
        ]

        label_map = {
            "programming code": "code",
            "scientific research": "scientific",
            "literature poetry": "literary",
            "technical documentation": "technical",
            "religious text": "religious",
            "general writing": "general",
        }

        try:
            result = self._pipeline(text, candidate_labels=candidate_labels)
            labels = result.get("labels", [])
            scores = result.get("scores", [])

            if not labels:
                return self._keyword_classify(text)

            top_label = labels[0]
            top_score = scores[0]

            # تحويل التسميات إلى الفئات الداخلية
            mapped_scores: dict[str, float] = {}
            for label, score in zip(labels, scores):
                mapped = label_map.get(label, "general")
                mapped_scores[mapped] = max(
                    mapped_scores.get(mapped, 0.0), score
                )

            category = label_map.get(top_label, "general")

            return {
                "category": category,
                "confidence": round(top_score, 4),
                "keywords_found": {},
                "scores": {k: round(v, 4) for k, v in mapped_scores.items()},
                "method": "model",
            }
        except Exception as e:
            logger.warning("فشل التصنيف بالنموذج: %s — يتم الرجوع للكلمات المفتاحية", e)
            return self._keyword_classify(text)

    # ------------------------------------------------------------------
    # الواجهة العامة
    # ------------------------------------------------------------------
    def classify(self, text: str) -> dict:
        """
        تصنيف النص إلى فئة.

        المعاملات:
            text: النص المراد تصنيفه.

        العائد:
            قاموس يحتوي على:
                - category (str): الفئة (code/scientific/literary/technical/religious/general)
                - confidence (float): مستوى الثقة [0-1]
                - keywords_found (dict): الكلمات المفتاحية التي تم العثور عليها
                - scores (dict): درجات جميع الفئات
                - method (str): طريقة التصنيف (keyword/model)
        """
        if not text or not text.strip():
            return {
                "category": "general",
                "confidence": 0.0,
                "keywords_found": {},
                "scores": {},
                "method": "none",
            }

        cleaned = text.strip()

        # إذا توفر النموذج → استخدامه
        if self._model_available and self._pipeline is not None:
            return self._model_classify(cleaned)

        # خلاف ذلك → كلمات مفتاحية
        return self._keyword_classify(cleaned)

    def classify_document(self, document_text: str) -> dict:
        """
        تصنيف مستند كامل.

        يقسم المستند إلى أقسام ويصنف كل قسم،
        ثم يجمع النتائج لتحديد الفئة العامة.

        المعاملات:
            document_text: نص المستند الكامل.

        العائد:
            قاموس يحتوي على:
                - category: الفئة السائدة
                - confidence: الثقة الإجمالية
                - section_results: نتائج الأقسام
                - dominant_sections: الفئات الأكثر شيوعاً
        """
        if not document_text or not document_text.strip():
            return {
                "category": "general",
                "confidence": 0.0,
                "section_results": [],
                "dominant_sections": {},
            }

        # تقسيم المستند إلى أقسام حسب الفقرات
        sections = re.split(r"\n\s*\n", document_text.strip())
        sections = [s.strip() for s in sections if len(s.strip()) > 20]

        if not sections:
            return self.classify(document_text)

        section_results: list[dict] = []
        category_counts: dict[str, float] = {}

        for i, section in enumerate(sections):
            result = self.classify(section)
            result["section_index"] = i
            section_results.append(result)

            cat = result["category"]
            conf = result.get("confidence", 0.0)
            category_counts[cat] = category_counts.get(cat, 0.0) + conf

        # الفئة السائدة
        if category_counts:
            dominant = max(category_counts, key=category_counts.get)  # type: ignore
            total_conf = sum(category_counts.values())
            overall_conf = round(category_counts[dominant] / max(total_conf, 1), 4)
        else:
            dominant = "general"
            overall_conf = 0.0

        # ترتيب الفئات حسب الشيوع
        sorted_categories = dict(
            sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        )

        return {
            "category": dominant,
            "confidence": overall_conf,
            "section_results": section_results,
            "dominant_sections": sorted_categories,
            "total_sections": len(sections),
            "method": "document",
        }

    def get_categories(self) -> list[str]:
        """
        عرض قائمة الفئات المدعومة.

        العائد:
            قائمة بأسماء الفئات.
        """
        return list(self._CATEGORY_KEYWORDS.keys()) + ["general"]
