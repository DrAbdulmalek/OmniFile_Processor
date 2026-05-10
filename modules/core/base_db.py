"""
modules/core/base_db.py
════════════════════════
قاعدة SQLite مشتركة — Shared SQLite Base Class
===============================================
تُحل مشكلة تكرار إعدادات SQLite في 9+ ملفات.
كل قاعدة بيانات في المشروع ترث من هذه الكلاس.

الميزات الموحّدة:
  ✅ WAL mode (أداء أفضل مع عمليات القراءة المتزامنة)
  ✅ foreign_keys=ON + busy_timeout=5000
  ✅ row_factory=sqlite3.Row (الوصول بالاسم بدل الرقم)
  ✅ Context manager آمن (commit/rollback تلقائي)
  ✅ execute_safe() مع retry عند SQLITE_BUSY
  ✅ migrate() للترقية التدريجي للـ schema

الاستخدام:
    class MyDB(BaseDB):
        def _create_schema(self, conn):
            conn.execute(\"CREATE TABLE IF NOT EXISTS ...\")

        def insert_item(self, data):
            with self.connection() as conn:
                conn.execute(\"INSERT INTO ...\", data)

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

# إعدادات موحّدة لكل قواعد البيانات
_PRAGMAS = [
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA cache_size=-8000",   # 8MB cache
    "PRAGMA temp_store=MEMORY",
]

_MAX_RETRIES = 3
_RETRY_DELAY = 0.1   # ثانية


class BaseDB:
    """
    كلاس أساسية لكل قواعد SQLite في OmniFile.

    الاستخدام:
        class WordDB(BaseDB):
            def _create_schema(self, conn):
                conn.execute(\"\"\"
                    CREATE TABLE IF NOT EXISTS words (
                        id   INTEGER PRIMARY KEY,
                        word TEXT NOT NULL
                    )
                \"\"\")
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    # ── التهيئة ─────────────────────────────────────────────────────

    def _init(self) -> None:
        """تهيئة قاعدة البيانات وإنشاء الـ schema."""
        with self.connection() as conn:
            self._create_schema(conn)
        logger.debug("%s: initialized at %s", self.__class__.__name__, self.db_path)

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """
        أنشئ الجداول والفهارس هنا في الكلاسات الفرعية.
        يُستدعى تلقائياً عند التهيئة.
        """
        pass   # override in subclass

    # ── Context Manager ──────────────────────────────────────────────

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        context manager آمن: commit عند النجاح، rollback عند الفشل.

        مثال:
            with db.connection() as conn:
                conn.execute(\"INSERT ...\")
        """
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            for pragma in _PRAGMAS:
                conn.execute(pragma)
            yield conn
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    # ── دوال مساعدة ─────────────────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> list:
        """تنفيذ SQL وإرجاع كل الصفوف كـ list[dict]."""
        with self.connection() as conn:
            cur = conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def execute_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """تنفيذ SQL وإرجاع صف واحد أو None."""
        with self.connection() as conn:
            cur = conn.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """
        تنفيذ INSERT/UPDATE/DELETE مع retry عند SQLITE_BUSY.
        Returns: lastrowid
        """
        for attempt in range(_MAX_RETRIES):
            try:
                with self.connection() as conn:
                    cur = conn.execute(sql, params)
                    return cur.lastrowid or 0
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAY * (attempt + 1))
                    logger.warning("%s: DB locked, retry %d", self.__class__.__name__, attempt+1)
                else:
                    raise
        return 0

    def executemany_write(self, sql: str, params_list: list) -> int:
        """تنفيذ INSERT متعدد في transaction واحدة. Returns: عدد الصفوف."""
        if not params_list:
            return 0
        with self.connection() as conn:
            conn.executemany(sql, params_list)
            return len(params_list)

    def table_exists(self, table: str) -> bool:
        """تحقق من وجود جدول."""
        row = self.execute_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        return row is not None

    def count(self, table: str, where: str = "", params: tuple = ()) -> int:
        """عدّ صفوف جدول مع شرط اختياري."""
        sql = f"SELECT COUNT(*) AS n FROM {table}"
        if where:
            sql += f" WHERE {where}"
        row = self.execute_one(sql, params)
        return row["n"] if row else 0

    def vacuum(self) -> None:
        """ضغط قاعدة البيانات (تنفيذ خارج transaction)."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("VACUUM")
            conn.close()
            logger.info("%s: VACUUM done", self.__class__.__name__)
        except Exception as e:
            logger.warning("%s: VACUUM failed: %s", self.__class__.__name__, e)
            conn.close()

    def migrate(self, version: int, sql: str) -> bool:
        """
        ترقية schema بأمان (idempotent).

        مثال:
            db.migrate(2, \"ALTER TABLE words ADD COLUMN lang TEXT DEFAULT 'ar'\")
        """
        # جدول تتبع الإصدارات
        with self.connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    version    INTEGER PRIMARY KEY,
                    applied_at TEXT DEFAULT (datetime('now'))
                )
            """)
            exists = conn.execute(
                "SELECT 1 FROM _migrations WHERE version=?", (version,)
            ).fetchone()
            if exists:
                return False   # already applied
            try:
                conn.execute(sql)
                conn.execute("INSERT INTO _migrations(version) VALUES(?)", (version,))
                logger.info("%s: migration v%d applied", self.__class__.__name__, version)
                return True
            except Exception as e:
                logger.error("%s: migration v%d failed: %s", self.__class__.__name__, version, e)
                raise

    def stats(self) -> dict:
        """إحصائيات مختصرة لقاعدة البيانات."""
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        tables = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '_migration%'"
        )
        counts = {}
        for t in tables:
            name = t["name"]
            counts[name] = self.count(name)
        return {
            "db_path":    str(self.db_path),
            "size_bytes": size_bytes,
            "size_kb":    round(size_bytes / 1024, 1),
            "tables":     counts,
        }
