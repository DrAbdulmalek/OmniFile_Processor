"""
HandwrittenOCR - محرك التعرف على النصوص v4.1
=================================================
المحسنات الرئيسية:
- Batch TrOCR inference (3-6x تسريع)
- Beam search (num_beams) لدقة أعلى
- Smart Ensemble: تخطي TrOCR إذا ثقة EasyOCR > easy_conf_threshold
- LoRA auto-loading
- دعم cache_dir + HF_TOKEN
- تسجيل مفصّل لكل عملية تعرف مع الوقت والنتائج
"""

import os
import cv2
import io
import time
import traceback
import numpy as np
import torch
import logging
from typing import Tuple, Optional, List
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import easyocr

logger = logging.getLogger("HandwrittenOCR")

# استيراد أدوات اللوق المفصّل
try:
    from src.logger import log_step, log_error_full, log_result
except ImportError:
    def log_step(lg, name, data=None):
        lg.info(f"STEP [{name}]")
        if data:
            for k, v in data.items():
                lg.info(f"      {k}: {v}")
    def log_error_full(lg, ctx, err, extra=None):
        lg.error(f"ERROR [{ctx}] {type(err).__name__}: {err}", exc_info=True)
    def log_result(lg, name, result):
        lg.info(f"RESULT [{name}] {result}")


def normalize_text(x) -> str:
    """تنظيف النص من NaN وNone مع تسجيل القيم المشبوهة."""
    import pandas as pd
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    result = str(x).strip()
    return result


