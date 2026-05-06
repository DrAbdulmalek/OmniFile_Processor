"""
HandwrittenOCR - محرك التعرف على النصوص v4.0
=================================================
المحسنات الرئيسية:
- Batch TrOCR inference (3-6x تسريع)
- Beam search (num_beams) لدقة أعلى
- Smart Ensemble: تخطي TrOCR إذا ثقة EasyOCR > easy_conf_threshold
- LoRA auto-loading
- دعم cache_dir + HF_TOKEN
"""

import os
import cv2
import io
import numpy as np
import torch
import logging
from typing import Tuple, Optional, List
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import easyocr

logger = logging.getLogger("HandwrittenOCR")


def normalize_text(x) -> str:
    """تنظيف النص من NaN وNone"""
    import pandas as pd
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return str(x).strip()


def detect_lang(text: str) -> str:
    """كشف اللغة"""
    try:
        from langdetect import detect
        return detect(str(text)) if text and text.strip() else "unknown"
    except Exception:
        return "unknown"


class OCREngine:
    """
    محرك التعرف يدعم:
    - recognize_word_ensemble: TrOCR + EasyOCR مع اختيار الأفضل
    - batch_predict: استدلال دفعي لـ TrOCR
    - auto-load LoRA adapter
    """

    def __init__(
        self,
        trocr_model_name: str = "David-Magdy/TR_OCR_LARGE",
        ocr_languages: Optional[list] = None,
        max_text_length: int = 64,
        device: Optional[str] = None,
        cache_dir: str = "",
        hf_token: str = "",
        trocr_default_confidence: float = 0.70,
        easy_conf_threshold: float = 0.80,
        num_beams: int = 5,
        trocr_batch_size: int = 16,
        lora_save_path: str = "",
        skip_trocr: bool = False,
    ):
        self.lora_loaded = False
        self.max_text_length = max_text_length
        self.trocr_default_confidence = trocr_default_confidence
        self.easy_conf_threshold = easy_conf_threshold
        self.num_beams = num_beams
        self.trocr_batch_size = trocr_batch_size

        if device is None:
            self.device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
        else:
            self.device = torch.device(device)

        self.skip_trocr = skip_trocr
        self.trocr_processor = None
        self.trocr_model = None

        logger.info(f"جهاز التعرف: {self.device}")

        # تحميل TrOCR (اختياري — يمكن تخطيه لتوفير ~600 MB)
        if not skip_trocr:
            # خيارات تحميل HuggingFace
            hf_kwargs = {}
            if cache_dir:
                hf_kwargs["cache_dir"] = cache_dir
            if hf_token:
                hf_kwargs["token"] = hf_token

            logger.info(f"جاري تحميل TrOCR: {trocr_model_name}")
            try:
                self.trocr_processor = TrOCRProcessor.from_pretrained(
                    trocr_model_name, **hf_kwargs
                )
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained(
                    trocr_model_name, **hf_kwargs
                ).to(self.device)
                logger.info("تم تحميل TrOCR بنجاح")
            except Exception as e:
                logger.error(f"فشل تحميل TrOCR: {e}")
                raise

            # تحميل LoRA المُحسَّن إذا كان موجوداً (تصحيح #9)
            if lora_save_path and os.path.exists(lora_save_path):
                self._load_lora_model(lora_save_path)
        else:
            logger.info("⏭️  تخطي TrOCR — وضع EasyOCR فقط (توفير ~600 MB)")

        # تحميل EasyOCR
        if ocr_languages is None:
            ocr_languages = ["en", "ar"]
        logger.info(f"جاري تحميل EasyOCR بلغات: {ocr_languages}")
        try:
            self.easy_reader = easyocr.Reader(
                ocr_languages, gpu=torch.cuda.is_available()
            )
        except Exception:
            self.easy_reader = easyocr.Reader(ocr_languages, gpu=False)
        logger.info("تم تحميل EasyOCR بنجاح")

    def _load_lora_model(self, lora_save_path: str) -> None:
        """تحميل نموذج LoRA المُحسَّن (تصحيح #9)"""
        try:
            from peft import PeftModel
            self.trocr_model = PeftModel.from_pretrained(
                self.trocr_model, lora_save_path
            ).to(self.device)
            self.lora_loaded = True
            logger.info(f"تم تحميل LoRA weights من: {lora_save_path}")
        except ImportError:
            logger.warning("peft غير مثبت - لن يتم تحميل LoRA")
        except Exception as e:
            logger.warning(f"فشل تحميل LoRA: {e}")

    def batch_predict(self, crops: List[np.ndarray]) -> List[str]:
        """
        Batch inference لـ TrOCR — التحسين الأهم: 3-6x تسريع
        مع beam search لدقة أعلى.
        """
        if self.skip_trocr or not crops:
            return [""] * len(crops) if crops else []
        pil_imgs = []
        for crop in crops:
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            pil_imgs.append(Image.fromarray(rgb))
        try:
            pv = self.trocr_processor(
                images=pil_imgs, return_tensors="pt", padding=True
            ).pixel_values.to(self.device)
            with torch.no_grad():
                ids = self.trocr_model.generate(
                    pv,
                    max_length=self.max_text_length,
                    num_beams=self.num_beams,
                    early_stopping=True,
                    length_penalty=1.0,
                )
            return self.trocr_processor.batch_decode(ids, skip_special_tokens=True)
        except Exception as e:
            logger.warning(f"batch_predict failed: {e}")
            return [""] * len(crops)

    def recognize_word_ensemble(
        self,
        img_bgr: np.ndarray,
        easyocr_raw: Optional[list] = None,
    ) -> Tuple[str, float, str, bool]:
        """
        Ensemble ذكي: يتخطى TrOCR إذا ثقة EasyOCR > easy_conf_threshold.

        Returns:
            tuple: (text, confidence, model_source, is_low_confidence)
        """
        candidates = []

        # EasyOCR أولاً
        if easyocr_raw is not None:
            _, txt, conf = easyocr_raw
            txt = normalize_text(txt)
            if txt:
                candidates.append(("easyocr", txt, float(conf)))
                # تخطي TrOCR لو EasyOCR واثق — توفير 70% من inference
                if float(conf) >= self.easy_conf_threshold:
                    return txt, float(conf), "easyocr", False

        # TrOCR (فقط عند الحاجة وتوفر النموذج)
        if not self.skip_trocr and self.trocr_processor is not None:
            try:
                rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                pv = self.trocr_processor(
                    images=Image.fromarray(rgb), return_tensors="pt"
                ).pixel_values.to(self.device)
                with torch.no_grad():
                    ids = self.trocr_model.generate(
                        pv,
                        max_length=self.max_text_length,
                        num_beams=self.num_beams,
                        early_stopping=True,
                    )
                txt = self.trocr_processor.batch_decode(
                    ids, skip_special_tokens=True
                )[0].strip()
                if txt:
                    candidates.append(("trocr", txt, self.trocr_default_confidence))
            except Exception as e:
                logger.debug(f"TrOCR single: {e}")

        candidates = [c for c in candidates if c[1]]
        if not candidates:
            return "", 0.0, "none", True

        best = max(candidates, key=lambda x: x[2])
        return (
            best[1],
            float(best[2]),
            best[0],
            best[2] < 0.5,
        )

    def recognize_word(self, img_bgr: np.ndarray) -> str:
        """التعرف على كلمة: TrOCR أولاً ثم EasyOCR كبديل."""
        if img_bgr is None or img_bgr.size == 0:
            return ""
        text = self._recognize_trocr(img_bgr)
        if len(text.strip()) > 1:
            return text.strip()
        text = self._recognize_easyocr(img_bgr)
        return text.strip() if text.strip() else ""

    def detect_words_full(self, img_bgr: np.ndarray) -> list:
        """كشف الكلمات مع الإحداثيات باستخدام EasyOCR."""
        try:
            return self.easy_reader.readtext(img_bgr, detail=1)
        except Exception as e:
            logger.debug(f"EasyOCR detection failed: {e}")
            return []

    def _recognize_trocr(self, img_bgr: np.ndarray) -> str:
        if self.skip_trocr or self.trocr_processor is None:
            return ""
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            pv = self.trocr_processor(
                images=pil_img, return_tensors="pt"
            ).pixel_values.to(self.device)
            with torch.no_grad():
                ids = self.trocr_model.generate(
                    pv,
                    max_length=self.max_text_length,
                    num_beams=self.num_beams,
                    early_stopping=True,
                    length_penalty=1.0,
                )
            text = self.trocr_processor.batch_decode(
                ids, skip_special_tokens=True
            )[0]
            return text.strip()
        except Exception as e:
            logger.debug(f"TrOCR failed: {e}")
            return ""

    def _recognize_easyocr(self, img_bgr: np.ndarray) -> str:
        """EasyOCR: يختار النص بأعلى ثقة (تصحيح #4)"""
        try:
            results = self.easy_reader.readtext(img_bgr)
            if results:
                best = max(results, key=lambda r: r[2])  # تصحيح #4
                return best[1]
            return ""
        except Exception as e:
            logger.debug(f"EasyOCR failed: {e}")
            return ""
