"""
كاشف اللغة التلقائي (Language Detector)
=========================================
يكتشف لغة النص تلقائياً (عربي، إنجليزي، أو مختلط).
يدعم النصوص القصيرة والمعالجة الدفعية.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    كاشف اللغة التلقائي — يكتشف ما إذا كان النص عربياً أو إنجليزياً أو مختلطاً.

    الخصائص:
        model_name (str, optional): اسم النموذج (محجوز للاستخدام المستقبلي).
        device (str, optional): الجهاز المستخدم (cpu/cuda).
        min_length (int): الحد الأدنى لطول النص للكشف عبر langdetect.
        arabic_pattern (re.Pattern): نمط مطابقة الحروف العربية.

    مثال:
        >>> detector = LanguageDetector()
        >>> result = detector.detect("مرحبا بالعالم")
        >>> print(result["language"])  # 'ar'
    """

    # نطاق أحرف اليونيكود للعربية
    _ARABIC_PATTERN = re.compile(
        r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
    )
    # نطاق أحرف اليونيكود للاتينية (إنجليزية أساساً)
    _LATIN_PATTERN = re.compile(r"[A-Za-z]")

    def __init__(self, model_name: Optional[str] = None, device: str = "cpu") -> None:
        """
        تهيئة كاشف اللغة.

        المعاملات:
            model_name: اسم النموذج (محجوز).
            device: الجهاز المستخدم (cpu/cuda).
        """
        self.model_name = model_name
        self.device = device
        self.min_length: int = 10  # الحد الأدنى لاستخدام langdetect

        # تحميل langdetect بشكل كسول
        self._langdetect_available: bool = False
        self._try_import_langdetect()

    def _try_import_langdetect(self) -> None:
        """محاولة استيراد مكتبة langdetect."""
        try:
            from langdetect import detect as ld_detect  # type: ignore
            from langdetect import detect_langs as ld_detect_langs  # type: ignore
            self._ld_detect = ld_detect
            self._ld_detect_langs = ld_detect_langs
            self._langdetect_available = True
            logger.info("تم تحميل مكتبة langdetect بنجاح")
        except ImportError:
            self._langdetect_available = False
            logger.warning(
                "مكتبة langdetect غير مثبتة. سيتم الاعتماد على التحليل الإحصائي فقط. "
                "قم بتثبيتها: pip install langdetect"
            )

    # ------------------------------------------------------------------
    # التحليل الإحصائي (يعمل دائماً بدون مكتبات خارجية)
    # ------------------------------------------------------------------
    def _count_scripts(self, text: str) -> dict[str, int]:
        """
        عدد الحروف العربية واللاتينية في النص.

        المعاملات:
            text: النص المراد تحليله.

        العائد:
            قاموس يحتوي على: arabic, latin, total
        """
        arabic_count = len(self._ARABIC_PATTERN.findall(text))
        latin_count = len(self._LATIN_PATTERN.findall(text))
        total = max(arabic_count + latin_count, 1)
        return {
            "arabic": arabic_count,
            "latin": latin_count,
            "total": total,
        }

    def _statistical_detect(self, text: str) -> dict:
        """
        كشف اللغة بالتحليل الإحصائي (يعمل دائماً).

        المعاملات:
            text: النص المراد تحليله.

        العائد:
            قاموس نتيجة الكشف.
        """
        counts = self._count_scripts(text)
        arabic_ratio = counts["arabic"] / counts["total"]
        latin_ratio = counts["latin"] / counts["total"]

        # عتبة لتحديد اللغة السائدة
        dominant_threshold = 0.70
        mixed_threshold = 0.30  # كل لغة تمثل 30% على الأقل = مختلط

        if arabic_ratio >= dominant_threshold:
            language = "ar"
            confidence = round(arabic_ratio, 4)
        elif latin_ratio >= dominant_threshold:
            language = "en"
            confidence = round(latin_ratio, 4)
        else:
            language = "mixed"
            confidence = round(max(arabic_ratio, latin_ratio), 4)

        return {
            "language": language,
            "confidence": confidence,
            "is_arabic": language == "ar",
            "is_english": language == "en",
            "is_mixed": language == "mixed",
            "arabic_ratio": round(arabic_ratio, 4),
            "latin_ratio": round(latin_ratio, 4),
            "method": "statistical",
        }

    # ------------------------------------------------------------------
    # الكشف عبر langdetect (أكثر دقة للنصوص الطويلة)
    # ------------------------------------------------------------------
    def _langdetect_analyze(self, text: str) -> dict:
        """
        كشف اللغة باستخدام مكتبة langdetect.

        المعاملات:
            text: النص المراد تحليله.

        العائد:
            قاموس نتيجة الكشف.
        """
        try:
            langs = self._ld_detect_langs(text)  # type: ignore
            # تحويل النتائج إلى قائمة مرتبة
            results = []
            for lang_obj in langs:
                code = str(lang_obj.lang).split("-")[0]  # مثال: ar, en
                prob = lang_obj.prob
                results.append((code, prob))

            if not results:
                return self._statistical_detect(text)

            top_lang, top_conf = results[0]

            # تحويل رموز اللغة
            lang_map = {
                "ar": "ar",
                "arz": "ar",
                "en": "en",
            }
            language = lang_map.get(top_lang, top_lang)

            # التحقق مما إذا كان مختلطاً
            is_mixed = False
            for code, prob in results:
                mapped = lang_map.get(code, code)
                if mapped != language and prob > 0.20:
                    is_mixed = True
                    break

            # دمج مع التحليل الإحصائي لتعزيز الثقة
            counts = self._count_scripts(text)
            arabic_ratio = counts["arabic"] / counts["total"]
            latin_ratio = counts["latin"] / counts["total"]

            if is_mixed:
                language = "mixed"

            return {
                "language": language,
                "confidence": round(top_conf, 4),
                "is_arabic": language == "ar",
                "is_english": language == "en",
                "is_mixed": language == "mixed",
                "arabic_ratio": round(arabic_ratio, 4),
                "latin_ratio": round(latin_ratio, 4),
                "method": "langdetect",
                "all_results": [(c, round(p, 4)) for c, p in results],
            }
        except Exception as e:
            logger.warning("فشل كشف اللغة بـ langdetect: %s — يتم الرجوع للتحليل الإحصائي", e)
            return self._statistical_detect(text)

    # ------------------------------------------------------------------
    # الواجهة العامة
    # ------------------------------------------------------------------
    def detect(self, text: str) -> dict:
        """
        كشف لغة النص.

        يستخدم langdetect إذا توفرت والنص طويل بما يكفي،
        وإلا يعتمد على التحليل الإحصائي.

        المعاملات:
            text: النص المراد تحليل لغته.

        العائد:
            قاموس يحتوي على:
                - language (str): 'ar' | 'en' | 'mixed'
                - confidence (float): مستوى الثقة [0-1]
                - is_arabic (bool)
                - is_english (bool)
                - is_mixed (bool)
                - arabic_ratio (float)
                - latin_ratio (float)
                - method (str): 'langdetect' | 'statistical'
        """
        if not text or not text.strip():
            logger.warning("نص فارغ تم تمريره لكاشف اللغة")
            return {
                "language": "unknown",
                "confidence": 0.0,
                "is_arabic": False,
                "is_english": False,
                "is_mixed": False,
                "arabic_ratio": 0.0,
                "latin_ratio": 0.0,
                "method": "none",
            }

        cleaned = text.strip()

        # نص قصير جداً → تحليل إحصائي فقط
        if len(cleaned) < self.min_length:
            logger.debug("نص قصير (%d حرف) — يتم استخدام التحليل الإحصائي", len(cleaned))
            return self._statistical_detect(cleaned)

        # إذا توفر langdetect → استخدامه
        if self._langdetect_available:
            return self._langdetect_analyze(cleaned)

        # خلاف ذلك → تحليل إحصائي
        return self._statistical_detect(cleaned)

    def detect_batch(self, texts: list[str]) -> list[dict]:
        """
        كشف لغة مجموعة نصوص دفعة واحدة.

        المعاملات:
            texts: قائمة بالنصوص المراد تحليل لغتها.

        العائد:
            قائمة بقواميس النتائج بنفس ترتيب الإدخال.
        """
        results: list[dict] = []
        for i, text in enumerate(texts):
            try:
                result = self.detect(text)
                result["index"] = i
                results.append(result)
            except Exception as e:
                logger.error("خطأ في كشف لغة النص #%d: %s", i, e)
                results.append({
                    "index": i,
                    "language": "error",
                    "confidence": 0.0,
                    "is_arabic": False,
                    "is_english": False,
                    "is_mixed": False,
                    "error": str(e),
                    "method": "none",
                })
        logger.info("تم كشف لغة %d نصوص بنجاح", len(results))
        return results

    def is_arabic(self, text: str) -> bool:
        """
        تحقق سريع: هل النص عربي؟

        المعاملات:
            text: النص المراد فحصه.

        العائد:
            True إذا كان النص عربياً.
        """
        return self.detect(text)["is_arabic"]

    def is_english(self, text: str) -> bool:
        """
        تحقق سريع: هل النص إنجليزي؟

        المعاملات:
            text: النص المراد فحصه.

        العائد:
            True إذا كان النص إنجليزياً.
        """
        return self.detect(text)["is_english"]
