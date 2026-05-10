#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/config/htr_config.py
=============================

Configurable HTR settings.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HTRConfig:
    """Handwriting recognition settings."""

    # Model
    model_path: Optional[str] = None
    base_model: str = "microsoft/trocr-large-handwritten"

    # Segmentation
    use_line_segmentation: bool = True
    use_word_segmentation: bool = True
    use_dotted_recovery: bool = True

    # Line Segmenter
    line_segmenter_type: str = "projection"  # projection, unet, contour
    min_line_height: int = 20
    gap_threshold: float = 0.1

    # Word Segmenter
    min_word_width: int = 20
    gap_threshold_factor: float = 0.3

    # Dotted Recovery
    dictionary_path: Optional[str] = None
    use_language_model: bool = True

    # Performance
    batch_size: int = 4
    device: str = "cuda"  # cuda, cpu, mps

    # Generation
    max_length: int = 128
    num_beams: int = 4
    early_stopping: bool = True


@dataclass
class OCRConfig:
    """OCR settings."""

    engine: str = "trocr"  # trocr, easyocr, tesseract, paddleocr
    language: str = "ar"
    device: str = "cuda"

    # Auto HTR for handwritten
    auto_detect_handwritten: bool = True
    htr_config: HTRConfig = field(default_factory=HTRConfig)
