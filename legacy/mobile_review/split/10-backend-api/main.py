# main.py - FastAPI backend for OmniFile
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
