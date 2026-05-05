#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF to Training Data Generator — for Handwriting Model Training
================================================================
Extracts training data from PDF files at multiple levels:
  1. Page-level images (full page renders)
  2. Word-level cropped images with text labels
  3. Character-level segmented images with character labels

Pipeline:
  PDF → Page Images → Preprocess → Segment Words → Segment Chars → Export JSONL

Usage:
  from modules.vision.pdf_to_training_data import TrainingDataGenerator
  gen = TrainingDataGenerator(output_dir="./training_data")
  stats = gen.process_pdf("notes.pdf", pages="1-10", level="character")
  # Output: training_data/page_images/, word_crops/, char_crops/, train.jsonl, val.jsonl

Author:  Dr Abdulmalek Tamer Al-husseini
License: MIT
"""

import cv2
import io
import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# ====================================================================
# Configuration
# ====================================================================

@dataclass
class TrainingDataConfig:
    """Configuration for training data generation."""
    # Output
    output_dir: str = "./training_data"

    # PDF Processing
    dpi: int = 300
    pages: str = "all"  # "all", "1-10", "1,3,5"
    pdf_backend: str = "auto"  # "auto", "pymupdf", "pdf2image"

    # Image Preprocessing
    enable_deskew: bool = True
    clahe_clip: float = 2.0
    clahe_tile: tuple = (8, 8)
    denoise_h: int = 10
    adaptive_threshold: bool = False

    # Word Segmentation
    min_word_w: int = 15
    min_word_h: int = 10
    dilation_kernel: tuple = (25, 5)
    min_word_confidence: float = 0.3

    # Character Segmentation
    char_dilation_kernel: tuple = (3, 3)
    min_char_w: int = 5
    min_char_h: int = 8
    char_padding: int = 4

    # Export
    val_ratio: float = 0.1
    max_image_width: int = 0  # 0 = no resize
    max_image_height: int = 64  # Resize char crops to height 64
    image_format: str = "png"  # "png" or "webp"
    webp_quality: int = 90

    # Augmentation
    enable_augmentation: bool = False
    augment_rotation: float = 3.0
    augment_brightness: float = 0.2
    augment_noise: float = 0.1


# ====================================================================
# PDF Page Loader
# ====================================================================

class PDFPageLoader:
    """Load PDF pages as images using PyMuPDF (preferred) or pdf2image."""

    def __init__(self, backend: str = "auto", dpi: int = 300):
        self.dpi = dpi
        self._use_fitz = True
        if backend == "pdf2image":
            self._use_fitz = False
        elif backend == "pymupdf":
            self._use_fitz = True

    def load_page(self, pdf_path: str, page_num: int) -> Optional[np.ndarray]:
        """Load a single PDF page as BGR numpy array."""
        if self._use_fitz:
            img = self._load_fitz(pdf_path, page_num)
            if img is not None:
                return img
            self._use_fitz = False
            logger.info("Falling back to pdf2image (PyMuPDF unavailable)")

        return self._load_pdf2image(pdf_path, page_num)

    def load_page_pil(self, pdf_path: str, page_num: int) -> Optional[Image.Image]:
        """Load a single PDF page as PIL Image (RGB)."""
        img_bgr = self.load_page(pdf_path, page_num)
        if img_bgr is None:
            return None
        return Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))

    def get_page_count(self, pdf_path: str) -> int:
        """Get total number of pages in PDF."""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception:
            pass
        try:
            from pdf2image import convert_from_path
            # pdf2image doesn't have a direct count, use PyMuPDF approach
            images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=72)
            return -1  # Unknown
        except Exception:
            return -1

    def _load_fitz(self, pdf_path: str, page_num: int) -> Optional[np.ndarray]:
        """Load page via PyMuPDF (10x lighter than pdf2image)."""
        try:
            import fitz
        except ImportError:
            return None

        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num - 1)
            zoom = self.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            doc.close()

            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 1:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            return img
        except Exception as e:
            logger.error("PyMuPDF failed for page %d: %s", page_num, e)
            return None

    def _load_pdf2image(self, pdf_path: str, page_num: int) -> Optional[np.ndarray]:
        """Load page via pdf2image (fallback)."""
        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.error("pdf2image not installed")
            return None

        try:
            images = convert_from_path(
                pdf_path, dpi=self.dpi,
                first_page=page_num, last_page=page_num,
            )
            if not images:
                return None
            arr = np.array(images[0])
            del images
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error("pdf2image failed for page %d: %s", page_num, e)
            return None


# ====================================================================
# Image Preprocessor
# ====================================================================

class ImagePreprocessor:
    """Preprocess images for better OCR and segmentation."""

    def __init__(self, config: TrainingDataConfig = None):
        self.config = config or TrainingDataConfig()

    def preprocess(self, img_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Full preprocessing pipeline. Returns (binary, enhanced_gray)."""
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if img_bgr.ndim == 3 else img_bgr.copy()

        if self.config.enable_deskew:
            gray = self._deskew(gray)

        gray = cv2.createCLAHE(
            clipLimit=self.config.clahe_clip,
            tileGridSize=self.config.clahe_tile,
        ).apply(gray)
        gray = cv2.fastNlMeansDenoising(gray, h=self.config.denoise_h)

        if self.config.adaptive_threshold:
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 31, 11,
            )
        else:
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        return binary, gray

    def _deskew(self, gray: np.ndarray) -> np.ndarray:
        """Correct text skew using minAreaRect."""
        coords = np.column_stack(np.where(gray < 250))
        if len(coords) < 50:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) < 0.3:
            return gray
        h, w = gray.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


