# active_learning.py - Active learning for OCR improvement

from typing import Dict, List, Optional, Union
from pathlib import Path
from modules.core.base_db import BaseDB
import json
import logging
from datetime import datetime
from .finetuning import TrOCRFineTuner

logger = logging.getLogger(__name__)

class ActiveLearningDB(BaseDB):
    """قاعدة بيانات للتعلم من تصحيحات المستخدم."""

    def __init__(self, db_path: Union[str, Path] = "active_learning.db"):
        super().__init__(db_path)

    def _create_schema(self, conn):
        """تهيئة قاعدة البيانات."""
        cursor = conn.cursor()

        # جدول التصحيحات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                language TEXT NOT NULL,
                confidence REAL,
                source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                correction_count INTEGER DEFAULT 1,
                is_used_in_training BOOLEAN DEFAULT FALSE
            )
        """)

        # جدول بيانات التدريب
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT,
                original_text TEXT,
                corrected_text TEXT,
                language TEXT NOT NULL,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_used_in_training BOOLEAN DEFAULT FALSE
            )
        """)

        # جدول نماذج OCR المدربة
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fine_tuned_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                model_path TEXT NOT NULL,
                language TEXT NOT NULL,
                base_model TEXT NOT NULL,
                accuracy REAL,
                version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # جدول إعدادات النظام
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # إعدادات افتراضية
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('correction_threshold', '2')
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('training_batch_size', '100')
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('min_confidence', '0.7')
        """)

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """الحصول على إعداد."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT value FROM settings WHERE key = ?
            """, (key,))
            result = cursor.fetchone()
            return result[0] if result else default

    def set_setting(self, key: str, value: str) -> bool:
        """تحديد إعداد."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            return cursor.rowcount > 0

    def save_correction(
        self,
        original_text: str,
        corrected_text: str,
        language: str,
        confidence: float,
        source: str = "manual"
    ) -> int:
        """
        حفظ تصحيح جديد.

        Args:
            original_text: النص الأصلي.
            corrected_text: النص المصحح.
            language: لغة النص.
            confidence: ثقة النتيجة.
            source: مصدر التصحيح (manual, auto, etc.).

        Returns:
            int: ID التصحيح.
        """
        with self.connection() as conn:
            cursor = conn.cursor()

            # التحقق من وجود تصحيح مشابه
            cursor.execute("""
                SELECT id, correction_count FROM corrections
                WHERE original_text = ? AND corrected_text = ? AND language = ?
            """, (original_text, corrected_text, language))

            result = cursor.fetchone()

            if result:
                # تحديث التصحيح الموجود
                correction_id, count = result
                cursor.execute("""
                    UPDATE corrections
                    SET correction_count = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (count + 1, correction_id))
            else:
                # إضافة تصحيح جديد
                cursor.execute("""
                    INSERT INTO corrections
                    (original_text, corrected_text, language, confidence, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (original_text, corrected_text, language, confidence, source))
                correction_id = cursor.lastrowid

            return correction_id

    def get_corrections(
        self,
        language: str,
        limit: int = 100,
        min_confidence: float = 0.0,
        min_correction_count: int = 1
    ) -> List[Dict]:
        """
        استعادة تصحيحات للمستخدم.

        Args:
            language: لغة التصحيحات.
            limit: الحد الأقصى لعدد التصحيحات.
            min_confidence: الحد الأدنى للثقة.
            min_correction_count: الحد الأدنى لعدد مرات التصحيح.

        Returns:
            List[Dict]: قائمة التصحيحات.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM corrections
                WHERE language = ? AND confidence >= ? AND correction_count >= ?
                ORDER BY correction_count DESC, created_at DESC
                LIMIT ?
            """, (language, min_confidence, min_correction_count, limit))

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def save_training_data(
        self,
        image_path: str,
        original_text: str,
        corrected_text: str,
        language: str,
        confidence: float
    ) -> int:
        """
        حفظ بيانات تدريب جديدة.

        Args:
            image_path: مسار الصورة.
            original_text: النص الأصلي.
            corrected_text: النص المصحح.
            language: لغة النص.
            confidence: ثقة النتيجة.

        Returns:
            int: ID بيانات التدريب.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO training_data
                (image_path, original_text, corrected_text, language, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (image_path, original_text, corrected_text, language, confidence))
            return cursor.lastrowid

    def get_training_data(
        self,
        language: str,
        limit: int = 1000,
        min_confidence: float = 0.7
    ) -> List[Dict]:
        """
        استعادة بيانات التدريب.

        Args:
            language: لغة البيانات.
            limit: الحد الأقصى لعدد البيانات.
            min_confidence: الحد الأدنى للثقة.

        Returns:
            List[Dict]: قائمة بيانات التدريب.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM training_data
                WHERE language = ? AND confidence >= ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (language, min_confidence, limit))

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def mark_as_used_in_training(self, correction_id: int) -> bool:
        """
        تحديد تصحيح كمستخدم في التدريب.

        Args:
            correction_id: ID التصحيح.

        Returns:
            bool: True إذا تم التحديث، False إذا لم يتم العثور على التصحيح.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE corrections
                SET is_used_in_training = TRUE
                WHERE id = ?
            """, (correction_id,))
            return cursor.rowcount > 0

    def mark_training_data_as_used(self, data_id: int) -> bool:
        """
        تحديد بيانات تدريب كمستخدمة.

        Args:
            data_id: ID بيانات التدريب.

        Returns:
            bool: True إذا تم التحديث، False إذا لم يتم العثور على البيانات.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE training_data
                SET is_used_in_training = TRUE
                WHERE id = ?
            """, (data_id,))
            return cursor.rowcount > 0

    def save_fine_tuned_model(
        self,
        model_name: str,
        model_path: str,
        language: str,
        base_model: str,
        accuracy: float,
        version: str = "1.0"
    ) -> int:
        """
        حفظ نموذج مدرب.

        Args:
            model_name: اسم النموذج.
            model_path: مسار النموذج.
            language: لغة النموذج.
            base_model: النموذج الأساسي.
            accuracy: دقة النموذج.
            version: الإصدار.

        Returns:
            int: ID النموذج.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fine_tuned_models
                (model_name, model_path, language, base_model, accuracy, version)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (model_name, model_path, language, base_model, accuracy, version))
            return cursor.lastrowid

    def get_fine_tuned_models(
        self,
        language: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        استعادة نماذج مدربة.

        Args:
            language: لغة النماذج.
            limit: الحد الأقصى لعدد النماذج.

        Returns:
            List[Dict]: قائمة النماذج.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fine_tuned_models
                WHERE language = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (language, limit))

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

class ActiveLearner:
    """نظام تعلم نشط من تصحيحات المستخدم."""

    def __init__(
        self,
        db_path: Union[str, Path] = "active_learning.db",
    ):
        """
        تهيئة النظام.

        Args:
            db_path: مسار قاعدة البيانات.
        """
        self.db = ActiveLearningDB(db_path)
        self.fine_tuner = TrOCRFineTuner()

    def log_correction(
        self,
        original_text: str,
        corrected_text: str,
        language: str,
        confidence: float,
        source: str = "manual",
        image_path: Optional[str] = None
    ) -> int:
        """
        سجل تصحيحًا جديدًا.

        Args:
            original_text: النص الأصلي.
            corrected_text: النص المصحح.
            language: لغة النص.
            confidence: ثقة النتيجة.
            source: مصدر التصحيح.
            image_path: مسار الصورة (اختياري).

        Returns:
            int: ID التصحيح.
        """
        correction_id = self.db.save_correction(
            original_text, corrected_text, language, confidence, source
        )

        # إذا كان هناك صورة، حفظها في بيانات التدريب
        if image_path:
            self.db.save_training_data(
                image_path, original_text, corrected_text, language, confidence
            )

        # التحقق من عدد التصحيحات لنفس النص
        correction_threshold = int(self.db.get_setting("correction_threshold", "2"))
        corrections = self.db.get_corrections(
            language=language,
            limit=100,
            min_confidence=confidence
        )

        # إذا كان هناك عدد كافٍ من التصحيحات، قم بتدريب النموذج
        if len(corrections) >= correction_threshold:
            self._retrain_model(language)

        return correction_id

    def _retrain_model(self, language: str):
        """إعادة تدريب النموذج على البيانات المصححة."""
        logger.info(f"جاري إعادة تدريب النموذج للغة {language}...")

        # استعادة بيانات التدريب
        training_batch_size = int(self.db.get_setting("training_batch_size", "100"))
        min_confidence = float(self.db.get_setting("min_confidence", "0.7"))

        training_data = self.db.get_training_data(
            language=language,
            limit=training_batch_size,
            min_confidence=min_confidence
        )

        if not training_data:
            logger.warning(f"لا توجد بيانات تدريب للغة {language}")
            return

        # هنا يتم تدريب النموذج (مثال: TrOCR)
        try:
            # تحميل الصور والنصوص
            train_images = []
            train_texts = []

            for data in training_data:
                try:
                    train_images.append(data["image_path"])
                    train_texts.append(data["corrected_text"])

                    # تحديد البيانات كمستخدمة في التدريب
                    self.db.mark_training_data_as_used(data["id"])
                except Exception as e:
                    logger.error(f"فشل تحميل البيانات {data['id']}: {e}")

            if not train_images:
                logger.warning("لا توجد بيانات صالحة للتدريب")
                return

            # تدريب النموذج
            model_name = f"trocr_{language}_v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_path = self.fine_tuner.train(
                train_images=train_images,
                train_texts=train_texts,
                epochs=3,
                batch_size=4,
                learning_rate=5e-5,
                model_name=model_name,
                save_model=True
            )

            # حفظ النموذج في قاعدة البيانات
            self.db.save_fine_tuned_model(
                model_name=model_name,
                model_path=str(output_path),
                language=language,
                base_model=self.fine_tuner.model_name,
                accuracy=0.95,  # دقة افتراضية
                version="1.0"
            )

            logger.info(f"تم تدريب النموذج للغة {language} وحفظه في {output_path}")

            # تحديد التصحيحات كمستخدمة في التدريب
            for data in training_data:
                self.db.mark_as_used_in_training(data["id"])

        except Exception as e:
            logger.error(f"فشل تدريب النموذج: {e}")

    def get_suggestions(self, text: str, language: str, limit: int = 5) -> List[str]:
        """
        الحصول على اقتراحات لتصحيح النص.

        Args:
            text: النص المراد تصحيحه.
            language: لغة النص.
            limit: الحد الأقصى لعدد الاقتراحات.

        Returns:
            List[str]: قائمة الاقتراحات.
        """
        min_confidence = float(self.db.get_setting("min_confidence", "0.7"))
        min_correction_count = int(self.db.get_setting("correction_threshold", "2"))

        corrections = self.db.get_corrections(
            language=language,
            limit=limit * 2,  # الحصول على ضعف العدد المطلوب
            min_confidence=min_confidence,
            min_correction_count=min_correction_count
        )

        suggestions = []
        for correction in corrections:
            if correction["original_text"] in text and correction["corrected_text"] not in suggestions:
                suggestions.append(correction["corrected_text"])
                if len(suggestions) >= limit:
                    break

        return suggestions

    def get_fine_tuned_model_path(self, language: str) -> Optional[str]:
        """
        الحصول على مسار نموذج مدرب للغة المحددة.

        Args:
            language: لغة النموذج.

        Returns:
            Optional[str]: مسار النموذج إذا كان متاحًا، None إذا لم يكن متاحًا.
        """
        models = self.db.get_fine_tuned_models(language=language, limit=1)
        if models:
            return models[0]["model_path"]
        return None

    def get_training_stats(self, language: str) -> Dict:
        """
        الحصول على إحصائيات التدريب.

        Args:
            language: لغة البيانات.

        Returns:
            Dict: إحصائيات التدريب.
        """
        with self.db.connection() as conn:
            cursor = conn.cursor()

            # عدد التصحيحات
            cursor.execute("""
                SELECT COUNT(*) FROM corrections WHERE language = ?
            """, (language,))
            total_corrections = cursor.fetchone()[0]

            # عدد التصحيحات المستخدمة في التدريب
            cursor.execute("""
                SELECT COUNT(*) FROM corrections
                WHERE language = ? AND is_used_in_training = TRUE
            """, (language,))
            used_corrections = cursor.fetchone()[0]

            # عدد بيانات التدريب
            cursor.execute("""
                SELECT COUNT(*) FROM training_data WHERE language = ?
            """, (language,))
            total_training_data = cursor.fetchone()[0]

            # عدد بيانات التدريب المستخدمة
            cursor.execute("""
                SELECT COUNT(*) FROM training_data
                WHERE language = ? AND is_used_in_training = TRUE
            """, (language,))
            used_training_data = cursor.fetchone()[0]

            # عدد النماذج المدربة
            cursor.execute("""
                SELECT COUNT(*) FROM fine_tuned_models WHERE language = ?
            """, (language,))
            total_models = cursor.fetchone()[0]

            return {
                "total_corrections": total_corrections,
                "used_corrections": used_corrections,
                "total_training_data": total_training_data,
                "used_training_data": used_training_data,
                "total_models": total_models,
                "language": language
            }
