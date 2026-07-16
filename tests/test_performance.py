"""
اختبارات الأداء (Performance Tests)
======================================
قياس سرعة ومعالجة الوحدات المختلفة.
"""

import pytest
import time
from unittest.mock import MagicMock, patch


class TestSpellCorrectorPerformance:
    """اختبار أداء المصحح الإملائي."""

    def test_single_word_performance(self):
        """اختبار سرعة تصحيح كلمة واحدة."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()
        
        start = time.time()
        for _ in range(100):
            corrector.correct_word("helloo")
        elapsed = time.time() - start
        
        # 100 كلمة في أقل من 2 ثانية
        assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s for 100 words"

    def test_text_correction_performance(self):
        """اختبار سرعة تصحيح نص."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()
        
        long_text = "helloo world testt samplee data " * 50
        
        start = time.time()
        result = corrector.correct_text(long_text)
        elapsed = time.time() - start
        
        assert elapsed < 5.0, f"Too slow: {elapsed:.2f}s for text correction"
        assert result["corrected_text"] is not None

    def test_batch_correction_performance(self):
        """اختبار سرعة التصحيح المتوازي."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()
        
        texts = ["helloo world testt"] * 20
        
        start = time.time()
        results = corrector.correct_batch(texts, max_workers=4)
        elapsed = time.time() - start
        
        assert len(results) == 20
        assert elapsed < 10.0, f"Batch too slow: {elapsed:.2f}s"


class TestEvaluationPerformance:
    """اختبار أداء التقييم."""

    def test_cer_performance(self):
        """اختبار سرعة حساب CER."""
        from modules.evaluation.metrics import calculate_cer
        
        ref = "This is a reference text for testing performance of the CER metric."
        hyp = "This is a hypothesis text for testing performance of the CER metric."
        
        start = time.time()
        for _ in range(100):
            calculate_cer(ref, hyp)
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"CER too slow: {elapsed:.2f}s for 100 iterations"

    def test_wer_performance(self):
        """اختبار سرعة حساب WER."""
        from modules.evaluation.metrics import calculate_wer
        
        ref = "This is a reference text for testing."
        hyp = "This is a hypothesis text for testing."
        
        start = time.time()
        for _ in range(100):
            calculate_wer(ref, hyp)
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"WER too slow: {elapsed:.2f}s for 100 iterations"


class TestImportPerformance:
    """اختبار سرعة استيراد الوحدات."""

    def test_vision_import_time(self):
        """اختبار سرعة استيراد وحدة الرؤية."""
        start = time.time()
        from modules.vision import ocr_engine
        elapsed = time.time() - start
        assert elapsed < 3.0, f"Vision module import too slow: {elapsed:.2f}s"

    def test_nlp_import_time(self):
        """اختبار سرعة استيراد وحدة NLP."""
        start = time.time()
        from modules.nlp import spell_corrector
        elapsed = time.time() - start
        assert elapsed < 3.0, f"NLP module import too slow: {elapsed:.2f}s"

    def test_config_import_time(self):
        """اختبار سرعة استيراد الإعدادات."""
        start = time.time()
        from config import OmniFileConfig
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Config import too slow: {elapsed:.2f}s"
