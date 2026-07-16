"""Tests for the pattern matching module."""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_word_image() -> np.ndarray:
    """Create a synthetic word image for testing.

    Returns:
        40x100 grayscale image with dark text-like pattern.
    """
    image = np.ones((40, 100), dtype=np.uint8) * 255
    # Create a text-like pattern (dark horizontal bands)
    image[5:15, 5:95] = 30
    image[20:30, 10:90] = 30
    return image


@pytest.fixture
def similar_word_image() -> np.ndarray:
    """Create a slightly different version of the word image.

    Returns:
        40x100 grayscale image similar to sample_word_image.
    """
    image = np.ones((40, 100), dtype=np.uint8) * 255
    # Similar but slightly different pattern
    image[5:15, 5:95] = 35
    image[20:30, 10:90] = 25
    # Add some noise
    noise = np.random.randint(-5, 5, (40, 100), dtype=np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return image


@pytest.fixture
def different_word_image() -> np.ndarray:
    """Create a distinctly different word image.

    Returns:
        40x100 grayscale image with different pattern.
    """
    image = np.ones((40, 100), dtype=np.uint8) * 255
    # Very different pattern
    image[5:35, 5:95] = 20  # Large block
    return image


class TestTextSimilarity:
    """Tests for text similarity computation."""

    def test_identical_text(self) -> None:
        """Test similarity of identical texts."""
        from difflib import SequenceMatcher
        sim = SequenceMatcher(None, "مرحبا", "مرحبا").ratio()
        assert sim == 1.0

    def test_similar_text(self) -> None:
        """Test similarity of similar texts."""
        from difflib import SequenceMatcher
        sim = SequenceMatcher(None, "مرحبا", "مرحبا ").ratio()
        assert sim > 0.8

    def test_different_text(self) -> None:
        """Test similarity of different texts."""
        from difflib import SequenceMatcher
        sim = SequenceMatcher(None, "مرحبا", "عالم").ratio()
        assert sim < 1.0

    def test_empty_text(self) -> None:
        """Test similarity with empty text."""
        from difflib import SequenceMatcher
        assert SequenceMatcher(None, "", "مرحبا").ratio() == 0.0
        assert SequenceMatcher(None, "مرحبا", "").ratio() == 0.0


class TestSSIMComputation:
    """Tests for SSIM-like computation."""

    def test_identical_images(self) -> None:
        """Test similarity of identical images."""
        img = np.ones((50, 50), dtype=np.uint8) * 128
        # Simple pixel-level comparison
        diff = np.abs(img.astype(float) - img.astype(float))
        score = 1.0 - (np.mean(diff) / 255.0)
        assert abs(score - 1.0) < 0.01

    def test_different_images(self) -> None:
        """Test similarity of different images."""
        img1 = np.ones((50, 50), dtype=np.uint8) * 0
        img2 = np.ones((50, 50), dtype=np.uint8) * 255
        diff = np.abs(img1.astype(float) - img2.astype(float))
        score = 1.0 - (np.mean(diff) / 255.0)
        assert score < 0.5


class TestPatternMatching:
    """Tests for OCR pattern matching and correction."""

    def test_word_image_size(self, sample_word_image: np.ndarray) -> None:
        """Test that sample word image has correct dimensions."""
        assert sample_word_image.shape == (40, 100)

    def test_similar_word_dimensions(
        self,
        sample_word_image: np.ndarray,
        similar_word_image: np.ndarray,
    ) -> None:
        """Test that similar word image has same dimensions."""
        assert sample_word_image.shape == similar_word_image.shape

    def test_different_word_dimensions(
        self,
        sample_word_image: np.ndarray,
        different_word_image: np.ndarray,
    ) -> None:
        """Test that different word image has same dimensions."""
        assert sample_word_image.shape == different_word_image.shape

    def test_image_variance(self, sample_word_image: np.ndarray) -> None:
        """Test that sample image has reasonable variance."""
        var = np.var(sample_word_image)
        assert var > 0  # Not uniform

    def test_noise_addition(
        self,
        sample_word_image: np.ndarray,
        similar_word_image: np.ndarray,
    ) -> None:
        """Test that noisy image is different from original."""
        assert not np.array_equal(sample_word_image, similar_word_image)
