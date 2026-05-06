# models.py - OmniFile backend component
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
