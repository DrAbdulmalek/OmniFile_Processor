"""
ملخص النصوص (Text Summarizer)
================================
تلخيص النصوص الطويلة باستخدام نماذج BART و Pegasus.
يدعم: الإنجليزية والعربية والألمانية.

النماذج المدعومة:
- facebook/bart-large-cnn (إنجليزية - تلخيص أخبار)
- facebook/bart-large-xsum (إنجليزية - تلخيص عام)
- google/pegasus-xsum (إنجليزية - تلخيص BBC)
- UAE-Code/mbart-summarization-ar (عربية)
"""

import hashlib
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class TextSummarizer:
    """
    ملخص النصوص الذكي — يدعم الإنجليزية والعربية والألمانية.

    الميزات:
    - تحميل بطيء (Lazy Loading)
    - كشف GPU تلقائي
    - تخزين مؤقت للنتائج
    - تلخيص متعدد النماذج
    - انحطاط سلس عند الفشل
    """

    # النموذج الأساسي لكل لغة (النموذج الأول المُستخدم عند التلخيص)
    # Primary model per language (first model used for summarization)
    _MODELS: dict[str, str] = {
        "en": "facebook/bart-large-cnn",
        "ar": "UAE-Code/mbart-summarization-ar",
        "de": "google/mt5-small",
    }

    # النموذج السريع للإنجليزية (أصغر وأسرع)
    # Fast model for English (smaller and faster)
    _FAST_MODEL: str = "sshleifer/distilbart-cnn-12-6"

    # النماذج المتاحة حسب اللغة (قائمة كاملة تشمل بدائل)
    # All available models per language (full list including alternatives)
    MODELS_BY_LANG = {
        "en": [
            "facebook/bart-large-cnn",
            "facebook/bart-large-xsum",
            "google/pegasus-xsum",
        ],
        "ar": [
            "UAE-Code/mbart-summarization-ar",
        ],
        "de": [
            "google/mt5-small",
            "facebook/bart-large-cnn",
        ],
    }

    # النماذج الاحتياطية (إذا فشل النموذج الأساسي)
    FALLBACK_MODELS = {
        "en": "facebook/bart-large-cnn",
        "ar": "UAE-Code/mbart-summarization-ar",
        "de": "facebook/bart-large-cnn",
    }

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        max_length: int = 130,
        min_length: int = 30,
        max_input_length: int = 1024,
        enable_cache: bool = True,
        fast_mode: bool = False,
    ) -> None:
        """
        تهيئة ملخص النصوص.

        المعاملات:
            model_name: اسم النموذج (إذا None، يُختار تلقائياً حسب اللغة)
            device: الجهاز ('cuda' أو 'cpu' أو None لتلقائي)
            max_length: أقصى طول للملخص
            min_length: أدنى طول للملخص
            max_input_length: أقصى طول للنص المدخل
            enable_cache: تفعيل التخزين المؤقت
            fast_mode: استخدام نموذج سريع للإنجليزية (distilbart)
        """
        self.model_name = model_name
        self._specified_device = device
        self.max_length = max_length
        self.min_length = min_length
        self.max_input_length = max_input_length
        self.enable_cache = enable_cache
        self.fast_mode = fast_mode

        # النموذج - تُحمّل بشكل بطيء
        self._pipeline = None
        self._loaded_model_name = None
        self._device = device or self._detect_device()

        # الكاش
        self._cache: dict[str, dict] = {}

        # فحص توفر المكتبات
        self._has_transformers = self._check_library("transformers")
        self._has_torch = self._check_library("torch")

    @staticmethod
    def _detect_device() -> str:
        """كشف أفضل جهاز متاح."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except (ImportError, Exception):
            pass
        return "cpu"

    @staticmethod
    def _check_library(import_name: str) -> bool:
        """التحقق من توفر مكتبة."""
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False

    @staticmethod
    def _detect_language(text: str) -> str:
        """
        كشف لغة النص بسيط.

        المعاملات:
            text: النص المراد فحصه

        العائد:
            رمز اللغة: 'ar', 'en', 'de' (افتراضي: 'en')
        """
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
        german_chars = sum(1 for c in text if c in "äöüÄÖÜß")

        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha == 0:
            return "en"

        if arabic_chars / total_alpha > 0.3:
            return "ar"
        if german_chars / total_alpha > 0.05:
            return "de"
        return "en"

    def _resolve_model_name(self, language: str) -> str:
        """
        اختيار النموذج المناسب للغة.
        Select the appropriate model for the given language.

        المعاملات / Args:
            language: رمز اللغة / Language code ('en', 'ar', 'de')

        العائد / Returns:
            اسم النموذج / Model name string
        """
        if self.model_name:
            return self.model_name

        # في الوضع السريع، استخدم نموذج distilbart للإنجليزية
        # In fast mode, use distilbart model for English
        if self.fast_mode and language == "en":
            return self._FAST_MODEL

        # استخدم النموذج الأساسي من _MODELS أولاً، ثم الرجوع لقائمة MODELS_BY_LANG
        # Use primary model from _MODELS first, then fall back to MODELS_BY_LANG list
        primary = self._MODELS.get(language)
        if primary:
            return primary

        models = self.MODELS_BY_LANG.get(language, self.MODELS_BY_LANG["en"])
        return models[0] if models else "facebook/bart-large-cnn"

    def _load_pipeline(self, model_name: str) -> bool:
        """
        تحميل نموذج التلخيص (يتم مرة واحدة).

        المعاملات:
            model_name: اسم النموذج

        العائد:
            True إذا تم التحميل بنجاح
        """
        if self._loaded_model_name == model_name and self._pipeline is not None:
            return True

        if not (self._has_transformers and self._has_torch):
            logger.warning(
                "مكتبات transformers/torch غير مثبتة. "
                "pip install transformers torch"
            )
            return False

        try:
            from transformers import pipeline

            logger.info("جارٍ تحميل نموذج التلخيص: %s على %s...", model_name, self._device)
            self._pipeline = pipeline(
                "summarization",
                model=model_name,
                device=self._device,
            )
            self._loaded_model_name = model_name
            logger.info("تم تحميل نموذج التلخيص بنجاح")
            return True

        except Exception as e:
            logger.error("فشل تحميل نموذج التلخيص '%s': %s", model_name, e)

            # محاولة بالنموذج الاحتياطي
            language = "en"  # default
            for lang, models in self.MODELS_BY_LANG.items():
                if model_name in models:
                    language = lang
                    break

            fallback = self.FALLBACK_MODELS.get(language)
            if fallback and fallback != model_name:
                logger.info("محاولة بالنموذج الاحتياطي: %s", fallback)
                try:
                    from transformers import pipeline
                    self._pipeline = pipeline(
                        "summarization",
                        model=fallback,
                        device=self._device,
                    )
                    self._loaded_model_name = fallback
                    logger.info("تم تحميل النموذج الاحتياطي بنجاح")
                    return True
                except Exception as e2:
                    logger.error("فشل النموذج الاحتياطي أيضاً: %s", e2)

            return False

    def _get_cache_key(self, text: str, model_name: str) -> str:
        """حساب مفتاح كاش."""
        content = f"{model_name}:{text[:500]}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def summarize(
        self,
        text: str,
        language: Optional[str] = None,
        max_length: Optional[int] = None,
        min_length: Optional[int] = None,
    ) -> dict:
        """
        تلخيص النص.

        المعاملات:
            text: النص المراد تلخيصه
            language: لغة النص (إذا None، يُكشف تلقائياً)
            max_length: أقصى طول للملخص
            min_length: أدنى طول للملخص

        العائد:
            قاموس يحتوي:
                - summary: الملخص
                - original_length: طول النص الأصلي
                - summary_length: طول الملخص
                - compression_ratio: نسبة الضغط
                - language: اللغة المكتشفة
                - model: النموذج المستخدم
                - from_cache: هل كانت من الكاش؟
                - processing_time: وقت المعالجة
        """
        start_time = time.time()

        if not text or not text.strip():
            return {
                "summary": "",
                "original_length": 0,
                "summary_length": 0,
                "compression_ratio": 0.0,
                "language": "unknown",
                "model": "none",
                "from_cache": False,
                "processing_time": time.time() - start_time,
            }

        # كشف اللغة
        detected_lang = language or self._detect_language(text)
        model_name = self._resolve_model_name(detected_lang)

        # فحص الكاش
        if self.enable_cache:
            cache_key = self._get_cache_key(text, model_name)
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                cached["from_cache"] = True
                return cached

        # تقصير النص إذا كان طويلاً جداً
        input_text = text.strip()
        if len(input_text) > self.max_input_length:
            # تقصير عند حدود الجمل
            cutoff = self.max_input_length
            last_period = input_text.rfind(".", 0, cutoff)
            if last_period > cutoff * 0.5:
                input_text = input_text[: last_period + 1]
            else:
                input_text = input_text[:cutoff]
            logger.info("تم تقصير النص من %d إلى %d حرف", len(text), len(input_text))

        # التأكد من أن النص طويل بما يكفي للتلخيص
        if len(input_text.split()) < 30:
            return {
                "summary": input_text,
                "original_length": len(input_text),
                "summary_length": len(input_text),
                "compression_ratio": 1.0,
                "language": detected_lang,
                "model": "none",
                "reason": "text_too_short",
                "from_cache": False,
                "processing_time": time.time() - start_time,
            }

        # تحميل النموذج
        if not self._load_pipeline(model_name):
            # انحطاط سلس: إرجاع أول 200 حرف
            fallback_summary = input_text[:200] + "..." if len(input_text) > 200 else input_text
            result = {
                "summary": fallback_summary,
                "original_length": len(input_text),
                "summary_length": len(fallback_summary),
                "compression_ratio": len(fallback_summary) / max(len(input_text), 1),
                "language": detected_lang,
                "model": "fallback_truncate",
                "from_cache": False,
                "processing_time": time.time() - start_time,
            }
            return result

        # التلخيص
        try:
            m_len = max_length or self.max_length
            n_len = min_length or self.min_length

            # التأكد من أن max_length أقل من طول النص
            if m_len >= len(input_text.split()):
                m_len = max(len(input_text.split()) // 2, n_len + 10)

            output = self._pipeline(
                input_text,
                max_length=m_len,
                min_length=n_len,
                do_sample=False,
                truncation=True,
            )

            summary = output[0]["summary_text"].strip()

        except Exception as e:
            logger.error("فشل التلخيص: %s", e)
            summary = input_text[:200] + "..." if len(input_text) > 200 else input_text

        processing_time = time.time() - start_time

        result = {
            "summary": summary,
            "original_length": len(input_text),
            "summary_length": len(summary),
            "compression_ratio": len(summary) / max(len(input_text), 1),
            "language": detected_lang,
            "model": self._loaded_model_name or model_name,
            "from_cache": False,
            "processing_time": processing_time,
        }

        # حفظ في الكاش
        if self.enable_cache:
            self._cache[self._get_cache_key(text, model_name)] = result

        return result

    def summarize_batch(
        self,
        texts: list[str],
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> list[dict]:
        """
        تلخيص مجموعة نصوص.

        المعاملات:
            texts: قائمة النصوص
            language: لغة مشتركة (إذا None، يُكشف لكل نص)
            progress_callback: دالة(current, total, status)

        العائد:
            قائمة نتائج التلخيص
        """
        results = []
        total = len(texts)

        for i, text in enumerate(texts):
            if progress_callback:
                progress_callback(i, total, f"تلخيص نص {i + 1}/{total}")

            result = self.summarize(text, language=language)
            result["batch_index"] = i
            results.append(result)

        if progress_callback:
            progress_callback(total, total, "اكتمل التلخيص")

        return results

    def get_available_models(self, language: str = "en") -> list[str]:
        """
        قائمة النماذج المتاحة للغة.

        المعاملات:
            language: رمز اللغة

        العائد:
            قائمة أسماء النماذج
        """
        return self.MODELS_BY_LANG.get(language, [])

    def clear_cache(self) -> None:
        """مسح التخزين المؤقت."""
        self._cache = {}
        logger.info("تم مسح كاش الملخصات")

    def is_available(self) -> bool:
        """هل الملخص متاح؟"""
        return self._has_transformers and self._has_torch
