"""
محرك التعرف على النصوص (OCR Engine)
======================================
محرك متكامل يجمع بين خمسة محركات OCR:
- Surya - محرك حديث عالي الدقة للغات المتعددة
- TrOCR (من Microsoft) - الأفضل للمخطوطات اليدوية
- EasyOCR - سريع ودقيق متعدد اللغات
- Tesseract (OCR) - محرك كلاسيكي موثوق
- PaddleOCR - الأفضل للنصوص العربية و80+ لغة

القدرات:
- تحميل بطيء (Lazy Loading) - النماذج لا تُحمّل إلا عند الحاجة
- انحطاط سلس (Graceful Degradation) - ينتقل لمحرك آخر عند الفشل
- دعم GPU و CPU
- معالجة بالدفعات (Batch Processing)
- معالجة ملفات PDF مباشرة
- نتائج مع بيانات وصفية (ال-confidence، المصدر، وقت المعالجة)
"""

import logging
import os
import time
from typing import Optional, Union

logger = logging.getLogger(__name__)


class OCREngine:
    """
    محرك OCR المتكامل - يجمع بين TrOCR + EasyOCR + Tesseract + PaddleOCR.

    مثال الاستخدام:
        >>> engine = OCREngine(
        ...     trocr_model_name="microsoft/trocr-base-handwritten",
        ...     easyocr_languages=["en", "ar"],
        ...     use_gpu=True,
        ... )
        >>> # صورة واحدة
        >>> result = engine.recognize(image, languages=["ar"])
        >>> print(result["text"], result["confidence"])
        >>> # دفعة صور
        >>> results = engine.recognize_batch(images)
        >>> # ملف PDF
        >>> pdf_results = engine.recognize_pdf("document.pdf", pages=[0, 1])
    """

    def __init__(
        self,
        # إعدادات TrOCR
        trocr_model_name: str = "microsoft/trocr-base-handwritten",
        trocr_processor_name: str = "microsoft/trocr-base-handwritten",
        trocr_batch_size: int = 8,
        trocr_num_beams: int = 4,
        trocr_max_length: int = 64,
        # إعدادات EasyOCR
        easyocr_languages: Optional[list[str]] = None,
        easyocr_gpu: Optional[bool] = None,
        easyocr_model_storage_directory: Optional[str] = None,
        # إعدادات Tesseract
        tesseract_langs: str = "eng+ara",
        tesseract_config: str = "--oem 3 --psm 6",
        # إعدادات عامة
        use_gpu: bool = True,
        confidence_threshold: float = 0.5,
        low_confidence_threshold: float = 0.7,
        enable_trocr: bool = True,
        enable_easyocr: bool = True,
        enable_tesseract: bool = True,
        enable_surya: bool = False,
        enable_paddleocr: bool = False,
        preprocess: bool = True,
        dpi: int = 300,
    ) -> None:
        """
        تهيئة محرك OCR.

        Args:
            trocr_model_name: اسم نموذج TrOCR
            trocr_processor_name: اسم معالج TrOCR
            trocr_batch_size: حجم الدفعة لـ TrOCR
            trocr_num_beams: عدد الأشعة لـ beam search
            trocr_max_length: أقصى طول نص لـ TrOCR
            easyocr_languages: لغات EasyOCR (الافتراضي ["en", "ar"])
            easyocr_gpu: استخدام GPU لـ EasyOCR (None = تلقائي)
            easyocr_model_storage_directory: مسار تخزين نماذج EasyOCR
            tesseract_langs: لغات Tesseract
            tesseract_config: إعدادات Tesseract
            use_gpu: تفعيل GPU بشكل عام
            confidence_threshold: حد الثقة الأدنى لقبول النتيجة
            low_confidence_threshold: حد الثقة المنخفض (يعيد المحاولة بمحرك آخر)
            enable_trocr: تفعيل محرك TrOCR
            enable_easyocr: تفعيل محرك EasyOCR
            enable_tesseract: تفعيل محرك Tesseract
            enable_paddleocr: تفعيل محرك PaddleOCR (الأفضل للعربية)
            preprocess: تطبيق المعالجة المسبقة قبل OCR
            dpi: دقة تحويل PDF
        """
        # حفظ الإعدادات
        self.trocr_model_name = trocr_model_name
        self.trocr_processor_name = trocr_processor_name
        self.trocr_batch_size = trocr_batch_size
        self.trocr_num_beams = trocr_num_beams
        self.trocr_max_length = trocr_max_length

        self.easyocr_languages = easyocr_languages or ["en", "ar"]
        self.easyocr_gpu = easyocr_gpu if easyocr_gpu is not None else use_gpu
        self.easyocr_model_storage_directory = easyocr_model_storage_directory

        self.tesseract_langs = tesseract_langs
        self.tesseract_config = tesseract_config

        self.use_gpu = use_gpu
        self.confidence_threshold = confidence_threshold
        self.low_confidence_threshold = low_confidence_threshold

        self.enable_trocr = enable_trocr
        self.enable_easyocr = enable_easyocr
        self.enable_tesseract = enable_tesseract
        self.enable_surya = enable_surya
        self.enable_paddleocr = enable_paddleocr
        self.preprocess = preprocess
        self.dpi = dpi

        # النماذج - تُحمّل بشكل بطيء عند أول استخدام
        self._trocr_model = None
        self._trocr_processor = None
        self._trocr_loaded = False
        self._easyocr_reader = None
        self._easyocr_loaded = False
        self._tesseract_available = None
        self._surya_engine = None
        self._surya_loaded = False
        self._paddleocr_reader = None
        self._paddleocr_loaded = False

        # التحقق من توفر المكتبات
        self._has_torch = self._check_library("torch", "PyTorch")
        self._has_transformers = self._check_library(
            "transformers", "transformers"
        )
        self._has_easyocr = self._check_library("easyocr", "EasyOCR")
        self._has_paddleocr = self._check_library("paddleocr", "PaddleOCR")
        self._has_surya = self._check_library("surya", "surya-ocr")
        self._has_pil = self._check_library("PIL", "Pillow")

        # تحقق مبدئي من Tesseract
        self._check_tesseract()

        # معالج الصور المسبق
        self._preprocessor = None
        self._reconstructor = None

        # معالج PDF
        self._pdf_processor = None

        # تحذيرات
        self._log_availability()

    @classmethod
    def from_legacy_config(cls, config) -> "OCREngine":
        """
        إنشاء محرك OCR من كائن Config القديم (src.config.Config).
        يُستخدم لسهولة الترحيل من src/ إلى modules/.

        Args:
            config: كائن الإعدادات من src.config أو config.py

        Returns:
            مثيل OCREngine مهيأ بالإعدادات المناسبة
        """
        return cls(
            trocr_model_name=getattr(config, "trocr_model_name", "microsoft/trocr-base-handwritten"),
            trocr_processor_name=getattr(config, "trocr_model_name", "microsoft/trocr-base-handwritten"),
            trocr_batch_size=getattr(config, "trocr_batch_size", 8),
            trocr_num_beams=getattr(config, "num_beams", 4),
            easyocr_languages=getattr(config, "ocr_languages", None) or getattr(config, "easyocr_languages", None),
            easyocr_gpu=getattr(config, "use_gpu", None),
            easyocr_model_storage_directory=getattr(config, "cache_dir", None),
            tesseract_langs=getattr(config, "tesseract_langs", "eng+ara"),
            use_gpu=getattr(config, "use_gpu", True),
            confidence_threshold=getattr(config, "easy_conf_threshold", 0.5),
            enable_trocr=getattr(config, "skip_trocr", False) is False,
            enable_easyocr=True,
            enable_tesseract=True,
            enable_surya=getattr(config, "enable_surya", False),
            enable_paddleocr=getattr(config, "enable_paddleocr", False),
            dpi=getattr(config, "dpi", 300),
        )

    @staticmethod
    def _check_library(import_name: str, package_name: str) -> bool:
        """التحقق من توفر مكتبة."""
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False

    def _check_tesseract(self) -> None:
        """التحقق من توفر Tesseract."""
        try:
            import subprocess
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self._tesseract_available = result.returncode == 0
            if self._tesseract_available:
                logger.info("Tesseract متاح: %s", result.stdout.split("\n")[0])
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            self._tesseract_available = False
            logger.debug("Tesseract غير مثبت على النظام")

    def _log_availability(self) -> None:
        """تسجيل حالة توفر المحركات."""
        logger.info("حالة محركات OCR:")
        logger.info(
            "  TrOCR: %s (مفعّل: %s)",
            "متاح" if self._has_torch and self._has_transformers else "غير متاح",
            self.enable_trocr,
        )
        logger.info(
            "  EasyOCR: %s (مفعّل: %s)",
            "متاح" if self._has_easyocr else "غير متاح",
            self.enable_easyocr,
        )
        logger.info(
            "  Tesseract: %s (مفعّل: %s)",
            "متاح" if self._tesseract_available else "غير متاح",
            self.enable_tesseract,
        )
        logger.info(
            "  Surya: %s (مفعّل: %s)",
            "متاح" if self._has_surya else "غير متاح",
            self.enable_surya,
        )
        logger.info(
            "  PaddleOCR: %s (مفعّل: %s)",
            "متاح" if self._has_paddleocr else "غير متاح",
            self.enable_paddleocr,
        )

        active_engines = self._get_active_engines()
        if not active_engines:
            logger.warning(
                "لا يوجد أي محرك OCR متاح! لن يعمل المحرك. "
                "قم بتثبيت أحد: EasyOCR, Tesseract, أو transformers+torch"
            )

    def _get_active_engines(self) -> list[str]:
        """الحصول على قائمة المحركات الفعالة والمتاحة."""
        engines = []
        if self.enable_easyocr and self._has_easyocr:
            engines.append("easyocr")
        if self.enable_trocr and self._has_torch and self._has_transformers:
            engines.append("trocr")
        if self.enable_tesseract and self._tesseract_available:
            engines.append("tesseract")
        if self.enable_surya and self._has_surya:
            engines.append("surya")
        if self.enable_paddleocr and self._has_paddleocr:
            engines.append("paddleocr")
        return engines

    # ------------------------------------------------------------------
    # تحميل النماذج (Lazy Loading)
    # ------------------------------------------------------------------

    def _load_easyocr(self) -> bool:
        """تحميل EasyOCR عند أول استخدام."""
        if self._easyocr_loaded:
            return True

        if not self._has_easyocr:
            logger.debug("EasyOCR غير متاح")
            return False

        try:
            logger.info(
                "جارٍ تحميل EasyOCR (لغات: %s)...",
                self.easyocr_languages,
            )
            import easyocr

            gpu = self.easyocr_gpu and self.use_gpu
            kwargs: dict = {
                "lang_list": self.easyocr_languages,
                "gpu": gpu,
                "verbose": False,
            }
            if self.easyocr_model_storage_directory:
                kwargs["model_storage_directory"] = (
                    self.easyocr_model_storage_directory
                )

            self._easyocr_reader = easyocr.Reader(**kwargs)
            self._easyocr_loaded = True
            logger.info("تم تحميل EasyOCR بنجاح")
            return True

        except Exception as e:
            logger.error("فشل في تحميل EasyOCR: %s", e)
            self._easyocr_loaded = False
            return False

    def _load_trocr(self) -> bool:
        """تحميل TrOCR عند أول استخدام."""
        if self._trocr_loaded:
            return True

        if not (self._has_torch and self._has_transformers):
            logger.debug("TrOCR غير متاح (يتطلب torch و transformers)")
            return False

        try:
            import torch
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            device = "cuda" if (self.use_gpu and torch.cuda.is_available()) else "cpu"
            logger.info(
                "جارٍ تحميل TrOCR (الجهاز: %s)...", device
            )

            self._trocr_processor = TrOCRProcessor.from_pretrained(
                self.trocr_processor_name
            )
            self._trocr_model = VisionEncoderDecoderModel.from_pretrained(
                self.trocr_model_name
            )
            self._trocr_model.to(device)
            self._trocr_model.eval()

            self._trocr_loaded = True
            self._trocr_device = device
            logger.info("تم تحميل TrOCR بنجاح على %s", device)
            return True

        except Exception as e:
            logger.error("فشل في تحميل TrOCR: %s", e)
            self._trocr_loaded = False
            return False

    def _get_preprocessor(self):
        """الحصول على معالج الصور المسبق."""
        if self._preprocessor is None:
            try:
                from modules.vision.image_preprocessor import ImagePreprocessor
                self._preprocessor = ImagePreprocessor(
                    apply_clahe=True,
                    apply_denoise=True,
                    apply_deskew=True,
                    apply_binarize=False,  # لا نحتاج ثنائنة لكل المحركات
                )
            except Exception as e:
                logger.warning("فشل في تحميل معالج الصور: %s", e)
        return self._preprocessor

    def _get_reconstructor(self):
        """الحصول على مُعيد تجميع النصوص."""
        if self._reconstructor is None:
            try:
                from modules.vision.text_reconstructor import TextReconstructor
                self._reconstructor = TextReconstructor()
            except Exception as e:
                logger.warning("فشل في تحميل مُعيد التجميع: %s", e)
        return self._reconstructor

    def _get_pdf_processor(self):
        """الحصول على معالج PDF."""
        if self._pdf_processor is None:
            try:
                from modules.vision.pdf_processor import PDFProcessor
                self._pdf_processor = PDFProcessor(dpi=self.dpi)
            except Exception as e:
                logger.warning("فشل في تحميل معالج PDF: %s", e)
        return self._pdf_processor

    # ------------------------------------------------------------------
    # الأساليب العامة (Public API)
    # ------------------------------------------------------------------

    def recognize(
        self,
        image: Union["np.ndarray", "PIL.Image.Image"],
        languages: Optional[list[str]] = None,
    ) -> dict:
        """
        التعرف على النص في صورة واحدة باستخدام أفضل محرك متاح.

        الاستراتيجية:
        1. تجربة EasyOCR أولاً (الأسرع)
        2. إذا كانت الثقة أقل من الحد، تجربة TrOCR
        3. تجربة Tesseract كاحتياطي أخير
        4. دمج النتائج واختيار الأفضل

        Args:
            image: صورة PIL أو مصفوفة numpy
            languages: لغات مطلوبة (تؤثر على اختيار المحرك)

        Returns:
            قاميس يحتوي:
            - text: النص المستخرج
            - confidence: مستوى الثقة (0-1)
            - source: المحرك المستخدم
            - processing_time: وقت المعالجة بالثواني
            - details: تفاصيل إضافية
        """
        start_time = time.time()

        # التحقق من الصورة
        pil_image = self._ensure_pil(image)

        # المعالجة المسبقة
        if self.preprocess:
            preprocessor = self._get_preprocessor()
            if preprocessor:
                try:
                    pil_image = preprocessor.preprocess(pil_image)
                except Exception as e:
                    logger.warning("فشلت المعالجة المسبقة: %s", e)

        results: list[dict] = []

        # 1. تجربة EasyOCR
        if self.enable_easyocr:
            easyocr_result = self._recognize_easyocr(pil_image)
            if easyocr_result:
                results.append(easyocr_result)

        # 2. تجربة TrOCR إذا كانت الثقة منخفضة أو لم تنجح EasyOCR
        use_trocr = False
        if results:
            best_conf = max(r["confidence"] for r in results)
            if best_conf < self.low_confidence_threshold:
                use_trocr = True
        else:
            use_trocr = True

        if use_trocr and self.enable_trocr:
            trocr_result = self._recognize_trocr(pil_image)
            if trocr_result:
                results.append(trocr_result)

        # 3. تجربة Tesseract كاحتياطي
        if self.enable_tesseract:
            tesseract_result = self._recognize_tesseract(pil_image)
            if tesseract_result:
                results.append(tesseract_result)

        # 4. تجربة Surya (محرك حديث عالي الدقة)
        if self.enable_surya:
            surya_result = self._recognize_surya(pil_image)
            if surya_result:
                results.append(surya_result)

        # 5. تجربة PaddleOCR (الأفضل للنصوص العربية)
        if self.enable_paddleocr:
            paddleocr_result = self._recognize_paddleocr(pil_image)
            if paddleocr_result:
                results.append(paddleocr_result)

        # اختيار أفضل نتيجة
        best_result = self._select_best_result(results)

        processing_time = time.time() - start_time
        best_result["processing_time"] = processing_time

        logger.info(
            "نتيجة OCR: '%s' (محرك: %s, ثقة: %.2f%%, وقت: %.2fs)",
            best_result["text"][:50],
            best_result["source"],
            best_result["confidence"] * 100,
            processing_time,
        )

        return best_result

    def recognize_batch(
        self,
        images: list[Union["np.ndarray", "PIL.Image.Image"]],
        languages: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        التعرف على النص في مجموعة صور.

        Args:
            images: قائمة صور (PIL أو numpy)
            languages: لغات مطلوبة

        Returns:
            قائمة نتائج OCR (نفس تنسيق recognize())
        """
        results: list[dict] = []

        for idx, image in enumerate(images):
            logger.debug("معالجة صورة %d من %d...", idx + 1, len(images))
            try:
                result = dict(self.recognize(image, languages=languages))
                result["batch_index"] = idx
                results.append(result)
            except Exception as e:
                logger.error("فشل في معالجة صورة %d: %s", idx, e)
                results.append({
                    "text": "",
                    "confidence": 0.0,
                    "source": "error",
                    "processing_time": 0.0,
                    "error": str(e),
                    "batch_index": idx,
                })

        return results

    def recognize_pdf(
        self,
        pdf_path: str,
        pages: Optional[list[int]] = None,
        languages: Optional[list[str]] = None,
        progress_callback: Optional[callable] = None,
    ) -> list[dict]:
        """
        استخراج النص من ملف PDF مباشرة.

        يجمع بين PDFProcessor لتحويل PDF إلى صور و OCREngine للتعرف.

        Args:
            pdf_path: مسار ملف PDF
            pages: أرقام الصفحات المطلوبة (None = الكل)
            languages: لغات مطلوبة
            progress_callback: دالة استدعاء لمراقبة التقدم

        Returns:
            قائمة نتائج لكل صفحة:
            - page_num: رقم الصفحة
            - text: النص المستخرج
            - ocr_result: نتيجة OCR التفصيلية
            - extracted_text: النص المدمج من PDFExtractor
        """
        pdf_processor = self._get_pdf_processor()
        if not pdf_processor:
            raise RuntimeError("معالج PDF غير متاح")

        # معالجة PDF
        pdf_results = pdf_processor.process_pdf(
            pdf_path, pages=pages, progress_callback=progress_callback
        )

        output: list[dict] = []

        for page_data in pdf_results:
            page_num = page_data["page_num"]
            extracted_text = page_data.get("text", "")
            page_image = page_data.get("page_image")

            ocr_text = ""
            ocr_result = None

            # إذا كانت هناك صورة للصفحة، نستخدم OCR
            if page_image is not None:
                try:
                    ocr_result = self.recognize(page_image, languages=languages)
                    ocr_text = ocr_result["text"]
                except Exception as e:
                    logger.error(
                        "فشل OCR للصفحة %d: %s", page_num, e
                    )

            # دمج النص المستخرج من PDF مع نتيجة OCR
            # نفضل النص الأطول والأكثر ثقة
            if ocr_text and len(ocr_text) > len(extracted_text):
                final_text = ocr_text
                source = "ocr"
            elif extracted_text:
                final_text = extracted_text
                source = "pdf_extract"
            else:
                final_text = ocr_text
                source = "ocr"

            output.append({
                "page_num": page_num,
                "text": final_text,
                "source": source,
                "ocr_result": ocr_result,
                "pdf_text": extracted_text,
                "images_count": len(page_data.get("images", [])),
                "tables_count": len(page_data.get("tables", [])),
                "error": page_data.get("error"),
            })

        logger.info(
            "تمت معالجة PDF: %d صفحة", len(output)
        )
        return output

    # ------------------------------------------------------------------
    # محركات OCR الفردية (Private)
    # ------------------------------------------------------------------

    def _recognize_easyocr(self, image: "PIL.Image.Image") -> Optional[dict]:
        """
        التعرف على النص باستخدام EasyOCR.

        Args:
            image: صورة PIL

        Returns:
            قاميس النتيجة أو None عند الفشل
        """
        if not self._load_easyocr():
            return None

        try:
            import numpy as np

            # تحويل PIL إلى numpy (RGB)
            img_array = np.array(image)

            # تشغيل EasyOCR
            results = self._easyocr_reader.readtext(img_array)

            if not results:
                return None

            # استخراج النصوص والثقة
            texts = []
            confidences = []
            word_boxes = []

            for bbox, text, conf in results:
                if conf >= self.confidence_threshold:
                    texts.append(text)
                    confidences.append(conf)

                    # حساب الموقع
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]
                    x = int(min(x_coords))
                    y = int(min(y_coords))
                    w = int(max(x_coords)) - x
                    h = int(max(y_coords)) - y

                    word_boxes.append({
                        "text": text,
                        "x": x, "y": y,
                        "w": w, "h": h,
                        "confidence": conf,
                    })

            if not texts:
                return None

            # إعادة تجميع النصوص
            reconstructor = self._get_reconstructor()
            if reconstructor and word_boxes:
                full_text = reconstructor.reconstruct(word_boxes)
            else:
                full_text = " ".join(texts)

            avg_confidence = sum(confidences) / len(confidences)

            return {
                "text": full_text.strip(),
                "confidence": avg_confidence,
                "source": "easyocr",
                "word_count": len(texts),
                "words": word_boxes,
                "details": {
                    "raw_texts": texts,
                    "raw_confidences": confidences,
                },
            }

        except Exception as e:
            logger.warning("فشل EasyOCR: %s", e)
            return None

    def _recognize_trocr(self, image: "PIL.Image.Image") -> Optional[dict]:
        """
        التعرف على النص باستخدام TrOCR.

        Args:
            image: صورة PIL

        Returns:
            قاميس النتيجة أو None عند الفشل
        """
        if not self._load_trocr():
            return None

        try:
            import torch

            # التأكد من وضع التقييم
            self._trocr_model.eval()

            device = getattr(self, "_trocr_device", "cpu")

            # معالجة الصورة
            pixel_values = self._trocr_processor(
                image, return_tensors="pt"
            ).pixel_values.to(device)

            # التوليد
            with torch.no_grad():
                generated_ids = self._trocr_model.generate(
                    pixel_values,
                    max_length=self.trocr_max_length,
                    num_beams=self.trocr_num_beams,
                )

            # فك التشفير
            generated_text = self._trocr_processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0].strip()

            if not generated_text:
                return None

            # TrOCR لا يوفر ثقة مباشرة، نستخدم قيمة افتراضية
            confidence = 0.85  # TrOCR عادةً دقيق جداً للمخطوطات

            return {
                "text": generated_text,
                "confidence": confidence,
                "source": "trocr",
                "word_count": len(generated_text.split()),
                "details": {
                    "model": self.trocr_model_name,
                    "device": device,
                },
            }

        except Exception as e:
            logger.warning("فشل TrOCR: %s", e)
            return None

    def _recognize_tesseract(self, image: "PIL.Image.Image") -> Optional[dict]:
        """
        التعرف على النص باستخدام Tesseract OCR.

        Args:
            image: صورة PIL

        Returns:
            قاميس النتيجة أو None عند الفشل
        """
        if not self._tesseract_available:
            return None

        try:
            import pytesseract
            from PIL import Image
            import numpy as np

            # التأكد من RGB
            if image.mode != "RGB":
                image = image.convert("RGB")

            # الحصول على البيانات مع الثقة
            data = pytesseract.image_to_data(
                image,
                lang=self.tesseract_langs,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT,
            )

            texts = []
            confidences = []
            word_boxes = []

            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf_str = data["conf"][i]

                if not text:
                    continue

                try:
                    conf = int(conf_str) / 100.0
                except (ValueError, TypeError):
                    conf = 0.0

                if conf < self.confidence_threshold:
                    continue

                texts.append(text)
                confidences.append(conf)

                word_boxes.append({
                    "text": text,
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                    "confidence": conf,
                })

            if not texts:
                return None

            # إعادة تجميع
            reconstructor = self._get_reconstructor()
            if reconstructor and word_boxes:
                full_text = reconstructor.reconstruct(word_boxes)
            else:
                full_text = " ".join(texts)

            avg_confidence = sum(confidences) / len(confidences)

            return {
                "text": full_text.strip(),
                "confidence": avg_confidence,
                "source": "tesseract",
                "word_count": len(texts),
                "words": word_boxes,
                "details": {
                    "langs": self.tesseract_langs,
                    "config": self.tesseract_config,
                },
            }

        except ImportError:
            logger.debug("pytesseract غير مثبت")
            return None
        except Exception as e:
            logger.warning("فشل Tesseract: %s", e)
            return None

    def _load_surya(self) -> bool:
        """تحميل Surya عند أول استخدام (Lazy Loading).

        Surya محرك OCR حديث عالي الدقة يدعم لغات متعددة.
        يُحمّل فقط عند أول استدعاء وليس عند التهيئة.

        Returns:
            True إذا تم التحميل بنجاح
        """
        if self._surya_loaded:
            return True

        if not self._has_surya:
            logger.debug("Surya غير متاح")
            return False

        try:
            logger.info("جارٍ تحميل Surya OCR...")
            from modules.vision.surya_ocr import SuryaOCREngine

            self._surya_engine = SuryaOCREngine(langs=self.easyocr_languages)
            self._surya_loaded = True
            logger.info("تم تحميل Surya OCR بنجاح")
            return True

        except ImportError:
            logger.warning(
                "Surya غير مثبت. قم بتثبيته:\n"
                "  pip install surya-ocr>=0.4.0"
            )
            self._surya_loaded = False
            return False
        except Exception as e:
            logger.error("فشل في تحميل Surya: %s", e)
            self._surya_loaded = False
            return False

    def _recognize_surya(self, image: "PIL.Image.Image") -> Optional[dict]:
        """
        التعرف على النص باستخدام Surya OCR.

        Args:
            image: صورة PIL

        Returns:
            قاميس النتيجة أو None عند الفشل
        """
        if not self._load_surya():
            return None

        try:
            import tempfile
            import os

            # Surya يعمل على مسار ملف، لذا نحفظ الصورة مؤقتاً
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                image.save(tmp.name)
                tmp_path = tmp.name

            try:
                text, blocks = self._surya_engine.extract_text(tmp_path)

                if not text.strip():
                    return None

                # حساب الثقة المتوسطة
                confidences = [b.get("confidence", 0.0) for b in blocks]
                avg_confidence = (
                    sum(confidences) / len(confidences) if confidences else 0.0
                )

                # تحويل الكتل إلى word_boxes للإعادة
                word_boxes = []
                for b in blocks:
                    bbox = b.get("bbox", [0, 0, 0, 0])
                    if len(bbox) == 4:
                        word_boxes.append({
                            "text": b.get("text", ""),
                            "x": int(bbox[0] * image.width),
                            "y": int(bbox[1] * image.height),
                            "w": int((bbox[2] - bbox[0]) * image.width),
                            "h": int((bbox[3] - bbox[1]) * image.height),
                            "confidence": b.get("confidence", 0.0),
                        })

                return {
                    "text": text.strip(),
                    "confidence": avg_confidence,
                    "source": "surya",
                    "word_count": len(blocks),
                    "words": word_boxes,
                    "details": {
                        "langs": self._surya_engine.langs,
                        "block_count": len(blocks),
                    },
                }
            finally:
                # حذف الملف المؤقت
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.warning("فشل Surya: %s", e)
            return None

    def _load_paddleocr(self) -> bool:
        """تحميل PaddleOCR عند أول استخدام (Lazy Loading).

        PaddleOCR هو الأفضل للنصوص العربية ويدعم 80+ لغة.
        يُحمّل فقط عند أول استدعاء وليس عند التهيئة.

        Returns:
            True إذا تم التحميل بنجاح
        """
        if self._paddleocr_loaded:
            return True

        if not self._has_paddleocr:
            logger.debug("PaddleOCR غير متاح")
            return False

        try:
            logger.info("جارٍ تحميل PaddleOCR...")
            from paddleocr import PaddleOCR

            lang_str = "ar"  # الافتراضي: العربية + الإنجليزية

            self._paddleocr_reader = PaddleOCR(
                use_angle_cls=True,
                lang=lang_str,
                use_gpu=self.use_gpu,
                show_log=False,
            )
            self._paddleocr_loaded = True
            logger.info("تم تحميل PaddleOCR بنجاح")
            return True

        except ImportError:
            logger.warning(
                "PaddleOCR غير مثبت. قم بتثبيته:\n"
                "  pip install paddlepaddle paddleocr"
            )
            self._paddleocr_loaded = False
            return False
        except Exception as e:
            logger.error("فشل في تحميل PaddleOCR: %s", e)
            self._paddleocr_loaded = False
            return False

    def _recognize_paddleocr(self, image: "PIL.Image.Image") -> Optional[dict]:
        """
        التعرف على النص باستخدام PaddleOCR.

        محرك ممتاز للنصوص العربية مع دعم اتجاه النص تلقائياً.

        Args:
            image: صورة PIL

        Returns:
            قاميس النتيجة أو None عند الفشل
        """
        if not self._load_paddleocr():
            return None

        try:
            import numpy as np

            # تحويل PIL إلى numpy (RGB → BGR)
            img_array = np.array(image)
            if img_array.ndim == 3 and img_array.shape[2] == 3:
                img_bgr = img_array[:, :, ::-1]  # RGB → BGR
            else:
                img_bgr = img_array

            # تشغيل PaddleOCR
            results = self._paddleocr_reader.ocr(img_bgr, cls=True)

            if not results or not results[0]:
                return None

            texts = []
            confidences = []
            word_boxes = []

            for item in results[0]:
                # item = [bbox_points, (text, confidence)]
                bbox_points = item[0]
                text, confidence = item[1]

                if confidence < self.confidence_threshold:
                    continue

                texts.append(text)
                confidences.append(confidence)

                # حساب الموقع
                xs = [p[0] for p in bbox_points]
                ys = [p[1] for p in bbox_points]
                x = int(min(xs))
                y = int(min(ys))
                w = int(max(xs)) - x
                h = int(max(ys)) - y

                word_boxes.append({
                    "text": text,
                    "x": x, "y": y,
                    "w": w, "h": h,
                    "confidence": confidence,
                })

            if not texts:
                return None

            # إعادة تجميع النصوص
            reconstructor = self._get_reconstructor()
            if reconstructor and word_boxes:
                full_text = reconstructor.reconstruct(word_boxes)
            else:
                full_text = " ".join(texts)

            avg_confidence = sum(confidences) / len(confidences)

            return {
                "text": full_text.strip(),
                "confidence": avg_confidence,
                "source": "paddleocr",
                "word_count": len(texts),
                "words": word_boxes,
                "details": {
                    "raw_texts": texts,
                    "raw_confidences": confidences,
                },
            }

        except Exception as e:
            logger.warning("فشل PaddleOCR: %s", e)
            return None

    # ------------------------------------------------------------------
    # دمج النتائج
    # ------------------------------------------------------------------

    @staticmethod
    def _select_best_result(results: list[dict]) -> dict:
        """
        اختيار أفضل نتيجة من عدة محركات.

        الاستراتيجية:
        1. إذا كانت هناك نتيجة واحدة فقط، إرجاعها
        2. اختيار النتيجة بأعلى ثقة
        3. إذا تساوت الثقة، نفضل TrOCR > EasyOCR > Tesseract

        Args:
            results: قائمة نتائج المحركات

        Returns:
            أفضل نتيجة
        """
        if not results:
            return {
                "text": "",
                "confidence": 0.0,
                "source": "none",
                "processing_time": 0.0,
                "word_count": 0,
                "details": {},
            }

        if len(results) == 1:
            return results[0]

        # ترتيب حسب الثقة (تنازلياً) ثم حسب أولوية المحرك
        engine_priority = {"surya": 5, "trocr": 4, "paddleocr": 3, "easyocr": 2, "tesseract": 1}

        def sort_key(r: dict) -> tuple:
            priority = engine_priority.get(r["source"], 0)
            return (r["confidence"], priority)

        best = max(results, key=sort_key)
        best["all_results"] = [
            {
                "text": r["text"],
                "confidence": r["confidence"],
                "source": r["source"],
            }
            for r in results
        ]

        return best

    # ------------------------------------------------------------------
    # أدوات مساعدة
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_pil(image: Union["np.ndarray", "PIL.Image.Image"]) -> "PIL.Image.Image":
        """التأكد من أن الصورة بصيغة PIL Image RGB."""
        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError("Pillow غير مثبت")

        if isinstance(image, Image.Image):
            if image.mode != "RGB":
                return image.convert("RGB")
            return image
        elif isinstance(image, __import__("numpy").ndarray):
            if image.ndim == 2:
                return Image.fromarray(image, mode="L").convert("RGB")
            elif image.ndim == 3:
                if image.shape[2] == 4:
                    return Image.fromarray(image[:, :, :3], mode="RGB")
                elif image.shape[2] == 3:
                    return Image.fromarray(image, mode="RGB")
                else:
                    return Image.fromarray(image[:, :, 0], mode="L").convert("RGB")
            return Image.fromarray(image).convert("RGB")
        else:
            raise TypeError(f"نوع غير مدعوم: {type(image)}")

    def get_available_engines(self) -> list[dict]:
        """
        الحصول على قائمة المحركات المتاحة مع حالتها.

        Returns:
            قائمة قواميس: {name, available, enabled}
        """
        return [
            {
                "name": "EasyOCR",
                "available": self._has_easyocr,
                "enabled": self.enable_easyocr,
                "loaded": self._easyocr_loaded,
            },
            {
                "name": "TrOCR",
                "available": self._has_torch and self._has_transformers,
                "enabled": self.enable_trocr,
                "loaded": self._trocr_loaded,
            },
            {
                "name": "Tesseract",
                "available": self._tesseract_available,
                "enabled": self.enable_tesseract,
                "loaded": self._tesseract_available is True,
            },
            {
                "name": "Surya",
                "available": self._has_surya,
                "enabled": self.enable_surya,
                "loaded": self._surya_loaded,
            },
            {
                "name": "PaddleOCR",
                "available": self._has_paddleocr,
                "enabled": self.enable_paddleocr,
                "loaded": self._paddleocr_loaded,
            },
        ]

    # ------------------------------------------------------------------
    # تخزين مؤقت لنتائج OCR (OCR Caching)
    # ------------------------------------------------------------------

    def _get_cache_key(self, image: "PIL.Image.Image") -> str:
        """حساب مفتاح كاش للصورة بناءً على محتواها وحجمها."""
        import hashlib
        from io import BytesIO
        buf = BytesIO()
        image.save(buf, format="PNG")
        img_hash = hashlib.md5(buf.getvalue()).hexdigest()
        return f"{img_hash}_{image.size[0]}x{image.size[1]}"

    def recognize_with_cache(
        self,
        image: Union["np.ndarray", "PIL.Image.Image"],
        languages: Optional[list[str]] = None,
        cache: Optional[dict] = None,
        ttl: int = 3600,
    ) -> dict:
        """
        التعرف مع تخزين مؤقت للنتائج.

        Args:
            image: صورة PIL أو numpy
            languages: لغات مطلوبة
            cache: قاموس الكاش المشترك (إذا None، يُنشأ محلياً)
            ttl: مدة صلاحية الكاش بالثواني

        Returns:
            نتيجة OCR مع توضيح ما إذا كانت من الكاش
        """
        import time as _time

        if cache is None:
            if not hasattr(self, "_result_cache"):
                self._result_cache = {}
            cache = self._result_cache

        pil_image = self._ensure_pil(image)
        cache_key = self._get_cache_key(pil_image)

        # فحص الكاش
        if cache_key in cache:
            cached_entry = cache[cache_key]
            cached_time = cached_entry.get("timestamp", 0)
            if _time.time() - cached_time < ttl:
                result = cached_entry["result"].copy()
                result["from_cache"] = True
                result["cache_age"] = _time.time() - cached_time
                logger.info("نتيجة OCR من الكاش (عمر: %.1fs)", result["cache_age"])
                return result

        # ليس في الكاش - معالجة عادية
        result = self.recognize(pil_image, languages=languages)
        result["from_cache"] = False

        # حفظ في الكاش
        cache[cache_key] = {
            "result": {k: v for k, v in result.items() if k != "from_cache"},
            "timestamp": _time.time(),
        }

        return result

    # ------------------------------------------------------------------
    # ONNX Runtime (تسريع الاستدلال)
    # ------------------------------------------------------------------

    def load_trocr_onnx(self, onnx_model_path: Optional[str] = None) -> bool:
        """
        تحميل نموذج TrOCR بتنسيق ONNX لتسريع الاستدلال.

        Args:
            onnx_model_path: مسار ملف ONNX (إذا None، يُصدّر تلقائياً)

        Returns:
            True إذا تم التحميل بنجاح
        """
        try:
            import onnxruntime as ort
            import numpy as np
            import torch
            from transformers import TrOCRProcessor

            if onnx_model_path and os.path.exists(onnx_model_path):
                # تحميل ONNX مباشرة
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                if self.use_gpu:
                    providers = ["CUDAExecutionProvider"] + providers
                self._onnx_session = ort.InferenceSession(onnx_model_path, providers=providers)
            else:
                # تصدير من PyTorch إلى ONNX
                logger.info("جارٍ تصدير TrOCR إلى ONNX...")
                if not self._load_trocr():
                    return False

                dummy_input = torch.randn(1, 3, 384, 384)
                onnx_path = onnx_model_path or "trocr_model.onnx"
                torch.onnx.export(
                    self._trocr_model,
                    dummy_input,
                    onnx_path,
                    input_names=["pixel_values"],
                    output_names=["logits"],
                    dynamic_axes={
                        "pixel_values": {0: "batch_size"},
                        "logits": {0: "batch_size"},
                    },
                    opset_version=14,
                )
                self._onnx_session = ort.InferenceSession(onnx_path)

            self._onnx_processor = TrOCRProcessor.from_pretrained(
                self.trocr_processor_name
            )
            self._onnx_available = True
            logger.info("تم تحميل TrOCR ONNX بنجاح")
            return True

        except ImportError:
            logger.warning("onnxruntime غير مثبت. pip install onnxruntime")
            self._onnx_available = False
            return False
        except Exception as e:
            logger.error("فشل تحميل ONNX: %s", e)
            self._onnx_available = False
            return False

    def _recognize_trocr_onnx(self, image: "PIL.Image.Image") -> Optional[dict]:
        """تشغيل TrOCR عبر ONNX Runtime."""
        if not getattr(self, "_onnx_available", False):
            return None

        try:
            import numpy as np

            pixel_values = self._onnx_processor(
                image, return_tensors="np"
            ).pixel_values

            outputs = self._onnx_session.run(
                None, {"pixel_values": pixel_values}
            )
            logits = outputs[0]

            generated_ids = np.argmax(logits, axis=-1)
            generated_text = self._onnx_processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0].strip()

            if not generated_text:
                return None

            return {
                "text": generated_text,
                "confidence": 0.85,
                "source": "trocr_onnx",
                "word_count": len(generated_text.split()),
                "details": {"runtime": "onnx"},
            }
        except Exception as e:
            logger.warning("فشل TrOCR ONNX: %s", e)
            return None

    # ------------------------------------------------------------------
    # Quantization (تخفيف دقة النماذج)
    # ------------------------------------------------------------------

    def quantize_model(self) -> bool:
        """
        تحويل نموذج TrOCR إلى دقة INT8 لتقليل استهلاك الذاكرة.

        Returns:
            True إذا تم التحويل بنجاح
        """
        try:
            import torch
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            if not self._load_trocr():
                return False

            logger.info("جارٍ تحويل TrOCR إلى INT8...")
            self._trocr_model = torch.quantization.quantize_dynamic(
                self._trocr_model,
                {torch.nn.Linear},
                dtype=torch.qint8,
            )

            device = "cuda" if (self.use_gpu and torch.cuda.is_available()) else "cpu"
            self._trocr_model.to(device)
            self._trocr_device = device
            self._quantized = True

            logger.info("تم تحويل TrOCR إلى INT8 بنجاح على %s", device)
            return True

        except Exception as e:
            logger.error("فشل تحويل النموذج: %s", e)
            self._quantized = False
            return False

    @property
    def is_quantized(self) -> bool:
        """هل النموذج محوّل إلى INT8؟"""
        return getattr(self, "_quantized", False)

    # ------------------------------------------------------------------
    # Batch Processing مع إبلاغ عن التقدم
    # ------------------------------------------------------------------

    def recognize_batch_with_progress(
        self,
        images: list[Union["np.ndarray", "PIL.Image.Image"]],
        languages: Optional[list[str]] = None,
        progress_callback: Optional[callable] = None,
    ) -> list[dict]:
        """
        معالجة دفعة صور مع إبلاغ عن التقدم.

        Args:
            images: قائمة صور
            languages: لغات مطلوبة
            progress_callback: دالة(current, total, status) للإبلاغ عن التقدم

        Returns:
            قائمة نتائج OCR
        """
        results: list[dict] = []
        total = len(images)

        for idx, image in enumerate(images):
            status = f"معالجة صورة {idx + 1}/{total}"
            if progress_callback:
                progress_callback(idx, total, status)

            try:
                result = self.recognize(image, languages=languages)
                result["batch_index"] = idx
                results.append(result)
            except Exception as e:
                logger.error("فشل معالجة صورة %d: %s", idx, e)
                results.append({
                    "text": "",
                    "confidence": 0.0,
                    "source": "error",
                    "processing_time": 0.0,
                    "error": str(e),
                    "batch_index": idx,
                })

        if progress_callback:
            progress_callback(total, total, "اكتملت المعالجة")

        return results

    def unload_models(self) -> None:
        """
        تفريغ النماذج من الذاكرة لتحرير الموارد.

        مفيد عند انتهاء المعالجة أو عند الحاجة لذاكرة إضافية.
        """
        # تفريغ EasyOCR
        if self._easyocr_reader is not None:
            try:
                del self._easyocr_reader
            except Exception:
                pass
            self._easyocr_reader = None
            self._easyocr_loaded = False
            logger.info("تم تفريغ EasyOCR")

        # تفريغ TrOCR
        if self._trocr_model is not None:
            try:
                import torch
                device = getattr(self, "_trocr_device", "cpu")
                if device == "cuda":
                    self._trocr_model.cpu()
                del self._trocr_model
                if device == "cuda":
                    torch.cuda.empty_cache()
            except Exception:
                pass
            self._trocr_model = None
            self._trocr_processor = None
            self._trocr_loaded = False
            logger.info("تم تفريغ TrOCR")

        # تفريغ معالج الصور
        if self._preprocessor is not None:
            try:
                del self._preprocessor
            except Exception:
                pass
            self._preprocessor = None

        # تفريغ GC
        try:
            import gc
            gc.collect()
        except Exception:
            pass

        logger.info("تم تفريغ جميع النماذج من الذاكرة")
