# schemas.py - OmniFile backend component
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# مخططات المستخدم
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# مخططات المستند
class DocumentBase(BaseModel):
    file_name: str
    raw_text: str
    processed_text: Optional[str] = None
    page_count: int = 1
    language: str = "ar"
    confidence: float = 0.0
    status: str = "pending_review"
    metadata: Optional[dict] = None

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: str
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner_id: Optional[int] = None

    class Config:
        from_attributes = True

# مخططات OCR
class OCRResultBase(BaseModel):
    page_num: int
    word_text: str
    raw_text: str
    confidence: float
    model_source: str

class OCRResultCreate(OCRResultBase):
    pass

class OCRResult(OCRResultBase):
    id: int
    document_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# مخططات التصحيح
class CorrectionBase(BaseModel):
    original_text: str
    corrected_text: str
    language: str
    confidence: float
    source: str = "manual"

class CorrectionCreate(CorrectionBase):
    pass

class Correction(CorrectionBase):
    id: int
    correction_count: int = 1
    is_used_in_training: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# مخططات النماذج المدربة
class FineTunedModelBase(BaseModel):
    model_name: str
    model_path: str
    language: str
    base_model: str
    accuracy: float
    version: str = "1.0"

class FineTunedModelCreate(FineTunedModelBase):
    pass

class FineTunedModel(FineTunedModelBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# مخططات المصادقة
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class Message(BaseModel):
    message: str
