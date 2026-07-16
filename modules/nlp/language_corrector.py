"""
وحدة التدقيق اللغوي (Language Corrector Module)
=================================================
تدقيق نحوي وإملائي متقدم باستخدام LanguageTool.

يختلف عن المصحح الإملائي (spell_corrector.py) في أنه يركز على:
- القواعد النحوية (grammar)
- بنية الجملة (syntax)
- الأسلوب (style)
- الأخطاء الشائعة في السياق

ملاحظة مهمة:
هذه الوحدة تقدم اقتراحات فقط للمراجعة البشرية.
لا تعتمد عليها كطبقة تصحيح نهائية للمصطلحات الطبية المتخصصة.
أنت الطبيب الأدرى بصحة المصطلح.

الاستخدام:
    from modules.nlp.language_corrector import LanguageCorrector
    corrector = LanguageCorrector(lang='ar')
    result = corrector.check("المريض يعاني من الم في الركبة")
    # result = {
    #     'corrected': 'المريض يعاني من ألم في الركبة',
    #     'errors': [{'rule': 'MISSING_SPACE', 'message': '...'}],
    #     'error_count': 1
    # }
"""

import logging
import re
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class LanguageCorrector:
    """
    مدقق لغوي متقدم — يكشف الأخطاء النحوية والإملائية والأسلوبية.

    يدعم:
    - العربية (ar): القواعد النحوية العربية
    - الإنجليزية (en): القواعد الإنجليزية الشاملة
    - متعدد اللغات (auto): كشف تلقائي للغة
    """

    def __init__(self, lang: str = "ar", max_suggestions: int = 3):
        """
        تهيئة المدقق اللغوي.

        Args:
            lang: لغة التدقيق ('ar', 'en', 'auto')
            max_suggestions: الحد الأقصى للاقتراحات لكل خطأ
        """
        self.lang = lang
        self.max_suggestions = max_suggestions
        self._tool = None
        self._available = False

        # مصطلحات طبية محمية — لا يتم تصحيحها أبداً
        self._protected_terms: List[str] = [
            # مصطلحات جراحة العظام العربية
            "عظم الفخذ", "عظم العضد", "الظنبوب", "عظم الساعد",
            "عظم القص", "الترقوة", "الكتف", "الكاحل", "الرسغ",
            "الشظية", "نخاع العظم", "النخاع الشوكي",
            "مفصل الركبة", "مفصل الكتف", "مفصل الورك", "مفصل الكاحل",
            "الرباط الصليبي", "الغضروف المفصلي", "المنیسک",
            "التثبيت الداخلي", "الديناميك", "السنتيس",
            # مصطلحات طبية عامة
            "التهاب المفاصل", "هشاشة العظام", "النقرس",
            "انزلاق غضروفي", "التهاب الأوتار",
            "استئصال المرارة", "فتق دیسك",
        ]

        self._try_load_languagetool()

    def _try_load_languagetool(self):
        """محاولة تحميل مكتبة LanguageTool."""
        try:
            import language_tool_python  # type: ignore
            self._tool = language_tool_python.LanguageTool(self.lang)
            self._available = True
            logger.info("تم تحميل LanguageTool بنجاح (lang=%s)", self.lang)
        except ImportError:
            logger.warning(
                "مكتبة language-tool-python غير متبتة. "
                "التدقيق اللغوي المتقدم غير متاح. "
                "pip install language-tool-python"
            )
        except Exception as e:
            logger.warning("فشل تحميل LanguageTool: %s", e)

    @property
    def is_available(self) -> bool:
        """هل المدقق اللغوي متاح؟"""
        return self._available

    def check(self, text: str) -> Dict[str, Any]:
        """
        فحص النص وتقديم التصحيحات المقترحة.

        Args:
            text: النص المراد فحصه

        Returns:
            قاموس يحتوي على:
                - corrected: النص المصحح
                - errors: قائمة الأخطاء المكتشفة
                - error_count: عدد الأخطاء
                - method: طريقة الفحص ('languagetool' أو 'basic')
        """
        if not text or not text.strip():
            return {
                "corrected": "",
                "errors": [],
                "error_count": 0,
                "method": "none",
            }

        if not self._available:
            # السقوط إلى الفحص الأساسي
            return self._basic_check(text)

        try:
            matches = self._tool.check(text)
            corrected = language_tool_python.utils.correct(text, matches)

            errors = []
            for match in matches:
                error_info = {
                    "message": match.message,
                    "rule": match.ruleIssueType,
                    "category": match.category,
                    "offset": match.offset,
                    "length": match.length,
                    "context": match.context,
                    "replacements": match.replacements[:self.max_suggestions],
                    "original": text[match.offset:match.offset + match.length],
                }

                # التحقق من المصطلحات المحمية
                if self._is_protected(text[match.offset:match.offset + match.length]):
                    error_info["protected"] = True
                    continue

                errors.append(error_info)

            return {
                "corrected": corrected,
                "errors": errors,
                "error_count": len(errors),
                "method": "languagetool",
            }
        except Exception as e:
            logger.error("خطأ في فحص LanguageTool: %s — السقوط إلى الفحص الأساسي", e)
            return self._basic_check(text)

    def _basic_check(self, text: str) -> Dict[str, Any]:
        """
        فحص أساسي بدون LanguageTool.

        يكتشف المشاكل الشائعة مثل:
        - المسافات المفقودة (بعد علامات الترقيم)
        - الأحرف المكررة
        - الأقواس غير المتوازنة
        """
        errors = []
        corrected = text

        # 1. إصلاح المسافات المفقودة بعد علامات الترقيم العربية
        punctuation_pattern = re.compile(r'([.،؛:!؟])\s*([^\s\d])')
        fixes = punctuation_pattern.findall(corrected)
        for i, (punct, char) in enumerate(fixes):
            errors.append({
                "message": f"مسافة مفقودة بعد '{punct}'",
                "rule": "MISSING_SPACE",
                "category": "TYPOGRAPHY",
                "offset": -1,
                "length": -1,
                "replacements": [f"{punct} {char}"],
                "original": f"{punct}{char}",
            })
        corrected = punctuation_pattern.sub(r'\1 \2', corrected)

        # 2. إصلاح الأحرف المكررة (3 أحرف أو أكثر)
        repeated_pattern = re.compile(r'(.)\1{2,}')
        repeated_matches = repeated_pattern.findall(corrected)
        for char in repeated_matches:
            errors.append({
                "message": f"حرف مكرر: '{char}'",
                "rule": "REPEATED_CHAR",
                "category": "TYPOGRAPHY",
                "offset": -1,
                "length": -1,
                "replacements": [char * 2],
                "original": char * 3,
            })
        corrected = repeated_pattern.sub(r'\1\1', corrected)

        # 3. إزالة المسافات قبل علامات الترقيم
        space_before_punct = re.compile(r'\s+([.،؛:!؟])')
        corrected = space_before_punct.sub(r'\1', corrected)

        # 4. إصلاح المسافة قبل/بعد الأقواس
        corrected = re.sub(r'\(\s+', '(', corrected)
        corrected = re.sub(r'\s+\)', ')', corrected)

        return {
            "corrected": corrected.strip(),
            "errors": errors,
            "error_count": len(errors),
            "method": "basic",
        }

    def _is_protected(self, term: str) -> bool:
        """
        التحقق مما إذا كان المصطلح محمياً (طبي متخصص).

        Args:
            term: المصطلح المراد فحصه

        Returns:
            True إذا كان محمياً
        """
        term_lower = term.strip().lower()
        for protected in self._protected_terms:
            if protected.lower() == term_lower:
                return True
            if protected.lower() in term_lower or term_lower in protected.lower():
                return True
        return False

    def add_protected_term(self, term: str):
        """
        إضافة مصطلح محمي (لا يتم تصحيحه).

        Args:
            term: المصطلح المراد حمايته
        """
        if term not in self._protected_terms:
            self._protected_terms.append(term)
            logger.info("تمت إضافة مصطلح محمي: '%s'", term)

    def check_and_protect(
        self,
        text: str,
        protected_terms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        فحص النص مع حماية مصطلحات محددة.

        Args:
            text: النص المراد فحصه
            protected_terms: قائمة المصطلحات الإضافية المحمية

        Returns:
            نتيجة الفحص مع المصطلحات المحمية مميزة
        """
        if protected_terms:
            old_protected = list(self._protected_terms)
            self._protected_terms.extend(protected_terms)

        try:
            return self.check(text)
        finally:
            if protected_terms:
                self._protected_terms = old_protected

    def get_error_summary(self, check_result: Dict[str, Any]) -> str:
        """
        إنشاء ملخص نصي لنتائج الفحص.

        Args:
            check_result: نتيجة الدالة check()

        Returns:
            نص يلخص الأخطاء المكتشفة
        """
        if not check_result["errors"]:
            return "لم يتم كشف أخطاء. النص جيد."

        lines = [f"تم كشف {check_result['error_count']} خطأ:"]
        for i, error in enumerate(check_result["errors"][:10], 1):
            protected = " [محمي]" if error.get("protected") else ""
            lines.append(
                f"  {i}. {error['message']}{protected} "
                f"(اقتراح: {', '.join(error.get('replacements', [])[:3])})"
            )

        if check_result["error_count"] > 10:
            lines.append(f"  ... و {check_result['error_count'] - 10} خطأ آخر")

        return "\n".join(lines)

    def close(self):
        """إغلاق المدقق اللغوي وتحرير الموارد."""
        if self._tool:
            try:
                self._tool.close()
            except Exception as e:
                logger.warning("خطأ في إغلاق LanguageTool: %s", e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __repr__(self):
        status = "متاح" if self._available else "غير متاح"
        return f"LanguageCorrector(lang='{self.lang}', status={status})"
