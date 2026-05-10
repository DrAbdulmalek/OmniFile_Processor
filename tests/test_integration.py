#!/usr/bin/env python3
"""
tests/test_integration.py - Integration tests for HTR components

Tests component interactions without requiring GPU or model weights.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestLineSegmenterIntegration(unittest.TestCase):
    """Integration tests for line segmentation pipeline."""

    def setUp(self):
        from modules.vision.htr.line_segmenter import LineSegmenter
        self.segmenter = LineSegmenter(method="projection")

    def test_document_with_multiple_lines(self):
        """Test segmentation of document with clear line separation."""
        img = np.ones((300, 400, 3), dtype=np.uint8) * 255
        lines = [(20, 40), (70, 90), (120, 140), (170, 190), (220, 240)]
        for y_start, y_end in lines:
            img[y_start:y_end, 30:370, :] = 0

        result = self.segmenter.segment(img)
        self.assertIsInstance(result, list)
        # Should detect at least some lines
        self.assertGreater(len(result), 0)

    def test_single_line_document(self):
        """Test segmentation of document with single line."""
        img = np.ones((100, 400, 3), dtype=np.uint8) * 255
        img[30:60, 30:370, :] = 0

        result = self.segmenter.segment(img)
        self.assertGreaterEqual(len(result), 1)

    def test_empty_document(self):
        """Test segmentation of blank document."""
        img = np.ones((200, 300, 3), dtype=np.uint8) * 255
        result = self.segmenter.segment(img)
        self.assertEqual(len(result), 0)


class TestWordSegmenterIntegration(unittest.TestCase):
    """Integration tests for word segmentation."""

    def setUp(self):
        from modules.vision.htr.word_segmenter import WordSegmenter
        self.segmenter = WordSegmenter()

    def test_line_with_multiple_words(self):
        """Test word segmentation with clear word boundaries."""
        img = np.ones((50, 500, 3), dtype=np.uint8) * 255
        words = [(10, 80), (100, 180), (200, 300), (320, 420)]
        for x_start, x_end in words:
            img[8:42, x_start:x_end, :] = 0

        result = self.segmenter.segment(img)
        self.assertIsInstance(result, list)

    def test_single_word(self):
        """Test with single word."""
        img = np.ones((50, 200, 3), dtype=np.uint8) * 255
        img[8:42, 20:180, :] = 0

        result = self.segmenter.segment(img)
        self.assertGreaterEqual(len(result), 1)


class TestDottedRecoveryIntegration(unittest.TestCase):
    """Integration tests for dotted character recovery."""

    def setUp(self):
        from modules.vision.htr.dotted_recovery import DottedRecovery
        self.recovery = DottedRecovery()

    def test_sentence_correction(self):
        """Test correction of full Arabic sentence."""
        result = self.recovery.correct("ذهب الولد الى المدرسة")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_common_word_list(self):
        """Test that common Arabic words are recognized."""
        from modules.vision.htr.dotted_recovery import COMMON_ARABIC_WORDS

        self.assertIn("في", COMMON_ARABIC_WORDS)
        self.assertIn("من", COMMON_ARABIC_WORDS)
        self.assertIn("على", COMMON_ARABIC_WORDS)
        self.assertIn("الله", COMMON_ARABIC_WORDS)

    def test_dot_groups_completeness(self):
        """Test that dot group definitions are complete."""
        from modules.vision.htr.dotted_recovery import DOT_GROUPS, CHAR_TO_GROUP

        # Every character in any group should have a reverse mapping
        for base, chars in DOT_GROUPS.items():
            for ch in chars:
                self.assertIn(ch, CHAR_TO_GROUP)

    def test_contextual_correction(self):
        """Test contextual (bigram) correction."""
        # "فم" after "بسم" should ideally be corrected
        result = self.recovery.correct("بسم فم الرحمن")
        # Result should be a string
        self.assertIsInstance(result, str)


class TestModuleIntegration(unittest.TestCase):
    """Test cross-module integration."""

    def test_htr_module_structure(self):
        """Test that HTR module has correct structure."""
        htr_path = project_root / "modules" / "vision" / "htr"
        self.assertTrue(htr_path.exists())

        expected_files = [
            "__init__.py",
            "arabic_htr.py",
            "line_segmenter.py",
            "word_segmenter.py",
            "dotted_recovery.py",
            "trocr_finetuned.py",
        ]

        for f in expected_files:
            self.assertTrue(
                (htr_path / f).exists(),
                f"Missing file: {f}"
            )

    def test_training_module_structure(self):
        """Test that training module has correct structure."""
        training_path = project_root / "training"
        self.assertTrue(training_path.exists())

        expected_dirs = ["scripts", "configs", "models", "data"]
        for d in expected_dirs:
            self.assertTrue(
                (training_path / d).exists(),
                f"Missing directory: {d}"
            )

    def test_config_file_valid(self):
        """Test that config file is valid YAML."""
        import yaml
        config_path = project_root / "training" / "configs" / "trocr_lora_arabic.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            self.assertIsInstance(config, dict)


class TestEndToEndPipeline(unittest.TestCase):
    """Test end-to-end pipeline without actual ML models."""

    def test_full_pipeline_import(self):
        """Test that all pipeline components can be imported."""
        from modules.vision.htr import ArabicHTR
        from modules.vision.htr import LineSegmenter
        from modules.vision.htr import WordSegmenter
        from modules.vision.htr import DottedRecovery
        from modules.vision.htr import TrOCRFineTuned

        # All should be importable
        self.assertIsNotNone(ArabicHTR)
        self.assertIsNotNone(LineSegmenter)
        self.assertIsNotNone(WordSegmenter)
        self.assertIsNotNone(DottedRecovery)
        self.assertIsNotNone(TrOCRFineTuned)

    def test_pipeline_without_gpu(self):
        """Test that pipeline can be configured without GPU."""
        from modules.vision.htr import ArabicHTR

        htr = ArabicHTR(
            checkpoint="dummy",
            device="cpu",
            enable_dotted_recovery=True,
        )

        config = htr.get_config()
        self.assertEqual(config["checkpoint"], "dummy")
        self.assertTrue(config["enable_dotted_recovery"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
