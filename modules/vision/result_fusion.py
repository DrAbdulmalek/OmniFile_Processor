"""
وحدة دمج نتائج التعرف على النصوص (Result Fusion Module)
==========================================================
دمج ذكي لنتائج عدة محركات OCR باستخدام استراتيجيات قائمة على مستوى الثقة.
Intelligent result fusion module that merges OCR results from multiple engines
using confidence-based strategies.

المصدر: دمج من مشروع advanced-ocr
Source: Merged from advanced-ocr project

الاستراتيجيات المدعومة:
- highest_confidence: اختيار السطر بأعلى ثقة
- voting: تصويت الأغلبية عبر المحركات
- weighted_average: المتوسط المرجح لدرجات الثقة
- longest_text: أطول نص (احتياطي فقط)

OmniFile AI Processor - وحدة معالجة الملفات الذكية
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# أنواع البيانات المحلية المطلوبة لدمج النتائج
# Local type definitions required for result fusion
# ---------------------------------------------------------------------------

class FusionStrategy(str, Enum):
    """استراتيجيات دمج نتائج OCR / OCR result fusion strategies."""
    HIGHEST_CONFIDENCE = "highest_confidence"
    WEIGHTED_AVERAGE = "weighted_average"
    VOTING = "voting"
    LONGEST_TEXT = "longest_text"


class TextBlockType(str, Enum):
    """أنواع الكتل النصية المكتشفة / Detected text block types."""
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    HEADER = "header"
    FOOTER = "footer"
    TABLE = "table"
    IMAGE = "image"
    UNKNOWN = "unknown"


class BoundingBox:
    """مربع إحاطي في إحداثيات البكسل / Bounding box in pixel coordinates."""

    def __init__(self, x: int = 0, y: int = 0, width: int = 0, height: int = 0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


class WordResult:
    """نتيجة التعرف على كلمة واحدة / Single word recognition result."""

    def __init__(
        self,
        text: str = "",
        confidence: float = 0.0,
        bbox: Optional[BoundingBox] = None,
    ):
        self.text = text
        self.confidence = confidence
        self.bbox = bbox


class LineResult:
    """نتيجة التعرف على سطر نصي كامل / Full text line recognition result."""

    def __init__(
        self,
        text: str = "",
        confidence: float = 0.0,
        bbox: Optional[BoundingBox] = None,
        words: Optional[list[WordResult]] = None,
        block_type: TextBlockType = TextBlockType.PARAGRAPH,
        language: str = "",
    ):
        self.text = text
        self.confidence = confidence
        self.bbox = bbox
        self.words = words or []
        self.block_type = block_type
        self.language = language


class PageResult:
    """نتائج التعرف على صفحة كاملة / Full page OCR result."""

    def __init__(
        self,
        page_number: int = 1,
        lines: Optional[list[LineResult]] = None,
        width: int = 0,
        height: int = 0,
    ):
        self.page_number = page_number
        self.lines = lines or []
        self.width = width
        self.height = height


class DocumentResult:
    """نتائج التعرف على مستند كامل / Full document OCR result."""

    def __init__(
        self,
        filename: str = "unknown",
        pages: Optional[list[PageResult]] = None,
        engine_name: str = "",
        metadata: Optional[dict] = None,
    ):
        self.filename = filename
        self.pages = pages or []
        self.engine_name = engine_name
        self.metadata = metadata or {}


# ---------------------------------------------------------------------------
# محرك الدمج الأساسي / Core Fusion Engine
# ---------------------------------------------------------------------------

class ResultFusion:
    """
    دمج ذكي لنتائج OCR من عدة محركات.
    Intelligently merges OCR results from multiple engines.

    يعمل الدمج على مستوى السطر (LINE level) بمقارنة درجات الثقة
    بدلاً من مطابقة النصوص الضبابية.
    Fusion operates at LINE level, comparing confidence scores
    rather than doing text similarity matching.

    الاستراتيجيات / Strategies:
    - highest_confidence: اختيار السطر الأعلى ثقة
    - weighted_average: نص المحرك الأعلى ثقة مع متوسط الثقة
    - voting: تصويت الأغلبية عبر المحركات
    - longest_text: أطول نص (احتياطي فقط)
    """

    def __init__(
        self,
        strategy: FusionStrategy = FusionStrategy.HIGHEST_CONFIDENCE,
        line_tolerance: int = 20,
        engine_weights: Optional[dict[str, float]] = None,
    ):
        """
        Args:
            strategy: استراتيجية الدمج / Fusion strategy to use
            line_tolerance: حد التسامح بالبكسل لمطابقة الأسطر / Pixel tolerance for line matching
            engine_weights: أوزان المحركات الاختيارية / Optional per-engine weights
        """
        self.strategy = strategy
        self.line_tolerance = line_tolerance
        self.engine_weights = engine_weights or {}

    def merge_pages(self, page_results: list[PageResult]) -> PageResult:
        """
        دمج عدة PageResults (من محركات مختلفة) في نتيجة واحدة.
        Merge multiple PageResults from different engines into one.

        Args:
            page_results: قائمة نتائج الصفحات / List of PageResult objects

        Returns:
            PageResult مدمج / Merged PageResult
        """
        if not page_results:
            return PageResult(page_number=1, lines=[])

        if len(page_results) == 1:
            return page_results[0]

        page_number = page_results[0].page_number
        width = max(p.width for p in page_results)
        height = max(p.height for p in page_results)

        # تجميع الأسطر حسب الإحداثي Y
        line_rows = self._group_lines_into_rows(page_results)

        # دمج كل مجموعة
        merged_lines = []
        for row in line_rows:
            merged_line = self._merge_line_group(row)
            if merged_line:
                merged_lines.append(merged_line)

        # ترتيب من الأعلى للأسفل
        merged_lines.sort(key=lambda l: l.bbox.y)

        return PageResult(
            page_number=page_number,
            lines=merged_lines,
            width=width,
            height=height,
        )

    def merge_documents(
        self, doc_results: list[DocumentResult]
    ) -> DocumentResult:
        """
        دمج عدة DocumentResults (من محركات مختلفة) في نتيجة واحدة.
        Merge multiple DocumentResults from different engines into one.

        Args:
            doc_results: قائمة نتائج المستندات / List of DocumentResult objects

        Returns:
            DocumentResult مدمج / Merged DocumentResult
        """
        if not doc_results:
            return DocumentResult(filename="unknown", pages=[])

        if len(doc_results) == 1:
            return doc_results[0]

        filename = doc_results[0].filename
        engine_names = " + ".join(d.engine_name for d in doc_results)

        max_pages = max(len(d.pages) for d in doc_results)

        merged_pages = []
        for page_idx in range(max_pages):
            page_results = []
            for doc in doc_results:
                if page_idx < len(doc.pages):
                    page_results.append(doc.pages[page_idx])
            merged_page = self.merge_pages(page_results)
            merged_pages.append(merged_page)

        return DocumentResult(
            filename=filename,
            pages=merged_pages,
            engine_name=engine_names,
            metadata={"fusion_strategy": self.strategy.value},
        )

    def _group_lines_into_rows(
        self, page_results: list[PageResult]
    ) -> list[list[LineResult]]:
        """
        تجميع الأسطر من جميع المحركات في صفوف حسب الإحداثي Y.
        Group lines from all engines into rows based on Y coordinate.
        """
        all_lines = []
        for page in page_results:
            for line in page.lines:
                all_lines.append(line)

        if not all_lines:
            return []

        all_lines.sort(key=lambda l: l.bbox.y)

        rows = []
        current_row = [all_lines[0]]

        for line in all_lines[1:]:
            ref_y = current_row[0].bbox.y
            if abs(line.bbox.y - ref_y) < self.line_tolerance:
                current_row.append(line)
            else:
                rows.append(current_row)
                current_row = [line]

        if current_row:
            rows.append(current_row)

        return rows

    def _merge_line_group(self, lines: list[LineResult]) -> Optional[LineResult]:
        """
        دمج مجموعة أسطر (نفس الصف) من محركات مختلفة.
        Merge a group of lines (same row) from different engines.
        """
        if not lines:
            return None
        if len(lines) == 1:
            return lines[0]

        valid_lines = [l for l in lines if l.text.strip()]
        if not valid_lines:
            return None

        if self.strategy == FusionStrategy.HIGHEST_CONFIDENCE:
            return self._strategy_highest_confidence(valid_lines)
        elif self.strategy == FusionStrategy.WEIGHTED_AVERAGE:
            return self._strategy_weighted_average(valid_lines)
        elif self.strategy == FusionStrategy.VOTING:
            return self._strategy_voting(valid_lines)
        elif self.strategy == FusionStrategy.LONGEST_TEXT:
            return self._strategy_longest_text(valid_lines)
        else:
            return self._strategy_highest_confidence(valid_lines)

    def _strategy_highest_confidence(self, lines: list[LineResult]) -> LineResult:
        """
        اختيار السطر بأعلى درجة ثقة.
        Select the line with the highest confidence score.
        """
        if self.engine_weights:
            weighted_lines = []
            for line in lines:
                weight = 1.0
                for engine_name, engine_weight in self.engine_weights.items():
                    if engine_name in line.text:
                        weight = engine_weight
                score = line.confidence * weight
                weighted_lines.append((line, score))
            best = max(weighted_lines, key=lambda x: x[1])[0]
        else:
            best = max(lines, key=lambda l: l.confidence)

        return best

    def _strategy_weighted_average(self, lines: list[LineResult]) -> LineResult:
        """
        إنشاء متوسط مرجح لدرجات الثقة.
        Create a weighted average of confidence scores.
        """
        total_conf = sum(l.confidence for l in lines)
        avg_conf = total_conf / len(lines)

        best = max(lines, key=lambda l: l.confidence)

        return LineResult(
            text=best.text,
            confidence=avg_conf,
            bbox=best.bbox,
            words=best.words,
            block_type=best.block_type,
            language=best.language,
        )

    def _strategy_voting(self, lines: list[LineResult]) -> LineResult:
        """
        تصويت الأغلبية: إذا اتفق معظم المحركات على نص مشابه.
        Majority voting: if most engines agree on similar text.
        """
        if len(lines) < 3:
            return self._strategy_highest_confidence(lines)

        text_counts = {}
        for line in lines:
            normalized = line.text.strip()
            matched = False
            for existing_text in text_counts:
                similarity = self._char_similarity(normalized, existing_text)
                if similarity > 0.8:
                    text_counts[existing_text] += line.confidence
                    matched = True
                    break
            if not matched:
                text_counts[normalized] = line.confidence

        best_text = max(text_counts, key=text_counts.get)
        best_line = max(lines, key=lambda l: l.confidence)

        return LineResult(
            text=best_text,
            confidence=text_counts[best_text] / len(lines),
            bbox=best_line.bbox,
            words=best_line.words,
            block_type=best_line.block_type,
        )

    def _strategy_longest_text(self, lines: list[LineResult]) -> LineResult:
        """
        اختيار السطر بأطول نص (احتياطي فقط).
        Pick the line with the longest text (FALLBACK only).
        """
        best = max(lines, key=lambda l: len(l.text))
        return best

    @staticmethod
    def _char_similarity(text1: str, text2: str) -> float:
        """
        حساب التشابه على مستوى الحروف بين نصين.
        Calculate character-level similarity between two strings.
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        len1, len2 = len(text1), len(text2)
        if len1 == 0 or len2 == 0:
            return 0.0

        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()


