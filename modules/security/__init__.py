"""
وحدة التنظيم والحماية (File Management & Security)
=====================================================
القدرات:
- أتمتة فرز الملفات بناءً على محتواها
- حماية الأكواد البرمجية من التعديل
- التعامل مع الأرشيفات المحمية بكلمات مرور
- فحص سلامة الملفات
- إدارة الإصدارات والنسخ الاحتياطية
- التعامل الآمن مع رفع الملفات (Secure File Handler)
"""
from modules.security.file_organizer import FileOrganizer
from modules.security.code_protector import CodeProtector
from modules.security.archive_handler import ArchiveHandler
from modules.security.file_scanner import FileScanner
from modules.security.backup_manager import BackupManager
from modules.security.secure_file_handler import SecureFileHandler
from modules.security.encryption import FileEncryptor
from modules.security.sensitive_data_scanner import SensitiveDataScanner

try:
    from modules.security.audit_logger import AuditLogger, get_audit_logger
    _audit_available = True
except ImportError:
    _audit_available = False

__all__ = [
    "FileOrganizer", "CodeProtector", "ArchiveHandler",
    "FileScanner", "BackupManager", "SecureFileHandler",
    "FileEncryptor", "SensitiveDataScanner",
]

if _audit_available:
    __all__.extend(["AuditLogger", "get_audit_logger"])
