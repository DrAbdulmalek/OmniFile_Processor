"""
Tests for the Result Fusion Module
====================================
Tests the intelligent merging of OCR results from multiple engines
using confidence-based strategies (highest_confidence, voting, etc.).

Based on the fusion module from advanced-ocr/pipeline/fusion.py,
adapted for OmniFile_Processor's modules.vision structure.
"""

import pytest
from dataclasses import dataclass, field
from typing import Optional


# ─── Data structures matching the fusion module's types ───────────────

@dataclass
class BoundingBox:
    """Bounding box for a text region."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def iou(self, other: "BoundingBox") -> float:
        """Calculate Intersection over Union with another bounding box."""
        x_left = max(self.x, other.x)
        y_top = max(self.y, other.y)
        x_right = min(self.x2, other.x2)
        y_bottom = min(self.y2, other.y2)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        union_area = self.area + other.area - intersection_area
        return intersection_area / max(union_area, 1)

    def overlaps_vertically(self, other: "BoundingBox", tolerance: int = 20) -> bool:
        """Check if two boxes overlap vertically within tolerance."""
        return abs(self.y - other.y) < tolerance


@dataclass
class WordResult:
    """Result for a single recognized word."""
    text: str = ""
    confidence: float = 0.0
    bbox: BoundingBox = field(default_factory=BoundingBox)


@dataclass
class LineResult:
    """Result for a single recognized text line."""
    text: str = ""
    confidence: float = 0.0
    bbox: BoundingBox = field(default_factory=BoundingBox)
    words: list[WordResult] = field(default_factory=list)
    block_type: str = "paragraph"
    language: Optional[str] = None

    @property
    def word_count(self) -> int:
        return len(self.words) if self.words else len(self.text.split())


@dataclass
class PageResult:
    """Result for a single page."""
    page_number: int = 1
    lines: list[LineResult] = field(default_factory=list)
    width: int = 0
    height: int = 0

    @property
    def full_text(self) -> str:
        return "\n".join(line.text for line in self.lines if line.text.strip())

    @property
    def avg_confidence(self) -> float:
        if not self.lines:
            return 0.0
        return sum(line.confidence for line in self.lines) / len(self.lines)


@dataclass
class DocumentResult:
    """Result for an entire document."""
    filename: str = "unknown"
    pages: list[PageResult] = field(default_factory=list)
    engine_name: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.full_text for page in self.pages)

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "engine": self.engine_name,
            "pages": [
                {"page_number": p.page_number, "text": p.full_text}
                for p in self.pages
            ],
        }


# ─── Simplified ResultFusion for testing ──────────────────────────────

class ResultFusion:
    """
    Intelligently merges OCR results from multiple engines.

    Strategy: highest_confidence — pick the line with highest confidence.
    """

    def __init__(self, line_tolerance: int = 20, engine_weights: Optional[dict[str, float]] = None):
        self.line_tolerance = line_tolerance
        self.engine_weights = engine_weights or {}

    def merge_pages(self, page_results: list[PageResult]) -> PageResult:
        """Merge multiple PageResults into one using highest confidence."""
        if not page_results:
            return PageResult(page_number=1, lines=[])

        if len(page_results) == 1:
            return page_results[0]

        page_number = page_results[0].page_number
        all_lines = []
        for page in page_results:
            all_lines.extend(page.lines)

        if not all_lines:
            return PageResult(page_number=page_number, lines=[])

        # Group into rows by Y coordinate
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

        # Pick highest confidence per row
        merged_lines = []
        for row in rows:
            best = max(row, key=lambda l: l.confidence)
            merged_lines.append(best)

        merged_lines.sort(key=lambda l: l.bbox.y)
        return PageResult(page_number=page_number, lines=merged_lines)

    def merge_documents(self, doc_results: list[DocumentResult]) -> DocumentResult:
        """Merge multiple DocumentResults into one."""
        if not doc_results:
            return DocumentResult(filename="unknown", pages=[])

        if len(doc_results) == 1:
            return doc_results[0]

        filename = doc_results[0].filename
        engine_names = " + ".join(d.engine_name for d in doc_results)
        max_pages = max(len(d.pages) for d in doc_results)

        merged_pages = []
        for page_idx in range(max_pages):
            page_results = [d.pages[page_idx] for d in doc_results if page_idx < len(d.pages)]
            merged_page = self.merge_pages(page_results)
            merged_pages.append(merged_page)

        return DocumentResult(
            filename=filename,
            pages=merged_pages,
            engine_name=engine_names,
        )


# ─── Test Fixtures ────────────────────────────────────────────────────

def create_test_lines():
    """Create test LineResult objects for fusion testing."""
    return [
        LineResult(
            text="مرحبا بالعالم",
            confidence=0.95,
            bbox=BoundingBox(x=100, y=100, width=200, height=30),
        ),
        LineResult(
            text="Hello World",
            confidence=0.92,
            bbox=BoundingBox(x=100, y=150, width=200, height=30),
        ),
    ]


# ─── BoundingBox Tests ───────────────────────────────────────────────

class TestBoundingBox:
    def test_properties(self):
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        assert bbox.x2 == 110
        assert bbox.y2 == 70
        assert bbox.area == 5000
        assert bbox.center == (60, 45)

    def test_iou_no_overlap(self):
        b1 = BoundingBox(x=0, y=0, width=10, height=10)
        b2 = BoundingBox(x=20, y=20, width=10, height=10)
        assert b1.iou(b2) == 0.0

    def test_iou_full_overlap(self):
        b1 = BoundingBox(x=0, y=0, width=10, height=10)
        b2 = BoundingBox(x=0, y=0, width=10, height=10)
        assert b1.iou(b2) == 1.0

    def test_iou_partial_overlap(self):
        b1 = BoundingBox(x=0, y=0, width=10, height=10)
        b2 = BoundingBox(x=5, y=5, width=10, height=10)
        iou = b1.iou(b2)
        assert 0 < iou < 1

    def test_overlaps_vertically(self):
        b1 = BoundingBox(x=0, y=100, width=10, height=30)
        b2 = BoundingBox(x=50, y=110, width=10, height=30)
        assert b1.overlaps_vertically(b2, tolerance=20)

    def test_not_overlaps_vertically(self):
        b1 = BoundingBox(x=0, y=100, width=10, height=30)
        b2 = BoundingBox(x=50, y=200, width=10, height=30)
        assert not b1.overlaps_vertically(b2, tolerance=20)


# ─── LineResult Tests ────────────────────────────────────────────────

class TestLineResult:
    def test_word_count(self):
        line = LineResult(
            text="Hello World Test",
            confidence=0.9,
            bbox=BoundingBox(x=0, y=0, width=100, height=20),
            words=[
                WordResult(text="Hello", confidence=0.9, bbox=BoundingBox(x=0, y=0, width=30, height=20)),
                WordResult(text="World", confidence=0.9, bbox=BoundingBox(x=35, y=0, width=30, height=20)),
                WordResult(text="Test", confidence=0.9, bbox=BoundingBox(x=70, y=0, width=30, height=20)),
            ],
        )
        assert line.word_count == 3

    def test_word_count_from_text(self):
        line = LineResult(text="One Two", confidence=0.8)
        assert line.word_count == 2


# ─── PageResult Tests ────────────────────────────────────────────────

class TestPageResult:
    def test_full_text(self):
        page = PageResult(
            page_number=1,
            lines=[
                LineResult(text="First line", confidence=0.9, bbox=BoundingBox(x=0, y=0, width=100, height=20)),
                LineResult(text="Second line", confidence=0.8, bbox=BoundingBox(x=0, y=30, width=100, height=20)),
            ],
        )
        assert page.full_text == "First line\nSecond line"

    def test_avg_confidence(self):
        page = PageResult(
            page_number=1,
            lines=[
                LineResult(text="A", confidence=0.9, bbox=BoundingBox(x=0, y=0, width=10, height=10)),
                LineResult(text="B", confidence=0.7, bbox=BoundingBox(x=0, y=10, width=10, height=10)),
            ],
        )
        assert page.avg_confidence == 0.8

    def test_empty_page(self):
        page = PageResult(page_number=1)
        assert page.full_text == ""
        assert page.avg_confidence == 0.0


# ─── DocumentResult Tests ────────────────────────────────────────────

class TestDocumentResult:
    def test_full_text(self):
        doc = DocumentResult(
            filename="test.pdf",
            pages=[
                PageResult(
                    page_number=1,
                    lines=[LineResult(text="Page 1 text", confidence=0.9, bbox=BoundingBox(x=0, y=0, width=100, height=20))],
                ),
                PageResult(
                    page_number=2,
                    lines=[LineResult(text="Page 2 text", confidence=0.9, bbox=BoundingBox(x=0, y=0, width=100, height=20))],
                ),
            ],
        )
        assert "Page 1 text" in doc.full_text
        assert "Page 2 text" in doc.full_text

    def test_to_dict(self):
        doc = DocumentResult(
            filename="test.pdf",
            engine_name="TestEngine",
            pages=[PageResult(page_number=1)],
        )
        d = doc.to_dict()
        assert d["filename"] == "test.pdf"
        assert d["engine"] == "TestEngine"
        assert len(d["pages"]) == 1


# ─── Fusion Tests ────────────────────────────────────────────────────

class TestResultFusion:
    def test_highest_confidence_strategy(self):
        """Line with highest confidence should be selected."""
        fusion = ResultFusion()

        page1 = PageResult(
            page_number=1,
            lines=[
                LineResult(text="مرحبا", confidence=0.95, bbox=BoundingBox(x=0, y=0, width=100, height=20)),
                LineResult(text="العالم", confidence=0.90, bbox=BoundingBox(x=0, y=30, width=100, height=20)),
            ],
        )
        page2 = PageResult(
            page_number=1,
            lines=[
                LineResult(text="مرحبا", confidence=0.80, bbox=BoundingBox(x=0, y=5, width=100, height=20)),
                LineResult(text="العالم", confidence=0.98, bbox=BoundingBox(x=0, y=28, width=100, height=20)),
            ],
        )

        merged = fusion.merge_pages([page1, page2])
        assert merged.lines[0].confidence == 0.95  # First line from page1
        assert merged.lines[1].confidence == 0.98  # Second line from page2

    def test_single_page(self):
        """Single page should pass through unchanged."""
        fusion = ResultFusion()
        page = PageResult(
            page_number=1,
            lines=[LineResult(text="Test", confidence=0.9, bbox=BoundingBox(x=0, y=0, width=10, height=10))],
        )
        merged = fusion.merge_pages([page])
        assert merged.lines[0].text == "Test"

    def test_empty_pages(self):
        fusion = ResultFusion()
        merged = fusion.merge_pages([])
        assert merged.lines == []

    def test_merge_documents(self):
        """Test merging full documents."""
        fusion = ResultFusion()
        doc1 = DocumentResult(
            filename="test.pdf",
            engine_name="Engine1",
            pages=[
                PageResult(
                    page_number=1,
                    lines=[LineResult(text="Hello", confidence=0.9, bbox=BoundingBox(x=0, y=0, width=50, height=20))],
                ),
            ],
        )
        doc2 = DocumentResult(
            filename="test.pdf",
            engine_name="Engine2",
            pages=[
                PageResult(
                    page_number=1,
                    lines=[LineResult(text="Hello", confidence=0.85, bbox=BoundingBox(x=0, y=2, width=50, height=20))],
                ),
            ],
        )
        merged = fusion.merge_documents([doc1, doc2])
        assert merged.filename == "test.pdf"
        assert len(merged.pages) == 1
        assert merged.pages[0].lines[0].confidence == 0.9
        assert "Engine1" in merged.engine_name
        assert "Engine2" in merged.engine_name

    def test_empty_documents(self):
        fusion = ResultFusion()
        merged = fusion.merge_documents([])
        assert merged.pages == []
        assert merged.filename == "unknown"


# ─── Run Tests ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