# ---------------------------------------------------------------------------
# دمج متوازي / Parallel Fusion
# ---------------------------------------------------------------------------

class ParallelFusion:
    """دمج نتائج محركات OCR بشكل متوازٍ باستخدام ThreadPoolExecutor.
    Parallel OCR result fusion using ThreadPoolExecutor.

    يتيح تحويل نتائج بسيطة (dict) من محركات OCR متعددة إلى تنسيق
    LineResult ثم دمجها باستخدام ResultFusion بشكل متوازٍ.
    """

    def __init__(self, fusion_strategy: str = "highest_confidence", max_workers: int = 4):
        """تهيئة الدمج المتوازي.

        Args:
            fusion_strategy: استراتيجية الدمج (highest_confidence, voting, weighted_average, longest_text)
            max_workers: أقصى عدد من العمال المتوازيين / Maximum number of parallel workers
        """
        self.fusion = ResultFusion(strategy=FusionStrategy(fusion_strategy))
        self.max_workers = max_workers

    def fuse_parallel(self, results: list) -> dict:
        """دمج نتائج متعددة من محركات مختلفة بشكل متوازي.
        Merge multiple OCR results from different engines in parallel.

        Args:
            results: قائمة نتائج OCR من محركات مختلفة
                     List of OCR results (dicts with 'text', 'confidence', 'source' keys)

        Returns:
            أفضل نتيجة بعد الدمج / Best result after fusion as a dict with
            keys: text, confidence, source
        """
        if not results:
            return {"text": "", "confidence": 0.0, "source": "none"}

        if len(results) <= 1:
            return results[0] if results else {"text": "", "confidence": 0.0, "source": "none"}

        def _convert_result(r):
            """تحويل نتيجة OCR إلى LineResult.
            Convert an OCR result dict to LineResult object."""
            return LineResult(
                text=r.get("text", ""),
                confidence=r.get("confidence", 0.0),
                bbox=BoundingBox(x=0, y=0, width=100, height=30),
                words=[],
                block_type=TextBlockType.PARAGRAPH,
            )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            line_results = list(executor.map(_convert_result, results))

        # تطبيق استراتيجية الدمج عبر ResultFusion
        page_result = PageResult(lines=line_results)
        merged = self.fusion.merge_pages([page_result])

        # تحويل النتيجة المدمجة إلى تنسيق dict
        if merged.lines:
            best_line = max(merged.lines, key=lambda l: l.confidence)
            return {
                "text": best_line.text,
                "confidence": best_line.confidence,
                "source": "parallel_fusion",
            }
        return {"text": "", "confidence": 0.0, "source": "none"}
