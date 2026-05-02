"""
وحدة تحليل تخطيط المستندات (Layout Analysis Module)
======================================================
تحليل بنية المستند باستخدام العمليات المورفولوجية لـ OpenCV:
- كتل النص (فقرات، أسطر)
- الجداول (باستخدام الكشف عن الخطوط الأفقية والعمودية)
- العناوين (بناءً على حجم النص)
- الصور والرسومات
- الرؤوس والتذييلات

Document layout analysis using OpenCV morphological operations.
Detects text blocks, tables, headings, images, headers and footers
using contour analysis and Hough line detection.

المصدر: دمج من مشروع arabic-ocr-pro
Source: Merged from arabic-ocr-pro project

OmniFile AI Processor - وحدة معالجة الملفات الذكية
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

from modules.core.structure import BBox, BlockType, DocumentBlock

logger = logging.getLogger(__name__)


class LayoutAnalyzer:
    """محلل تخطيط المستندات باستخدام تقنيات الرؤية الحاسوبية.

    يكتشف مناطق الاهتمام في صور المستندات بتحليل
    التوزيع المكاني للنص والعناصر الرسومية.

    Document layout analyzer using computer vision techniques.
    Detects regions of interest by analyzing spatial distribution
    of text and graphical elements.

    Attributes:
        min_block_area: الحد الأدنى لمساحة الكتلة بالبكسل / Minimum block area in pixels
        table_line_threshold: الحد الأدنى لطول خط الجدول / Minimum line length for table detection
        heading_size_ratio: نسبة حجم الخط للعناوين / Font size ratio for heading detection
    """

    def __init__(
        self,
        min_block_area: int = 500,
        table_line_threshold: float = 0.3,
        heading_size_ratio: float = 1.5,
    ) -> None:
        """تهيئة محلل التخطيط / Initialize the layout analyzer.

        Args:
            min_block_area: الحد الأدنى لمساحة كتلة نص صالحة / Minimum area for a valid text block
            table_line_threshold: الحد الأدنى لعرض الصورة لخطوط الجدول / Min fraction for table lines
            heading_size_ratio: نسبة ارتفاع النص فوق المتوسط للعناوين / Height ratio for headings
        """
        self.min_block_area = min_block_area
        self.table_line_threshold = table_line_threshold
        self.heading_size_ratio = heading_size_ratio

    def analyze(self, image: np.ndarray) -> list[DocumentBlock]:
        """تحليل تخطيط صورة مستند / Analyze the layout of a document image.

        يكتشف كتل النص والجداول والعناوين والمناطق الأخرى.

        Args:
            image: صورة المستند (BGR أو تدرج رمادي) / Input document image

        Returns:
            قائمة كائنات DocumentBlock / List of DocumentBlock objects
        """
        gray = self._to_grayscale(image)
        h, w = gray.shape

        blocks: list[DocumentBlock] = []

        # الكشف عن الجداول أولاً
        table_regions = self._detect_tables(gray, w, h)
        for table_bbox in table_regions:
            blocks.append(DocumentBlock(
                block_type=BlockType.TABLE,
                bbox=table_bbox,
                confidence=0.8,
            ))

        # إنشاء قناع نصي مع استبعاد مناطق الجداول
        text_mask = self._create_text_mask(gray, table_regions)

        # الكشف عن كتل النص
        text_regions = self._detect_text_blocks(text_mask, w, h)
        avg_height = self._compute_average_text_height(text_regions)

        for region_bbox, region_height in text_regions:
            block_type = BlockType.TEXT
            if avg_height > 0 and region_height > avg_height * self.heading_size_ratio:
                block_type = BlockType.HEADING

            blocks.append(DocumentBlock(
                block_type=block_type,
                bbox=region_bbox,
                confidence=0.7,
            ))

        # الكشف عن الرؤوس والتذييلات
        header_footer = self._detect_headers_footers(gray, w, h, text_regions)
        blocks.extend(header_footer)

        # ترتيب من الأعلى للأسفل ومن اليمين لليسار للمستندات RTL
        blocks.sort(key=lambda b: (b.bbox.y if b.bbox else 0, -(b.bbox.x if b.bbox else 0)))

        logger.debug(f"Layout analysis found {len(blocks)} blocks "
                     f"(tables: {len(table_regions)}, text: {len(text_regions)})")
        return blocks

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """تحويل الصورة إلى تدرج رمادي / Convert image to grayscale."""
        if len(image.shape) == 2:
            return image
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _detect_tables(
        self,
        gray: np.ndarray,
        width: int,
        height: int,
    ) -> list[BBox]:
        """الكشف عن مناطق الجداول / Detect table regions.

        يستخدم العمليات المورفولوجية للعثور على الخطوط
        الأفقية والعمودية ثم يحدد المناطق المستطيلة.
        """
        # ثنائية التحويل
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 5,
        )

        # الكشف عن الخطوط الأفقية
        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(width * 0.05), 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel, iterations=2)

        # الكشف عن الخطوط العمودية
        vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(height * 0.03)))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel, iterations=2)

        # دمج للعثور على خلايا الجدول
        table_mask = cv2.add(horizontal_lines, vertical_lines)

        # توسيع لإغلاق الفجوات
        table_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        table_mask = cv2.dilate(table_mask, table_kernel, iterations=3)

        # البحث عن محيطات الجداول
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        tables: list[BBox] = []
        min_table_area = 5000

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_table_area:
                continue

            x, y, w_t, h_t = cv2.boundingRect(contour)
            aspect = h_t / max(w_t, 1)

            if 0.2 < aspect < 5.0 and w_t > width * 0.1:
                tables.append(BBox(x=x, y=y, width=w_t, height=h_t))

        return tables

    def _detect_text_blocks(
        self,
        text_mask: np.ndarray,
        width: int,
        height: int,
    ) -> list[tuple[BBox, int]]:
        """الكشف عن كتل النص من القناع النصي / Detect text block regions."""
        # توسيع لربط أسطر النص في فقرات
        block_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (int(width * 0.02), int(height * 0.005)),
        )
        dilated = cv2.dilate(text_mask, block_kernel, iterations=3)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        blocks: list[tuple[BBox, int]] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_block_area:
                continue

            x, y, w_b, h_b = cv2.boundingRect(contour)

            # تخطي الكتل العريضة جداً
            if w_b > width * 0.95 and h_b < 20:
                continue

            blocks.append((BBox(x=x, y=y, width=w_b, height=h_b), h_b))

        # دمج الكتل المتداخلة
        blocks = self._merge_overlapping_blocks(blocks)

        return blocks

    def _create_text_mask(
        self,
        gray: np.ndarray,
        table_regions: list[BBox],
    ) -> np.ndarray:
        """إنشاء قناع نصي مع استبعاد مناطق الجداول / Create text mask excluding tables."""
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        for table in table_regions:
            x1 = table.x
            y1 = table.y
            x2 = table.x + table.width
            y2 = table.y + table.height
            binary[y1:y2, x1:x2] = 0

        return binary

    def _detect_headers_footers(
        self,
        gray: np.ndarray,
        width: int,
        height: int,
        text_regions: list[tuple[BBox, int]],
    ) -> list[DocumentBlock]:
        """الكشف عن مناطق الرؤوس والتذييلات / Detect header and footer regions."""
        results: list[DocumentBlock] = []

        # مناطق الرؤوس والتذييلات (أعلى/أسفل 10% من الصفحة)
        header_zone = int(height * 0.10)
        footer_zone = int(height * 0.90)

        for region_bbox, _ in text_regions:
            if region_bbox.y < header_zone:
                results.append(DocumentBlock(
                    block_type=BlockType.HEADER,
                    bbox=region_bbox,
                    confidence=0.6,
                ))
            elif region_bbox.y + region_bbox.height > footer_zone:
                results.append(DocumentBlock(
                    block_type=BlockType.FOOTER,
                    bbox=region_bbox,
                    confidence=0.6,
                ))

        return results

    @staticmethod
    def _compute_average_text_height(
        regions: list[tuple[BBox, int]],
    ) -> float:
        """حساب متوسط ارتفاع النص / Compute average text height."""
        if not regions:
            return 0.0
        heights = [h for _, h in regions]
        return float(sum(heights) / len(heights))

    @staticmethod
    def _merge_overlapping_blocks(
        blocks: list[tuple[BBox, int]],
        overlap_threshold: float = 0.3,
    ) -> list[tuple[BBox, int]]:
        """دمج الكتل المتداخلة / Merge overlapping or nearby blocks."""
        if not blocks:
            return []

        blocks.sort(key=lambda b: b[0].y)

        merged: list[tuple[BBox, int]] = [blocks[0]]

        for bbox, height in blocks[1:]:
            prev_bbox, prev_height = merged[-1]

            iou = prev_bbox.iou(bbox)
            y_overlap = min(prev_bbox.y2, bbox.y2) - max(prev_bbox.y, bbox.y)
            y_overlap_ratio = y_overlap / max(min(prev_bbox.height, bbox.height), 1)

            if iou > overlap_threshold or y_overlap_ratio > 0.5:
                x1 = min(prev_bbox.x, bbox.x)
                y1 = min(prev_bbox.y, bbox.y)
                x2 = max(prev_bbox.x2, bbox.x2)
                y2 = max(prev_bbox.y2, bbox.y2)
                new_bbox = BBox(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
                new_height = max(prev_height, height)
                merged[-1] = (new_bbox, new_height)
            else:
                merged.append((bbox, height))

        return merged
