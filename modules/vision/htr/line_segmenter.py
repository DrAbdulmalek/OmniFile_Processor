"""
تجزئة الأسطر (Line Segmentation).

يوفر ثلاث استراتيجيات لتقسيم صورة المستند إلى أسطر نصّية:
  - ProjectionProfileSegmenter: تحليل المسقط الأفقي.
  - UNetLineSegmenter: شبكة U-Net للكشف عن الأسطر على مستوى البكسل.
  - ContourLineSegmenter: التحليل المورفولوجي + كشف المحيطات.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------- الأنواع ----------
LineSegment = Tuple["PIL.Image.Image", Dict[str, Any]]


def _ensure_gray(image) -> "np.ndarray":
    """تحويل المدخل إلى مصفوفة NumPy رمادية (H, W).

    Args:
        image: كائن PIL.Image أو مصفوفة NumPy.

    Returns:
        مصفوفة NumPy أحادية القناة (uint8).
    """
    import PIL.Image

    if isinstance(image, np.ndarray):
        if image.ndim == 3:
            import cv2

            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
    elif isinstance(image, PIL.Image.Image):
        gray = np.array(image.convert("L"))
    else:
        raise TypeError(f"نوع المدخل غير مدعوم: {type(image)}")
    return gray.astype(np.uint8)


def _to_binary(gray: np.ndarray, threshold: int = 127) -> np.ndarray:
    """تحويل الصورة الرمادية إلى صورة ثنائية (نصّ=أبيض، خلفية=سوداء).

    Args:
        gray: مصفوفة رمادية.
        threshold: عتبة التحويل.

    Returns:
        مصفوفة ثنائية (uint8).
    """
    # افتراض: الخلفية فاتحة والنصّ داكن
    binary = np.zeros_like(gray)
    binary[gray < threshold] = 255
    return binary


# ============================================================
# BaseLineSegmenter — الفئة الأساسية المجردة
# ============================================================
class BaseLineSegmenter(ABC):
    """الواجهة الأساسية لمُجزِّئات الأسطر.

    يجب أن تُنفِّذ الفئات الفرعية الطريقتين:
      - segment(): إرجاع قائمة بصور الأسطر فقط.
      - segment_with_info(): إرجاع صور الأسطر مع البيانات الوصفية.
    """

    @abstractmethod
    def segment(self, image) -> List["PIL.Image.Image"]:
        """تقسيم الصورة إلى أسطر نصّية.

        Args:
            image: كائن PIL.Image أو مصفوفة NumPy.

        Returns:
            قائمة من كائنات PIL.Image لكل سطر.
        """
        ...

    @abstractmethod
    def segment_with_info(self, image) -> List[LineSegment]:
        """تقسيم الصورة مع إرجاع البيانات الوصفية لكل سطر.

        Args:
            image: كائن PIL.Image أو مصفوفة NumPy.

        Returns:
            قائمة من الأزواج (صورة_السطر, بيانات_وصفية).
        """
        ...


# ============================================================
# ProjectionProfileSegmenter — المسقط الأفقي
# ============================================================
class ProjectionProfileSegmenter(BaseLineSegmenter):
    """تقسيم الأسطر باستخدام تحليل المسقط الأفقي (Horizontal Projection Profile).

    يقوم بجمع قيم البكسل في كل صفّ أفقي ثم يبحث عن الوديان (مناطق فارغة)
    التي تمثّل الفواصل بين الأسطر.

    Args:
        min_line_height: أقل ارتفاع مسموح لسطر (بالبكسل).
        gap_threshold: العتبة الدنيا للفجوة بين الأسطر.
        smoothing_window: حجم نافذة التنعيم على المسقط.
        binary_threshold: عتبة التحويل الثنائي.
    """

    def __init__(
        self,
        min_line_height: int = 10,
        gap_threshold: int = 5,
        smoothing_window: int = 5,
        binary_threshold: int = 127,
    ) -> None:
        self._min_line_height = min_line_height
        self._gap_threshold = gap_threshold
        self._smoothing_window = smoothing_window
        self._binary_threshold = binary_threshold

    def segment(self, image) -> List["PIL.Image.Image"]:
        """تقسيم الصورة إلى أسطر (الصور فقط)."""
        return [img for img, _info in self.segment_with_info(image)]

    def segment_with_info(self, image) -> List[LineSegment]:
        """تقسيم الصورة إلى أسطر مع البيانات الوصفية.

        Returns:
            قائمة من الأزواج (صورة_السطر, {
                'y_start', 'y_end', 'mean_density', 'peak_density'
            }).
        """
        import PIL.Image

        gray = _ensure_gray(image)
        binary = _to_binary(gray, self._binary_threshold)

        # حساب المسقط الأفقي
        h_profile = np.sum(binary, axis=1).astype(np.float64)

        # تنعيم المسقط
        if self._smoothing_window > 1:
            kernel = np.ones(self._smoothing_window) / self._smoothing_window
            h_profile = np.convolve(h_profile, kernel, mode="same")

        # تحديد مناطق الأسطر
        lines = self._find_line_regions(h_profile, gray.shape[0])

        result: List[LineSegment] = []
        for y_start, y_end in lines:
            line_img = PIL.Image.fromarray(gray[y_start:y_end, :]).convert("RGB")
            line_patch = binary[y_start:y_end, :]
            mean_density = float(np.mean(line_patch) / 255.0)
            peak_density = float(np.max(h_profile[y_start:y_end]) / (gray.shape[1] * 255.0))

            info: Dict[str, Any] = {
                "y_start": y_start,
                "y_end": y_end,
                "mean_density": round(mean_density, 4),
                "peak_density": round(min(peak_density, 1.0), 4),
            }
            result.append((line_img, info))

        logger.debug("تمّ تقسيم الصورة إلى %d سطر (مسقط أفقي).", len(result))
        return result

    def _find_line_regions(
        self, profile: np.ndarray, image_height: int
    ) -> List[Tuple[int, int]]:
        """إيجاد مناطق الأسطر في المسقط الأفقي.

        Args:
            profile: مصفوفة المسقط الأفقي.
            image_height: ارتفاع الصورة الأصلي.

        Returns:
            قائمة من الأزواج (y_start, y_end).
        """
        threshold = np.max(profile) * 0.05  # عتبة تحسّس منخفضة
        in_line = False
        y_start = 0
        regions: List[Tuple[int, int]] = []
        last_gap_start: Optional[int] = None

        for y in range(image_height):
            if profile[y] > threshold:
                if not in_line:
                    # إذا كانت هناك فجوة سابقة قصيرة، نتخطّاها
                    if (
                        last_gap_start is not None
                        and (y - last_gap_start) < self._gap_threshold
                    ):
                        # دمج مع السطر السابق
                        last_gap_start = None
                    else:
                        y_start = y
                    in_line = True
            else:
                if in_line:
                    last_gap_start = y
                    in_line = False

        # إغلاق السطر الأخير
        if in_line:
            regions.append((y_start, image_height))
        elif last_gap_start is not None and (image_height - last_gap_start) >= self._min_line_height:
            # الودي الأخير لا يُغلَق — سطر حتى نهاية الصورة
            pass

        # المرور الثاني: جمع مناطق الأسطر من y_start إلى last_gap_start
        in_line = False
        y_start = 0
        final_regions: List[Tuple[int, int]] = []
        gap_counter = 0

        for y in range(image_height):
            if profile[y] > threshold:
                if not in_line:
                    y_start = y
                    in_line = True
                gap_counter = 0
            else:
                gap_counter += 1
                if in_line and gap_counter >= self._gap_threshold:
                    y_end = y - self._gap_threshold
                    if y_end - y_start >= self._min_line_height:
                        final_regions.append((y_start, y_end))
                    in_line = False

        if in_line and image_height - y_start >= self._min_line_height:
            final_regions.append((y_start, image_height))

        return final_regions


# ============================================================
# UNetLineSegmenter — شبكة U-Net
# ============================================================
class UNetLineSegmenter(BaseLineSegmenter):
    """تقسيم الأسطر باستخدام شبكة U-Net للكشف عن الأسطر على مستوى البكسل.

    تُنتِج الشبكة قناعًا ثنائيًا يُحدِّد مواقع الأسطر، ثم تُستخرج
    المكونات المتصلة ويُرتَّبَت حسب الموقع الرأسي.

    Args:
        model_path: مسار نموذج U-Net (اختياري).
        device: الجهاز المستخدم ('cpu' أو 'cuda').
        min_line_height: أقل ارتفاع مسموح لسطر.
        confidence_threshold: عتبة الثقة لقناع U-Net.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        min_line_height: int = 10,
        confidence_threshold: float = 0.5,
    ) -> None:
        self._model_path = model_path
        self._device = device
        self._min_line_height = min_line_height
        self._confidence_threshold = confidence_threshold
        self._model = None

        if model_path:
            self._load_model()

    def _load_model(self) -> None:
        """تحميل نموذج U-Net."""
        try:
            import torch
            from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large

            self._model = deeplabv3_mobilenet_v3_large(
                weights=None, num_classes=2
            )
            state = torch.load(
                self._model_path, map_location=self._device, weights_only=True
            )
            self._model.load_state_dict(state)
            self._model.to(self._device)
            self._model.eval()
            logger.info("تمّ تحميل نموذج U-Net من: %s", self._model_path)
        except Exception as exc:
            logger.warning(
                "تعذّر تحميل نموذج U-Net (%s). سيتم استخدام المسقط الأفقي كاحتياطي.",
                exc,
            )
            self._model = None

    def segment(self, image) -> List["PIL.Image.Image"]:
        """تقسيم الصورة إلى أسطر (الصور فقط)."""
        return [img for img, _info in self.segment_with_info(image)]

    def segment_with_info(self, image) -> List[LineSegment]:
        """تقسيم الصورة باستخدام U-Net مع البيانات الوصفية.

        في حال عدم توفر النموذج، يتراجع إلى المسقط الأفقي.
        """
        import PIL.Image

        gray = _ensure_gray(image)

        if self._model is None:
            logger.debug("النموذج غير متوفّر — التراجع إلى المسقط الأفقي.")
            fallback = ProjectionProfileSegmenter(
                min_line_height=self._min_line_height
            )
            return fallback.segment_with_info(image)

        mask = self._predict_mask(gray)
        line_regions = self._extract_regions_from_mask(mask, gray)

        result: List[LineSegment] = []
        for y_start, y_end in line_regions:
            line_img = PIL.Image.fromarray(gray[y_start:y_end, :]).convert("RGB")
            line_patch = mask[y_start:y_end, :]
            mean_density = float(np.mean(line_patch) / 255.0)
            peak_density = float(np.max(line_patch) / 255.0)

            info: Dict[str, Any] = {
                "y_start": y_start,
                "y_end": y_end,
                "mean_density": round(mean_density, 4),
                "peak_density": round(peak_density, 4),
            }
            result.append((line_img, info))

        logger.debug("تمّ تقسيم الصورة إلى %d سطر (U-Net).", len(result))
        return result

    def _predict_mask(self, gray: np.ndarray) -> np.ndarray:
        """توقع قناع الأسطر باستخدام U-Net.

        Args:
            gray: صورة رمادية (H, W).

        Returns:
            قناع ثنائي (H, W) uint8.
        """
        import torch
        import torchvision.transforms as T

        h, w = gray.shape
        transform = T.Compose([
            T.ToPILImage(),
            T.Resize((512, 512)),
            T.ToTensor(),
            T.Normalize(mean=[0.5], std=[0.5]),
        ])

        # تحويل الصورة الرمادية إلى 3 قنوات
        gray_3ch = np.stack([gray, gray, gray], axis=-1)
        input_tensor = transform(gray_3ch).unsqueeze(0).to(self._device)

        with torch.no_grad():
            output = self._model(input_tensor)["out"][0]
            pred = torch.argmax(output, dim=0).cpu().numpy()

        # إعادة الحجم الأصلي
        mask = (pred * 255).astype(np.uint8)
        mask = np.array(
            PIL.Image.fromarray(mask).resize((w, h), PIL.Image.NEAREST)
        )
        return mask

    def _extract_regions_from_mask(
        self, mask: np.ndarray, gray: np.ndarray
    ) -> List[Tuple[int, int]]:
        """استخراج مناطق الأسطر من القناع عبر المكونات المتصلة.

        Args:
            mask: قناع الأسطر.
            gray: الصورة الرمادية الأصلية.

        Returns:
            قائمة من الأزواج (y_start, y_end).
        """
        import cv2

        h_profile = np.sum(mask, axis=1)
        threshold = np.max(h_profile) * self._confidence_threshold if np.max(h_profile) > 0 else 0

        in_line = False
        y_start = 0
        regions: List[Tuple[int, int]] = []

        for y in range(mask.shape[0]):
            if h_profile[y] > threshold:
                if not in_line:
                    y_start = y
                    in_line = True
            else:
                if in_line:
                    if y - y_start >= self._min_line_height:
                        regions.append((y_start, y))
                    in_line = False

        if in_line and mask.shape[0] - y_start >= self._min_line_height:
            regions.append((y_start, mask.shape[0]))

        # ترتيب حسب الموقع الرأسي
        regions.sort(key=lambda r: r[0])
        return regions


