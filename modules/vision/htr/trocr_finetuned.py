"""
غلاف نموذج TrOCR المُضبَط (Fine-Tuned TrOCR Wrapper).

يوفر فئة FineTunedTrOCR للتعرف على النصّ اليدوي باستخدام نموذج
VisionEncoderDecoderModel من مكتبة transformers مع إعدادات
تحسين جاهزة لنصّ عربي يدوي.

يدعم:
  - تحميل نموذج مُضبَط أو النموذج الأساسي مسبق التدريب.
  - التعرف على صورة واحدة أو دفعة من الصور.
  - ضبط إعدادات التوليد (beam search, max_length, ...).
  - تصحيح يستند إلى السياق (placeholder لدمج نموذج لغوي).
"""

import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================
# FineTunedTrOCR
# ============================================================
class FineTunedTrOCR:
    """غلاف لنموذج TrOCR المُضبَط للتعرف على النصّ العربي اليدوي.

    يُغَلِّف TrOCRProcessor و VisionEncoderDecoderModel مع إعدادات
    توليد محسّنة (beam search، طول أقصى، منع التكرار).

    Args:
        model_path: مسار النموذج المُضبَط (اختياري).
            إذا لم يُحدَّد، يُحمَّل النموذج الأساسي
            ``microsoft/trocr-base-handwritten``.
        device: الجهاز المستخدم ('cpu' أو 'cuda').
        use_fine_tuned: استخدام النموذج المُضبَط إذا كان متوفّرًا.
    """

    # النموذج الأساسي الافتراضي
    _DEFAULT_MODEL = "microsoft/trocr-base-handwritten"

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        use_fine_tuned: bool = False,
    ) -> None:
        self._device = device
        self._model_path = model_path
        self._use_fine_tuned = use_fine_tuned and model_path is not None
        self._processor = None
        self._model = None
        self._generation_config = None

        self._load_model()

    # ----------------------------------------------------------
    # _load_model — تحميل النموذج والمعالج
    # ----------------------------------------------------------
    def _load_model(self) -> None:
        """تحميل نموذج VisionEncoderDecoderModel ومعالج TrOCRProcessor."""
        try:
            from transformers import (
                GenerationConfig,
                TrOCRProcessor,
                VisionEncoderDecoderModel,
            )
        except ImportError:
            logger.error(
                "مكتبة transformers غير متوفرة. "
                "ثبّتها بـ: pip install transformers torch"
            )
            raise

        # تحديد مسار النموذج
        model_name = self._model_path if self._use_fine_tuned else self._DEFAULT_MODEL
        logger.info("جاري تحميل النموذج: %s ...", model_name)

        # تحميل المعالج
        if self._use_fine_tuned and self._model_path:
            self._processor = TrOCRProcessor.from_pretrained(self._model_path)
            self._model = VisionEncoderDecoderModel.from_pretrained(self._model_path)
        else:
            self._processor = TrOCRProcessor.from_pretrained(self._DEFAULT_MODEL)
            self._model = VisionEncoderDecoderModel.from_pretrained(self._DEFAULT_MODEL)

        # نقل النموذج إلى الجهاز
        self._model.to(self._device)
        self._model.eval()

        # إعداد GenerationConfig
        self._generation_config = GenerationConfig(
            max_length=128,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=3,
            length_penalty=1.0,
            bad_words_ids=None,
            bos_token_id=self._model.config.decoder.bos_token_id,
            eos_token_id=self._model.config.decoder.eos_token_id,
            pad_token_id=self._model.config.decoder.pad_token_id,
        )

        logger.info(
            "تمّ تحميل النموذج بنجاح على: %s (مُضبَط: %s)",
            self._device,
            self._use_fine_tuned,
        )

    # ----------------------------------------------------------
    # recognize — التعرف على صورة واحدة
    # ----------------------------------------------------------
    def recognize(
        self,
        image,
        context: Optional[str] = None,
    ) -> Tuple[str, float]:
        """التعرف على النصّ في صورة واحدة.

        Args:
            image: صورة الكلمة/السطر (PIL.Image، مسار ملف، أو numpy.ndarray).
            context: نصّ السياق للتصحيح (اختياري).

        Returns:
            زوج (النصّ المُتعَرَّف عليه، مستوى_الثقة).
        """
        import PIL.Image

        # تحميل الصورة
        pil_img = self._ensure_pil_image(image)

        try:
            import torch

            # تجهيز المدخلات
            pixel_values = self._processor(
                pil_img, return_tensors="pt"
            ).pixel_values.to(self._device)

            # التوليد
            with torch.no_grad():
                output = self._model.generate(
                    pixel_values,
                    generation_config=self._generation_config,
                )

            # فكّ التشفير
            generated_text = self._processor.batch_decode(
                output, skip_special_tokens=True
            )[0].strip()

            # حساب مستوى الثقة (تقريبي من احتمالات beam search)
            confidence = self._estimate_confidence(output)

            # تصحيح بالسياق
            if context:
                generated_text = self._apply_context(generated_text, context)

            logger.debug(
                "TrOCR — النصّ: '%s'، الثقة: %.2f%%",
                generated_text,
                confidence * 100,
            )
            return generated_text, confidence

        except Exception as exc:
            logger.error("خطأ في التعرف بـ TrOCR: %s", exc)
            return "", 0.0

    # ----------------------------------------------------------
    # recognize_batch — التعرف على دفعة من الصور
    # ----------------------------------------------------------
    def recognize_batch(
        self,
        images: list,
        batch_size: int = 4,
        contexts: Optional[List[Optional[str]]] = None,
    ) -> List[Tuple[str, float]]:
        """التعرف على النصّ في مجموعة من الصور.

        Args:
            images: قائمة صور (PIL.Image أو مسارات أو مصفوفات).
            batch_size: حجم الدفعة.
            contexts: قائمة نصوص السياق (اختياري، بنفس طول images).

        Returns:
            قائمة من الأزواج (نصّ، ثقة).
        """
        if contexts is None:
            contexts = [None] * len(images)

        results: List[Tuple[str, float]] = []

        try:
            import torch
        except ImportError:
            logger.error("مكتبة torch غير متوفرة.")
            return [("", 0.0)] * len(images)

        # معالجة على دفعات
        for i in range(0, len(images), batch_size):
            batch_imgs = images[i: i + batch_size]
            batch_ctx = contexts[i: i + batch_size]

            # تحويل إلى PIL
            pil_images = [self._ensure_pil_image(img) for img in batch_imgs]

            # تجهيز المدخلات
            try:
                pixel_values = self._processor(
                    pil_images, return_tensors="pt", padding=True
                ).pixel_values.to(self._device)

                with torch.no_grad():
                    outputs = self._model.generate(
                        pixel_values,
                        generation_config=self._generation_config,
                    )

                # فكّ التشفير
                texts = self._processor.batch_decode(
                    outputs, skip_special_tokens=True
                )

                for j, text in enumerate(texts):
                    text = text.strip()
                    confidence = self._estimate_confidence(outputs[j: j + 1])

                    # تصحيح بالسياق
                    ctx = batch_ctx[j] if j < len(batch_ctx) else None
                    if ctx:
                        text = self._apply_context(text, ctx)

                    results.append((text, confidence))

            except Exception as exc:
                logger.error("خطأ في معالجة الدفعة: %s", exc)
                for _ in batch_imgs:
                    results.append(("", 0.0))

        logger.info(
            "تمّ التعرف على %d صورة (حجم الدفعة: %d).",
            len(results),
            batch_size,
        )
        return results

    # ----------------------------------------------------------
    # _apply_context — تصحيح بالسياق (placeholder)
    # ----------------------------------------------------------
    def _apply_context(self, text: str, context: str) -> str:
        """تصحيح النصّ المُتعَرَّف عليه باستخدام السياق.

        حالياً نائب (placeholder) — يُمكن تفعيله بدمج نموذج لغوي
        مثل GPT-2 عربي أو AraBERT.

        الاستراتيجيات المحتملة:
          1. مطابقة الكلمات مع قاموس السياق.
          2. تصحيح إملائي يستند إلى n-grams.
          3. إعادة ترتيب beam search حسب السياق.

        Args:
            text: النصّ المُتعَرَّف عليه.
            context: نصّ السياق.

        Returns:
            النصّ بعد التصحيح.
        """
        # تنفيذ بسيط: إذا كانت كلمة من الكلمات المعروفة في السياق
        # تظهر في النتيجة مع اختلاف طفيف، نستبدلها.
        context_words = set(context.split())
        result_words = text.split()

        corrected = []
        for word in result_words:
            # البحث عن تطابق شبه مطابق في السياق
            best_match = None
            best_score = 0.8  # عتبة أدنى

            for ctx_word in context_words:
                if len(ctx_word) < 2:
                    continue
                # مقارنة بسيطة: نسبة الحروف المشتركة
                common = sum(
                    1 for c in word if c in ctx_word
                )
                score = common / max(len(word), len(ctx_word), 1)

                if score > best_score:
                    best_score = score
                    best_match = ctx_word

            if best_match:
                corrected.append(best_match)
            else:
                corrected.append(word)

        result = " ".join(corrected)
        return result

    # ----------------------------------------------------------
    # update_generation_config — تحديث إعدادات التوليد
    # ----------------------------------------------------------
    def update_generation_config(
        self,
        max_length: Optional[int] = None,
        num_beams: Optional[int] = None,
        early_stopping: Optional[bool] = None,
        no_repeat_ngram_size: Optional[int] = None,
        length_penalty: Optional[float] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> None:
        """تحديث إعدادات التوليد للنموذج.

        Args:
            max_length: الطول الأقصى للتوليد.
            num_beams: عدد أشعة beam search.
            early_stopping: إيقاف مبكر.
            no_repeat_ngram_size: منع تكرار n-grams.
            length_penalty: عقوبة الطول.
            temperature: درجة حرارة أخذ العينات.
            top_k: أخذ العينات top-k.
            top_p: أخذ العينات top-p (nucleus).
        """
        if self._generation_config is None:
            logger.warning("GenerationConfig غير مهيأ.")
            return

        updates = {
            "max_length": max_length,
            "num_beams": num_beams,
            "early_stopping": early_stopping,
            "no_repeat_ngram_size": no_repeat_ngram_size,
            "length_penalty": length_penalty,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
        }

        changed = []
        for param, value in updates.items():
            if value is not None:
                old_val = getattr(self._generation_config, param, None)
                setattr(self._generation_config, param, value)
                changed.append(f"{param}: {old_val} → {value}")

        if changed:
            logger.info("تمّ تحديث إعدادات التوليد:\n  %s", "\n  ".join(changed))

    # ----------------------------------------------------------
    # _ensure_pil_image — تحويل المدخل إلى PIL.Image
    # ----------------------------------------------------------
    def _ensure_pil_image(self, image) -> "PIL.Image.Image":
        """تحويل المدخل إلى كائن PIL.Image بصيغة RGB.

        Args:
            image: مسار ملف (str)، مصفوفة NumPy، أو كائن PIL.Image.

        Returns:
            كائن PIL.Image بصيغة RGB.
        """
        import PIL.Image
        from pathlib import Path

        if isinstance(image, (str, Path)):
            image = PIL.Image.open(image)
        elif isinstance(image, np.ndarray):
            if image.ndim == 2:
                image = PIL.Image.fromarray(image)
            else:
                image = PIL.Image.fromarray(image)
        elif not isinstance(image, PIL.Image.Image):
            raise TypeError(
                f"نوع المدخل غير مدعوم: {type(image)}. "
                "يجب أن يكون مسار ملف أو مصفوفة NumPy أو كائن PIL.Image."
            )
        return image.convert("RGB")

    # ----------------------------------------------------------
    # _estimate_confidence — تقدير مستوى الثقة
    # ----------------------------------------------------------
    def _estimate_confidence(self, output) -> float:
        """تقدير مستوى ثقة النتيجة.

        يستخدم طول التسلسل المُولَّد ومعلومات beam search
        لحساب تقدير للثقة. هذه طريقة تقريبية لأن TrOCR لا يُرجع
        احتمالات مباشرة لكل توكن.

        الاستراتيجية:
          1. إذا كان التوليد قصيرًا جدًا أو طويلاً جدًا، الثقة منخفضة.
          2. طول معتدل + توافق مع beam search → ثقة أعلى.

        Args:
            output: ناتج model.generate().

        Returns:
            مستوى الثقة التقريبي (0–1).
        """
        try:
            import torch

            if isinstance(output, torch.Tensor):
                seq_len = output.shape[1]
            else:
                seq_len = len(output[0]) if output else 0

            # نموذج خطي بسيط: الطول المثالي ≈ 10–30 توكن
            if seq_len == 0:
                return 0.0

            if seq_len <= 1:
                return 0.3

            # انحراف عن الطول المثالي
            ideal_len = 15.0
            deviation = abs(seq_len - ideal_len) / ideal_len
            base_confidence = max(0.3, 1.0 - deviation * 0.5)

            # عامل beam search: المزيد من الأشعة → ثقة أعلى
            num_beams = self._generation_config.num_beams if self._generation_config else 4
            beam_factor = min(num_beams / 8.0, 1.0) * 0.2

            confidence = min(1.0, base_confidence + beam_factor)
            return round(confidence, 4)

        except Exception:
            return 0.5  # افتراضي في حال عدم التمكن من الحساب

    # ----------------------------------------------------------
    # خصائص (Properties)
    # ----------------------------------------------------------
    @property
    def processor(self):
        """معالج TrOCRProcessor."""
        return self._processor

    @property
    def model(self):
        """نموذج VisionEncoderDecoderModel."""
        return self._model

    @property
    def device(self) -> str:
        """الجهاز المستخدم."""
        return self._device

    @property
    def generation_config(self):
        """إعدادات التوليد الحالية."""
        return self._generation_config

    def __repr__(self) -> str:
        return (
            f"FineTunedTrOCR("
            f"model={self._model_path or self._DEFAULT_MODEL}, "
            f"device={self._device}, "
            f"fine_tuned={self._use_fine_tuned})"
        )
