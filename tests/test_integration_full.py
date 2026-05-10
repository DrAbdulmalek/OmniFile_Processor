#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_integration_full.py
==============================

اختبارات تكاملية شاملة للنظام الكامل.
Covers: Security, Monitoring, Versioning, HTR pipeline, Quality Assurance
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestSecurityModule(unittest.TestCase):
    """اختبارات وحدة الأمان."""

    def setUp(self):
        from interactive_learning.core.security import (
            SecureCorrectionStorage,
            AuditLogger,
            InputSanitizer,
            RateLimiter,
        )
        self.storage = SecureCorrectionStorage()
        self.temp_dir = tempfile.mkdtemp()
        self.audit = AuditLogger(Path(self.temp_dir) / "audit")
        self.limiter = RateLimiter(max_requests=5, window_seconds=1)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption/decryption roundtrip."""
        original = {
            "word_id": "w_001",
            "original": "فم",
            "corrected": "في",
            "confidence": 0.95,
        }
        encrypted = self.storage.encrypt_correction(original)
        decrypted = self.storage.decrypt_correction(encrypted)
        self.assertEqual(decrypted, original)

    def test_sign_and_verify(self):
        """Test HMAC signing and verification."""
        data = {"word_id": "w_002", "text": "مرحبا"}
        secret = "test_secret_key"
        signature = self.storage.sign_data(data, secret)
        self.assertTrue(self.storage.verify_signature(data, signature, secret))
        # Tampered data should fail
        tampered = {**data, "text": "متبنى"}
        self.assertFalse(self.storage.verify_signature(tampered, signature, secret))

    def test_hash_content(self):
        """Test content hashing is deterministic."""
        h1 = self.storage.hash_content("بسم الله")
        h2 = self.storage.hash_content("بسم الله")
        h3 = self.storage.hash_content("بسم الله ")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_generate_token(self):
        """Test token generation uniqueness."""
        tokens = [self.storage.generate_token() for _ in range(100)]
        self.assertEqual(len(set(tokens)), 100)

    def test_audit_log_correction(self):
        """Test audit logging for corrections."""
        self.audit.log_correction(
            user_id="user_42",
            word_id="w_001",
            original="فم",
            corrected="في",
            ip_address="192.168.1.1"
        )
        activities = self.audit.get_user_activity("user_42")
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]['action'], 'correction')

    def test_audit_log_training(self):
        """Test audit logging for training."""
        self.audit.log_training(
            model_version="v1.0.0",
            num_samples=5000,
            metrics={"cer": 0.05, "wer": 0.12},
            user_id="admin"
        )
        activities = self.audit.get_user_activity("admin", action_filter="training")
        self.assertEqual(len(activities), 1)

    def test_audit_log_access(self):
        """Test audit logging for access."""
        self.audit.log_access("user_10", "/api/ocr", "read")
        activities = self.audit.get_user_activity("user_10")
        self.assertTrue(any(a['action'] == 'access' for a in activities))

    def test_audit_user_anonymization(self):
        """Test that user IDs are hashed, not stored in plain text."""
        self.audit.log_correction("real_user_id", "w_001", "a", "b")
        with open(self.audit.current_log) as f:
            entry = json.loads(f.readline())
        self.assertNotIn("real_user_id", json.dumps(entry))
        self.assertIn(entry['user_id'], json.dumps(entry))

    def test_audit_date_filtering(self):
        """Test date range filtering."""
        today = datetime.utcnow()
        self.audit.log_correction("user_1", "w_001", "a", "b")

        # Query today only
        activities = self.audit.get_user_activity(
            "user_1",
            start_date=today - timedelta(hours=1),
            end_date=today + timedelta(hours=1)
        )
        self.assertEqual(len(activities), 1)

        # Query old dates
        activities = self.audit.get_user_activity(
            "user_1",
            start_date=today - timedelta(days=365),
            end_date=today - timedelta(days=300)
        )
        self.assertEqual(len(activities), 0)

    def test_audit_stats(self):
        """Test audit statistics."""
        self.audit.log_correction("u1", "w1", "a", "b")
        self.audit.log_correction("u2", "w2", "c", "d")
        self.audit.log_training("v1", 100, {"cer": 0.05})

        stats = self.audit.get_stats()
        self.assertEqual(stats['total_entries'], 3)
        self.assertEqual(stats['by_action']['correction'], 2)
        self.assertEqual(stats['by_action']['training'], 1)

    def test_rate_limiter(self):
        """Test rate limiting."""
        for i in range(5):
            self.assertTrue(self.limiter.allow_request("client_1"))
        # 6th request should be blocked
        self.assertFalse(self.limiter.allow_request("client_1"))
        # Different client should still work
        self.assertTrue(self.limiter.allow_request("client_2"))

    def test_rate_limiter_reset(self):
        """Test rate limiter reset."""
        for _ in range(5):
            self.limiter.allow_request("client_1")
        self.assertFalse(self.limiter.allow_request("client_1"))
        self.limiter.reset("client_1")
        self.assertTrue(self.limiter.allow_request("client_1"))

    def test_input_sanitizer(self):
        """Test input sanitization."""
        # Dangerous content should be cleaned
        clean = InputSanitizer.sanitize_correction('<script>alert("xss")</script>')
        self.assertNotIn('<script>', clean)
        self.assertNotIn('javascript:', InputSanitizer.sanitize_correction('javascript:alert(1)'))

    def test_input_sanitizer_empty(self):
        """Test empty/null input."""
        self.assertEqual(InputSanitizer.sanitize_correction(""), "")
        self.assertIsNone(InputSanitizer.sanitize_correction(None))

    def test_input_sanitizer_length_limit(self):
        """Test length truncation."""
        long_text = "أ" * 20000
        result = InputSanitizer.sanitize_correction(long_text)
        self.assertLessEqual(len(result), 10000)

    def test_file_path_validation(self):
        """Test file path validation."""
        base = tempfile.mkdtemp()
        try:
            self.assertTrue(InputSanitizer.validate_file_path(
                os.path.join(base, "safe.txt"), base
            ))
            self.assertFalse(InputSanitizer.validate_file_path(
                "/etc/passwd", base
            ))
        finally:
            os.rmdir(base)


class TestMonitoringModule(unittest.TestCase):
    """اختبارات وحدة المراقبة."""

    def setUp(self):
        from interactive_learning.core.monitoring import (
            MetricsCollector,
            PerformanceMonitor,
            QualityAssurance,
            AlertManager,
        )
        self.collector = MetricsCollector()
        self.monitor = PerformanceMonitor()
        self.qa = QualityAssurance()
        self.alerts = AlertManager()

    def test_record_and_summary(self):
        """Test metric recording and summary."""
        for i in range(100):
            self.collector.record('test_metric', float(i) / 100)

        summary = self.collector.get_summary('test_metric')
        self.assertEqual(summary['count'], 100)
        self.assertAlmostEqual(summary['min'], 0.0)
        self.assertAlmostEqual(summary['max'], 0.99)
        self.assertGreater(summary['mean'], 0.4)

    def test_metric_labels(self):
        """Test label-based metric filtering."""
        for i in range(50):
            self.collector.record('latency', 0.1 + i * 0.01, {'engine': 'trocr'})
        for i in range(50):
            self.collector.record('latency', 0.5 + i * 0.01, {'engine': 'tesseract'})

        trocr_summary = self.collector.get_summary('latency', labels={'engine': 'trocr'})
        tesseract_summary = self.collector.get_summary('latency', labels={'engine': 'tesseract'})

        self.assertEqual(trocr_summary['count'], 50)
        self.assertEqual(tesseract_summary['count'], 50)
        self.assertLess(trocr_summary['mean'], tesseract_summary['mean'])

    def test_time_series(self):
        """Test time series generation."""
        import time
        for i in range(100):
            self.collector.record('ts_metric', float(i))
            time.sleep(0.001)  # Small delay

        series = self.collector.get_time_series('ts_metric', bucket_size=0.01)
        self.assertGreater(len(series), 0)

    def test_performance_monitor(self):
        """Test operation timing."""
        self.monitor.start_operation("op_1")
        time.sleep(0.05)
        duration = self.monitor.end_operation("op_1", "ocr")
        self.assertIsNotNone(duration)
        self.assertGreaterEqual(duration, 0.04)

    def test_performance_monitor_accuracy(self):
        """Test accuracy recording."""
        self.monitor.record_accuracy("v1.0.0", 0.05, "cer")
        self.monitor.record_accuracy("v1.0.0", 0.12, "wer")

        summary = self.collector.get_summary(
            'model_accuracy', labels={'model_version': 'v1.0.0', 'metric_type': 'cer'}
        )
        self.assertEqual(summary['count'], 1)
        self.assertAlmostEqual(summary['mean'], 0.05)

    def test_quality_assurance_valid(self):
        """Test QA validation of a valid correction."""
        result = self.qa.validate_correction("فم", "في")
        self.assertTrue(result['is_valid'])
        self.assertGreater(result['score'], 0.5)

    def test_quality_assurance_empty(self):
        """Test QA rejects empty correction."""
        result = self.qa.validate_correction("original", "")
        self.assertFalse(result['is_valid'])
        self.assertEqual(result['score'], 0.0)

    def test_quality_assurance_no_change(self):
        """Test QA warns about no change."""
        result = self.qa.validate_correction("same", "same")
        self.assertIn('meaningful_change', result['checks'])
        self.assertFalse(result['checks']['meaningful_change'])

    def test_quality_assurance_custom_rule(self):
        """Test custom quality rule."""
        def arabic_only(original, corrected):
            return all('\u0600' <= c <= '\u06FF' or c.isspace() for c in corrected)

        self.qa.add_rule(arabic_only, 'arabic_only_rule')
        result = self.qa.validate_correction("a", "مرحبا")
        self.assertTrue(result['checks'].get('arabic_only_rule', False))

    def test_quality_assurance_length_ratio(self):
        """Test length ratio check."""
        result = self.qa.validate_correction("ab", "abcdefghijklmnopqrstuvwxyz")
        self.assertFalse(result['checks']['reasonable_length'])
        self.assertLess(result['score'], 1.0)

    def test_alert_manager(self):
        """Test alert triggering."""
        self.alerts.add_rule(
            'high_error', 'error_metric', 'above', 0.5, cooldown_seconds=0
        )

        for _ in range(10):
            self.collector.record('error_metric', 0.8)

        triggered = self.alerts.check_rules(self.collector)
        self.assertGreater(len(triggered), 0)
        self.assertEqual(triggered[0]['name'], 'high_error')

    def test_alert_cooldown(self):
        """Test alert cooldown."""
        self.alerts.add_rule(
            'test_alert', 'test_m', 'above', 0.0, cooldown_seconds=10
        )

        for _ in range(10):
            self.collector.record('test_m', 1.0)

        # First check triggers
        t1 = self.alerts.check_rules(self.collector)
        # Second check should be suppressed by cooldown
        t2 = self.alerts.check_rules(self.collector)
        self.assertGreater(len(t1), 0)
        self.assertEqual(len(t2), 0)

    def test_list_metrics(self):
        """Test metric listing."""
        self.collector.record('metric_a', 1.0)
        self.collector.record('metric_b', 2.0)
        names = self.collector.list_metrics()
        self.assertIn('metric_a', names)
        self.assertIn('metric_b', names)

    def test_clear_metrics(self):
        """Test metric clearing."""
        self.collector.record('clear_test', 1.0)
        self.collector.clear('clear_test')
        self.assertEqual(self.collector.get_summary('clear_test'), {})

    def test_export_json(self):
        """Test JSON export."""
        self.collector.record('export_test', 1.0)
        json_str = self.collector.export_json()
        data = json.loads(json_str)
        self.assertIn('export_test', data)


class TestVersioningModule(unittest.TestCase):
    """اختبارات وحدة إدارة الإصدارات."""

    def setUp(self):
        from interactive_learning.core.versioning import (
            SemanticVersion,
            ModelRegistry,
            DatasetVersioning,
            VersionManager,
        )
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(Path(self.temp_dir) / "models")
        self.ds_versioning = DatasetVersioning(Path(self.temp_dir) / "data")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_semantic_version_parse(self):
        """Test version parsing."""
        v = SemanticVersion.parse("1.2.3")
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 2)
        self.assertEqual(v.patch, 3)

    def test_semantic_version_bump(self):
        """Test version bumping."""
        v = SemanticVersion.parse("1.2.3")
        self.assertEqual(str(v.bump_major()), "2.0.0")
        self.assertEqual(str(v.bump_minor()), "1.3.0")
        self.assertEqual(str(v.bump_patch()), "1.2.4")

    def test_semantic_version_comparison(self):
        """Test version comparison."""
        v1 = SemanticVersion.parse("1.0.0")
        v2 = SemanticVersion.parse("2.0.0")
        v3 = SemanticVersion.parse("1.5.0")
        self.assertTrue(v1 < v2)
        self.assertTrue(v1 < v3)
        self.assertTrue(v2 > v3)

    def test_semantic_version_string_comparison(self):
        """Test comparing with strings."""
        v = SemanticVersion.parse("1.2.3")
        self.assertTrue(v == "1.2.3")
        self.assertTrue(v == "v1.2.3")
        self.assertTrue(v < "2.0.0")

    def test_model_registry_register(self):
        """Test model registration."""
        # Create a dummy checkpoint
        ckpt_dir = Path(self.temp_dir) / "checkpoint"
        ckpt_dir.mkdir()
        (ckpt_dir / "model.bin").write_bytes(b"fake model data")

        record = self.registry.register_model(
            version="1.0.0",
            checkpoint_path=str(ckpt_dir),
            metrics={"cer": 0.05, "wer": 0.12},
            description="First trained model"
        )

        self.assertEqual(record['version'], "1.0.0")
        self.assertEqual(record['metrics']['cer'], 0.05)
        self.assertTrue(len(record['model_hash']) > 0)

    def test_model_registry_duplicate_version(self):
        """Test that duplicate versions are rejected."""
        ckpt_dir = Path(self.temp_dir) / "ckpt"
        ckpt_dir.mkdir()
        (ckpt_dir / "model.bin").write_bytes(b"data")

        self.registry.register_model("1.0.0", str(ckpt_dir))
        with self.assertRaises(ValueError):
            self.registry.register_model("1.0.0", str(ckpt_dir))

    def test_model_registry_get_best(self):
        """Test getting best model by metric."""
        for i, (cer, wer) in enumerate([(0.10, 0.25), (0.05, 0.12), (0.08, 0.18)]):
            ckpt = Path(self.temp_dir) / f"ckpt_{i}"
            ckpt.mkdir()
            (ckpt / "model.bin").write_bytes(b"data")
            self.registry.register_model(
                f"1.{i}.0", str(ckpt),
                metrics={"cer": cer, "wer": wer}
            )

        best_cer = self.registry.get_best_model("cer")
        self.assertEqual(best_cer['version'], "1.1.0")

        best_wer = self.registry.get_best_model("wer")
        self.assertEqual(best_wer['version'], "1.1.0")

    def test_model_registry_history(self):
        """Test model history."""
        for i in range(3):
            ckpt = Path(self.temp_dir) / f"ckpt_h{i}"
            ckpt.mkdir()
            (ckpt / "model.bin").write_bytes(b"data")
            self.registry.register_model(f"1.{i}.0", str(ckpt))

        history = self.registry.get_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]['version'], "1.0.0")

    def test_model_registry_latest(self):
        """Test getting latest model."""
        for i in range(3):
            ckpt = Path(self.temp_dir) / f"ckpt_l{i}"
            ckpt.mkdir()
            (ckpt / "model.bin").write_bytes(b"data")
            self.registry.register_model(f"2.{i}.0", str(ckpt))

        latest = self.registry.get_latest()
        self.assertIsNotNone(latest)
        self.assertEqual(latest['version'], "2.2.0")

    def test_dataset_snapshot(self):
        """Test dataset snapshot."""
        data_dir = Path(self.temp_dir) / "data" / "train"
        data_dir.mkdir(parents=True)
        (data_dir / "image_001.png").write_bytes(b"fake image")
        (data_dir / "metadata.jsonl").write_text('{"text": "test"}\n')

        snapshot = self.ds_versioning.snapshot(
            "train", "1.0.0",
            data_path=str(data_dir),
            num_samples=100
        )

        self.assertEqual(snapshot['version'], "1.0.0")
        self.assertEqual(snapshot['file_count'], 2)
        self.assertEqual(snapshot['num_samples'], 100)

    def test_dataset_list_versions(self):
        """Test listing dataset versions."""
        for i in range(3):
            data_dir = Path(self.temp_dir) / "data" / "train"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.ds_versioning.snapshot("train", f"1.{i}.0", str(data_dir))

        versions = self.ds_versioning.list_versions("train")
        self.assertEqual(len(versions), 3)


class TestHTRPipelineIntegration(unittest.TestCase):
    """اختبارات تكامل خط أنابيب HTR."""

    def test_line_segmenter(self):
        """Test line segmentation produces results."""
        from modules.vision.htr.line_segmenter import LineSegmenter

        # Create test image with text lines
        img = np.ones((300, 400, 3), dtype=np.uint8) * 255
        for y in [30, 80, 130, 180]:
            img[y:y+20, 30:370, :] = 0

        segmenter = LineSegmenter(method="projection")
        lines = segmenter.segment(img)
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)

    def test_word_segmenter(self):
        """Test word segmentation."""
        from modules.vision.htr.word_segmenter import WordSegmenter

        img = np.ones((50, 400, 3), dtype=np.uint8) * 255
        for x in [10, 100, 200, 300]:
            img[5:45, x:x+60, :] = 0

        segmenter = WordSegmenter()
        words = segmenter.segment(img)
        self.assertIsInstance(words, list)

    def test_dotted_recovery(self):
        """Test Arabic dotted character recovery."""
        from modules.vision.htr.dotted_recovery import DottedRecovery

        recovery = DottedRecovery()
        result = recovery.correct("فم المدرسة الكبري")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_dotted_recovery_candidates(self):
        """Test word correction candidates."""
        from modules.vision.htr.dotted_recovery import DottedRecovery

        recovery = DottedRecovery()
        candidates = recovery.correct_word("فم")
        self.assertIsInstance(candidates, list)
        self.assertGreater(len(candidates), 1)

    def test_arabic_htr_config(self):
        """Test ArabicHTR pipeline configuration."""
        from modules.vision.htr import ArabicHTR

        htr = ArabicHTR(
            checkpoint="dummy",
            line_method="contour",
            num_beams=8,
            enable_dotted_recovery=False
        )

        config = htr.get_config()
        self.assertEqual(config['line_method'], 'contour')
        self.assertEqual(config['num_beams'], 8)
        self.assertFalse(config['enable_dotted_recovery'])


class TestErrorRecovery(unittest.TestCase):
    """اختبارات التعافي من الأخطاء."""

    def test_corrupted_image_handling(self):
        """Test handling corrupted images."""
        from modules.vision.htr.line_segmenter import LineSegmenter

        segmenter = LineSegmenter()
        with self.assertRaises(Exception):
            segmenter.segment("nonexistent_file.xyz")

    def test_empty_image(self):
        """Test handling blank images."""
        from modules.vision.htr.line_segmenter import LineSegmenter

        blank = np.ones((100, 100, 3), dtype=np.uint8) * 255
        segmenter = LineSegmenter(method="projection")
        lines = segmenter.segment(blank)
        self.assertEqual(len(lines), 0)

    def test_very_large_image(self):
        """Test handling large images without crashing."""
        from modules.vision.htr.line_segmenter import LineSegmenter

        large = np.ones((2000, 3000, 3), dtype=np.uint8) * 255
        segmenter = LineSegmenter(method="projection")
        start = time.time()
        lines = segmenter.segment(large)
        duration = time.time() - start
        self.assertLess(duration, 30)  # Should be fast


class TestDataIntegrity(unittest.TestCase):
    """اختبارات سلامة البيانات."""

    def test_correction_idempotency(self):
        """Test that repeated corrections are idempotent."""
        from modules.vision.htr.dotted_recovery import DottedRecovery

        recovery = DottedRecovery()
        r1 = recovery.correct("الكلية")
        r2 = recovery.correct("الكلية")
        self.assertEqual(r1, r2)

    def test_empty_string_handling(self):
        """Test empty string handling across modules."""
        from modules.vision.htr.dotted_recovery import DottedRecovery

        recovery = DottedRecovery()
        self.assertEqual(recovery.correct(""), "")
        self.assertIsNone(recovery.correct(None))

    def test_special_characters(self):
        """Test handling of special characters."""
        from interactive_learning.core.security import InputSanitizer

        # Should handle unicode, control chars, etc.
        clean = InputSanitizer.sanitize_correction("نص\twith\0null")
        self.assertNotIn('\0', clean)


if __name__ == "__main__":
    unittest.main(verbosity=2)
