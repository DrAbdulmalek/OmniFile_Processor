# config.py - OmniFile backend component
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
