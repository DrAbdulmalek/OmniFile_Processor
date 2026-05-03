"""
فاحص البيانات الحساسة (Sensitive Data Scanner)
==================================================
فحص النصوص للكشف عن بيانات حساسة مثل:
- أرقام بطاقات الائتمانية
- أرقام الهواتف
- عناوين البريد الإلكتروني
- أرقام الهويات الوطنية
- كلمات المرور والأسرار
- عناوين IP

يدعم:
- مكتبة presidio (عند توفرها)
- أنماط Regex احتياطية (بدون مكتبات خارجية)
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class SensitiveDataScanner:
    """
    فاحص البيانات الحساسة — يكشف عن الأنماط الخطرة في النصوص.

    يعمل بطريقتين:
    1. باستخدام presidio (أكثر دقة) إذا كان متاحاً
    2. باستخدام Regex احتياطي (يعمل دائماً)
    """

    # أنماط Regex الاحتياطية
    FALLBACK_PATTERNS: list[dict] = [
        {
            "name": "CREDIT_CARD",
            "label": "بطاقة ائتمانية",
            "regex": r"\b(?:\d[ -]*?){13,16}\b",
            "risk": "high",
        },
        {
            "name": "EMAIL_ADDRESS",
            "label": "بريد إلكتروني",
            "regex": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
            "risk": "medium",
        },
        {
            "name": "PHONE_NUMBER",
            "label": "رقم هاتف",
            "regex": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b",
            "risk": "medium",
        },
        {
            "name": "IP_ADDRESS",
            "label": "عنوان IP",
            "regex": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "risk": "low",
        },
        {
            "name": "SSN",
            "label": "رقم ضمان اجتماعي",
            "regex": r"\b\d{3}-\d{2}-\d{4}\b",
            "risk": "high",
        },
        {
            "name": "API_KEY",
            "label": "مفتاح API",
            "regex": r"(?i)(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}['\"]?",
            "risk": "high",
        },
        {
            "name": "JWT_TOKEN",
            "label": "رمز JWT",
            "regex": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
            "risk": "high",
        },
        {
            "name": "AWS_KEY",
            "label": "مفتاح AWS",
            "regex": r"(?:AKIA|ASIA)[A-Z0-9]{16}",
            "risk": "high",
        },
        {
            "name": "PRIVATE_KEY",
            "label": "مفتاح خاص",
            "regex": r"-----BEGIN(?: RSA | EC | DSA | OPENSSH )?PRIVATE KEY-----",
            "risk": "critical",
        },
        {
            "name": "IBAN",
            "label": "رقم IBAN",
            "regex": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,}",
            "risk": "high",
        },
    ]

    def __init__(self, use_presidio: bool = True) -> None:
        """
        تهيئة الفاحص.

        المعاملات:
            use_presidio: محاولة استخدام presidio إذا كان متاحاً
        """
        self.use_presidio = use_presidio
        self._presidio_available = False
        self._analyzer = None
        self._anonymizer = None

        # أنماط مخصصة إضافية
        self._custom_patterns: list[dict] = []

        if use_presidio:
            self._try_load_presidio()

    def _try_load_presidio(self) -> None:
        """محاولة تحميل مكتبة presidio."""
        try:
            from presidio_analyzer import AnalyzerEngine  # type: ignore
            from presidio_anonymizer import AnonymizerEngine  # type: ignore

            self._analyzer = AnalyzerEngine()
            self._anonymizer = AnonymizerEngine()
            self._presidio_available = True
            logger.info("تم تحميل presidio بنجاح")
        except ImportError:
            logger.info(
                "presidio غير مثبت. سيتم استخدام Regex فقط. "
                "pip install presidio-analyzer presidio-anonymizer"
            )
        except Exception as e:
            logger.warning("فشل تحميل presidio: %s", e)

    def add_custom_pattern(
        self,
        name: str,
        label: str,
        regex: str,
        risk: str = "medium",
    ) -> None:
        """
        إضافة نمط مخصص للكشف.

        المعاملات:
            name: اسم النمط
            label: وصف بالعربية
            regex: نمط Regex
            risk: مستوى الخطورة (low/medium/high/critical)
        """
        self._custom_patterns.append({
            "name": name,
            "label": label,
            "regex": regex,
            "risk": risk,
        })

        # إضافة لـ presidio أيضاً
        if self._presidio_available:
            try:
                from presidio_analyzer import Pattern, PatternRecognizer

                pattern = Pattern(
                    name=name,
                    regex=regex,
                    score=0.7 if risk == "medium" else 0.9,
                )
                recognizer = PatternRecognizer(
                    supported_entity=name,
                    patterns=[pattern],
                )
                self._analyzer.registry.add_recognizer(recognizer)
                logger.info("تم إضافة النمط المخصص '%s' لـ presidio", name)
            except Exception as e:
                logger.warning("فشل إضافة النمط لـ presidio: %s", e)

    def scan_text(
        self,
        text: str,
        language: str = "en",
    ) -> dict:
        """
        فحص نص للكشف عن بيانات حساسة.

        المعاملات:
            text: النص المراد فحصه
            language: لغة النص ('en' أو 'ar')

        العائد:
            قاموس يحتوي:
                - sensitive_data_found: هل وُجدت بيانات حساسة؟
                - entities: قائمة الكيانات المكتشفة
                - risk_level: مستوى الخطورة العام
                - total_entities: عدد الكيانات
                - scanner_type: نوع الفاحص المستخدم
        """
        if not text or not text.strip():
            return {
                "sensitive_data_found": False,
                "entities": [],
                "risk_level": "none",
                "total_entities": 0,
                "scanner_type": "none",
            }

        entities = []

        # استخدام presidio إذا كان متاحاً
        if self._presidio_available and self._analyzer:
            try:
                results = self._analyzer.analyze(
                    text=text,
                    language=language,
                )
                for entity in results:
                    entities.append({
                        "type": entity.entity_type,
                        "text": text[entity.start: entity.end],
                        "start": entity.start,
                        "end": entity.end,
                        "confidence": entity.score,
                        "scanner": "presidio",
                    })
            except Exception as e:
                logger.warning("فشل فحص presidio: %s", e)

        # دائماً: استخدام Regex كطبقة إضافية
        all_patterns = self.FALLBACK_PATTERNS + self._custom_patterns
        for pattern_info in all_patterns:
            try:
                matches = re.finditer(pattern_info["regex"], text)
                for match in matches:
                    matched_text = match.group()
                    # تجنب التكرار مع presidio
                    already_found = any(
                        e["text"] == matched_text and e["start"] == match.start()
                        for e in entities
                    )
                    if not already_found:
                        entities.append({
                            "type": pattern_info["name"],
                            "label": pattern_info["label"],
                            "text": matched_text,
                            "start": match.start(),
                            "end": match.end(),
                            "risk": pattern_info["risk"],
                            "scanner": "regex",
                        })
            except re.error:
                logger.warning("نمط Regex غير صالح: %s", pattern_info["name"])

        # حساب مستوى الخطورة
        risk_level = self._calculate_risk_level(entities)

        return {
            "sensitive_data_found": len(entities) > 0,
            "entities": entities,
            "risk_level": risk_level,
            "total_entities": len(entities),
            "scanner_type": "presidio" if self._presidio_available else "regex",
        }

    def anonymize_text(
        self,
        text: str,
        language: str = "en",
        mask_char: str = "[REDACTED]",
    ) -> str:
        """
        إزالة البيانات الحساسة من النص.

        المعاملات:
            text: النص المراد معالجته
            language: لغة النص
            mask_char: النص البديل للبيانات الحساسة

        العائد:
            النص بعد إزالة البيانات الحساسة
        """
        if not text:
            return text

        # استخدام presidio إذا كان متاحاً
        if self._presidio_available and self._anonymizer and self._analyzer:
            try:
                results = self._analyzer.analyze(text=text, language=language)
                anonymized = self._anonymizer.anonymize(
                    text=text,
                    analyzer_results=results,
                )
                return anonymized.text
            except Exception as e:
                logger.warning("فشل إخفاء presidio: %s", e)

        # استخدام Regex كاحتياطي
        anonymized = text
        all_patterns = self.FALLBACK_PATTERNS + self._custom_patterns
        for pattern_info in all_patterns:
            try:
                anonymized = re.sub(pattern_info["regex"], mask_char, anonymized)
            except re.error:
                pass

        return anonymized

    def scan_file(self, file_path: str, encoding: str = "utf-8") -> dict:
        """
        فحص ملف للكشف عن بيانات حساسة.

        المعاملات:
            file_path: مسار الملف
            encoding: ترميز الملف

        العائد:
            نتيجة الفحص (مثل scan_text) مع إضافة file_path
        """
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            result = self.scan_text(content)
            result["file_path"] = file_path
            result["file_size"] = len(content)
            return result
        except Exception as e:
            return {
                "sensitive_data_found": False,
                "entities": [],
                "risk_level": "error",
                "total_entities": 0,
                "file_path": file_path,
                "error": str(e),
            }

    @staticmethod
    def _calculate_risk_level(entities: list[dict]) -> str:
        """
        حساب مستوى الخطورة العام.

        المعاملات:
            entities: قائمة الكيانات المكتشفة

        العائد:
            مستوى الخطورة: none/low/medium/high/critical
        """
        if not entities:
            return "none"

        risk_scores = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        max_risk = 0

        for entity in entities:
            risk = entity.get("risk", "medium")
            if isinstance(risk, str):
                score = risk_scores.get(risk, 2)
            else:
                score = risk
            max_risk = max(max_risk, score)

        for level, score in risk_scores.items():
            if score == max_risk:
                return level

        return "medium"

    def is_available(self) -> dict:
        """
        فحص حالة توفر الفاحص.

        العائد:
            قاموس: {presidio: bool, regex: bool}
        """
        return {
            "presidio": self._presidio_available,
            "regex": True,
            "custom_patterns": len(self._custom_patterns),
        }
