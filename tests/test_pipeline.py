"""Tests for the OCR pipeline orchestrator."""

import json
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_image() -> np.ndarray:
    """Create a simple test image.

    Returns:
        100x200 BGR image with synthetic text regions.
    """
    image = np.ones((100, 200, 3), dtype=np.uint8) * 255
    image[20:35, 10:80] = 0    # Text line 1
    image[45:60, 10:100] = 0   # Text line 2
    image[70:85, 10:120] = 0   # Text line 3
    return image


class TestPipelineOptions:
    """Tests for pipeline configuration."""

    def test_default_engine_config(self) -> None:
        """Test default OCR engine configuration."""
        engine = __import__("modules.vision.ocr_engine", fromlist=["OCREngine"]).OCREngine()
        assert engine.confidence_threshold == 0.5
        assert engine.use_gpu is True
        assert engine.enable_easyocr is True

    def test_custom_engine_config(self) -> None:
        """Test custom OCR engine configuration."""
        engine = __import__("modules.vision.ocr_engine", fromlist=["OCREngine"]).OCREngine(
            confidence_threshold=0.8,
            use_gpu=False,
            enable_easyocr=False,
            enable_tesseract=True,
        )
        assert engine.confidence_threshold == 0.8
        assert engine.use_gpu is False
        assert engine.enable_easyocr is False


class TestTextReconstructor:
    """Tests for text reconstruction module."""

    def test_reconstruct_empty(self) -> None:
        """Test reconstruct with empty word list."""
        from modules.vision.text_reconstructor import TextReconstructor
        reconstructor = TextReconstructor()
        assert reconstructor.reconstruct([]) == ""

    def test_reconstruct_single_word(self) -> None:
        """Test reconstruct with single word."""
        from modules.vision.text_reconstructor import TextReconstructor
        reconstructor = TextReconstructor()
        words = [{"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20}]
        result = reconstructor.reconstruct(words, direction="rtl")
        assert "مرحبا" in result

    def test_reconstruct_ltr(self) -> None:
        """Test reconstruct with LTR direction."""
        from modules.vision.text_reconstructor import TextReconstructor
        reconstructor = TextReconstructor()
        words = [
            {"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20},
            {"text": "World", "x": 70, "y": 10, "w": 50, "h": 20},
        ]
        result = reconstructor.reconstruct(words, direction="ltr")
        assert "Hello" in result
        assert "World" in result

    def test_reconstruct_rtl(self) -> None:
        """Test reconstruct with RTL direction."""
        from modules.vision.text_reconstructor import TextReconstructor
        reconstructor = TextReconstructor()
        words = [
            {"text": "مرحبا", "x": 100, "y": 10, "w": 50, "h": 20},
            {"text": "بالعالم", "x": 40, "y": 10, "w": 60, "h": 20},
        ]
        result = reconstructor.reconstruct(words, direction="rtl")
        assert "مرحبا" in result
        assert "بالعالم" in result

    def test_detect_direction_arabic(self) -> None:
        """Test auto-detection of Arabic (RTL) direction."""
        from modules.vision.text_reconstructor import TextReconstructor
        reconstructor = TextReconstructor()
        words = [
            {"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20},
        ]
        direction = reconstructor._detect_direction(words, "auto")
        assert direction == "rtl"

    def test_detect_direction_english(self) -> None:
        """Test auto-detection of English (LTR) direction."""
        from modules.vision.text_reconstructor import TextReconstructor
        reconstructor = TextReconstructor()
        words = [
            {"text": "Hello", "x": 10, "y": 10, "w": 50, "h": 20},
        ]
        direction = reconstructor._detect_direction(words, "auto")
        assert direction == "ltr"

    def test_is_arabic_text(self) -> None:
        """Test Arabic text detection."""
        from modules.vision.text_reconstructor import TextReconstructor
        assert TextReconstructor._is_arabic_text("مرحبا") is True
        assert TextReconstructor._is_arabic_text("Hello") is False
        assert TextReconstructor._is_arabic_text("") is False

    def test_is_latin_text(self) -> None:
        """Test Latin text detection."""
        from modules.vision.text_reconstructor import TextReconstructor
        assert TextReconstructor._is_latin_text("Hello") is True
        assert TextReconstructor._is_latin_text("مرحبا") is False
        assert TextReconstructor._is_latin_text("") is False

    def test_statistics(self) -> None:
        """Test getting reconstruction statistics."""
        from modules.vision.text_reconstructor import TextReconstructor
        reconstructor = TextReconstructor()
        words = [
            {"text": "مرحبا", "x": 10, "y": 10, "w": 50, "h": 20},
            {"text": "Hello", "x": 10, "y": 40, "w": 50, "h": 20},
        ]
        stats = reconstructor.get_statistics(words)
        assert stats["total_words"] == 2
        assert stats["arabic_words"] == 1
        assert stats["english_words"] == 1

    def test_group_into_lines(self) -> None:
        """Test grouping words into lines."""
        from modules.vision.text_reconstructor import TextReconstructor
        reconstructor = TextReconstructor(line_threshold=15.0)
        words = [
            {"text": "Word1", "x": 10, "y": 10, "w": 50, "h": 20},
            {"text": "Word2", "x": 70, "y": 10, "w": 50, "h": 20},
            {"text": "Word3", "x": 10, "y": 50, "w": 50, "h": 20},
        ]
        lines = reconstructor._group_into_lines(words)
        assert len(lines) == 2
        assert len(lines[0]) == 2
        assert len(lines[1]) == 1


class TestImagePreprocessor:
    """Tests for image preprocessing module."""

    def test_preprocessor_creation(self) -> None:
        """Test preprocessor initialization."""
        from modules.vision.image_preprocessor import ImagePreprocessor
        pp = ImagePreprocessor(
            apply_clahe=True,
            apply_denoise=True,
            apply_deskew=True,
            apply_binarize=True,
        )
        assert pp.apply_clahe is True
        assert pp.apply_denoise is True
        assert pp.apply_deskew is True
        assert pp.apply_binarize is True

    def test_preprocessor_all_disabled(self) -> None:
        """Test preprocessor with all steps disabled."""
        from modules.vision.image_preprocessor import ImagePreprocessor
        pp = ImagePreprocessor(
            apply_clahe=False,
            apply_denoise=False,
            apply_deskew=False,
            apply_binarize=False,
        )
        assert pp.apply_clahe is False
        assert pp.apply_denoise is False

    def test_to_numpy(self, sample_image: np.ndarray) -> None:
        """Test converting image to numpy."""
        from modules.vision.image_preprocessor import ImagePreprocessor
        result = ImagePreprocessor._to_numpy(sample_image)
        assert isinstance(result, np.ndarray)
        assert result.shape == sample_image.shape

    def test_to_numpy_pil(self) -> None:
        """Test converting PIL image to numpy."""
        from PIL import Image
        from modules.vision.image_preprocessor import ImagePreprocessor
        pil_img = Image.new("RGB", (100, 100), color="white")
        result = ImagePreprocessor._to_numpy(pil_img)
        assert isinstance(result, np.ndarray)
        assert result.shape == (100, 100, 3)

    def test_ensure_odd(self) -> None:
        """Test that odd number helper works."""
        from modules.vision.image_preprocessor import ImagePreprocessor
        pp = ImagePreprocessor()
        # Verify denoise window sizes are odd
        assert pp.denoise_template_window % 2 == 1
        assert pp.denoise_search_window % 2 == 1
