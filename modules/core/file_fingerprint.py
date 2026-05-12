"""
نظام بصمة الملفات (File Fingerprinting System)
================================================
وحدة متخصصة لإدارة بصمات الملفات ومنع إعادة المعالجة.

الوظائف:
- حساب بصمة SHA-256 لأي ملف
- إدارة سجل المعالجة في قاعدة بيانات SQLite
- كشف الملفات المكررة
- تنظيف السجلات القديمة
- إحصائيات الأرشيف

الاستخدام:
    from modules.core.file_fingerprint import FileFingerprintManager
    mgr = FileFingerprintManager()
    is_new = mgr.is_new_file("/path/to/document.pdf")
    mgr.mark_processed("/path/to/document.pdf", category="medical")
"""

import hashlib
import os
from modules.core.base_db import BaseDB
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class FileFingerprintManager(BaseDB):
    """
    مدير بصمات الملفات — يمنع إعادة معالجة الملفات المتطابقة.

    يستخدم خوارزمية SHA-256 لتوليد بصمة فريدة لكل ملف بناءً على محتواه،
    ويخزنها في قاعدة بيانات SQLite خفيفة لضمان سرعة الفحص.
    """

    def __init__(self, db_path: str = "omni_fingerprints.db"):
        """
        تهيئة مدير البصمات.

        Args:
            db_path: مسار ملف قاعدة البيانات SQLite
        """
        super().__init__(db_path)
        logger.info("تم تهيئة مدير بصمات الملفات: %s", db_path)

    def _create_schema(self, conn):
        """إنشاء جداول قاعدة البيانات."""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS file_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT,
                file_extension TEXT,
                file_size INTEGER,
                category TEXT DEFAULT 'uncategorized',
                subcategory TEXT DEFAULT '',
                status TEXT DEFAULT 'processed',
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified REAL,
                processing_time REAL DEFAULT 0.0,
                ocr_engine TEXT DEFAULT 'unknown',
                confidence_score REAL DEFAULT 0.0,
                notes TEXT DEFAULT ''
            )
        ''')

        # فهرس للبحث السريع
        conn.execute('CREATE INDEX IF NOT EXISTS idx_hash ON file_fingerprints(file_hash)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_category ON file_fingerprints(category)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON file_fingerprints(status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_date ON file_fingerprints(processed_at)')

        # جدول سجل العمليات
        conn.execute('''
            CREATE TABLE IF NOT EXISTS processing_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    @staticmethod
    def calculate_hash(file_path: str, algorithm: str = "sha256") -> str:
        """
        حساب بصمة فريدة للملف.

        Args:
            file_path: مسار الملف
            algorithm: خوارزمية التجزئة (sha256 أو md5)

        Returns:
            سلسلة hex تمثل البصمة الفريدة
        """
        if algorithm == "md5":
            hasher = hashlib.md5()
        else:
            hasher = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(8192), b""):
                hasher.update(byte_block)
        return hasher.hexdigest()

    @staticmethod
    def calculate_hash_from_bytes(data: bytes, algorithm: str = "sha256") -> str:
        """
        حساب بصمة من بيانات خام.

        Args:
            data: البيانات الثنائية
            algorithm: خوارزمية التجزئة

        Returns:
            سلسلة hex تمثل البصمة
        """
        if algorithm == "md5":
            hasher = hashlib.md5()
        else:
            hasher = hashlib.sha256()
        hasher.update(data)
        return hasher.hexdigest()

    def is_new_file(self, file_path: str) -> bool:
        """
        التحقق مما إذا كان الملف جديداً (لم تتم معالجته سابقاً).

        Args:
            file_path: مسار الملف

        Returns:
            True إذا كان الملف جديداً
        """
        try:
            file_hash = self.calculate_hash(file_path)
            with self.connection() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM file_fingerprints WHERE file_hash = ?",
                    (file_hash,)
                )
                result = cursor.fetchone()
            return result is None
        except Exception as e:
            logger.error("خطأ في فحص الملف %s: %s", file_path, e)
            return True

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        الحصول على معلومات ملف سبق معالجته.

        Args:
            file_path: مسار الملف

        Returns:
            قاموس بمعلومات الملف أو None إذا لم يكن موجوداً
        """
        try:
            file_hash = self.calculate_hash(file_path)
            with self.connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM file_fingerprints WHERE file_hash = ?",
                    (file_hash,)
                )
                row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error("خطأ في استرجاع معلومات الملف: %s", e)
            return None

    def mark_processed(
        self,
        file_path: str,
        category: str = "uncategorized",
        subcategory: str = "",
        status: str = "processed",
        ocr_engine: str = "unknown",
        confidence_score: float = 0.0,
        processing_time: float = 0.0,
        notes: str = ""
    ) -> bool:
        """
        تسجيل ملف كمعالج في قاعدة البيانات.

        Args:
            file_path: مسار الملف
            category: التصنيف الرئيسي
            subcategory: التصنيف الفرعي
            status: حالة المعالجة (processed, failed, skipped)
            ocr_engine: محرك OCR المستخدم
            confidence_score: نسبة الثقة
            processing_time: زمن المعالجة بالثواني
            notes: ملاحظات إضافية

        Returns:
            True إذا تم التسجيل بنجاح
        """
        try:
            file_hash = self.calculate_hash(file_path)
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            last_modified = os.path.getmtime(file_path) if os.path.exists(file_path) else 0

            with self.connection() as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO file_fingerprints
                    (file_hash, file_name, file_path, file_extension, file_size,
                     category, subcategory, status, processing_time, ocr_engine,
                     confidence_score, notes, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_hash, file_name, file_path, file_ext, file_size,
                    category, subcategory, status, processing_time, ocr_engine,
                    confidence_score, notes, last_modified
                ))

                # تسجيل العملية
                conn.execute('''
                    INSERT INTO processing_log (file_hash, action, details)
                    VALUES (?, ?, ?)
                ''', (file_hash, "processed", f"category={category}, engine={ocr_engine}"))

            logger.info("تم تسجيل بصمة: %s [%s]", file_name, category)
            return True
        except Exception as e:
            logger.error("خطأ في تسجيل البصمة: %s", e)
            if "UNIQUE constraint" in str(e):
                logger.debug("الملف مسجل مسبقاً: %s", file_path)
            return False

    def find_duplicates(self, directory: str) -> List[List[Dict[str, Any]]]:
        """
        البحث عن الملفات المكررة في مجلد.

        Args:
            directory: المسار المراد فحصه

        Returns:
            قائمة مجموعات الملفات المكررة
        """
        hash_map: Dict[str, List[Dict[str, Any]]] = {}

        for root, _, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    file_hash = self.calculate_hash(filepath)
                    if file_hash not in hash_map:
                        hash_map[file_hash] = []
                    hash_map[file_hash].append({
                        "path": filepath,
                        "name": filename,
                        "size": os.path.getsize(filepath)
                    })
                except (PermissionError, OSError):
                    continue

        # تصفية: فقط المجموعات التي تحتوي أكثر من ملف
        duplicates = [group for group in hash_map.values() if len(group) > 1]
        logger.info("تم العثور على %d مجموعة مكررة في %s", len(duplicates), directory)
        return duplicates

    def get_statistics(self) -> Dict[str, Any]:
        """
        الحصول على إحصائيات شاملة عن الأرشيف.

        Returns:
            قاموس يحتوي على الإحصائيات
        """
        with self.connection() as conn:
            stats = {}

            # إجمالي الملفات
            cursor = conn.execute("SELECT COUNT(*) as total FROM file_fingerprints")
            stats["total_files"] = cursor.fetchone()["total"]

            # عدد الملفات حسب التصنيف
            cursor = conn.execute(
                "SELECT category, COUNT(*) as count FROM file_fingerprints "
                "GROUP BY category ORDER BY count DESC"
            )
            stats["by_category"] = [dict(row) for row in cursor.fetchall()]

            # عدد الملفات حسب الامتداد
            cursor = conn.execute(
                "SELECT file_extension, COUNT(*) as count FROM file_fingerprints "
                "GROUP BY file_extension ORDER BY count DESC LIMIT 20"
            )
            stats["by_extension"] = [dict(row) for row in cursor.fetchall()]

            # عدد الملفات حسب الحالة
            cursor = conn.execute(
                "SELECT status, COUNT(*) as count FROM file_fingerprints "
                "GROUP BY status"
            )
            stats["by_status"] = [dict(row) for row in cursor.fetchall()]

            # متوسط نسبة الثقة
            cursor = conn.execute(
                "SELECT AVG(confidence_score) as avg_conf FROM file_fingerprints"
            )
            result = cursor.fetchone()["avg_conf"]
            stats["average_confidence"] = round(result, 4) if result else 0.0

            # إجمالي حجم الملفات
            cursor = conn.execute(
                "SELECT SUM(file_size) as total_size FROM file_fingerprints"
            )
            result = cursor.fetchone()["total_size"]
            stats["total_size_bytes"] = result or 0
            stats["total_size_mb"] = round((result or 0) / (1024 * 1024), 2)

            # متوسط زمن المعالجة
            cursor = conn.execute(
                "SELECT AVG(processing_time) as avg_time FROM file_fingerprints WHERE processing_time > 0"
            )
            result = cursor.fetchone()["avg_time"]
            stats["average_processing_time"] = round(result, 2) if result else 0.0

        # حجم قاعدة البيانات
        if os.path.exists(self.db_path):
            stats["database_size_bytes"] = os.path.getsize(self.db_path)

        return stats

    def get_pending_files(self, directory: str, extensions: List[str] = None) -> List[str]:
        """
        الحصول على قائمة الملفات التي لم تتم معالجتها بعد في مجلد.

        Args:
            directory: المسار المراد فحصه
            extensions: قائمة الامتدادات المقبولة (مثل ['.pdf', '.png'])

        Returns:
            قائمة بمسارات الملفات الجديدة
        """
        if extensions is None:
            extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']

        new_files = []
        for root, _, files in os.walk(directory):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in extensions:
                    continue
                filepath = os.path.join(root, filename)
                if self.is_new_file(filepath):
                    new_files.append(filepath)

        logger.info("تم العثور على %d ملف جديد في %s", len(new_files), directory)
        return new_files

    def cleanup_old_records(self, days: int = 90) -> int:
        """
        حذف السجلات القديمة من قاعدة البيانات.

        Args:
            days: عدد الأيام للحفاظ على السجلات

        Returns:
            عدد السجلات المحذوفة
        """
        cutoff = datetime.now() - timedelta(days=days)
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM file_fingerprints WHERE processed_at < ?",
                (cutoff.isoformat(),)
            )
            deleted = cursor.rowcount
        logger.info("تم حذف %d سجل قديم (أقدم من %d يوم)", deleted, days)
        return deleted

    def export_fingerprints(self, output_path: str) -> bool:
        """
        تصدير سجل البصمات إلى ملف JSON.

        Args:
            output_path: مسار ملف التصدير

        Returns:
            True إذا تم التصدير بنجاح
        """
        try:
            import json
            with self.connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM file_fingerprints ORDER BY processed_at DESC"
                )
                records = [dict(row) for row in cursor.fetchall()]

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2, default=str)

            logger.info("تم تصدير %d بصمة إلى %s", len(records), output_path)
            return True
        except Exception as e:
            logger.error("خطأ في تصدير البصمات: %s", e)
            return False

    def close(self):
        """إغلاق اتصال قاعدة البيانات (no-op: BaseDB manages connections)."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
