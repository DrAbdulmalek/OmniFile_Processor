#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/core/fast_segmenter.py
===========================================

Fast page segmentation with batch OCR inference.

Uses MSER-based text region detection and batched TrOCR inference
with mixed precision (FP16) for speed.

Replaces the sequential word-by-word recognition with parallel
batch processing.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class WordBox:
    """A detected word region with OCR result."""
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    confidence: float = 0.0
    image: Optional[np.ndarray] = None


@dataclass
class LineBox:
    """A detected text line."""
    x: int
    y: int
    width: int
    height: int
    words: List[WordBox] = None
    text: str = ""
    confidence: float = 0.0

    def __post_init__(self):
        if self.words is None:
            self.words = []


class FastSegmenter:
    """
    Fast page segmenter with batched OCR inference.

    Features:
    - MSER-based text region detection (robust to noise/contrast)
    - Batch inference (16 words at a time)
    - Mixed precision (FP16) for speed
    - GPU memory management with explicit cache clearing
    - IoU-based overlapping region merging

    Accepts pre-loaded processor/model (no internal loading to avoid
    circular dependency issues).

    Usage:
        segmenter = FastSegmenter(processor=processor, model=model)
        result = segmenter.segment_page_from_array(image_array)
    """

    def __init__(
        self,
        processor: Any,
        model: Any,
        batch_size: int = 16,
        device: Optional[str] = None,
        num_beams: int = 1,
    ):
        """
        Args:
            processor: Pre-loaded TrOCRProcessor
            model: Pre-loaded VisionEncoderDecoderModel
            batch_size: Words per inference batch
            device: Device override (auto-detect if None)
            num_beams: Beam search width (1 = greedy for speed)
        """
        self.processor = processor
        self.model = model
        self.batch_size = batch_size
        self.num_beams = num_beams

        # Auto-detect device
        if device is None:
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device

    def segment_page_from_array(self, image: np.ndarray) -> Dict:
        """
        Segment and recognize a full page.

        Args:
            image: Input image as numpy array (H, W, 3) BGR or RGB

        Returns:
            Dictionary with:
            - full_text: Complete recognized text
            - words: List of WordBox objects
            - lines: List of LineBox objects
            - avg_confidence: Average confidence score
        """
        # Ensure RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            if image[:, :, 0].mean() > image[:, :, 2].mean():  # BGR detected
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detect text regions using MSER
        regions = self._detect_text_regions(image)

        if not regions:
            return {
                "full_text": "",
                "words": [],
                "lines": [],
                "avg_confidence": 0.0,
            }

        # Merge overlapping regions
        regions = self._merge_overlapping(regions, iou_threshold=0.3)

        # Extract word images
        word_boxes = []
        for (x, y, w, h) in regions:
            word_img = image[max(0, y):min(image.shape[0], y + h),
                             max(0, x):min(image.shape[1], x + w)]

            if word_img.size == 0:
                continue

            word_boxes.append(WordBox(
                x=x, y=y, width=w, height=h, image=word_img
            ))

        # Batch recognition
        if word_boxes:
            word_boxes = self._recognize_batch(word_boxes)

        # Build lines from word positions
        lines = self._build_lines(word_boxes)

        # Build full text
        line_texts = [line.text for line in lines if line.text.strip()]
        full_text = "\n".join(line_texts)

        # Compute average confidence
        confidences = [wb.confidence for wb in word_boxes if wb.confidence > 0]
        avg_conf = np.mean(confidences) if confidences else 0.0

        return {
            "full_text": full_text,
            "words": word_boxes,
            "lines": lines,
            "avg_confidence": float(avg_conf),
        }

    def _detect_text_regions(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect text regions using MSER.

        MSER (Maximally Stable Extremal Regions) is robust to:
        - Varying illumination
        - Low contrast
        - Noise
        - Different writing styles
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image

        # MSER detection
        mser = cv2.MSER_create()
        mser.setMinArea(50)
        mser.setMaxArea(int(image.shape[0] * image.shape[1] * 0.5))

        try:
            regions, _ = mser.detectRegions(gray)
        except cv2.error:
            # Fallback to connected components
            return self._detect_regions_fallback(gray)

        if regions is None or len(regions) == 0:
            return []

        # Compute bounding boxes
        boxes = []
        for region in regions:
            x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2).astype(np.int32))
            if w > 10 and h > 10:  # Filter tiny regions
                boxes.append((x, y, w, h))

        return boxes

    def _detect_regions_fallback(self, gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Fallback detection using connected components + contours."""
        # Adaptive threshold
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 10 and h > 10:
                boxes.append((x, y, w, h))

        return boxes

    def _merge_overlapping(
        self,
        boxes: List[Tuple[int, int, int, int]],
        iou_threshold: float = 0.3
    ) -> List[Tuple[int, int, int, int]]:
        """Merge overlapping bounding boxes using IoU."""
        if not boxes:
            return []

        boxes = np.array(boxes, dtype=np.float32)
        merged = True

        while merged:
            merged = False
            new_boxes = []
            used = set()

            for i in range(len(boxes)):
                if i in used:
                    continue
                x1, y1, w1, h1 = boxes[i]
                x2_max, y2_max = x1 + w1, y1 + h1

                for j in range(i + 1, len(boxes)):
                    if j in used:
                        continue

                    x2, y2, w2, h2 = boxes[j]
                    x2_max2, y2_max2 = x2 + w2, y2 + h2

                    # Compute intersection
                    ix1 = max(x1, x2)
                    iy1 = max(y1, y2)
                    ix2 = min(x2_max, x2_max2)
                    iy2 = min(y2_max, y2_max2)

                    if ix2 <= ix1 or iy2 <= iy1:
                        continue

                    intersection = (ix2 - ix1) * (iy2 - iy1)
                    area1 = w1 * h1
                    area2 = w2 * h2
                    union = area1 + area2 - intersection
                    iou = intersection / union if union > 0 else 0

                    if iou > iou_threshold:
                        # Merge boxes
                        nx1 = min(x1, x2)
                        ny1 = min(y1, y2)
                        nx2 = max(x2_max, x2_max2)
                        ny2 = max(y2_max, y2_max2)
                        boxes[i] = [nx1, ny1, nx2 - nx1, ny2 - ny1]
                        x1, y1, w1, h1 = boxes[i]
                        x2_max, y2_max = nx1 + (nx2 - nx1), ny1 + (ny2 - ny1)
                        used.add(j)
                        merged = True

                new_boxes.append(boxes[i])

            boxes = np.array(new_boxes, dtype=np.float32) if new_boxes else np.empty((0, 4))

        return [(int(b[0]), int(b[1]), int(b[2]), int(b[3])) for b in boxes]

    def _recognize_batch(self, word_boxes: List[WordBox]) -> List[WordBox]:
        """
        Recognize words in batches with mixed precision.

        Processes batch_size words at a time using FP16 for speed.
        Explicitly clears GPU cache between batches.
        """
        try:
            import torch
        except ImportError:
            logger.error("PyTorch not available for batch recognition")
            return word_boxes

        all_results = list(word_boxes)

        for i in range(0, len(all_results), self.batch_size):
            batch = all_results[i:i + self.batch_size]
            images = [wb.image for wb in batch if wb.image is not None]

            if not images:
                continue

            try:
                # Preprocess
                pixel_values = self.processor(
                    images=images, return_tensors="pt"
                ).pixel_values.to(self.device)

                # Inference with mixed precision
                with torch.no_grad():
                    if self.device == "cuda":
                        with torch.cuda.amp.autocast():
                            generated = self.model.generate(
                                pixel_values,
                                max_length=128,
                                num_beams=self.num_beams,
                                early_stopping=True if self.num_beams > 1 else False,
                                pad_token_id=self.processor.tokenizer.pad_token_id,
                            )
                    else:
                        generated = self.model.generate(
                            pixel_values,
                            max_length=128,
                            num_beams=self.num_beams,
                            early_stopping=True if self.num_beams > 1 else False,
                            pad_token_id=self.processor.tokenizer.pad_token_id,
                        )

                # Decode
                decoded = self.processor.batch_decode(
                    generated, skip_special_tokens=True
                )

                # Update word boxes
                for j, wb in enumerate(batch):
                    if wb.image is not None and j < len(decoded):
                        wb.text = decoded[j].strip()
                        wb.confidence = 0.9  # TrOCR doesn't expose per-word confidence

                # Explicit GPU cache cleanup
                if self.device == "cuda":
                    del pixel_values
                    del generated
                    torch.cuda.empty_cache()

            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    logger.warning(f"GPU OOM on batch {i}, falling back to CPU")
                    # Retry on CPU
                    try:
                        pixel_values = self.processor(
                            images=images, return_tensors="pt"
                        ).pixel_values.to("cpu")

                        with torch.no_grad():
                            generated = self.model.to("cpu").generate(
                                pixel_values,
                                max_length=128,
                                num_beams=1,
                                pad_token_id=self.processor.tokenizer.pad_token_id,
                            )

                        decoded = self.processor.batch_decode(
                            generated, skip_special_tokens=True
                        )

                        for j, wb in enumerate(batch):
                            if wb.image is not None and j < len(decoded):
                                wb.text = decoded[j].strip()
                                wb.confidence = 0.9

                        # Move back to GPU if possible
                        if self.device == "cuda":
                            self.model.to(self.device)

                    except Exception as e2:
                        logger.error(f"CPU fallback also failed: {e2}")
                else:
                    logger.error(f"Batch inference error: {e}")

        return all_results

    def _build_lines(self, word_boxes: List[WordBox]) -> List[LineBox]:
        """
        Group word boxes into text lines based on vertical position.

        Words with overlapping Y-ranges are grouped into the same line.
        Lines are sorted by Y position (top to bottom for RTL).
        """
        if not word_boxes:
            return []

        # Sort by Y position
        sorted_words = sorted(word_boxes, key=lambda w: (w.y, w.x))

        lines = []
        current_line_words = [sorted_words[0]]

        for wb in sorted_words[1:]:
            prev = current_line_words[-1]

            # Check if this word is on the same line
            # (Y overlap > 50% of word height)
            overlap_y = min(prev.y + prev.height, wb.y + wb.height) - max(prev.y, wb.y)
            min_height = min(prev.height, wb.height)

            if overlap_y > min_height * 0.5:
                current_line_words.append(wb)
            else:
                # Finalize current line
                lines.append(self._finalize_line(current_line_words))
                current_line_words = [wb]

        # Don't forget the last line
        if current_line_words:
            lines.append(self._finalize_line(current_line_words))

        return lines

    def _finalize_line(self, words: List[WordBox]) -> LineBox:
        """Create a LineBox from a list of word boxes."""
        if not words:
            return LineBox(x=0, y=0, width=0, height=0)

        # Sort by X position
        words = sorted(words, key=lambda w: w.x)

        x = min(w.x for w in words)
        y = min(w.y for w in words)
        x2 = max(w.x + w.width for w in words)
        y2 = max(w.y + w.height for w in words)

        text = " ".join(w.text for w in words if w.text)
        confidences = [w.confidence for w in words if w.confidence > 0]
        avg_conf = float(np.mean(confidences)) if confidences else 0.0

        return LineBox(
            x=x, y=y,
            width=x2 - x, height=y2 - y,
            words=words, text=text, confidence=avg_conf
        )
