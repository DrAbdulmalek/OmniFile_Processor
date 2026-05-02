"""
اختبارات التكامل (Integration Tests)
========================================
اختبار تفاعل الوحدات المختلفة مع بعضها.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestOCRToNLPIntegration:
    """اختبار تسلسل OCR → NLP."""

    def test_ocr_engine_initialization(self):
        """اختبار تهيئة محرك OCR."""
        from modules.vision.ocr_engine import OCREngine
        engine = OCREngine(
            enable_trocr=False,
            enable_easyocr=False,
            enable_tesseract=False,
        )
        assert engine is not None
        assert len(engine.get_available_engines()) == 0

    def test_spell_corrector_initialization(self):
        """اختبار تهيئة المصحح الإملائي."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()
        assert corrector is not None
        assert "en" in corrector.supported_languages
        assert "ar" in corrector.supported_languages
        assert "de" in corrector.supported_languages

    def test_spell_corrector_protected_terms(self):
        """اختبار حماية المصطلحات التقنية."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()
        
        # كلمات بايثون محجوزة
        assert corrector.correct_word("print") == "print"
        assert corrector.correct_word("numpy") == "numpy"
        assert corrector.correct_word("async") == "async"
        
        # أرقام
        assert corrector.correct_word("123") == "123"
        
        # مقاطع كود
        assert corrector.correct_word("my_variable") == "my_variable"

    def test_spell_corrector_english(self):
        """اختبار التصحيح الإنجليزي."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()
        
        result = corrector.correct_text("helloo world")
        assert result["corrected_text"] is not None
        assert isinstance(result["total_corrections"], int)

    def test_spell_corrector_batch(self):
        """اختبار التصحيح المتوازي."""
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()
        
        texts = ["helloo world", "testt text", "samplee data"]
        results = corrector.correct_batch(texts)
        
        assert len(results) == 3
        for result in results:
            assert "corrected_text" in result

    def test_ocr_engine_availability(self):
        """اختبار توفر المحركات."""
        from modules.vision.ocr_engine import OCREngine
        engine = OCREngine()
        
        engines = engine.get_available_engines()
        assert isinstance(engines, list)
        for e in engines:
            assert "name" in e
            assert "available" in e
            assert "enabled" in e


class TestModuleImports:
    """اختبار استيراد جميع الوحدات."""

    def test_import_vision_modules(self):
        """اختبار استيراد وحدة الرؤية."""
        from modules.vision import ocr_engine, image_preprocessor, text_reconstructor, pdf_processor
        assert ocr_engine is not None
        assert image_preprocessor is not None

    def test_import_nlp_modules(self):
        """اختبار استيراد وحدة NLP."""
        from modules.nlp import spell_corrector, translator, summarizer, language_detector
        assert spell_corrector is not None

    def test_import_evaluation(self):
        """اختبار استيراد وحدة التقييم."""
        from modules.evaluation import metrics
        assert metrics is not None

    def test_import_core_structure(self):
        """اختبار استيراد النماذج الأساسية."""
        from modules.core.structure import BBox, OCRToken, DocumentPage, Document
        assert BBox is not None
        assert OCRToken is not None

    def test_import_export(self):
        """اختبار استيراد وحدة التصدير."""
        from modules.export import exporter
        assert exporter is not None

    def test_import_security(self):
        """اختبار استيراد وحدة الأمان."""
        from modules.security import secure_file_handler, sensitive_data_scanner
        assert secure_file_handler is not None

    def test_import_rtl(self):
        """اختبار استيراد معالجة RTL."""
        from modules.nlp import arabic_rtl
        assert arabic_rtl is not None


class TestConfigIntegration:
    """اختبار تكامل الإعدادات."""

    def test_config_defaults(self):
        """اختبار الإعدادات الافتراضية."""
        from config import OmniFileConfig
        cfg = OmniFileConfig()
        
        assert cfg.enable_trocr is True
        assert cfg.enable_easyocr is True
        assert cfg.enable_tesseract is True
        assert "en" in cfg.supported_languages
        assert "ar" in cfg.supported_languages
        assert "de" in cfg.supported_languages

    def test_config_save_load(self, tmp_path):
        """اختبار حفظ وتحميل الإعدادات."""
        from config import OmniFileConfig
        cfg = OmniFileConfig(enable_paddleocr=True, fusion_strategy="voting")
        
        config_path = str(tmp_path / "test_config.json")
        cfg.save(config_path)
        
        loaded = OmniFileConfig.load(config_path)
        assert loaded.enable_paddleocr is True
        assert loaded.fusion_strategy == "voting"


class TestResultFusion:
    """اختبار دمج النتائج."""

    def test_fusion_empty_results(self):
        """اختبار دمج نتائج فارغة."""
        from modules.vision.result_fusion import ResultFusion
        fusion = ResultFusion()
        result = fusion.fuse_page_results([])
        assert result is not None

    def test_fusion_single_result(self):
        """اختبار دمج نتيجة واحدة."""
        from modules.vision.result_fusion import ResultFusion, LineResult, BoundingBox, PageResult
        fusion = ResultFusion()
        
        line = LineResult(
            text="test text",
            confidence=0.9,
            bbox=BoundingBox(x=0, y=0, width=100, height=30),
            words=[],
            block_type="paragraph",
            source_engine="easyocr"
        )
        page = PageResult(lines=[line])
        result = fusion.fuse_page_results([page])
        assert result is not None


class TestMetricsIntegration:
    """اختبار تكامل مقاييس الأداء."""

    def test_cer_perfect_match(self):
        """اختبار CER مع تطابق مثالي."""
        from modules.evaluation.metrics import calculate_cer
        cer = calculate_cer("hello world", "hello world")
        assert cer == 0.0

    def test_wer_perfect_match(self):
        """اختبار WER مع تطابق مثالي."""
        from modules.evaluation.metrics import calculate_wer
        wer = calculate_wer("hello world", "hello world")
        assert wer == 0.0

    def test_arabic_normalization(self):
        """اختبار تطبيع النص العربي."""
        from modules.evaluation.metrics import _normalize_arabic
        
        # إزالة التشكيل
        normalized = _normalize_arabic("بِسْمِ اللهِ الرَّحْمٰنِ الرَّحِيمِ")
        assert "بسم" in normalized
        
        # توحيد الألف
        normalized = _normalize_arabic("أحمد إبراهيم")
        assert "ا" in normalized
