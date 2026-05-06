### **🎯 الهدف**
إنشاء **تطبيق Android** باستخدام **Flutter** لمراجعة نتائج OCR، مع **Backend** باستخدام **FastAPI** لإدارة البيانات.

---

### **📁 هيكل المشروع الكامل**
```
omnifile_mobile/
├── backend/                  # Backend (FastAPI)
│   ├── main.py               # نقطة الدخول
│   ├── models.py             # نماذج البيانات
│   ├── schemas.py            # مخططات Pydantic
│   ├── crud.py               # عمليات قاعدة البيانات
│   ├── database.py           # إعداد قاعدة البيانات
│   ├── config.py             # الإعدادات
│   ├── requirements.txt      # التبعيات
│   └── Dockerfile            # Dockerfile للنشر
│
├── mobile/                   # Frontend (Flutter)
│   ├── lib/
│   │   ├── main.dart          # نقطة الدخول
│   │   ├── screens/           # الشاشات
│   │   │   ├── home_screen.dart
│   │   │   ├── review_screen.dart
│   │   │   ├── document_list_screen.dart
│   │   │   └── settings_screen.dart
│   │   ├── models/            # النماذج
│   │   │   ├── document.dart
│   │   │   └── ocr_result.dart
│   │   ├── services/          # الخدمات
│   │   │   ├── api_service.dart
│   │   │   ├── database_service.dart
│   │   │   └── file_service.dart
│   │   ├── widgets/           # الويدجات
│   │   │   ├── text_editor.dart
│   │   │   ├── correction_suggestions.dart
│   │   │   ├── table_widget.dart
│   │   │   └── image_widget.dart
│   │   └── utils/             # الأدوات
│   │       ├── constants.dart
│   │       └── format_utils.dart
│   ├── assets/
│   │   └── images/
│   ├── pubspec.yaml
│   └── android/
│       └── app/
│           └── build.gradle
│
└── README.md
```

---

---

## 🚀 **1. تطوير Backend (FastAPI)**
### **📌 الخطوة 1: إعداد بيئة Backend**
```bash
# إنشاء مجلد backend
mkdir -p omnifile_mobile/backend
cd omnifile_mobile/backend

# إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# تثبيت التبعيات
pip install fastapi uvicorn sqlalchemy pydantic python-multipart python-jose[cryptography] passlib bcrypt
pip install pillow pytesseract easyocr transformers torch opencv-python-headless
pip install python-docx openpyxl beautifulsoup4 pdfkit
```

---

### **📄 `backend/requirements.txt`**
```text
fastapi==0.104.0
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.0.0
python-multipart==0.0.6
python-jose[cryptography]==3.0.2
passlib[bcrypt]==1.7.4
bcrypt==4.1.1
pillow==10.0.0
pytesseract==0.3.10
easyocr==1.7.0
transformers==4.36.0
torch==2.1.0
opencv-python-headless==4.8.0
python-docx==0.8.11
openpyxl==3.1.0
beautifulsoup4==4.12.0
pdfkit==0.6.0
wkhtmltopdf==0.12.6
alembic==1.13.0
```

---

### **📄 `backend/config.py`**
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # إعدادات قاعدة البيانات
    DATABASE_URL: str = "sqlite:///./omnifile.db"

    # إعدادات المصادقة
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # إعدادات OCR
    ENABLE_TROCR: bool = True
    ENABLE_EASYOCR: bool = True
    ENABLE_TESSERACT: bool = True
    ENABLE_PADDLEOCR: bool = False
    TROCR_MODEL: str = "microsoft/trocr-base-handwritten"
    USE_GPU: bool = True

    # إعدادات التصدير
    EXPORT_DIR: str = "./exports"
    TEMP_DIR: str = "./temp"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### **📄 `backend/database.py`**
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# إنشاء محرك قاعدة البيانات
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# قاعدة النماذج
Base = declarative_base()

