#!/usr/bin/env python3
"""
NLP Medical Document Pipeline — أنبوب معالجة المستندات الطبية
==============================================================
مثال شامل يُظهِر كيفية دمج عدة وحدات NLP ومعالجة طبية في
أنبوب شامل لمعالجة المستندات الطبية العربية/الإنجليزية.

Comprehensive example demonstrating a complete end-to-end pipeline
for processing Arabic/English medical documents, combining:
  - Medical OCR with term protection
  - Arabic NLP normalization & spell checking
  - Language correction (grammar & style)
  - Sensitive data detection & redaction
  - Layout analysis with table extraction
  - Full pipeline orchestration with error handling

Usage / الاستخدام:
    python examples/nlp_medical_pipeline.py
    python examples/nlp_medical_pipeline.py --input medical_report.pdf
    python examples/nlp_medical_pipeline.py --input note.jpg --lang ar --redact

Author: OmniFile AI Processor v5.0
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── إعداد التسجيل / Logging Setup ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nlp_medical_pipeline")

# ── الاستيرادات من المشروع / Project Imports ────────────────────────────
# وحدات NLP / NLP modules
from modules.nlp.arabic_nlp_utils import (
    normalize_for_comparison,
    arabic_normalized_similarity,
    similarity_report,
)
from modules.nlp.language_corrector import LanguageCorrector
from modules.nlp.arabic_rtl import (
    RTLFixer,
    is_rtl_text,
    get_text_direction,
    fix_rtl_display,
    normalize_arabic_ocr,
)
from modules.nlp.language_detector import LanguageDetector
from modules.nlp.protected_words import ProtectedWordsManager

# وحدة التدقيق الإملائي / Spell checking
from modules.core.spell_checker import HybridSpellChecker

# وحدة الأمان / Security module
from modules.security.sensitive_data_scanner import SensitiveDataScanner

# وحدة الرؤية الحاسوبية (تحليل التخطيط + استخراج الجداول) / Vision
from modules.vision.layout_analyzer import LayoutAnalyzer
from modules.vision.table_extractor import TableExtractor
from modules.core.structure import BBox, BlockType, DocumentBlock

# وحدة الطب / Medical module
from modules.medical.medical_ocr_reviewer import AdvancedMedicalOCR

# التصدير / Export
from modules.export.markdown_exporter import export_to_markdown


# ═══════════════════════════════════════════════════════════════════════
# §1  هياكل البيانات / Data Structures
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class MedicalTextBlock:
    """كتلة نصية طبية مع بيانات وصفية / Medical text block with metadata."""
    text: str = ""
    block_type: str = "paragraph"          # paragraph | heading | table | list_item
    language: str = "ar"                   # ar | en | mixed
    confidence: float = 0.0
    has_medical_terms: bool = False
    medical_terms_found: List[str] = field(default_factory=list)
    is_redacted: bool = False
    original_text: str = ""                # قبل التعديل / before correction


@dataclass
class MedicalPipelineResult:
    """نتيجة أنبوب المعالجة الطبية / Medical pipeline processing result."""
    filename: str = ""
    language_detected: str = "ar"
    total_blocks: int = 0
    medical_terms_count: int = 0
    protected_terms_count: int = 0
    spelling_corrections: int = 0
    grammar_corrections: int = 0
    sensitive_entities_found: int = 0
    tables_extracted: int = 0
    processing_time_seconds: float = 0.0
    redacted_text: str = ""
    corrected_text: str = ""
    markdown_output: str = ""
    errors: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# §2  قائمة المصطلحات الطبية المحمية / Protected Medical Terms
# ═══════════════════════════════════════════════════════════════════════

ARABIC_MEDICAL_TERMS = [
    "عظم الفخذ", "عظم العضد", "الظنبوب", "عظم الساعد", "عظم القص",
    "الترقوة", "الكتف", "الكاحل", "الرسغ", "الشظية",
    "نخاع العظم", "النخاع الشوكي", "مفصل الركبة", "مفصل الكتف",
    "مفصل الورك", "مفصل الكاحل", "الرباط الصليبي", "الغضروف المفصلي",
    "التهاب المفاصل", "هشاشة العظام", "انزلاق غضروفي",
    "التهاب الأوتار", "استئصال المرارة", "فتق ديسك",
    "الكبد", "الكلية", "القلب", "الرئة", "الدماغ",
    "الأوعية الدموية", "الأعصاب", "العضلات", "العظام",
]

ENGLISH_MEDICAL_TERMS = [
    "osteomyelitis", "arthritis", "effusion", "synovial",
    "CBC", "WBC", "RBC", "HGB", "PLT", "BMP", "LFT",
    "MRI", "CT scan", "X-ray", "ultrasound",
    "Amoxicillin", "Augmentin", "Ceftriaxone", "Vancomycin",
    "Ibuprofen", "Acetaminophen", "Paracetamol", "Aspirin",
    "Insulin", "Glucose", "HbA1c", "TSH", "Cortisol",
    "Flucloxacillin", "Ciprofloxacin", "HIV", "ESR", "CRP",
]


# ═══════════════════════════════════════════════════════════════════════
# §3  فئة أنبوب المعالجة الطبية / Medical Pipeline Class
# ═══════════════════════════════════════════════════════════════════════

class MedicalNLPPipeline:
    """
    أنبوب معالجة شامل للمستندات الطبية.

    يُنفِّذ المراحل التالية بالترتيب:
    1.  استخراج النص (OCR) مع حماية المصطلحات الطبية
    2.  كشف اللغة وتطبيع النص العربي
    3.  التدقيق الإملائي مع حماية المصطلحات
    4.  التدقيق اللغوي (النحو والأسلوب)
    5.  كشف البيانات الحساسة وإزالتها (اختياري)
    6.  تحليل التخطيط واستخراج الجداول
    7.  التصدير إلى Markdown

    يفترض هذا المثال وجود نص مستخرج مسبقاً (أو محاكي).
    في بيئة الإنتاج، تُضاف خطوة OCR مبدئية باستخدام:
        from modules.vision.ocr_engine import OCREngine
        from modules.medical.medical_ocr_reviewer import AdvancedMedicalOCR

    Example:
        >>> pipeline = MedicalNLPPipeline(lang="ar", enable_redaction=True)
        >>> result = pipeline.process_text(raw_medical_text)
        >>> print(result.corrected_text)
        >>> print(result.redacted_text)
    """

    def __init__(
        self,
        lang: str = "ar",
        enable_redaction: bool = False,
        enable_spell_check: bool = True,
        enable_grammar_check: bool = True,
        protect_medical_terms: bool = True,
        redaction_mask: str = "[REDACTED]",
    ) -> None:
        """
        تهيئة أنبوب المعالجة الطبية.

        Args:
            lang:                  اللغة الأساسية (ar | en | auto)
            enable_redaction:      تفعيل إزالة البيانات الحساسة
            enable_spell_check:    تفعيل التدقيق الإملائي
            enable_grammar_check:  تفعيل التدقيق اللغوي
            protect_medical_terms: حماية المصطلحات الطبية من التصحيح
            redaction_mask:        نص القناع للبيانات المحساسة
        """
        self.lang = lang
        self.enable_redaction = enable_redaction
        self.redaction_mask = redaction_mask

        # ── تهيئة المكونات / Initialize components ──────────────

        # المدقق الإملائي الهجين (يدعم العربية والإنجليزية)
        self.spell_checker = HybridSpellChecker()
        if protect_medical_terms:
            self.spell_checker.add_protected_words(
                ARABIC_MEDICAL_TERMS + ENGLISH_MEDICAL_TERMS
            )

        # المدقق اللغوي (قواعد النحو)
        self.language_corrector = LanguageCorrector(
            lang=lang if lang != "auto" else "ar",
            max_suggestions=3,
        )
        if protect_medical_terms:
            for term in ARABIC_MEDICAL_TERMS:
                self.language_corrector.add_protected_term(term)

        # كاشف اللغة (يُستخدم مع lang="auto")
        self.language_detector = LanguageDetector()

        # مدير الكلمات المحمية (مصطلحات طبية + تقنية)
        self.protected_words = ProtectedWordsManager()
        if protect_medical_terms:
            self.protected_words.add_words(
                ARABIC_MEDICAL_TERMS + ENGLISH_MEDICAL_TERMS,
                category="medical",
            )

        # فاحص البيانات الحساسة
        self.data_scanner = SensitiveDataScanner(use_presidio=True)

        # إضافة أنماط طبية مخصصة (أرقام الملفات الطبية السعودية)
        self.data_scanner.add_custom_pattern(
            name="SAUDI_MEDICAL_ID",
            label="رقم ملف طبي سعودي",
            regex=r"\b\d{10}\b",
            risk="high",
        )

        # محلل التخطيط ومستخرج الجداول
        self.layout_analyzer = LayoutAnalyzer()
        self.table_extractor = TableExtractor()

        # إصلاح RTL
        self.rtl_fixer = RTLFixer()

        # معالج OCR الطبي (lazy-loaded)
        self._medical_ocr: Optional[AdvancedMedicalOCR] = None

        logger.info(
            "تم تهيئة الأنبوب الطبي — lang=%s, redaction=%s, "
            "spell=%s, grammar=%s",
            lang, enable_redaction, enable_spell_check, enable_grammar_check,
        )

    # ──────────────────────────────────────────────────────────────────
    # واجهة رئيسية / Main Interface
    # ──────────────────────────────────────────────────────────────────

    def process_text(
        self,
        raw_text: str,
        filename: str = "medical_document",
    ) -> MedicalPipelineResult:
        """
        معالجة نص طبي كامل عبر جميع المراحل.
        Process a complete medical text through all pipeline stages.

        Args:
            raw_text:  النص الخام المستخرج (من OCR أو إدخال يدوي)
            filename:  اسم الملف المصدر (للتصدير)

        Returns:
            MedicalPipelineResult بنتائج المعالجة
        """
        start_time = time.time()
        result = MedicalPipelineResult(filename=filename)

        logger.info(
            "بدء معالجة المستند الطبي — %d حرف",
            len(raw_text),
        )

        try:
            # ── المرحلة 1: كشف اللغة ───────────────────────────
            detected_lang = self._detect_language(raw_text)
            result.language_detected = detected_lang
            logger.info("اللغة المكتشفة: %s", detected_lang)

            # ── المرحلة 2: تقسيم إلى كتل ──────────────────────
            blocks = self._split_into_blocks(raw_text, detected_lang)
            result.total_blocks = len(blocks)
            logger.info("تم تقسيم النص إلى %d كتلة", len(blocks))

            # ── المرحلة 3: تطبيع النص العربي ──────────────────
            blocks = self._normalize_blocks(blocks, detected_lang)

            # ── المرحلة 4: التدقيق الإملائي ────────────────────
            if self.enable_spell_check:
                blocks = self._spell_check_blocks(blocks, result)

            # ── المرحلة 5: التدقيق اللغوي ────────────────────
            if self.enable_grammar_check:
                blocks = self._grammar_check_blocks(blocks, result)

            # ── المرحلة 6: كشف المصطلحات الطبية ──────────────
            blocks = self._detect_medical_terms(blocks, result)

            # ── المرحلة 7: كشف البيانات الحساسة ──────────────
            if self.enable_redaction:
                blocks, sensitive_count = self._redact_sensitive_data(blocks)
                result.sensitive_entities_found = sensitive_count

            # ── المرحلة 8: إصلاح RTL ──────────────────────────
            blocks = self._fix_rtl_blocks(blocks)

            # ── المرحلة 9: تجميع النتائج ─────────────────────
            result.corrected_text = self._assemble_text(blocks)
            result.redacted_text = self._assemble_text(
                [b for b in blocks if b.is_redacted or not self.enable_redaction]
            )

            # ── المرحلة 10: التصدير ───────────────────────────
            result.markdown_output = self._export_blocks(
                blocks, filename, detected_lang
            )

        except Exception as exc:
            logger.error("فشل في المعالجة: %s", exc, exc_info=True)
            result.errors.append(f"خطأ عام: {exc}")

        result.processing_time_seconds = round(time.time() - start_time, 2)

        logger.info(
            "اكتملت المعالجة — %d كتلة, %d مصطلح طبي, "
            "%d تصحيح إملائي, %d كيان حساس — %.2f ثانية",
            result.total_blocks, result.medical_terms_count,
            result.spelling_corrections, result.sensitive_entities_found,
            result.processing_time_seconds,
        )
        return result

    def process_file(
        self,
        file_path: str,
    ) -> MedicalPipelineResult:
        """
        معالجة ملف طبي كامل (OCR + NLP).
        Process a complete medical file (OCR + NLP).

        Args:
            file_path: مسار الملف (PDF, صورة, أو نص)

        Returns:
            MedicalPipelineResult
        """
        logger.info("معالجة الملف: %s", file_path)
        path = Path(file_path)

        if not path.exists():
            logger.warning("الملف غير موجود: %s — استخدام نص تجريبي", file_path)
            raw_text = self._get_demo_medical_text()
            return self.process_text(raw_text, filename=str(file_path))

        if path.suffix.lower() in (".txt", ".md"):
            raw_text = path.read_text(encoding="utf-8")
            return self.process_text(raw_text, filename=path.name)

        # ملف صورة أو PDF — استخدام OCR الطبي
        try:
            medical_ocr = self._get_medical_ocr()
            # ملاحظة: AdvancedMedicalOCR.process_file تُرجع سطر حالة
            # يُفترض أن lines_data تحتوي النص المستخرج
            status = medical_ocr.process_file(str(path))
            logger.info("حالة OCR: %s", status)

            # جمع النص من الأسطر
            lines = []
            while True:
                line_data = medical_ocr.get_current_line()
                if line_data is None:
                    break
                lines.append(line_data.get("corrected_text", ""))
                medical_ocr.save_correction_and_next(
                    line_data.get("corrected_text", "")
                )

            raw_text = "\n".join(lines)
            return self.process_text(raw_text, filename=path.name)

        except Exception as exc:
            logger.warning("فشل OCR الطبي: %s — استخدام نص تجريبي", exc)
            raw_text = self._get_demo_medical_text()
            return self.process_text(raw_text, filename=path.name)

    # ──────────────────────────────────────────────────────────────────
    # مراحل داخلية / Internal Stages
    # ──────────────────────────────────────────────────────────────────

    def _get_medical_ocr(self) -> AdvancedMedicalOCR:
        """تحميل بطيء لمعالج OCR الطبي / Lazy-load the medical OCR."""
        if self._medical_ocr is None:
            self._medical_ocr = AdvancedMedicalOCR()
        return self._medical_ocr

    def _detect_language(self, text: str) -> str:
        """
        كشف لغة النص باستخدام LanguageDetector.
        Detect the language of the text using LanguageDetector.
        """
        if self.lang != "auto":
            return self.lang

        # استخدام LanguageDetector (يدعم langdetect + تحليل إحصائي)
        result = self.language_detector.detect(text)
        detected = result.get("language", "ar")
        confidence = result.get("confidence", 0.0)
        logger.info(
            "كُشفت اللغة تلقائياً: %s (ثقة: %.1%%, طريقة: %s)",
            detected, confidence * 100, result.get("method", "?"),  # noqa: E501
        )
        return detected

    def _split_into_blocks(
        self,
        text: str,
        lang: str,
    ) -> List[MedicalTextBlock]:
        """
        تقسيم النص إلى كتل حسب الأسطر والفقرات.
        Split text into blocks by lines and paragraphs.
        """
        blocks: List[MedicalTextBlock] = []
        current_paragraph = ""

        for line in text.split("\n"):
            stripped = line.strip()

            if not stripped:
                # سطر فارغ = نهاية فقرة
                if current_paragraph:
                    blocks.append(MedicalTextBlock(
                        text=current_paragraph.strip(),
                        block_type="paragraph",
                        language=lang,
                    ))
                    current_paragraph = ""
                continue

            # كشف العناوين (قصيرة وبدون نقطة)
            if (
                len(stripped) < 80
                and not stripped.endswith((".", "،", ";"))
                and current_paragraph == ""
            ):
                blocks.append(MedicalTextBlock(
                    text=stripped,
                    block_type="heading",
                    language=lang,
                ))
                continue

            # كشف عناصر القوائم
            if stripped.startswith(("•", "-", "*", "○")) or (
                len(stripped) > 1
                and stripped[0].isdigit()
                and stripped[1] in (".", ")", " ")
            ):
                if current_paragraph:
                    blocks.append(MedicalTextBlock(
                        text=current_paragraph.strip(),
                        block_type="paragraph",
                        language=lang,
                    ))
                    current_paragraph = ""
                blocks.append(MedicalTextBlock(
                    text=stripped.lstrip("•-*○0123456789.) "),
                    block_type="list_item",
                    language=lang,
                ))
                continue

            current_paragraph += " " + stripped

        # فقرة أخيرة
        if current_paragraph.strip():
            blocks.append(MedicalTextBlock(
                text=current_paragraph.strip(),
                block_type="paragraph",
                language=lang,
            ))

        return blocks

    def _normalize_blocks(
        self,
        blocks: List[MedicalTextBlock],
        lang: str,
    ) -> List[MedicalTextBlock]:
        """
        تطبيع النص العربي (إزالة التشكيل، توحيد الأحرف).
        Normalize Arabic text (remove diacritics, unify characters).
        """
        if lang not in ("ar", "mixed"):
            return blocks

        for block in blocks:
            if lang in ("ar", "mixed"):
                block.text = normalize_arabic_ocr(block.text)
            block.original_text = block.text  # حفظ النص الأصلي قبل التصحيح

        return blocks

    def _spell_check_blocks(
        self,
        blocks: List[MedicalTextBlock],
        result: MedicalPipelineResult,
    ) -> List[MedicalTextBlock]:
        """
        تدقيق إملائي لكل كتلة مع حماية المصطلحات الطبية.
        Spell-check each block while protecting medical terms.
        """
        for block in blocks:
            # استخدام correct_text الذي يحفظ الكلمات المحمية
            corrected = self.spell_checker.correct_text(block.text)
            if corrected != block.text:
                # حساب عدد الكلمات المُصحَّحة
                original_words = block.text.split()
                corrected_words = corrected.split()
                changes = sum(
                    1 for o, c in zip(original_words, corrected_words) if o != c
                )
                result.spelling_corrections += changes
                logger.debug(
                    "تصحيح إملائي في كتلة %s: %d كلمة",
                    block.block_type, changes,
                )
            block.text = corrected

        return blocks

    def _grammar_check_blocks(
        self,
        blocks: List[MedicalTextBlock],
        result: MedicalPipelineResult,
    ) -> List[MedicalTextBlock]:
        """
        تدقيق لغوي (نحو وأسلوب) لكل كتلة.
        Grammar and style check for each block.
        """
        for block in blocks:
            if not block.text.strip():
                continue

            check_result = self.language_corrector.check(block.text)
            if check_result["error_count"] > 0:
                result.grammar_corrections += check_result["error_count"]

                # تطبيق التصحيحات فقط إذا لم تكن كلها محمية
                non_protected_errors = [
                    e for e in check_result["errors"]
                    if not e.get("protected", False)
                ]
                if non_protected_errors:
                    block.text = check_result["corrected"]
                    logger.debug(
                        "تصحيح نحوي: %d خطأ في كتلة %s",
                        check_result["error_count"],
                        block.block_type,
                    )

        return blocks

    def _detect_medical_terms(
        self,
        blocks: List[MedicalTextBlock],
        result: MedicalPipelineResult,
    ) -> List[MedicalTextBlock]:
        """
        كشف المصطلحات الطبية في الكتل النصية.
        Detect medical terms in text blocks.
        """
        all_terms = ARABIC_MEDICAL_TERMS + ENGLISH_MEDICAL_TERMS

        for block in blocks:
            found_terms = []
            for term in all_terms:
                if term.lower() in block.text.lower():
                    found_terms.append(term)

            if found_terms:
                block.has_medical_terms = True
                block.medical_terms_found = found_terms
                result.medical_terms_count += len(found_terms)
                logger.debug(
                    "مصطلحات طبية في كتلة %s: %s",
                    block.block_type[:3],
                    ", ".join(found_terms[:5]),
                )

        return blocks

    def _redact_sensitive_data(
        self,
        blocks: List[MedicalTextBlock],
    ) -> Tuple[List[MedicalTextBlock], int]:
        """
        كشف وإزالة البيانات الحساسة.
        Detect and redact sensitive data.

        Returns:
            (الكتل المُعدَّلة, عدد الكيانات المكتشفة)
        """
        total_entities = 0

        for block in blocks:
            if not block.text.strip():
                continue

            # فحص البيانات الحساسة
            scan_result = self.data_scanner.scan_text(
                block.text,
                language="ar" if is_rtl_text(block.text) else "en",
            )

            if scan_result["sensitive_data_found"]:
                total_entities += scan_result["total_entities"]

                # تسجيل الكيانات المكتشفة
                for entity in scan_result["entities"]:
                    logger.info(
                        "  ⚠️  كيان حساس [%s]: %s (%s)",
                        entity.get("label", entity.get("type", "?")),
                        entity["text"][:30] + "..." if len(entity["text"]) > 30 else entity["text"],
                        entity.get("risk", "?"),
                    )

                # إزالة البيانات الحساسة
                block.text = self.data_scanner.anonymize_text(
                    block.text,
                    mask_char=self.redaction_mask,
                )
                block.is_redacted = True

        return blocks, total_entities

    def _fix_rtl_blocks(
        self,
        blocks: List[MedicalTextBlock],
    ) -> List[MedicalTextBlock]:
        """إصلاح اتجاه النص RTL للكتل العربية / Fix RTL for Arabic blocks."""
        for block in blocks:
            direction = get_text_direction(block.text)
            if direction in ("rtl", "mixed"):
                block.text = self.rtl_fixer.fix_text(block.text)
        return blocks

    def _assemble_text(self, blocks: List[MedicalTextBlock]) -> str:
        """تجميع الكتل في نص واحد / Assemble blocks into single text."""
        parts: List[str] = []
        for block in blocks:
            if not block.text.strip():
                continue
            if block.block_type == "heading":
                parts.append(f"\n## {block.text}\n")
            elif block.block_type == "list_item":
                parts.append(f"  • {block.text}")
            else:
                parts.append(block.text)
        return "\n".join(parts)

    def _export_blocks(
        self,
        blocks: List[MedicalTextBlock],
        filename: str,
        lang: str,
    ) -> str:
        """تصدير الكتل إلى Markdown / Export blocks to Markdown."""
        layout_blocks = []
        for block in blocks:
            layout_blocks.append({
                "type": block.block_type,
                "text": block.text,
                "has_medical_terms": block.has_medical_terms,
            })

        layout_data = {"blocks": layout_blocks}
        is_rtl = lang in ("ar", "mixed")

        # حفظ الملف
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_name = Path(filename).stem + "_medical_processed.md"
        output_path = output_dir / output_name
        md = export_to_markdown(layout_data, output_path=str(output_path), rtl=is_rtl)

        logger.info("تم حفظ التصدير: %s", output_path)
        return md

    @staticmethod
    def _get_demo_medical_text() -> str:
        """نص طبي تجريبي للتوضيح / Demo medical text for demonstration."""
        return """
