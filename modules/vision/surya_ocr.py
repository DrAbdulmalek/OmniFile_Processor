"""
محرك Surya OCR — المحرك الخامس لـ OmniFile Processor
========================================================
محرك OCR يعتمد على مكتبة Surya (من VikParuchuri) مع تحميل بطيء
للنماذج لتجنب استهلاك الذاكرة عند عدم الاستخدام.

يدعم اللغتين العربية والإنجليزية افتراضياً مع إمكانية إضافة لغات أخرى.
يُرجع نصاً كاملاً مع قائمة كتل مهيكلة متوافقة مع normalize_ocr_output.

المؤلف: Dr Abdulmalek Tamer Al-husseini
الترخيص: MIT
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SuryaOCREngine:
    """
    محرك Surya OCR مع تحميل بطيء للنماذج.

    مثال الاستخدام:
        >>> engine = SuryaOCREngine(langs=["ar", "en"])
        >>> text, blocks = engine.extract_text("image.jpg")
        >>> print(text)
    """

    def __init__(self, langs: Optional[list[str]] = None):
        """
        تهيئة محرك Surya.

        Args:
            langs: قائمة اللغات المدعومة (الافتراضي: ["ar", "en"])
        """
        if langs is None:
            langs = ["ar", "en"]
        self.langs = langs

        # تأخير التحميل لتجنب استهلاك الذاكرة عند عدم الاستخدام
        self.det_model = None
        self.det_processor = None
        self.rec_model = None
        self.rec_processor = None
        self._loaded = False

    def _load_models(self) -> bool:
        """
        تحميل نماذج Surya عند أول استخدام (Lazy Loading).

        Returns:
            True إذا تم التحميل بنجاح
        """
        if self._loaded and self.det_model is not None:
            return True

        try:
            from surya.model.detection.model import (
                load_model as load_det_model,
                load_processor as load_det_processor,
            )
            from surya.model.recognition.model import (
                load_model as load_rec_model,
            )
            from surya.model.recognition.processor import (
                load_processor as load_rec_processor,
            )

            logger.info(
                "جارٍ تحميل نماذج Surya (لغات: %s)...",
                self.langs,
            )

            self.det_model = load_det_model()
            self.det_processor = load_det_processor()
            self.rec_model = load_rec_model()
            self.rec_processor = load_rec_processor()

            self._loaded = True
            logger.info("تم تحميل نماذج Surya بنجاح")
            return True

        except ImportError:
            logger.warning(
                "مكتبة surya-ocr غير مثبتة. قم بتثبيتها:\n"
                "  pip install surya-ocr>=0.4.0"
            )
            return False
        except Exception as e:
            logger.error("فشل في تحميل نماذج Surya: %s", e)
            return False

    def extract_text(
        self,
        image_path: str,
    ) -> tuple[str, list[dict]]:
        """
        استخراج النص من صورة باستخدام Surya.

        Args:
            image_path: مسار ملف الصورة

        Returns:
            tuple (نص كامل, قائمة كتل مهيكلة):
            - النص الكامل المستخرج (كل الأسطر متصلة بـ \\n)
            - قائمة كتل تحتوي على: type, bbox, text, confidence
        """
        if not self._load_models():
            raise RuntimeError(
                "تعذر تحميل نماذج Surya. تأكد من تثبيت surya-ocr."
            )

        from PIL import Image
        from surya.ocr import run_ocr

        image = Image.open(image_path).convert("RGB")

        # تشغيل Surya OCR
        predictions = run_ocr(
            [image],
            [self.langs],
            self.det_model,
            self.det_processor,
            self.rec_model,
            self.rec_processor,
        )

        lines = predictions[0] if predictions else []
        blocks = []
        full_text = []

        for line in lines:
            # تحويل الإحداثيات المطلقة إلى نسبية
            bbox_rel = [
                line.bbox[0] / image.width,
                line.bbox[1] / image.height,
                line.bbox[2] / image.width,
                line.bbox[3] / image.height,
            ]

            confidence = getattr(line, "confidence", 0.0)

            blocks.append({
                "type": "paragraph",
                "bbox": bbox_rel,
                "text": getattr(line, "text", ""),
                "confidence": confidence,
            })
            full_text.append(getattr(line, "text", ""))

        return "\n".join(full_text), blocks

    def process(
        self,
        image_path: str,
        output_json_path: Optional[str] = None,
    ) -> dict:
        """
        معالجة كاملة: استخراج نص + تطبيع + حفظ JSON.

        Args:
            image_path: مسار ملف الصورة
            output_json_path: (اختياري) مسار ملف JSON للنتيجة

        Returns:
            dict النتيجة الموحدة بالهيكل القياسي
        """
        from PIL import Image
        from modules.vision.normalize import normalize_ocr_output, save_normalized

        text, blocks = self.extract_text(image_path)
        img = Image.open(image_path)
        w, h = img.size

        result = normalize_ocr_output(
            blocks, image_path, w, h, "surya", self.langs
        )

        if output_json_path:
            save_normalized(result, output_json_path)

        return result
