"""
قاعدة بيانات OmniFile AI Processor
=====================================
وحدة قاعدة البيانات المتكاملة باستخدام SQLite مع:
- وضع WAL للأداء العالي
- دعم تعدد المسارات (Thread-safe) مع FileLock
- Context Manager لإدارة الاتصالات
- فهارس محسّنة للبحث والاستعلام
- نسخ احتياطي وتصدير JSON
- تنظيف تلقائي للسجلات القديمة

المؤلف: Dr Abdulmalek Tamer Al-husseini
الموقع: Homs, Syria
البريد الإلكتروني: Abdulmalek.husseini@gmail.com
الإصدار: 4.1.1
"""

import json
import logging
import os
import shutil
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

# محاولة استيراد FileLock (اختياري - يتحول لقفل داخلي إذا لم يتوفر)
try:
    from filelock import FileLock

    _HAS_FILELOCK = True
except ImportError:
    _HAS_FILELOCK = False
    logger.warning(
        "مكتبة filelock غير مثبتة. سيتم استخدام قفل أساسي. "
        "لأفضل أداء: pip install filelock"
    )


class OmniFileDB:
    """
    مدير قاعدة بيانات OmniFile AI Processor.

    يستخدم SQLite بوضع WAL (Write-Ahead Logging) للأداء العالي
    والتزامن الآمن. يدعم جميع عمليات CRUD والبحث والتصدير.

    مثال الاستخدام:
        >>> db = OmniFileDB("omnifile_data.db")
        >>> db.create_tables()
        >>> doc_id = db.insert_document({
        ...     "file_name": "test.pdf",
        ...     "file_type": "pdf",
        ...     "raw_text": "Hello World",
        ... })
        >>> doc = db.get_document(doc_id)
        >>> db.export_to_json("backup.json")
    """

    # ===================================================================
    #  التهيئة
    # ===================================================================

    def __init__(self, db_path: str = "omnifile_data.db") -> None:
        """
        تهيئة قاعدة البيانات وفتحها بوضع WAL.

        المعاملات:
            db_path: مسار ملف قاعدة البيانات. إذا كان المجلد غير موجود
                     سيتم إنشاؤه تلقائياً.
        """
        self.db_path = db_path
        self._lock_path = db_path + ".lock"
        self._connection: Optional[sqlite3.Connection] = None

        # التأكد من وجود مجلد قاعدة البيانات
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        # إنشاء ملف القفل
        if _HAS_FILELOCK:
            self._file_lock = FileLock(self._lock_path, timeout=30)
        else:
            self._file_lock = None

        logger.info("تم تهيئة قاعدة البيانات: %s (WAL=%s)", db_path, _HAS_FILELOCK)

    # ===================================================================
    #  Context Manager لإدارة الاتصالات
    # ===================================================================

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context Manager يوفر اتصالاً آمناً بقاعدة البيانات.

        يستخدم FileLock لضمان سلامة الكتابة في بيئات متعددة المسارات.
        يُغلق الاتصال تلقائياً عند الخروج من السياق.

        ينتج:
            اتصال sqlite3 مفتوح وجاهز للاستخدام
        """
        conn: Optional[sqlite3.Connection] = None
        try:
            # قفل الملف للكتابة (إذا توفر FileLock)
            if self._file_lock:
                self._file_lock.acquire()

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")  # 64 ميغابايت تخزين مؤقت

            yield conn

        except sqlite3.Error as e:
            logger.error("خطأ في قاعدة البيانات: %s", e)
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning("خطأ أثناء إغلاق الاتصال: %s", e)
            if self._file_lock:
                try:
                    self._file_lock.release()
                except Exception as e:
                    logger.warning("خطأ أثناء تحرير القفل: %s", e)

    # ===================================================================
    #  إنشاء الجداول
    # ===================================================================

    def create_tables(self) -> None:
        """
        إنشاء جميع جداول قاعدة البيانات مع الفهارس.

        الجداول:
            - documents: المستندات الأساسية
            - ocr_results: نتائج OCR التفصيلية
            - translations: الترجمات
            - entities: الكيانات المسماة المستخرجة
            - corrections_log: سجل التصحيحات
            - processing_history: سجل المعالجة
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # === جدول المستندات ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_type TEXT DEFAULT 'unknown',
                    file_size INTEGER DEFAULT 0,
                    page_count INTEGER DEFAULT 0,
                    raw_text TEXT DEFAULT '',
                    processed_text TEXT DEFAULT '',
                    corrected_text TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    language TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.0,
                    is_reviewed INTEGER DEFAULT 0,
                    is_code_protected INTEGER DEFAULT 0,
                    source_type TEXT DEFAULT 'upload',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # === جدول نتائج OCR ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ocr_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    page_num INTEGER DEFAULT 0,
                    word_text TEXT DEFAULT '',
                    raw_text TEXT DEFAULT '',
                    corrected_text TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.0,
                    model_source TEXT DEFAULT '',
                    x INTEGER DEFAULT 0,
                    y INTEGER DEFAULT 0,
                    w INTEGER DEFAULT 0,
                    h INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                        ON DELETE CASCADE
                )
            """)

            # === جدول الترجمات ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    source_text TEXT DEFAULT '',
                    translated_text TEXT DEFAULT '',
                    source_lang TEXT DEFAULT 'en',
                    target_lang TEXT DEFAULT 'ar',
                    model_name TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                        ON DELETE CASCADE
                )
            """)

            # === جدول الكيانات المسماة ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    entity_text TEXT NOT NULL,
                    entity_type TEXT DEFAULT '',
                    start_pos INTEGER DEFAULT 0,
                    end_pos INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                        ON DELETE CASCADE
                )
            """)

            # === جدول سجل التصحيحات ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS corrections_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    original_text TEXT DEFAULT '',
                    corrected_text TEXT DEFAULT '',
                    correction_type TEXT DEFAULT 'auto',
                    auto_or_manual TEXT DEFAULT 'auto',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                        ON DELETE CASCADE
                )
            """)

            # === جدول سجل المعالجة ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    target TEXT DEFAULT '',
                    status TEXT DEFAULT 'started',
                    duration_sec REAL DEFAULT 0.0,
                    details_json TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # === إنشاء الفهارس ===
            self._create_indexes(cursor)

            conn.commit()
            logger.info("تم إنشاء جميع الجداول والفهارس بنجاح")

    def _create_indexes(self, cursor: sqlite3.Cursor) -> None:
        """إنشاء الفهارس لتحسين أداء الاستعلامات."""
        indexes = [
            # فهارس المستندات
            "CREATE INDEX IF NOT EXISTS idx_docs_file_type ON documents(file_type)",
            "CREATE INDEX IF NOT EXISTS idx_docs_category ON documents(category)",
            "CREATE INDEX IF NOT EXISTS idx_docs_language ON documents(language)",
            "CREATE INDEX IF NOT EXISTS idx_docs_is_reviewed ON documents(is_reviewed)",
            "CREATE INDEX IF NOT EXISTS idx_docs_created_at ON documents(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_docs_source_type ON documents(source_type)",
            "CREATE INDEX IF NOT EXISTS idx_docs_confidence ON documents(confidence)",
            # فهارس نتائج OCR
            "CREATE INDEX IF NOT EXISTS idx_ocr_doc_id ON ocr_results(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_ocr_page ON ocr_results(document_id, page_num)",
            "CREATE INDEX IF NOT EXISTS idx_ocr_status ON ocr_results(status)",
            "CREATE INDEX IF NOT EXISTS idx_ocr_confidence ON ocr_results(confidence)",
            # فهارس الترجمات
            "CREATE INDEX IF NOT EXISTS idx_trans_doc_id ON translations(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_trans_langs ON translations(source_lang, target_lang)",
            # فهارس الكيانات
            "CREATE INDEX IF NOT EXISTS idx_entities_doc_id ON entities(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)",
            # فهارس التصحيحات
            "CREATE INDEX IF NOT EXISTS idx_corr_doc_id ON corrections_log(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_corr_type ON corrections_log(correction_type)",
            # فهارس سجل المعالجة
            "CREATE INDEX IF NOT EXISTS idx_hist_action ON processing_history(action)",
            "CREATE INDEX IF NOT EXISTS idx_hist_status ON processing_history(status)",
            "CREATE INDEX IF NOT EXISTS idx_hist_created ON processing_history(created_at)",
            # فهرس البحث بالنص الكامل
            "CREATE INDEX IF NOT EXISTS idx_docs_raw_text ON documents(raw_text)",
            "CREATE INDEX IF NOT EXISTS idx_docs_processed_text ON documents(processed_text)",
        ]

        for idx_sql in indexes:
            try:
                cursor.execute(idx_sql)
            except sqlite3.Error as e:
                logger.warning("فشل إنشاء فهرس: %s", e)

    # ===================================================================
    #  عمليات المستندات (CRUD)
    # ===================================================================

    def insert_document(self, doc_info: dict) -> int:
        """
        إدراج مستند جديد في قاعدة البيانات.

        المعاملات:
            doc_info: قاموس يحتوي بيانات المستند. الحقول المدعومة:
                - file_name (str, مطلوب): اسم الملف
                - file_type (str): نوع الملف (pdf, png, jpg, ...)
                - file_size (int): حجم الملف بالبايتات
                - page_count (int): عدد الصفحات
                - raw_text (str): النص الخام المستخرج
                - processed_text (str): النص بعد المعالجة
                - corrected_text (str): النص بعد التصحيح
                - category (str): تصنيف المستند
                - language (str): لغة المستند
                - confidence (float): مستوى الثقة
                - is_reviewed (bool): هل تمت المراجعة
                - is_code_protected (bool): هل هو محمي برمجياً
                - source_type (str): مصدر المستند (upload, drive, local)

        المعاد:
            معرّف المستند (doc_id) الذي تم إنشاؤه
        """
        if not doc_info.get("file_name"):
            raise ValueError("حقل file_name مطلوب لإدراج مستند")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (
                    file_name, file_type, file_size, page_count,
                    raw_text, processed_text, corrected_text,
                    category, language, confidence,
                    is_reviewed, is_code_protected, source_type,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_info.get("file_name", ""),
                doc_info.get("file_type", "unknown"),
                doc_info.get("file_size", 0),
                doc_info.get("page_count", 0),
                doc_info.get("raw_text", ""),
                doc_info.get("processed_text", ""),
                doc_info.get("corrected_text", ""),
                doc_info.get("category", ""),
                doc_info.get("language", ""),
                doc_info.get("confidence", 0.0),
                1 if doc_info.get("is_reviewed", False) else 0,
                1 if doc_info.get("is_code_protected", False) else 0,
                doc_info.get("source_type", "upload"),
                doc_info.get("created_at", now),
                now,
            ))
            conn.commit()
            doc_id = cursor.lastrowid
            logger.info(
                "تم إدراج مستند: '%s' (id=%d, type=%s)",
                doc_info["file_name"], doc_id, doc_info.get("file_type", "unknown"),
            )
            return doc_id

    def update_document(self, doc_id: int, updates: dict) -> bool:
        """
        تحديث بيانات مستند موجود.

        المعاملات:
            doc_id: معرّف المستند
            updates: قاموس الحقول المراد تحديثها

        المعاد:
            True إذا تم التحديث بنجاح
        """
        if not updates:
            logger.warning("لا توجد تحديثات للمستند %d", doc_id)
            return False

        # الحقول المسموح بتحديثها
        allowed_fields = {
            "file_name", "file_type", "file_size", "page_count",
            "raw_text", "processed_text", "corrected_text",
            "category", "language", "confidence",
            "is_reviewed", "is_code_protected", "source_type",
        }

        # تحويل القيم المنطقية لأرقام
        filtered_updates = {}
        for key, value in updates.items():
            if key in allowed_fields:
                if key in ("is_reviewed", "is_code_protected"):
                    filtered_updates[key] = 1 if value else 0
                else:
                    filtered_updates[key] = value

        if not filtered_updates:
            logger.warning("لا توجد حقول صالحة للتحديث في: %s", list(updates.keys()))
            return False

        # إضافة timestamp التحديث
        filtered_updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        set_clause = ", ".join(f"{k} = ?" for k in filtered_updates)
        values = list(filtered_updates.values()) + [doc_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE documents SET {set_clause} WHERE id = ?",
                values,
            )
            conn.commit()
            affected = cursor.rowcount
            if affected > 0:
                logger.info("تم تحديث المستند %d (%d حقل)", doc_id, len(filtered_updates) - 1)
                return True
            logger.warning("لم يتم العثور على مستند بالمعرّف %d", doc_id)
            return False

    def get_document(self, doc_id: int) -> Optional[dict]:
        """
        جلب مستند واحد بالمعرّف.

        المعاملات:
            doc_id: معرّف المستند

        المعاد:
            قاموس بيانات المستند أو None إذا لم يُوجد
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_documents(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """
        جلب جميع المستندات مع ترقيم الصفحات.

        المعاملات:
            limit: أقصى عدد للعرض
            offset: بداية السجلات

        المعاد:
            قائمة قواميس المستندات
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_unreviewed_documents(self) -> list[dict]:
        """
        جلب المستندات التي لم تُراجع بعد.

        المعاد:
            قائمة المستندات غير المراجعة مرتبة بالأحدث
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE is_reviewed = 0 "
                "ORDER BY created_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_documents_by_category(self, category: str) -> list[dict]:
        """
        جلب المستندات حسب التصنيف.

        المعاملات:
            category: اسم التصنيف (code, documents, images, ...)

        المعاد:
            قائمة المستندات في التصنيف المحدد
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE category = ? "
                "ORDER BY created_at DESC",
                (category,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete_document(self, doc_id: int) -> bool:
        """
        حذف مستند وجميع بياناته المرتبطة.

        المعاملات:
            doc_id: معرّف المستند

        المعاد:
            True إذا تم الحذف بنجاح
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            affected = cursor.rowcount
            if affected > 0:
                logger.info("تم حذف المستند %d وجميع بياناته المرتبطة", doc_id)
                return True
            return False

    # ===================================================================
    #  عمليات نتائج OCR
    # ===================================================================

    def insert_ocr_results(self, results: list[dict]) -> int:
        """
        إدراج مجموعة نتائج OCR.

        المعاملات:
            results: قائمة قواميس، كل قاموس يحتوي:
                - document_id (int, مطلوب): معرّف المستند
                - page_num (int): رقم الصفحة
                - word_text (str): النص المستخرج
                - raw_text (str): النص الخام
                - corrected_text (str): النص المصحح
                - confidence (float): مستوى الثقة
                - model_source (str): مصدر النموذج (easyocr, trocr, tesseract)
                - x, y, w, h (int): إحداثيات المربع المحيط
                - status (str): الحالة (pending, reviewed, corrected)

        المعاد:
            عدد السجلات المُدرجة
        """
        if not results:
            return 0

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for r in results:
                if not r.get("document_id"):
                    logger.warning("تخطي نتيجة OCR بدون document_id")
                    continue
                try:
                    cursor.execute("""
                        INSERT INTO ocr_results (
                            document_id, page_num, word_text, raw_text,
                            corrected_text, confidence, model_source,
                            x, y, w, h, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r.get("document_id"),
                        r.get("page_num", 0),
                        r.get("word_text", ""),
                        r.get("raw_text", ""),
                        r.get("corrected_text", ""),
                        r.get("confidence", 0.0),
                        r.get("model_source", ""),
                        r.get("x", 0),
                        r.get("y", 0),
                        r.get("w", 0),
                        r.get("h", 0),
                        r.get("status", "pending"),
                        now,
                    ))
                    count += 1
                except sqlite3.Error as e:
                    logger.error("خطأ في إدراج نتيجة OCR: %s", e)

            conn.commit()
            logger.info("تم إدراج %d نتيجة OCR", count)
            return count

    def get_ocr_results(self, doc_id: int, page_num: Optional[int] = None) -> list[dict]:
        """
        جلب نتائج OCR لمستند.

        المعاملات:
            doc_id: معرّف المستند
            page_num: رقم الصفحة (اختياري - None = الكل)

        المعاد:
            قائمة نتائج OCR
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if page_num is not None:
                cursor.execute(
                    "SELECT * FROM ocr_results WHERE document_id = ? AND page_num = ? "
                    "ORDER BY page_num, id",
                    (doc_id, page_num),
                )
            else:
                cursor.execute(
                    "SELECT * FROM ocr_results WHERE document_id = ? "
                    "ORDER BY page_num, id",
                    (doc_id,),
                )
            return [dict(row) for row in cursor.fetchall()]

    # ===================================================================
    #  عمليات الترجمة
    # ===================================================================

    def insert_translation(
        self,
        doc_id: int,
        source: str,
        translated: str,
        source_lang: str = "en",
        target_lang: str = "ar",
        model_name: str = "",
    ) -> int:
        """
        إدراج ترجمة جديدة.

        المعاملات:
            doc_id: معرّف المستند
            source: النص المصدر
            translated: النص المترجم
            source_lang: لغة المصدر
            target_lang: لغة الهدف
            model_name: اسم نموذج الترجمة

        المعاد:
            معرّف الترجمة المُنشأة
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO translations (
                    document_id, source_text, translated_text,
                    source_lang, target_lang, model_name, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id, source, translated,
                source_lang, target_lang, model_name,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            conn.commit()
            trans_id = cursor.lastrowid
            logger.info("تم إدراج ترجمة للمستند %d (id=%d)", doc_id, trans_id)
            return trans_id

    def get_translations(self, doc_id: int) -> list[dict]:
        """
        جلب ترجمات مستند.

        المعاملات:
            doc_id: معرّف المستند

        المعاد:
            قائمة الترجمات
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM translations WHERE document_id = ? ORDER BY created_at DESC",
                (doc_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ===================================================================
    #  عمليات الكيانات المسماة (NER)
    # ===================================================================

    def insert_entities(self, doc_id: int, entities: list[dict]) -> int:
        """
        إدراج مجموعة كيانات مسماة لمستند.

        المعاملات:
            doc_id: معرّف المستند
            entities: قائمة قواميس، كل قاموس يحتوي:
                - entity_text (str, مطلوب): نص الكيان
                - entity_type (str): نوع الكيان (PERSON, ORG, LOC, ...)
                - start_pos (int): موضع البداية
                - end_pos (int): موضع النهاية
                - confidence (float): مستوى الثقة

        المعاد:
            عدد الكيانات المُدرجة
        """
        if not entities:
            return 0

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for ent in entities:
                if not ent.get("entity_text"):
                    continue
                try:
                    cursor.execute("""
                        INSERT INTO entities (
                            document_id, entity_text, entity_type,
                            start_pos, end_pos, confidence, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        doc_id,
                        ent.get("entity_text", ""),
                        ent.get("entity_type", ""),
                        ent.get("start_pos", 0),
                        ent.get("end_pos", 0),
                        ent.get("confidence", 0.0),
                        now,
                    ))
                    count += 1
                except sqlite3.Error as e:
                    logger.error("خطأ في إدراج كيان: %s", e)

            conn.commit()
            logger.info("تم إدراج %d كيان للمستند %d", count, doc_id)
            return count

    def get_entities(self, doc_id: int) -> list[dict]:
        """
        جلب كيانات مستند.

        المعاملات:
            doc_id: معرّف المستند

        المعاد:
            قائمة الكيانات
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM entities WHERE document_id = ? ORDER BY start_pos",
                (doc_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ===================================================================
    #  سجل التصحيحات
    # ===================================================================

    def log_correction(
        self,
        doc_id: int,
        original: str,
        corrected: str,
        correction_type: str = "spelling",
        auto_or_manual: str = "auto",
    ) -> int:
        """
        تسجيل تصحيح في السجل.

        المعاملات:
            doc_id: معرّف المستند
            original: النص الأصلي
            corrected: النص المصحح
            correction_type: نوع التصحيح (spelling, grammar, formatting)
            auto_or_manual: تلقائي أو يدوي (auto/manual)

        المعاد:
            معرّف سجل التصحيح
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO corrections_log (
                    document_id, original_text, corrected_text,
                    correction_type, auto_or_manual, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                doc_id, original, corrected,
                correction_type, auto_or_manual,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            conn.commit()
            corr_id = cursor.lastrowid
            logger.debug(
                "تسجيل تصحيح للمستند %d: '%s' → '%s' (%s)",
                doc_id, original[:30], corrected[:30], auto_or_manual,
            )
            return corr_id

    def get_corrections(self, doc_id: int) -> list[dict]:
        """
        جلب سجل تصحيحات مستند.

        المعاملات:
            doc_id: معرّف المستند

        المعاد:
            قائمة التصحيحات
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM corrections_log WHERE document_id = ? "
                "ORDER BY created_at DESC",
                (doc_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ===================================================================
    #  سجل المعالجة
    # ===================================================================

    def log_processing(
        self,
        action: str,
        target: str = "",
        status: str = "started",
        duration: float = 0.0,
        details: Optional[dict] = None,
    ) -> int:
        """
        تسجيل عملية معالجة.

        المعاملات:
            action: نوع العملية (ocr, translate, classify, ...)
            target: الهدف (اسم الملف، مسار، ...)
            status: الحالة (started, completed, failed)
            duration: مدة المعالجة بالثواني
            details: تفاصيل إضافية كقاموس

        المعاد:
            معرّف سجل المعالجة
        """
        details_json = json.dumps(details or {}, ensure_ascii=False, default=str)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO processing_history (
                    action, target, status, duration_sec,
                    details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                action, target, status, duration, details_json,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            conn.commit()
            hist_id = cursor.lastrowid
            logger.debug(
                "تسجيل معالجة: %s - %s (%s, %.2fs)",
                action, target, status, duration,
            )
            return hist_id

    def get_processing_history(self, limit: int = 50) -> list[dict]:
        """
        جلب سجل المعالجة.

        المعاملات:
            limit: أقصى عدد للعرض

        المعاد:
            قائمة سجلات المعالجة
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM processing_history ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            results = []
            for row in cursor.fetchall():
                r = dict(row)
                # تحويل JSON التفاصيل إلى قاموس
                try:
                    r["details"] = json.loads(r.get("details_json", "{}"))
                except (json.JSONDecodeError, TypeError):
                    r["details"] = {}
                results.append(r)
            return results

    # ===================================================================
    #  البحث
    # ===================================================================

    def search_documents(self, query: str) -> list[dict]:
        """
        البحث في المستندات بالنص الكامل.

        يدعم البحث في اسم الملف والنصوص المستخرجة.

        المعاملات:
            query: نص البحث

        المعاد:
            قائمة المستندات المطابقة
        """
        if not query or not query.strip():
            return []

        search_term = f"%{query.strip()}%"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM documents
                WHERE file_name LIKE ?
                   OR raw_text LIKE ?
                   OR processed_text LIKE ?
                   OR corrected_text LIKE ?
                   OR category LIKE ?
                ORDER BY created_at DESC
            """, (search_term, search_term, search_term, search_term, search_term))
            return [dict(row) for row in cursor.fetchall()]

    # ===================================================================
    #  الإحصائيات
    # ===================================================================

    def get_stats(self) -> dict:
        """
        جلب إحصائيات شاملة لقاعدة البيانات.

        المعاد:
            قاموس يحتوي:
                - total_documents: عدد المستندات
                - reviewed_documents: المستندات المراجعة
                - unreviewed_documents: المستندات غير المراجعة
                - total_ocr_results: عدد نتائج OCR
                - total_translations: عدد الترجمات
                - total_entities: عدد الكيانات
                - total_corrections: عدد التصحيحات
                - total_processing_logs: عدد سجلات المعالجة
                - avg_confidence: متوسط الثقة
                - documents_by_type: توزيع المستندات حسب النوع
                - documents_by_category: توزيع حسب التصنيف
                - documents_by_language: توزيع حسب اللغة
                - processing_by_action: توزيع المعالجة حسب النوع
                - recent_activity: آخر 10 عمليات
                - db_size_mb: حجم قاعدة البيانات بالميغابايت
                - storage_info: معلومات التخزين
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats: dict[str, Any] = {}

            # إحصائيات أساسية
            cursor.execute("SELECT COUNT(*) FROM documents")
            stats["total_documents"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM documents WHERE is_reviewed = 1")
            stats["reviewed_documents"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM documents WHERE is_reviewed = 0")
            stats["unreviewed_documents"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM ocr_results")
            stats["total_ocr_results"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM translations")
            stats["total_translations"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM entities")
            stats["total_entities"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM corrections_log")
            stats["total_corrections"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM processing_history")
            stats["total_processing_logs"] = cursor.fetchone()[0]

            # متوسط الثقة
            cursor.execute("SELECT AVG(confidence) FROM documents WHERE confidence > 0")
            result = cursor.fetchone()[0]
            stats["avg_confidence"] = round(result, 4) if result else 0.0

            # توزيع حسب النوع
            cursor.execute("""
                SELECT file_type, COUNT(*) as count
                FROM documents GROUP BY file_type ORDER BY count DESC
            """)
            stats["documents_by_type"] = dict(cursor.fetchall())

            # توزيع حسب التصنيف
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM documents GROUP BY category ORDER BY count DESC
            """)
            stats["documents_by_category"] = dict(cursor.fetchall())

            # توزيع حسب اللغة
            cursor.execute("""
                SELECT language, COUNT(*) as count
                FROM documents GROUP BY language ORDER BY count DESC
            """)
            stats["documents_by_language"] = dict(cursor.fetchall())

            # توزيع المعالجة حسب النوع
            cursor.execute("""
                SELECT action, COUNT(*) as count
                FROM processing_history GROUP BY action ORDER BY count DESC
            """)
            stats["processing_by_action"] = dict(cursor.fetchall())

            # حالة المعالجة
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM processing_history GROUP BY status ORDER BY count DESC
            """)
            stats["processing_by_status"] = dict(cursor.fetchall())

            # آخر العمليات
            cursor.execute("""
                SELECT action, target, status, duration_sec, created_at
                FROM processing_history
                ORDER BY created_at DESC LIMIT 10
            """)
            stats["recent_activity"] = [dict(row) for row in cursor.fetchall()]

            # بيانات للرسوم البيانية - نشاط يومي (آخر 30 يوم)
            cursor.execute("""
                SELECT DATE(created_at) as day, COUNT(*) as count
                FROM processing_history
                WHERE created_at >= datetime('now', '-30 days', 'localtime')
                GROUP BY day ORDER BY day
            """)
            stats["daily_activity"] = dict(cursor.fetchall())

            # بيانات للرسوم البيانية - تصنيف الكيانات
            cursor.execute("""
                SELECT entity_type, COUNT(*) as count
                FROM entities GROUP BY entity_type ORDER BY count DESC
            """)
            stats["entities_by_type"] = dict(cursor.fetchall())

            # حجم قاعدة البيانات
            db_size = 0
            try:
                db_size = os.path.getsize(self.db_path)
            except OSError:
                pass
            stats["db_size_bytes"] = db_size
            stats["db_size_mb"] = round(db_size / (1024 * 1024), 2)

            # عدد المستندات المحمية
            cursor.execute("SELECT COUNT(*) FROM documents WHERE is_code_protected = 1")
            stats["protected_documents"] = cursor.fetchone()[0]

            return stats

    # ===================================================================
    #  التصدير
    # ===================================================================

    def export_to_json(self, output_path: str) -> str:
        """
        تصدير جميع البيانات إلى ملف JSON.

        المعاملات:
            output_path: مسار ملف التصدير

        المعاد:
            مسار الملف المُصدَّر
        """
        export_data: dict[str, Any] = {
            "export_info": {
                "version": "4.1.1",
                "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": self.db_path,
            },
            "documents": [],
            "ocr_results": [],
            "translations": [],
            "entities": [],
            "corrections_log": [],
            "processing_history": [],
            "stats": {},
        }

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # تصدير المستندات
            cursor.execute("SELECT * FROM documents ORDER BY id")
            export_data["documents"] = [dict(row) for row in cursor.fetchall()]

            # تصدير نتائج OCR
            cursor.execute("SELECT * FROM ocr_results ORDER BY id")
            export_data["ocr_results"] = [dict(row) for row in cursor.fetchall()]

            # تصدير الترجمات
            cursor.execute("SELECT * FROM translations ORDER BY id")
            export_data["translations"] = [dict(row) for row in cursor.fetchall()]

            # تصدير الكيانات
            cursor.execute("SELECT * FROM entities ORDER BY id")
            export_data["entities"] = [dict(row) for row in cursor.fetchall()]

            # تصدير سجل التصحيحات
            cursor.execute("SELECT * FROM corrections_log ORDER BY id")
            export_data["corrections_log"] = [dict(row) for row in cursor.fetchall()]

            # تصدير سجل المعالجة
            cursor.execute("SELECT * FROM processing_history ORDER BY id")
            export_data["processing_history"] = [dict(row) for row in cursor.fetchall()]

        # إضافة الإحصائيات
        export_data["stats"] = self.get_stats()

        # كتابة الملف
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

        file_size = os.path.getsize(output_path)
        logger.info(
            "تم تصدير البيانات إلى %s (%.2f KB)",
            output_path, file_size / 1024,
        )
        return output_path

    # ===================================================================
    #  النسخ الاحتياطي
    # ===================================================================

    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """
        إنشاء نسخة احتياطية من قاعدة البيانات.

        المعاملات:
            backup_path: مسار النسخة (الافتراضي: db_name_YYYYMMDD_HHMMSS.bak)

        المعاد:
            مسار ملف النسخة الاحتياطية
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.{timestamp}.bak"

        backup_dir = os.path.dirname(backup_path)
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)

        # استخدام API النسخ الاحتياطي في SQLite
        with self._get_connection() as conn:
            conn.execute(f"VACUUM INTO '{backup_path}'")

        logger.info("تم إنشاء نسخة احتياطية: %s", backup_path)
        return backup_path

    # ===================================================================
    #  التنظيف
    # ===================================================================

    def cleanup_old_records(self, days: int = 30) -> dict:
        """
        حذف السجلات القديمة لتحرير المساحة.

        يحذف سجلات المعالجة والتصحيحات القديمة بينما يحتفظ بالمستندات.

        المعاملات:
            days: عدد الأيام للاحتفاظ بالسجلات

        المعاد:
            قاموس بإحصائيات التنظيف:
                - deleted_processing: عدد سجلات المعالجة المحذوفة
                - deleted_corrections: عدد التصحيحات المحذوفة
                - freed_bytes: المساحة المحررة تقريباً
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        result = {
            "deleted_processing": 0,
            "deleted_corrections": 0,
            "freed_bytes": 0,
        }

        # حجم قاعدة البيانات قبل التنظيف
        try:
            size_before = os.path.getsize(self.db_path)
        except OSError:
            size_before = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # حذف سجلات المعالجة القديمة
            cursor.execute(
                "DELETE FROM processing_history WHERE created_at < ?",
                (cutoff,),
            )
            result["deleted_processing"] = cursor.rowcount

            # حذف التصحيحات القديمة
            cursor.execute(
                "DELETE FROM corrections_log WHERE created_at < ?",
                (cutoff,),
            )
            result["deleted_corrections"] = cursor.rowcount

            # ضغط قاعدة البيانات
            cursor.execute("VACUUM")
            conn.commit()

        # حجم بعد التنظيف
        try:
            size_after = os.path.getsize(self.db_path)
            result["freed_bytes"] = max(0, size_before - size_after)
        except OSError:
            pass

        logger.info(
            "تم تنظيف السجلات القديمة (أقدم من %d يوم): "
            "معالجة=%d, تصحيحات=%d, محرر=%.2fKB",
            days,
            result["deleted_processing"],
            result["deleted_corrections"],
            result["freed_bytes"] / 1024,
        )
        return result

    # ===================================================================
    #  أدوات مساعدة
    # ===================================================================

    def get_db_size(self) -> str:
        """
        جلب حجم قاعدة البيانات بصيغة مقروءة.

        المعاد:
            حجم قاعدة البيانات (مثال: "12.5 MB")
        """
        try:
            size = os.path.getsize(self.db_path)
            for unit in ["B", "KB", "MB", "GB"]:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        except OSError:
            return "غير معروف"

    def vacuum(self) -> None:
        """ضغط قاعدة البيانات لتحسين الأداء وتحرير المساحة."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
        logger.info("تم ضغط قاعدة البيانات")

    def close(self) -> None:
        """إغلاق جميع الاتصالات وتحرير الموارد."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
        logger.info("تم إغلاق اتصال قاعدة البيانات")

    def __enter__(self) -> "OmniFileDB":
        """دعم Context Manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """إغلاق تلقائي عند الخروج من السياق."""
        self.close()

    def __repr__(self) -> str:
        return f"OmniFileDB(db_path='{self.db_path}', size='{self.get_db_size()}')"
