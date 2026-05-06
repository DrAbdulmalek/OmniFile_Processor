"""
HandwrittenOCR - FastAPI Backend v5.0
=======================================
REST API for the HandwrittenOCR project.
Designed to run on Google Colab with ngrok tunnel
or locally on Manjaro/Windows/macOS.

v5.0 New features:
- Sync status endpoint + network info
- File locking for multi-device safety
- Local/offline mode support
- Syncthing configuration generator
"""

import os
import sys
import json
import csv
import sqlite3
import shutil
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Ensure project root is importable
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import Config
from src.database import HandwritingDB
from src.recognition import OCREngine
from src.correction import (
    init_correctors,
    load_correction_dict,
    correct_text,
    append_feedback,
    load_custom_vocabulary,
    get_protected_words_count,
)
from src.study_guide import (
    generate_study_guide, generate_study_guide_full,
    export_study_guide_html, generate_mermaid_diagram,
    generate_flashcards, export_flashcards_anki,
)
from src.preprocessing import column_aware_sort
from src.reconstruction import reconstruct_sentences, extract_bilingual_vocab
from src.export import (
    export_finetuning_dataset,
    push_to_huggingface,
    auto_export,
    create_backup,
)
from src.finetuning import finetune_trocr_lora
from src.pdf_processor import PDFProcessor
from src.logger import setup_logging
from src.metrics import compute_metrics, plot_metrics_fig
from src.sync import FileLock, SyncManager
from src.migration import DataMigrator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HandwrittenOCR.API")

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_config: Optional[Config] = None
_db: Optional[HandwritingDB] = None
_ocr_engine: Optional[OCREngine] = None
_models_loaded = False
_processing_lock = threading.Lock()
_finetuning_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Lazy-initialisation
# ---------------------------------------------------------------------------
def _ensure_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
        _config.setup()
        _config.apply_hf_token()
        _config.apply_cache_env()
    return _config


def _ensure_db() -> HandwritingDB:
    global _db
    cfg = _ensure_config()
    if _db is None:
        _db = HandwritingDB(cfg.db_path)
    return _db


def _ensure_ocr() -> OCREngine:
    global _ocr_engine, _models_loaded
    cfg = _ensure_config()
    if _ocr_engine is None:
        logger.info("Loading OCR models...")
        init_correctors()
        _ocr_engine = OCREngine(
            trocr_model_name=cfg.trocr_model_name,
            ocr_languages=cfg.ocr_languages,
            max_text_length=cfg.max_text_length,
            cache_dir=cfg.model_cache_dir or cfg.cache_dir,
            hf_token=cfg.hf_token,
            trocr_default_confidence=cfg.trocr_default_confidence,
            easy_conf_threshold=cfg.easy_conf_threshold,
            num_beams=cfg.num_beams,
            trocr_batch_size=cfg.trocr_batch_size,
            lora_save_path=cfg.lora_save_path,
        )
        _models_loaded = True
        logger.info("OCR models loaded.")
    return _ocr_engine


def _get_device() -> str:
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ProcessPDFRequest(BaseModel):
    pdf_path: str
    pages_start: int = 1
    pages_end: int = 5
    resume: bool = False
    adaptive: bool = False


class UpdateWordRequest(BaseModel):
    predicted_text: str
    status: str


class SentenceItem(BaseModel):
    word_ids: list[int]
    original: str
    corrected: str
    page: int


class SaveSentencesRequest(BaseModel):
    sentences: list[SentenceItem]


class CorrectionRequest(BaseModel):
    original: str
    corrected: str


class ExportDatasetRequest(BaseModel):
    val_ratio: float = 0.1


class FinetuneRequest(BaseModel):
    min_samples: int = 50


class PushHFRequest(BaseModel):
    repo_id: str
    token: str
    commit_message: str = ""


class SettingsUpdate(BaseModel):
    pdf_path: Optional[str] = None
    pages_start: Optional[int] = None
    pages_end: Optional[int] = None
    dpi: Optional[int] = None
    hf_token: Optional[str] = None
    hf_dataset_repo: Optional[str] = None


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HandwrittenOCR API",
    description="REST API v5.3 for handwritten text OCR, review, fine-tuning, export, study guides with Mermaid diagrams and flashcards, and data migration.",
    version="5.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# 1. GET /api/health
# ===========================================================================
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "device": _get_device(),
        "models_loaded": _models_loaded,
    }