# ====================================================================
# Word Segmenter
# ====================================================================

class WordSegmenter:
    """Segment preprocessed images into word-level bounding boxes."""

    def __init__(self, config: TrainingDataConfig = None):
        self.config = config or TrainingDataConfig()

    def segment(self, img_bgr: np.ndarray, binary: np.ndarray,
                detections: list = None) -> List[Tuple[int, int, int, int]]:
        """
        Segment image into word bounding boxes.

        Args:
            img_bgr: Original BGR image
            binary: Binary thresholded image
            detections: Optional EasyOCR detections [(points, text, conf), ...]

        Returns:
            List of (x, y, w, h) bounding boxes sorted by reading order
        """
        # Try EasyOCR detections first
        if detections:
            boxes = []
            for det in detections:
                pts = np.array(det[0], dtype=np.int32)
                x, y, w, h = cv2.boundingRect(pts)
                if w > self.config.min_word_w and h > self.config.min_word_h:
                    boxes.append((x, y, w, h))
            if boxes:
                return self._column_aware_sort(boxes, img_bgr.shape[1])

        # Fallback: morphological + contour
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, self.config.dilation_kernel)
        dilated = cv2.dilate(binary, kernel, iterations=1)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = [
            (x, y, w, h)
            for c in contours
            for x, y, w, h in [cv2.boundingRect(c)]
            if w > self.config.min_word_w and h > self.config.min_word_h
        ]
        return self._column_aware_sort(boxes, img_bgr.shape[1])

    def crop_words(self, img_bgr: np.ndarray, boxes: List[Tuple[int, int, int, int]]
                   ) -> List[np.ndarray]:
        """Crop word images from original BGR image."""
        crops = []
        H, W = img_bgr.shape[:2]
        for x, y, w, h in boxes:
            crop = img_bgr[max(0, y):min(H, y + h), max(0, x):min(W, x + w)]
            if crop.size > 0:
                crops.append(crop)
        return crops

    def _column_aware_sort(self, boxes, img_width: int) -> List[Tuple[int, int, int, int]]:
        """Sort boxes with column detection for multi-column layouts."""
        if len(boxes) < 6:
            return sorted(boxes, key=lambda b: (b[1], b[0]))

        gap_threshold = img_width * 0.15
        centers = sorted([(x + w / 2, i) for i, (x, y, w, h) in enumerate(boxes)])
        columns = []
        current_col = [centers[0]]

        for i in range(1, len(centers)):
            if abs(centers[i][0] - centers[i - 1][0]) > gap_threshold:
                columns.append(current_col)
                current_col = [centers[i]]
            else:
                current_col.append(centers[i])
        columns.append(current_col)

        result = []
        for col in columns:
            col_boxes = sorted(col, key=lambda c: boxes[c[1]][1])  # Sort by Y
            result.extend([boxes[c[1]] for c in col_boxes])
        return result


# ====================================================================
# Character Segmenter
# ====================================================================

