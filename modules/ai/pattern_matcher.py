"""
OmniFile AI Processor — Pattern Matching Engine
=================================================
Source: arabic-ocr-pro/ai/pattern_matcher.py

Uses SSIM (Structural Similarity Index) to compare new OCR word images
against stored patterns from the pattern database. When a match is found,
the stored correct label can replace the OCR output.

This enables the system to learn from user corrections: when a user
corrects "المملكك" to "المملكة", the corrected word image is stored
as a pattern. Future occurrences of similar-looking word images will
be automatically corrected.
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Lazy import for skimage to avoid hard dependency at module load
_skimage_ssim = None


def _get_ssim_fn():
    """Lazily import and cache the SSIM function."""
    global _skimage_ssim
    if _skimage_ssim is None:
        try:
            from skimage.metrics import structural_similarity
            _skimage_ssim = structural_similarity
        except ImportError:
            logger.warning(
                "scikit-image not installed. SSIM matching unavailable. "
                "Install with: pip install scikit-image"
            )
            _skimage_ssim = False  # sentinel
    return _skimage_ssim if _skimage_ssim else None


class PatternMatch:
    """Result of a pattern matching operation.

    Attributes:
        pattern_id: ID of the matched pattern in the database.
        label: Correct text label from the matched pattern.
        confidence: SSIM similarity score (0.0 to 1.0).
        pattern_image: Decoded pattern image (numpy array).
    """

    def __init__(
        self,
        pattern_id: int,
        label: str,
        confidence: float,
        pattern_image: Optional[np.ndarray] = None,
    ) -> None:
        """Initialize a pattern match result.

        Args:
            pattern_id: Database ID of the matched pattern.
            label: Correct text label.
            confidence: Similarity confidence score.
            pattern_image: Decoded image of the pattern.
        """
        self.pattern_id = pattern_id
        self.label = label
        self.confidence = confidence
        self.pattern_image = pattern_image

    def __repr__(self) -> str:
        return (
            f"PatternMatch(id={self.pattern_id}, "
            f"label='{self.label}', conf={self.confidence:.3f})"
        )


class PatternMatcher:
    """SSIM-based pattern matching engine.

    Compares word images against stored patterns to find matches
    and suggest corrections based on previously learned corrections.

    Attributes:
        db: Pattern database instance.
        threshold: Minimum SSIM score to consider a match valid.
        _patterns_cache: In-memory cache of loaded patterns.
    """

    def __init__(
        self,
        db: Optional["PatternDatabase"] = None,  # type: ignore[type-arg]
        db_path: str = "data/corrections.db",
        threshold: float = 0.85,
    ) -> None:
        """Initialize the pattern matcher.

        Args:
            db: Pattern database instance. Creates a new one if None.
            db_path: Path to the database (used only if db is None).
            threshold: Minimum SSIM threshold for accepting matches.
        """
        # Lazy import to avoid circular dependency
        if db is None:
            from modules.ai.pattern_db import PatternDatabase
            db = PatternDatabase(db_path)

        self.db = db
        self.threshold = threshold
        self._patterns_cache: list[dict] = []

    # ------------------------------------------------------------------
    # Loading patterns
    # ------------------------------------------------------------------

    def load_patterns(self, label_filter: Optional[str] = None) -> int:
        """Load patterns from the database into memory cache.

        Loads pattern images and their labels for fast matching.
        Should be called before batch matching operations.

        Args:
            label_filter: Optional label to filter patterns.

        Returns:
            Number of patterns loaded.
        """
        patterns = self.db.get_patterns(label=label_filter, limit=5000)
        self._patterns_cache = patterns
        logger.info(f"Loaded {len(self._patterns_cache)} patterns for matching")
        return len(self._patterns_cache)

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def match_word(
        self,
        word_image: np.ndarray,
        label_filter: Optional[str] = None,
    ) -> Optional[PatternMatch]:
        """Find the best matching pattern for a word image.

        Compares the input word image against all cached patterns
        using SSIM and returns the best match above the threshold.

        Args:
            word_image: Cropped word image (grayscale or BGR).
            label_filter: Optional label to filter search.

        Returns:
            PatternMatch if a match is found, None otherwise.
        """
        ssim_fn = _get_ssim_fn()
        if ssim_fn is None:
            logger.debug("SSIM not available — skipping image matching")
            return None

        # Convert to grayscale if needed
        if len(word_image.shape) == 3:
            gray_word = cv2.cvtColor(word_image, cv2.COLOR_BGR2GRAY)
        else:
            gray_word = word_image.copy()

        # Ensure patterns are loaded
        if not self._patterns_cache:
            self.load_patterns(label_filter)

        best_match: Optional[PatternMatch] = None
        best_score = -1.0

        for pattern in self._patterns_cache:
            # Filter by label if specified
            if label_filter and pattern["label"] != label_filter:
                continue

            # Skip patterns without image data
            if pattern["image_data"] is None:
                continue

            # Decode pattern image
            pattern_image = self._decode_pattern_image(pattern)
            if pattern_image is None:
                continue

            # Resize to match dimensions for comparison
            resized_word, resized_pattern = self._resize_for_comparison(
                gray_word, pattern_image
            )

            # Compute SSIM
            score = self._compute_ssim(resized_word, resized_pattern, ssim_fn)

            if score > best_score:
                best_score = score
                best_match = PatternMatch(
                    pattern_id=pattern["id"],
                    label=pattern["label"],
                    confidence=score,
                    pattern_image=resized_pattern,
                )

        # Check threshold
        if best_match and best_match.confidence >= self.threshold:
            try:
                self.db.increment_pattern_use(best_match.pattern_id)
            except Exception:
                pass

            logger.debug(
                f"Pattern matched: '{best_match.label}' "
                f"(score={best_match.confidence:.3f})"
            )
            return best_match

        return None

    def match_text_corrections(self, text: str) -> list[dict]:
        """Look up text-based corrections from the database.

        Checks the corrections table for exact or similar text matches.

        Args:
            text: OCR text to look up corrections for.

        Returns:
            List of correction dictionaries with original, corrected,
            and confidence.
        """
        # Try exact match first
        exact = self.db.find_correction(text)
        if exact:
            return [{
                "original": exact["original_text"],
                "corrected": exact["corrected_text"],
                "confidence": 1.0,
                "source": "exact",
            }]

        # Try corrections with similar original text
        all_corrections = self.db.get_corrections(limit=100)
        matches: list[dict] = []

        for corr in all_corrections:
            if corr["original_text"] == text:
                matches.append({
                    "original": corr["original_text"],
                    "corrected": corr["corrected_text"],
                    "confidence": 1.0,
                    "source": "exact",
                })
            elif self._text_similarity(text, corr["original_text"]) > 0.8:
                matches.append({
                    "original": corr["original_text"],
                    "corrected": corr["corrected_text"],
                    "confidence": self._text_similarity(
                        text, corr["original_text"]
                    ),
                    "source": "fuzzy",
                })

        # Sort by confidence
        matches.sort(key=lambda m: m["confidence"], reverse=True)
        return matches

    # ------------------------------------------------------------------
    # Storing patterns
    # ------------------------------------------------------------------

    def store_word_pattern(
        self,
        label: str,
        word_image: np.ndarray,
        ocr_text: str = "",
        confidence: float = 0.0,
        source_engine: str = "",
    ) -> int:
        """Store a word pattern image in the database.

        Used after user correction to save the corrected word image
        as a pattern for future matching.

        Args:
            label: Correct text (user-provided).
            word_image: Cropped word image to store.
            ocr_text: Original OCR text.
            confidence: Original OCR confidence.
            source_engine: OCR engine that produced the result.

        Returns:
            Pattern ID in the database.
        """
        # Convert to grayscale for storage efficiency
        if len(word_image.shape) == 3:
            gray = cv2.cvtColor(word_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = word_image

        # Resize to a standard size for consistency
        target_height = 40
        scale = target_height / max(gray.shape[0], 1)
        target_width = max(int(gray.shape[1] * scale), 10)
        resized = cv2.resize(gray, (target_width, target_height))

        # Encode as PNG
        success, encoded = cv2.imencode(".png", resized)
        if not success:
            logger.error("Failed to encode pattern image")
            return -1

        image_bytes = encoded.tobytes()

        return self.db.add_pattern(
            label=label,
            image_data=image_bytes,
            image_width=target_width,
            image_height=target_height,
            ocr_text=ocr_text,
            confidence=confidence,
            source_engine=source_engine,
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict:
        """Get pattern matching statistics.

        Returns:
            Dictionary with pattern count, correction count, and other stats.
        """
        stats = self.db.get_all_stats()
        stats["cached_patterns"] = len(self._patterns_cache)
        stats["threshold"] = self.threshold
        return stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_pattern_image(pattern: dict) -> Optional[np.ndarray]:
        """Decode a pattern image from stored bytes.

        Args:
            pattern: Pattern dictionary with image_data field.

        Returns:
            Decoded grayscale image, or None if decoding fails.
        """
        try:
            if pattern["image_data"] is None:
                return None

            np_array = np.frombuffer(pattern["image_data"], dtype=np.uint8)
            image = cv2.imdecode(np_array, cv2.IMREAD_GRAYSCALE)

            if image is None:
                return None

            return image
        except Exception as exc:
            logger.debug(f"Failed to decode pattern image: {exc}")
            return None

    @staticmethod
    def _resize_for_comparison(
        img1: np.ndarray,
        img2: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Resize two images to the same dimensions for SSIM comparison.

        Resizes the smaller image to match the larger one's dimensions.

        Args:
            img1: First grayscale image.
            img2: Second grayscale image.

        Returns:
            Tuple of (resized_img1, resized_img2) with matching dimensions.
        """
        h1, w1 = img1.shape
        h2, w2 = img2.shape

        target_h = max(h1, h2)
        target_w = max(w1, w2)

        if h1 != target_h or w1 != target_w:
            img1 = cv2.resize(img1, (target_w, target_h))

        if h2 != target_h or w2 != target_w:
            img2 = cv2.resize(img2, (target_w, target_h))

        return img1, img2

    @staticmethod
    def _compute_ssim(
        img1: np.ndarray,
        img2: np.ndarray,
        ssim_fn,
    ) -> float:
        """Compute SSIM between two images.

        Args:
            img1: First grayscale image.
            img2: Second grayscale image.
            ssim_fn: The structural_similarity function reference.

        Returns:
            SSIM score between -1.0 and 1.0.
        """
        try:
            if img1.shape != img2.shape:
                return 0.0

            score = ssim_fn(img1, img2, data_range=255)
            return float(score)
        except Exception as exc:
            logger.debug(f"SSIM computation failed: {exc}")
            return 0.0

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """Compute simple character-level similarity between two strings.

        Uses character-level Jaccard similarity.

        Args:
            text1: First text string.
            text2: Second text string.

        Returns:
            Similarity ratio between 0.0 and 1.0.
        """
        if not text1 or not text2:
            return 0.0

        set1 = set(text1)
        set2 = set(text2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 1.0

        return intersection / union
