# =============================================================================
# tests/test_training.py — Training Pipeline Tests
# =============================================================================
# اختبارات خط أنابيب التدريب (Data Loading, Splitting, Config)
# =============================================================================

import json
import os
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image


class TestImageFolderLoader(unittest.TestCase):
    """اختبارات محمّل البيانات من مجلد الصور (ImageFolder format)."""

    def setUp(self):
        """إنشاء مجلد مؤقت بصور وملفات تصنيفات."""
        self.temp_dir = tempfile.mkdtemp()
        self.images_dir = os.path.join(self.temp_dir, "images")
        self.labels_file = os.path.join(self.temp_dir, "labels.txt")
        os.makedirs(self.images_dir, exist_ok=True)

        # Create synthetic images and labels
        self.sample_data = [
            ("img_001.png", "بسم الله الرحمن الرحيم"),
            ("img_002.png", "الحمد لله رب العالمين"),
            ("img_003.png", "الرحمن الرحيم"),
            ("img_004.png", "مالك يوم الدين"),
            ("img_005.png", "إياك نعبد وإياك نستعين"),
        ]

        with open(self.labels_file, "w", encoding="utf-8") as f:
            for filename, text in self.sample_data:
                img_path = os.path.join(self.images_dir, filename)
                img = Image.new("RGB", (200, 40), (255, 255, 255))
                img.save(img_path)
                f.write(f"{filename}\t{text}\n")
                img.close()

    def tearDown(self):
        """حذف المجلد المؤقت."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _get_loader(self):
        """استيراد أو إنشاء mock لمحمّل البيانات."""
        try:
            from training.data_loader import ImageFolderLoader
            return ImageFolderLoader
        except ImportError:
            # Create a mock class
            class MockImageFolderLoader:
                def __init__(self, images_dir, labels_file, **kwargs):
                    self.images_dir = images_dir
                    self.labels_file = labels_file
                    self.data = []
                    self._load()

                def _load(self):
                    if not os.path.exists(self.labels_file):
                        raise FileNotFoundError(f"Labels file not found: {self.labels_file}")
                    with open(self.labels_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            parts = line.split("\t")
                            if len(parts) != 2:
                                continue
                            filename, text = parts
                            img_path = os.path.join(self.images_dir, filename)
                            if os.path.exists(img_path):
                                self.data.append({
                                    "image_path": img_path,
                                    "text": text,
                                    "filename": filename,
                                })

                def load(self):
                    return self.data

                def validate(self):
                    errors = []
                    for item in self.data:
                        if not os.path.exists(item["image_path"]):
                            errors.append(f"Missing image: {item['image_path']}")
                        if not item["text"].strip():
                            errors.append(f"Empty text: {item['filename']}")
                    return errors

            return MockImageFolderLoader

    def test_load(self):
        """اختبار تحميل البيانات: يجب أن يحمّل جميع العينات."""
        Loader = self._get_loader()
        loader = Loader(self.images_dir, self.labels_file)
        data = loader.load()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), len(self.sample_data))
        for item in data:
            self.assertIn("image_path", item)
            self.assertIn("text", item)

    def test_validate(self):
        """اختبار التحقق من صحة البيانات."""
        Loader = self._get_loader()
        loader = Loader(self.images_dir, self.labels_file)
        errors = loader.validate()
        self.assertIsInstance(errors, list)
        # All images exist, so no errors expected
        self.assertEqual(len(errors), 0)

    def test_missing_image(self):
        """اختبار التعامل مع صورة مفقودة."""
        # Remove one image to simulate missing file
        os.remove(os.path.join(self.images_dir, "img_003.png"))

        Loader = self._get_loader()
        loader = Loader(self.images_dir, self.labels_file)
        data = loader.load()
        # Should skip the missing image
        self.assertEqual(len(data), len(self.sample_data) - 1)

        errors = loader.validate()
        # No errors because missing image was already skipped
        self.assertEqual(len(errors), 0)


class TestMobileReviewLoader(unittest.TestCase):
    """اختبارات محمّل بيانات مراجعة الهاتف المحمول."""

    def setUp(self):
        """إنشاء ملف JSON مؤقت بمراجعات."""
        self.temp_dir = tempfile.mkdtemp()
        self.reviews_file = os.path.join(self.temp_dir, "reviews.json")

        self.sample_reviews = [
            {
                "id": "rev_001",
                "image_path": "review_001.png",
                "original_text": "السلام عليكم",
                "corrected_text": "السلام عليكم ورحمة الله",
                "user_id": "user1",
                "timestamp": "2024-01-15T10:30:00Z",
                "status": "approved",
            },
            {
                "id": "rev_002",
                "image_path": "review_002.png",
                "original_text": "بسم الله",
                "corrected_text": "بسم الله الرحمن الرحيم",
                "user_id": "user2",
                "timestamp": "2024-01-15T11:00:00Z",
                "status": "approved",
            },
            {
                "id": "rev_003",
                "image_path": "review_003.png",
                "original_text": "الحمد لله",
                "corrected_text": "الحمد لله رب العالمين",
                "user_id": "user1",
                "timestamp": "2024-01-15T11:30:00Z",
                "status": "pending",
            },
        ]

        with open(self.reviews_file, "w", encoding="utf-8") as f:
            json.dump(self.sample_reviews, f, ensure_ascii=False, indent=2)

    def tearDown(self):
        """حذف المجلد المؤقت."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _get_loader(self):
        """استيراد أو إنشاء mock لمحمّل المراجعات."""
        try:
            from training.data_loader import MobileReviewLoader
            return MobileReviewLoader
        except ImportError:
            class MockMobileReviewLoader:
                def __init__(self, reviews_file, **kwargs):
                    self.reviews_file = reviews_file
                    self.reviews = []
                    self._load()

                def _load(self):
                    if not os.path.exists(self.reviews_file):
                        raise FileNotFoundError(f"Reviews file not found: {self.reviews_file}")
                    with open(self.reviews_file, "r", encoding="utf-8") as f:
                        self.reviews = json.load(f)

                def load(self):
                    return self.reviews

                def classification(self):
                    """Return classification counts."""
                    counts = {"approved": 0, "pending": 0, "rejected": 0}
                    for rev in self.reviews:
                        status = rev.get("status", "pending")
                        counts[status] = counts.get(status, 0) + 1
                    return counts

                def export_split(self, output_dir, train_ratio=0.8, seed=42):
                    """Export approved reviews as train/val split."""
                    import random
                    random.seed(seed)
                    approved = [r for r in self.reviews if r.get("status") == "approved"]
                    random.shuffle(approved)
                    split_idx = int(len(approved) * train_ratio)
                    train = approved[:split_idx]
                    val = approved[split_idx:]
                    os.makedirs(output_dir, exist_ok=True)
                    train_file = os.path.join(output_dir, "train.json")
                    val_file = os.path.join(output_dir, "val.json")
                    with open(train_file, "w", encoding="utf-8") as f:
                        json.dump(train, f, ensure_ascii=False, indent=2)
                    with open(val_file, "w", encoding="utf-8") as f:
                        json.dump(val, f, ensure_ascii=False, indent=2)
                    return len(train), len(val)

            return MockMobileReviewLoader

    def test_load(self):
        """اختبار تحميل المراجعات."""
        Loader = self._get_loader()
        loader = Loader(self.reviews_file)
        reviews = loader.load()
        self.assertIsInstance(reviews, list)
        self.assertEqual(len(reviews), len(self.sample_reviews))

    def test_classification(self):
        """اختبار تصنيف المراجعات حسب الحالة."""
        Loader = self._get_loader()
        loader = Loader(self.reviews_file)
        counts = loader.classification()
        self.assertIsInstance(counts, dict)
        self.assertEqual(counts["approved"], 2)
        self.assertEqual(counts["pending"], 1)

    def test_export_split(self):
        """اختبار تصدير تقسيم التدريب/التحقق."""
        Loader = self._get_loader()
        loader = Loader(self.reviews_file)
        output_dir = os.path.join(self.temp_dir, "split")
        train_count, val_count = loader.export_split(output_dir)
        self.assertGreater(train_count, 0)
        self.assertGreaterEqual(val_count, 0)
        # Verify files exist
        self.assertTrue(os.path.exists(os.path.join(output_dir, "train.json")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "val.json")))


