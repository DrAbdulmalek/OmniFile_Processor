"""
backend/schemas.py
==================
Pydantic schemas for the Medical OCR API endpoints.
نماذج بيانات Pydantic لنقاط نهاية OCR الطبي.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# === OCR Task Schemas ===

class MedicalOCRTaskCreate(BaseModel):
    """نموذج لإنشاء مهمة OCR طبية جديدة."""
    file_path: str = Field(..., description="مسار الملف في النظام")
    max_pages: Optional[int] = Field(None, description="الحد الأقصى لعدد الصفحات")
    use_gpu: bool = Field(False, description="استخدام GPU")


class MedicalOCRTaskStatus(BaseModel):
    """نموذج لحالة مهمة OCR."""
    task_id: str
    status: str = Field(..., description="pending | processing | completed | failed")
    progress: float = Field(0, description="نسبة التقدم 0-100")
    result_file: Optional[str] = None
    review_file: Optional[str] = None
    error: Optional[str] = None
    total_pages: Optional[int] = None
    total_lines: Optional[int] = None


class CorrectionItem(BaseModel):
    """عنصر تصحيح واحد (صفحة + سطر + نص مصحح)."""
    page: int
    line_idx: int
    corrected_text: str


class UpdateCorrectionsRequest(BaseModel):
    """طلب تحديث التصحيحات."""
    corrections: List[CorrectionItem]


class MedicalOCRResult(BaseModel):
    """نتيجة معالجة OCR كاملة."""
    task_id: str
    status: str
    json_file: Optional[str] = None
    html_file: Optional[str] = None
    total_pages: int = 0
    total_lines: int = 0
    processing_time_ms: Optional[float] = None


# === Health & Stats Schemas ===

class HealthResponse(BaseModel):
    """استجابة فحص الحالة."""
    status: str = "healthy"
    version: str
    medical_ocr_available: bool = False
    engines: List[str] = []


class OCRStatsResponse(BaseModel):
    """إحصائيات OCR."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_processing_time_ms: float = 0.0