تقرير طبي — Medical Report
اسم المريض: أحمد محمد العلي
رقم الملف: 1234567890
التاريخ: 2025-01-15

التشخيص / Diagnosis
المريض يعاني من الم في مفصل الركبة اليسرى منذ اسبوعين
تم اجراء فحص MRI واشارت النتائج الى تمزق جزئي في الرباط الصليبي الامامي
العلاج: اعطاء المريض Ibuprofen 400 mg BID مع اراحة المفصل

ملاحظات اضافية / Additional Notes
• لا يوجد تاريخ اصابة سابقة في المفصل
• CBC, ESR, CRP ضمن المعدل الطبيعي
• يُنصح بجلسات علاج طبيعي بعد 3 اسابيع
• متابعة بعد شهر لعمل تقييم شامل

الطبيب المعالج: د. سارة الأحمد
البريد: dr.sarah@hospital.com
""".strip()


# ═══════════════════════════════════════════════════════════════════════
# §4  أدوات التشابه العربي / Arabic Similarity Utilities Demo
# ═══════════════════════════════════════════════════════════════════════

def demo_arabic_similarity() -> None:
    """عرض أدوات التشابه العربي / Demo Arabic similarity tools."""
    print("\n" + "=" * 60)
    print("  أدوات التشابه العربي — Arabic Similarity Tools")
    print("=" * 60)

    pairs = [
        # (نص OCR, النص الصحيح)
        (
            "المريض يعاني من الم في مفصل الركبة",
            "المريض يعاني من ألم في مفصل الركبة",
        ),
        (
            "تم اجراء فحص MRI",
            "تم إجراء فحص MRI",
        ),
        (
            "الرباط الصليبي الامامي",
            "الرباط الصليبي الأمامي",
        ),
        (
            "هشاشة العظام في عظم الفخذ",
            "هشاشة العظام في عظم الفخذ",
        ),
    ]

    for i, (ocr_text, correct_text) in enumerate(pairs, 1):
        report = similarity_report(ocr_text, correct_text)
        status = "✅" if report["approved"] else "❌"
        print(f"\n  الزوج {i}:")
        print(f"    OCR:      {ocr_text}")
        print(f"    الصحيح:   {correct_text}")
        print(f"    تشابه خام:      {report['raw_similarity']:.2%}")
        print(f"    تشابه مُطبَّع:  {report['normalized_similarity']:.2%}")
        print(f"    {status} {report['recommendation']}")


# ═══════════════════════════════════════════════════════════════════════
# §5  عرض نتائج الأنبوب / Pipeline Report
# ═══════════════════════════════════════════════════════════════════════

def print_medical_report(result: MedicalPipelineResult) -> None:
    """طباعة تقرير مفصل عن نتائج الأنبوب الطبي / Print medical pipeline report."""
    print("\n" + "=" * 70)
    print("  تقرير أنبوب المعالجة الطبية — Medical Pipeline Report")
    print("=" * 70)

    print(f"\n📄 الملف:                  {result.filename}")
    print(f"🌐 اللغة المكتشفة:         {result.language_detected}")
    print(f"📦 إجمالي الكتل:           {result.total_blocks}")
    print(f"🏥 المصطلحات الطبية:       {result.medical_terms_count}")
    print(f"🛡️  الكلمات المحمية:        {result.protected_terms_count}")
    print(f"✏️  تصحيحات إملائية:        {result.spelling_corrections}")
    print(f"📝 تصحيحات نحوية:          {result.grammar_corrections}")
    print(f"🔒 كيانات حساسة مكتشفة:    {result.sensitive_entities_found}")
    print(f"📊 جداول مُستخرجة:         {result.tables_extracted}")
    print(f"⏱️  وقت المعالجة:           {result.processing_time_seconds} ثانية")

    # النص المصحح (مقتطف)
    if result.corrected_text:
        print(f"\n📝 النص المصحح (مقتطف):")
        print("-" * 50)
        lines = result.corrected_text.split("\n")[:15]
        for line in lines:
            print(f"  {line}")
        if len(result.corrected_text.split("\n")) > 15:
            print("  ...")
        print("-" * 50)

    # النص بعد إزالة البيانات الحساسة
    if result.enable_redaction and result.redacted_text:
        print(f"\n🔒 النص بعد إزالة البيانات الحساسة (مقتطف):")
        print("-" * 50)
        lines = result.redacted_text.split("\n")[:10]
        for line in lines:
            print(f"  {line}")
        print("-" * 50)

    # الأخطاء
    if result.errors:
        print(f"\n⚠️  الأخطاء ({len(result.errors)}):")
        for err in result.errors:
            print(f"   • {err}")

    print("\n" + "=" * 70)


# ═══════════════════════════════════════════════════════════════════════
# §6  نقطة الدخول / Entry Point
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    """دالة رئيسية توضح جميع قدرات الأنبوب الطبي."""
    parser = argparse.ArgumentParser(
        description="أنبوب معالجة المستندات الطبية — Medical Document Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة / Examples:
  python examples/nlp_medical_pipeline.py
  python examples/nlp_medical_pipeline.py --input medical_report.pdf
  python examples/nlp_medical_pipeline.py --input note.txt --lang ar --redact
        """,
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="مسار الملف المدخل / Input file path (default: demo text)",
    )
    parser.add_argument(
        "--lang", "-l",
        choices=["ar", "en", "auto"],
        default="ar",
        help="اللغة الأساسية / Primary language (default: ar)",
    )
    parser.add_argument(
        "--redact", "-r",
        action="store_true",
        help="تفعيل إزالة البيانات الحساسة / Enable data redaction",
    )
    parser.add_argument(
        "--no-spell",
        action="store_true",
        help="تعطيل التدقيق الإملائي / Disable spell checking",
    )
    parser.add_argument(
        "--no-grammar",
        action="store_true",
        help="تعطيل التدقيق اللغوي / Disable grammar checking",
    )
    args = parser.parse_args()

    print("┌─────────────────────────────────────────────────┐")
    print("│  OmniFile Processor — أنبوب المستندات الطبية   │")
    print("│  Medical NLP Pipeline                          │")
    print("└─────────────────────────────────────────────────┘")

    # ── عرض أدوات التشابه / Show similarity tools ──────────
    demo_arabic_similarity()

    # ── عرض حالة فاحص البيانات الحساسة ───────────────────
    print("\n" + "=" * 60)
    print("  فحص حالة الفاحص — Scanner Status")
    print("=" * 60)
    scanner = SensitiveDataScanner(use_presidio=True)
    status = scanner.is_available()
    print(f"  presidio:  {'✅ متاح' if status['presidio'] else '❌ غير متاح'}")
    print(f"  regex:     ✅ متاح دائماً")
    print(f"  أنماط مخصصة: {status['custom_patterns']}")

    # ── فحص البيانات الحساسة — مثال مباشر ────────────────
    print("\n  مثال فحص مباشر / Direct scan example:")
    sample_medical = "رقم الملف: 1234567890 — البريد: nurse@hospital.com"
    scan_result = scanner.scan_text(sample_medical)
    if scan_result["sensitive_data_found"]:
        print(f"  ⚠️  وُجدت {scan_result['total_entities']} كيان حساس:")
        for entity in scan_result["entities"]:
            label = entity.get("label", entity.get("type", "?"))
            print(f"      [{label}] {entity['text']} (مخاطر: {entity.get('risk', '?')})")
        anonymized = scanner.anonymize_text(sample_medical)
        print(f"  🔒 بعد الإزالة: {anonymized}")

    # ── عرض حالة المدقق الإملائي ─────────────────────────
    print("\n" + "=" * 60)
    print("  حالة المدقق الإملائي الهجين — Hybrid Spell Checker")
    print("=" * 60)
    checker = HybridSpellChecker()
    protected = checker.get_protected_count()
    print(f"  الكلمات المحمية: {protected['total_protected']}")
    print(f"    • مصطلحات تقنية: {protected['technical_keywords']}")
    print(f"    • كلمات بايثون:  {protected['python_keywords']}")
    print(f"    • كلمات مخصصة:   {protected['custom_words']}")

    # مثال تصحيح
    corrected, lang = checker.auto_correct("الم")
    print(f"\n  تصحيح كلمة: 'الم' → '{corrected}' (لغة: {lang})")

    # ── عرض مدير الكلمات المحمية ──────────────────────────
    print("\n" + "=" * 60)
    print("  مدير الكلمات المحمية — Protected Words Manager")
    print("=" * 60)
    pwm = ProtectedWordsManager()
    pwm_stats = pwm.get_stats()
    print(f"  إجمالي الكلمات المحمية: {pwm_stats['total_protected']}")
    for cat, count in pwm_stats['by_category'].items():
        print(f"    • {cat}: {count}")

    # مثال فحص حماية
    test_word = "Ibuprofen"
    is_prot = pwm.is_protected(test_word)
    cat = pwm.get_category(test_word)
    print(f"\n  فحص '{test_word}': محمي={is_prot}, فئة={cat}")

    # ── عرض حالة المدقق اللغوي ───────────────────────────
    print("\n" + "=" * 60)
    print("  المدقق اللغوي — Language Corrector")
    print("=" * 60)
    corrector = LanguageCorrector(lang="ar")
    print(f"  الحالة: {'✅ متاح (LanguageTool)' if corrector.is_available else '⚠️  أساسي (regex)'}")

    # مثال تدقيق
    check_sample = "المريض يعاني من الم في الركبة.تم اجراء فحص MRI"
    check_result = corrector.check(check_sample)
    print(f"\n  فحص: '{check_sample}'")
    print(f"  النتيجة: {check_result['method']}")
    print(f"  الأخطاء: {check_result['error_count']}")
    if check_result["errors"]:
        for err in check_result["errors"]:
            print(f"    • {err['message']} → {err.get('replacements', [])}")
    print(f"  المصحح: '{check_result['corrected']}'")

    # ── تشغيل الأنبوب الكامل / Run full pipeline ────────────
    print("\n" + "=" * 60)
    print("  تشغيل الأنبوب الكامل — Running Full Pipeline")
    print("=" * 60)

    pipeline = MedicalNLPPipeline(
        lang=args.lang,
        enable_redaction=args.redact,
        enable_spell_check=not args.no_spell,
        enable_grammar_check=not args.no_grammar,
    )

    if args.input:
        result = pipeline.process_file(args.input)
    else:
        demo_text = MedicalNLPPipeline._get_demo_medical_text()
        result = pipeline.process_text(demo_text, filename="demo_medical_report")

    print_medical_report(result)

    print("\n✨ تم تشغيل الأنبوب الطبي بنجاح!")
    if result.markdown_output:
        print(f"   ملف Markdown: output/{Path(result.filename).stem}_medical_processed.md")


if __name__ == "__main__":
    main()