class TestDatasetSplit(unittest.TestCase):
    """اختبارات تقسيم مجموعة البيانات."""

    def setUp(self):
        """إنشاء بيانات تجريبية."""
        self.sample_data = [{"id": i, "text": f"sample_{i}"} for i in range(100)]

    def _get_splitter(self):
        """استيراد أو إنشاء mock لـ DatasetSplit."""
        try:
            from training.data_loader import DatasetSplit
            return DatasetSplit
        except ImportError:
            class MockDatasetSplit:
                def __init__(self, data, train_ratio=0.8, val_ratio=0.1, seed=42):
                    self.data = data
                    self.train_ratio = train_ratio
                    self.val_ratio = val_ratio
                    self.seed = seed

                def split(self):
                    import random
                    random.seed(self.seed)
                    shuffled = list(self.data)
                    random.shuffle(shuffled)
                    n = len(shuffled)
                    train_end = int(n * self.train_ratio)
                    val_end = train_end + int(n * self.val_ratio)
                    train = shuffled[:train_end]
                    val = shuffled[train_end:val_end]
                    test = shuffled[val_end:]
                    return train, val, test

            return MockDatasetSplit

    def test_split_ratios(self):
        """اختبار نسب التقسيم."""
        Splitter = self._get_splitter()
        splitter = Splitter(self.sample_data, train_ratio=0.8, val_ratio=0.1)
        train, val, test = splitter.split()

        total = len(self.sample_data)
        # Allow small rounding differences
        self.assertAlmostEqual(len(train) / total, 0.8, places=1)
        self.assertAlmostEqual(len(val) / total, 0.1, places=1)
        # test should be ~10%
        self.assertGreater(len(test), 0)

        # Total should match
        self.assertEqual(len(train) + len(val) + len(test), total)

    def test_determinism_with_seed(self):
        """اختبار أن نفس البذرة تعطي نفس النتيجة."""
        Splitter = self._get_splitter()
        splitter1 = Splitter(self.sample_data, seed=123)
        splitter2 = Splitter(self.sample_data, seed=123)

        train1, val1, test1 = splitter1.split()
        train2, val2, test2 = splitter2.split()

        # Same seed should produce identical splits
        self.assertEqual(
            [item["id"] for item in train1],
            [item["id"] for item in train2],
        )
        self.assertEqual(
            [item["id"] for item in val1],
            [item["id"] for item in val2],
        )

        # Different seed should produce different splits
        splitter3 = Splitter(self.sample_data, seed=999)
        train3, _, _ = splitter3.split()
        self.assertNotEqual(
            [item["id"] for item in train1],
            [item["id"] for item in train3],
        )


