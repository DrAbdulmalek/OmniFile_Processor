"""
وحدة البنية الأساسية للمستندات (Document Structure Module)
=============================================================
تعريف مخطط البيانات لنتائج OCR باستخدام نماذج Pydantic v2.
جميع مكونات OCR تنتج وتستهلك هذه الأنواع المهيكلة.

Defines the data schema for OCR results using Pydantic v2 models.
All OCR components produce and consume these structured types.

المصدر: دمج من مشروع arabic-ocr-pro
Source: Merged from arabic-ocr-pro project

OmniFile AI Processor - وحدة معالجة الملفات الذكية
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BlockType(str, Enum):
    """أنواع كتل محتوى المستند / Types of document content blocks."""
    TEXT = "text"
    HEADING = "heading"
    TABLE = "table"
    IMAGE = "image"
    FOOTER = "footer"
    HEADER = "header"
    UNKNOWN = "unknown"


class BBox(BaseModel):
    """مربع إحاطي محاذي للمحاور بإحداثيات البكسل / Axis-aligned bounding box.

    Attributes:
        x: الحافة اليسرى / Left edge x-coordinate
        y: الحافة العلوية / Top edge y-coordinate
        width: العرض / Width
        height: الارتفاع / Height
    """

    x: int = Field(ge=0, description="Left edge x-coordinate in pixels")
    y: int = Field(ge=0, description="Top edge y-coordinate in pixels")
    width: int = Field(ge=0, description="Width in pixels")
    height: int = Field(ge=0, description="Height in pixels")

    @property
    def x2(self) -> int:
        """الحافة اليمنى / Right edge x-coordinate."""
        return self.x + self.width

    @property
    def y2(self) -> int:
        """الحافة السفلية / Bottom edge y-coordinate."""
        return self.y + self.height

    @property
    def area(self) -> int:
        """المساحة بالبكسل المربع / Area in square pixels."""
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        """نقطة المركز / Center point."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def intersection(self, other: BBox) -> Optional[BBox]:
        """حساب تقاطع مربعين / Compute intersection of two bounding boxes."""
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)

        if x1 >= x2 or y1 >= y2:
            return None

        return BBox(x=x1, y=y1, width=x2 - x1, height=y2 - y1)

    def iou(self, other: BBox) -> float:
        """حساب نسبة التقاطع على الاتحاد / Compute IoU."""
        intersection = self.intersection(other)
        if intersection is None:
            return 0.0

        inter_area = intersection.area
        union_area = self.area + other.area - inter_area

        if union_area == 0:
            return 0.0

        return inter_area / union_area

    def contains(self, other: BBox) -> bool:
        """التحقق من احتواء مربع لآخر / Check if this box fully contains another."""
        return (
            self.x <= other.x
            and self.y <= other.y
            and self.x2 >= other.x2
            and self.y2 >= other.y2
        )


class OCRToken(BaseModel):
    """رمز OCR واحد (كلمة أو مجموعة أحرف) / Single OCR result token.

    Attributes:
        text: النص المعترف به / Recognized text
        bbox: مربع الإحاطة / Bounding box
        confidence: درجة الثقة / Confidence score
        engine: محرك OCR المصدر / Source OCR engine
    """

    text: str = Field(description="Recognized text content")
    bbox: BBox = Field(description="Bounding box in the source image")
    confidence: float = Field(ge=0.0, le=1.0, description="Recognition confidence score")
    engine: str = Field(default="", description="Source OCR engine name")

    def is_arabic(self) -> bool:
        """هل الرمز يحتوي أحرف عربية؟ / Check if token contains Arabic characters."""
        return any("\u0600" <= ch <= "\u06FF" or "\uFB50" <= ch <= "\uFDFF" or "\uFE70" <= ch <= "\uFEFF" for ch in self.text)

    def is_empty(self) -> bool:
        """هل الرمز فارغ؟ / Check if token has empty text."""
        return len(self.text.strip()) == 0


