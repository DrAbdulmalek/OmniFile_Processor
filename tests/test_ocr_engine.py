"""Tests for the hybrid OCR engine module."""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from modules.vision.ocr_engine import OCREngine


@pytest.fixture
def sample_image() -> np.ndarray:
    """Create a simple test image.

    Returns:
        100x200 BGR white image with some dark regions.
    """
    image = np.ones((100, 200, 3), dtype=np.uint8) * 255
    image[20:40, 10:80] = 0   # Dark rectangle
    image[50:70, 10:120] = 0  # Another dark rectangle
    return image


class TestOCREngineInit:
    """Tests for OCR engine initialization."""

    def test_default_initialization(self) -> None:
        """Test engine initialization with defaults."""
        engine = OCREngine()
        assert engine.confidence_threshold == 0.5
        assert engine.use_gpu is True

    def test_custom_initialization(self) -> None:
        """Test engine initialization with custom parameters."""
        engine = OCREngine(
            use_gpu=False,
            confidence_threshold=0.7,
            enable_easyocr=True,
            enable_trocr=False,
            enable_tesseract=False,
        )
        assert engine.confidence_threshold == 0.7
        assert engine.use_gpu is False

    def test_available_engines(self) -> None:
        """Test getting available engines list."""
        engine = OCREngine()
        engines = engine.get_available_engines()
        assert isinstance(engines, list)
        assert len(engines) == 3
        for e in engines:
            assert "name" in e
            assert "available" in e
            assert "enabled" in e


class TestOCREngineRecognition:
    """Tests for the OCR recognition flow."""

    @patch("modules.vision.ocr_engine.OCREngine._load_easyocr")
    @patch("modules.vision.ocr_engine.OCREngine._ensure_pil")
    def test_recognize_no_engines_available(
        self,
        mock_ensure_pil: MagicMock,
        mock_load_easyocr: MagicMock,
        sample_image: np.ndarray,
    ) -> None:
        """Test recognition when no engines are available."""
        from PIL import Image
        mock_ensure_pil.return_value = Image.new("RGB", (200, 100))
        mock_load_easyocr.return_value = False

        engine = OCREngine(
            enable_easyocr=True,
            enable_trocr=False,
            enable_tesseract=False,
        )
        result = engine.recognize(sample_image)
        assert result["text"] == ""
        assert result["source"] == "none"


class TestOCREngineBatch:
    """Tests for batch processing."""

    @patch("modules.vision.ocr_engine.OCREngine.recognize")
    def test_recognize_batch(
        self,
        mock_recognize: MagicMock,
        sample_image: np.ndarray,
    ) -> None:
        """Test batch recognition."""
        mock_recognize.return_value = {
            "text": "مرحبا",
            "confidence": 0.9,
            "source": "mock",
            "processing_time": 0.1,
        }
        engine = OCREngine()
        results = engine.recognize_batch([sample_image, sample_image])
        assert len(results) == 2
        assert results[0]["text"] == "مرحبا"
        assert results[0]["batch_index"] == 0
        assert results[1]["batch_index"] == 1


class TestOCREngineCaching:
    """Tests for OCR result caching."""

    def test_cache_key_generation(self, sample_image: np.ndarray) -> None:
        """Test cache key generation from image."""
        from PIL import Image
        engine = OCREngine()
        pil_image = Image.fromarray(sample_image)
        key = engine._get_cache_key(pil_image)
        assert isinstance(key, str)
        assert len(key) > 0

    @patch("modules.vision.ocr_engine.OCREngine.recognize")
    @patch("modules.vision.ocr_engine.OCREngine._ensure_pil")
    def test_recognize_with_cache(
        self,
        mock_ensure_pil: MagicMock,
        mock_recognize: MagicMock,
        sample_image: np.ndarray,
    ) -> None:
        """Test cached recognition returns same result."""
        from PIL import Image
        mock_ensure_pil.return_value = Image.fromarray(sample_image)
        mock_recognize.return_value = {
            "text": "test",
            "confidence": 0.9,
            "source": "mock",
            "processing_time": 0.1,
        }
        engine = OCREngine()
        cache = {}

        result1 = engine.recognize_with_cache(sample_image, cache=cache)
        result2 = engine.recognize_with_cache(sample_image, cache=cache)

        assert result1["from_cache"] is False
        assert result2["from_cache"] is True
        assert mock_recognize.call_count == 1


class TestImageConversion:
    """Tests for image format conversion."""

    def test_ensure_pil_from_numpy(self, sample_image: np.ndarray) -> None:
        """Test converting numpy array to PIL Image."""
        result = OCREngine._ensure_pil(sample_image)
        assert hasattr(result, "mode")

    def test_ensure_pil_grayscale(self) -> None:
        """Test converting grayscale numpy array to PIL Image."""
        gray = np.ones((100, 100), dtype=np.uint8) * 128
        result = OCREngine._ensure_pil(gray)
        assert hasattr(result, "mode")