# دالة للحصول على جلسة قاعدة البيانات
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### **📄 `backend/models.py`**
```python
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="owner")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, index=True)
    file_name = Column(String(255))
    file_path = Column(String(500))
    raw_text = Column(Text)
    processed_text = Column(Text)
    page_count = Column(Integer, default=1)
    language = Column(String(10), default="ar")
    confidence = Column(Float, default=0.0)
    status = Column(String(20), default="pending_review")
    metadata = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="documents")
    ocr_results = relationship("OCRResult", back_populates="document")

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    page_num = Column(Integer)
    word_text = Column(Text)
    raw_text = Column(Text)
    confidence = Column(Float)
    model_source = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    document_id = Column(String(36), ForeignKey("documents.id"))
    document = relationship("Document", back_populates="ocr_results")

class Correction(Base):
    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)
    original_text = Column(Text)
    corrected_text = Column(Text)
    language = Column(String(10))
    confidence = Column(Float)
    source = Column(String(20), default="manual")
    correction_count = Column(Integer, default=1)
    is_used_in_training = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FineTunedModel(Base):
    __tablename__ = "fine_tuned_models"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100))
    model_path = Column(String(500))
    language = Column(String(10))
    base_model = Column(String(100))
    accuracy = Column(Float)
    version = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### **📄 `backend/schemas.py`**
```python
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
```

---

### **📄 `backend/crud.py`**
```python
from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime
import uuid

# عمليات المستخدم
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password.decode(),
        full_name=user.full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# عمليات المستند
def get_document(db: Session, document_id: str):
    return db.query(models.Document).filter(models.Document.id == document_id).first()

def get_documents(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None):
    query = db.query(models.Document)
    if status:
        query = query.filter(models.Document.status == status)
    return query.offset(skip).limit(limit).all()

def create_document(db: Session, document: schemas.DocumentCreate, owner_id: int):
    doc_id = str(uuid.uuid4())
    db_document = models.Document(
        id=doc_id,
        file_name=document.file_name,
        raw_text=document.raw_text,
        processed_text=document.processed_text,
        page_count=document.page_count,
        language=document.language,
        confidence=document.confidence,
        status=document.status,
        metadata=str(document.metadata) if document.metadata else None,
        owner_id=owner_id,
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

def update_document(db: Session, document_id: str, document: schemas.DocumentBase):
    db_document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if db_document:
        for key, value in document.model_dump(exclude_unset=True).items():
            setattr(db_document, key, value)
        db_document.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_document)
    return db_document

def delete_document(db: Session, document_id: str):
    db_document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if db_document:
        db.delete(db_document)
        db.commit()
    return db_document

# عمليات OCR
def get_ocr_results(db: Session, document_id: str):
    return db.query(models.OCRResult).filter(models.OCRResult.document_id == document_id).all()

def create_ocr_result(db: Session, ocr_result: schemas.OCRResultCreate, document_id: str):
    db_ocr_result = models.OCRResult(
        **ocr_result.model_dump(),
        document_id=document_id
    )
    db.add(db_ocr_result)
    db.commit()
    db.refresh(db_ocr_result)
    return db_ocr_result

# عمليات التصحيح
def get_corrections(db: Session, skip: int = 0, limit: int = 100, language: Optional[str] = None):
    query = db.query(models.Correction)
    if language:
        query = query.filter(models.Correction.language == language)
    return query.offset(skip).limit(limit).all()

def create_correction(db: Session, correction: schemas.CorrectionCreate):
    # التحقق من وجود تصحيح مشابه
    existing = db.query(models.Correction).filter(
        models.Correction.original_text == correction.original_text,
        models.Correction.corrected_text == correction.corrected_text,
        models.Correction.language == correction.language
    ).first()

    if existing:
        existing.correction_count += 1
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    db_correction = models.Correction(
        **correction.model_dump()
    )
    db.add(db_correction)
    db.commit()
    db.refresh(db_correction)
    return db_correction

