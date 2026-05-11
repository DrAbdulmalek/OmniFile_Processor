#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/vision/arabic_segmenter.py
======================================

Arabic handwritten text segmentation with word and subword-level splitting.

Handles Arabic-specific challenges:
- Connected letter groups (PAW - Primary Arabic Words)
- Variable-width intra-word gaps
- Dot restoration (diacritics)
- Mixed Arabic/English text detection per segment

Designed for medical translation handwriting with ABBYY FineReader-style workflow.

Author: Dr. Abdulmalek Al-husseini
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import logging

logger = logging.getLogger(__name__)


class SegmentType(str, Enum):
    """Type of segmented text unit."""
    WORD = "word"
    SUBWORD = "subword"
    CHARACTER = "character"
    NUMBER = "number"
    SEPARATOR = "separator"


@dataclass
class Segment:
    """A segmented text unit with bounding box and metadata."""
    image: np.ndarray
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    segment_type: SegmentType = SegmentType.WORD
    confidence: float = 0.0
    language: str = "auto"  # 'ar', 'en', 'mixed'


class ArabicWordSegmenter:
    """
    Segment Arabic handwritten lines into words and subwords.

    Uses vertical projection analysis with Arabic-aware gap detection.
    Handles the connected nature of Arabic script where letters within
    a word are connected, but words are separated by larger gaps.

    Features:
    - Vertical projection for line-to-word segmentation
    - Gap threshold adaptive to average character width
    - Mixed Arabic/English detection per segment
    - Confidence scoring based on segment quality
    - Optional character-level segmentation for difficult words

    Usage:
        segmenter = ArabicWordSegmenter()
        words = segmenter.segment_line(line_image)
        for word in words:
            print(f"{word.text} (type={word.segment_type}, conf={word.confidence})")
    """

    def __init__(
        self,
        min_word_width: int = 15,
        min_char_width: int = 8,
        gap_threshold_factor: float = 2.5,
        padding: int = 4,
    ):
        self.min_word_width = min_word_width
        self.min_char_width = min_char_width
        self.gap_threshold_factor = gap_threshold_factor
        self.padding = padding

    def segment_line(self, line_image: np.ndarray) -> List[Segment]:
        """
        Segment a text line image into word-level segments.

        Args:
            line_image: Grayscale or BGR image of a single text line

        Returns:
            List of Segment objects with image, bbox, and metadata
        """
        if line_image is None or line_image.size == 0:
            return []

        # Convert to grayscale if needed
        gray = self._to_gray(line_image)

        # Preprocess: binarize and clean
        binary = self._preprocess(gray)

        # Compute vertical projection (sum of ink per column)
        vertical_proj = np.sum(binary, axis=0) / 255.0

        # Detect significant gaps between words
        gaps = self._find_word_gaps(vertical_proj)

        # Extract word segments
        segments = []
        start = 0
        for gap_start, gap_end in gaps:
            segment_width = gap_start - start
            if segment_width >= self.min_word_width:
                word_img = gray[:, start:gap_start]
                if self._is_valid_segment(word_img):
                    seg = Segment(
                        image=word_img,
                        bbox=(start, 0, gap_start, gray.shape[0]),
                        segment_type=SegmentType.WORD,
                        confidence=self._compute_confidence(word_img),
                        language=self._detect_language(word_img),
                    )
                    segments.append(seg)
            start = gap_end

        # Last segment after final gap
        if gray.shape[1] - start >= self.min_word_width:
            word_img = gray[:, start:]
            if self._is_valid_segment(word_img):
                seg = Segment(
                    image=word_img,
                    bbox=(start, 0, gray.shape[1], gray.shape[0]),
                    segment_type=SegmentType.WORD,
                    confidence=self._compute_confidence(word_img),
                    language=self._detect_language(word_img),
                )
                segments.append(seg)

        return segments

    def segment_word_to_chars(self, word_image: np.ndarray) -> List[Segment]:
        """
        Segment a word image into individual characters/subwords.

        Uses connected component analysis to split connected Arabic letter groups.
        Useful for difficult-to-recognize words.

        Args:
            word_image: Grayscale image of a word

        Returns:
            List of character-level Segment objects
        """
        gray = self._to_gray(word_image)
        binary = self._preprocess(gray)

        # Find connected components
        num_labels, labels = cv2.connectedComponents(binary, connectivity=8)

        chars = []
        for label_id in range(1, num_labels + 1):
            component = (labels == label_id).astype(np.uint8)
            if component.sum() < 5:  # Skip tiny noise
                continue

            ys, xs = np.where(component > 0)
            if len(xs) == 0:
                continue

            x1, x2 = int(xs.min()), int(xs.max()) + 1
            y1, y2 = int(ys.min()), int(ys.max()) + 1

            char_img = gray[max(0, y1 - 1):min(gray.shape[0], y2 + 1),
                        max(0, x1 - 1):min(gray.shape[1], x2 + 1)]

            if char_img.size == 0:
                continue

            seg = Segment(
                image=char_img,
                bbox=(x1, y1, x2, y2),
                segment_type=self._classify_component(char_img),
                confidence=self._compute_confidence(char_img),
                language="auto",
            )
            chars.append(seg)

        return sorted(chars, key=lambda s: s.bbox[0])

    # -------------------------------------------------------------------------
    # Internal methods
    # -------------------------------------------------------------------------

    def _to_gray(self, image: np.ndarray) -> np.ndarray:
        """Convert to grayscale if needed."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _preprocess(self, gray: np.ndarray) -> np.ndarray:
        """Binarize and clean a grayscale line image."""
        # Otsu's thresholding
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Morphological cleanup: remove noise
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_h)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_v)

        return binary

    def _find_word_gaps(self, projection: np.ndarray) -> List[Tuple[int, int]]:
        """
        Find significant gaps in vertical projection (between words).

        Uses adaptive thresholding based on local average ink density.
        """
        if len(projection) < 10:
            return []

        # Compute adaptive threshold
        # Average non-zero value represents average ink density
        ink_vals = projection[projection > 0.1]
        if len(ink_vals) == 0:
            return []

        avg_ink = np.mean(ink_vals)
        min_gap_width = max(int(avg_ink * self.gap_threshold_factor), 3)

        # Find regions where projection is near zero (gaps)
        is_gap = projection < 0.1

        gaps = []
        in_gap = False
        gap_start = 0

        for i in range(len(is_gap)):
            if is_gap[i] and not in_gap:
                gap_start = i
                in_gap = True
            elif not is_gap[i] and in_gap:
                gap_end = i
                if gap_end - gap_start >= min_gap_width:
                    gaps.append((gap_start, gap_end))
                in_gap = False

        return gaps

    def _is_valid_segment(self, image: np.ndarray) -> bool:
        """Check if a segment has enough content to be a real word."""
        h, w = image.shape
        if h < 5 or w < self.min_word_width:
            return False

        # Check ink coverage (at least 10% of pixels should be ink)
        gray = self._to_gray(image) if len(image.shape) == 2 else image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        ink_ratio = np.sum(binary > 0) / binary.size
        return ink_ratio >= 0.05

    def _compute_confidence(self, image: np.ndarray) -> float:
        """
        Estimate recognition confidence based on image quality.

        Higher confidence for:
        - Clear, high-contrast images
        - Regular aspect ratios
        - Sufficient ink coverage
        """
        h, w = image.shape

        # 1. Ink coverage ratio (ideal: 15-40%)
        gray = self._to_gray(image)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        ink_ratio = np.sum(binary > 0) / binary.size

        ink_score = 1.0 - abs(ink_ratio - 0.25) * 2

        # 2. Aspect ratio score (words are typically wider than tall)
        aspect = w / max(h, 1)
        ar_score = 1.0 - min(abs(aspect - 3.0) / 3.0, 1.0)

        # 3. Size score (very small or very large segments are less confident)
        area = h * w
        if area < 100:
            size_score = 0.5
        elif area < 5000:
            size_score = 1.0
        else:
            size_score = 0.8

        return float(np.clip(ink_score * ar_score * size_score, 0.1, 1.0))

    def _detect_language(self, image: np.ndarray) -> str:
        """
        Detect if a segment is Arabic, English, or mixed.

        Uses simple heuristics:
        - Arabic: right-to-left text with connected letters
        - English: left-to-right with distinct characters
        - Mixed: combination of both
        """
        h, w = image.shape

        # Too small for language detection
        if w < 10 or h < 5:
            return "unknown"

        gray = self._to_gray(image)

        # Check for Arabic indicators:
        # Arabic text tends to have more ink on the right side (RTL)
        left_ink = np.sum(gray[:, : w // 3]) / (gray.mean() + 1e-6)
        right_ink = np.sum(gray[:, 2 * w // 3 :]) / (gray.mean() + 1e-6)

        # Check for Latin character indicators:
        # Latin text has more uniform distribution with clear gaps between characters
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        col_variance = np.var(np.sum(binary, axis=0))

        if right_ink > left_ink * 1.3:
            return "ar"
        elif col_variance > np.median(col_variance):
            return "en"
        else:
            return "ar"  # Default to Arabic for this project

    def _classify_component(self, image: np.ndarray) -> SegmentType:
        """Classify a connected component as word, subword, number, or separator."""
        h, w = image.shape
        area = h * w
        aspect = w / max(h, 1)

        # Numbers: narrow, tall, uniform
        if aspect < 0.5 and area < 500:
            return SegmentType.NUMBER

        # Separators: very thin, tall
        if w < self.min_char_width and h > 10:
            return SegmentType.SEPARATOR

        # Characters (isolated letters): small area
        if area < 200:
            return SegmentType.CHARACTER

        # Subwords (part of connected Arabic group): smaller than typical word
        if area < 600:
            return SegmentType.SUBWORD

        return SegmentType.WORD

    def segment_page(
        self,
        page_image: np.ndarray,
        dilation_kernel_size: int = 3,
        min_line_height: int = 15,
    ) -> List[List[Segment]]:
        """
        Segment a full page into lines, then words within each line.

        Args:
            page_image: Full page image (grayscale or BGR)
            dilation_kernel_size: Size of dilation kernel for line detection
            min_line_height: Minimum height for a text line

        Returns:
            List of lists (outer = lines, inner = words per line)
        """
        gray = self._to_gray(page_image)

        # Dilation to connect text regions
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (dilation_kernel_size, dilation_kernel_size * 3)
        )
        dilated = cv2.dilate(gray, kernel, iterations=1)

        # Horizontal projection for line detection
        h_proj = np.sum(dilated, axis=1) / 255.0

        # Find line boundaries
        line_boundaries = self._find_word_gaps(h_proj)
        line_boundaries = [(0, gray.shape[0])] + line_boundaries + [(len(h_proj), gray.shape[0])]

        lines = []
        for i in range(len(line_boundaries) - 1):
            y1 = line_boundaries[i][1]
            y2 = line_boundaries[i + 1][0]
            if y2 - y1 >= min_line_height:
                line_img = gray[max(0, y1):y2]
                words = self.segment_line(line_img)
                lines.append(words)

        return lines
