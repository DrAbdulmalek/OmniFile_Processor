"""
modules/core/engine_router.py
══════════════════════════════
الموجّه الذكي للمحركات — Engine Router
========================================
بدلاً من تشغيل كل محركات OCR معاً (يستهلك كل الذاكرة)،
يختار هذا الموجّه المحركَين الأمثلَين بناءً على:
  - جودة الصورة (image_quality)
  - اللغة المكتشفة (language)
  - نوع الكتلة (block_type: paragraph, table, handwriting, header, footer)
  - البروفايل المحدد (low | balanced | high)

اقتراح من: QWEN (Smart Engine Selector) + Claude (Resource Optimization)

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── ثوابت المحركات ───────────────────────────────────────────────────
ENGINE_EASYOCR   = "EasyOCR"
ENGINE_TROCR     = "TrOCR"
ENGINE_TESSERACT = "Tesseract"
ENGINE_PADDLE    = "PaddleOCR"

# ── متطلبات ذاكرة كل محرك (GB تقريبية) ─────────────────────────────
ENGINE_RAM_REQUIREMENTS = {
    ENGINE_TESSERACT: 0.5,
    ENGINE_EASYOCR:   1.5,
    ENGINE_TROCR:     3.5,
    ENGINE_PADDLE:    4.0,
}

# ── بروفايلات المحركات (اقتراح QWEN: Progressive Enhancement) ────────
PROFILE_ENGINES = {
    "low":      [ENGINE_TESSERACT],
    "balanced": [ENGINE_EASYOCR, ENGINE_TESSERACT, ENGINE_TROCR],
    "high":     [ENGINE_EASYOCR, ENGINE_TESSERACT, ENGINE_TROCR, ENGINE_PADDLE],
}


class EngineRouter:
    """
    الموجّه الذكي لمحركات OCR.

    يختار المحركين الأمثلَين بناءً على سياق الصورة
    دون تشغيل كل المحركات — يوفر ~60% من الذاكرة.

    مثال:
        router = EngineRouter(profile="balanced", use_gpu=True)
        engines, reasons = router.select(
            image_quality=0.85,
            language="ar",
            block_type="paragraph"
        )
        # engines = ["EasyOCR", "Tesseract"]
        # reasons = ["Arabic language detected", "high quality fallback"]
    """

    def __init__(
        self,
        profile: str = "balanced",
        use_gpu: bool = False,
        max_engines: int = 2,
        available_ram_gb: float = 8.0,
    ) -> None:
        """
        تهيئة الموجّه.

        Args:
            profile:          بروفايل الجهاز — "low" | "balanced" | "high"
            use_gpu:          هل GPU متاح
            max_engines:      أقصى عدد محركات تُشغَّل معاً (الافتراضي 2)
            available_ram_gb: الذاكرة المتاحة بالجيجابايت
        """
        self.profile          = profile
        self.use_gpu          = use_gpu
        self.max_engines      = max_engines
        self.available_ram_gb = available_ram_gb
        self._allowed         = PROFILE_ENGINES.get(profile, PROFILE_ENGINES["balanced"])
        logger.info("EngineRouter init: profile=%s, gpu=%s, max=%d", profile, use_gpu, max_engines)

    # ── الواجهة الرئيسية ────────────────────────────────────────────

    def select(
        self,
        image_quality: float = 0.80,
        language: str = "ar",
        block_type: str = "paragraph",
    ) -> tuple[list[str], list[str]]:
        """
        اختيار المحركات الأمثل بناءً على السياق.

        Args:
            image_quality: جودة الصورة 0.0–1.0 (مستمدة من ImagePreprocessor)
            language:      "ar" | "en" | "de" | "mixed"
            block_type:    "paragraph" | "table" | "handwriting" | "header" | "footer"

        Returns:
            (engines, reasons) حيث engines قائمة أسماء المحركات المختارة
        """
        recommendations: list[str] = []
        reasons:          list[str] = []

        # ── بروفايل منخفض: محرك واحد فقط ──────────────────────────
        if self.profile == "low":
            return [ENGINE_TESSERACT], ["low-end profile — single engine mode"]

        # ── خط يدوي → TrOCR الأول ──────────────────────────────────
        if block_type == "handwriting" and ENGINE_TROCR in self._allowed:
            if image_quality >= 0.65:
                recommendations.append(ENGINE_TROCR)
                reasons.append("handwriting block detected")

        # ── عربي أو مختلط → EasyOCR ────────────────────────────────
        if language in ("ar", "mixed") and ENGINE_EASYOCR in self._allowed:
            if ENGINE_EASYOCR not in recommendations:
                recommendations.append(ENGINE_EASYOCR)
                reasons.append(f"Arabic/mixed language ({language})")

        # ── جودة منخفضة → Tesseract (أكثر تسامحاً مع الضجيج) ──────
        if image_quality < 0.60 and ENGINE_TESSERACT in self._allowed:
            if ENGINE_TESSERACT not in recommendations:
                recommendations.append(ENGINE_TESSERACT)
                reasons.append("low image quality — noise-tolerant engine")

        # ── إنجليزي/ألماني جودة عالية → TrOCR ──────────────────────
        if language in ("en", "de") and image_quality >= 0.75:
            if ENGINE_TROCR in self._allowed and ENGINE_TROCR not in recommendations:
                recommendations.append(ENGINE_TROCR)
                reasons.append(f"Latin script + high quality ({language})")
            elif ENGINE_EASYOCR in self._allowed and ENGINE_EASYOCR not in recommendations:
                recommendations.append(ENGINE_EASYOCR)
                reasons.append(f"Latin script — EasyOCR fallback ({language})")

        # ── جداول → Tesseract (أفضل للبنية الشبكية) ─────────────────
        if block_type == "table" and ENGINE_TESSERACT in self._allowed:
            if ENGINE_TESSERACT not in recommendations:
                recommendations.append(ENGINE_TESSERACT)
                reasons.append("table block — structure-aware engine")

        # ── بروفايل high + عربي → PaddleOCR كبديل ─────────────────
        if (self.profile == "high"
                and language in ("ar", "mixed")
                and ENGINE_PADDLE in self._allowed
                and len(recommendations) < self.max_engines):
            if ENGINE_PADDLE not in recommendations:
                recommendations.append(ENGINE_PADDLE)
                reasons.append("high profile — PaddleOCR for Arabic")

        # ── fallback إذا لم يُختَر شيء ──────────────────────────────
        if not recommendations:
            fallback = [e for e in [ENGINE_EASYOCR, ENGINE_TESSERACT] if e in self._allowed]
            recommendations = fallback[:self.max_engines]
            reasons = ["default fallback — no specific signal"]

        # ── تحقق من الذاكرة المتاحة ─────────────────────────────────
        recommendations, reasons = self._filter_by_ram(recommendations, reasons)

        # ── إزالة التكرار والحد بـ max_engines ──────────────────────
        seen, unique = set(), []
        for e in recommendations:
            if e not in seen:
                seen.add(e)
                unique.append(e)
        final = unique[: self.max_engines]

        logger.debug("EngineRouter.select → %s (reasons: %s)", final, reasons)
        return final, reasons[: len(final)]

    def estimate_time(self, engines: list[str]) -> float:
        """تقدير وقت المعالجة بالثواني بناءً على المحركات المختارة."""
        TIME_EST = {
            ENGINE_TESSERACT: 0.4,
            ENGINE_EASYOCR:   1.5,
            ENGINE_TROCR:     2.5,
            ENGINE_PADDLE:    2.0,
        }
        total = sum(TIME_EST.get(e, 1.0) for e in engines)
        if not self.use_gpu:
            total *= 1.8  # CPU أبطأ بـ 80%
        return round(total, 1)

    def summary(self) -> dict:
        """ملخص إعدادات الموجّه."""
        return {
            "profile":          self.profile,
            "use_gpu":          self.use_gpu,
            "max_engines":      self.max_engines,
            "available_ram_gb": self.available_ram_gb,
            "allowed_engines":  self._allowed,
        }

    # ── مساعدات داخلية ──────────────────────────────────────────────

    def _filter_by_ram(
        self,
        engines: list[str],
        reasons: list[str],
    ) -> tuple[list[str], list[str]]:
        """إزالة المحركات التي تتجاوز الذاكرة المتاحة."""
        total_ram = 0.0
        filtered_engines, filtered_reasons = [], []
        for engine, reason in zip(engines, reasons):
            req = ENGINE_RAM_REQUIREMENTS.get(engine, 1.0)
            if total_ram + req <= self.available_ram_gb:
                filtered_engines.append(engine)
                filtered_reasons.append(reason)
                total_ram += req
            else:
                logger.warning(
                    "EngineRouter: skipping %s (needs %.1fGB, available %.1fGB)",
                    engine, req, self.available_ram_gb - total_ram,
                )
        return filtered_engines or [ENGINE_TESSERACT], filtered_reasons or ["RAM-constrained fallback"]

    @classmethod
    def from_config(cls, config) -> "EngineRouter":
        """
        إنشاء EngineRouter من OmniFileConfig.

        Args:
            config: OmniFileConfig instance

        Returns:
            EngineRouter مُعَدّ وفق الإعدادات
        """
        try:
            import psutil
            ram_gb = psutil.virtual_memory().available / 1e9
        except ImportError:
            ram_gb = 8.0
        return cls(
            profile=getattr(config, "engine_profile", "balanced"),
            use_gpu=getattr(config, "use_gpu", False),
            max_engines=getattr(config, "router_max_engines", 2),
            available_ram_gb=ram_gb,
        )
