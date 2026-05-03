"""
اختبارات التكامل (Integration Tests)
========================================
اختبار تفاعل الوحدات المختلفة مع بعضها.
يشمل اختبارات الوحدات القديمة + اختبارات المكونات الجديدة:
- Surya OCR
- التطبيع (normalize)
- كشف الجداول (table detection)
- معالجة اللغات المختلطة
- التصدير من JSON القياسي
"""

import json
import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch


class TestOCRToNLPIntegration:
    """اختبار تسلسل OCR -> NLP."""

    def test_ocr_engine_initialization(self):
        """اختبار تهيئة محرك OCR."""
        from modules.vision.ocr_engine import OCREngine
        engine = OCREngine(
            enable_trocr=False,
            enable_easyocr=False,
            enable_tesseract=False,
            enable_surya=False,
            enable_paddleocr=False,
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

    def test_ocr_engine_includes_surya(self):
        """اختبار تضمين Surya في قائمة المحركات."""
        from modules.vision.ocr_engine import OCREngine
        engine = OCREngine()

        engines = engine.get_available_engines()
        engine_names = [e["name"] for e in engines]
        assert "Surya" in engine_names


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

    def test_import_new_normalize(self):
        """اختبار استيراد وحدة التطبيع الجديدة."""
        from modules.vision.normalize import normalize_ocr_output
        assert normalize_ocr_output is not None

    def test_import_new_surya(self):
        """اختبار استيراد محرك Surya."""
        from modules.vision.surya_ocr import SuryaOCREngine
        assert SuryaOCREngine is not None

    def test_import_new_table_detection(self):
        """اختبار استيراد كاشف الجداول."""
        from modules.vision.table_detection import TableDetectionTransformer
        assert TableDetectionTransformer is not None

    def test_import_new_mixed_language(self):
        """اختبار استيراد معالج اللغات المختلطة."""
        from modules.nlp.mixed_language import MixedLanguageHandler
        assert MixedLanguageHandler is not None


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


class TestNormalizeOCR:
    """اختبار وحدة التطبيع الجديدة."""

    def test_normalize_basic(self):
        """اختبار التطبيع الأساسي."""
        from modules.vision.normalize import normalize_ocr_output

        raw_blocks = [
            {
                "type": "paragraph",
                "bbox": [0.1, 0.2, 0.9, 0.3],
                "text": "مرحبا بالعالم",
                "confidence": 0.95,
            },
            {
                "type": "paragraph",
                "bbox": [0.1, 0.4, 0.9, 0.5],
                "text": "Hello World",
                "confidence": 0.90,
            },
        ]

        result = normalize_ocr_output(
            raw_blocks, "test.jpg", 2480, 3508, "tesseract", ["ar", "en"]
        )

        assert "metadata" in result
        assert "pages" in result
        assert len(result["pages"]) == 1
        assert len(result["pages"][0]["blocks"]) == 2
        assert result["metadata"]["engine"] == "tesseract"
        assert result["pages"][0]["width"] == 2480
        assert result["pages"][0]["blocks"][0]["id"] == "block_1"

    def test_normalize_table(self):
        """اختبار تطبيع كتل الجداول."""
        from modules.vision.normalize import normalize_ocr_output

        raw_blocks = [
            {
                "type": "table",
                "bbox": [0.1, 0.1, 0.9, 0.5],
                "confidence": 0.85,
                "cells": [
                    ["اسم", "العمر"],
                    ["أحمد", "25"],
                    ["سارة", "30"],
                ],
            }
        ]

        result = normalize_ocr_output(
            raw_blocks, "test.jpg", 2480, 3508, "surya", ["ar"]
        )

        block = result["pages"][0]["blocks"][0]
        assert block["type"] == "table"
        assert "structure" in block
        assert block["structure"]["rows"] == 3
        assert block["structure"]["cols"] == 2
        assert len(block["structure"]["cells"]) == 6

    def test_normalize_image_with_caption(self):
        """اختبار تطبيع صور مع تسمية."""
        from modules.vision.normalize import normalize_ocr_output

        raw_blocks = [
            {
                "type": "image",
                "bbox": [0.1, 0.1, 0.9, 0.5],
                "image_file": "figure1.png",
                "caption": {
                    "text": "شكل 1: مخطط النظام",
                    "bbox": [0.2, 0.52, 0.8, 0.56],
                },
            }
        ]

        result = normalize_ocr_output(
            raw_blocks, "test.jpg", 2480, 3508, "easyocr", ["ar"]
        )

        block = result["pages"][0]["blocks"][0]
        assert block["type"] == "image"
        assert block["image_file"] == "figure1.png"
        assert "caption" in block
        assert block["caption"]["text"] == "شكل 1: مخطط النظام"

    def test_normalize_save_and_load(self, tmp_path):
        """اختبار حفظ وتحميل JSON الموحد."""
        from modules.vision.normalize import (
            normalize_ocr_output,
            save_normalized,
            load_normalized,
        )

        raw_blocks = [
            {"type": "paragraph", "bbox": [0, 0, 1, 1], "text": "test", "confidence": 0.9}
        ]
        result = normalize_ocr_output(
            raw_blocks, "test.jpg", 100, 100, "tesseract", ["en"]
        )

        json_path = str(tmp_path / "result.json")
        save_normalized(result, json_path)

        loaded = load_normalized(json_path)
        assert loaded["metadata"]["engine"] == "tesseract"
        assert len(loaded["pages"]) == 1

    def test_merge_pages(self):
        """اختبار دمج نتائج متعددة."""
        from modules.vision.normalize import normalize_ocr_output, merge_pages

        blocks1 = [{"type": "paragraph", "bbox": [0, 0, 1, 0.5], "text": "صفحة 1", "confidence": 0.9}]
        blocks2 = [{"type": "paragraph", "bbox": [0, 0, 1, 0.5], "text": "صفحة 2", "confidence": 0.9}]

        result1 = normalize_ocr_output(blocks1, "p1.jpg", 100, 100, "tesseract", ["ar"])
        result2 = normalize_ocr_output(blocks2, "p2.jpg", 100, 100, "tesseract", ["ar"])

        merged = merge_pages([result1, result2])
        assert merged["metadata"]["page_count"] == 2
        assert merged["pages"][0]["page_index"] == 0
        assert merged["pages"][1]["page_index"] == 1


class TestMixedLanguageHandler:
    """اختبار معالج اللغات المختلطة."""

    def test_detect_language_arabic(self):
        """اختبار كشف اللغة العربية."""
        from modules.nlp.mixed_language import MixedLanguageHandler
        handler = MixedLanguageHandler()
        assert handler.detect_language("مرحبا بالعالم") == "ar"

    def test_detect_language_english(self):
        """اختبار كشف اللغة الإنجليزية."""
        from modules.nlp.mixed_language import MixedLanguageHandler
        handler = MixedLanguageHandler()
        assert handler.detect_language("Hello World") == "en"

    def test_detect_language_empty(self):
        """اختبار كشف لغة نص فارغ."""
        from modules.nlp.mixed_language import MixedLanguageHandler
        handler = MixedLanguageHandler()
        assert handler.detect_language("") == "ar"

    def test_split_by_language(self):
        """اختبار تقسيم النص حسب اللغة."""
        from modules.nlp.mixed_language import MixedLanguageHandler
        handler = MixedLanguageHandler()
        segments = handler.split_by_language("مرحبا Hello")
        assert len(segments) >= 2
        # التحقق من وجود لغتين مختلفتين
        langs = [s[0] for s in segments]
        assert "ar" in langs
        assert "en" in langs

    def test_correct_arabic(self):
        """اختبار التصحيح العربي."""
        from modules.nlp.mixed_language import MixedLanguageHandler
        handler = MixedLanguageHandler()
        # الحياة موجودة في القاموس
        result = handler.correct_text_mixed("الحياه")
        assert "الحياة" in result

    def test_get_ocr_language_params(self):
        """اختبار استخراج معلمات اللغات."""
        from modules.nlp.mixed_language import MixedLanguageHandler
        handler = MixedLanguageHandler()
        langs = handler.get_ocr_language_params("مرحبا Hello world")
        assert "ar" in langs
        assert "en" in langs


class TestLayoutExport:
    """اختبار التصدير المطابق للتنسيق."""

    def test_export_to_docx_basic(self, tmp_path):
        """اختبار تصدير DOCX أساسي."""
        from modules.export.layout_preserving import export_to_docx

        layout_data = {
            "blocks": [
                {"type": "paragraph", "text": "مرحبا بالعالم", "bbox": [0, 0, 1, 1]},
                {"type": "header", "text": "عنوان", "bbox": [0, 0, 1, 1]},
            ]
        }
        output_path = str(tmp_path / "test.docx")
        result = export_to_docx(layout_data, output_path)
        assert os.path.exists(result)

    def test_layout_to_docx_from_json(self, tmp_path):
        """اختبار التصدير من JSON القياسي."""
        from modules.export.layout_preserving import layout_to_docx
        from modules.vision.normalize import normalize_ocr_output, save_normalized

        raw_blocks = [
            {"type": "paragraph", "bbox": [0.1, 0.1, 0.9, 0.2], "text": "مرحبا", "confidence": 0.95},
            {"type": "header", "bbox": [0.1, 0.0, 0.9, 0.1], "text": "عنوان", "confidence": 0.9},
        ]
        normalized = normalize_ocr_output(
            raw_blocks, "test.jpg", 2480, 3508, "tesseract", ["ar"]
        )
        json_path = str(tmp_path / "result.json")
        save_normalized(normalized, json_path)

        docx_path = str(tmp_path / "output.docx")
        result = layout_to_docx(json_path, docx_path)
        assert os.path.exists(result)

    def test_layout_to_docx_with_table(self, tmp_path):
        """اختبار التصدير مع جدول."""
        from modules.export.layout_preserving import layout_to_docx
        from modules.vision.normalize import normalize_ocr_output, save_normalized

        raw_blocks = [
            {
                "type": "table",
                "bbox": [0.1, 0.1, 0.9, 0.5],
                "confidence": 0.85,
                "cells": [
                    ["اسم", "القيمة"],
                    ["أ", "100"],
                    ["ب", "200"],
                ],
            }
        ]
        normalized = normalize_ocr_output(
            raw_blocks, "test.jpg", 2480, 3508, "surya", ["ar"]
        )
        json_path = str(tmp_path / "table_result.json")
        save_normalized(normalized, json_path)

        docx_path = str(tmp_path / "table_output.docx")
        result = layout_to_docx(json_path, docx_path)
        assert os.path.exists(result)

    def test_ocr_result_to_layout(self):
        """اختبار تحويل نتيجة OCR إلى layout."""
        from modules.export.layout_preserving import ocr_result_to_layout

        ocr_json = {
            "blocks": [
                {"type": "paragraph", "bbox": [0, 0, 1, 1], "text": "test"},
                {"type": "table", "bbox": [0, 0, 1, 1], "cells": [["a", "b"]]},
            ]
        }
        layout = ocr_result_to_layout(ocr_json, "img.jpg")
        assert "blocks" in layout
        assert len(layout["blocks"]) == 2


class TestTableDetection:
    """اختبار كاشف الجداول."""

    def test_table_detection_init(self):
        """اختبار تهيئة كاشف الجداول."""
        from modules.vision.table_detection import TableDetectionTransformer
        detector = TableDetectionTransformer(device="cpu")
        assert detector is not None
        assert detector.device == "cpu"

    def test_table_detection_without_model(self):
        """اختبار كشف الجداول بدون تحميل نموذج (يُرجع قائمة فارغة)."""
        from modules.vision.table_detection import TableDetectionTransformer
        detector = TableDetectionTransformer(device="cpu")
        # بدون تحميل النموذج فعلياً، detect_tables ستسجل تحذيراً وترجع []
        tables = detector.detect_tables("nonexistent.jpg", threshold=0.5)
        assert isinstance(tables, list)
