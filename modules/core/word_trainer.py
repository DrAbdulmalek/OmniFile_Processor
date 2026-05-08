"""
modules/core/word_trainer.py
══════════════════════════════
محرك التعلم من تصحيحات المستخدم — Word-Level OCR Trainer
==========================================================
يتعلم من تصحيحات المستخدم ليحسّن توقعات OCR بشكل مستمر.

الميزات:
  ✅ قاعدة بيانات SQLite للتصحيحات (كلمة + ثقة + لغة + طابع زمني)
  ✅ تتبع تكرار الكلمات لاقتراحات ذكية
  ✅ اقتراح تصحيح بناءً على سجل التعلم
  ✅ تحديث arabic_fixes.json تلقائياً بعد كل حفظ
  ✅ تصدير كـ JSON للمزامنة مع GitHub و Google Drive
  ✅ تراجع (Undo) عن آخر دفعة محفوظة
  ✅ حذف كلمات عديمة المعنى

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import json
import logging
import sqlite3
from datetime import datetime
from difflib import get_close_matches, SequenceMatcher
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH             = "artifacts/corrections.db"
ARABIC_FIXES_PATH   = "data/arabic_fixes.json"
EXPORT_JSON_PATH    = "artifacts/corrections_db_export.json"

# ── حد التعلم: كم مرة لازم يُصحَّح الخطأ حتى يُضاف للقاموس ─────────
LEARN_THRESHOLD = 2


class WordCorrectionDB:
    """
    قاعدة بيانات SQLite لتصحيحات المستخدم.

    مثال:
        db = WordCorrectionDB()
        db.save_batch([
            {"idx":0,"predicted":"مرحبا","corrected":"مرحباً","lang":"ar","confidence":0.72},
            {"idx":1,"predicted":"world","corrected":"world","lang":"en","confidence":0.95},
        ])
        db.undo_last()
        suggestions = db.get_suggestions("مرح", lang="ar")
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── تهيئة قاعدة البيانات ─────────────────────────────────────────

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS corrections (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id    TEXT,
                    image_hash  TEXT    DEFAULT '',
                    word_idx    INTEGER DEFAULT 0,
                    predicted   TEXT    NOT NULL,
                    corrected   TEXT    NOT NULL,
                    lang        TEXT    DEFAULT 'ar',
                    confidence  REAL    DEFAULT 0.0,
                    is_improved INTEGER DEFAULT 0,
                    created_at  TEXT    DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS word_freq (
                    id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    word  TEXT NOT NULL,
                    lang  TEXT DEFAULT 'ar',
                    count INTEGER DEFAULT 1,
                    UNIQUE(word, lang)
                );

                CREATE INDEX IF NOT EXISTS idx_corrections_lang   ON corrections(lang);
                CREATE INDEX IF NOT EXISTS idx_corrections_batch  ON corrections(batch_id);
                CREATE INDEX IF NOT EXISTS idx_word_freq_lang     ON word_freq(lang, count);
            """)
            conn.commit()

    # ── الحفظ ──────────────────────────────────────────────────────────

    def save_batch(
        self,
        items: list[dict],
        image_hash: str = "",
        batch_id: str = "",
    ) -> int:
        """
        حفظ دفعة تصحيحات من جلسة واحدة.

        Args:
            items:      قائمة dicts: {idx, predicted, corrected, lang, confidence}
            image_hash: بصمة الصورة المصدر
            batch_id:   معرّف الدفعة (للتراجع)

        Returns:
            عدد العناصر المحفوظة
        """
        if not batch_id:
            batch_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        saved = 0
        with sqlite3.connect(self.db_path) as conn:
            for item in items:
                predicted  = (item.get("predicted")  or "").strip()
                corrected  = (item.get("corrected")  or "").strip()
                lang       = item.get("lang",       "ar")
                confidence = float(item.get("confidence", 0.0))
                idx        = int(item.get("idx", 0))

                if not corrected:          # كلمة فارغة → تجاهل
                    continue
                if item.get("deleted"):    # محددة للحذف
                    continue

                is_improved = int(predicted != corrected)

                conn.execute("""
                    INSERT INTO corrections
                    (batch_id, image_hash, word_idx, predicted, corrected, lang, confidence, is_improved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (batch_id, image_hash, idx, predicted, corrected,
                      lang, confidence, is_improved))

                # تحديث تكرار الكلمة
                conn.execute("""
                    INSERT INTO word_freq (word, lang, count) VALUES (?, ?, 1)
                    ON CONFLICT(word, lang) DO UPDATE SET count = count + 1
                """, (corrected, lang))

                saved += 1
            conn.commit()

        logger.info("WordCorrectionDB: saved %d corrections (batch=%s)", saved, batch_id)

        # تحديث arabic_fixes بعد كل حفظ
        if any(i.get("lang","ar") == "ar" for i in items):
            self.update_arabic_fixes()

        return saved

    # ── التراجع ─────────────────────────────────────────────────────────

    def undo_last_batch(self) -> tuple[int, str]:
        """
        حذف آخر دفعة محفوظة (التراجع).

        Returns:
            (عدد الصفوف المحذوفة, batch_id)
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT batch_id FROM corrections ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not row:
                return 0, ""
            bid = row[0]
            cnt = conn.execute(
                "SELECT COUNT(*) FROM corrections WHERE batch_id=?", (bid,)
            ).fetchone()[0]
            conn.execute("DELETE FROM corrections WHERE batch_id=?", (bid,))
            conn.commit()
        logger.info("Undo: deleted batch=%s (%d rows)", bid, cnt)
        return cnt, bid

    def delete_correction(self, correction_id: int) -> bool:
        """حذف تصحيح واحد بمعرّفه."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM corrections WHERE id=?", (correction_id,))
            conn.commit()
        return True

    # ── الاقتراحات ──────────────────────────────────────────────────────

    def get_suggestions(self, partial: str, lang: str = "ar", n: int = 5) -> list[str]:
        """
        اقتراحات كلمات بناءً على التكرار والتشابه.

        Args:
            partial: الكلمة أو جزء منها
            lang:    اللغة
            n:       عدد الاقتراحات

        Returns:
            قائمة الاقتراحات مرتبة بالتشابه
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT word FROM word_freq WHERE lang=? ORDER BY count DESC LIMIT 300
            """, (lang,)).fetchall()

        words = [r[0] for r in rows]
        if not words or not partial:
            return []

        return get_close_matches(partial, words, n=n, cutoff=0.45)

    def get_best_correction(self, predicted: str, lang: str = "ar") -> Optional[str]:
        """
        أفضل تصحيح متعلَّم لكلمة متوقعة معينة.

        Returns:
            الكلمة المصحَّحة الأكثر تكراراً، أو None إذا لم يوجد
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT corrected, COUNT(*) AS cnt
                FROM corrections
                WHERE predicted=? AND lang=? AND is_improved=1
                GROUP BY corrected
                ORDER BY cnt DESC LIMIT 1
            """, (predicted, lang)).fetchone()
        return row[0] if row else None

    # ── الاستعراض ────────────────────────────────────────────────────────

    def get_corrections(
        self,
        limit: int = 200,
        lang: Optional[str] = None,
        improved_only: bool = False,
    ) -> list[dict]:
        """استرجاع التصحيحات المحفوظة."""
        with sqlite3.connect(self.db_path) as conn:
            conds, params = [], []
            if lang:
                conds.append("lang=?"); params.append(lang)
            if improved_only:
                conds.append("is_improved=1")
            where = ("WHERE " + " AND ".join(conds)) if conds else ""
            params.append(limit)
            rows = conn.execute(f"""
                SELECT id, batch_id, predicted, corrected, lang, confidence, is_improved, created_at
                FROM corrections {where} ORDER BY id DESC LIMIT ?
            """, params).fetchall()
        return [
            {"id": r[0], "batch_id": r[1], "predicted": r[2],
             "corrected": r[3], "lang": r[4], "confidence": r[5],
             "improved": bool(r[6]), "created_at": r[7]}
            for r in rows
        ]

    def stats(self) -> dict:
        """إحصائيات قاعدة البيانات."""
        with sqlite3.connect(self.db_path) as conn:
            total    = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
            improved = conn.execute("SELECT COUNT(*) FROM corrections WHERE is_improved=1").fetchone()[0]
            by_lang  = dict(conn.execute("SELECT lang, COUNT(*) FROM corrections GROUP BY lang").fetchall())
            batches  = conn.execute("SELECT COUNT(DISTINCT batch_id) FROM corrections").fetchone()[0]
            top_w    = conn.execute("""
                SELECT word, lang, count FROM word_freq ORDER BY count DESC LIMIT 10
            """).fetchall()
        acc = (1 - improved / max(total, 1)) * 100
        return {
            "total_corrections": total,
            "corrections_improved": improved,
            "accuracy_rate": f"{acc:.1f}%",
            "sessions": batches,
            "by_language": by_lang,
            "top_words": [{"word": w, "lang": l, "count": c} for w, l, c in top_w],
        }

    # ── التصدير ─────────────────────────────────────────────────────────

    def export_json(self, path: str = EXPORT_JSON_PATH) -> str:
        """تصدير كامل قاعدة البيانات كـ JSON."""
        data  = self.get_corrections(limit=50000)
        stats = self.stats()
        pkg   = {
            "omnifile_version": "5.0",
            "exported_at":      datetime.now().isoformat(),
            "stats":            stats,
            "corrections":      data,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(pkg, f, ensure_ascii=False, indent=2)
        return path

    # ── التعلم التلقائي ───────────────────────────────────────────────

    def update_arabic_fixes(self, path: str = ARABIC_FIXES_PATH) -> int:
        """
        تحديث arabic_fixes.json بالتصحيحات المتكررة.
        يضيف فقط الأخطاء التي صُحِّحت >= LEARN_THRESHOLD مرات.
        """
        try:
            existing = {}
            if Path(path).exists():
                with open(path, encoding="utf-8") as f:
                    existing = json.load(f)

            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(f"""
                    SELECT predicted, corrected, COUNT(*) AS cnt
                    FROM corrections
                    WHERE lang='ar' AND is_improved=1
                    GROUP BY predicted, corrected
                    HAVING cnt >= {LEARN_THRESHOLD}
                    ORDER BY cnt DESC
                """).fetchall()

            new_fixes = {r[0]: r[1] for r in rows}
            existing.update(new_fixes)

            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            logger.info("arabic_fixes updated: +%d entries (total %d)", len(new_fixes), len(existing))
            return len(new_fixes)
        except Exception as e:
            logger.error("update_arabic_fixes: %s", e)
            return 0
