#!/usr/bin/env python3
"""
tests/test_e2e.py - End-to-end test for HTR pipeline

Minimal E2E test that verifies the complete pipeline
using synthetic data and mocked model inference.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestE2EHTRPipeline(unittest.TestCase):
    """
    End-to-end test for the Arabic HTR pipeline.

    This test creates synthetic document images and runs them
    through the complete pipeline (line segmentation → word segmentation
    → text recognition (mocked) → dotted recovery).
    """

    @classmethod
    def setUpClass(cls):
        """Create test resources once for all tests."""
        # Create synthetic document
        cls.test_doc = cls._create_synthetic_document()
        cls.test_line = cls._create_synthetic_line()

    @staticmethod
    def _create_synthetic_document() -> np.ndarray:
        """Create a realistic-looking synthetic Arabic document image."""
        img = np.ones((400, 600, 3), dtype=np.uint8) * 245  # Slightly off-white

        # Add margins
        img[10:390, 10:590, :] = 255

        # Draw text lines with varying heights
        lines = [
            (40, 65), (90, 112), (140, 165), (195, 218),
            (250, 275), (305, 328), (340, 365)
        ]

        for y_start, y_end in lines:
            # Add ink-like noise
            line_region = img[y_start:y_end, 60:540, :]
            noise = np.random.randint(0, 30, line_region.shape, dtype=np.uint8)
            line_region = np.clip(
                line_region.astype(np.int16) - noise,
                0, 255
            ).astype(np.uint8)

            # Add text blocks (darker regions simulating words)
            num_words = np.random.randint(3, 7)
            x_positions = np.linspace(60, 400, num_words).astype(int)
            for x in x_positions:
                word_width = np.random.randint(30, 80)
                img[y_start+5:y_end-5, x:x+word_width, :] = np.random.randint(
                    20, 60, (y_end-y_start-10, word_width, 3), dtype=np.uint8
                )

        return img

    @staticmethod
    def _create_synthetic_line() -> np.ndarray:
        """Create a synthetic text line image."""
        img = np.ones((50, 500, 3), dtype=np.uint8) * 250

        # Draw word blocks
        words = [(20, 90), (120, 210), (240, 330), (360, 450)]
        for x_start, x_end in words:
            h = np.random.randint(25, 45)
            y_start = (50 - h) // 2
            img[y_start:y_start+h, x_start:x_end, :] = np.random.randint(
                15, 50, (h, x_end-x_start, 3), dtype=np.uint8
            )

        return img

    def test_line_segmentation_e2e(self):
        """E2E: Document → Line segments."""
        from modules.vision.htr.line_segmenter import LineSegmenter

        segmenter = LineSegmenter(method="projection")
        lines = segmenter.segment(self.test_doc)

        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0, "Should detect at least one line")

        for line in lines:
            self.assertIsInstance(line, Image.Image)
            self.assertGreater(line.width, 0)
            self.assertGreater(line.height, 0)

    def test_word_segmentation_e2e(self):
        """E2E: Text line → Word segments."""
        from modules.vision.htr.word_segmenter import WordSegmenter

        segmenter = WordSegmenter()
        words = segmenter.segment(self.test_line)

        self.assertIsInstance(words, list)

        for word in words:
            self.assertIsInstance(word, Image.Image)
            self.assertGreater(word.width, 0)
            self.assertGreater(word.height, 0)

    def test_dotted_recovery_e2e(self):
        """E2E: Raw OCR text → Corrected text."""
        from modules.vision.htr.dotted_recovery import DottedRecovery

        recovery = DottedRecovery()

        # Simulate OCR output with dot errors
        raw_text = "فم البيت الكبري المدرسة"
        corrected = recovery.correct(raw_text)

        self.assertIsInstance(corrected, str)
        self.assertGreater(len(corrected), 0)

    def test_pipeline_config_e2e(self):
        """E2E: Pipeline configuration."""
        from modules.vision.htr.arabic_htr import ArabicHTR

        htr = ArabicHTR(
            checkpoint="training/outputs/best_model",
            line_method="projection",
            num_beams=4,
            enable_dotted_recovery=True,
            word_segmentation=False,
        )

        config = htr.get_config()
        self.assertEqual(config["checkpoint"], "training/outputs/best_model")
        self.assertEqual(config["line_method"], "projection")
        self.assertEqual(config["num_beams"], 4)

    def test_full_pipeline_with_mock(self):
        """E2E: Full pipeline with mocked TrOCR."""
        from modules.vision.htr.arabic_htr import ArabicHTR
        from modules.vision.htr.trocr_finetuned import TrOCRFineTuned

        # Mock the TrOCR recognize method
        original_recognize = TrOCRFineTuned.recognize

        def mock_recognize(self, image, return_confidence=False, skip_cache=False):
            if return_confidence:
                return {"text": "بسم الله الرحمن الرحيم", "inference_time": 0.01}
            return "بسم الله الرحمن الرحيم"

        with patch.object(TrOCRFineTuned, 'recognize', mock_recognize):
            htr = ArabicHTR(
                checkpoint="dummy",
                device="cpu",
                line_method="projection",
            )

            result = htr.recognize(self.test_doc, return_confidence=True)

            self.assertIn("full_text", result)
            self.assertIn("lines", result)
            self.assertIn("total_lines", result)
            self.assertGreater(result["total_lines"], 0)
            self.assertIsInstance(result["full_text"], str)
            self.assertGreater(len(result["full_text"]), 0)

    def test_training_config_e2e(self):
        """E2E: Training configuration is valid."""
        import yaml

        config_path = project_root / "training" / "configs" / "trocr_lora_arabic.yaml"
        if not config_path.exists():
            self.skipTest("Config file not found")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Validate required sections
        self.assertIn("model", config)
        self.assertIn("training", config)
        self.assertIn("data", config)

        # Validate model config
        self.assertIn("name", config["model"])
        self.assertIn("lora", config["model"])
        self.assertIn("r", config["model"]["lora"])
        self.assertIn("target_modules", config["model"]["lora"])

        # Validate training config
        self.assertIn("output_dir", config["training"])
        self.assertIn("num_train_epochs", config["training"])
        self.assertIn("learning_rate", config["training"])

    def test_requirements_file_e2e(self):
        """E2E: Requirements file exists and is readable."""
        req_path = project_root / "requirements-training.txt"
        if not req_path.exists():
            self.skipTest("Requirements file not found")

        with open(req_path) as f:
            content = f.read()

        # Check for key dependencies
        self.assertIn("torch", content)
        self.assertIn("transformers", content)
        self.assertIn("peft", content)


class TestE2ESyntheticData(unittest.TestCase):
    """E2E test for synthetic data generation."""

    def test_synthetic_text_generation(self):
        """Test Arabic text generation utilities."""
        spec = __import__('importlib.util')
        gen_script = project_root / "training" / "scripts" / "generate_synthetic_data.py"
        if not gen_script.exists():
            self.skipTest("Generate script not found")

        import importlib.util
        mod_spec = importlib.util.spec_from_file_location("gen", str(gen_script))
        mod = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(mod)

        # Test random text generation
        text = mod.generate_random_arabic_text(min_words=2, max_words=5)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)

        # Test line text generation
        line_text = mod.generate_line_text(min_chars=10, max_chars=60)
        self.assertIsInstance(line_text, str)
        self.assertGreater(len(line_text), 0)

    def test_font_discovery(self):
        """Test font discovery mechanism."""
        gen_script = project_root / "training" / "scripts" / "generate_synthetic_data.py"
        if not gen_script.exists():
            self.skipTest("Generate script not found")

        import importlib.util
        mod_spec = importlib.util.spec_from_file_location("gen", str(gen_script))
        mod = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(mod)

        fonts = mod.discover_fonts([])
        self.assertIsInstance(fonts, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