# ============================================================
# ContourLineSegmenter — التحليل المورفولوجي + المحيطات
# ============================================================
class ContourLineSegmenter(BaseLineSegmenter):
    """تقسيم الأسطر باستخدام الإغلاق المورفولوجي وكشف المحيطات.

    مناسب للنصوص المائلة أو المنحنية حيث لا ينجح المسقط الأفقي.

    Args:
        min_line_height: أقل ارتفاع مسموح لسطر.
        morph_kernel_width: عرض نواة الإغلاق المورفولوجي.
        morph_kernel_height: ارتفاع نواة الإغلاق المورفولوجي.
        min_area: الحدّ الأدنى لمساحة المحيط.
        binary_threshold: عتبة التحويل الثنائي.
    """

    def __init__(
        self,
        min_line_height: int = 10,
        morph_kernel_width: int = 100,
        morph_kernel_height: int = 5,
        min_area: int = 500,
        binary_threshold: int = 127,
    ) -> None:
        self._min_line_height = min_line_height
        self._kernel_w = morph_kernel_width
        self._kernel_h = morph_kernel_height
        self._min_area = min_area
        self._binary_threshold = binary_threshold

    def segment(self, image) -> List["PIL.Image.Image"]:
        """تقسيم الصورة إلى أسطر (الصور فقط)."""
        return [img for img, _info in self.segment_with_info(image)]

    def segment_with_info(self, image) -> List[LineSegment]:
        """تقسيم الصورة باستخدام المحيطات مع البيانات الوصفية.

        Returns:
            قائمة من الأزواج (صورة_السطر, {
                'y_start', 'y_end', 'mean_density', 'peak_density',
                'contour_area', 'bounding_box'
            }).
        """
        import PIL.Image
        import cv2

        gray = _ensure_gray(image)
        binary = _to_binary(gray, self._binary_threshold)

        # الإغلاق المورفولوجي لربط البكسلات في نفس السطر
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (self._kernel_w, self._kernel_h)
        )
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

        # كشف المحيطات
        contours, _hierarchy = cv2.findContours(
            closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        result: List[LineSegment] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self._min_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            if h < self._min_line_height:
                continue

            # اقتطاع السطر من الصورة الأصلية
            y_start = max(0, y)
            y_end = min(gray.shape[0], y + h)
            line_img = PIL.Image.fromarray(gray[y_start:y_end, :]).convert("RGB")

            line_patch = binary[y_start:y_end, :]
            mean_density = float(np.mean(line_patch) / 255.0)
            peak_density = float(np.max(line_patch) / 255.0)

            info: Dict[str, Any] = {
                "y_start": y_start,
                "y_end": y_end,
                "mean_density": round(mean_density, 4),
                "peak_density": round(peak_density, 4),
                "contour_area": int(area),
                "bounding_box": (int(x), int(y), int(w), int(h)),
            }
            result.append((line_img, info))

        # ترتيب حسب الموقع الرأسي
        result.sort(key=lambda r: r[1]["y_start"])

        logger.debug("تمّ تقسيم الصورة إلى %d سطر (المحيطات).", len(result))
        return result
