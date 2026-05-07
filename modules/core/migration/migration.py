"""
HandwrittenOCR - وحدة ترحيل البيانات v5.1
============================================
ترحيل البيانات من النسخ القديمة للمشروع إلى النسخة الحالية.
يدعم:
- دمج قواعد البيانات القديمة (verified/sentence_corrected فقط)
- دمج ملفات التصحيحات (feedback CSV)
- إعادة بناء قاموس التصحيح من التصحيحات المدمجة
- كشف تلقائي للمجلدات القديمة على Drive/المحلي
- سجل مفصل لعملية الترحيل
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Optional

logger = logging.getLogger("HandwrittenOCR.Migration")


# أسماء المجلدات القديمة المحتملة
DEFAULT_OLD_FOLDERS = [
    "Handwriting_Dataset",
    "Handwritten_OCR_Integrated",
    "Handwritten_OCR_Pro",
    "Handwritten_OCR",
    "arabic_ocr_project",
]


class DataMigrator:
    """
    مُرحِّل البيانات من النسخ القديمة.
    يبحث في المسار المحدد عن مجلدات المشروع القديمة
    ويرحّل البيانات الموثقة (verified) والتصحيحات.
    """

    def __init__(self, config):
        """
        Args:
            config: كائن Config من config.py
        """
        self.config = config
        self.db_path = config.db_path
        self.feedback_csv = config.feedback_csv
        self.correction_dict_path = config.correction_dict_path

    def scan_old_projects(
        self,
        base_path: str = "",
        extra_folders: list[str] = None,
    ) -> list[dict]:
        """
        مسح المسار للبحث عن مشاريع قديمة.
        يُرجع قائمة بالمشاريع المكتشفة مع تفاصيلها.

        Args:
            base_path: المسار الأساسي للبحث (الافتراضي: مجلد Drive أو المنزل)
            extra_folders: مجلدات إضافية للبحث
        """
        if not base_path:
            base_path = str(Path(self.config.project_root).parent)

        search_folders = list(DEFAULT_OLD_FOLDERS)
        if extra_folders:
            search_folders.extend(extra_folders)

        # إزالة مجلد المشروع الحالي من البحث
        current_name = Path(self.config.project_root).name
        if current_name in search_folders:
            search_folders.remove(current_name)

        found = []
        base = Path(base_path)

        for folder_name in search_folders:
            folder_path = base / folder_name
            if not folder_path.exists():
                continue

            # كشف محتويات المجلد
            info = {
                "name": folder_name,
                "path": str(folder_path),
                "has_db": False,
                "db_files": [],
                "has_feedback": False,
                "feedback_files": [],
                "has_models": False,
            }

            # البحث عن قواعد بيانات
            for db_file in folder_path.rglob("*.db"):
                info["db_files"].append(str(db_file))
                info["has_db"] = True

            # البحث عن ملفات تصحيحات
            for fb_pattern in ["*feedback*.csv", "*correction*.csv", "*review*.csv"]:
                for fb_file in folder_path.rglob(fb_pattern):
                    info["feedback_files"].append(str(fb_file))
                    info["has_feedback"] = True

            # البحث عن نماذج
            if any(p.name.startswith("models") for p in folder_path.iterdir() if p.is_dir()):
                info["has_models"] = True
            if (folder_path / "models_cache").exists():
                info["has_models"] = True

            if info["has_db"] or info["has_feedback"]:
                found.append(info)

        return found

    def migrate(
        self,
        base_path: str = "",
        old_folders: list[str] = None,
        skip_existing: bool = True,
        verified_only: bool = True,
    ) -> dict:
        """
        ترحيل شامل: دمج قواعد البيانات + التصحيحات + إعادة بناء القاموس.

        Args:
            base_path: المسار الأساسي (الافتراضي: مجلد Drive أو المنزل)
            old_folders: مجلدات محددة للترحيل (بدلاً من البحث التلقائي)
            skip_existing: تخطي السجلات الموجودة مسبقاً
            verified_only: ترحيل الموثق فقط (أو كل شيء)

        Returns:
            dict مع إحصائيات الترحيل
        """
        if not base_path:
            base_path = str(Path(self.config.project_root).parent)

        if old_folders is None:
            old_folders = DEFAULT_OLD_FOLDERS

        stats = {
            "started_at": datetime.now().isoformat(),
            "base_path": base_path,
            "target_db": self.db_path,
            "folders_scanned": 0,
            "folders_found": 0,
            "db_records_migrated": 0,
            "feedback_merged": 0,
            "correction_dict_entries": 0,
            "errors": [],
            "details": {},
        }

        logger.info(f"بدء الترحيل من: {base_path}")

        # 1. التأكد من وجود قاعدة البيانات الهدف
        target_dir = Path(self.db_path).parent
        target_dir.mkdir(parents=True, exist_ok=True)

        # 2. دمج قواعد البيانات
        for folder_name in old_folders:
            folder_path = Path(base_path) / folder_name
            if not folder_path.exists():
                continue

            stats["folders_scanned"] += 1
            folder_stats = {"db_files": 0, "records": 0, "errors": []}

            for db_file in folder_path.rglob("*.db"):
                try:
                    migrated = self._migrate_db(
                        src_db=str(db_file),
                        tgt_db=self.db_path,
                        source_label=folder_name,
                        skip_existing=skip_existing,
                        verified_only=verified_only,
                    )
                    folder_stats["db_files"] += 1
                    folder_stats["records"] += migrated
                    stats["db_records_migrated"] += migrated
                except Exception as e:
                    err_msg = f"DB {db_file.name}: {e}"
                    folder_stats["errors"].append(err_msg)
                    stats["errors"].append(err_msg)
                    logger.warning(f"خطأ في ترحيل {db_file}: {e}")

            if folder_stats["db_files"] > 0:
                stats["folders_found"] += 1
                stats["details"][folder_name] = folder_stats

        # 3. دمج ملفات التصحيحات
        total_feedback = self._merge_feedback_files(
            base_path=base_path,
            old_folders=old_folders,
        )
        stats["feedback_merged"] = total_feedback

        # 4. إعادة بناء قاموس التصحيح
        dict_count = self._rebuild_correction_dict()
        stats["correction_dict_entries"] = dict_count

        stats["ended_at"] = datetime.now().isoformat()
        logger.info(
            f"اكتمل الترحيل: {stats['db_records_migrated']} كلمة + "
            f"{stats['feedback_merged']} تصحيح + "
            f"{stats['correction_dict_entries']} قاموس"
        )

        return stats

    def _migrate_db(
        self,
        src_db: str,
        tgt_db: str,
        source_label: str = "unknown",
        skip_existing: bool = True,
        verified_only: bool = True,
    ) -> int:
        """
        ترحيل سجلات من قاعدة بيانات مصدر إلى قاعدة بيانات هدف.

        Corrections applied:
        - Status 'yes' -> 'verified', 'no' -> 'unverified'
        - Only migrates verified data by default
        - Handles missing columns gracefully
        """
        src_conn = sqlite3.connect(src_db)
        tgt_conn = sqlite3.connect(tgt_db)
        src_cur = src_conn.cursor()
        tgt_cur = tgt_conn.cursor()

        migrated = 0

        try:
            # كشف أعمدة الجدول المصدر
            src_cur.execute("PRAGMA table_info(handwriting_data)")
            src_cols = {r[1] for r in src_cur.fetchall()}

            # كشف أعمدة الجدول الهدف
            tgt_cur.execute("PRAGMA table_info(handwriting_data)")
            tgt_cols = {r[1] for r in tgt_cur.fetchall()}

            # بناء الاستعلام بناءً على الأعمدة المتوفرة في المصدر
            select_cols = []
            for col in ["image_data", "predicted_text", "status", "confidence",
                        "model_source", "x", "y", "w", "h", "page_num"]:
                if col in src_cols:
                    select_cols.append(col)

            # إضافة raw_text إذا وجد
            if "raw_text" in src_cols:
                select_cols.append("raw_text")
            elif "raw_text" not in select_cols:
                # no raw_text column - will use NULL
                pass

            # إضافة created_at/updated_at إذا وجدت
            has_created = "created_at" in src_cols
            has_updated = "updated_at" in src_cols
            if has_created:
                select_cols.append("created_at")
            if has_updated:
                select_cols.append("updated_at")

            cols_str = ", ".join(select_cols)
            placeholders = ", ".join(["?"] * len(select_cols))

            # بناء شرط WHERE
            where_clause = ""
            params = []
            if verified_only:
                # شمل verified, sentence_corrected, yes (قديم)
                where_clause = "WHERE status IN ('verified', 'sentence_corrected', 'yes')"
            else:
                where_clause = "WHERE 1=1"

            query = f"SELECT {cols_str} FROM handwriting_data {where_clause}"

            try:
                src_cur.execute(query)
            except Exception:
                # إذا فشل الاستعلام بسبب أعمدة مفقودة، استخدم استعلام بسيط
                src_cur.execute(
                    "SELECT image_data, predicted_text, status, confidence "
                    "FROM handwriting_data"
                )
                select_cols = ["image_data", "predicted_text", "status", "confidence"]
                placeholders = ", ".join(["?"] * 4)
                has_created = False
                has_updated = False

            rows = src_cur.fetchall()

            for row in rows:
                try:
                    row_dict = dict(zip(select_cols, row))

                    # تطبيع قيم status القديمة (Correction #10)
                    status = row_dict.get("status", "unverified")
                    if status == "yes":
                        status = "verified"
                    elif status == "no":
                        status = "unverified"
                    row_dict["status"] = status

                    # التحقق من وجود السجل (تخطي التكرارات)
                    if skip_existing:
                        predicted = row_dict.get("predicted_text", "")
                        page = row_dict.get("page_num", 0)
                        check = tgt_cur.execute(
                            "SELECT image_id FROM handwriting_data "
                            "WHERE predicted_text = ? AND page_num = ? LIMIT 1",
                            (predicted, page),
                        ).fetchone()
                        if check:
                            continue

                    # بناء INSERT مع الأعمدة المتوفرة في الهدف
                    now = datetime.now().isoformat()
                    insert_cols = []
                    insert_vals = []

                    for col in ["image_data", "predicted_text", "raw_text",
                                "status", "confidence", "model_source",
                                "x", "y", "w", "h", "page_num"]:
                        if col in tgt_cols:
                            val = row_dict.get(col)
                            if val is None and col == "raw_text":
                                val = row_dict.get("predicted_text", "")
                            if val is None:
                                if col in ("x", "y", "w", "h", "page_num"):
                                    val = 0
                                elif col == "confidence":
                                    val = 0.0
                                elif col == "status":
                                    val = "unverified"
                                elif col == "model_source":
                                    val = "none"
                                else:
                                    val = ""
                            insert_cols.append(col)
                            insert_vals.append(val)

                    # إضافة run_id و timestamps
                    if "run_id" in tgt_cols:
                        insert_cols.append("run_id")
                        insert_vals.append(f"migrated_{source_label}")
                    if "created_at" in tgt_cols:
                        insert_cols.append("created_at")
                        insert_vals.append(
                            row_dict.get("created_at", now) if has_created else now
                        )
                    if "updated_at" in tgt_cols:
                        insert_cols.append("updated_at")
                        insert_vals.append(
                            row_dict.get("updated_at", now) if has_updated else now
                        )

                    insert_str = ", ".join(insert_cols)
                    insert_ph = ", ".join(["?"] * len(insert_vals))

                    tgt_cur.execute(
                        f"INSERT INTO handwriting_data ({insert_str}) VALUES ({insert_ph})",
                        insert_vals,
                    )
                    migrated += 1

                except Exception as e:
                    logger.debug(f"تخطي سجل: {e}")
                    continue

            tgt_conn.commit()

        finally:
            src_conn.close()
            tgt_conn.close()

        return migrated

    def _merge_feedback_files(
        self,
        base_path: str,
        old_folders: list[str],
    ) -> int:
        """دمج ملفات التصحيحات من المجلدات القديمة"""
        import pandas as pd

        all_feedback = []

        for folder_name in old_folders:
            folder_path = Path(base_path) / folder_name
            if not folder_path.exists():
                continue

            for pattern in ["*feedback*.csv", "*correction*.csv", "*review*.csv"]:
                for fb_file in folder_path.rglob(pattern):
                    try:
                        df = pd.read_csv(str(fb_file), encoding="utf-8-sig")
                        if df.empty:
                            continue

                        # التأكد من الأعمدة المطلوبة
                        required = {"original_text", "corrected_text"}
                        if not required.issubset(set(df.columns)):
                            continue

                        # إضافة مصدر الترحيل
                        df["migration_source"] = folder_name
                        all_feedback.append(df)
                    except Exception as e:
                        logger.debug(f"تخطي ملف تصحيحات {fb_file}: {e}")

        if not all_feedback:
            return 0

        # دمج وإزالة التكرارات
        merged = pd.concat(all_feedback, ignore_index=True)
        before = len(merged)

        # إزالة التكرارات (نفس original + corrected)
        merged = merged.drop_duplicates(
            subset=["original_text", "corrected_text"],
            keep="last",
        )

        # إزالة الأسطر الفارغة
        merged = merged.dropna(subset=["original_text", "corrected_text"])
        merged = merged[merged["original_text"].astype(str).str.strip() != ""]
        merged = merged[merged["corrected_text"].astype(str).str.strip() != ""]
        merged = merged[merged["original_text"] != merged["corrected_text"]]

        # التأكد من وجود ملف الهدف
        Path(self.feedback_csv).parent.mkdir(parents=True, exist_ok=True)

        # دمج مع ملف التصحيحات الحالي
        target_df = pd.DataFrame()
        if os.path.exists(self.feedback_csv):
            try:
                target_df = pd.read_csv(self.feedback_csv, encoding="utf-8-sig")
            except Exception:
                pass

        if not target_df.empty:
            # إزالة عمود migration_source من التصحيحات الحالية
            if "migration_source" in target_df.columns:
                target_df = target_df.drop(columns=["migration_source"])

            # إزالة migration_source قبل الدمج النهائي
            merge_df = merged.drop(columns=["migration_source"], errors="ignore")
            combined = pd.concat([target_df, merge_df], ignore_index=True)
            combined = combined.drop_duplicates(
                subset=["original_text", "corrected_text"],
                keep="last",
            )
        else:
            combined = merged.drop(columns=["migration_source"], errors="ignore")

        # حفظ
        combined.to_csv(
            self.feedback_csv,
            index=False,
            encoding="utf-8-sig",
        )

        return len(combined) - len(target_df) if not target_df.empty else len(combined)

    def _rebuild_correction_dict(self) -> int:
        """إعادة بناء قاموس التصحيح من جميع التصحيحات"""
        import pandas as pd

        dict_path = Path(self.correction_dict_path)
        dict_path.parent.mkdir(parents=True, exist_ok=True)

        # تحميل التصحيحات الموجودة
        if not os.path.exists(self.feedback_csv):
            return 0

        try:
            df = pd.read_csv(self.feedback_csv, encoding="utf-8-sig")
        except Exception:
            return 0

        if df.empty:
            return 0

        # بناء قاموس (Correction #1: min_votes)
        buckets = defaultdict(Counter)
        min_votes = self.config.correction_min_votes  # Correction #10: 1 not 2

        for _, row in df.iterrows():
            o = str(row.get("original_text", "")).strip()
            c = str(row.get("corrected_text", "")).strip()
            if o and c and o != c:
                buckets[o][c] += 1

        # اختيار التصحيح الأكثر شيوعاً لكل كلمة
        correction_dict = {}
        for original, counter in buckets.items():
            if counter:
                top_correction, top_count = counter.most_common(1)[0]
                if top_count >= min_votes:
                    correction_dict[original] = top_correction

        # حفظ
        with open(dict_path, "w", encoding="utf-8") as f:
            json.dump(correction_dict, f, ensure_ascii=False, indent=2)

        logger.info(f"تم بناء قاموس التصحيح: {len(correction_dict)} إدخال")
        return len(correction_dict)

    def scan_and_report(self, base_path: str = "") -> dict:
        """فحص سريع يُرجع تقرير بالمشاريع القديمة المتاحة"""
        projects = self.scan_old_projects(base_path=base_path)

        return {
            "scanned_at": datetime.now().isoformat(),
            "base_path": base_path or str(Path(self.config.project_root).parent),
            "projects_found": len(projects),
            "projects": projects,
            "total_db_files": sum(len(p.get("db_files", [])) for p in projects),
            "total_feedback_files": sum(len(p.get("feedback_files", [])) for p in projects),
        }


# === Compatibility alias for OmniFile_v500_Colab ===
MigrationManager = DataMigrator
