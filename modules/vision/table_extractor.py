"""
وحدة استخراج الجداول (Table Extraction Module)
==================================================
استخراج بيانات الجداول المهيكلة من مناطق الجداول المكتشفة:
- كشف الخلايا باستخدام تحليل المحيطات وتقاطعات الخطوط
- إعادة بناء الصفوف والأعمدة
- التعرف على محتوى الخلايا
- إخراج بيانات مهيكلة (قائمة قوائم)

Extracts structured table data from detected table regions using
contour analysis and line intersection detection.

المصدر: دمج من مشروع arabic-ocr-pro
Source: Merged from arabic-ocr-pro project

OmniFile AI Processor - وحدة معالجة الملفات الذكية
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

from modules.core.structure import BBox

logger = logging.getLogger(__name__)


class TableExtractor:
    """مستخرج البيانات المهيكلة من مناطق الجداول في صور المستندات.

    يستخدم مزيجاً من كشف الخطوط وتحليل المحيطات
    لتحديد خلايا الجدول وصفوفه وأعمدته.

    Extracts structured data from table regions using a combination
    of line detection and contour analysis.

    Attributes:
        ocr_engine: محرك OCR لقراءة محتوى الخلايا / OCR engine for cell contents
        min_cell_area: الحد الأدنى لمساحة الخلية / Minimum cell area in pixels
        cell_padding: حشوة حول الخلايا للتعرف الأفضل / Padding around cell boundaries
    """

    def __init__(
        self,
        ocr_engine: Optional[object] = None,
        min_cell_area: int = 200,
        cell_padding: int = 2,
    ) -> None:
        """تهيئة مستخرج الجداول / Initialize the table extractor.

        Args:
            ocr_engine: محرك OCR (إذا None، تُستخرج الخلايا فقط) / OCR engine instance
            min_cell_area: الحد الأدنى لمساحة الخلية بالبكسل / Minimum cell area in pixels
            cell_padding: حشوة بالبكسل حول حدود الخلية / Padding in pixels around cells
        """
        self.ocr_engine = ocr_engine
        self.min_cell_area = min_cell_area
        self.cell_padding = cell_padding

    def extract_table(
        self,
        image: np.ndarray,
        table_bbox: BBox,
    ) -> list[list[str]]:
        """استخراج بيانات الجدول من منطقة جدول / Extract table data from a table region.

        يكتشف بنية الشبكة ويحدد الخلايا ويشغل OCR على كل خلية.

        Args:
            image: صورة المستند الكاملة / Full document image
            table_bbox: مربع إحاطة منطقة الجدول / Bounding box of the table region

        Returns:
            قائمة صفوف، كل صف قائمة نصوص خلايا / List of rows with cell text strings
        """
        h, w = image.shape[:2]

        # قص منطقة الجدول
        x1 = max(0, table_bbox.x)
        y1 = max(0, table_bbox.y)
        x2 = min(w, table_bbox.x + table_bbox.width)
        y2 = min(h, table_bbox.y + table_bbox.height)

        if x1 >= x2 or y1 >= y2:
            return []

        table_image = image[y1:y2, x1:x2].copy()
        gray = self._to_grayscale(table_image)

        # كشف الخطوط الأفقية والعمودية
        h_lines = self._detect_lines(gray, orientation="horizontal")
        v_lines = self._detect_lines(gray, orientation="vertical")

        # إذا وجدنا خطوط شبكة، نستخدم كشف الخلايا بالخطوط
        if h_lines and v_lines:
            cells = self._detect_cells_from_lines(table_image, h_lines, v_lines)
        else:
            # الرجوع لكشف الخلايا بالمحيطات
            cells = self._detect_cells_from_contours(table_image)

        if not cells:
            logger.debug("No cells detected in table region")
            return []

        # تنظيم الخلايا في صفوف
        rows = self._organize_into_rows(cells)

        # التعرف على كل خلية
        if self.ocr_engine is not None:
            result = self._ocr_cells(table_image, rows)
        else:
            result = [["" for _ in row] for row in rows]

        logger.debug(f"Extracted table: {len(result)} rows x {max(len(r) for r in result) if result else 0} cols")
        return result

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """تحويل الصورة إلى تدرج رمادي / Convert image to grayscale."""
        if len(image.shape) == 2:
            return image.copy()
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _detect_lines(
        self,
        gray: np.ndarray,
        orientation: str = "horizontal",
        min_line_length_ratio: float = 0.2,
    ) -> list[tuple[int, int, int, int]]:
        """كشف الخطوط في اتجاه معين / Detect lines in a specific orientation."""
        h, w = gray.shape

        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 5,
        )

        if orientation == "horizontal":
            kernel_length = int(w * 0.3)
            if kernel_length % 2 == 0:
                kernel_length += 1
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_length, 1))
            min_length = int(w * min_line_length_ratio)
        else:
            kernel_length = int(h * 0.2)
            if kernel_length % 2 == 0:
                kernel_length += 1
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_length))
            min_length = int(h * min_line_length_ratio)

        lines_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)

        edges = cv2.Canny(lines_mask, 50, 150)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=50,
            minLineLength=min_length,
            maxLineGap=10,
        )

        result: list[tuple[int, int, int, int]] = []
        if lines is not None:
            for line in lines:
                x1_l, y1_l, x2_l, y2_l = line[0]
                result.append((int(x1_l), int(y1_l), int(x2_l), int(y2_l)))

        return result

    def _detect_cells_from_lines(
        self,
        image: np.ndarray,
        h_lines: list[tuple[int, int, int, int]],
        v_lines: list[tuple[int, int, int, int]],
    ) -> list[BBox]:
        """كشف خلايا الجدول من خطوط الشبكة / Detect table cells from grid lines."""
        h, w = image.shape[:2]

        h_y_values: list[int] = []
        for x1, y1, x2, y2 in h_lines:
            h_y_values.extend([y1, y2])
        h_y_values = sorted(set(h_y_values))

        v_x_values: list[int] = []
        for x1, y1, x2, y2 in v_lines:
            v_x_values.extend([x1, x2])
        v_x_values = sorted(set(v_x_values))

        # إضافة حدود الصورة
        h_y_values = [0] + h_y_values + [h]
        v_x_values = [0] + v_x_values + [w]

        # دمج الإحداثيات المتقاربة
        h_y_values = self._merge_close_values(h_y_values, threshold=5)
        v_x_values = self._merge_close_values(v_x_values, threshold=5)

        # إنشاء مربعات إحاطة الخلايا
        cells: list[BBox] = []
        for i in range(len(h_y_values) - 1):
            for j in range(len(v_x_values) - 1):
                y1 = h_y_values[i]
                y2 = h_y_values[i + 1]
                x1 = v_x_values[j]
                x2 = v_x_values[j + 1]

                cw = x2 - x1
                ch = y2 - y1

                if cw > 5 and ch > 5 and cw * ch >= self.min_cell_area:
                    cells.append(BBox(x=x1, y=y1, width=cw, height=ch))

        return cells

    def _detect_cells_from_contours(self, image: np.ndarray) -> list[BBox]:
        """كشف خلايا الجدول باستخدام تحليل المحيطات / Detect cells using contour analysis."""
        gray = self._to_grayscale(image)

        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        cells: list[BBox] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_cell_area:
                continue

            x, y, w_c, h_c = cv2.boundingRect(contour)

            aspect = h_c / max(w_c, 1)
            if 0.1 < aspect < 10.0:
                cells.append(BBox(x=x, y=y, width=w_c, height=h_c))

        return cells

    def _organize_into_rows(self, cells: list[BBox]) -> list[list[BBox]]:
        """تنظيم الخلايا المكتشفة في صفوف / Organize cells into rows."""
        if not cells:
            return []

        sorted_cells = sorted(cells, key=lambda c: c.y)

        rows: list[list[BBox]] = []
        current_row: list[BBox] = [sorted_cells[0]]

        for cell in sorted_cells[1:]:
            row_y_center = sum(c.center[1] for c in current_row) / len(current_row)
            row_height = max(c.height for c in current_row)

            if abs(cell.center[1] - row_y_center) < row_height * 0.6:
                current_row.append(cell)
            else:
                current_row.sort(key=lambda c: c.x, reverse=True)
                rows.append(current_row)
                current_row = [cell]

        if current_row:
            current_row.sort(key=lambda c: c.x, reverse=True)
            rows.append(current_row)

        return rows

    def _ocr_cells(
        self,
        table_image: np.ndarray,
        rows: list[list[BBox]],
    ) -> list[list[str]]:
        """تشغيل OCR على كل خلية من الجدول / Run OCR on each table cell."""
        result: list[list[str]] = []
        h, w = table_image.shape[:2]

        for row in rows:
            row_texts: list[str] = []
            for cell_bbox in row:
                pad = self.cell_padding
                x1 = max(0, cell_bbox.x - pad)
                y1 = max(0, cell_bbox.y - pad)
                x2 = min(w, cell_bbox.x + cell_bbox.width + pad)
                y2 = min(h, cell_bbox.y + cell_bbox.height + pad)

                cell_image = table_image[y1:y2, x1:x2]

                try:
                    tokens = self.ocr_engine.recognize(cell_image)
                    text = " ".join(t.text for t in tokens).strip()
                except Exception as exc:
                    logger.debug(f"Cell OCR failed: {exc}")
                    text = ""

                row_texts.append(text)

            result.append(row_texts)

        return result

    @staticmethod
    def _merge_close_values(
        values: list[int],
        threshold: int = 5,
    ) -> list[int]:
        """دمج القيم المتقاربة / Merge values that are close to each other."""
        if not values:
            return []

        merged: list[int] = [values[0]]

        for val in values[1:]:
            if val - merged[-1] <= threshold:
                merged[-1] = (merged[-1] + val) // 2
            else:
                merged.append(val)

        return merged