def detect_lang(text: str) -> str:
    """كشف اللغة مع تسجيل النتائج."""
    try:
        from langdetect import detect
        lang = detect(str(text)) if text and text.strip() else "unknown"
        logger.debug(f"كشف اللغة: '{text[:50]}...' => '{lang}'")
        return lang
    except Exception as e:
        logger.debug(f"فشل كشف اللغة: {e}")
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
        logger.info("=" * 55)
        logger.info("تهيئة محرك التعرف OCREngine")
        logger.info("=" * 55)

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

        log_step(logger, "إعدادات محرك التعرف", {
            "device": str(self.device),
            "CUDA_available": str(torch.cuda.is_available()),
            "trocr_model": trocr_model_name,
            "languages": str(ocr_languages or ["en", "ar", "de"]),
            "skip_trocr": str(skip_trocr),
            "num_beams": str(num_beams),
            "batch_size": str(trocr_batch_size),
            "max_text_length": str(max_text_length),
            "easy_conf_threshold": str(easy_conf_threshold),
            "trocr_default_confidence": str(trocr_default_confidence),
            "cache_dir": cache_dir or "(default)",
            "hf_token_set": str(bool(hf_token)),
            "lora_save_path": lora_save_path or "(none)",
        })

        # تحميل TrOCR (اختياري — يمكن تخطيه لتوفير ~600 MB)
        if not skip_trocr:
            hf_kwargs = {}
            if cache_dir:
                hf_kwargs["cache_dir"] = cache_dir
            if hf_token:
                hf_kwargs["token"] = hf_token

            logger.info(f"جاري تحميل TrOCR: {trocr_model_name}")
            logger.debug(f"  HF kwargs: {list(hf_kwargs.keys())}")
            start = time.time()
            try:
                self.trocr_processor = TrOCRProcessor.from_pretrained(
                    trocr_model_name, **hf_kwargs
                )
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained(
                    trocr_model_name, **hf_kwargs
                ).to(self.device)
                elapsed = time.time() - start
                logger.info(f"تم تحميل TrOCR بنجاح في {elapsed:.2f}s")
                log_result(logger, "تحميل TrOCR", {
                    "model": trocr_model_name,
                    "device": str(self.device),
                    "time_sec": round(elapsed, 2),
                    "params_M": f"{sum(p.numel() for p in self.trocr_model.parameters()) / 1e6:.1f}",
                })
            except Exception as e:
                log_error_full(logger, "تحميل TrOCR", e, extra={
                    "model": trocr_model_name,
                    "kwargs_keys": list(hf_kwargs.keys()),
                })
                raise

            # تحميل LoRA المُحسَّن إذا كان موجوداً
            if lora_save_path and os.path.exists(lora_save_path):
                self._load_lora_model(lora_save_path)
            elif lora_save_path:
                logger.info(f"مسار LoRA غير موجود: {lora_save_path} — يتجاوز")
        else:
            logger.info("تخطي TrOCR — وضع EasyOCR فقط (توفير ~600 MB)")

        # تحميل EasyOCR
        if ocr_languages is None:
            ocr_languages = ["en", "ar", "de"]
        logger.info(f"جاري تحميل EasyOCR بلغات: {ocr_languages}")
        start = time.time()
        try:
            self.easy_reader = easyocr.Reader(
                ocr_languages, gpu=torch.cuda.is_available()
            )
            elapsed = time.time() - start
            logger.info(f"تم تحميل EasyOCR بنجاح في {elapsed:.2f}s (GPU={torch.cuda.is_available()})")
        except Exception as e:
            logger.warning(f"فشل تحميل EasyOCR بـ GPU — الانتقال لوضع CPU: {e}")
            start = time.time()
            self.easy_reader = easyocr.Reader(ocr_languages, gpu=False)
            elapsed = time.time() - start
            logger.info(f"تم تحميل EasyOCR بـ CPU في {elapsed:.2f}s")

    def _load_lora_model(self, lora_save_path: str) -> None:
        """تحميل نموذج LoRA المُحسَّن مع تسجيل مفصّل."""
        log_step(logger, "تحميل LoRA", {"path": lora_save_path})
        try:
            from peft import PeftModel
            start = time.time()
            self.trocr_model = PeftModel.from_pretrained(
                self.trocr_model, lora_save_path
            ).to(self.device)
            self.lora_loaded = True
            elapsed = time.time() - start
            logger.info(f"تم تحميل LoRA weights من: {lora_save_path} في {elapsed:.2f}s")
        except ImportError as e:
            logger.warning(f"peft غير مثبت - لن يتم تحميل LoRA: {e}")
            logger.debug(traceback.format_exc())
        except Exception as e:
            log_error_full(logger, "تحميل LoRA", e, extra={"path": lora_save_path})

    def batch_predict(self, crops: List[np.ndarray]) -> List[str]:
        """
        Batch inference لـ TrOCR — التحسين الأهم: 3-6x تسريع
        مع beam search لدقة أعلى.
        """
        if self.skip_trocr or not crops:
            logger.debug(f"batch_predict: تخطي (skip_trocr={self.skip_trocr}, crops={len(crops) if crops else 0})")
            return [""] * len(crops) if crops else []

        log_step(logger, "TrOCR batch_predict", {
            "num_crops": len(crops),
            "batch_size": self.trocr_batch_size,
            "num_beams": self.num_beams,
            "max_length": self.max_text_length,
        })

        pil_imgs = []
        for i, crop in enumerate(crops):
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            pil_imgs.append(Image.fromarray(rgb))
            logger.debug(f"  crop[{i}]: أبعاد={crop.shape[:2]}, نوع={crop.dtype}")

        start = time.time()
        try:
            pv = self.trocr_processor(
                images=pil_imgs, return_tensors="pt", padding=True
            ).pixel_values.to(self.device)

            logger.debug(f"  tensor shape: {pv.shape}, dtype: {pv.dtype}, device: {pv.device}")

            with torch.no_grad():
                ids = self.trocr_model.generate(
                    pv,
                    max_length=self.max_text_length,
                    num_beams=self.num_beams,
                    early_stopping=True,
                    length_penalty=1.0,
                )

            results = self.trocr_processor.batch_decode(ids, skip_special_tokens=True)
            elapsed = time.time() - start

            logger.debug(f"  batch_predict اكتمل في {elapsed:.2f}s")
            for i, txt in enumerate(results):
                logger.debug(f"  crop[{i}] => '{txt}'")

            return results

        except RuntimeError as e:
            if 'out of memory' in str(e).lower():
                logger.warning(f"batch_predict: OOM — تقليل batch size تلقائياً (كان {len(crops)} crop)")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                # Fallback: واحد واحد
                results = []
                for i, single_crop in enumerate(crops):
                    try:
                        rgb = cv2.cvtColor(single_crop, cv2.COLOR_BGR2RGB)
                        pv = self.trocr_processor(
                            images=[Image.fromarray(rgb)], return_tensors="pt", padding=True
                        ).pixel_values.to(self.device)
                        with torch.no_grad():
                            ids = self.trocr_model.generate(
                                pv, max_length=self.max_text_length, num_beams=self.num_beams,
                                early_stopping=True, length_penalty=1.0,
                            )
                        txt = self.trocr_processor.batch_decode(ids, skip_special_tokens=True)[0]
                        results.append(txt)
                    except Exception as e2:
                        logger.debug(f"  OOM fallback crop[{i}] فشل: {e2}")
                        results.append("")
                return results
            logger.warning(f"batch_predict failed: {e}")
            return [""] * len(crops)
        except Exception as e:
            log_error_full(logger, "TrOCR batch_predict", e, extra={
                "num_crops": len(crops),
                "device": str(self.device),
            })
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
            conf_val = float(conf)
            if txt:
                candidates.append(("easyocr", txt, conf_val))
                logger.debug(f"  EasyOCR: '{txt}' (ثقة={conf_val:.3f})")
                # تخطي TrOCR لو EasyOCR واثق
                if conf_val >= self.easy_conf_threshold:
                    logger.debug(f"  => اختيار EasyOCR مباشرة (ثقة >= {self.easy_conf_threshold})")
                    return txt, conf_val, "easyocr", False

        # TrOCR (فقط عند الحاجة وتوفر النموذج)
        if not self.skip_trocr and self.trocr_processor is not None:
            try:
                start = time.time()
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
                elapsed = time.time() - start
                if txt:
                    candidates.append(("trocr", txt, self.trocr_default_confidence))
                    logger.debug(f"  TrOCR: '{txt}' (ثقة={self.trocr_default_confidence:.3f}, وقت={elapsed:.3f}s)")
            except Exception as e:
                logger.debug(f"  TrOCR single فشل: {type(e).__name__}: {e}")

        candidates = [c for c in candidates if c[1]]
        if not candidates:
            logger.debug("  => لا نتائج من أي محرك")
            return "", 0.0, "none", True

        best = max(candidates, key=lambda x: x[2])
        logger.debug(f"  => الاختيار النهائي: '{best[1]}' من {best[0]} (ثقة={best[2]:.3f})")
        return (
            best[1],
            float(best[2]),
            best[0],
            best[2] < 0.5,
        )

    def recognize_word(self, img_bgr: np.ndarray) -> str:
        """التعرف على كلمة: TrOCR أولاً ثم EasyOCR كبديل مع تسجيل مفصّل."""
        if img_bgr is None or img_bgr.size == 0:
            logger.debug("recognize_word: صورة فارغة")
            return ""

        logger.debug(f"recognize_word: أبعاد={img_bgr.shape[:2]}, dtype={img_bgr.dtype}")

        text = self._recognize_trocr(img_bgr)
        if len(text.strip()) > 1:
            logger.debug(f"recognize_word => TrOCR: '{text.strip()}'")
            return text.strip()

        text = self._recognize_easyocr(img_bgr)
        result = text.strip() if text.strip() else ""
        logger.debug(f"recognize_word => EasyOCR: '{result}'")
        return result

    def detect_words_full(self, img_bgr: np.ndarray) -> list:
        """كشف الكلمات مع الإحداثيات باستخدام EasyOCR مع تسجيل مفصّل."""
        logger.debug(f"detect_words_full: أبعاد الصورة={img_bgr.shape[:2]}")
        start = time.time()
        try:
            results = self.easy_reader.readtext(img_bgr, detail=1)
            elapsed = time.time() - start
            logger.info(f"  EasyOCR detect: {len(results)} كلمة في {elapsed:.2f}s")
            for i, det in enumerate(results[:5]):  # أول 5 فقط
                logger.debug(f"    det[{i}]: '{det[1][:30]}' ثقة={det[2]:.3f}")
            if len(results) > 5:
                logger.debug(f"    ... و {len(results) - 5} كلمة أخرى")
            return results
        except Exception as e:
            log_error_full(logger, "EasyOCR detect_words_full", e)
            return []

    def _recognize_trocr(self, img_bgr: np.ndarray) -> str:
        """TrOCR للتعرف على كلمة واحدة مع تسجيل."""
        if self.skip_trocr or self.trocr_processor is None:
            logger.debug("  _recognize_trocr: متجاوز (skip_trocr أو لا يوجد نموذج)")
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
            logger.debug(f"  _recognize_trocr فشل: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            return ""

    def _recognize_easyocr(self, img_bgr: np.ndarray) -> str:
        """EasyOCR: يختار النص بأعلى ثقة مع تسجيل مفصّل."""
        try:
            results = self.easy_reader.readtext(img_bgr)
            if results:
                best = max(results, key=lambda r: r[2])
                logger.debug(f"  _recognize_easyocr: '{best[1]}' ثقة={best[2]:.3f} (من {len(results)} نتيجة)")
                return best[1]
            logger.debug("  _recognize_easyocr: لا نتائج")
            return ""
        except Exception as e:
            logger.debug(f"  _recognize_easyocr فشل: {type(e).__name__}: {e}")
            return ""
