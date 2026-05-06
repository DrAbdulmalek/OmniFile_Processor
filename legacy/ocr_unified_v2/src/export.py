"""
HandwrittenOCR - تصدير بيانات التدريب ورفع إلى HuggingFace v4.0
====================================================================
المحسنات:
- auto_export(): CSV + XLSX + نص كامل + JSONL تدريب
- create_backup(): نسخ احتياطي شامل
- push_to_huggingface(): مع commit_message يحتوي التاريخ
"""

import os
import json
import random
import shutil
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger("HandwrittenOCR")


def auto_export(
    db,
    run_id: str,
    output_dir: str = None,
    config=None,
) -> dict:
    """
    تصدير تلقائي شامل: CSV + XLSX + النص الكامل + JSONL تدريب.

    Parameters:
        db: كائن قاعدة البيانات
        run_id: معرف التشغيل
        output_dir: مجلد الإخراج (اختياري)
        config: كائن الإعدادات (اختياري)

    Returns:
        ملخص التصدير {files, total_words, verified, ...}
    """
    if output_dir is None:
        if config:
            output_dir = os.path.join(config.exports_dir, "auto", run_id)
        else:
            output_dir = os.path.join("exports", "auto", run_id)

    os.makedirs(output_dir, exist_ok=True)

    # جلب البيانات
    words = db.get_all()
    if not words:
        logger.warning("لا توجد بيانات للتصدير")
        return {}

    df_all = pd.DataFrame(words)
    df_verified = df_all[
        df_all["status"].isin(["verified", "sentence_corrected"])
    ]
    df_csv = df_all.drop(columns=["image_data"], errors="ignore")

    exported = {}

    # --- CSV ---
    csv_path = os.path.join(output_dir, "all_words.csv")
    df_csv.to_csv(csv_path, index=False, encoding="utf-8-sig")
    exported["csv"] = csv_path

    # --- XLSX (مع ورقة لكل صفحة) ---
    try:
        xlsx_path = os.path.join(output_dir, "all_words.xlsx")
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df_csv.to_excel(writer, sheet_name="All", index=False)
            for pg in sorted(df_csv["page_num"].dropna().unique()):
                page_df = df_csv[df_csv["page_num"] == pg]
                page_df.to_excel(writer, sheet_name=f"P{int(pg)}", index=False)
        exported["xlsx"] = xlsx_path
    except ImportError:
        logger.warning("openpyxl غير مثبت - تخطي XLSX")

    # --- النص الكامل المُعاد بناؤه ---
    try:
        from src.reconstruction import reconstruct_sentences_direct
        text_lines = reconstruct_sentences_direct(df_all)
        text_path = os.path.join(output_dir, "reconstructed_text.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("\n".join(text_lines))
        exported["text"] = text_path
    except Exception as e:
        logger.warning(f"فشل إعادة بناء النص: {e}")

    # --- JSONL للتدريب ---
    if not df_verified.empty:
        img_dir = os.path.join(output_dir, "training_images")
        os.makedirs(img_dir, exist_ok=True)
        records = []
        for _, row in df_verified.iterrows():
            fname = f"img_{row['image_id']}.png"
            with open(os.path.join(img_dir, fname), "wb") as f:
                f.write(row["image_data"])
            txt = (row["predicted_text"] or "").strip()
            if txt:
                records.append({"image": fname, "text": txt})

        jsonl_path = os.path.join(output_dir, "training_data.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        exported["jsonl"] = jsonl_path
        exported["training_samples"] = len(records)

    summary = {
        "run_id": run_id,
        "exported_at": datetime.now().isoformat(),
        "total_words": len(df_all),
        "verified": len(df_verified),
        "dir": output_dir,
        "files": exported,
    }

    summary_path = os.path.join(output_dir, "export_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    logger.info(f"تم التصدير التلقائي: {output_dir}")
    return summary


def export_finetuning_dataset(
    db,
    output_dir: str,
    val_ratio: float = 0.1,
) -> str | None:
    """
    تصدير البيانات الموثقة كبيانات تدريب JSONL مع train/val split.

    Parameters:
        db: كائن قاعدة البيانات
        output_dir: مجلد الإخراج
        val_ratio: نسبة بيانات التحقق

    Returns:
        مسار مجلد الإخراج أو None
    """
    verified = db.get_verified()
    verified = [
        w for w in verified
        if w.get("status") in ("verified", "sentence_corrected")
    ]

    if not verified:
        logger.warning("لا توجد بيانات موثقة للتصدير")
        return None

    os.makedirs(output_dir, exist_ok=True)
    img_dir = os.path.join(output_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    jsonl_records = []
    for row in verified:
        filename = f"img_{row['image_id']}.png"
        filepath = os.path.join(img_dir, filename)
        with open(filepath, "wb") as f:
            f.write(row["image_data"])

        text = (row["predicted_text"] or "").strip()
        if text:
            jsonl_records.append({"image": filename, "text": text})

    if not jsonl_records:
        return None

    random.shuffle(jsonl_records)
    split_idx = int(len(jsonl_records) * (1 - val_ratio))
    train_data = jsonl_records[:split_idx]
    val_data = jsonl_records[split_idx:]

    def save_jsonl(data, fname):
        path = os.path.join(output_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            for rec in data:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return path

    train_path = save_jsonl(train_data, "train.jsonl")
    val_path = save_jsonl(val_data, "val.jsonl")

    logger.info(
        f"تم التصدير: {len(jsonl_records)} عينة "
        f"(train={len(train_data)}, val={len(val_data)})"
    )
    return output_dir


def create_backup(config) -> str:
    """
    إنشاء نسخة احتياطية شاملة.
    — بدون استخدام !cp (تصحيح #1)
    """
    label = datetime.now().strftime("%Y%m%d_%H%M%S")
    bk_dir = os.path.join(config.backups_dir, f"backup_{label}")
    os.makedirs(bk_dir, exist_ok=True)

    files_to_backup = [
        config.db_path,
        config.feedback_csv,
        config.stats_json,
        config.correction_dict_path,
        config.events_jsonl,
    ]

    for p in files_to_backup:
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(bk_dir, os.path.basename(p)))

    # نسخ مجلد artifacts إذا وُجد
    artifacts = config.artifacts_dir
    if os.path.isdir(artifacts):
        dest = os.path.join(bk_dir, "artifacts")
        if not os.path.exists(dest):
            shutil.copytree(artifacts, dest)

    logger.info(f"تم إنشاء نسخة احتياطية: {bk_dir}")
    return bk_dir


def push_to_huggingface(
    local_dataset_dir: str,
    hf_repo_id: str,
    hf_token: str = "",
    commit_message: str = "",
) -> bool:
    """
    رفع البيانات الموثقة إلى HuggingFace Hub.
    مع commit_message يحتوي التاريخ.
    """
    try:
        from huggingface_hub import HfApi, login
    except ImportError:
        logger.error("huggingface_hub غير مثبت")
        return False

    if not os.path.exists(local_dataset_dir):
        logger.error(f"المجلد غير موجود: {local_dataset_dir}")
        return False

    if hf_token:
        try:
            login(token=hf_token)
        except Exception as e:
            logger.error(f"فشل تسجيل الدخول: {e}")
            return False

    api = HfApi()

    try:
        api.create_repo(
            repo_id=hf_repo_id, repo_type="dataset", exist_ok=True
        )
    except Exception:
        pass

    # commit_message مع التاريخ
    if not commit_message:
        commit_message = f"Update dataset - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    try:
        api.upload_folder(
            folder_path=local_dataset_dir,
            repo_id=hf_repo_id,
            repo_type="dataset",
            commit_message=commit_message,
        )
        url = f"https://huggingface.co/datasets/{hf_repo_id}"
        logger.info(f"تم رفع البيانات إلى {url}")
        return True
    except Exception as e:
        logger.error(f"فشل الرفع: {e}")
        return False
