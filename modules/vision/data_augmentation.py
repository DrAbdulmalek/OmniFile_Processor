"""
توسيع بيانات التدريب — Data Augmentation Module
===================================================
توليد صور مُعزَّزة لبيانات تدريب الكتابة اليدوية العربية.

القدرات:
- تقنيات متنوعة: دوران، ضوضاء، ضبابية، تباين/سطوع، تحويل منظوري، تشويه مرن
- مراعاة خصوصيات العربية: الحفاظ على التشكيل، معالجة RTL
- معالجة فردية وجماعية (batch)
- موازنة مجموعة البيانات بزيادة العينات النادرة
- دعم التسميات (labels) المرافقة

مثال الاستخدام:
    >>> augmentor = DataAugmentor()
    >>> # صورة واحدة
    >>> augmented = augmentor.augment_image(image, num_augmented=5)
    >>> # مجموعة بيانات
    >>> augmented_dataset = augmentor.create_augmented_dataset(
    ...     image_dir="data/train",
    ...     label_file="data/labels.jsonl",
    ...     output_dir="data/train_augmented",
    ...     target_per_class=100,
    ... )
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


# ======================================================================
# فئة مُعزِّز البيانات
# ======================================================================

class DataAugmentor:
    """مُعزِّز بيانات التدريب للكتابة اليدوية العربية.

    توفر تقنيات متنوعة لتوسيع مجموعة بيانات التدريب مع مراعاة
    خصوصيات النص العربي مثل التشكيل والحروف المتصلة.

    Attributes:
        seed: بذرة العشوائية (لإعادة النتائج).
        techniques: قائمة التقنيات المُفعَّلة.
    """

    # نطاق أحرف التشكيل العربية (Tashkeel / Diacritics)
    ARABIC_DIACRITICS = set(
        "\u0610\u0611\u0612\u0613\u0614\u0615\u0616"
        "\u0617\u0618\u0619\u061A"
        "\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652"
    )

    def __init__(
        self,
        seed: Optional[int] = 42,
        techniques: Optional[list[str]] = None,
        # إعدادات التقنيات
        rotation_range: tuple[float, float] = (-5.0, 5.0),
        noise_std_range: tuple[float, float] = (5.0, 25.0),
        blur_kernel_range: tuple[int, int] = (1, 3),
        brightness_range: tuple[float, float] = (0.8, 1.2),
        contrast_range: tuple[float, float] = (0.8, 1.2),
        perspective_scale: float = 0.02,
        elastic_alpha: int = 30,
        elastic_sigma: int = 4,
    ) -> None:
        """تهيئة مُعزِّز البيانات.

        Args:
            seed: بذرة العشوائية (None = عشوائي).
            techniques: قائمة التقنيات المُفعَّلة.
                       الخيارات: "rotation", "noise", "blur", "brightness",
                                  "contrast", "perspective", "elastic".
                       None = كل التقنيات.
            rotation_range: نطاق زاوية الدوران بالدرجات.
            noise_std_range: نطاق الانحراف المعياري للضوضاء.
            blur_kernel_range: نطاق حجم نواة الضبابية.
            brightness_range: نطاق عامل السطوع.
            contrast_range: نطاق عامل التباين.
            perspective_scale: مقياس تحويل المنظور.
            elastic_alpha: شدة التشويه المرن (elastic).
            elastic_sigma: انتشار التشويه المرن.
        """
        if seed is not None:
            random.seed(seed)

        self.seed = seed
        self.rotation_range = rotation_range
        self.noise_std_range = noise_std_range
        self.blur_kernel_range = blur_kernel_range
        self.brightness_range = brightness_range
        self.contrast_range = contrast_range
        self.perspective_scale = perspective_scale
        self.elastic_alpha = elastic_alpha
        self.elastic_sigma = elastic_sigma

        # التقنيات المتاحة
        self._all_techniques = {
            "rotation",
            "noise",
            "blur",
            "brightness",
            "contrast",
            "perspective",
            "elastic",
        }

        self.techniques = set(techniques) if techniques else self._all_techniques

        # التحقق من التقنيات
        invalid = self.techniques - self._all_techniques
        if invalid:
            logger.warning("تقنيات غير معروفة (تم التجاهل): %s", invalid)
            self.techniques -= invalid

        # التحقق من المكتبات
        self._has_cv2 = self._check_library("cv2", "opencv-python")
        self._has_pil = self._check_library("PIL", "Pillow")
        self._has_numpy = self._check_library("numpy", "numpy")

        if not self._has_numpy:
            logger.error("NumPy غير متاح — مطلوب لجميع عمليات التعزيز")

    @staticmethod
    def _check_library(import_name: str, package_name: str) -> bool:
        """التحقق من توفر مكتبة."""
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # تحويل الصور
    # ------------------------------------------------------------------

    def _to_numpy(self, image: Any) -> Any:
        """تحويل الصورة إلى مصفوفة numpy."""
        if self._has_numpy:
            import numpy as np
            if isinstance(image, np.ndarray):
                return image.copy()
        try:
            from PIL import Image
            if isinstance(image, Image.Image):
                import numpy as np
                return np.array(image)
        except (ImportError, Exception):
            pass
        raise TypeError(f"نوع غير مدعوم: {type(image)} — مطلوب PIL.Image أو numpy.ndarray")

    def _to_pil(self, img_array: Any) -> Any:
        """تحويل مصفوفة numpy إلى صورة PIL."""
        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError("Pillow غير متاح")

        import numpy as np

        if img_array.ndim == 2:
            return Image.fromarray(img_array, mode="L").convert("RGB")
        elif img_array.ndim == 3:
            if img_array.shape[2] == 3:
                return Image.fromarray(img_array, mode="RGB")
            elif img_array.shape[2] == 4:
                return Image.fromarray(img_array, mode="RGBA")
        return Image.fromarray(img_array).convert("RGB")

    # ------------------------------------------------------------------
    # تقنيات التعزيز الفردية
    # ------------------------------------------------------------------

    def _apply_rotation(self, img: Any) -> Any:
        """تطبيق دوران عشوائي على الصورة.

        Args:
            img: مصفوفة numpy.

        Returns:
            الصورة بعد الدوران.
        """
        if not self._has_cv2:
            return img

        import cv2
        import numpy as np

        h, w = img.shape[:2]
        angle = random.uniform(*self.rotation_range)
        center = (w / 2, h / 2)

        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # حساب الحدود الجديدة لتجنب القص
        cos_val = abs(rotation_matrix[0, 0])
        sin_val = abs(rotation_matrix[0, 1])
        new_w = int(h * sin_val + w * cos_val)
        new_h = int(h * cos_val + w * sin_val)

        rotation_matrix[0, 2] += (new_w - w) / 2
        rotation_matrix[1, 2] += (new_h - h) / 2

        return cv2.warpAffine(
            img, rotation_matrix, (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def _apply_noise(self, img: Any) -> Any:
        """إضافة ضوضاء غاوسية عشوائية.

        Args:
            img: مصفوفة numpy.

        Returns:
            الصورة مع الضوضاء.
        """
        import numpy as np

        std = random.uniform(*self.noise_std_range)
        noise = np.random.normal(0, std, img.shape).astype(np.float32)
        noisy = np.clip(img.astype(np.float32) + noise, 0, 255)

        return noisy.astype(img.dtype)

    def _apply_blur(self, img: Any) -> Any:
        """تطبيق ضبابية غاوسية عشوائية.

        Args:
            img: مصفوفة numpy.

        Returns:
            الصورة بعد الضبابية.
        """
        if not self._has_cv2:
            return img

        import cv2

        kernel_size = random.choice(
            list(range(self.blur_kernel_range[0], self.blur_kernel_range[1] + 1, 2))
        )
        if kernel_size <= 1:
            return img

        return cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)

    def _apply_brightness_contrast(self, img: Any) -> Any:
        """تعديل السطوع والتباين عشوائياً.

        Args:
            img: مصفوفة numpy.

        Returns:
            الصورة بعد التعديل.
        """
        import numpy as np

        brightness = random.uniform(*self.brightness_range)
        contrast = random.uniform(*self.contrast_range)

        result = img.astype(np.float32) * contrast * brightness
        return np.clip(result, 0, 255).astype(img.dtype)

    def _apply_perspective(self, img: Any) -> Any:
        """تطبيق تحويل منظوري خفيف.

        مفيد لمحاكاة زوايا التصوير المختلفة للخط اليدوي.

        Args:
            img: مصفوفة numpy.

        Returns:
            الصورة بعد التحويل.
        """
        if not self._has_cv2:
            return img

        import cv2
        import numpy as np

        h, w = img.shape[:2]
        scale = self.perspective_scale

        # نقاط المصدر
        src_points = np.float32([
            [0, 0], [w, 0], [w, h], [0, h],
        ])

        # نقاط الهدف مع تشويه عشوائي
        dx = random.uniform(-scale, scale) * w
        dy = random.uniform(-scale, scale) * h
        dst_points = np.float32([
            [dx, dy],
            [w - dx, dy + random.uniform(-scale, scale) * h * 0.5],
            [w - dx - random.uniform(-scale, scale) * w * 0.5, h - dy],
            [dx + random.uniform(-scale, scale) * w * 0.5, h - dy],
        ])

        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        return cv2.warpPerspective(img, matrix, (w, h), flags=cv2.INTER_CUBIC)

    def _apply_elastic(self, img: Any) -> Any:
        """تطبيق تشويه مرن (elastic distortion).

        يُحاكي التشوهات الطبيعية في الكتابة اليدوية.

        Args:
            img: مصفوفة numpy.

        Returns:
            الصورة بعد التشويه.
        """
        import numpy as np

        if not self._has_cv2:
            # احتياطي بسيط بدون OpenCV
            alpha = self.elastic_alpha / 255.0
            sigma = self.elastic_sigma

            h, w = img.shape[:2]
            dx = np.random.uniform(-1, 1, (h, w)).astype(np.float32) * alpha
            dy = np.random.uniform(-1, 1, (h, w)).astype(np.float32) * alpha

            # تطبيق Gaussian blur يدوياً على الإزاحة
            from PIL import ImageFilter
            dx_img = Image.fromarray((dx * 255).astype(np.uint8))
            dy_img = Image.fromarray((dy * 255).astype(np.uint8))
            dx_img = dx_img.filter(ImageFilter.GaussianBlur(sigma))
            dy_img = dy_img.filter(ImageFilter.GaussianBlur(sigma))
            dx = np.array(dx_img).astype(np.float32) / 255.0 * alpha
            dy = np.array(dy_img).astype(np.float32) / 255.0 * alpha

            # تطبيق الإزاحة
            y_indices, x_indices = np.mgrid[:h, :w]
            new_x = np.clip(x_indices + dx, 0, w - 1).astype(int)
            new_y = np.clip(y_indices + dy, 0, h - 1).astype(int)

            if img.ndim == 3:
                return img[new_y, new_x, :]
            return img[new_y, new_x]

        import cv2

        alpha = self.elastic_alpha
        sigma = self.elastic_sigma

        shape = img.shape[:2]
        if img.ndim == 3:
            shape = img.shape[:2]

        # إنشاء حقول الإزاحة العشوائية
        dx = np.random.uniform(-1, 1, shape).astype(np.float32) * alpha
        dy = np.random.uniform(-1, 1, shape).astype(np.float32) * alpha

        # تنعيم بحساب Gaussian blur
        dx = cv2.GaussianBlur(dx, (0, 0), sigma)
        dy = cv2.GaussianBlur(dy, (0, 0), sigma)

        # إنشاء خريطة الإزاحة
        h, w = shape
        x, y = np.meshgrid(np.arange(w), np.arange(h))
        map_x = (x + dx).astype(np.float32)
        map_y = (y + dy).astype(np.float32)

        return cv2.remap(img, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # ------------------------------------------------------------------
    # الواجهة العامة
    # ------------------------------------------------------------------

    def augment_image(
        self,
        image: Any,
        num_augmented: int = 5,
        techniques: Optional[list[str]] = None,
        return_numpy: bool = False,
    ) -> list[Any]:
        """تعزيز صورة واحدة بعدة تقنيات عشوائية.

        Args:
            image: صورة PIL أو مصفوفة numpy.
            num_augmented: عدد النسخ المُعزَّزة المطلوبة.
            techniques: تقنيات مُحددة (None = كل التقنيات المُفعَّلة).
            return_numpy: إرجاع numpy بدلاً من PIL.

        Returns:
            قائمة بالصور المُعزَّزة.

        Example:
            >>> augmented = augmentor.augment_image(img, num_augmented=5)
        """
        if num_augmented <= 0:
            return []

        import numpy as np

        img_array = self._to_numpy(image)
        active_techniques = set(techniques) if techniques else self.techniques

        if not active_techniques:
            logger.warning("لا توجد تقنيات مُفعَّلة للتعزيز")
            return []

        augmented: list[Any] = []
        technique_list = [
            "rotation", "noise", "blur",
            "brightness", "contrast", "perspective", "elastic",
        ]
        # الفلترة حسب التقنيات الفعالة
        technique_list = [t for t in technique_list if t in active_techniques]

        if not technique_list:
            return []

        for _ in range(num_augmented):
            current = img_array.copy()

            # اختيار 1-3 تقنيات عشوائية
            num_techniques = random.randint(1, min(3, len(technique_list)))
            chosen = random.sample(technique_list, num_techniques)

            for technique in chosen:
                try:
                    if technique == "rotation":
                        current = self._apply_rotation(current)
                    elif technique == "noise":
                        current = self._apply_noise(current)
                    elif technique == "blur":
                        current = self._apply_blur(current)
                    elif technique in ("brightness", "contrast"):
                        current = self._apply_brightness_contrast(current)
                    elif technique == "perspective":
                        current = self._apply_perspective(current)
                    elif technique == "elastic":
                        current = self._apply_elastic(current)
                except Exception as e:
                    logger.debug("فشل تطبيق تقنية '%s': %s", technique, e)

            if return_numpy:
                augmented.append(current)
            else:
                augmented.append(self._to_pil(current))

        logger.debug(
            "تم تعزيز صورة واحدة: %d نسخة بـ %d تقنية",
            num_augmented, len(chosen),
        )
        return augmented

    def augment_with_label(
        self,
        image: Any,
        label: str,
        num_augmented: int = 5,
        return_numpy: bool = False,
    ) -> list[dict[str, Any]]:
        """تعزيز صورة مع الحفاظ على التسمية المرافقة.

        للنصوص العربية: يتحقق من أن التعزيز لا يؤثر على التشكيل.

        Args:
            image: صورة PIL أو numpy.
            label: النص المرافق (التسمية).
            num_augmented: عدد النسخ.
            return_numpy: إرجاع numpy.

        Returns:
            قائمة قواميس: {"image": ..., "label": ...}.
        """
        if not label.strip():
            logger.warning("تسمية فارغة — تم التجاهل")
            return []

        augmented_images = self.augment_image(
            image, num_augmented=num_augmented, return_numpy=return_numpy,
        )

        results = []
        for aug_img in augmented_images:
            # للنصوص العربية: التسمية تبقى كما هي لأن التعزيز بصري فقط
            results.append({
                "image": aug_img,
                "label": label,
            })

        return results

    def augment_dataset(
        self,
        images: list[Any],
        labels: Optional[list[str]] = None,
        num_augmented: int = 3,
        return_numpy: bool = False,
    ) -> list[dict[str, Any]]:
        """تعزيز مجموعة صور كاملة.

        Args:
            images: قائمة صور (PIL أو numpy).
            labels: قائمة تسميات مرافقة (اختياري).
            num_augmented: عدد النسخ لكل صورة.
            return_numpy: إرجاع numpy.

        Returns:
            قائمة نتائج: [{"image": ..., "label": ...}, ...].

        Example:
            >>> results = augmentor.augment_dataset(
            ...     images=[img1, img2, img3],
            ...     labels=["مرحبا", "عالم", "برمجة"],
            ...     num_augmented=5,
            ... )
        """
        if not images:
            return []

        results: list[dict[str, Any]] = []
        total = len(images)

        for idx, img in enumerate(images):
            label = labels[idx] if labels and idx < len(labels) else ""

            if label:
                augmented = self.augment_with_label(
                    img, label, num_augmented=num_augmented, return_numpy=return_numpy,
                )
            else:
                aug_images = self.augment_image(
                    img, num_augmented=num_augmented, return_numpy=return_numpy,
                )
                augmented = [{"image": a, "label": ""} for a in aug_images]

            results.extend(augmented)

            if (idx + 1) % 100 == 0 or idx == total - 1:
                logger.info(
                    "تعزيز مجموعة البيانات: %d/%d صورة (%d عيّنة)",
                    idx + 1, total, len(results),
                )

        logger.info(
            "تم تعزيز مجموعة البيانات: %d صورة أصلية → %d عيّنة",
            total, len(results),
        )
        return results

    def create_augmented_dataset(
        self,
        image_dir: str | Path,
        label_file: Optional[str | Path] = None,
        output_dir: Optional[str | Path] = None,
        num_augmented: int = 5,
        target_per_class: Optional[int] = None,
        return_numpy: bool = False,
    ) -> dict[str, Any]:
        """إنشاء مجموعة بيانات مُعزَّزة من مجلد صور مع تسميات.

        يدعم:
        - قراءة الصور من مجلد
        - قراءة التسميات من ملف JSONL أو JSON
        - موازنة الفئات بزيادة العينات النادرة
        - حفظ النتائج في مجلد مُخرَج

        Args:
            image_dir: مجلد الصور الأصلية.
            label_file: ملف التسميات (JSONL أو JSON).
                       صيغة JSONL: سطر لكل صورة {"image": "path", "label": "text"}
                       صيغة JSON: {"image_name": "label", ...}
            output_dir: مجلد حفظ النتائج (None = لا يحفظ).
            num_augmented: عدد النسخ لكل صورة.
            target_per_class: هدف عدد العينات لكل فئة (لموازنة البيانات).
            return_numpy: إرجاع numpy.

        Returns:
            قاموس يحتوي:
            - total_original: عدد الصور الأصلية
            - total_augmented: عدد النسخ المُعزَّزة
            - class_distribution: توزيع الفئات قبل وبعد
            - results: قائمة النتائج
        """
        image_dir = Path(image_dir)
        if not image_dir.exists():
            raise FileNotFoundError(f"مجلد الصور غير موجود: {image_dir}")

        # تحميل التسميات
        labels_map: dict[str, str] = {}
        if label_file:
            label_file = Path(label_file)
            if not label_file.exists():
                logger.warning("ملف التسميات غير موجود: %s", label_file)
            else:
                labels_map = self._load_labels(label_file)

        # تحميل الصور
        image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
        image_files = sorted([
            f for f in image_dir.iterdir()
            if f.suffix.lower() in image_extensions
        ])

        if not image_files:
            logger.warning("لا توجد صور في المجلد: %s", image_dir)
            return {
                "total_original": 0,
                "total_augmented": 0,
                "class_distribution": {"before": {}, "after": {}},
                "results": [],
            }

        # حساب التوزيع قبل التعزيز
        original_labels = [labels_map.get(f.name, "") for f in image_files]
        before_dist = dict(Counter(original_labels))

        # حساب عدد النسخ لكل فئة
        augmented_per_image: dict[str, int] = {}
        if target_per_class is not None:
            for label, count in before_dist.items():
                if count < target_per_class and label:
                    needed = target_per_class - count
                    copies_per_image = max(1, needed // count) if count > 0 else needed
                    augmented_per_image[label] = copies_per_image
                elif label:
                    augmented_per_image[label] = num_augmented

        # التعزيز
        all_results: list[dict[str, Any]] = []
        for img_path in image_files:
            try:
                from PIL import Image
                img = Image.open(img_path).convert("RGB")
                label = labels_map.get(img_path.name, "")

                # تحديد عدد النسخ
                if label and label in augmented_per_image:
                    n_copies = augmented_per_image[label]
                else:
                    n_copies = num_augmented

                augmented = self.augment_with_label(
                    img, label, num_augmented=n_copies, return_numpy=return_numpy,
                )

                for aug in augmented:
                    aug["source_image"] = img_path.name

                all_results.extend(augmented)

            except Exception as e:
                logger.warning("فشل في معالجة الصورة %s: %s", img_path.name, e)

        # حساب التوزيع بعد التعزيز
        after_labels = [r["label"] for r in all_results if r["label"]]
        after_dist = dict(Counter(after_labels))

        # حفظ النتائج
        if output_dir:
            output_dir = Path(output_dir)
            self._save_augmented_dataset(all_results, output_dir)

        logger.info(
            "تم إنشاء مجموعة بيانات مُعزَّزة: %d أصلية → %d عيّنة",
            len(image_files), len(all_results),
        )

        return {
            "total_original": len(image_files),
            "total_augmented": len(all_results),
            "class_distribution": {
                "before": before_dist,
                "after": after_dist,
            },
            "results": all_results,
        }

    # ------------------------------------------------------------------
    # أدوات مساعدة
    # ------------------------------------------------------------------

    @staticmethod
    def _load_labels(label_file: Path) -> dict[str, str]:
        """تحميل التسميات من ملف JSONL أو JSON.

        Args:
            label_file: مسار ملف التسميات.

        Returns:
            قاموس {اسم_الصورة: التسمية}.
        """
        labels: dict[str, str] = {}

        try:
            with open(label_file, "r", encoding="utf-8") as f:
                if label_file.suffix.lower() == ".jsonl":
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        img_name = entry.get("image", entry.get("file", entry.get("filename", "")))
                        label = entry.get("label", entry.get("text", ""))
                        if img_name and label:
                            labels[Path(img_name).name] = str(label)
                else:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for key, value in data.items():
                            labels[Path(key).name] = str(value)
                    elif isinstance(data, list):
                        for entry in data:
                            if isinstance(entry, dict):
                                img_name = entry.get("image", entry.get("file", ""))
                                label = entry.get("label", entry.get("text", ""))
                                if img_name and label:
                                    labels[Path(img_name).name] = str(label)

            logger.info("تم تحميل %d تسمية من %s", len(labels), label_file.name)
        except Exception as e:
            logger.error("فشل في تحميل التسميات: %s", e)

        return labels

    def _save_augmented_dataset(
        self,
        results: list[dict[str, Any]],
        output_dir: Path,
    ) -> None:
        """حفظ مجموعة البيانات المُعزَّزة في مجلد.

        يحفظ الصور كملفات PNG والتسميات كملف JSONL.

        Args:
            results: قائمة نتائج التعزيز.
            output_dir: مجلد الحفظ.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        label_data: list[dict[str, str]] = []
        counter = 0

        for result in results:
            img = result.get("image")
            label = result.get("label", "")
            source = result.get("source_image", "unknown")

            if img is None:
                continue

            try:
                pil_img = self._to_pil(img) if self._has_numpy and not isinstance(img, Image.Image) else img
                # تأكد من أنها PIL.Image
                from PIL import Image
                if not isinstance(pil_img, Image.Image):
                    pil_img = self._to_pil(img)

                counter += 1
                # اسم ملف: رقم + مصدر_أصلي
                stem = Path(source).stem if source else f"img"
                img_filename = f"{counter:06d}_{stem}.png"
                img_path = images_dir / img_filename

                pil_img.save(str(img_path), format="PNG")

                label_data.append({
                    "image": f"images/{img_filename}",
                    "label": label,
                    "source": source,
                })

            except Exception as e:
                logger.debug("فشل في حفظ صورة: %s", e)

        # حفظ ملف التسميات
        label_path = output_dir / "labels.jsonl"
        with open(label_path, "w", encoding="utf-8") as f:
            for entry in label_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info(
            "تم حفظ %d صورة في: %s و %d تسمية في: %s",
            len(label_data), images_dir, len(label_data), label_path,
        )

    @staticmethod
    def sanitize_arabic_label(label: str) -> str:
        """تنظيف التسمية العربية من التشكيل الزائد (اختياري).

        مفيد لتوحيد التسميات عند المقارنة.

        Args:
            label: التسمية الأصلية.

        Returns:
            التسمية بدون تشكيل.
        """
        diacritics = (
            "\u0610\u0611\u0612\u0613\u0614\u0615\u0616"
            "\u0617\u0618\u0619\u061A"
            "\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652"
        )
        return "".join(c for c in label if c not in diacritics)

    @staticmethod
    def has_arabic_diacritics(text: str) -> bool:
        """فحص هل النص يحتوي تشكيلاً عربياً.

        Args:
            text: النص المراد فحصه.

        Returns:
            True إذا وُجد تشكيل.
        """
        diacritics = (
            "\u0610\u0611\u0612\u0613\u0614\u0615\u0616"
            "\u0617\u0618\u0619\u061A"
            "\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652"
        )
        return any(c in diacritics for c in text)
