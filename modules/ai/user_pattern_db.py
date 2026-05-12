#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/ai/user_pattern_db.py
==================================

User Pattern Database for handwriting recognition learning.

Stores word image patterns with their corrected texts, enabling:
- Automatic correction suggestions for repeated patterns
- Training data collection for fine-tuning
- Writer-specific pattern management (multiple handwriting styles)
- Visual similarity-based pattern lookup

Uses SQLite for lightweight, serverless operation.
Images are stored as compressed blobs with perceptual hashing.

Usage:
    db = UserPatternDB()
    db.save_correction(image, "predicted", "corrected", confidence=0.65)
    suggestion = db.suggest_correction(image, "ar")
    samples = db.get_training_samples(min_usage=3)
"""

import hashlib
import json
import logging
import os
from modules.core.base_db import BaseDB
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class UserPatternDB(BaseDB):
    """
    SQLite-based pattern database for learning user handwriting patterns.

    Each correction creates a pattern: (image_hash, image_blob, predicted,
    corrected, confidence, language, writer_id, context, usage_count).

    When the same image pattern appears again, the system auto-suggests
    the previously corrected text, improving accuracy over time.

    Features:
    - Robust perceptual hashing (resistant to noise/contrast changes)
    - Compressed image storage (JPEG + zlib)
    - Writer-specific pattern isolation
    - Usage count tracking for confidence scoring
    - Training sample export for LoRA fine-tuning
    - Pattern statistics per writer

    Usage:
        db = UserPatternDB(db_path="data/user_patterns.db")

        # Save a correction
        db.save_correction(
            image=word_image,
            predicted="فم",
            corrected="في",
            confidence=0.65,
            language="ar",
            writer_id="default",
        )

        # Auto-suggest when same pattern appears
        suggestion = db.suggest_correction(
            image=new_word_image,
            language="ar",
            writer_id="default"
        )
        # => {'suggested_text': 'في', 'confidence': 0.85, 'source': 'exact', 'times_used': 5}

        # Get training samples for fine-tuning
        samples = db.get_training_samples(min_usage=3, limit=500)

        # Get statistics
        stats = db.get_writer_stats(writer_id="default")
    """

    def __init__(self, db_path: str = "data/user_patterns.db"):
        """
        Args:
            db_path: Path to SQLite database file
        """
        super().__init__(db_path)
        self._compression_level = 6  # zlib level

    def _create_schema(self, conn):
        """Initialize database tables and indexes."""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_hash TEXT UNIQUE NOT NULL,
                image_blob BLOB NOT NULL,
                predicted_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'ar',
                confidence REAL DEFAULT 0.0,
                writer_id TEXT NOT NULL DEFAULT 'default',
                context_hint TEXT,
                usage_count INTEGER DEFAULT 1,
                last_used TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS learning_stats (
                id INTEGER PRIMARY KEY,
                writer_id TEXT UNIQUE NOT NULL,
                language TEXT NOT NULL DEFAULT 'ar',
                total_corrections INTEGER DEFAULT 0,
                patterns_learned INTEGER DEFAULT 0,
                total_images INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0.0,
                improvement_rate REAL DEFAULT 0.0,
                last_trained TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_pattern_lookup
            ON patterns(image_hash, language, writer_id);

            CREATE INDEX IF NOT EXISTS idx_writer_language
            ON patterns(writer_id, language);

            CREATE INDEX IF NOT EXISTS idx_usage_count
            ON patterns(usage_count DESC, last_used DESC);
        """)

    def save_correction(
        self,
        image: np.ndarray,
        predicted: str,
        corrected: str,
        confidence: float = 0.0,
        language: str = "ar",
        writer_id: str = "default",
        context_hint: Optional[str] = None,
    ) -> bool:
        """
        Save a user correction as a learnable pattern.

        Args:
            image: Word image as numpy array
            predicted: What the OCR predicted
            corrected: What the user corrected it to
            confidence: OCR confidence (0-1)
            language: 'ar', 'en', 'mixed'
            writer_id: Identifier for different handwriting styles
            context_hint: Optional context ('drug', 'diagnosis', etc.)

        Returns:
            True if saved successfully
        """
        img_hash = self._robust_image_hash(image)
        img_blob = self._compress_image(image)

        now = datetime.utcnow().isoformat()

        try:
            with self.connection() as conn:
                conn.execute("""
                    INSERT INTO patterns
                    (image_hash, image_blob, predicted_text, corrected_text,
                     language, confidence, writer_id, context_hint,
                     usage_count, last_used, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                    ON CONFLICT(image_hash) DO UPDATE SET
                        corrected_text = excluded.corrected_text,
                        predicted_text = excluded.predicted_text,
                        confidence = excluded.confidence,
                        usage_count = usage_count + 1,
                        last_used = excluded.last_used,
                        updated_at = excluded.updated_at
                """, (
                    img_hash, img_blob, predicted, corrected,
                    language, confidence, writer_id, context_hint,
                    now, now, now,
                ))

            # Update learning stats
            self._update_stats(writer_id, language)

            return True

        except Exception as e:
            logger.error(f"Failed to save pattern: {e}")
            return False

    def suggest_correction(
        self,
        image: np.ndarray,
        language: str = "ar",
        writer_id: str = "default",
        min_usage: int = 2,
    ) -> Optional[Dict]:
        """
        Suggest a correction based on previously seen patterns.

        Args:
            image: Word image as numpy array
            language: Language code
            writer_id: Writer identifier
            min_usage: Minimum times a pattern must be seen to be trusted

        Returns:
            Dict with suggestion info, or None if no match found
        """
        img_hash = self._robust_image_hash(image)

        with self.connection() as conn:
            cursor = conn.execute("""
                SELECT corrected_text, predicted_text, confidence,
                       usage_count, context_hint
                FROM patterns
                WHERE image_hash = ? AND language = ? AND writer_id = ?
                  AND usage_count >= ?
                ORDER BY usage_count DESC, confidence DESC
                LIMIT 1
            """, (img_hash, language, writer_id, min_usage))

            row = cursor.fetchone()

        if row:
            return {
                "suggested_text": row["corrected_text"],
                "original_predicted": row["predicted_text"],
                "confidence": row["confidence"],
                "times_used": row["usage_count"],
                "source": "exact_pattern_match",
                "context": row["context_hint"],
            }

        return None

    def find_similar_patterns(
        self,
        image: np.ndarray,
        language: str = "ar",
        writer_id: str = "default",
        max_results: int = 5,
        threshold: float = 0.80,
    ) -> List[Dict]:
        """
        Find patterns with similar (but not exact) visual appearance.

        Uses hash prefix matching for fast approximate search.

        Args:
            image: Query image
            language: Language filter
            writer_id: Writer filter
            max_results: Maximum number of results
            threshold: Minimum hash similarity (0-1)

        Returns:
            List of similar pattern dicts
        """
        img_hash = self._robust_image_hash(image)
        prefix_len = max(len(img_hash) // 2, 8)

        with self.connection() as conn:
            cursor = conn.execute("""
                SELECT image_hash, corrected_text, predicted_text,
                       confidence, usage_count, writer_id
                FROM patterns
                WHERE image_hash LIKE ? AND language = ? AND writer_id = ?
                  AND usage_count >= 2
                ORDER BY usage_count DESC
                LIMIT ?
            """, (f"{img_hash[:prefix_len]}%", language, writer_id, max_results))

            results = []
            for row in cursor.fetchall():
                # Compute hash similarity
                similarity = self._hash_similarity(img_hash, row["image_hash"])
                if similarity >= threshold:
                    results.append({
                        "corrected_text": row["corrected_text"],
                        "predicted_text": row["predicted_text"],
                        "confidence": row["confidence"],
                        "usage_count": row["usage_count"],
                        "similarity": similarity,
                        "hash_match": row["image_hash"],
                    })

        return sorted(results, key=lambda x: x["similarity"], reverse=True)

    def get_training_samples(
        self,
        writer_id: str = "default",
        language: Optional[str] = None,
        min_usage: int = 3,
        limit: int = 1000,
    ) -> List[Dict]:
        """
        Get high-quality samples suitable for LoRA fine-tuning.

        Filters by minimum usage count (repeated corrections = more reliable).

        Args:
            writer_id: Writer filter
            language: Language filter
            min_usage: Minimum usage count for reliability
            limit: Maximum number of samples

        Returns:
            List of dicts with 'image' (numpy array) and 'label' (corrected text)
        """
        conditions = [writer_id]
        params = [writer_id, min_usage, limit]

        query = """
            SELECT image_blob, corrected_text, language, context_hint,
                   predicted_text, confidence
            FROM patterns
            WHERE writer_id = ? AND usage_count >= ?
        """

        if language:
            query += " AND language = ?"
            conditions.append(language)
            params.append(language)

        query += " ORDER BY usage_count DESC, confidence DESC LIMIT ?"

        try:
            with self.connection() as conn:
                cursor = conn.execute(query, params)

                samples = []
                for row in cursor.fetchall():
                    image = self._decompress_image(row["image_blob"])
                    if image is not None:
                        samples.append({
                            "image": image,
                            "label": row["corrected_text"],
                            "language": row["language"],
                            "context": row["context_hint"],
                            "predicted": row["predicted_text"],
                            "confidence": row["confidence"],
                        })
        except Exception as e:
            logger.error(f"Failed to get training samples: {e}")
            return []

        logger.info(f"Retrieved {len(samples)} training samples (writer={writer_id})")
        return samples

    def get_writer_stats(self, writer_id: str = "default") -> Dict:
        """Get learning statistics for a writer."""
        with self.connection() as conn:
            cursor = conn.execute("""
                SELECT language, total_corrections, patterns_learned,
                       total_images, avg_confidence, improvement_rate, last_trained
                FROM learning_stats
                WHERE writer_id = ?
            """, (writer_id,))

            stats = {}
            for row in cursor.fetchall():
                stats[row["language"]] = {
                    "total_corrections": row["total_corrections"],
                    "patterns_learned": row["patterns_learned"],
                    "total_images": row["total_images"],
                    "avg_confidence": row["avg_confidence"],
                    "improvement_rate": row["improvement_rate"],
                    "last_trained": row["last_trained"],
                }

        return stats

    def get_all_stats(self) -> Dict:
        """Get global statistics."""
        with self.connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as total_patterns FROM patterns"
            ).fetchone()["total_patterns"]

            writers = conn.execute(
                "SELECT COUNT(DISTINCT writer_id) as total_writers FROM patterns"
            ).fetchone()["total_writers"]

            languages = conn.execute(
                "SELECT COUNT(DISTINCT language) as total_languages FROM patterns"
            ).fetchone()["total_languages"]

        return {
            "total_patterns": total,
            "total_writers": writers,
            "total_languages": languages,
        }

    def delete_writer(self, writer_id: str) -> int:
        """Delete all patterns for a writer. Returns count deleted."""
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM patterns WHERE writer_id = ?", (writer_id,)
            )
            return cursor.rowcount

    def cleanup_old_patterns(self, days: int = 90) -> int:
        """Delete patterns older than N days. Returns count deleted."""
        with self.connection() as conn:
            cursor = conn.execute("""
                DELETE FROM patterns
                WHERE last_used < datetime('now', '-' || str(days) || ' days').isoformat()
            """)
            return cursor.rowcount

    def export_to_json(self, output_path: str) -> str:
        """Export all patterns as JSON for backup."""
        with self.connection() as conn:
            cursor = conn.execute("""
                SELECT image_hash, predicted_text, corrected_text, language,
                       confidence, writer_id, context_hint, usage_count,
                       last_used, created_at
                FROM patterns
                ORDER BY usage_count DESC
            """)

            rows = [dict(row) for row in cursor.fetchall()]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

        return output_path

    # -------------------------------------------------------------------------
    # Internal methods
    # -------------------------------------------------------------------------

    def _robust_image_hash(self, image: np.ndarray) -> str:
        """
        Generate a perceptual hash resistant to minor variations.

        Process: resize -> normalize contrast -> Gaussian blur -> SHA256.
        This ensures the same word written slightly differently
        produces the same or similar hash.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Resize to fixed size
        resized = cv2.resize(gray, (64, 32), interpolation=cv2.INTER_LINEAR)

        # Normalize contrast
        normalized = cv2.normalize(resized, None, 0, 255, cv2.NORM_MINMAX)

        # Light blur to reduce noise sensitivity
        blurred = cv2.GaussianBlur(normalized, (3, 3), 0)

        return hashlib.sha256(blurred.tobytes()).hexdigest()[:32]

    def _compress_image(self, image: np.ndarray) -> bytes:
        """Compress image using JPEG + zlib for storage."""
        success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            success, buffer = cv2.imencode(".png", image)
        jpeg_bytes = buffer.tobytes()

        import zlib
        return zlib.compress(jpeg_bytes, level=self._compression_level)

    def _decompress_image(self, blob: bytes) -> Optional[np.ndarray]:
        """Decompress image from stored blob."""
        try:
            import zlib
            jpeg_bytes = zlib.decompress(blob)
            img_array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"Failed to decompress image: {e}")
            return None

    def _hash_similarity(self, hash1: str, hash2: str) -> float:
        """Compute Jaccard-like similarity between two hash prefixes."""
        if not hash1 or not hash2:
            return 0.0
        common = sum(1 for a, b in zip(hash1, hash2) if a == b)
        total = len(hash1) + len(hash2)
        return common / total if total > 0 else 0.0

    def _update_stats(self, writer_id: str, language: str):
        """Update learning statistics for a writer."""
        now = datetime.utcnow().isoformat()

        with self.connection() as conn:
            # Get current stats or create new
            cursor = conn.execute("""
                SELECT total_corrections, patterns_learned, total_images,
                       avg_confidence, last_trained
                FROM learning_stats
                WHERE writer_id = ? AND language = ?
            """, (writer_id, language))

            row = cursor.fetchone()
            if row:
                new_corrections = row["total_corrections"] + 1
                new_patterns = row["patterns_learned"] + 1
                total_images = row["total_images"] + 1
                avg_conf = row["avg_confidence"]
                last_trained = row["last_trained"]
            else:
                new_corrections = 1
                new_patterns = 1
                total_images = 1
                avg_conf = 0.0
                last_trained = None

            # Compute improvement rate
            improvement = 0.0
            if last_trained and avg_conf > 0:
                improvement = (new_corrections / max(new_patterns, 1)) / max(total_images, 1)

            conn.execute("""
                INSERT INTO learning_stats
                    (writer_id, language, total_corrections, patterns_learned,
                     total_images, avg_confidence, improvement_rate, last_trained, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(writer_id, language) DO UPDATE SET
                    total_corrections = excluded.total_corrections,
                    patterns_learned = excluded.patterns_learned,
                    total_images = excluded.total_images,
                    avg_confidence = excluded.avg_confidence,
                    improvement_rate = excluded.improvement_rate,
                    last_trained = excluded.last_trained,
                    updated_at = ?
            """, (
                writer_id, language, new_corrections, new_patterns,
                total_images, avg_conf, improvement, now, now,
            ))
