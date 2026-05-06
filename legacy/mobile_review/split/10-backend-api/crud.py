# crud.py - OmniFile backend component
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
