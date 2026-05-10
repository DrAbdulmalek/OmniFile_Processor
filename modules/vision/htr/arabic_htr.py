"""
التعرف على النصوص العربية اليدوية — المسار الرئيسي للأنبوب (Pipeline).

يوفر فئة ArabicHandwrittenHTR التي تنسّق بين:
  - تجزئة الأسطر (LineSegmenter)
  - تجزئة الكلمات (WordSegmenter)
  - الاسترداد النقطي (DottedRecovery)
  - نموذج TrOCR المُضبَط (FineTunedTrOCR)

المدخلات: مسار ملف صورة، كائن PIL.Image، أو مصفوفة NumPy.
المخرجات: كائن HTRResult يحتوي النصّ الكامل، الأسطر، الكلمات، ومستوى الثقة.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

# ---------- أنواع المدخلات ----------
ImageInput = Union[str, Path, "np.ndarray", "PIL.Image.Image"]


def _load_image(img: ImageInput) -> "PIL.Image.Image":
    """تحميل الصورة من مسار ملف أو مصفوفة NumPy أو كائن PIL.

    Args:
        img: مسار ملف (str/Path)، مصفوفة NumPy (H,W) أو (H,W,C)، أو كائن PIL.Image.

    Returns:
        كائن PIL.Image بصيغة RGB.
    """
    import PIL.Image

    if isinstance(img, (str, Path)):
        img = PIL.Image.open(img)
    if isinstance(img, np.ndarray):
        if img.ndim == 2:
            img = PIL.Image.fromarray(img).convert("RGB")
        else:
            img = PIL.Image.fromarray(img).convert("RGB")
    if not isinstance(img, PIL.Image.Image):
        raise TypeError(
            f"نوع المدخل غير مدعوم: {type(img)}. "
            "يجب أن يكون مسار ملف أو مصفوفة NumPy أو كائن PIL.Image."
        )
    return img.convert("RGB")


# ============================================================
# HTRResult — حاوية النتائج
# ============================================================
@dataclass
class HTRResult:
    """نتيجة التعرف على النصّ اليدوي.

    Attributes:
        text: النصّ الكامل المُتعَرَّف عليه (RTL).
        lines: قائمة النتائج لكل سطر.
        words: قائمة الكلمات المُتعَرَّف عليها مع مواقعها.
        confidence: مستوى الثقة الكلي (0–1).
    """

    text: str = ""
    lines: List["LineResult"] = field(default_factory=list)
    words: List["WordResult"] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class LineResult:
    """نتيجة التعرف على سطر واحد.

    Attributes:
        text: نصّ السطر.
        image: صورة السطر المُقتطَعة (PIL.Image أو None).
        confidence: مستوى الثقة (0–1).
        y_start: بداية السطر (بكسل).
        y_end: نهاية السطر (بكسل).
        words: قائمة نتائج الكلمات ضمن السطر.
    """

    text: str = ""
    image: Optional["PIL.Image.Image"] = None
    confidence: float = 0.0
    y_start: int = 0
    y_end: int = 0
    words: List["WordResult"] = field(default_factory=list)


@dataclass
class WordResult:
    """نتيجة التعرف على كلمة واحدة.

    Attributes:
        text: نصّ الكلمة.
        image: صورة الكلمة المُقتطَعة (PIL.Image أو None).
        confidence: مستوى الثقة (0–1).
        x_start: بداية الكلمة الأفقية (بكسل).
        x_end: نهاية الكلمة الأفقية (بكسل).
        line_index: فهرس السطر الذي تنتمي إليه الكلمة.
    """

    text: str = ""
    image: Optional["PIL.Image.Image"] = None
    confidence: float = 0.0
    x_start: int = 0
    x_end: int = 0
    line_index: int = 0


# ============================================================
# ArabicHandwrittenHTR — الأنبوب الرئيسي
# ============================================================
class ArabicHandwrittenHTR:
    """الأنبوب الرئيسي للتعرف على النصوص العربية اليدوية.

    ينسّق بين: تجزئة الأسطر ← تجزئة الكلمات ← التعرف ← استرداد النقاط.

    Args:
        model_path: مسار نموذج TrOCR المُضبَط (اختياري).
        device: الجهاز المستخدم ('cpu' أو 'cuda').
        line_segmentation: تفعيل تجزئة الأسطر.
        word_segmentation: تفعيل تجزئة الكلمات.
        dotted_recovery: تفعيل استرداد النقاط والحركات.
        line_segmenter_type: نوع مُجزِّئ الأسطر ('projection', 'unet', 'contour').
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        *,
        line_segmentation: bool = True,
        word_segmentation: bool = True,
        dotted_recovery: bool = True,
        line_segmenter_type: str = "projection",
    ) -> None:
        from .line_segmenter import (
            ContourLineSegmenter,
            ProjectionProfileSegmenter,
            UNetLineSegmenter,
        )
        from .word_segmenter import ArabicWordSegmenter

        self._device = device
        self._do_line_seg = line_segmentation
        self._do_word_seg = word_segmentation
        self._do_dot_recovery = dotted_recovery

        # --- مُجزِّئ الأسطر ---
        segmenter_map = {
            "projection": ProjectionProfileSegmenter,
            "unet": UNetLineSegmenter,
            "contour": ContourLineSegmenter,
        }
        seg_cls = segmenter_map.get(line_segmenter_type, ProjectionProfileSegmenter)
        self._line_segmenter = seg_cls()
        logger.info(
            "تمّ تهيئة مُجزِّئ الأسطر: %s", line_segmenter_type
        )

        # --- مُجزِّئ الكلمات ---
        self._word_segmenter = ArabicWordSegmenter()
        logger.info("تمّ تهيئة مُجزِّئ الكلمات.")

        # --- استرداد النقاط ---
        self._dot_recovery = None
        if dotted_recovery:
            from .dotted_recovery import ArabicDottedRecovery

            self._dot_recovery = ArabicDottedRecovery()
            logger.info("تمّ تهيئة وحدة استرداد النقاط.")

        # --- نموذج TrOCR ---
        from .trocr_finetuned import FineTunedTrOCR

        self._trocr = FineTunedTrOCR(
            model_path=model_path,
            device=device,
            use_fine_tuned=model_path is not None,
        )
        logger.info("تمّ تهيئة نموذج TrOCR.")

    # ----------------------------------------------------------
    # recognize — المعالجة الكاملة لصورة واحدة
    # ----------------------------------------------------------
    def recognize(self, image: ImageInput) -> HTRResult:
        """التعرف على النصّ في صورة واحدة.

        خطوات الأنبوب:
            1. تحميل الصورة
            2. تجزئة الأسطر
            3. لكل سطر: تجزئة الكلمات ← تعرّف TrOCR ← استرداد النقاط
            4. تجميع النتائج في HTRResult

        Args:
            image: مسار ملف، مصفوفة NumPy، أو كائن PIL.Image.

        Returns:
            كائن HTRResult يحتوي النصّ والتفاصيل.
        """
        pil_img = _load_image(image)
        logger.info("بدء التعرف على النصّ اليدوي (الحجم: %s)", pil_img.size)

        # --- تجزئة الأسطر ---
        if self._do_line_seg:
            line_data = self._line_segmenter.segment_with_info(pil_img)
        else:
            line_data = [(pil_img, {"y_start": 0, "y_end": pil_img.height})]
        logger.info("تمّ العثور على %d سطر.", len(line_data))

        # --- معالجة كل سطر ---
        line_results: List[LineResult] = []
        all_words: List[WordResult] = []

        for line_idx, (line_img, info) in enumerate(line_data):
            line_result = self._process_line(line_img, line_idx, info)
            line_results.append(line_result)
            all_words.extend(line_result.words)

        # --- تجميع النصّ الكامل (RTL) ---
        full_text = "\n".join(lr.text for lr in line_results)

        # --- مستوى الثقة الكلي ---
        total_conf = (
            sum(lr.confidence for lr in line_results) / len(line_results)
            if line_results
            else 0.0
        )

        # --- استرداد النقاط على النصّ الكامل ---
        if self._do_dot_recovery and self._dot_recovery is not None:
            full_text = self._dot_recovery.recover(full_text)
            logger.info("تمّ استرداد النقاط والحركات للنصّ الكامل.")

        result = HTRResult(
            text=full_text,
            lines=line_results,
            words=all_words,
            confidence=round(total_conf, 4),
        )
        logger.info("انتهى التعرف. الثقة: %.2f%%", total_conf * 100)
        return result

    # ----------------------------------------------------------
    # recognize_batch — معالجة دفعة من الصور
    # ----------------------------------------------------------
    def recognize_batch(
        self, images: List[ImageInput]
    ) -> List[HTRResult]:
        """التعرف على النصّ في مجموعة من الصور.

        Args:
            images: قائمة من المدخلات (مسارات، مصفوفات، PIL.Image).

        Returns:
            قائمة من كائنات HTRResult.
        """
        logger.info("بدء معالجة دفعة من %d صورة.", len(images))
        results: List[HTRResult] = []
        for idx, img in enumerate(images):
            logger.info("معالجة الصورة %d/%d ...", idx + 1, len(images))
            results.append(self.recognize(img))
        return results

    # ----------------------------------------------------------
    # _process_line — معالجة سطر واحد
    # ----------------------------------------------------------
    def _process_line(
        self,
        line_image: "PIL.Image.Image",
        line_index: int,
        info: dict,
    ) -> LineResult:
        """معالجة سطر واحد: تجزئة الكلمات ← تعرّف ← استرداد.

        Args:
            line_image: صورة السطر.
            line_index: فهرس السطر.
            info: قاموس بيانات التجزئة (y_start, y_end, ...).

        Returns:
            كائن LineResult.
        """
        y_start = info.get("y_start", 0)
        y_end = info.get("y_end", line_image.height)

        # --- تجزئة الكلمات ---
        if self._do_word_seg:
            word_images = self._word_segmenter.segment(line_image)
        else:
            word_images = [line_image]

        word_results: List[WordResult] = []
        recognized_texts: List[str] = []

        for w_idx, w_img in enumerate(word_images):
            text, conf = self._trocr.recognize(w_img)
            recognized_texts.append(text)
            word_results.append(
                WordResult(
                    text=text,
                    image=w_img,
                    confidence=conf,
                    x_start=w_idx,
                    x_end=w_idx + 1,
                    line_index=line_index,
                )
            )

        # --- تجميع نصّ السطر (RTL: انضمام من اليمين لليسار) ---
        line_text = " ".join(recognized_texts)

        # --- استرداد النقاط على مستوى السطر ---
        if self._do_dot_recovery and self._dot_recovery is not None:
            line_text = self._dot_recovery.recover(line_text)

        # --- حساب الثقة ---
        avg_conf = (
            sum(wr.confidence for wr in word_results) / len(word_results)
            if word_results
            else 0.0
        )

        return LineResult(
            text=line_text,
            image=line_image,
            confidence=round(avg_conf, 4),
            y_start=y_start,
            y_end=y_end,
            words=word_results,
        )

    # ----------------------------------------------------------
    # fine_tune — اختصار لبدء الضبط الدقيق (LoRA)
    # ----------------------------------------------------------
    def fine_tune(
        self,
        train_dataset,
        output_dir: str = "./htr_finetuned",
        *,
        num_epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 5e-5,
        lora_r: int = 8,
        lora_alpha: int = 16,
    ) -> None:
        """بدء الضبط الدقيق لنموذج TrOCR باستخدام LoRA.

        Args:
            train_dataset: مجموعة التدريب (قائمة من أزواج (صورة, نص)).
            output_dir: مسار حفظ النموذج المُضبَط.
            num_epochs: عدد الحقب.
            batch_size: حجم الدفعة.
            learning_rate: معدّل التعلّم.
            lora_r: بُعد LoRA.
            lora_alpha: مُعامِل alpha لـ LoRA.
        """
        logger.info(
            "بدء الضبط الدقيق — الحقب: %d، الدفعة: %d، lr: %.1e",
            num_epochs,
            batch_size,
            learning_rate,
        )

        try:
            from peft import LoraConfig, get_peft_model

            model = self._trocr.model

            lora_config = LoraConfig(
                r=lora_r,
                lora_alpha=lora_alpha,
                lora_dropout=0.05,
                bias="none",
                target_modules=["query", "value"],
            )
            model = get_peft_model(model, lora_config)
            model.print_trainable_parameters()
        except ImportError:
            logger.warning(
                "مكتبة PEFT غير متوفرة. سُيستخدم الضبط الدقيق الكامل بدلاً من LoRA."
            )

        try:
            from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

            training_args = Seq2SeqTrainingArguments(
                output_dir=output_dir,
                num_train_epochs=num_epochs,
                per_device_train_batch_size=batch_size,
                learning_rate=learning_rate,
                predict_with_generate=True,
                evaluation_strategy="no",
                save_strategy="epoch",
                logging_steps=50,
                remove_unused_columns=False,
                fp16=self._device == "cuda",
                report_to="none",
            )

            # تجهيز المعالج والنموذج
            processor = self._trocr.processor

            def _collate_fn(batch):
                images = [item[0] for item in batch]
                texts = [item[1] for item in batch]
                pixel_values = processor(images=images, return_tensors="pt").pixel_values
                labels = processor(
                    text=texts, return_tensors="pt", padding=True
                ).input_ids
                labels[labels == processor.tokenizer.pad_token_id] = -100
                return {"pixel_values": pixel_values, "labels": labels}

            trainer = Seq2SeqTrainer(
                model=model,
                args=training_args,
                train_dataset=train_dataset,
                data_collator=_collate_fn,
            )
            trainer.train()
            trainer.save_model(output_dir)
            logger.info("تمّ حفظ النموذج المُضبَط في: %s", output_dir)

        except ImportError:
            logger.error(
                "مكتبة transformers غير متوفرة أو لا تحتوي Seq2SeqTrainer. "
                "تعذّر إتمام الضبط الدقيق."
            )
