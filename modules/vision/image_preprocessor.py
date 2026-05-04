"""
معالج الصور المسبق
====================
تحضير الصور لمحركات التعرف على النصوص (OCR) عبر سلسلة خطوات معالجة.

القدرات:
- تحسين التباين باستخدام CLAHE
- إزالة الضوضاء (Denoising)
- تصحيح الميل (Deskewing)
- ثنائنة أوتسو (Otsu Binarization)
- التوسع (Dilation) لتجزئة الكلمات
- تجزئة ذكية للصور إلى كلمات

ملاحظة: المكتبات مطلوبة هي opencv-python و Pillow
"""

import logging
from typing import Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    معالج الصور المسبق - يحسن جودة الصور قبل تمريرها لمحرك OCR.

    مثال الاستخدام:
        >>> preprocessor = ImagePreprocessor(
        ...     clahe_clip_limit=2.0,
        ...     denoise_strength=10,
        ...     apply_deskew=True,
        ... )
        >>> from PIL import Image
        >>> img = Image.open("handwriting.png")
        >>> processed = preprocessor.preprocess(img)
        >>> words = preprocessor.smart_segment(img)
    """

    def __init__(
        self,
        # إعدادات CLAHE
        apply_clahe: bool = True,
        clahe_clip_limit: float = 2.0,
        clahe_tile_size: tuple[int, int] = (8, 8),
        # إعدادات إزالة الضوضاء
        apply_denoise: bool = True,
        denoise_strength: int = 10,
        denoise_template_window: int = 7,
        denoise_search_window: int = 21,
        # إعدادات تصحيح الميل
        apply_deskew: bool = True,
        deskew_angle_threshold: float = 5.0,
        # إعدادات الثنائنة
        apply_binarize: bool = True,
        # إعدادات التوسع
        apply_dilate: bool = False,
        dilate_kernel_size: tuple[int, int] = (2, 2),
        dilate_iterations: int = 1,
        # إعدادات عامة
        target_size: Optional[tuple[int, int]] = None,
        convert_to_grayscale: bool = True,
    ) -> None:
        """
        تهيئة معالج الصور.

        Args:
            apply_clahe: تفعيل تحسين التباين CLAHE
            clahe_clip_limit: حد القص لـ CLAHE (الافتراضي 2.0)
            clahe_tile_size: حجم البلاط لـ CLAHE (الافتراضي 8×8)
            apply_denoise: تفعيل إزالة الضوضاء
            denoise_strength: قوة إزالة الضوضاء (1-20، الافتراضي 10)
            denoise_template_window: حجم نافذة القالب (يجب أن يكون فردياً)
            denoise_search_window: حجم نافذة البحث (يجب أن يكون فردياً)
            apply_deskew: تفعيل تصحيح الميل
            deskew_angle_threshold: زاوية الميل المقبولة بالدرجات
            apply_binarize: تفعيل ثنائنة أوتسو
            apply_dilate: تفعيل التوسع (مفيد لتجزئة الكلمات)
            dilate_kernel_size: حجم نواة التوسع
            dilate_iterations: عدد تكرارات التوسع
            target_size: الحجم المستهدف (عرض، ارتفاع) أو None للحفاظ على الأصل
            convert_to_grayscale: تحويل إلى تدرج رمادي
        """
        self.apply_clahe = apply_clahe
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_tile_size = clahe_tile_size

        self.apply_denoise = apply_denoise
        self.denoise_strength = denoise_strength
        self.denoise_template_window = max(1, denoise_template_window | 1)  # التأكد من أنه فردي
        self.denoise_search_window = max(1, denoise_search_window | 1)

        self.apply_deskew = apply_deskew
        self.deskew_angle_threshold = deskew_angle_threshold

        self.apply_binarize = apply_binarize

        self.apply_dilate = apply_dilate
        self.dilate_kernel_size = dilate_kernel_size
        self.dilate_iterations = dilate_iterations

        self.target_size = target_size
        self.convert_to_grayscale = convert_to_grayscale

        # التحقق من توفر المكتبات
        self._has_cv2 = self._check_library("cv2", "opencv-python")
        self._has_pil = self._check_library("PIL", "Pillow")

        if not self._has_cv2:
            logger.warning(
                "OpenCV غير مثبت. لن تعمل معالجة الصور بشكل كامل. "
                "قم بالتثبيت: pip install opencv-python"
            )

    @staticmethod
    def _check_library(import_name: str, package_name: str) -> bool:
        """التحقق من توفر مكتبة."""
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # الأساليب العامة (Public API)
    # ------------------------------------------------------------------

    def preprocess(
        self,
        image: Union["np.ndarray", "PIL.Image.Image"],
        return_numpy: bool = False,
    ) -> Union["np.ndarray", "PIL.Image.Image"]:
        """
        تطبيق سلسلة المعالجة المسبقة الكاملة على الصورة.

        الترتيب:
        1. تحويل إلى تدرج رمادي
        2. تغيير الحجم (اختياري)
        3. تحسين التباين (CLAHE)
        4. إزالة الضوضاء
        5. تصحيح الميل
        6. الثنائنة (Otsu)
        7. التوسع (اختياري)

        Args:
            image: صورة PIL أو مصفوفة numpy
            return_numpy: إرجاع مصفوفة numpy بدلاً من PIL Image

        Returns:
            الصورة المعالجة (PIL Image أو numpy array)
        """
        # التحويل إلى numpy
        img_array = self._to_numpy(image)

        # 1. تحويل إلى تدرج رمادي عند الحاجة فقط
        needs_grayscale = (
            self.convert_to_grayscale
            and img_array.ndim == 3
            and (
                self.apply_clahe
                or self.apply_denoise
                or self.apply_deskew
                or self.apply_binarize
                or self.apply_dilate
            )
        )
        if needs_grayscale:
            img_array = self._to_grayscale(img_array)

        # 2. تغيير الحجم
        if self.target_size is not None:
            img_array = self._resize(img_array, self.target_size)

        # 3. تحسين التباين CLAHE
        if self.apply_clahe:
            img_array = self._apply_clahe(img_array)

        # 4. إزالة الضوضاء
        if self.apply_denoise:
            img_array = self._apply_denoise(img_array)

        # 5. تصحيح الميل
        if self.apply_deskew:
            img_array = self._apply_deskew(img_array)

        # 6. الثنائنة (Otsu)
        if self.apply_binarize:
            img_array = self._apply_otsu(img_array)

        # 7. التوسع
        if self.apply_dilate:
            img_array = self._apply_dilate(img_array)

        # إرجاع النتيجة
        if return_numpy:
            return img_array
        else:
            return self._to_pil(img_array)

    def smart_segment(
        self,
        image: Union["np.ndarray", "PIL.Image.Image"],
        min_word_area: int = 100,
        padding: int = 5,
    ) -> list["PIL.Image.Image"]:
        """
        تجزئة الصورة إلى صور كلمات فردية.

        يستخدم كشف الحواف والمحيطات لفصل الكلمات.

        Args:
            image: صورة PIL أو مصفوفة numpy
            min_word_area: الحد الأدنى لمساحة الكلمة بالبكسل
            padding: حشوة إضافية حول كل كلمة

        Returns:
            قائمة صور PIL لكل كلمة
        """
        if not self._has_cv2:
            logger.warning("OpenCV غير متاح - لا يمكن تجزئة الصورة")
            return []

        try:
            import cv2
            from PIL import Image

            img_array = self._to_numpy(image)

            # التأكد من تدرج رمادي
            if img_array.ndim == 3:
                gray = self._to_grayscale(img_array)
            else:
                gray = img_array.copy()

            # ثنائنة
            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

            # توسع خفيف لربط أجزاء الكلمة
            kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT, (3, 3)
            )
            dilated = cv2.dilate(binary, kernel, iterations=1)

            # كشف المحيطات
            contours, _ = cv2.findContours(
                dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            word_images: list[Image.Image] = []
            img_h, img_w = gray.shape

            # فرز المحيطات من اليسار لليمين
            bounding_boxes = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                if area >= min_word_area:
                    bounding_boxes.append((x, y, w, h, area))

            # ترتيب حسب الموقع (أولاً حسب Y ثم حسب X)
            bounding_boxes.sort(key=lambda b: (b[1] // 20, b[0]))

            for x, y, w, h, _ in bounding_boxes:
                # حساب الحشوة مع مراعاة حدود الصورة
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(img_w, x + w + padding)
                y2 = min(img_h, y + h + padding)

                word_crop = gray[y1:y2, x1:x2]
                word_pil = Image.fromarray(word_crop).convert("RGB")
                word_images.append(word_pil)

            logger.debug(
                "تم تجزئة الصورة إلى %d كلمة", len(word_images)
            )
            return word_images

        except Exception as e:
            logger.error("فشل في تجزئة الصورة: %s", e)
            return []

    def get_word_bounding_boxes(
        self,
        image: Union["np.ndarray", "PIL.Image.Image"],
        min_word_area: int = 100,
        padding: int = 5,
    ) -> list[dict]:
        """
        استخراج مربعات إحاطة الكلمات مع مواقعها.

        مفيد للخطوات التالية في إعادة تجميع النصوص.

        Args:
            image: صورة PIL أو مصفوفة numpy
            min_word_area: الحد الأدنى لمساحة الكلمة
            padding: حشوة إضافية

        Returns:
            قائمة قواميس: {bbox: (x, y, w, h), center: (cx, cy)}
        """
        if not self._has_cv2:
            return []

        try:
            import cv2

            img_array = self._to_numpy(image)
            if img_array.ndim == 3:
                gray = self._to_grayscale(img_array)
            else:
                gray = img_array.copy()

            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            dilated = cv2.dilate(binary, kernel, iterations=1)

            contours, _ = cv2.findContours(
                dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            boxes: list[dict] = []
            img_h, img_w = gray.shape

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                if area >= min_word_area:
                    cx = x + w // 2
                    cy = y + h // 2
                    boxes.append({
                        "bbox": (x, y, w, h),
                        "center": (cx, cy),
                        "area": area,
                    })

            # ترتيب حسب الموقع
            boxes.sort(key=lambda b: (b["center"][1] // 20, b["center"][0]))
            return boxes

        except Exception as e:
            logger.error("فشل في استخراج مربعات الإحاطة: %s", e)
            return []

    # ------------------------------------------------------------------
    # أساليب المعالجة الفردية
    # ------------------------------------------------------------------

    def _apply_clahe(self, gray: np.ndarray) -> np.ndarray:
        """
        تحسين التباين باستخدام خوارزمية CLAHE.

        CLAHE = Contrast Limited Adaptive Histogram Equalization
        مفيدة جداً للمخطوطات والنصوص ذات الإضاءة غير المتساوية.
        """
        if not self._has_cv2:
            return gray

        try:
            import cv2

            clahe = cv2.createCLAHE(
                clipLimit=self.clahe_clip_limit,
                tileGridSize=self.clahe_tile_size,
            )
            return clahe.apply(gray)
        except Exception as e:
            logger.warning("فشل في تطبيق CLAHE: %s", e)
            return gray

    def _apply_denoise(self, gray: np.ndarray) -> np.ndarray:
        """
        إزالة الضوضاء باستخدام خوارزمية fastNlMeansDenoising.

        تعمل فقط على الصور ذات التدرج الرمادي.
        """
        if not self._has_cv2:
            return gray

        try:
            import cv2

            strength = max(1, min(30, self.denoise_strength))
            return cv2.fastNlMeansDenoising(
                gray,
                None,
                h=strength,
                templateWindowSize=self.denoise_template_window,
                searchWindowSize=self.denoise_search_window,
            )
        except Exception as e:
            logger.warning("فشل في إزالة الضوضاء: %s", e)
            return gray

    def _apply_deskew(self, gray: np.ndarray) -> np.ndarray:
        """
        تصحيح ميل النص في الصورة.

        يكتشف زاوية الميل باستخدام تحويل Hough ويصححها.
        """
        if not self._has_cv2:
            return gray

        try:
            import cv2

            # ثنائنة
            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

            # تحويل Hough لكشف الخطوط
            edges = cv2.Canny(binary, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=100,
                minLineLength=gray.shape[1] // 4,
                maxLineGap=20,
            )

            if lines is None:
                return gray

            # حساب زاوية الميل المتوسطة
            angles: list[float] = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 - x1 == 0:
                    continue
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                # فقط الزوايا الصغيرة (نص مائل، وليس خطوط عمودية)
                if abs(angle) < self.deskew_angle_threshold:
                    angles.append(angle)

            if not angles:
                return gray

            median_angle = float(np.median(angles))
            logger.debug("زاوية الميل المكتشفة: %.2f درجة", median_angle)

            # تصحيح الميل
            if abs(median_angle) > 0.1:
                h, w = gray.shape
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                rotated = cv2.warpAffine(
                    gray, rotation_matrix, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )
                return rotated

            return gray

        except Exception as e:
            logger.warning("فشل في تصحيح الميل: %s", e)
            return gray

    def _apply_otsu(self, gray: np.ndarray) -> np.ndarray:
        """
        تحويل الصورة إلى صورة ثنائية باستخدام طريقة أوتسو.

        مفيد جداً لـ OCR حيث يحول الصورة إلى أبيض وأسود فقط.
        """
        if not self._has_cv2:
            return gray

        try:
            import cv2

            # التأكد من أن القيم 0-255
            if gray.dtype != np.uint8:
                gray = np.clip(gray, 0, 255).astype(np.uint8)

            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            return binary
        except Exception as e:
            logger.warning("فشل في تطبيق ثنائنة أوتسو: %s", e)
            return gray

    def _apply_dilate(self, gray: np.ndarray) -> np.ndarray:
        """
        تطبيق التوسع على الصورة الثنائية.

        مفيد لتجزئة الكلمات الملتصقة.
        """
        if not self._has_cv2:
            return gray

        try:
            import cv2

            kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT, self.dilate_kernel_size
            )
            dilated = cv2.dilate(
                gray, kernel, iterations=self.dilate_iterations
            )
            return dilated
        except Exception as e:
            logger.warning("فشل في تطبيق التوسع: %s", e)
            return gray

    # ------------------------------------------------------------------
    # أدوات التحويل
    # ------------------------------------------------------------------

    @staticmethod
    def _to_numpy(image: Union[np.ndarray, "PIL.Image.Image"]) -> np.ndarray:
        """تحويل أي صورة إلى مصفوفة numpy."""
        if isinstance(image, np.ndarray):
            return image.copy()
        try:
            from PIL import Image
            if isinstance(image, Image.Image):
                return np.array(image)
        except ImportError:
            pass
        raise TypeError(f"نوع غير مدعوم: {type(image)} - مطلوب PIL.Image أو numpy.ndarray")

    def _to_grayscale(self, img_array: np.ndarray) -> np.ndarray:
        """تحويل مصفوفة ألوان إلى تدرج رمادي."""
        if not self._has_cv2:
            # استخدام PIL كاحتياطي
            try:
                from PIL import Image
                pil_img = Image.fromarray(img_array)
                return np.array(pil_img.convert("L"))
            except Exception:
                # احتياطي بسيط: المتوسط المرجح
                if img_array.ndim == 3:
                    return np.dot(img_array[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)

        try:
            import cv2
            return cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        except Exception:
            if img_array.ndim == 3:
                return np.dot(img_array[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)
            return img_array

    @staticmethod
    def _to_pil(img_array: np.ndarray) -> "PIL.Image.Image":
        """تحويل مصفوفة numpy إلى صورة PIL."""
        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError("Pillow غير مثبت")

        if img_array.ndim == 2:
            return Image.fromarray(img_array, mode="L").convert("RGB")
        elif img_array.ndim == 3:
            if img_array.shape[2] == 4:
                return Image.fromarray(img_array, mode="RGBA")
            elif img_array.shape[2] == 3:
                return Image.fromarray(img_array, mode="RGB")
            else:
                return Image.fromarray(img_array[:, :, 0], mode="L").convert("RGB")
        else:
            return Image.fromarray(img_array).convert("RGB")

    @staticmethod
    def _resize(img_array: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
        """تغيير حجم مصفوفة الصورة."""
        try:
            from PIL import Image
            pil_img = Image.fromarray(img_array)
            pil_img = pil_img.resize(target_size, Image.LANCZOS)
            return np.array(pil_img)
        except Exception as e:
            logger.warning("فشل في تغيير الحجم: %s", e)
            return img_array