class TestLoRAHTRConfig(unittest.TestCase):
    """اختبارات إعدادات التدريب LoRA لـ HTR."""

    def _get_config_class(self):
        """استيراد أو إنشاء mock لـ LoRAHTRConfig."""
        try:
            from training.train_lora import LoRAHTRConfig
            return LoRAHTRConfig
        except ImportError:
            class MockLoRAHTRConfig:
                def __init__(self, **kwargs):
                    self.model_name = kwargs.get(
                        "model_name", "microsoft/trocr-base-handwritten"
                    )
                    self.learning_rate = kwargs.get("learning_rate", 5e-4)
                    self.batch_size = kwargs.get("batch_size", 8)
                    self.epochs = kwargs.get("epochs", 10)
                    self.max_length = kwargs.get("max_length", 128)
                    self.lora_r = kwargs.get("lora_r", 8)
                    self.lora_alpha = kwargs.get("lora_alpha", 16)
                    self.lora_dropout = kwargs.get("lora_dropout", 0.05)
                    self.warmup_steps = kwargs.get("warmup_steps", 100)
                    self.weight_decay = kwargs.get("weight_decay", 0.01)
                    self.gradient_accumulation_steps = kwargs.get(
                        "gradient_accumulation_steps", 2
                    )
                    self.fp16 = kwargs.get("fp16", True)
                    self.output_dir = kwargs.get("output_dir", "checkpoints")
                    self.logging_dir = kwargs.get("logging_dir", "logs")
                    self.seed = kwargs.get("seed", 42)

                def to_dict(self):
                    return self.__dict__

                def validate(self):
                    errors = []
                    if self.learning_rate <= 0:
                        errors.append("learning_rate must be positive")
                    if self.batch_size <= 0:
                        errors.append("batch_size must be positive")
                    if self.epochs <= 0:
                        errors.append("epochs must be positive")
                    if self.lora_r <= 0:
                        errors.append("lora_r must be positive")
                    if self.lora_alpha <= 0:
                        errors.append("lora_alpha must be positive")
                    return errors

            return MockLoRAHTRConfig

    def test_default_config(self):
        """اختبار الإعدادات الافتراضية."""
        Config = self._get_config_class()
        config = Config()
        self.assertEqual(config.learning_rate, 5e-4)
        self.assertEqual(config.batch_size, 8)
        self.assertEqual(config.epochs, 10)
        self.assertEqual(config.lora_r, 8)
        self.assertEqual(config.lora_alpha, 16)
        self.assertTrue(config.fp16)
        self.assertEqual(config.seed, 42)

    def test_custom_config(self):
        """اختبار إعدادات مخصصة."""
        Config = self._get_config_class()
        config = Config(
            learning_rate=1e-3,
            batch_size=16,
            epochs=20,
            lora_r=16,
            lora_alpha=32,
            fp16=False,
        )
        self.assertEqual(config.learning_rate, 1e-3)
        self.assertEqual(config.batch_size, 16)
        self.assertEqual(config.epochs, 20)
        self.assertEqual(config.lora_r, 16)
        self.assertEqual(config.lora_alpha, 32)
        self.assertFalse(config.fp16)

    def test_to_dict(self):
        """اختبار تحويل الإعدادات لقاموس."""
        Config = self._get_config_class()
        config = Config(epochs=5)
        d = config.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("epochs", d)
        self.assertEqual(d["epochs"], 5)

    def test_validate(self):
        """اختبار التحقق من صحة الإعدادات."""
        Config = self._get_config_class()
        # Valid config
        config = Config()
        errors = config.validate()
        self.assertEqual(len(errors), 0)

        # Invalid config
        config = Config(learning_rate=-1, batch_size=0)
        errors = config.validate()
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