# ===========================================================================
# 2. GET /api/stats
# ===========================================================================
@app.get("/api/stats")
async def get_stats():
    cfg = _ensure_config()
    db = _ensure_db()

    stats_from_file = {}
    if os.path.isfile(cfg.stats_json):
        try:
            with open(cfg.stats_json, "r", encoding="utf-8") as f:
                stats_from_file = json.load(f)
        except Exception:
            pass

    counts = db.count_by_status()
    conn = db._conn()
    try:
        pages_row = conn.execute(
            "SELECT COUNT(DISTINCT page_num) FROM handwriting_data WHERE page_num > 0"
        ).fetchone()
        total_pages = pages_row[0] if pages_row else 0
    finally:
        conn.close()

    return {
        "total_words": sum(counts.values()),
        "unverified": counts.get("unverified", 0),
        "verified": counts.get("verified", 0),
        "sentence_corrected": counts.get("sentence_corrected", 0),
        "total_pages": total_pages,
        "last_run": stats_from_file,
    }


# ===========================================================================
# 3. POST /api/process-pdf
# ===========================================================================
@app.post("/api/process-pdf")
async def process_pdf(req: ProcessPDFRequest):
    if not os.path.isfile(req.pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF not found: {req.pdf_path}")

    if _processing_lock.locked():
        raise HTTPException(status_code=409, detail="Processing already in progress.")

    cfg = _ensure_config()
    cfg.pdf_path = req.pdf_path
    cfg.pages_start = req.pages_start
    cfg.pages_end = req.pages_end

    def _run():
        try:
            ocr = _ensure_ocr()
            db = _ensure_db()
            processor = PDFProcessor(cfg, ocr, db)
            stats = processor.process(resume=req.resume)
            logger.info(f"Processing done: {stats.get('words', 0)} words")

            # Auto-export if enabled
            if cfg.auto_export_after_run and stats.get("run_id"):
                run_id = stats["run_id"]
                try:
                    auto_export(db, run_id, config=cfg)
                except Exception as e:
                    logger.warning(f"Auto-export failed: {e}")

        except Exception as exc:
            logger.error(f"Processing failed: {exc}", exc_info=True)
        finally:
            _processing_lock.release()

    _processing_lock.acquire()
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"status": "started"}


# ===========================================================================
# 4. GET /api/checkpoint
# ===========================================================================
@app.get("/api/checkpoint")
async def get_checkpoint():
    cfg = _ensure_config()
    ckpt_path = cfg.checkpoint_file
    if not os.path.exists(ckpt_path):
        return {"checkpoint": None}
    try:
        with open(ckpt_path, "r", encoding="utf-8") as f:
            return {"checkpoint": json.load(f)}
    except Exception:
        return {"checkpoint": None}


# ===========================================================================
# 5. DELETE /api/checkpoint
# ===========================================================================
@app.delete("/api/checkpoint")
async def delete_checkpoint():
    cfg = _ensure_config()
    ckpt_path = cfg.checkpoint_file
    if os.path.exists(ckpt_path):
        os.remove(ckpt_path)
        return {"success": True}
    return {"success": False}


