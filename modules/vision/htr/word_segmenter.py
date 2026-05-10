"""
تجزئة الكلمات العربية (Arabic Word Segmentation).

يوفر فئة ArabicWordSegmenter لتقسيم صورة السطر إلى صور كلمات منفصلة
باستخدام تحليل المسقط الرأسي أو تحليل المكونات المتصلة.

يدعم وضع التوجيه بالنسخ المتوقَّع حيث يُستخدم النصّ المُتنبَّأ به
لتوجيه حدود الكلمات.
"""

import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def _ensure_gray(image) -> np.ndarray:
    """تحويل المدخل إلى مصفوفة NumPy رمادية (H, W)."""
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
    """تحويل الصورة الرمادية إلى صورة ثنائية (نصّ=أبيض، خلفية=سوداء)."""
    binary = np.zeros_like(gray)
    binary[gray < threshold] = 255
    return binary


# ============================================================
# ArabicWordSegmenter
# ============================================================
class ArabicWordSegmenter:
    """مُجزِّئ الكلمات العربية.

    يقسّم صورة السطر إلى صور كلمات منفصلة باستخدام:
      - المسقط الرأسي (Vertical Projection Profile): افتراضي.
      - تحليل المكونات المتصلة (Connected Components): للخطوط الكبيرة.

    Args:
        min_word_width: أقل عرض مسموح لكلمة (بالبكسل).
        gap_threshold_factor: مضاعِف حساب عتبة الفجوة بين الكلمات.
            تُحسَب العتبة كـ: (ارتفاع_السطر × gap_threshold_factor).
        use_vertical_profile: استخدام المسقط الرأسي (True) أو المكونات المتصلة (False).
        binary_threshold: عتبة التحويل الثنائي.
    """

    def __init__(
        self,
        min_word_width: int = 5,
        gap_threshold_factor: float = 0.5,
        use_vertical_profile: bool = True,
        binary_threshold: int = 127,
    ) -> None:
        self._min_word_width = min_word_width
        self._gap_factor = gap_threshold_factor
        self._use_profile = use_vertical_profile
        self._binary_threshold = binary_threshold

    def segment(self, line_image) -> List["PIL.Image.Image"]:
        """تقسيم صورة سطر إلى صور كلمات.

        Args:
            line_image: صورة السطر (PIL.Image أو numpy.ndarray).

        Returns:
            قائمة من كائنات PIL.Image لكل كلمة.
        """
        if self._use_profile:
            return self._segment_by_profile(line_image)
        return self._segment_by_contours(line_image)

    def segment_with_spaces(
        self, line_image, predicted_text: str
    ) -> List[Tuple["PIL.Image.Image", str]]:
        """تقسيم صورة السطر باستخدام النصّ المُتنبَّأ به للتوجيه.

        يُستخدم طول كل كلمة في النصّ المُتنبَّأ لتقدير عرضها المتوقّع
        في الصورة، ممّا يُحسِّن دقة التقسيم.

        Args:
            line_image: صورة السطر.
            predicted_text: النصّ المُتنبَّأ به (بدون تنقيط).

        Returns:
            قائمة من الأزواج (صورة_الكلمة, نص_الكلمة).
        """
        import PIL.Image

        gray = _ensure_gray(line_image)
        binary = _to_binary(gray, self._binary_threshold)
        h, w = binary.shape

        if not predicted_text.strip():
            return [(PIL.Image.fromarray(gray).convert("RGB"), predicted_text)]

        words = predicted_text.split()
        n_words = len(words)

        if n_words <= 1:
            return [(PIL.Image.fromarray(gray).convert("RGB"), predicted_text)]

        # حساب المسقط الرأسي
        v_profile = np.sum(binary, axis=0).astype(np.float64)

        # تقدير عرض كل كلمة بناءً على طولها النسبي
        total_chars = sum(len(word) for word in words)
        if total_chars == 0:
            return [(PIL.Image.fromarray(gray).convert("RGB"), predicted_text)]

        word_boundaries: List[Tuple[int, int]] = []
        margin = 2  # هامش بكسل إضافي

        if n_words == 2:
            # حالة كلمتين: ابحث عن أكبر فجوة
            split_ratio = len(words[0]) / total_chars
            target_x = int(w * split_ratio)

            # البحث في نطاق حول الهدف
            search_start = max(0, target_x - w // 8)
            search_end = min(w, target_x + w // 8)
            search_region = v_profile[search_start:search_end]

            if len(search_region) > 0:
                best_gap_x = search_start + int(np.argmin(search_region))
                word_boundaries.append((0, best_gap_x))
                word_boundaries.append((best_gap_x, w))
            else:
                word_boundaries.append((0, w))
        else:
            # حالة أكثر من كلمتين: تقسيم متتابع
            cumulative_ratio = 0.0
            prev_x = 0

            for i in range(n_words - 1):
                cumulative_ratio += len(words[i]) / total_chars
                target_x = int(w * cumulative_ratio)

                search_start = max(prev_x + self._min_word_width, target_x - w // 10)
                search_end = min(w - self._min_word_width, target_x + w // 10)

                if search_start >= search_end:
                    continue

                search_region = v_profile[search_start:search_end]
                best_gap_x = search_start + int(np.argmin(search_region))
                word_boundaries.append((prev_x, best_gap_x))
                prev_x = best_gap_x

            word_boundaries.append((prev_x, w))

        # اقتطاع صور الكلمات
        results: List[Tuple["PIL.Image.Image", str]] = []
        for i, (x_start, x_end) in enumerate(word_boundaries):
            x_start = max(0, x_start - margin)
            x_end = min(w, x_end + margin)
            word_img = PIL.Image.fromarray(gray[:, x_start:x_end]).convert("RGB")
            word_text = words[i] if i < len(words) else ""
            results.append((word_img, word_text))

        logger.debug(
            "تمّ تقسيم السطر إلى %d كلمة (توجيه بالنسخ).", len(results)
        )
        return results

    # ----------------------------------------------------------
    # _segment_by_profile — المسقط الرأسي
    # ----------------------------------------------------------
    def _segment_by_profile(self, line_image) -> List["PIL.Image.Image"]:
        """تقسيم السطر باستخدام تحليل المسقط الرأسي.

        يبحث عن الوديان في المسقط الرأسي (أعمدة فارغة) ويستخدمها
        كفواصل بين الكلمات.

        Args:
            line_image: صورة السطر.

        Returns:
            قائمة من صور الكلمات.
        """
        import PIL.Image

        gray = _ensure_gray(line_image)
        binary = _to_binary(gray, self._binary_threshold)
        h, w = binary.shape

        # حساب المسقط الرأسي
        v_profile = np.sum(binary, axis=0).astype(np.float64)

        # حساب عتبة الفجوة
        line_height = h
        gap_threshold = line_height * self._gap_factor * 255.0

        # تنعيم المسقط
        kernel_size = max(3, min(7, w // 20))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = np.ones(kernel_size) / kernel_size
        v_profile = np.convolve(v_profile, kernel, mode="same")

        # إيجاد مناطق الكلمات
        in_word = False
        x_start = 0
        gap_counter = 0
        regions: List[Tuple[int, int]] = []

        for x in range(w):
            if v_profile[x] > gap_threshold:
                if not in_word:
                    x_start = x
                    in_word = True
                gap_counter = 0
            else:
                gap_counter += 1
                if in_word and gap_counter >= 2:
                    x_end = x - gap_counter
                    if x_end - x_start >= self._min_word_width:
                        regions.append((x_start, x_end))
                    in_word = False

        # إغلاق الكلمة الأخيرة
        if in_word and w - x_start >= self._min_word_width:
            regions.append((x_start, w))

        # اقتطاع صور الكلمات
        results: List["PIL.Image.Image"] = []
        for x_start, x_end in regions:
            word_img = PIL.Image.fromarray(gray[:, x_start:x_end]).convert("RGB")
            results.append(word_img)

        logger.debug(
            "تمّ تقسيم السطر إلى %d كلمة (مسقط رأسي).", len(results)
        )
        return results

    # ----------------------------------------------------------
    # _segment_by_contours — المكونات المتصلة
    # ----------------------------------------------------------
    def _segment_by_contours(self, line_image) -> List["PIL.Image.Image"]:
        """تقسيم السطر باستخدام تحليل المكونات المتصلة.

        يكتشف المكونات المتصلة في الصورة الثنائية ويجمع المكونات
        المتقاربة رأسيًا في كلمة واحدة.

        Args:
            line_image: صورة السطر.

        Returns:
            قائمة من صور الكلمات.
        """
        import PIL.Image
        import cv2

        gray = _ensure_gray(line_image)
        binary = _to_binary(gray, self._binary_threshold)
        h, w = binary.shape

        # كشف المكونات المتصلة
        num_labels, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )

        # تجميع المكونات (استبعاد الخلفية — label 0)
        merge_threshold = h * 0.3  # عتبة الدمج الرأسي
        components: List[dict] = []

        for i in range(1, num_labels):
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            bw = stats[i, cv2.CC_STAT_WIDTH]
            bh = stats[i, cv2.CC_STAT_HEIGHT]
            area = stats[i, cv2.CC_STAT_AREA]

            if area < 10 or bw < 2 or bh < 2:
                continue

            components.append({
                "x": x,
                "y": y,
                "w": bw,
                "h": bh,
                "cx": x + bw / 2,
                "cy": y + bh / 2,
                "area": area,
            })

        if not components:
            return [PIL.Image.fromarray(gray).convert("RGB")]

        # ترتيب حسب الموقع الأفقي
        components.sort(key=lambda c: c["x"])

        # دمج المكونات المتقاربة
        word_groups: List[List[dict]] = []
        current_group: List[dict] = [components[0]]

        for comp in components[1:]:
            prev = current_group[-1]
            gap = comp["x"] - (prev["x"] + prev["w"])
            overlap_y = min(prev["y"] + prev["h"], comp["y"] + comp["h"]) - max(prev["y"], comp["y"])
            vertical_proximity = max(0, h - overlap_y) / h if h > 0 else 1.0

            if gap < merge_threshold or vertical_proximity < 0.5:
                current_group.append(comp)
            else:
                word_groups.append(current_group)
                current_group = [comp]

        word_groups.append(current_group)

        # اقتطاع صور الكلمات
        results: List["PIL.Image.Image"] = []
        for group in word_groups:
            x_min = min(c["x"] for c in group)
            x_max = max(c["x"] + c["w"] for c in group)
            y_min = min(c["y"] for c in group)
            y_max = max(c["y"] + c["h"] for c in group)

            x_min = max(0, x_min - 1)
            x_max = min(w, x_max + 1)
            y_min = max(0, y_min - 1)
            y_max = min(h, y_max + 1)

            word_img = PIL.Image.fromarray(gray[y_min:y_max, x_min:x_max]).convert("RGB")
            if word_img.width >= self._min_word_width:
                results.append(word_img)

        logger.debug(
            "تمّ تقسيم السطر إلى %d كلمة (مكونات متصلة).", len(results)
        )
        return results