class CharacterSegmenter:
    """Segment word crops into individual character images.

    Uses connected component analysis with Arabic-aware merging.
    """

    def __init__(self, config: TrainingDataConfig = None):
        self.config = config or TrainingDataConfig()

    def segment_word(self, word_crop: np.ndarray) -> List[Tuple[np.ndarray, int, int, int, int]]:
        """
        Segment a word image into individual characters.

        Returns:
            List of (char_image, x, y, w, h) tuples sorted left-to-right
        """
        if word_crop is None or word_crop.size == 0:
            return []

        # Convert to grayscale if needed
        if word_crop.ndim == 3:
            gray = cv2.cvtColor(word_crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = word_crop.copy()

        # Binarize
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Small dilation to connect broken characters (important for Arabic)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, self.config.char_dilation_kernel)
        binary = cv2.dilate(binary, kernel, iterations=1)

        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

        chars = []
        pad = self.config.char_padding
        H, W = word_crop.shape[:2]

        for i in range(1, num_labels):  # Skip background (label 0)
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]

            # Filter tiny noise
            if w < self.config.min_char_w or h < self.config.min_char_h:
                continue

            # Skip very large components (likely not characters)
            if w > W * 0.8 or h > H * 0.8:
                continue

            # Crop with padding
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(W, x + w + pad)
            y2 = min(H, y + h + pad)

            char_img = word_crop[y1:y2, x1:x2]
            if char_img.size > 0:
                chars.append((char_img, x, y, w, h))

        # Sort left-to-right by x position
        chars.sort(key=lambda c: c[1])
        return chars

    def segment_and_label(
        self,
        word_crop: np.ndarray,
        word_text: str,
    ) -> List[Tuple[np.ndarray, str]]:
        """
        Segment word into characters and match with text labels.

        Uses character width proportions to distribute text labels.

        Returns:
            List of (char_image, char_label) tuples
        """
        if not word_text or not word_text.strip():
            return []

        chars = self.segment_word(word_crop)
        if not chars:
            return []

        # If character count matches text length, assign directly
        clean_text = word_text.strip()
        if len(chars) == len(clean_text):
            return [(img, ch) for (img, _, _, _, _), ch in zip(chars, clean_text)]

        # If not matching, distribute based on character widths
        total_w = sum(w for _, _, _, w, _ in chars)
        if total_w == 0:
            return []

        labeled = []
        char_idx = 0
        accumulated_w = 0

        for i, (img, x, y, w, h) in enumerate(chars):
            proportion = w / total_w
            expected_chars = max(1, round(proportion * len(clean_text)))

            # Assign characters
            end_idx = min(char_idx + expected_chars, len(clean_text))
            assigned_text = clean_text[char_idx:end_idx]

            if len(assigned_text) == 1:
                labeled.append((img, assigned_text))
            else:
                # Multiple chars in one component — use first char as label
                labeled.append((img, assigned_text[0]))

            char_idx = end_idx
            accumulated_w += w

        return labeled


# ====================================================================
# Training Data Exporter
# ====================================================================

