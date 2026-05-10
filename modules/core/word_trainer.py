"""
modules/core/word_trainer.py
══════════════════════════════
محرك التعلم من تصحيحات المستخدم — Word-Level OCR Trainer
v6.0: مُرحَّل إلى BaseDB
==========================================================
OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import json
import logging
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from typing import Optional

from modules.core.base_db import BaseDB

logger = logging.getLogger(__name__)

ARABIC_FIXES_PATH = "data/arabic_fixes.json"
EXPORT_JSON_PATH  = "artifacts/corrections_db_export.json"
LEARN_THRESHOLD   = 2


class WordCorrectionDB(BaseDB):
    """
    قاعدة بيانات تصحيحات OCR — يرث من BaseDB.

    مثال:
        db = WordCorrectionDB()
        db.save_batch([{"idx":0,"predicted":"مرحبا","corrected":"مرحباً","lang":"ar","confidence":0.72}])
        best = db.get_best_correction("مرحبا", "ar")
        cnt, bid = db.undo_last_batch()
    """

    def __init__(self, db_path: str = "artifacts/corrections.db") -> None:
        super().__init__(db_path)

    # ── Schema ──────────────────────────────────────────────────────

    def _create_schema(self, conn) -> None:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS corrections (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id    TEXT    DEFAULT '',
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

            CREATE INDEX IF NOT EXISTS idx_corr_lang    ON corrections(lang);
            CREATE INDEX IF NOT EXISTS idx_corr_batch   ON corrections(batch_id);
            CREATE INDEX IF NOT EXISTS idx_corr_pred    ON corrections(predicted, lang);
            CREATE INDEX IF NOT EXISTS idx_freq_lang    ON word_freq(lang, count);
        """)

    # ── الحفظ ───────────────────────────────────────────────────────

    def save_batch(
        self,
        items: list,
        image_hash: str = "",
        batch_id:   str = "",
    ) -> int:
        """حفظ دفعة تصحيحات من جلسة واحدة."""
        if not batch_id:
            batch_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        saved = 0
        with self.connection() as conn:
            for item in items:
                predicted  = (item.get("predicted")  or "").strip()
                corrected  = (item.get("corrected")  or "").strip()
                lang       = item.get("lang", "ar")
                confidence = float(item.get("confidence", 0.0))
                idx        = int(item.get("idx", 0))

                if not corrected or item.get("deleted"):
                    continue

                is_improved = int(predicted != corrected)
                conn.execute("""
                    INSERT INTO corrections
                    (batch_id,image_hash,word_idx,predicted,corrected,lang,confidence,is_improved)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (batch_id, image_hash, idx, predicted, corrected, lang, confidence, is_improved))

                conn.execute("""
                    INSERT INTO word_freq(word,lang,count) VALUES(?,?,1)
                    ON CONFLICT(word,lang) DO UPDATE SET count=count+1
                """, (corrected, lang))

                saved += 1

        logger.info("WordCorrectionDB: saved %d (batch=%s)", saved, batch_id)

        if any(i.get("lang","ar") == "ar" for i in items):
            self.update_arabic_fixes()

        return saved

    # ── التراجع ─────────────────────────────────────────────────────

    def undo_last_batch(self) -> tuple:
        """تراجع عن آخر دفعة. Returns: (count, batch_id)"""
        row = self.execute_one(
            "SELECT batch_id FROM corrections ORDER BY id DESC LIMIT 1"
        )
        if not row:
            return 0, ""
        bid = row["batch_id"]
        cnt = self.count("corrections", "batch_id=?", (bid,))
        with self.connection() as conn:
            conn.execute("DELETE FROM corrections WHERE batch_id=?", (bid,))
        logger.info("Undo: batch=%s (%d rows)", bid, cnt)
        return cnt, bid

    def delete_correction(self, correction_id: int) -> bool:
        self.execute_write("DELETE FROM corrections WHERE id=?", (correction_id,))
        return True

    # ── الاقتراحات ──────────────────────────────────────────────────

    def get_suggestions(self, partial: str, lang: str = "ar", n: int = 5) -> list:
        rows = self.execute(
            "SELECT word FROM word_freq WHERE lang=? ORDER BY count DESC LIMIT 300",
            (lang,)
        )
        words = [r["word"] for r in rows]
        return get_close_matches(partial, words, n=n, cutoff=0.45) if words and partial else []

    def get_best_correction(self, predicted: str, lang: str = "ar") -> Optional[str]:
        row = self.execute_one("""
            SELECT corrected, COUNT(*) AS cnt
            FROM corrections
            WHERE predicted=? AND lang=? AND is_improved=1
            GROUP BY corrected ORDER BY cnt DESC LIMIT 1
        """, (predicted, lang))
        return row["corrected"] if row else None

    # ── الاسترجاع ───────────────────────────────────────────────────

    def get_corrections(
        self,
        limit:        int  = 200,
        lang:         Optional[str] = None,
        improved_only: bool = False,
    ) -> list:
        conds, params = [], []
        if lang:
            conds.append("lang=?"); params.append(lang)
        if improved_only:
            conds.append("is_improved=1")
        where  = ("WHERE " + " AND ".join(conds)) if conds else ""
        params.append(limit)
        return self.execute(f"""
            SELECT id,batch_id,predicted,corrected,lang,confidence,is_improved,created_at
            FROM corrections {where} ORDER BY id DESC LIMIT ?
        """, tuple(params))

    def stats(self) -> dict:
        total    = self.count("corrections")
        improved = self.count("corrections", "is_improved=1")
        batches  = self.execute_one("SELECT COUNT(DISTINCT batch_id) AS n FROM corrections")
        by_lang  = {r["lang"]: r["n"] for r in self.execute(
            "SELECT lang, COUNT(*) AS n FROM corrections GROUP BY lang"
        )}
        top_w    = self.execute(
            "SELECT word,lang,count FROM word_freq ORDER BY count DESC LIMIT 10"
        )
        acc = (1 - improved / max(total, 1)) * 100
        return {
            "total_corrections":    total,
            "corrections_improved": improved,
            "accuracy_rate":        f"{acc:.1f}%",
            "sessions":             batches["n"] if batches else 0,
            "by_language":          by_lang,
            "top_words":            top_w,
        }

    # ── التصدير ─────────────────────────────────────────────────────

    def export_json(self, path: str = EXPORT_JSON_PATH) -> str:
        data  = self.get_corrections(limit=50000)
        s     = self.stats()
        pkg   = {
            "omnifile_version": "5.0",
            "exported_at":      datetime.now().isoformat(),
            "stats":            s,
            "corrections":      data,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(pkg, f, ensure_ascii=False, indent=2)
        return path

    # ── التعلم التلقائي ──────────────────────────────────────────────

    def update_arabic_fixes(self, path: str = ARABIC_FIXES_PATH) -> int:
        """تحديث arabic_fixes.json بالتصحيحات المتكررة (>= LEARN_THRESHOLD)."""
        try:
            existing = {}
            if Path(path).exists():
                with open(path, encoding="utf-8") as f:
                    existing = json.load(f)

            rows = self.execute(f"""
                SELECT predicted, corrected, COUNT(*) AS cnt
                FROM corrections
                WHERE lang='ar' AND is_improved=1
                GROUP BY predicted, corrected
                HAVING cnt >= {LEARN_THRESHOLD}
                ORDER BY cnt DESC
            """)
            new_fixes = {r["predicted"]: r["corrected"] for r in rows}
            existing.update(new_fixes)

            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            logger.info("arabic_fixes: +%d new entries (total %d)", len(new_fixes), len(existing))
            return len(new_fixes)
        except Exception as e:
            logger.error("update_arabic_fixes: %s", e)
            return 0
