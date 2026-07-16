"""Tests for image preprocessing module."""

import numpy as np
import pytest
from modules.vision.image_preprocessor import ImagePreprocessor


@pytest.fixture
def sample_image() -> np.ndarray:
    """Create a synthetic test image (white background with black text).

    Returns:
        200x400 BGR image with synthetic text-like content.
    """
    image = np.ones((200, 400, 3), dtype=np.uint8) * 255

    # Draw some "text" as dark rectangles
    image[50:60, 50:150] = 0    # Horizontal line of "text"
    image[80:90, 50:200] = 0    # Longer line
    image[110:120, 50:180] = 0  # Medium line
    image[140:150, 50:160] = 0  # Shorter line

    # Add some noise
    noise = np.random.randint(0, 10, (200, 400, 3), dtype=np.uint8)
    image = np.clip(image.astype(np.int16) - noise.astype(np.int16), 0, 255).astype(np.uint8)

    return image


@pytest.fixture
def noisy_image() -> np.ndarray:
    """Create a noisy test image.

    Returns:
        200x400 BGR image with Gaussian noise.
    """
    image = np.ones((200, 400, 3), dtype=np.uint8) * 255
    image[70:130, 50:350] = 0  # Dark band

    # Add heavy noise
    noise = np.random.normal(0, 25, (200, 400, 3)).astype(np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return image


@pytest.fixture
def preprocessor() -> ImagePreprocessor:
    """Create a preprocessor with all steps enabled."""
    return ImagePreprocessor(
        apply_clahe=True,
        apply_denoise=True,
        apply_deskew=True,
        apply_binarize=True,
        denoise_strength=10,
    )


class TestPreprocessorInit:
    """Tests for preprocessor initialization."""

    def test_default_config(self) -> None:
        """Test default preprocessor configuration."""
        pp = ImagePreprocessor()
        assert pp.apply_clahe is True
        assert pp.apply_denoise is True
        assert pp.apply_deskew is True
        assert pp.apply_binarize is True
        assert pp.denoise_strength == 10

    def test_custom_config(self) -> None:
        """Test custom preprocessor configuration."""
        pp = ImagePreprocessor(
            apply_clahe=False,
            apply_denoise=False,
            clahe_clip_limit=3.0,
            denoise_strength=15,
        )
        assert pp.apply_clahe is False
        assert pp.apply_denoise is False
        assert pp.clahe_clip_limit == 3.0
        assert pp.denoise_strength == 15

    def test_odd_window_sizes(self) -> None:
        """Test that window sizes are forced to odd values."""
        pp = ImagePreprocessor(
            denoise_template_window=6,  # Even number
            denoise_search_window=20,    # Even number
        )
        assert pp.denoise_template_window % 2 == 1
        assert pp.denoise_search_window % 2 == 1


class TestGrayscaleConversion:
    """Tests for grayscale conversion."""

    def test_bgr_to_grayscale(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test converting a BGR image to grayscale."""
        gray = preprocessor._to_grayscale(sample_image)
        assert gray.ndim == 2
        assert gray.shape == (200, 400)

    def test_already_grayscale(self, preprocessor: ImagePreprocessor) -> None:
        """Test that grayscale input is returned unchanged."""
        gray = np.ones((100, 100), dtype=np.uint8) * 128
        result = preprocessor._to_grayscale(gray)
        assert result.shape == (100, 100)


class TestDenoising:
    """Tests for Gaussian blur denoising."""

    def test_denoise_reduces_noise(self, preprocessor: ImagePreprocessor, noisy_image: np.ndarray) -> None:
        """Test that denoising reduces noise variance."""
        gray = preprocessor._to_grayscale(noisy_image)
        denoised = preprocessor._apply_denoise(gray)

        # Denoised should have less variance in flat areas
        original_var = np.var(noisy_image[0:50, 0:50].astype(np.float64))
        denoised_var = np.var(denoised[0:50, 0:50].astype(np.float64))
        assert denoised_var <= original_var

    def test_denoise_preserves_shape(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test that denoising preserves image shape."""
        gray = preprocessor._to_grayscale(sample_image)
        result = preprocessor._apply_denoise(gray)
        assert result.shape == gray.shape


class TestBinarization:
    """Tests for Otsu threshold binarization."""

    def test_binarize_output(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test that binarization produces binary output."""
        gray = preprocessor._to_grayscale(sample_image)
        binary = preprocessor._apply_otsu(gray)

        # Check that output is single channel
        assert binary.ndim == 2

        # Check that values are binary (0 or 255)
        unique_values = set(np.unique(binary))
        assert unique_values.issubset({0, 255})

    def test_binarize_preserves_shape(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test that binarization preserves shape."""
        gray = preprocessor._to_grayscale(sample_image)
        binary = preprocessor._apply_otsu(gray)
        assert binary.shape == gray.shape


class TestCLAHE:
    """Tests for CLAHE contrast enhancement."""

    def test_clahe_output(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test that CLAHE produces valid output."""
        gray = preprocessor._to_grayscale(sample_image)
        enhanced = preprocessor._apply_clahe(gray)
        assert enhanced.shape == gray.shape
        assert enhanced.dtype == np.uint8


class TestDeskew:
    """Tests for deskew detection and correction."""

    def test_deskew_preserves_shape(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test that deskew preserves image shape."""
        gray = preprocessor._to_grayscale(sample_image)
        result = preprocessor._apply_deskew(gray)
        assert result is not None
        assert result.shape == gray.shape


class TestFullPipeline:
    """Tests for the full preprocessing pipeline."""

    def test_process_all_enabled(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test full pipeline with all steps enabled."""
        result = preprocessor.preprocess(sample_image)
        assert result is not None

    def test_process_no_steps(self, sample_image: np.ndarray) -> None:
        """Test pipeline with all steps disabled."""
        pp = ImagePreprocessor(
            apply_clahe=False,
            apply_denoise=False,
            apply_deskew=False,
            apply_binarize=False,
        )
        result = pp.preprocess(sample_image, return_numpy=True)
        np.testing.assert_array_equal(result, ImagePreprocessor._to_numpy(sample_image))

    def test_process_return_numpy(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test pipeline returning numpy array."""
        result = preprocessor.preprocess(sample_image, return_numpy=True)
        assert isinstance(result, np.ndarray)

    def test_process_return_pil(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test pipeline returning PIL image."""
        result = preprocessor.preprocess(sample_image, return_numpy=False)
        assert hasattr(result, "mode")


class TestSmartSegment:
    """Tests for word segmentation."""

    def test_segment_returns_list(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test that segmentation returns a list."""
        result = preprocessor.smart_segment(sample_image)
        assert isinstance(result, list)

    def test_get_bounding_boxes(self, preprocessor: ImagePreprocessor, sample_image: np.ndarray) -> None:
        """Test bounding box extraction."""
        result = preprocessor.get_word_bounding_boxes(sample_image)
        assert isinstance(result, list)
