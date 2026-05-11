"""
Vocabulary Column Splitter — تقسيم صفحات المفردات ثنائية العمود
مصمم خصيصاً للدفاتر المسطرة والخط اليدوي المختلط (إنجليزي ← عربي)
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional


class VocabularyColumnSplitter:
    """تقسيم صفحات المفردات ثنائية العمود (إنجليزي ← عربي)"""

    def __init__(self,
                 min_column_gap: int = 50,
                 expected_columns: int = 2,
                 detect_header: bool = True,
                 rtl_column_index: int = 1):
        self.min_column_gap = min_column_gap
        self.expected_columns = expected_columns
        self.detect_header = detect_header
        self.rtl_column_index = rtl_column_index

    def split(self, image: np.ndarray) -> dict:
        """
        تقسيم صورة الصفحة إلى مكوناتها المنطقية

        Returns:
            dict: {
                'header': np.ndarray | None,
                'left_column': np.ndarray,
                'right_column': np.ndarray,
                'column_bounds': [(x1,x2), ...],
                'line_positions': List[int],
                'metadata': {}
            }
        """
        result = {
            'header': None,
            'left_column': None,
            'right_column': None,
            'column_bounds': [],
            'line_positions': [],
            'metadata': {}
        }

        processed = self._preprocess_for_segmentation(image)
        height, width = processed.shape[:2]

        if self.detect_header:
            header_height = self._detect_header_height(processed)
            if header_height > 0:
                result['header'] = image[0:header_height, :].copy()
                processed = processed[header_height:, :]
                result['metadata']['header_height'] = header_height

        vertical_proj = np.sum(processed == 0, axis=0)
        column_split_x = self._find_column_gap(vertical_proj, width, self.min_column_gap)

        if column_split_x is None:
            column_split_x = width // 2
            result['metadata']['split_method'] = 'fallback_center'
        else:
            result['metadata']['split_method'] = 'projection_gap'

        margin = 5
        result['left_column'] = image[:, max(0, 0):min(width, column_split_x - margin)].copy()
        result['right_column'] = image[:, max(0, column_split_x + margin):width].copy()
        result['column_bounds'] = [(0, column_split_x - margin), (column_split_x + margin, width)]

        result['line_positions'] = self._detect_line_positions(processed)
        result['metadata'].update({
            'image_size': (width, height),
            'split_x': column_split_x,
            'avg_line_spacing': np.mean(np.diff(result['line_positions'])) if len(result['line_positions']) > 1 else None
        })

        return result

    def _preprocess_for_segmentation(self, image: np.ndarray) -> np.ndarray:
        """تحضير الصورة لاكتشاف الهيكل"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        cleaned = cv2.subtract(gray, lines)
        _, binary = cv2.threshold(cleaned, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return binary

    def _detect_header_height(self, binary: np.ndarray) -> int:
        """اكتشاف ارتفاع سطر العنوان/التاريخ في الأعلى"""
        height, width = binary.shape
        header_region = binary[0:int(height * 0.15), :]
        horizontal_proj = np.sum(header_region, axis=1)

        empty_threshold = width * 0.7
        for i, density in enumerate(horizontal_proj):
            if density < empty_threshold and i > 20:
                if i + 2 < len(horizontal_proj) and \
                   horizontal_proj[i+1] < empty_threshold and \
                   horizontal_proj[i+2] < empty_threshold:
                    return i
        return 0

    def _find_column_gap(self, projection: np.ndarray, width: int, min_gap: int) -> Optional[int]:
        """إيجاد موقع الفجوة الرأسية بين العمودين"""
        text_pixels = projection[projection > 0]
        if len(text_pixels) == 0:
            return None

        avg_density = np.mean(text_pixels)
        gap_threshold = avg_density * 0.1

        best_gap = None
        best_width = 0
        in_gap = False
        gap_start = 0

        for x in range(width):
            if projection[x] < gap_threshold and not in_gap:
                in_gap = True
                gap_start = x
            elif projection[x] >= gap_threshold and in_gap:
                in_gap = False
                gap_width = x - gap_start
                if gap_width >= min_gap and gap_width > best_width:
                    best_width = gap_width
                    best_gap = (gap_start + x) // 2

        if in_gap:
            gap_width = width - gap_start
            if gap_width >= min_gap and gap_width > best_width:
                best_gap = (gap_start + width) // 2

        return best_gap

    def _detect_line_positions(self, binary: np.ndarray,
                              min_line_spacing: int = 10,
                              max_line_spacing: int = 100) -> List[int]:
        """اكتشاف مواقع بداية كل سطر للمحاذاة بين العمودين"""
        height = binary.shape[0]
        horizontal_proj = np.sum(binary, axis=1)

        text_threshold = np.percentile(horizontal_proj[horizontal_proj > 0], 25) if np.any(horizontal_proj > 0) else 0

        lines = []
        in_text = False
        line_start = 0

        for y in range(height):
            if horizontal_proj[y] > text_threshold and not in_text:
                in_text = True
                line_start = y
            elif horizontal_proj[y] <= text_threshold and in_text:
                in_text = False
                line_height = y - line_start
                if min_line_spacing <= line_height <= max_line_spacing:
                    lines.append(line_start)

        if in_text and height - line_start >= min_line_spacing:
            lines.append(line_start)

        if len(lines) > 1:
            filtered = [lines[0]]
            for i in range(1, len(lines)):
                if lines[i] - filtered[-1] >= min_line_spacing * 0.7:
                    filtered.append(lines[i])
            lines = filtered

        return lines
