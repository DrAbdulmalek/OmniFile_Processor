"""
HandwrittenDB — إدارة قاعدة بيانات الخط اليدوي v4
=====================================================
v4.0: مُرحَّل إلى BaseDB (WAL + retry + context manager موحَّد)
مخطط v3 يبقى متوافقاً تماماً مع الكود القديم.
"""

import sqlite3
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime

from modules.core.base_db import BaseDB

logger = logging.getLogger("modules.core.handwriting_db")

DB_SCHEMA_VERSION = 3


class HandwritingDB(BaseDB):
    """
    مدير قاعدة بيانات الخط اليدوي — يرث من BaseDB (v4.0).
    يدعم: run_id, raw_text, created_at/updated_at, processing_runs, review_events.
    متوافق تماماً مع الكود القديم (v3 schema).
    """

    SCHEMA_V3 = '''
        CREATE TABLE IF NOT EXISTS handwriting_data (
            image_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            image_data    BLOB    NOT NULL,
            predicted_text TEXT   DEFAULT '',
            raw_text      TEXT    DEFAULT '',
            status        TEXT    DEFAULT 'unverified',
            confidence    REAL    DEFAULT 0.0,
            model_source  TEXT    DEFAULT 'none',
            x INTEGER DEFAULT 0, y INTEGER DEFAULT 0,
            w INTEGER DEFAULT 0, h INTEGER DEFAULT 0,
            page_num      INTEGER DEFAULT 0,
            run_id        TEXT    DEFAULT '',
            created_at    TEXT    DEFAULT '',
            updated_at    TEXT    DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS processing_runs (
            run_id      TEXT PRIMARY KEY,
            started_at  TEXT, ended_at TEXT,
            input_path  TEXT,
            pages_processed INTEGER DEFAULT 0,
            words_processed INTEGER DEFAULT 0,
            avg_confidence  REAL    DEFAULT 0.0,
            status      TEXT DEFAULT 'running'
        );
        CREATE TABLE IF NOT EXISTS review_events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT,
            image_id      INTEGER,
            original_text TEXT,
            corrected_text TEXT,
            action        TEXT,
            reviewer      TEXT DEFAULT 'user'
        );
        CREATE INDEX IF NOT EXISTS idx_status  ON handwriting_data(status);
        CREATE INDEX IF NOT EXISTS idx_page    ON handwriting_data(page_num);
        CREATE INDEX IF NOT EXISTS idx_run     ON handwriting_data(run_id);
        CREATE INDEX IF NOT EXISTS idx_conf    ON handwriting_data(confidence);
    '''

    def __init__(self, db_path: str):
        super().__init__(db_path)   # BaseDB: WAL + PRAGMA + mkdir
        logger.info("HandwritingDB جاهزة: %s", db_path)

    def _create_schema(self, conn) -> None:
        """يُستدعى من BaseDB.__init__()"""
        conn.executescript(self.SCHEMA_V3)
        self._migrate(conn)

    def _migrate(self, conn) -> None:
        """ترقية مخطط v1/v2 → v3"""
        cur = conn.execute("PRAGMA table_info(handwriting_data)")
        existing = {r[1] for r in cur.fetchall()}

        # أعمدة v2 (للمخططات القديمة جداً)
        v2_cols = {
            "confidence": "REAL DEFAULT 0.0",
            "model_source": "TEXT DEFAULT 'none'",
            "x": "INTEGER DEFAULT 0",
            "y": "INTEGER DEFAULT 0",
            "w": "INTEGER DEFAULT 0",
            "h": "INTEGER DEFAULT 0",
            "page_num": "INTEGER DEFAULT 0",
        }

        # أعمدة v3
        v3_cols = {
            "raw_text": "TEXT DEFAULT ''",
            "run_id": "TEXT DEFAULT ''",
            "created_at": "TEXT DEFAULT ''",
            "updated_at": "TEXT DEFAULT ''",
        }

        migrated = False
        for col, typedef in {**v2_cols, **v3_cols}.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE handwriting_data ADD COLUMN {col} {typedef}")
                migrated = True

        # توحيد قيم status القديمة
        conn.execute("UPDATE handwriting_data SET status='verified'   WHERE status='yes'")
        conn.execute("UPDATE handwriting_data SET status='unverified' WHERE status='no'")

        if migrated:
            conn.commit()
            logger.info("تم ترقية مخطط قاعدة البيانات إلى v3")

    # --- Insert ---
    def insert_word(
        self,
        image_data: bytes,
        predicted_text: str,
        raw_text: str = "",
        status: str = "unverified",
        confidence: float = 0.0,
        model_source: str = "none",
        x: int = 0, y: int = 0, w: int = 0, h: int = 0,
        page_num: int = 0,
        run_id: str = "",
    ) -> int:
        """إضافة كلمة جديدة (مخطط v3 مع raw_text, run_id, timestamps)"""
        ts = datetime.now().isoformat()
        with self.connection() as conn:
            cur = conn.execute(
                '''INSERT INTO handwriting_data
                   (image_data, predicted_text, raw_text, status, confidence,
                    model_source, x, y, w, h, page_num, run_id, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (image_data, predicted_text, raw_text, status, confidence,
                 model_source, x, y, w, h, page_num, run_id, ts, ts),
            )
            conn.commit()
            return cur.lastrowid

    # --- Update ---
    def update_word(
        self,
        image_id: int,
        predicted_text: Optional[str] = None,
        status: Optional[str] = None,
    ) -> None:
        """تحديث نص أو حالة كلمة مع updated_at تلقائي"""
        sets, vals = [], []
        if predicted_text is not None:
            sets.append("predicted_text=?")
            vals.append(predicted_text)
        if status is not None:
            sets.append("status=?")
            vals.append(status)
        sets.append("updated_at=?")
        vals.append(datetime.now().isoformat())
        vals.append(image_id)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE handwriting_data SET {','.join(sets)} WHERE image_id=?",
                vals,
            )
            conn.commit()

    # --- Delete ---
    def delete_word(self, image_id: int) -> bool:
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM handwriting_data WHERE image_id=?", (image_id,)
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_pages(self, page_start: int, page_end: int) -> int:
        """حذف بيانات صفحات محددة لتجنب التكرار عند إعادة المعالجة"""
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM handwriting_data WHERE page_num BETWEEN ? AND ?",
                (page_start, page_end),
            )
            conn.commit()
            deleted = cur.rowcount
            if deleted > 0:
                logger.info(f"تم حذف {deleted} سجل من الصفحات {page_start}-{page_end}")
            return deleted

    # --- Queries ---
    def _rows(self, sql: str, params=()) -> list[dict]:
        with self.connection() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def get_word(self, image_id: int) -> Optional[dict]:
        rows = self._rows("SELECT * FROM handwriting_data WHERE image_id=?", (image_id,))
        return rows[0] if rows else None

    def get_all(self) -> list[dict]:
        return self._rows("SELECT * FROM handwriting_data ORDER BY page_num, y, x")

    def get_unverified(self, order_by_confidence: bool = True) -> list[dict]:
        order = "ORDER BY confidence ASC" if order_by_confidence else "ORDER BY image_id"
        return self._rows(
            f"SELECT * FROM handwriting_data WHERE status='unverified' {order}"
        )

    def get_verified(self) -> list[dict]:
        return self._rows(
            "SELECT * FROM handwriting_data "
            "WHERE status IN ('verified','sentence_corrected') ORDER BY image_id"
        )

    def get_low_confidence(self, threshold: float = 0.5, limit: int = 100) -> list[dict]:
        return self._rows(
            "SELECT * FROM handwriting_data WHERE confidence<? ORDER BY confidence ASC LIMIT ?",
            (threshold, limit),
        )

    def count_by_status(self) -> dict:
        rows = self._rows("SELECT status, COUNT(*) as cnt FROM handwriting_data GROUP BY status")
        return {r["status"]: r["cnt"] for r in rows}

    def get_count(self) -> int:
        with self.connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM handwriting_data").fetchone()[0]

    def get_verified_count(self) -> int:
        with self.connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM handwriting_data "
                "WHERE status IN ('verified','sentence_corrected')"
            ).fetchone()[0]

    def get_unverified_count(self) -> int:
        with self.connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM handwriting_data WHERE status='unverified'"
            ).fetchone()[0]

    def clear_all(self) -> int:
        with self.connection() as conn:
            cur = conn.execute("DELETE FROM handwriting_data")
            conn.commit()
            return cur.rowcount

    # --- Run tracking ---
    def insert_run(self, run_id: str, input_path: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO processing_runs "
                "(run_id, started_at, input_path, status) VALUES (?,?,?,?)",
                (run_id, datetime.now().isoformat(), str(input_path), "running"),
            )
            conn.commit()

    def finish_run(
        self, run_id: str, pages: int, words: int, avg_conf: float
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE processing_runs SET ended_at=?, pages_processed=?, "
                "words_processed=?, avg_confidence=?, status=? WHERE run_id=?",
                (datetime.now().isoformat(), pages, words, avg_conf, "completed", run_id),
            )
            conn.commit()

    # --- Review events ---
    def log_review(
        self, image_id: int, original: str, corrected: str, action: str
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO review_events "
                "(timestamp, image_id, original_text, corrected_text, action) "
                "VALUES (?,?,?,?,?)",
                (datetime.now().isoformat(), image_id, original, corrected, action),
            )
            conn.commit()

    def get_last_review_event(self) -> dict | None:
        """جلب آخر حدث مراجعة للتراجع."""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cur = conn.execute(
                "SELECT * FROM review_events ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
            return None
        except Exception:
            return None

    def delete_review_event(self, event_id: int) -> None:
        """حذف حدث مراجعة."""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("DELETE FROM review_events WHERE id = ?", (event_id,))
            conn.commit()
        except Exception:
            pass
