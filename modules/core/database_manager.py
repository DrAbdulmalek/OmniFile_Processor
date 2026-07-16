"""
database_manager.py — نظام قاعدة البيانات المحسّن لـ OmniFile Processor

الميزات:
- بصمة الملف (SHA-256 Hash) لتجنب إعادة المعالجة
- البحث النصي الكامل (FTS5) للاسترجاع الفوري
- نسبة الثقة (Confidence Score) لتتبع جودة OCR
- نظام الكاش (Cache) لتسريع المعالجة على الدفعات

الاستخدام:
    from modules.core.database_manager import OmniDatabase
    db = OmniDatabase("my_archive.db")
    db.process_file(file_path, my_ai_engine)
    results = db.search_text("كسر عنق الفخذ")
"""

import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Callable


class OmniDatabase:
    """
    نظام إدارة قاعدة البيانات لمعالجة الملفات والأرشفة الرقمية.
    
    يجمع بين ثلاثة أنظمة:
    1. Hash-based Cache — تجنب إعادة المعالجة
    2. Full-Text Search (FTS5) — بحث دلالي فوري
    3. Confidence Tracking — تتبع جودة الاستخراج
    """

    def __init__(self, db_name: str = "omni_processor.db"):
        """
        تهيئة قاعدة البيانات.
        
        Args:
            db_name: مسار ملف قاعدة البيانات SQLite
        """
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """إنشاء الجداول اللازمة إذا لم تكن موجودة."""

        # 1. الجدول الأساسي لتخزين البيانات الوصفية
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT,
                file_extension TEXT,
                file_size INTEGER,
                category TEXT,
                subcategory TEXT,
                tags TEXT,
                extracted_text TEXT,
                process_date DATETIME,
                confidence_score REAL,
                ocr_engine TEXT,
                language TEXT,
                page_count INTEGER,
                processing_time REAL
            )
        ''')

        # 2. فهرس لتحسين البحث حسب التصنيف
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_category 
            ON processed_files(category)
        ''')

        # 3. فهرس لتحسين البحث حسب التاريخ
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_date 
            ON processed_files(process_date)
        ''')

        # 4. فهرس للبحث حسب نسبة الثقة
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_confidence 
            ON processed_files(confidence_score)
        ''')

        # 5. جدول البحث النصي الكامل (FTS5) — محرك البحث السريع
        self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts 
            USING fts5(
                content,
                file_name,
                category,
                tags,
                file_id UNINDEXED
            )
        ''')

        # 6. جدول لتخزين تاريخ التصحيحات اليدوية
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS corrections_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                original_text TEXT,
                corrected_text TEXT,
                correction_date DATETIME,
                FOREIGN KEY (file_id) REFERENCES processed_files(id)
            )
        ''')

        self.conn.commit()

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        توليد بصمة فريدة للملف بناءً على محتواه (SHA-256).
        
        Args:
            file_path: مسار الملف
            
        Returns:
            سلسلة hex تمثل البصمة الفريدة (64 حرف)
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def check_file_exists(self, file_hash: str) -> Optional[Tuple]:
        """
        التحقق مما إذا كان الملف قد تمت معالجته سابقاً.
        
        Args:
            file_hash: بصمة الملف
            
        Returns:
            tuple (category, extracted_text, confidence_score) أو None
        """
        self.cursor.execute(
            "SELECT category, extracted_text, confidence_score, ocr_engine "
            "FROM processed_files WHERE file_hash = ?",
            (file_hash,)
        )
        return self.cursor.fetchone()

    def save_record(
        self,
        file_hash: str,
        file_name: str,
        file_path: str,
        category: str,
        text: str,
        confidence: float = 0.0,
        ocr_engine: str = "unknown",
        language: str = "ar",
        tags: str = "",
        subcategory: str = "",
        page_count: int = 1,
        processing_time: float = 0.0
    ) -> bool:
        """
        حفظ سجل معالجة جديد في قاعدة البيانات.
        
        Args:
            file_hash: بصمة الملف الفريدة
            file_name: اسم الملف الأصلي
            file_path: مسار الملف
            category: التصنيف الرئيسي
            text: النص المستخرج
            confidence: نسبة الثقة (0.0 - 1.0)
            ocr_engine: محرك OCR المستخدم
            language: لغة المحتوى
            tags: وسوم إضافية (مفصولة بفواصل)
            subcategory: التصنيف الفرعي
            page_count: عدد الصفحات
            processing_time: زمن المعالجة بالثواني
            
        Returns:
            True إذا تم الحفظ بنجاح، False إذا كان الملف موجوداً
        """
        try:
            file_ext = os.path.splitext(file_name)[1].lower()
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            self.cursor.execute('''
                INSERT INTO processed_files 
                (file_hash, file_name, file_path, file_extension, file_size,
                 category, subcategory, tags, extracted_text, process_date,
                 confidence_score, ocr_engine, language, page_count, processing_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_hash, file_name, file_path, file_ext, file_size,
                category, subcategory, tags, text, datetime.now(),
                confidence, ocr_engine, language, page_count, processing_time
            ))

            # إضافة النص إلى محرك البحث السريع
            last_id = self.cursor.lastrowid
            self.cursor.execute(
                "INSERT INTO files_fts(content, file_name, category, tags, file_id) VALUES (?, ?, ?, ?, ?)",
                (text, file_name, category, tags, last_id)
            )

            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def search_text(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        البحث السريع جداً عن أي كلمة أو جملة داخل الملفات المعالجة.
        
        يستخدم محرك FTS5 للاسترجاع الفوري مع تمييز السياق.
        
        Args:
            query: كلمة أو جملة البحث
            limit: الحد الأقصى للنتائج
            
        Returns:
            قائمة من القواميس تحتوي على تفاصيل كل نتيجة
        """
        search_query = """
            SELECT 
                p.file_name, 
                p.file_path, 
                p.category,
                p.confidence_score,
                p.process_date,
                snippet(files_fts, 0, '<b>', '</b>', '...', 32) as context_snippet
            FROM processed_files p
            JOIN files_fts f ON p.id = f.file_id
            WHERE files_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """

        try:
            self.cursor.execute(search_query, (query, limit))
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            return []

    def search_by_category(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        البحث حسب التصنيف الرئيسي.
        
        Args:
            category: اسم التصنيف
            limit: الحد الأقصى للنتائج
        """
        self.cursor.execute(
            "SELECT * FROM processed_files WHERE category = ? ORDER BY process_date DESC LIMIT ?",
            (category, limit)
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def get_low_confidence_files(self, threshold: float = 0.7, limit: int = 50) -> List[Dict[str, Any]]:
        """
        الحصول على الملفات التي حصلت على نسبة ثقة منخفضة — تحتاج مراجعة يدوية.
        
        Args:
            threshold: حد الثقة الأدنى
            limit: الحد الأقصى للنتائج
        """
        self.cursor.execute(
            "SELECT file_name, file_path, category, confidence_score, extracted_text "
            "FROM processed_files WHERE confidence_score < ? "
            "ORDER BY confidence_score ASC LIMIT ?",
            (threshold, limit)
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def log_correction(self, file_id: int, original_text: str, corrected_text: str):
        """
        تسجيل تصحيح يدوي للنص المستخرج.
        
        Args:
            file_id: معرف الملف في قاعدة البيانات
            original_text: النص الأصلي (قبل التصحيح)
            corrected_text: النص المصحح
        """
        self.cursor.execute('''
            INSERT INTO corrections_log (file_id, original_text, corrected_text, correction_date)
            VALUES (?, ?, ?, ?)
        ''', (file_id, original_text, corrected_text, datetime.now()))
        self.conn.commit()

    def get_statistics(self) -> Dict[str, Any]:
        """
        الحصول على إحصائيات شاملة عن قاعدة البيانات.
        
        Returns:
            قاموس يحتوي على الإحصائيات
        """
        stats = {}

        # إجمالي الملفات المعالجة
        self.cursor.execute("SELECT COUNT(*) as total FROM processed_files")
        stats["total_files"] = self.cursor.fetchone()["total"]

        # إجمالي الملفات المخزنة مؤقتاً (cache hits)
        self.cursor.execute("SELECT COUNT(*) as cached FROM processed_files WHERE processing_time = 0")
        stats["cached_files"] = self.cursor.fetchone()["cached"]

        # متوسط نسبة الثقة
        self.cursor.execute("SELECT AVG(confidence_score) as avg_conf FROM processed_files")
        result = self.cursor.fetchone()["avg_conf"]
        stats["average_confidence"] = round(result, 4) if result else 0.0

        # عدد الملفات حسب التصنيف
        self.cursor.execute(
            "SELECT category, COUNT(*) as count FROM processed_files "
            "GROUP BY category ORDER BY count DESC"
        )
        stats["categories"] = [dict(row) for row in self.cursor.fetchall()]

        # عدد الملفات حسب اللغة
        self.cursor.execute(
            "SELECT language, COUNT(*) as count FROM processed_files "
            "GROUP BY language ORDER BY count DESC"
        )
        stats["languages"] = [dict(row) for row in self.cursor.fetchall()]

        # عدد الملفات حسب المحرك
        self.cursor.execute(
            "SELECT ocr_engine, COUNT(*) as count FROM processed_files "
            "GROUP BY ocr_engine ORDER BY count DESC"
        )
        stats["engines"] = [dict(row) for row in self.cursor.fetchall()]

        # إجمالي التصحيحات اليدوية
        self.cursor.execute("SELECT COUNT(*) as total FROM corrections_log")
        stats["total_corrections"] = self.cursor.fetchone()["total"]

        return stats

    def process_file(
        self,
        file_path: str,
        ai_engine: Callable,
        force_reprocess: bool = False
    ) -> Tuple[str, str, float]:
        """
        معالجة ملف كامل مع نظام الكاش التلقائي.
        
        هذه هي الدالة الرئيسية التي تربط قاعدة البيانات بمحرك المعالجة.
        
        Args:
            file_path: مسار الملف
            ai_engine: دالة المعالجة يجب أن ترجع (category, text, confidence, engine, lang)
            force_reprocess: إعادة المعالجة حتى لو كان الملف موجوداً في الكاش
            
        Returns:
            tuple (category, extracted_text, confidence_score)
        """
        import time

        # 1. حساب بصمة الملف
        file_hash = self.calculate_file_hash(file_path)

        # 2. التحقق من الكاش (إلا إذا طلب إعادة المعالجة)
        if not force_reprocess:
            cached = self.check_file_exists(file_hash)
            if cached:
                print(f"  ✅ كاش: {os.path.basename(file_path)} ← {cached[0]} ({cached[2]:.0%})")
                return cached[0], cached[1], cached[2]

        # 3. المعالجة الثقيلة (OCR + NLP)
        start_time = time.time()
        result = ai_engine(file_path)
        processing_time = time.time() - start_time

        # 4. حفظ النتيجة
        if len(result) >= 5:
            category, text, confidence, engine, lang = result[0], result[1], result[2], result[3], result[4]
        elif len(result) == 3:
            category, text, confidence = result
            engine, lang = "unknown", "ar"
        else:
            category, text = result[0], result[1]
            confidence, engine, lang = 0.0, "unknown", "ar"

        self.save_record(
            file_hash=file_hash,
            file_name=os.path.basename(file_path),
            file_path=file_path,
            category=category,
            text=text,
            confidence=confidence,
            ocr_engine=engine,
            language=lang,
            processing_time=processing_time
        )

        print(f"  🆕 جديد: {os.path.basename(file_path)} → {category} ({confidence:.0%}) [{processing_time:.1f}s]")
        return category, text, confidence

    def close(self):
        """إغلاق اتصال قاعدة البيانات."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
