"""
backend/utils.py
================
Utility functions for the Medical OCR backend.
وظائف مساعدة لخلفية OCR الطبي.
"""

import os
import shutil
import uuid
import time
from pathlib import Path
from typing import Optional, Dict, Any


def get_upload_dir() -> Path:
    """الحصول على مجلد الرفع (يُنشأ إذا لم يكن موجوداً)."""
    upload_dir = Path(os.environ.get("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_media_dir() -> Path:
    """الحصول على مجلد الوسائط (يُنشأ إذا لم يكن موجوداً)."""
    media_dir = Path(os.environ.get("MEDIA_DIR", "media/ocr_results"))
    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir


def generate_unique_filename(original_name: str) -> str:
    """توليد اسم ملف فريد لمنع التعارض."""
    ext = Path(original_name).suffix
    unique_id = uuid.uuid4().hex[:8]
    return f"{unique_id}_{original_name}"


def cleanup_old_files(directory: Path, max_age_hours: int = 24):
    """
    حذف الملفات القديمة من مجلد.

    Args:
        directory: المسار المراد تنظيفه
        max_age_hours: العمر الأقصى بالساعات
    """
    if not directory.exists():
        return

    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0

    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.stat().st_mtime < cutoff:
            try:
                file_path.unlink()
                removed += 1
            except OSError:
                pass

    if removed > 0:
        print(f"[Cleanup] تم حذف {removed} ملف قديم من {directory}")


def validate_file_type(filename: str, allowed_extensions: set = None) -> bool:
    """
    التحقق من نوع الملف.

    Args:
        filename: اسم الملف
        allowed_extensions: الامتدادات المسموحة (default: PDF + images)

    Returns:
        True إذا كان النوع مسموحاً
    """
    if allowed_extensions is None:
        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


def get_file_size_mb(filepath: str) -> float:
    """الحصول على حجم الملف بالميجابايت."""
    return Path(filepath).stat().st_size / (1024 * 1024)


def format_processing_time(ms: float) -> str:
    """تنسيق وقت المعالجة."""
    if ms < 1000:
        return f"{ms:.0f} ms"
    elif ms < 60000:
        return f"{ms/1000:.1f} sec"
    else:
        return f"{ms/60000:.1f} min"
