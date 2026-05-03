"""
src/database.py — Backward Compatibility Layer
═════════════════════════════════════════════════
⚠️  هذا الملف يُبقى للتوافق مع الكود القديم فقط.
سيتم حذفه في v5.0.

الموقع الجديد: modules/core/handwriting_db.py
"""

from modules.core.handwriting_db import HandwritingDB, DB_SCHEMA_VERSION

__all__ = ["HandwritingDB", "DB_SCHEMA_VERSION"]

