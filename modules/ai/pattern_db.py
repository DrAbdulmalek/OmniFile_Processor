"""
OmniFile AI Processor — Pattern Database
==========================================
Source: arabic-ocr-pro/ai/pattern_db.py

Provides a SQLite-based storage for:
- User corrections (original text → corrected text)
- Pattern images (cropped word images + labels)
- Usage statistics
- Training status tracking

The database enables the system to learn from user corrections
and improve OCR accuracy over time through pattern matching.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PatternDatabase:
    """SQLite database for storing OCR correction patterns.

    Manages persistent storage of user corrections and word pattern
    images, enabling the system to learn and improve over time.

    Attributes:
        db_path: Path to the SQLite database file.
        _connection: Active SQLite connection.
    """

    def __init__(self, db_path: str | Path = "data/corrections.db") -> None:
        """Initialize the pattern database.

        Creates the database file and tables if they don't exist.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection: Optional[sqlite3.Connection] = None
        self._initialize_database()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection.

        Returns:
            Active SQLite connection.
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent access
            self._connection.execute("PRAGMA journal_mode=WAL")
        return self._connection

    def _initialize_database(self) -> None:
        """Create database tables if they don't exist.

        Creates:
        - corrections: Stores original → corrected text mappings
        - patterns: Stores word pattern images (BLOB) with labels
        - statistics: Tracks usage statistics
        - training_status: Tracks model training progress
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                engine TEXT DEFAULT '',
                confidence REAL DEFAULT 0.0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                use_count INTEGER DEFAULT 0,
                last_used_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_corrections_original
                ON corrections(original_text);

            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                image_data BLOB,
                image_width INTEGER,
                image_height INTEGER,
                ocr_text TEXT,
                confidence REAL DEFAULT 0.0,
                source_engine TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                use_count INTEGER DEFAULT 0,
                last_used_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_patterns_label
                ON patterns(label);

            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_key TEXT NOT NULL UNIQUE,
                stat_value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS training_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                total_samples INTEGER DEFAULT 0,
                trained_samples INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0.0,
                last_trained_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)

        conn.commit()
        logger.debug(f"Database initialized: {self.db_path}")

    # ------------------------------------------------------------------
    # Corrections CRUD
    # ------------------------------------------------------------------

    def add_correction(
        self,
        original_text: str,
        corrected_text: str,
        engine: str = "",
        confidence: float = 0.0,
    ) -> int:
        """Add a new correction to the database.

        If the same correction already exists, increments its use count
        instead of creating a duplicate.

        Args:
            original_text: Original (incorrect) OCR text.
            corrected_text: User-provided corrected text.
            engine: OCR engine that produced the original text.
            confidence: Confidence score of the original OCR result.

        Returns:
            Row ID of the correction record.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if correction already exists
        cursor.execute(
            "SELECT id, use_count FROM corrections "
            "WHERE original_text = ? AND corrected_text = ?",
            (original_text, corrected_text),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE corrections SET use_count = ?, "
                "last_used_at = datetime('now') WHERE id = ?",
                (existing["use_count"] + 1, existing["id"]),
            )
            conn.commit()
            return existing["id"]

        cursor.execute(
            """INSERT INTO corrections (original_text, corrected_text, engine, confidence)
               VALUES (?, ?, ?, ?)""",
            (original_text, corrected_text, engine, confidence),
        )
        conn.commit()
        row_id = cursor.lastrowid

        # Update statistics
        self._increment_stat("total_corrections")

        logger.debug(
            f"Added correction: '{original_text}' -> '{corrected_text}'"
        )
        return row_id

    def get_corrections(
        self,
        limit: int = 1000,
        min_use_count: int = 0,
    ) -> list[dict]:
        """Get all stored corrections.

        Args:
            limit: Maximum number of corrections to return.
            min_use_count: Minimum use count filter.

        Returns:
            List of correction dictionaries.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT id, original_text, corrected_text, engine, confidence,
                      use_count, created_at
               FROM corrections
               WHERE use_count >= ?
               ORDER BY use_count DESC, created_at DESC
               LIMIT ?""",
            (min_use_count, limit),
        )

        return [
            {
                "id": row["id"],
                "original_text": row["original_text"],
                "corrected_text": row["corrected_text"],
                "engine": row["engine"],
                "confidence": row["confidence"],
                "use_count": row["use_count"],
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]

    def find_correction(self, original_text: str) -> Optional[dict]:
        """Look up a correction for specific original text.

        Args:
            original_text: The text to look up.

        Returns:
            Correction dictionary if found, None otherwise.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT id, original_text, corrected_text, engine, confidence,
                      use_count, created_at
               FROM corrections
               WHERE original_text = ?
               ORDER BY use_count DESC
               LIMIT 1""",
            (original_text,),
        )

        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "original_text": row["original_text"],
                "corrected_text": row["corrected_text"],
                "engine": row["engine"],
                "confidence": row["confidence"],
                "use_count": row["use_count"],
                "created_at": row["created_at"],
            }
        return None

    def delete_correction(self, correction_id: int) -> bool:
        """Delete a correction record.

        Args:
            correction_id: ID of the correction to delete.

        Returns:
            True if deleted, False if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM corrections WHERE id = ?", (correction_id,)
        )
        conn.commit()
        deleted = cursor.rowcount > 0

        if deleted:
            logger.debug(f"Deleted correction id={correction_id}")

        return deleted

    # ------------------------------------------------------------------
    # Patterns CRUD
    # ------------------------------------------------------------------

    def add_pattern(
        self,
        label: str,
        image_data: bytes,
        image_width: int,
        image_height: int,
        ocr_text: str = "",
        confidence: float = 0.0,
        source_engine: str = "",
    ) -> int:
        """Add a new word pattern image to the database.

        Stores a cropped word image along with its label (correct text)
        for future pattern matching.

        Args:
            label: Correct text label for the pattern.
            image_data: Raw image bytes (PNG or JPEG encoded).
            image_width: Width of the pattern image.
            image_height: Height of the pattern image.
            ocr_text: OCR result that produced this pattern.
            confidence: Confidence score of the OCR result.
            source_engine: OCR engine that produced the result.

        Returns:
            Row ID of the pattern record.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO patterns (label, image_data, image_width, image_height,
                                      ocr_text, confidence, source_engine)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (label, image_data, image_width, image_height,
             ocr_text, confidence, source_engine),
        )
        conn.commit()
        row_id = cursor.lastrowid

        self._increment_stat("total_patterns")
        logger.debug(
            f"Added pattern: label='{label}', size={len(image_data)} bytes"
        )
        return row_id

    def get_patterns(
        self,
        label: Optional[str] = None,
        limit: int = 500,
    ) -> list[dict]:
        """Get stored pattern images.

        Args:
            label: Optional label filter.
            limit: Maximum number of patterns to return.

        Returns:
            List of pattern dictionaries with image data.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if label:
            cursor.execute(
                """SELECT id, label, image_data, image_width, image_height,
                          ocr_text, confidence, source_engine, use_count
                   FROM patterns
                   WHERE label = ?
                   ORDER BY use_count DESC
                   LIMIT ?""",
                (label, limit),
            )
        else:
            cursor.execute(
                """SELECT id, label, image_data, image_width, image_height,
                          ocr_text, confidence, source_engine, use_count
                   FROM patterns
                   ORDER BY use_count DESC
                   LIMIT ?""",
                (limit,),
            )

        return [
            {
                "id": row["id"],
                "label": row["label"],
                "image_data": row["image_data"],
                "image_width": row["image_width"],
                "image_height": row["image_height"],
                "ocr_text": row["ocr_text"],
                "confidence": row["confidence"],
                "source_engine": row["source_engine"],
                "use_count": row["use_count"],
            }
            for row in cursor.fetchall()
        ]

    def get_unique_labels(self) -> list[str]:
        """Get all unique pattern labels.

        Returns:
            Sorted list of unique label strings.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT label FROM patterns ORDER BY label")
        return [row["label"] for row in cursor.fetchall()]

    def increment_pattern_use(self, pattern_id: int) -> None:
        """Increment the use count for a pattern.

        Args:
            pattern_id: ID of the pattern to update.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE patterns SET use_count = use_count + 1, "
            "last_used_at = datetime('now') WHERE id = ?",
            (pattern_id,),
        )
        conn.commit()

    def delete_pattern(self, pattern_id: int) -> bool:
        """Delete a pattern record.

        Args:
            pattern_id: ID of the pattern to delete.

        Returns:
            True if deleted, False if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
        conn.commit()
        deleted = cursor.rowcount > 0

        if deleted:
            logger.debug(f"Deleted pattern id={pattern_id}")

        return deleted

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def _increment_stat(self, key: str, increment: int = 1) -> None:
        """Increment a statistics counter.

        Args:
            key: Statistics key name.
            increment: Amount to increment by.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO statistics (stat_key, stat_value)
               VALUES (?, ?)
               ON CONFLICT(stat_key) DO UPDATE SET
                   stat_value = CAST(stat_value AS INTEGER) + ?,
                   updated_at = datetime('now')""",
            (key, str(increment), increment),
        )
        conn.commit()

    def get_stat(self, key: str) -> int:
        """Get a statistics value.

        Args:
            key: Statistics key name.

        Returns:
            Integer value, or 0 if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT stat_value FROM statistics WHERE stat_key = ?", (key,)
        )
        row = cursor.fetchone()

        if row:
            try:
                return int(row["stat_value"])
            except (ValueError, TypeError):
                return 0
        return 0

    def get_all_stats(self) -> dict[str, int]:
        """Get all statistics.

        Returns:
            Dictionary of all statistic key-value pairs.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT stat_key, stat_value FROM statistics")
        return {
            row["stat_key"]: int(row["stat_value"])
            for row in cursor.fetchall()
        }

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def cleanup(self, max_age_days: int = 90) -> int:
        """Remove old records that haven't been used recently.

        Args:
            max_age_days: Maximum age in days for unused records.

        Returns:
            Number of records deleted.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff = f"datetime('now', '-{max_age_days} days')"

        cursor.execute(
            f"DELETE FROM corrections WHERE last_used_at IS NULL "
            f"AND created_at < {cutoff} AND use_count = 0"
        )
        deleted_corrections = cursor.rowcount

        cursor.execute(
            f"DELETE FROM patterns WHERE last_used_at IS NULL "
            f"AND created_at < {cutoff} AND use_count = 0"
        )
        deleted_patterns = cursor.rowcount

        conn.commit()
        total = deleted_corrections + deleted_patterns

        if total > 0:
            logger.info(
                f"Cleanup: deleted {deleted_corrections} corrections "
                f"and {deleted_patterns} patterns"
            )

        return total

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.debug("Database connection closed")

    def __enter__(self) -> "PatternDatabase":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
