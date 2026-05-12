"""
Pattern DB — قاعدة بيانات لأنماط الخط اليدوي الشخصية
تتعلم من تصحيحات المستخدم وتقترح تلقائياً
"""
from modules.core.base_db import BaseDB
import hashlib
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict


class PatternDB(BaseDB):
    """قاعدة بيانات لأنماط الخط اليدوي الشخصية"""

    def __init__(self, db_path: str = "data/vocab_patterns.db"):
        super().__init__(db_path)

    def _create_schema(self, conn):
        """إنشاء الجداول إذا لم تكن موجودة"""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_hash TEXT UNIQUE NOT NULL,
                image_blob BLOB,
                predicted_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                language TEXT CHECK(language IN ('en', 'ar', 'mixed', 'symbol')),
                category TEXT DEFAULT 'vocab',
                writer_id TEXT DEFAULT 'default',
                confidence REAL,
                usage_count INTEGER DEFAULT 1,
                correction_count INTEGER DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context_json TEXT
            );

            CREATE TABLE IF NOT EXISTS correction_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                page_hash TEXT,
                total_words INTEGER,
                corrected_words INTEGER,
                avg_confidence REAL,
                notes TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_hash_lang ON patterns(image_hash, language);
            CREATE INDEX IF NOT EXISTS idx_writer_cat ON patterns(writer_id, category);
            CREATE INDEX IF NOT EXISTS idx_usage ON patterns(usage_count DESC);
        """)

    def save_pattern(self,
                    image: np.ndarray,
                    predicted: str,
                    corrected: str,
                    language: str,
                    confidence: float,
                    category: str = 'vocab',
                    writer_id: str = 'default',
                    context: dict = None) -> int:
        """حفظ نمط جديد أو تحديث نمط موجود"""
        image_hash = self._compute_robust_hash(image)
        _, buffer = cv2.imencode('.png', image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        image_blob = buffer.tobytes()
        context_json = str(context) if context else None

        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO patterns
                (image_hash, image_blob, predicted_text, corrected_text,
                 language, category, writer_id, confidence, context_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(image_hash) DO UPDATE SET
                    corrected_text = excluded.corrected_text,
                    usage_count = usage_count + 1,
                    correction_count = correction_count + 1,
                    last_used = CURRENT_TIMESTAMP,
                    confidence = (confidence + excluded.confidence) / 2
            """, (image_hash, image_blob, predicted, corrected,
                  language, category, writer_id, confidence, context_json))

            return cursor.lastrowid or self._get_id_by_hash(image_hash)

    def find_similar(self,
                    image: np.ndarray,
                    language: str,
                    threshold: float = 0.92,
                    writer_id: str = 'default') -> Optional[Dict]:
        """البحث عن نمط مشابه بصرياً"""
        image_hash = self._compute_robust_hash(image)

        with self.connection() as conn:
            cursor = conn.execute("""
                SELECT id, corrected_text, confidence, usage_count, correction_count, category
                FROM patterns
                WHERE image_hash = ? AND language = ? AND writer_id = ?
                AND usage_count >= 2
            """, (image_hash, language, writer_id))

            result = cursor.fetchone()
            if result:
                pattern_id, text, conf, usage, corrections, category = result
                if usage >= 3 or corrections >= 1:
                    return {
                        'id': pattern_id,
                        'corrected_text': text,
                        'confidence': conf,
                        'category': category,
                        'match_type': 'exact_hash'
                    }

        return None

    def get_training_samples(self,
                           writer_id: str = 'default',
                           min_usage: int = 3,
                           limit: int = 500,
                           category: str = None) -> List[Dict]:
        """جلب عينات عالية الجودة لإعادة تدريب النموذج"""
        samples = []

        with self.connection() as conn:
            query = """
                SELECT image_blob, corrected_text, language, category, confidence
                FROM patterns
                WHERE writer_id = ? AND usage_count >= ?
            """
            params = [writer_id, min_usage]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " ORDER BY usage_count DESC, last_used DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)

            for row in cursor.fetchall():
                image_blob, text, lang, cat, conf = row
                img_array = np.frombuffer(image_blob, dtype=np.uint8)
                image = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

                samples.append({
                    'image': image,
                    'label': text,
                    'language': lang,
                    'category': cat,
                    'confidence': conf
                })

        return samples

    def log_session(self,
                   page_hash: str,
                   total_words: int,
                   corrected_words: int,
                   avg_confidence: float,
                   notes: str = None) -> int:
        """تسجيل إحصائيات جلسة معالجة"""
        with self.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO correction_sessions
                (page_hash, total_words, corrected_words, avg_confidence, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (page_hash, total_words, corrected_words, avg_confidence, notes))
            return cursor.lastrowid

    def get_stats(self) -> Dict:
        """إحصائيات عامة لقاعدة الأنماط"""
        with self.connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]
            languages = conn.execute(
                "SELECT language, COUNT(*) FROM patterns GROUP BY language"
            ).fetchall()
            writers = conn.execute(
                "SELECT writer_id, COUNT(*) FROM patterns GROUP BY writer_id"
            ).fetchall()
            sessions = conn.execute("SELECT COUNT(*) FROM correction_sessions").fetchone()[0]

            return {
                'total_patterns': total,
                'by_language': dict(languages),
                'by_writer': dict(writers),
                'total_sessions': sessions
            }

    def _compute_robust_hash(self, image: np.ndarray) -> str:
        """توليد بصمة مقاومة للتغيرات الطفيفة في الإضاءة/الحجم"""
        resized = cv2.resize(image, (64, 32), interpolation=cv2.INTER_LINEAR)

        if resized.std() > 0:
            normalized = (resized - resized.mean()) / resized.std()
            normalized = ((normalized - normalized.min()) /
                         (normalized.max() - normalized.min()) * 255).astype(np.uint8)
        else:
            normalized = resized

        blurred = cv2.GaussianBlur(normalized, (3, 3), 0)
        return hashlib.sha256(blurred.tobytes()).hexdigest()[:32]

    def _get_id_by_hash(self, image_hash: str) -> Optional[int]:
        """مساعدة: جلب معرف النمط من البصمة"""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM patterns WHERE image_hash = ?",
                (image_hash,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