class DocumentBlock(BaseModel):
    """كتلة محتوى مستند (فقرة، عنوان، جدول، إلخ) / Document content block.

    Attributes:
        block_type: تصنيف الكتلة / Block type classification
        tokens: رموز OCR داخل الكتلة / OCR tokens
        bbox: مربع إحاطة الكتلة / Bounding box
        confidence: متوسط الثقة / Average confidence
        table_data: بيانات الجدول المهيكلة / Structured table data
    """

    block_type: BlockType = Field(default=BlockType.TEXT, description="Type of content block")
    tokens: list[OCRToken] = Field(default_factory=list, description="OCR tokens in this block")
    bbox: Optional[BBox] = Field(default=None, description="Bounding box of the entire block")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Average confidence score")
    table_data: Optional[list[list[str]]] = Field(
        default=None,
        description="Structured table data (rows x cols) if this is a table block",
    )

    def get_text(self) -> str:
        """الحصول على النص المدمج / Get concatenated text."""
        return " ".join(token.text for token in self.tokens if not token.is_empty())

    def compute_confidence(self) -> float:
        """حساب متوسط الثقة / Compute average confidence."""
        non_empty = [t for t in self.tokens if not t.is_empty()]
        if not non_empty:
            return 0.0
        return sum(t.confidence for t in non_empty) / len(non_empty)


class DocumentPage(BaseModel):
    """صفحة واحدة من المستند / A single page of a document.

    Attributes:
        page_number: رقم الصفحة (يبدأ من 1) / 1-based page index
        width: عرض الصفحة / Page width
        height: ارتفاع الصفحة / Page height
        blocks: كتل المحتوى / Content blocks
        image_path: مسار صورة الصفحة / Path to page image
    """

    page_number: int = Field(ge=1, description="1-based page index")
    width: int = Field(ge=0, description="Page width in pixels")
    height: int = Field(ge=0, description="Page height in pixels")
    blocks: list[DocumentBlock] = Field(default_factory=list, description="Detected content blocks")
    image_path: Optional[str] = Field(default=None, description="Path to the rendered page image")

    def get_full_text(self) -> str:
        """الحصول على كل النصوص من الصفحة / Get all text from the page."""
        texts = []
        for block in self.blocks:
            text = block.get_text().strip()
            if text:
                texts.append(text)
        return "\n".join(texts)


class DocumentMetadata(BaseModel):
    """بيانات وصفية عن المستند / Document metadata.

    Attributes:
        filename: اسم الملف الأصلي / Original file name
        file_size: حجم الملف / File size
        page_count: عدد الصفحات / Total pages
        processing_time: وقت المعالجة / Processing time
        engine_used: محرك OCR المستخدم / Primary OCR engine
        preprocessing_applied: خطوات المعالجة المسبقة / Preprocessing steps
    """

    filename: str = Field(default="", description="Original source file name")
    file_size: int = Field(default=0, ge=0, description="File size in bytes")
    page_count: int = Field(default=0, ge=0, description="Total number of pages")
    processing_time: float = Field(default=0.0, ge=0.0, description="Processing time in seconds")
    engine_used: str = Field(default="", description="Primary OCR engine used")
    preprocessing_applied: list[str] = Field(
        default_factory=list,
        description="List of preprocessing steps that were applied",
    )


class Document(BaseModel):
    """نتيجة مستند OCR الكامل / Complete OCR document result.

    Attributes:
        pages: صفحات المستند / Document pages
        metadata: البيانات الوصفية / Document metadata
    """

    pages: list[DocumentPage] = Field(default_factory=list, description="Document pages with OCR results")
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata, description="Document metadata")

    def get_full_text(self) -> str:
        """الحصول على كل النصوص من جميع الصفحات / Get all text from all pages."""
        page_texts = []
        for page in self.pages:
            text = page.get_full_text().strip()
            if text:
                page_texts.append(f"--- Page {page.page_number} ---\n{text}")
        return "\n\n".join(page_texts)

    def get_page_text(self, page_number: int) -> str:
        """الحصول على نص صفحة محددة / Get text from a specific page."""
        for page in self.pages:
            if page.page_number == page_number:
                return page.get_full_text()
        return ""

    def get_all_tables(self) -> list[list[list[str]]]:
        """استخراج كل الجداول / Extract all tables from the document."""
        tables = []
        for page in self.pages:
            for block in page.blocks:
                if block.block_type == BlockType.TABLE and block.table_data:
                    tables.append(block.table_data)
        return tables

    @property
    def total_pages(self) -> int:
        """عدد الصفحات / Total number of pages."""
        return len(self.pages)

    @property
    def total_tokens(self) -> int:
        """عدد الرموز / Total number of OCR tokens."""
        return sum(
            len(block.tokens)
            for page in self.pages
            for block in page.blocks
        )
