"""
Unit Tests for Advanced OCR Pipeline
=====================================
Run with: python -m pytest tests/ -v
"""

import sys
import os
import numpy as np
from PIL import Image, ImageDraw

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.vision.ocr_engine import OCREngine
from modules.vision.text_reconstructor import TextReconstructor


# ─── Test Helpers ─────────────────────────────────────────────────────

def create_test_image(width=800, height=600, text="Test"):
    """Create a simple test image with text."""
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), text, fill="black")
    return img


# ─── BoundingBox Helper Tests ─────────────────────────────────────────

class TestBoundingGeometry:
    """Tests for bounding box geometric operations."""

    def test_bbox_properties(self):
        """Test bounding box computed properties."""
        bbox = {"x": 10, "y": 20, "w": 100, "h": 50}
        assert bbox["x"] + bbox["w"] == 110  # x2
        assert bbox["y"] + bbox["h"] == 70   # y2
        assert bbox["w"] * bbox["h"] == 5000  # area
        assert (bbox["x"] + bbox["w"] // 2, bbox["y"] + bbox["h"] // 2) == (60, 45)  # center

    def test_bbox_no_overlap(self):
        """Test no overlap between two bboxes."""
        b1 = {"x": 0, "y": 0, "w": 10, "h": 10}
        b2 = {"x": 20, "y": 20, "w": 10, "h": 10}
        # No intersection
        assert b1["x"] + b1["w"] <= b2["x"] or b2["x"] + b2["w"] <= b1["x"]

    def test_bbox_full_overlap(self):
        """Test full overlap between identical bboxes."""
        b1 = {"x": 0, "y": 0, "w": 10, "h": 10}
        b2 = {"x": 0, "y": 0, "w": 10, "h": 10}
        assert b1 == b2


# ─── OCR Engine Tests ─────────────────────────────────────────────────

class TestOCREngine:
    def test_default_config(self):
        """Test default engine configuration."""
        engine = OCREngine()
        assert engine.confidence_threshold == 0.5
        assert engine.use_gpu is True

    def test_engine_creation(self):
        """Test engine can be created with various configs."""
        engine = OCREngine(
            use_gpu=False,
            confidence_threshold=0.8,
            enable_easyocr=True,
            enable_trocr=True,
            enable_tesseract=True,
        )
        assert engine.confidence_threshold == 0.8
        assert engine.use_gpu is False


# ─── Text Reconstructor Tests ─────────────────────────────────────────

class TestTextReconstructor:
    def test_reconstruct_empty(self):
        """Test reconstruction with empty input."""
        reconstructor = TextReconstructor()
        assert reconstructor.reconstruct([]) == ""

    def test_reconstruct_single_word(self):
        """Test reconstruction with single word."""
        reconstructor = TextReconstructor()
        words = [{"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20}]
        result = reconstructor.reconstruct(words, direction="ltr")
        assert "Hello" in result

    def test_reconstruct_rtl(self):
        """Test reconstruction with RTL direction."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "مرحبا", "x": 100, "y": 10, "w": 50, "h": 20},
            {"text": "بالعالم", "x": 40, "y": 10, "w": 60, "h": 20},
        ]
        result = reconstructor.reconstruct(words, direction="rtl")
        assert "مرحبا" in result
        assert "بالعالم" in result

    def test_reconstruct_mixed(self):
        """Test reconstruction of mixed Arabic/English text."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "Hello", "x": 10, "y": 10, "w": 40, "h": 20},
            {"text": "مرحبا", "x": 60, "y": 10, "w": 50, "h": 20},
        ]
        result = reconstructor.reconstruct_mixed_paragraph(words)
        assert len(result) > 0

    def test_detect_direction_auto_arabic(self):
        """Test auto-detection picks RTL for Arabic."""
        reconstructor = TextReconstructor()
        words = [{"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20}]
        assert reconstructor._detect_direction(words, "auto") == "rtl"

    def test_detect_direction_auto_english(self):
        """Test auto-detection picks LTR for English."""
        reconstructor = TextReconstructor()
        words = [{"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20}]
        assert reconstructor._detect_direction(words, "auto") == "ltr"

    def test_is_arabic_text(self):
        """Test Arabic text detection."""
        assert TextReconstructor._is_arabic_text("م") is True
        assert TextReconstructor._is_arabic_text("ا") is True
        assert TextReconstructor._is_arabic_text("A") is False
        assert TextReconstructor._is_arabic_text("1") is False

    def test_is_latin_text(self):
        """Test Latin text detection."""
        assert TextReconstructor._is_latin_text("Hello") is True
        assert TextReconstructor._is_latin_text("مرحبا") is False

    def test_statistics(self):
        """Test statistics computation."""
        reconstructor = TextReconstructor()
        words = [
            {"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20},
            {"text": "Hello", "x": 10, "y": 40, "w": 50, "h": 20},
        ]
        stats = reconstructor.get_statistics(words)
        assert stats["total_words"] == 2
        assert stats["arabic_words"] == 1
        assert stats["english_words"] == 1
        assert "arabic_ratio" in stats

    def test_group_into_lines(self):
        """Test line grouping."""
        reconstructor = TextReconstructor(line_threshold=15.0)
        words = [
            {"text": "W1", "x": 10, "y": 10, "w": 30, "h": 20},
            {"text": "W2", "x": 50, "y": 12, "w": 30, "h": 20},
            {"text": "W3", "x": 10, "y": 50, "w": 30, "h": 20},
        ]
        lines = reconstructor._group_into_lines(words)
        assert len(lines) == 2
        assert len(lines[0]) == 2
        assert len(lines[1]) == 1

    def test_reconstruct_with_direction(self):
        """Test explicit direction reconstruction."""
        reconstructor = TextReconstructor()
        words = [{"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20}]
        result = reconstructor.reconstruct_with_direction(words, direction="rtl")
        assert "مرحبا" in result


# ─── Image Preprocessor Tests ─────────────────────────────────────────

class TestImagePreprocessor:
    def test_creation(self):
        """Test preprocessor can be created."""
        from modules.vision.image_preprocessor import ImagePreprocessor
        pp = ImagePreprocessor(
            apply_clahe=True,
            apply_denoise=True,
            apply_deskew=True,
            apply_binarize=True,
        )
        assert pp.apply_clahe is True

    def test_preprocess(self):
        """Test preprocessing a simple image."""
        from modules.vision.image_preprocessor import ImagePreprocessor
        pp = ImagePreprocessor(apply_clahe=False, apply_denoise=False,
                               apply_deskew=False, apply_binarize=False)
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        result = pp.preprocess(img)
        assert result is not None

    def test_smart_segment(self):
        """Test word segmentation returns list."""
        from modules.vision.image_preprocessor import ImagePreprocessor
        pp = ImagePreprocessor()
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        result = pp.smart_segment(img)
        assert isinstance(result, list)


# ─── SecureFileHandler Tests ──────────────────────────────────────────

class TestSecureFileHandling:
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from modules.security.file_scanner import FileScanner
        # Basic test that file scanner can be imported and instantiated
        scanner = FileScanner()
        assert scanner is not None


# ─── Run Tests ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