class TrainingDataExporter:
    """Export processed data as JSONL training datasets."""

    def __init__(self, config: TrainingDataConfig = None):
        self.config = config or TrainingDataConfig()

    def save_image(self, img: np.ndarray, path: str) -> str:
        """Save image with optional resizing. Returns the saved path."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if self.config.max_image_width or self.config.max_image_height:
            img = self._resize(img, self.config.max_image_width, self.config.max_image_height)

        if self.config.image_format == "webp":
            success, buf = cv2.imencode(".webp", img, [cv2.IMWRITE_WEBP_QUALITY, self.config.webp_quality])
        else:
            success, buf = cv2.imencode(".png", img)

        if success:
            with open(path, "wb") as f:
                f.write(buf.tobytes())
        return path

    def export_jsonl(
        self,
        records: List[Dict],
        output_path: str,
    ) -> str:
        """Export records as JSONL file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return output_path

    def split_train_val(
        self,
        records: List[Dict],
        val_ratio: float = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """Split records into train and validation sets."""
        ratio = val_ratio or self.config.val_ratio
        shuffled = list(records)
        random.shuffle(shuffled)
        split_idx = int(len(shuffled) * (1 - ratio))
        return shuffled[:split_idx], shuffled[split_idx:]

    def _resize(self, img: np.ndarray, max_w: int, max_h: int) -> np.ndarray:
        """Resize image maintaining aspect ratio."""
        h, w = img.shape[:2]
        if max_w and w > max_w:
            scale = max_w / w
            img = cv2.resize(img, (max_w, int(h * scale)))
            h, w = img.shape[:2]
        if max_h and h > max_h:
            scale = max_h / h
            img = cv2.resize(img, (int(w * scale), max_h))
        return img


# ====================================================================
# Main Generator
# ====================================================================

class TrainingDataGenerator:
    """
    Complete pipeline: PDF → Images → Words → Characters → JSONL Training Data.

    Example:
        gen = TrainingDataGenerator(output_dir="./training_output")
        stats = gen.process_pdf(
            "handwritten_notes.pdf",
            pages="1-20",
            level="word",  # "page", "word", or "character"
            ocr_texts={"1": [("word1", 0.9), ("word2", 0.8)]}  # Optional pre-computed OCR
        )
    """

    def __init__(self, config: TrainingDataConfig = None, output_dir: str = None):
        self.config = config or TrainingDataConfig()
        if output_dir:
            self.config.output_dir = output_dir
        self._loader = PDFPageLoader(self.config.pdf_backend, self.config.dpi)
        self._preprocessor = ImagePreprocessor(self.config)
        self._word_segmenter = WordSegmenter(self.config)
        self._char_segmenter = CharacterSegmenter(self.config)
        self._exporter = TrainingDataExporter(self.config)

    def process_pdf(
        self,
        pdf_path: str,
        pages: str = None,
        level: str = "word",
        ocr_engine=None,
    ) -> Dict:
        """
        Process a PDF file and generate training data.

        Args:
            pdf_path: Path to PDF file
            pages: Page range ("all", "1-10", "1,3,5")
            level: "page" (full page images), "word" (word crops), "character" (char crops)
            ocr_engine: Optional OCR engine for text labels (e.g., EasyOCR instance)

        Returns:
            Statistics dict with counts and output paths
        """
        if not os.path.isfile(pdf_path):
            logger.error("PDF not found: %s", pdf_path)
            return {"error": f"PDF not found: {pdf_path}"}

        pages = pages or self.config.pages
        page_nums = self._parse_pages(pages, pdf_path)
        if not page_nums:
            return {"error": "No valid pages to process"}

        logger.info("Processing %d pages from %s (level=%s)", len(page_nums), pdf_path, level)

        base_dir = os.path.join(self.config.output_dir, Path(pdf_path).stem)
        all_records = []
        stats = {
            "pdf_path": pdf_path,
            "level": level,
            "pages_total": len(page_nums),
            "pages_processed": 0,
            "page_images": 0,
            "word_crops": 0,
            "char_crops": 0,
            "output_dir": base_dir,
            "timestamp": datetime.now().isoformat(),
        }

        for i, pg in enumerate(page_nums):
            logger.info("Page %d/%d (page %d)", i + 1, len(page_nums), pg)

            # 1. Load page
            img_bgr = self._loader.load_page(pdf_path, pg)
            if img_bgr is None:
                logger.warning("Failed to load page %d", pg)
                continue

            stats["pages_processed"] += 1

            # Save page image
            if level in ("page", "word", "character"):
                page_dir = os.path.join(base_dir, "page_images")
                page_path = os.path.join(page_dir, f"page_{pg:04d}.{self.config.image_format}")
                self._exporter.save_image(img_bgr, page_path)
                stats["page_images"] += 1

            # 2. Preprocess
            binary, gray = self._preprocessor.preprocess(img_bgr)

            # 3. Detect words (with OCR if engine provided)
            detections = None
            if ocr_engine is not None:
                try:
                    detections = ocr_engine.readtext(img_bgr)
                except Exception as e:
                    logger.warning("OCR detection failed on page %d: %s", pg, e)

            # 4. Segment words
            boxes = self._word_segmenter.segment(img_bgr, binary, detections)
            word_crops = self._word_segmenter.crop_words(img_bgr, boxes)

            if level == "word" or level == "character":
                word_dir = os.path.join(base_dir, "word_crops")
                for j, (box, crop) in enumerate(zip(boxes, word_crops)):
                    word_path = os.path.join(word_dir, f"page{pg:04d}_word{j:04d}.{self.config.image_format}")
                    self._exporter.save_image(crop, word_path)

                    # Get text label from OCR if available
                    text_label = ""
                    if detections:
                        text_label = self._match_detection_text(detections, box)

                    rel_path = os.path.relpath(word_path, base_dir)
                    all_records.append({
                        "image": rel_path,
                        "text": text_label,
                        "page": pg,
                        "box": list(box),
                        "level": "word",
                    })
                    stats["word_crops"] += 1

            # 5. Segment characters
            if level == "character" and word_crops:
                char_dir = os.path.join(base_dir, "char_crops")
                char_count = 0

                for j, (box, crop) in enumerate(zip(boxes, word_crops)):
                    # Get word text for character labeling
                    word_text = ""
                    if detections:
                        word_text = self._match_detection_text(detections, box)

                    if not word_text:
                        continue

                    chars = self._char_segmenter.segment_and_label(crop, word_text)

                    for k, (char_img, char_label) in enumerate(chars):
                        if not char_label.strip():
                            continue

                        char_path = os.path.join(
                            char_dir,
                            f"page{pg:04d}_word{j:04d}_char{k:03d}_{char_label}.{self.config.image_format}"
                        )
                        # Normalize Arabic character for filename
                        char_path_safe = self._safe_path(char_path)
                        self._exporter.save_image(char_img, char_path_safe)

                        rel_path = os.path.relpath(char_path_safe, base_dir)
                        all_records.append({
                            "image": rel_path,
                            "text": char_label,
                            "page": pg,
                            "word_idx": j,
                            "level": "character",
                        })
                        char_count += 1

                stats["char_crops"] += char_count

            # Cleanup
            del img_bgr, binary, gray, word_crops

        # 6. Export JSONL
        if all_records:
            train, val = self._exporter.split_train_val(all_records)
            train_path = os.path.join(base_dir, "train.jsonl")
            val_path = os.path.join(base_dir, "val.jsonl")
            self._exporter.export_jsonl(train, train_path)
            self._exporter.export_jsonl(val, val_path)
            stats["train_samples"] = len(train)
            stats["val_samples"] = len(val)
            stats["train_path"] = train_path
            stats["val_path"] = val_path

        # Save summary
        summary_path = os.path.join(base_dir, "generation_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        logger.info("Done! %s", json.dumps({k: v for k, v in stats.items() if k != "error"}, indent=2))
        return stats

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _parse_pages(self, pages_str: str, pdf_path: str) -> List[int]:
        """Parse page specification string."""
        if pages_str == "all" or pages_str == "*":
            count = self._loader.get_page_count(pdf_path)
            if count > 0:
                return list(range(1, count + 1))
            return []

        nums = set()
        for part in pages_str.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    nums.update(range(int(start), int(end) + 1))
                except ValueError:
                    pass
            else:
                try:
                    nums.add(int(part))
                except ValueError:
                    pass
        return sorted(nums)

    def _match_detection_text(self, detections: list, box: Tuple[int, int, int, int]) -> str:
        """Find the text from OCR detections that best matches a bounding box."""
        if not detections:
            return ""

        bx, by, bw, bh = box
        best_text = ""
        best_iou = 0.0

        for det in detections:
            pts = np.array(det[0], dtype=np.int32)
            dx, dy, dw, dh = cv2.boundingRect(pts)
            iou = self._compute_iou(box, (dx, dy, dw, dh))
            if iou > best_iou:
                best_iou = iou
                best_text = det[1] if len(det) > 1 else ""

        return best_text.strip() if best_iou > 0.1 else ""

    @staticmethod
    def _compute_iou(b1, b2) -> float:
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        xi1, yi1 = max(x1, x2), max(y1, y2)
        xi2, yi2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
        inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        union = w1 * h1 + w2 * h2 - inter
        return inter / union if union > 0 else 0

    @staticmethod
    def _safe_path(path: str) -> str:
        """Make path safe by replacing non-ASCII characters."""
        parent = os.path.dirname(path)
        filename = os.path.basename(path)
        # Keep only ASCII + Arabic range for filename
        safe = re.sub(r'[^\w\u0600-\u06FF.\-]', '_', filename)
        return os.path.join(parent, safe)
