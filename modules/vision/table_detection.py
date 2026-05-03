"""
محرك كشف الجداول بـ Table Transformer (TATR)
================================================
يكشف مواقع الجداول في الصور باستخدام Microsoft Table Transformer.
يُرجع قائمة بالجداول المكتشفة مع إحداثيات BBox ونسبة الثقة.

يمكن دمج النتائج مع الهيكل القياسي لـ normalize_ocr_output().

المؤلف: Dr Abdulmalek Tamer Al-husseini
الترخيص: MIT
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TableDetectionTransformer:
    """
    محرك كشف الجداول باستخدام Table Transformer.

    مثال الاستخدام:
        >>> detector = TableDetectionTransformer(device='cpu')
        >>> tables = detector.detect_tables("image.jpg", threshold=0.8)
        >>> for t in tables:
        ...     print(f"جدول: {t['bbox']}, ثقة: {t['score']}")
    """

    def __init__(
        self,
        model_name: str = "microsoft/table-transformer-detection",
        device: Optional[str] = None,
    ):
        """
        تهيئة كاشف الجداول.

        Args:
            model_name: اسم النموذج من HuggingFace
            device: الجهاز ('cuda' أو 'cpu'). إذا None يُكتشف تلقائياً.
        """
        self.model_name = model_name
        self.processor = None
        self.model = None
        self._loaded = False

        if device is None:
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device

    def _load_model(self) -> bool:
        """
        تحميل النموذج والمعالج (Lazy Loading).

        Returns:
            True إذا تم التحميل بنجاح
        """
        if self._loaded and self.model is not None:
            return True

        try:
            from transformers import (
                AutoImageProcessor,
                AutoModelForObjectDetection,
            )
            import torch

            logger.info("جارٍ تحميل Table Transformer (الجهاز: %s)...", self.device)

            self.processor = AutoImageProcessor.from_pretrained(self.model_name)
            self.model = (
                AutoModelForObjectDetection.from_pretrained(self.model_name)
                .to(self.device)
            )
            self.model.eval()

            self._loaded = True
            logger.info("تم تحميل Table Transformer بنجاح")
            return True

        except ImportError:
            logger.warning(
                "مكتبة transformers غير مثبتة. قم بتثبيتها:\n"
                "  pip install transformers>=4.37.0 torch>=2.0.0"
            )
            return False
        except Exception as e:
            logger.error("فشل في تحميل Table Transformer: %s", e)
            return False

    def detect_tables(
        self,
        image_path: str,
        threshold: float = 0.8,
    ) -> list[dict]:
        """
        كشف الجداول في صورة.

        Args:
            image_path: مسار ملف الصورة
            threshold: حد الثقة الأدنى لاكتشاف الجداول (الافتراضي 0.8)

        Returns:
            قائمة جداول، كل جدول يحتوي على:
            - bbox: [x1, y1, x2, y2] (إحداثيات مطلقة)
            - score: نسبة الثقة (0-1)
            - label: تسمية الكائن المكتشف
        """
        if not self._load_model():
            logger.warning("تعذر تحميل Table Transformer")
            return []

        try:
            import torch
            from PIL import Image

            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(
                images=image, return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)

            target_sizes = torch.tensor([image.size[::-1]]).to(self.device)
            results = self.processor.post_process_object_detection(
                outputs,
                threshold=threshold,
                target_sizes=target_sizes,
            )[0]

            tables = []
            for score, label, box in zip(
                results["scores"],
                results["labels"],
                results["boxes"],
            ):
                box_coords = [round(i) for i in box.tolist()]
                tables.append({
                    "bbox": box_coords,
                    "score": round(score.item(), 3),
                    "label": self.model.config.id2label[label.item()],
                })

            logger.info(
                "تم كشف %d جدول في الصورة (عتبة: %.2f)",
                len(tables),
                threshold,
            )
            return tables

        except Exception as e:
            logger.error("فشل في كشف الجداول: %s", e)
            return []

    def detect_tables_relative(
        self,
        image_path: str,
        threshold: float = 0.8,
    ) -> list[dict]:
        """
        كشف الجداول مع إحداثيات نسبية (للدمج مع الهيكل القياسي).

        Args:
            image_path: مسار ملف الصورة
            threshold: حد الثقة الأدنى

        Returns:
            قائمة جداول مع bbox نسبي [x1/W, y1/H, x2/W, y2/H]
        """
        from PIL import Image

        tables = self.detect_tables(image_path, threshold)
        img = Image.open(image_path)
        w, h = img.size

        for table in tables:
            x1, y1, x2, y2 = table["bbox"]
            table["bbox_relative"] = [x1 / w, y1 / h, x2 / w, y2 / h]

        return tables