# ===========================================================================
# 6. GET /api/words
# ===========================================================================
@app.get("/api/words")
async def get_words(
    status: str = Query("unverified"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    sort_by: str = Query("confidence"),
    sort_order: str = Query("asc"),
):
    db = _ensure_db()

    order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"
    allowed_sort = {"confidence", "image_id", "page_num", "y", "predicted_text"}
    if sort_by not in allowed_sort:
        sort_by = "confidence"

    conn = db._conn()
    try:
        conn.row_factory = sqlite3.Row
        total = conn.execute(
            "SELECT COUNT(*) FROM handwriting_data WHERE status = ?", (status,)
        ).fetchone()[0]

        offset = (page - 1) * limit
        cols = "image_id, predicted_text, raw_text, status, confidence, model_source, x, y, w, h, page_num, run_id"
        rows = conn.execute(
            f"SELECT {cols} FROM handwriting_data "
            f"WHERE status = ? ORDER BY {sort_by} {order_dir} "
            f"LIMIT ? OFFSET ?",
            (status, limit, offset),
        ).fetchall()
        words = [dict(r) for r in rows]
    finally:
        conn.close()

    return {"words": words, "total": total, "page": page, "limit": limit}


# ===========================================================================
# 7. GET /api/words/{image_id}/image
# ===========================================================================
@app.get("/api/words/{image_id}/image")
async def get_word_image(image_id: int):
    db = _ensure_db()
    word = db.get_word(image_id)
    if word is None:
        raise HTTPException(status_code=404, detail=f"Word {image_id} not found.")
    return Response(content=bytes(word["image_data"]), media_type="image/png")


# ===========================================================================
# 8. PUT /api/words/{image_id}
# ===========================================================================
@app.put("/api/words/{image_id}")
async def update_word(image_id: int, req: UpdateWordRequest):
    db = _ensure_db()
    cfg = _ensure_config()

    word = db.get_word(image_id)
    if word is None:
        raise HTTPException(status_code=404, detail=f"Word {image_id} not found.")

    original_text = word["predicted_text"]
    db.update_word(image_id=image_id, predicted_text=req.predicted_text, status=req.status)

    # Log to feedback CSV + DB review_events
    if req.predicted_text != original_text and req.status in ("verified", "sentence_corrected"):
        append_feedback(cfg.feedback_csv, image_id, original_text, req.predicted_text, req.status)
        db.log_review(image_id, original_text, req.predicted_text, "update")

    return {"success": True}


# ===========================================================================
# 9. DELETE /api/words/{image_id}
# ===========================================================================
@app.delete("/api/words/{image_id}")
async def delete_word(image_id: int):
    db = _ensure_db()
    deleted = db.delete_word(image_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Word {image_id} not found.")
    return {"success": True}


# ===========================================================================
# 10. GET /api/sentences
# ===========================================================================
@app.get("/api/sentences")
async def get_sentences(y_tolerance: int = Query(25, ge=5, le=100)):
    db = _ensure_db()
    conn = db._conn()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM handwriting_data "
            "WHERE status IN ('verified', 'sentence_corrected') "
            "ORDER BY page_num, y, x"
        ).fetchall()
        words = [dict(r) for r in rows]
    finally:
        conn.close()

    if not words:
        return {"sentences": []}

    sentences = []
    pages = sorted(set(w["page_num"] for w in words if w["page_num"] > 0))

    for page_num in pages:
        p_words = sorted(
            [w for w in words if w["page_num"] == page_num],
            key=lambda k: (k["y"], k["x"]),
        )
        if not p_words:
            continue

        lines = []
        curr = [p_words[0]]
        for i in range(1, len(p_words)):
            if abs(p_words[i]["y"] - curr[-1]["y"]) <= y_tolerance:
                curr.append(p_words[i])
            else:
                lines.append(curr)
                curr = [p_words[i]]
        lines.append(curr)

        for line in lines:
            try:
                from langdetect import detect
                lang = detect(" ".join(str(w["predicted_text"]) for w in line))
            except Exception:
                lang = "en"

            sl = sorted(line, key=lambda k: k["x"], reverse=(lang == "ar"))
            sentences.append({
                "page": page_num,
                "text": " ".join(str(w["predicted_text"]) for w in sl),
                "lang": lang,
                "word_ids": [w["image_id"] for w in sl],
            })

    return {"sentences": sentences}


# ===========================================================================
# 11. PUT /api/sentences
# ===========================================================================
@app.put("/api/sentences")
async def save_sentence_corrections(req: SaveSentencesRequest):
    db = _ensure_db()
    cfg = _ensure_config()
    total_updated = 0

    for sentence in req.sentences:
        for wid in sentence.word_ids:
            word = db.get_word(wid)
            if word is None:
                continue
            db.update_word(wid, status="sentence_corrected")
            db.log_review(wid, sentence.original, sentence.corrected, "sentence_correct")

            # Derived word-level corrections
            if word["predicted_text"] and len(sentence.original.split()) == len(sentence.corrected.split()):
                orig_w = sentence.original.split()
                corr_w = sentence.corrected.split()
                idx_in_sent = sum(1 for _id in sentence.word_ids[:sentence.word_ids.index(wid)])
                if idx_in_sent < len(orig_w) and idx_in_sent < len(corr_w):
                    ow, cw = orig_w[idx_in_sent], corr_w[idx_in_sent]
                    if ow != cw and word["predicted_text"] != cw:
                        db.update_word(wid, predicted_text=cw)
                        append_feedback(cfg.feedback_csv, wid, word["predicted_text"], cw, "sentence_derived")

        total_updated += len(sentence.word_ids)

    return {"success": True, "updated": total_updated}


# ===========================================================================
# 12. GET /api/correction-dict
# ===========================================================================
@app.get("/api/correction-dict")
async def get_correction_dict():
    cfg = _ensure_config()
    data = load_correction_dict(cfg.correction_dict_path)
    return {"corrections": data}


# ===========================================================================
# 13. POST /api/correction-dict
# ===========================================================================
@app.post("/api/correction-dict")
async def add_correction(req: CorrectionRequest):
    cfg = _ensure_config()
    existing = load_correction_dict(cfg.correction_dict_path)
    existing[req.original] = req.corrected
    os.makedirs(os.path.dirname(cfg.correction_dict_path), exist_ok=True)
    with open(cfg.correction_dict_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return {"success": True}


# ===========================================================================
# 14. DELETE /api/correction-dict/{original}
# ===========================================================================
@app.delete("/api/correction-dict/{original}")
async def delete_correction(original: str):
    cfg = _ensure_config()
    existing = load_correction_dict(cfg.correction_dict_path)
    if original not in existing:
        raise HTTPException(status_code=404, detail=f"'{original}' not found.")
    del existing[original]
    os.makedirs(os.path.dirname(cfg.correction_dict_path), exist_ok=True)
    with open(cfg.correction_dict_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return {"success": True}


# ===========================================================================
# 15. POST /api/export-dataset
# ===========================================================================
@app.post("/api/export-dataset")
async def export_dataset(req: ExportDatasetRequest):
    cfg = _ensure_config()
    db = _ensure_db()
    output_dir = export_finetuning_dataset(db=db, output_dir=cfg.export_dir, val_ratio=req.val_ratio)
    if output_dir is None:
        raise HTTPException(status_code=400, detail="No verified data available.")

    train_path = os.path.join(output_dir, "train.jsonl")
    val_path = os.path.join(output_dir, "val.jsonl")
    train_count = _count_jsonl(train_path)
    val_count = _count_jsonl(val_path)

    return {"success": True, "path": os.path.abspath(output_dir), "train_count": train_count, "val_count": val_count}


# ===========================================================================
# 16. POST /api/finetune
# ===========================================================================
@app.post("/api/finetune")
async def start_finetune(req: FinetuneRequest):
    if _finetuning_lock.locked():
        raise HTTPException(status_code=409, detail="Fine-tuning already in progress.")

    cfg = _ensure_config()

    def _run():
        try:
            ocr = _ensure_ocr()
            db = _ensure_db()
            finetune_trocr_lora(
                ocr_engine=ocr, db=db, save_path=cfg.lora_save_path,
                min_samples=req.min_samples, epochs=cfg.finetune_epochs,
                batch_size=cfg.finetune_batch_size, lr=cfg.finetune_lr,
                lora_r=cfg.lora_r, lora_alpha=cfg.lora_alpha,
                lora_dropout=cfg.lora_dropout, lora_target_modules=cfg.lora_target_modules,
            )
        except Exception as exc:
            logger.error(f"Fine-tuning failed: {exc}", exc_info=True)
        finally:
            _finetuning_lock.release()

    _finetuning_lock.acquire()
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"status": "started"}


# ===========================================================================
# 17. POST /api/push-huggingface
# ===========================================================================
@app.post("/api/push-huggingface")
async def push_to_hf(req: PushHFRequest):
    cfg = _ensure_config()
    dataset_dir = cfg.export_dir
    if not os.path.isdir(dataset_dir):
        raise HTTPException(status_code=400, detail="No exported dataset. Run /api/export-dataset first.")

    success = push_to_huggingface(
        local_dataset_dir=dataset_dir,
        hf_repo_id=req.repo_id,
        hf_token=req.token,
        commit_message=req.commit_message,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to push to HuggingFace.")

    return {"success": True, "url": f"https://huggingface.co/datasets/{req.repo_id}"}


# ===========================================================================
# 18. GET /api/bilingual-vocab
# ===========================================================================
@app.get("/api/bilingual-vocab")
async def get_bilingual_vocab(y_tolerance: int = Query(30, ge=5, le=100)):
    db = _ensure_db()
    cfg = _ensure_config()
    vocab_path = os.path.join(cfg.exports_dir, "bilingual_vocab.csv")
    df = extract_bilingual_vocab(db=db, y_tolerance=y_tolerance, output_path=vocab_path)
    if df is None:
        return {"vocab": [], "total": 0}
    return {"vocab": df.to_dict(orient="records"), "total": len(df), "csv_path": vocab_path}


# ===========================================================================
# 19. GET /api/status-counts
# ===========================================================================
@app.get("/api/status-counts")
async def get_status_counts():
    db = _ensure_db()
    counts = db.count_by_status()
    return {
        "unverified": counts.get("unverified", 0),
        "verified": counts.get("verified", 0),
        "sentence_corrected": counts.get("sentence_corrected", 0),
        "total": sum(counts.values()),
    }


# ===========================================================================
# 20. POST /api/auto-export  [NEW v4.0]
# ===========================================================================
@app.post("/api/auto-export")
async def api_auto_export():
    """تصدير تلقائي شامل: CSV + XLSX + نص + JSONL تدريب"""
    cfg = _ensure_config()
    db = _ensure_db()

    run_id = datetime.now().strftime("auto_%Y%m%d_%H%M%S")
    try:
        result = auto_export(db, run_id, config=cfg)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# 21. POST /api/backup  [NEW v4.0]
# ===========================================================================
@app.post("/api/backup")
async def api_create_backup():
    """إنشاء نسخة احتياطية شاملة"""
    cfg = _ensure_config()
    try:
        bk_dir = create_backup(cfg)
        return {"success": True, "backup_dir": bk_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# 22. GET /api/metrics  [NEW v4.0]
# ===========================================================================
@app.get("/api/metrics")
async def api_compute_metrics():
    """حساب WER/CER الحاليين"""
    cfg = _ensure_config()
    db = _ensure_db()
    try:
        m = compute_metrics(db, metrics_log=cfg.metrics_log)
        return m
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# 23. GET /api/metrics/history  [NEW v4.0]
# ===========================================================================
@app.get("/api/metrics/history")
async def api_metrics_history():
    """سجل WER/CER عبر جلسات التدريب"""
    cfg = _ensure_config()
    if not os.path.exists(cfg.metrics_log):
        return {"history": []}
    try:
        import pandas as pd
        df = pd.read_csv(cfg.metrics_log, encoding="utf-8-sig")
        return {"history": df.to_dict(orient="records")}
    except Exception:
        return {"history": []}


# ===========================================================================
# 24. GET /api/runs  [NEW v4.0]
# ===========================================================================
@app.get("/api/runs")
async def api_get_runs():
    """سجل التشغيلات السابقة"""
    cfg = _ensure_config()
    if not os.path.exists(cfg.runs_csv):
        return {"runs": []}
    try:
        import pandas as pd
        df = pd.read_csv(cfg.runs_csv, encoding="utf-8-sig")
        return {"runs": df.to_dict(orient="records")}
    except Exception:
        return {"runs": []}


# ===========================================================================
# 25. GET /api/settings  [NEW v4.0]
# ===========================================================================
@app.get("/api/settings")
async def api_get_settings():
    """الحصول على الإعدادات الحالية (بدون كلمات المرور)"""
    cfg = _ensure_config()
    return {
        "pdf_path": cfg.pdf_path,
        "pages_start": cfg.pages_start,
        "pages_end": cfg.pages_end,
        "dpi": cfg.dpi,
        "trocr_model_name": cfg.trocr_model_name,
        "hf_dataset_repo": cfg.hf_dataset_repo,
        "trocr_batch_size": cfg.trocr_batch_size,
        "num_beams": cfg.num_beams,
        "easy_conf_threshold": cfg.easy_conf_threshold,
        "correction_min_votes": cfg.correction_min_votes,
        "finetune_lr": cfg.finetune_lr,
        "auto_export_after_run": cfg.auto_export_after_run,
        "lora_loaded": _ocr_engine.lora_loaded if _ocr_engine else False,
    }


# ===========================================================================
# 26. PUT /api/settings  [NEW v4.0]
# ===========================================================================
@app.put("/api/settings")
async def api_update_settings(req: SettingsUpdate):
    """تحديث الإعدادات"""
    cfg = _ensure_config()
    if req.pdf_path is not None:
        cfg.pdf_path = req.pdf_path
    if req.pages_start is not None:
        cfg.pages_start = req.pages_start
    if req.pages_end is not None:
        cfg.pages_end = req.pages_end
    if req.dpi is not None:
        cfg.dpi = req.dpi
    if req.hf_token is not None:
        cfg.hf_token = req.hf_token
        cfg.apply_hf_token()
    if req.hf_dataset_repo is not None:
        cfg.hf_dataset_repo = req.hf_dataset_repo
    return {"success": True}


# ===========================================================================
# 27. GET /api/sync/status  [NEW v5.0]
# ===========================================================================
@app.get("/api/sync/status")
async def api_sync_status():
    """حالة المزامنة بين الأجهزة"""
    cfg = _ensure_config()
    if not cfg.sync_enabled:
        return {"sync_enabled": False}

    sync_mgr = SyncManager(cfg)
    status = sync_mgr.get_status()
    conflicts = sync_mgr.detect_conflicts()
    network = sync_mgr.get_network_info()
    lock = FileLock(cfg.lock_file_path, timeout=cfg.sync_lock_timeout)

    return {
        "sync_enabled": True,
        "current_device": sync_mgr.device_id,
        "devices": status.get("devices", {}),
        "last_sync": status.get("last_sync"),
        "conflicts": conflicts,
        "is_locked": lock.is_locked(),
        "lock_info": lock.get_lock_info(),
        "network": network,
    }


# ===========================================================================
# 28. POST /api/sync/config  [NEW v5.0]
# ===========================================================================
@app.get("/api/sync/config")
async def api_sync_config():
    """إعدادات Syncthing للمشروع"""
    cfg = _ensure_config()
    sync_mgr = SyncManager(cfg)
    return sync_mgr.get_syncthing_config()


# ===========================================================================
# 29. GET /api/sync/stignore  [NEW v5.0]
# ===========================================================================
@app.get("/api/sync/stignore")
async def api_sync_stignore():
    """محتوى ملف .stignore لـ Syncthing"""
    cfg = _ensure_config()
    sync_mgr = SyncManager(cfg)
    content = sync_mgr.generate_syncthing_stignore()
    return Response(content=content, media_type="text/plain")


# ===========================================================================
# 30. GET /api/network  [NEW v5.0]
# ===========================================================================
@app.get("/api/network")
async def api_network_info():
    """معلومات الشبكة المحلية للوصول من الجوال"""
    cfg = _ensure_config()
    sync_mgr = SyncManager(cfg)
    return sync_mgr.get_network_info()


# ===========================================================================
# 31. GET /api/migration/scan  [NEW v5.1]
# ===========================================================================
@app.get("/api/migration/scan")
async def api_migration_scan(base_path: str = ""):
    """فحص المشاريع القديمة المتاحة للترحيل"""
    cfg = _ensure_config()
    migrator = DataMigrator(cfg)
    report = migrator.scan_and_report(base_path=base_path)
    return report


# ===========================================================================
# 32. POST /api/migration/run  [NEW v5.1]
# ===========================================================================
class MigrationRequest(BaseModel):
    base_path: str = ""
    old_folders: list[str] = []
    verified_only: bool = True


class CustomVocabRequest(BaseModel):
    words: list[str]


class ColumnSortRequest(BaseModel):
    page_num: int
    lang: str = "en"


@app.post("/api/migration/run")
async def api_run_migration(req: MigrationRequest):
    """تشغيل ترحيل البيانات من النسخ القديمة"""
    cfg = _ensure_config()
    db = _ensure_db()

    migrator = DataMigrator(cfg)
    try:
        result = migrator.migrate(
            base_path=req.base_path,
            old_folders=req.old_folders if req.old_folders else None,
            verified_only=req.verified_only,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# 33. POST /api/migration/rebuild-dict  [NEW v5.1]
# ===========================================================================
@app.post("/api/migration/rebuild-dict")
async def api_rebuild_correction_dict():
    """إعادة بناء قاموس التصحيح من ملف التصحيحات"""
    cfg = _ensure_config()
    migrator = DataMigrator(cfg)
    count = migrator._rebuild_correction_dict()
    return {"success": True, "entries": count}


# ===========================================================================
# 34. GET /api/vocabulary/protected  [NEW v5.2]
# ===========================================================================
@app.get("/api/vocabulary/protected")
async def api_get_protected_vocabulary():
    """عرض الكلمات المحمية من التصحيح الإملائي"""
    from src.correction import TECHNICAL_KEYWORDS, PYTHON_KEYWORDS, get_protected_words_count

    counts = get_protected_words_count()

    return {
        "technical_keywords": sorted(TECHNICAL_KEYWORDS),
        "python_keywords": sorted(PYTHON_KEYWORDS),
        "counts": counts,
    }


# ===========================================================================
# 35. POST /api/vocabulary/custom  [NEW v5.2]
# ===========================================================================
@app.post("/api/vocabulary/custom")
async def api_add_custom_vocabulary(req: CustomVocabRequest):
    """إضافة مصطلحات مخصصة لحمايتها من التصحيح الإملائي"""
    from src.correction import load_custom_vocabulary, get_protected_words_count

    if not req.words:
        raise HTTPException(status_code=400, detail="قائمة الكلمات فارغة")

    load_custom_vocabulary(req.words)

    return {
        "success": True,
        "added": len(req.words),
        "total_protected": get_protected_words_count()["total_protected"],
    }


# ===========================================================================
# 36. GET /api/study-guide  [NEW v5.2]
# ===========================================================================
@app.get("/api/study-guide")
async def api_generate_study_guide(
    title: str = "مرجع دراسة — مستخرج من الملاحظات اليدوية",
    highlight: bool = True,
):
    """توليد مرجع دراسي بصيغة Markdown من البيانات الموثقة"""
    from src.study_guide import generate_study_guide
    cfg = _ensure_config()
    db = _ensure_db()

    output_path = os.path.join(cfg.exports_dir, "study_guide.md")
    content = generate_study_guide(
        db=db,
        output_path=output_path,
        title=title,
        highlight_terms=highlight,
    )

    if not content:
        raise HTTPException(status_code=400, detail="لا توجد بيانات كافية لتوليد المرجع")

    return {
        "success": True,
        "path": output_path,
        "size": len(content),
        "preview": content[:1000] + ("..." if len(content) > 1000 else ""),
    }


# ===========================================================================
# 37. GET /api/study-guide/html  [NEW v5.2]
# ===========================================================================
@app.get("/api/study-guide/html")
async def api_generate_study_guide_html(
    title: str = "مرجع دراسة",
):
    """تصدير المرجع الدراسي بصيغة HTML للطباعة"""
    cfg = _ensure_config()
    db = _ensure_db()

    md_content = generate_study_guide(db=db, title=title)
    if not md_content:
        raise HTTPException(status_code=400, detail="لا توجد بيانات كافية")

    html_path = os.path.join(cfg.exports_dir, "study_guide.html")
    export_study_guide_html(md_content, html_path, title=title)

    return {
        "success": True,
        "html_path": html_path,
        "markdown_path": os.path.join(cfg.exports_dir, "study_guide.md"),
    }


# ===========================================================================
# 38. POST /api/words/column-sort  [NEW v5.2]
# ===========================================================================
@app.post("/api/words/column-sort")
async def api_column_sort(req: ColumnSortRequest):
    """
    ترتيب كلمات صفحة محددة مع كشف الأعمدة.
    مفيد للصفحات المكتوبة في أعمدة (مثل جداول المفردات).
    """
    from src.preprocessing import column_aware_sort
    db = _ensure_db()

    conn = db._conn()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT image_id, x, y, w, h, predicted_text FROM handwriting_data "
            "WHERE page_num = ? ORDER BY y, x",
            (req.page_num,),
        ).fetchall()
        words = [dict(r) for r in rows]
    finally:
        conn.close()

    if not words:
        raise HTTPException(
            status_code=404,
            detail=f"لا توجد كلمات في الصفحة {req.page_num}"
        )

    max_x = max(w["x"] + w["w"] for w in words)
    img_width = max_x + 100

    boxes = [(w["x"], w["y"], w["w"], w["h"]) for w in words]
    sorted_boxes = column_aware_sort(boxes, img_width, lang=req.lang)

    word_map = {(w["x"], w["y"], w["w"], w["h"]): w for w in words}
    sorted_words = []
    for box in sorted_boxes:
        if box in word_map:
            sorted_words.append(word_map[box])

    return {
        "success": True,
        "page": req.page_num,
        "total_words": len(sorted_words),
        "words": [
            {
                "image_id": w["image_id"],
                "predicted_text": w["predicted_text"],
                "x": w["x"],
                "y": w["y"],
            }
            for w in sorted_words
        ],
    }


# ===========================================================================
# 39. GET /api/study-guide/full  [NEW v5.3]
# ===========================================================================
@app.get("/api/study-guide/full")
async def api_generate_study_guide_full(
    title: str = "مرجع دراسة شامل — مستخرج من الملاحظات اليدوية",
    include_mermaid: bool = True,
    mermaid_type: str = Query("mindmap", enum=["mindmap", "flowchart", "graph"]),
    include_flashcards: bool = True,
    flashcard_type: str = Query("bilingual", enum=["bilingual", "concept", "fill_blank"]),
    max_flashcards: int = Query(100, ge=1, le=500),
):
    """توليد مرجع دراسي شامل يتضمن Mermaid + Flashcards + Markdown"""
    cfg = _ensure_config()
    db = _ensure_db()

    content = generate_study_guide_full(
        db=db,
        output_dir=cfg.exports_dir,
        title=title,
        include_mermaid=include_mermaid,
        mermaid_type=mermaid_type,
        include_flashcards=include_flashcards,
        flashcard_type=flashcard_type,
        max_flashcards=max_flashcards,
    )

    if not content:
        raise HTTPException(status_code=400, detail="لا توجد بيانات كافية لتوليد المرجع الشامل")

    return {
        "success": True,
        "size": len(content),
        "files": {
            "markdown": os.path.join(cfg.exports_dir, "study_guide_full.md"),
            "html": os.path.join(cfg.exports_dir, "study_guide_full.html"),
            "mermaid": os.path.join(cfg.exports_dir, "vocab_diagram.mmd") if include_mermaid else None,
            "flashcards_anki": os.path.join(cfg.exports_dir, "flashcards_anki.csv") if include_flashcards else None,
        },
        "preview": content[:1500] + ("..." if len(content) > 1500 else ""),
    }


# ===========================================================================
# 40. GET /api/study-guide/mermaid  [NEW v5.3]
# ===========================================================================
@app.get("/api/study-guide/mermaid")
async def api_generate_mermaid(
    diagram_type: str = Query("mindmap", enum=["mindmap", "flowchart", "graph"]),
    max_terms: int = Query(50, ge=1, le=200),
):
    """توليد مخطط Mermaid للمفردات المستخرجة"""
    db = _ensure_db()

    mermaid_code = generate_mermaid_diagram(db, diagram_type=diagram_type, max_terms=max_terms)
    if not mermaid_code:
        raise HTTPException(status_code=400, detail="لا توجد مفردات لتوليد المخطط")

    return {
        "success": True,
        "diagram_type": diagram_type,
        "terms_count": mermaid_code.count("[") - 1,  # تقريبي
        "mermaid_code": mermaid_code,
    }


# ===========================================================================
# 41. GET /api/study-guide/flashcards  [NEW v5.3]
# ===========================================================================
@app.get("/api/study-guide/flashcards")
async def api_generate_flashcards(
    card_type: str = Query("bilingual", enum=["bilingual", "concept", "fill_blank"]),
    max_cards: int = Query(100, ge=1, le=500),
    shuffle: bool = True,
):
    """توليد بطاقات تعليمية (Flashcards) من البيانات المستخرجة"""
    cfg = _ensure_config()
    db = _ensure_db()

    cards = generate_flashcards(
        db=db,
        card_type=card_type,
        max_cards=max_cards,
        shuffle=shuffle,
    )

    if not cards:
        raise HTTPException(status_code=400, detail="لا توجد بيانات كافية لتوليد البطاقات")

    return {
        "success": True,
        "card_type": card_type,
        "total_cards": len(cards),
        "cards": cards[:20],  # عرض أول 20 فقط
        "note": f"عرض أول 20 من {len(cards)} بطاقة. استخدم /api/study-guide/flashcards/export للحصول على الكل.",
    }


# ===========================================================================
# 42. GET /api/study-guide/flashcards/export  [NEW v5.3]
# ===========================================================================
@app.get("/api/study-guide/flashcards/export")
async def api_export_flashcards_anki(
    card_type: str = Query("bilingual", enum=["bilingual", "concept", "fill_blank"]),
    max_cards: int = Query(100, ge=1, le=500),
):
    """تصدير بطاقات تعليمية بتنسيق Anki CSV"""
    cfg = _ensure_config()
    db = _ensure_db()

    cards = generate_flashcards(db=db, card_type=card_type, max_cards=max_cards)
    if not cards:
        raise HTTPException(status_code=400, detail="لا توجد بطاقات للتصدير")

    anki_path = os.path.join(cfg.exports_dir, f"flashcards_{card_type}.csv")
    export_flashcards_anki(cards, anki_path)

    return Response(
        content=open(anki_path, "r", encoding="utf-8-sig").read(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=flashcards_{card_type}.csv"},
    )


# ===========================================================================
# Helpers
# ===========================================================================
def _count_jsonl(path: str) -> int:
    if not os.path.isfile(path):
        return 0
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count