# عمليات النماذج المدربة
def get_fine_tuned_models(db: Session, language: Optional[str] = None):
    query = db.query(models.FineTunedModel)
    if language:
        query = query.filter(models.FineTunedModel.language == language)
    return query.all()

def create_fine_tuned_model(db: Session, model: schemas.FineTunedModelCreate):
    db_model = models.FineTunedModel(
        **model.model_dump()
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model
```

---

### **📄 `backend/main.py`**
```python
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List
import os
from pathlib import Path

from . import models, schemas, crud
from .database import engine, get_db
from .config import settings

# إنشاء الجداول
models.Base.metadata.create_all(bind=engine)

# إعداد FastAPI
app = FastAPI(
    title="OmniFile Mobile API",
    description="API لتطبيق مراجعة OCR على الموبايل",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# إعداد المصادقة
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# دالة لإنشاء JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# دالة للحصول على المستخدم الحالي
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# دالة للحصول على المستخدم النشط
async def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# دالة للحصول على المستخدم المشرف
async def get_current_superuser(current_user: schemas.User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="The user doesn't have enough privileges")
    return current_user

# ============ مصادقة ============
@app.post("/api/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/users/", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    return crud.create_user(db=db, user=user)

@app.get("/api/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_active_user)):
    return current_user

# ============ مستندات ============
@app.post("/api/documents/", response_model=schemas.Document)
async def create_document(
    file: UploadFile = File(...),
    language: str = Form("ar"),
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # قراءة الملف
    contents = await file.read()

    # معالج OCR
    from modules.vision.ocr_engine import OCREngine
    ocr_engine = OCREngine(
        enable_trocr=settings.ENABLE_TROCR,
        enable_easyocr=settings.ENABLE_EASYOCR,
        enable_tesseract=settings.ENABLE_TESSERACT,
        enable_paddleocr=settings.ENABLE_PADDLEOCR,
        use_gpu=settings.USE_GPU,
        trocr_model=settings.TROCR_MODEL
    )

    # معالج الصورة
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(contents))

    # تحديد نوع الملف
    file_type = file.filename.split(".")[-1].lower()
    if file_type == "pdf":
        from modules.vision.pdf_processor import PDFProcessor
        pdf_proc = PDFProcessor()
        result = pdf_proc.process_pdf(contents)
        raw_text = "\n\n".join([page["text"] for page in result])
        page_count = len(result)
    else:
        result = ocr_engine.recognize(img, languages=[language])
        raw_text = result["text"]
        page_count = 1

    # حفظ الملف مؤقتًا
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    file_path = os.path.join(settings.TEMP_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(contents)

    # إنشاء مستند
    document = schemas.DocumentCreate(
        file_name=file.filename,
        raw_text=raw_text,
        page_count=page_count,
        language=language,
        confidence=result.get("confidence", 0.0),
        metadata={
            "file_type": file_type,
            "file_size": len(contents),
            "engine": result.get("source", "unknown"),
            "processing_time": result.get("processing_time", 0)
        }
    )

    return crud.create_document(db=db, document=document, owner_id=current_user.id)

@app.get("/api/documents/", response_model=List[schemas.Document])
async def read_documents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return crud.get_documents(db=db, skip=skip, limit=limit, status=status)

@app.get("/api/documents/{document_id}", response_model=schemas.Document)
async def read_document(
    document_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_document = crud.get_document(db=db, document_id=document_id)
    if db_document is None or db_document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_document

@app.put("/api/documents/{document_id}", response_model=schemas.Document)
async def update_document(
    document_id: str,
    document: schemas.DocumentBase,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_document = crud.get_document(db=db, document_id=document_id)
    if db_document is None or db_document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return crud.update_document(db=db, document_id=document_id, document=document)

@app.post("/api/documents/{document_id}/corrections")
async def save_corrections(
    document_id: str,
    corrected_text: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_document = crud.get_document(db=db, document_id=document_id)
    if db_document is None or db_document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    # تحديث المستند
    db_document = crud.update_document(
        db=db,
        document_id=document_id,
        document=schemas.DocumentBase(
            processed_text=corrected_text,
            status="reviewed"
        )
    )

    # تسجيل التصحيح
    correction = schemas.CorrectionCreate(
        original_text=db_document.raw_text,
        corrected_text=corrected_text,
        language=db_document.language,
        confidence=db_document.confidence,
        source="manual"
    )
    crud.create_correction(db=db, correction=correction)

    return {"status": "success"}

@app.post("/api/documents/{document_id}/mark_reviewed")
async def mark_document_as_reviewed(
    document_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_document = crud.get_document(db=db, document_id=document_id)
    if db_document is None or db_document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    return crud.update_document(
        db=db,
        document_id=document_id,
        document=schemas.DocumentBase(status="reviewed")
    )

@app.post("/api/documents/{document_id}/export")
async def export_document(
    document_id: str,
    format: str = "pdf",
    file_name: Optional[str] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_document = crud.get_document(db=db, document_id=document_id)
    if db_document is None or db_document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    text = db_document.processed_text or db_document.raw_text

    # تهيئة المصدّر
    from modules.export.exporter import TextExporter
    exporter = TextExporter(language=db_document.language)

    # تحديد اسم الملف
    if not file_name:
        file_name = f"{db_document.file_name.split('.')[0]}.{format}"

    # تصدير الملف
    output_path = os.path.join(settings.EXPORT_DIR, file_name)
    os.makedirs(settings.EXPORT_DIR, exist_ok=True)

    exporter.export(
        text=text,
        output_path=output_path,
        format=format,
        title=db_document.file_name,
        metadata={
            "file_name": db_document.file_name,
            "language": db_document.language,
            "confidence": db_document.confidence,
            "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

    return {"file_url": f"/exports/{file_name}"}

# ============ OCR ============
@app.post("/api/ocr/")
async def process_ocr(
    file: UploadFile = File(...),
    language: str = Form("ar"),
    current_user: schemas.User = Depends(get_current_active_user)
):
    # قراءة الملف
    contents = await file.read()

    # معالج OCR
    from modules.vision.ocr_engine import OCREngine
    ocr_engine = OCREngine(
        enable_trocr=settings.ENABLE_TROCR,
        enable_easyocr=settings.ENABLE_EASYOCR,
        enable_tesseract=settings.ENABLE_TESSERACT,
        enable_paddleocr=settings.ENABLE_PADDLEOCR,
        use_gpu=settings.USE_GPU,
        trocr_model=settings.TROCR_MODEL
    )

    # معالج الصورة
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(contents))

    result = ocr_engine.recognize(img, languages=[language])
    return result

# ============ اقتراحات ============
@app.post("/api/suggestions/")
async def get_suggestions(
    text: str,
    language: str = "ar",
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from modules.ai.active_learning import ActiveLearner
    active_learner = ActiveLearner(db_path="active_learning.db")
    suggestions = active_learner.get_suggestions(text, language, limit=5)
    return {"suggestions": suggestions}

# ============ نماذج مدربة ============
@app.get("/api/models/", response_model=List[schemas.FineTunedModel])
async def read_models(
    language: Optional[str] = None,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return crud.get_fine_tuned_models(db=db, language=language)

# ============ ملفات ثابت ============
app.mount("/exports", StaticFiles(directory=settings.EXPORT_DIR), name="exports")
app.mount("/temp", StaticFiles(directory=settings.TEMP_DIR), name="temp")

# ============ تشغيل الخادم ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
```

---

### **📄 `backend/Dockerfile`**
```dockerfile
# استخدام صورة Python رسمية
FROM python:3.10-slim

# تعيين مجلد العمل
WORKDIR /app

# تثبيت التبعيات النظام
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    libtesseract-dev \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملفات التبعيات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# تعريض المنفذ
EXPOSE 5001

# تشغيل الخادم
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
```

---
---
---

## 📱 **2. تطوير Frontend (Flutter)**
