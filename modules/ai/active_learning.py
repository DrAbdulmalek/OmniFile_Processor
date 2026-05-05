"""
التعلم النشط — Active Learning Module
========================================
نظام تعلم نشط يحسّن دقة OCR عبر تصحيحات المستخدم وإعادة التدريب التلقائي.

القدرات:
- تخزين تصحيحات المستخدم في قاعدة بيانات SQLite مع إلغاء التكرار
- مراقبة وصول التصحيحات لعتبة إعادة التدريب
- تصدير بيانات التدريب بصيغة JSONL متوافقة مع TrOCR
- تتبع إصدارات النماذج بعد الضبط الدقيق
- إحصائيات شاملة وتحليلات تحسين الثقة

مثال الاستخدام:
    >>> learner = ActiveLearner(db_path="data/active_learning.db")
    >>> learner.log_correction("hellp", "hello", confidence=0.45, source="trocr")
    >>> learner.log_correction("wrld", "world", confidence=0.62, source="easyocr")
    >>> stats = learner.get_stats()
    >>> if learner.should_retrain():
    ...     path = learner.export_training_data("training_data.jsonl")
    ...     learner.record_model_version("trocr-v2", metrics={"cer": 0.03})
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ======================================================================
# قاعدة بيانات التعلم النشط
# ======================================================================

class ActiveLearningDB:
    """قاعدة بيانات SQLite لإدارة نظام التعلم النشط.

    تدير ثلاثة جداول:
    - **corrections**: تصحيحات المستخدم (النص الأصلي ← النص المصحّح)
    - **training_data**: بيانات التدريب المُصدَّرة للضبط الدقيق
    - **fine_tuned_models**: إصدارات النماذج ونتائج التقييم

    Attributes:
        db_path: مسار ملف قاعدة البيانات.
    """

    def __init__(self, db_path: str | Path = "data/active_learning.db") -> None:
        """تهيئة قاعدة بيانات التعلم النشط.

        Args:
            db_path: مسار ملف SQLite (يُنشأ تلقائياً إذا لم يوجد).
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None
        self._initialize_database()

    # ------------------------------------------------------------------
    # إدارة الاتصال
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """الحصول على اتصال نشط بقاعدة البيانات (يُنشأ عند أول استخدام).

        Returns:
            كائن sqlite3.Connection مُهيأ.
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
        return self._connection

    def _initialize_database(self) -> None:
        """إنشاء الجداول إذا لم تكن موجودة.

        الجداول المُنشأة:
        - corrections: تخزين تصحيحات المستخدم مع إلغاء التكرار
        - training_data: بيانات التدريب بتنسيق JSONL
        - fine_tuned_models: سجل إصدارات النماذج المُضبَّطة
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                original_confidence REAL DEFAULT 0.0,
                source_engine TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                dedup_hash TEXT NOT NULL,
                UNIQUE(dedup_hash)
            );

            CREATE INDEX IF NOT EXISTS idx_corrections_source
                ON corrections(source_engine);

            CREATE INDEX IF NOT EXISTS idx_corrections_confidence
                ON corrections(original_confidence);

            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                correction_id INTEGER NOT NULL,
                original_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                image_data BLOB,
                source_engine TEXT DEFAULT '',
                exported_at TEXT NOT NULL DEFAULT (datetime('now')),
                included_in_version TEXT DEFAULT NULL,
                FOREIGN KEY (correction_id) REFERENCES corrections(id)
            );

            CREATE INDEX IF NOT EXISTS idx_training_version
                ON training_data(included_in_version);

            CREATE TABLE IF NOT EXISTS fine_tuned_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_name TEXT NOT NULL UNIQUE,
                base_model TEXT DEFAULT '',
                training_samples INTEGER DEFAULT 0,
                metrics_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                notes TEXT DEFAULT ''
            );
        """)

        conn.commit()
        logger.debug("تم تهيئة قاعدة بيانات التعلم النشط: %s", self.db_path)

    # ------------------------------------------------------------------
    # عمليات التصحيحات
    # ------------------------------------------------------------------

    def add_correction(
        self,
        original_text: str,
        corrected_text: str,
        original_confidence: float = 0.0,
        source_engine: str = "",
    ) -> Optional[int]:
        """إضافة تصحيح جديد مع إلغاء التكرار التلقائي.

        يُحسب تجزئة فريدة (hash) من النص الأصلي والمُصحَّح لمنع التكرار.

        Args:
            original_text: النص الأصلي (قبل التصحيح).
            corrected_text: النص المصحّح من المستخدم.
            original_confidence: ثقة OCR الأصلية (0.0 - 1.0).
            source_engine: محرك OCR المصدر.

        Returns:
            معرّف السجل (ID) أو None إذا كان مكرراً.
        """
        import hashlib

        conn = self._get_connection()
        cursor = conn.cursor()

        # حساب تجزئة فريدة لإلغاء التكرار
        dedup_key = f"{original_text.strip().lower()}|||{corrected_text.strip()}"
        dedup_hash = hashlib.sha256(dedup_key.encode("utf-8")).hexdigest()

        try:
            cursor.execute(
                """INSERT INTO corrections
                   (original_text, corrected_text, original_confidence,
                    source_engine, dedup_hash)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    original_text.strip(),
                    corrected_text.strip(),
                    original_confidence,
                    source_engine,
                    dedup_hash,
                ),
            )
            conn.commit()
            row_id = cursor.lastrowid
            logger.info(
                "تصحيح جديد #%d: '%s' → '%s' (ثقة: %.2f, محرك: %s)",
                row_id, original_text, corrected_text,
                original_confidence, source_engine,
            )
            return row_id
        except sqlite3.IntegrityError:
            logger.debug(
                "تصحيح مكرر (تم التجاهل): '%s' → '%s'",
                original_text, corrected_text,
            )
            return None

    def get_corrections(
        self,
        min_confidence: float = 0.0,
        source_engine: Optional[str] = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """استرجاع التصحيحات مع فلاتر اختيارية.

        Args:
            min_confidence: أقل حد للثقة (للتركيز على التصحيحات ذات الثقة المنخفضة).
            source_engine: فلتر حسب المحرك.
            limit: أقصى عدد نتائج.

        Returns:
            قائمة قواميس التصحيحات.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT id, original_text, corrected_text, original_confidence,
                   source_engine, created_at, dedup_hash
            FROM corrections
            WHERE original_confidence >= ?
        """
        params: list[Any] = [min_confidence]

        if source_engine:
            query += " AND source_engine = ?"
            params.append(source_engine)

        query += " ORDER BY original_confidence ASC, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        return [
            {
                "id": row["id"],
                "original_text": row["original_text"],
                "corrected_text": row["corrected_text"],
                "original_confidence": row["original_confidence"],
                "source_engine": row["source_engine"],
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]

    def count_corrections(self) -> int:
        """عدد التصحيحات الفريدة.

        Returns:
            عدد السجلات في جدول corrections.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM corrections")
        return cursor.fetchone()["cnt"]

    # ------------------------------------------------------------------
    # عمليات بيانات التدريب
    # ------------------------------------------------------------------

    def add_training_entry(
        self,
        correction_id: int,
        original_text: str,
        corrected_text: str,
        image_data: Optional[bytes] = None,
        source_engine: str = "",
    ) -> int:
        """إضافة سجل بيانات تدريب مرتبط بتصحيح.

        Args:
            correction_id: معرّف التصحيح المرتبط.
            original_text: النص الأصلي.
            corrected_text: النص المصحّح.
            image_data: بيانات الصورة (اختياري).
            source_engine: محرك OCR المصدر.

        Returns:
            معرّف سجل التدريب.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO training_data
               (correction_id, original_text, corrected_text,
                image_data, source_engine)
               VALUES (?, ?, ?, ?, ?)""",
            (correction_id, original_text, corrected_text,
             image_data, source_engine),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_training_data(
        self,
        included_in_version: Optional[str] = None,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        """استرجاع بيانات التدريب.

        Args:
            included_in_version: فلتر حسب إصدار النموذج.
            limit: أقصى عدد نتائج.

        Returns:
            قائمة بيانات التدريب.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if included_in_version is not None:
            cursor.execute(
                """SELECT id, correction_id, original_text, corrected_text,
                          source_engine, exported_at, included_in_version
                   FROM training_data
                   WHERE included_in_version = ?
                   ORDER BY id DESC LIMIT ?""",
                (included_in_version, limit),
            )
        else:
            cursor.execute(
                """SELECT id, correction_id, original_text, corrected_text,
                          source_engine, exported_at, included_in_version
                   FROM training_data
                   WHERE included_in_version IS NULL
                   ORDER BY id DESC LIMIT ?""",
                (limit,),
            )

        return [
            {
                "id": row["id"],
                "correction_id": row["correction_id"],
                "original_text": row["original_text"],
                "corrected_text": row["corrected_text"],
                "source_engine": row["source_engine"],
                "exported_at": row["exported_at"],
                "included_in_version": row["included_in_version"],
            }
            for row in cursor.fetchall()
        ]

    def mark_training_used(self, version_name: str) -> int:
        """تحديد بيانات التدريب غير المستخدمة كـمُستخدمة في إصدار محدد.

        Args:
            version_name: اسم إصدار النموذج.

        Returns:
            عدد السجلات المُحدَّثة.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """UPDATE training_data
               SET included_in_version = ?
               WHERE included_in_version IS NULL""",
            (version_name,),
        )
        conn.commit()
        updated = cursor.rowcount
        logger.info("تم تحديد %d سجل تدريب كـمُستخدم في الإصدار '%s'", updated, version_name)
        return updated

    # ------------------------------------------------------------------
    # عمليات النماذج
    # ------------------------------------------------------------------

    def add_model_version(
        self,
        version_name: str,
        base_model: str = "",
        training_samples: int = 0,
        metrics: Optional[dict[str, Any]] = None,
        notes: str = "",
    ) -> int:
        """تسجيل إصدار نموذج جديد بعد الضبط الدقيق.

        Args:
            version_name: اسم الإصدار (يجب أن يكون فريداً).
            base_model: اسم النموذج الأساسي.
            training_samples: عدد عيّنات التدريب المستخدمة.
            metrics: قاموس مقاييس الأداء (مثل CER, WER, accuracy).
            notes: ملاحظات إضافية.

        Returns:
            معرّف الإصدار.

        Raises:
            ValueError: إذا كان اسم الإصدار مكرراً.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        metrics_json = json.dumps(metrics or {}, ensure_ascii=False)

        try:
            cursor.execute(
                """INSERT INTO fine_tuned_models
                   (version_name, base_model, training_samples,
                    metrics_json, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (version_name, base_model, training_samples,
                 metrics_json, notes),
            )
            conn.commit()
            model_id = cursor.lastrowid
            logger.info(
                "إصدار نموذج جديد #%d: '%s' (عدد عيّنات: %d)",
                model_id, version_name, training_samples,
            )
            return model_id  # type: ignore[return-value]
        except sqlite3.IntegrityError:
            raise ValueError(f"اسم الإصدار مكرر: '{version_name}'")

    def get_model_versions(self, limit: int = 20) -> list[dict[str, Any]]:
        """استرجاع سجل إصدارات النماذج.

        Args:
            limit: أقصى عدد نتائج.

        Returns:
            قائمة إصدارات النماذج مع مقاييس الأداء.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT id, version_name, base_model, training_samples,
                      metrics_json, created_at, notes
               FROM fine_tuned_models
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        )

        versions = []
        for row in cursor.fetchall():
            version = {
                "id": row["id"],
                "version_name": row["version_name"],
                "base_model": row["base_model"],
                "training_samples": row["training_samples"],
                "created_at": row["created_at"],
                "notes": row["notes"],
            }
            try:
                version["metrics"] = json.loads(row["metrics_json"])
            except (json.JSONDecodeError, TypeError):
                version["metrics"] = {}
            versions.append(version)

        return versions

    def get_latest_model(self) -> Optional[dict[str, Any]]:
        """الحصول على أحدث إصدار نموذج.

        Returns:
            قاموس الإصدار أو None إذا لم يوجد أي نموذج.
        """
        versions = self.get_model_versions(limit=1)
        return versions[0] if versions else None

    # ------------------------------------------------------------------
    # دورة الحياة
    # ------------------------------------------------------------------

    def close(self) -> None:
        """إغلاق اتصال قاعدة البيانات."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.debug("تم إغلاق اتصال قاعدة بيانات التعلم النشط")

    def __enter__(self) -> "ActiveLearningDB":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


# ======================================================================
# المتعلم النشط
# ======================================================================

class ActiveLearner:
    """نظام التعلم النشط لتحسين دقة OCR عبر الزمن.

    يتتبع تصحيحات المستخدم، ويُصدر بيانات تدريب عند بلوغ عتبة
    إعادة التدريب، ويسجّل إصدارات النماذج المُضبَّطة دقيقاً.

    Attributes:
        db: كائن ActiveLearningDB لإدارة التخزين.
        retrain_threshold: عتبة عدد التصحيحات لإعادة التدريب.
    """

    def __init__(
        self,
        db_path: str | Path = "data/active_learning.db",
        retrain_threshold: int = 50,
    ) -> None:
        """تهيئة المتعلم النشط.

        Args:
            db_path: مسار قاعدة بيانات SQLite.
            retrain_threshold: عدد التصحيحات المطلوب لتفعيل إعادة التدريب
                              (الافتراضي: 50).
        """
        self.db = ActiveLearningDB(db_path)
        self.retrain_threshold = retrain_threshold
        logger.info(
            "تم تهيئة المتعلم النشط (عتبة إعادة التدريب: %d)", retrain_threshold,
        )

    def log_correction(
        self,
        original_text: str,
        corrected_text: str,
        confidence: float = 0.0,
        source: str = "",
        image_data: Optional[bytes] = None,
    ) -> Optional[int]:
        """تسجيل تصحيح من المستخدم مع إلغاء التكرار.

        يُخزن التصحيح في قاعدة البيانات ويُنشئ سجل بيانات تدريب مرتبط.
        إذا كان التصحيح مكرراً، يُتجاهل بصمت.

        Args:
            original_text: النص الأصلي من OCR.
            corrected_text: التصحيح المُقدَّم من المستخدم.
            confidence: مستوى ثقة OCR الأصلية (0.0 - 1.0).
            source: محرك OCR المصدر (مثل "trocr", "easyocr").
            image_data: بيانات الصورة المرتبطة (اختياري).

        Returns:
            معرّف التصحيح أو None إذا كان مكرراً.

        Example:
            >>> learner.log_correction("hellp", "hello", confidence=0.45, source="trocr")
        """
        if not original_text.strip() or not corrected_text.strip():
            logger.warning("تم تجاهل تصحيح فارغ")
            return None

        if original_text.strip().lower() == corrected_text.strip().lower():
            logger.debug("النص الأصلي والمصحّح متطابقان — تم التجاهل")
            return None

        # إضافة إلى جدول التصحيحات
        correction_id = self.db.add_correction(
            original_text=original_text,
            corrected_text=corrected_text,
            original_confidence=confidence,
            source_engine=source,
        )

        if correction_id is not None:
            # إنشاء سجل بيانات تدريب مرتبط
            self.db.add_training_entry(
                correction_id=correction_id,
                original_text=original_text.strip(),
                corrected_text=corrected_text.strip(),
                image_data=image_data,
                source_engine=source,
            )

            # تسجيل تحذير عند اقتراب العتبة
            total = self.db.count_corrections()
            if total >= self.retrain_threshold:
                logger.info(
                    "⚠️ بلغ عدد التصحيحات %d (العتبة: %d) — يُوصى بإعادة التدريب",
                    total, self.retrain_threshold,
                )

        return correction_id

    def get_stats(self) -> dict[str, Any]:
        """الحصول على إحصائيات شاملة عن نظام التعلم النشط.

        تتضمن:
        - إجمالي التصحيحات
        - متوسط الثقة قبل التصحيح
        - عدد التصحيحات حسب المحرك
        - حالة إعادة التدريب
        - آخر إصدار نموذج

        Returns:
            قاموس يحتوي جميع الإحصائيات.

        Example:
            >>> stats = learner.get_stats()
            >>> print(f"Corrections: {stats['total_corrections']}")
        """
        corrections = self.db.get_corrections(limit=10000)
        total = len(corrections)

        if total == 0:
            return {
                "total_corrections": 0,
                "should_retrain": False,
                "retrain_threshold": self.retrain_threshold,
                "avg_confidence_before": 0.0,
                "corrections_by_engine": {},
                "confidence_distribution": {},
                "latest_model": None,
                "model_versions_count": 0,
            }

        # حساب متوسط الثقة
        confidences = [c["original_confidence"] for c in corrections if c["original_confidence"] > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # توزيع التصحيحات حسب المحرك
        by_engine: dict[str, int] = {}
        for c in corrections:
            engine = c["source_engine"] or "unknown"
            by_engine[engine] = by_engine.get(engine, 0) + 1

        # توزيع الثقة
        conf_dist: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
        for conf in confidences:
            if conf < 0.5:
                conf_dist["low"] += 1
            elif conf < 0.8:
                conf_dist["medium"] += 1
            else:
                conf_dist["high"] += 1

        # آخر إصدار نموذج
        latest_model = self.db.get_latest_model()
        all_models = self.db.get_model_versions()

        return {
            "total_corrections": total,
            "should_retrain": total >= self.retrain_threshold,
            "retrain_threshold": self.retrain_threshold,
            "retrain_progress": min(1.0, total / self.retrain_threshold) * 100,
            "avg_confidence_before": round(avg_confidence, 4),
            "corrections_by_engine": by_engine,
            "confidence_distribution": conf_dist,
            "latest_model": latest_model,
            "model_versions_count": len(all_models),
            "pending_training_samples": len(
                self.db.get_training_data(limit=100000)
            ),
        }

    def should_retrain(self) -> bool:
        """فحص هل بلغ عدد التصحيحات عتبة إعادة التدريب.

        Returns:
            True إذا وصل العدد إلى العتبة أو تجاوزها.
        """
        total = self.db.count_corrections()
        result = total >= self.retrain_threshold

        if result:
            logger.info(
                "✅ بلغ عدد التصحيحات %d/%d — جاهز لإعادة التدريب",
                total, self.retrain_threshold,
            )

        return result

    def export_training_data(
        self,
        output_path: str | Path,
        include_image_data: bool = False,
        min_confidence: float = 0.0,
    ) -> str:
        """تصدير بيانات التدريب بصيغة JSONL لضبط TrOCR الدقيق.

        كل سطر في الملف يتضمن:
        ```json
        {"original_text": "...", "corrected_text": "...", "source_engine": "..."}
        ```

        Args:
            output_path: مسار ملف JSONL المُخرَج.
            include_image_data: تضمين بيانات الصور (base64) إن وُجدت.
            min_confidence: أقل حد للثقة (لتصفية التصحيحات عالية الثقة).

        Returns:
            مسار الملف المُنشأ.

        Raises:
            ValueError: إذا لم توجد بيانات للتصدير.

        Example:
            >>> path = learner.export_training_data("training_data.jsonl")
            >>> # استخدم الملف مع transformers Trainer:
            >>> # trainer = Trainer(..., train_dataset=load_dataset("json", data_files=path))
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        corrections = self.db.get_corrections(
            min_confidence=min_confidence,
            limit=100000,
        )

        if not corrections:
            raise ValueError("لا توجد تصحيحات للتصدير")

        lines_written = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for correction in corrections:
                entry = {
                    "original_text": correction["original_text"],
                    "corrected_text": correction["corrected_text"],
                    "source_engine": correction["source_engine"],
                    "original_confidence": correction["original_confidence"],
                }

                if include_image_data:
                    # محاولة استخراج بيانات الصورة من بيانات التدريب
                    training_entries = self.db.get_training_data(limit=100000)
                    for te in training_entries:
                        if te["correction_id"] == correction["id"]:
                            # ملاحظة: بيانات الصور تُخزن كـ BLOB ولا تُصدَّر في JSONL
                            # يمكن إضافتها كـ base64 إذا لزم الأمر
                            break

                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                lines_written += 1

        logger.info(
            "تم تصدير %d سجل تدريب إلى: %s", lines_written, output_path,
        )
        return str(output_path)

    def record_model_version(
        self,
        version_name: str,
        metrics: Optional[dict[str, Any]] = None,
        notes: str = "",
        base_model: str = "",
    ) -> int:
        """تسجيل إصدار نموذج جديد بعد الضبط الدقيق.

        يُحدَّث بيانات التدريب غير المستخدمة لتكون مرتبطة بهذا الإصدار.

        Args:
            version_name: اسم الإصدار (يجب أن يكون فريداً).
            metrics: مقاييس الأداء (مثل {"cer": 0.03, "wer": 0.08}).
            notes: ملاحظات إضافية.
            base_model: اسم النموذج الأساسي قبل الضبط.

        Returns:
            معرّف الإصدار المسجّل.

        Raises:
            ValueError: إذا كان اسم الإصدار مكرراً.

        Example:
            >>> learner.record_model_version(
            ...     "trocr-ar-v2",
            ...     metrics={"cer": 0.032, "wer": 0.085, "accuracy": 0.968},
            ...     notes="ضبط على 150 عيّنة عربية يدوية",
            ... )
        """
        # تسجيل الإصدار
        model_id = self.db.add_model_version(
            version_name=version_name,
            base_model=base_model,
            training_samples=len(self.db.get_training_data(limit=100000)),
            metrics=metrics,
            notes=notes,
        )

        # تحديد بيانات التدريب المُستخدمة
        self.db.mark_training_used(version_name)

        logger.info(
            "✅ تم تسجيل إصدار النموذج '%s' (ID: %d) مع %d عيّنة تدريب",
            version_name, model_id,
            len(self.db.get_model_versions(limit=1)),
        )

        return model_id

    def get_confidence_improvement(self) -> Optional[dict[str, float]]:
        """حساب تحسّن الثقة بين إصدارات النماذج.

        يُقارن مقاييس CER/WER بين آخر إصدارين.

        Returns:
            قاموس التحسّن أو None إذا لم يوجد إصداران للمقارنة.

        Example:
            >>> improvement = learner.get_confidence_improvement()
            >>> if improvement:
            ...     print(f"CER improved by: {improvement['cer_delta']:.2%}")
        """
        versions = self.db.get_model_versions(limit=2)
        if len(versions) < 2:
            logger.debug("لا يوجد إصداران كافيان لمقارنة التحسّن")
            return None

        latest = versions[0]
        previous = versions[1]

        improvement: dict[str, float] = {}
        for metric_key in set(list(latest["metrics"].keys()) + list(previous["metrics"].keys())):
            latest_val = latest["metrics"].get(metric_key)
            prev_val = previous["metrics"].get(metric_key)

            if latest_val is not None and prev_val is not None:
                try:
                    delta = float(prev_val) - float(latest_val)
                    improvement[f"{metric_key}_delta"] = delta
                    improvement[f"{metric_key}_delta_pct"] = (
                        delta / float(prev_val) * 100 if float(prev_val) != 0 else 0.0
                    )
                except (ValueError, ZeroDivisionError):
                    continue

        if improvement:
            logger.info("تحسّن الأداء بين الإصدارات: %s", improvement)
            return improvement

        return None

    def close(self) -> None:
        """إغلاق قاعدة البيانات وتحرير الموارد."""
        self.db.close()

    def __enter__(self) -> "ActiveLearner":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
