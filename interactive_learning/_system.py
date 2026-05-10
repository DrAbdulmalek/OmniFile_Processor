#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/_system.py
================================

Main InteractiveLearningSystem class.

Separated from __init__.py to avoid circular imports.
Uses lazy initialization for all heavy components.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class InteractiveLearningSystem:
    """
    End-to-end interactive learning system for Arabic OCR/HTR.

    Integrates:
    - Model loading and management
    - Smart text segmentation
    - Online learning from user corrections
    - Security (encryption, audit logging, rate limiting)
    - Monitoring and quality assurance

    Usage:
        system = InteractiveLearningSystem()
        result = system.recognize_page(image)
        system.apply_correction("word_1", "original", "corrected")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._initialized = False

        # Lazy-loaded components
        self._model_manager = None
        self._processor = None
        self._model = None
        self._segmenter = None
        self._learner = None
        self._secure_storage = None
        self._audit_logger = None
        self._rate_limiter = None
        self._metrics = None

    def _ensure_initialized(self):
        """Initialize heavy components on first use."""
        if self._initialized:
            return

        logger.info("Initializing InteractiveLearningSystem (lazy)...")

        try:
            self._init_model_manager()
        except Exception as e:
            logger.warning(f"Model manager init failed (offline mode): {e}")

        try:
            self._init_segmenter()
        except Exception as e:
            logger.warning(f"Segmenter init failed: {e}")

        try:
            self._init_learner()
        except Exception as e:
            logger.warning(f"Learner init failed: {e}")

        try:
            self._init_security()
        except Exception as e:
            logger.warning(f"Security init failed: {e}")

        self._initialized = True
        logger.info("InteractiveLearningSystem initialized successfully")

    def _init_model_manager(self):
        """Initialize model manager and load models."""
        from .core.model_manager import ModelManager
        self._model_manager = ModelManager(cache_dir=self._config.get("cache_dir"))

        model_name = self._config.get("model_name", "trocr-base-handwritten")
        info = self._model_manager.load_model(model_name)

        # Lazy load transformers
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        self._processor = TrOCRProcessor.from_pretrained(str(info.local_path))
        self._model = VisionEncoderDecoderModel.from_pretrained(str(info.local_path))

        device = self._config.get("device", "cuda" if self._model_manager._is_gpu_available() else "cpu")
        self._model.to(device)
        self._model.eval()

    def _init_segmenter(self):
        """Initialize fast segmenter."""
        from .core.fast_segmenter import FastSegmenter
        self._segmenter = FastSegmenter(
            processor=self._processor,
            model=self._model
        )

    def _init_learner(self):
        """Initialize memory-efficient learner."""
        from .learning.efficient_learner import MemoryEfficientLearner
        cache_dir = self._config.get("learner_cache_dir", ".learner_cache")
        self._learner = MemoryEfficientLearner(
            model=self._model,
            processor=self._processor,
            cache_dir=cache_dir
        )

    def _init_security(self):
        """Initialize security components."""
        from .core.security import SecureCorrectionStorage, AuditLogger, RateLimiter

        log_dir = self._config.get("audit_log_dir", ".audit_logs")
        self._secure_storage = SecureCorrectionStorage()
        self._audit_logger = AuditLogger(log_dir=Path(log_dir))
        self._rate_limiter = RateLimiter(
            max_requests=self._config.get("rate_limit", 100),
            window_seconds=self._config.get("rate_window", 60)
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def recognize_page(self, image: np.ndarray, return_layout: bool = False) -> Dict:
        """
        Recognize a full page of handwritten Arabic text.

        Args:
            image: Input image as numpy array (H, W, 3)
            return_layout: Whether to return layout structure

        Returns:
            Dictionary with recognized text and optional layout
        """
        self._ensure_initialized()

        if self._segmenter is None:
            raise RuntimeError("Segmenter not available")

        result = self._segmenter.segment_page_from_array(image)

        output = {
            "text": result.get("full_text", ""),
            "words": result.get("words", []),
            "confidence": result.get("avg_confidence", 0.0),
            "word_count": len(result.get("words", [])),
        }

        if return_layout:
            output["layout"] = result.get("layout", None)

        return output

    def apply_correction(
        self,
        word_id: str,
        original_text: str,
        corrected_text: str,
        user_id: str = "anonymous",
        ip_address: Optional[str] = None,
        image: Optional[np.ndarray] = None,
        confidence: Optional[float] = None
    ) -> Dict:
        """
        Apply a user correction with full security.

        Args:
            word_id: Unique word identifier
            original_text: Original OCR output
            corrected_text: User-corrected text
            user_id: User identifier (will be hashed)
            ip_address: Client IP (will be hashed)
            image: Original word image for training
            confidence: OCR confidence score

        Returns:
            Dictionary with correction status
        """
        self._ensure_initialized()

        # Rate limiting
        if self._rate_limiter and not self._rate_limiter.allow_request(user_id):
            return {
                "status": "rate_limited",
                "message": "Too many corrections. Please wait."
            }

        # Input validation
        from .core.security import InputSanitizer
        original_text = InputSanitizer.sanitize_correction(original_text)
        corrected_text = InputSanitizer.sanitize_correction(corrected_text)

        if not original_text or not corrected_text:
            return {"status": "error", "message": "Invalid correction text"}

        # Audit logging
        if self._audit_logger:
            self._audit_logger.log_correction(
                user_id=user_id,
                word_id=word_id,
                original=original_text,
                corrected=corrected_text,
                ip_address=ip_address,
                confidence_before=confidence
            )

        # Secure storage
        correction_data = {
            "word_id": word_id,
            "original": original_text,
            "corrected": corrected_text,
            "user_id": user_id,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }

        if self._secure_storage:
            encrypted = self._secure_storage.encrypt_correction(correction_data)
            correction_data["encrypted"] = encrypted

        # Add to learner
        if self._learner and image is not None:
            try:
                self._learner.add_correction(
                    image=image,
                    original_text=original_text,
                    corrected_text=corrected_text,
                    confidence=confidence or 0.0
                )
            except Exception as e:
                logger.error(f"Failed to add correction to learner: {e}")

        return {
            "status": "accepted",
            "word_id": word_id,
            "original": original_text,
            "corrected": corrected_text
        }

    def train_from_corrections(self, epochs: int = 1, batch_size: int = 4) -> Dict:
        """
        Train model on accumulated corrections.

        Args:
            epochs: Number of training epochs
            batch_size: Batch size for training

        Returns:
            Training metrics
        """
        self._ensure_initialized()

        if self._learner is None:
            return {"status": "error", "message": "Learner not available"}

        metrics = self._learner.learn_from_corrections(
            epochs=epochs,
            batch_size=batch_size
        )

        # Log training
        if self._audit_logger:
            self._audit_logger.log_training(
                model_version=self._config.get("model_name", "unknown"),
                num_samples=metrics.get("num_samples", 0),
                metrics=metrics
            )

        return {"status": "completed", **metrics}

    def get_stats(self) -> Dict:
        """Get system statistics."""
        self._ensure_initialized()

        stats = {
            "model_loaded": self._model is not None,
            "corrections_pending": 0,
            "learner_cache_size": 0,
        }

        if self._learner:
            stats["corrections_pending"] = self._learner.total_corrections
            stats["learner_cache_size"] = self._learner.cache_size_mb

        if self._audit_logger:
            stats["audit_stats"] = self._audit_logger.get_stats()

        return stats
