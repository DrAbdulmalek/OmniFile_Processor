"""
HandwrittenOCR - واجهة Gradio v5.5
====================================
واجهة مستخدم كاملة مع 7 تبويبات:
1. ⚙️ المعالجة — PDF Processing
2. 🔍 مراجعة الكلمات — Word Review
3. 📝 مراجعة الجمل — Sentence Review
4. 📊 Dashboard — إحصائيات ورسوم بيانية
5. 🧠 Fine-tuning & Active Learning
6. 📚 دليل الدراسة — Study Guide
7. ⚙️ الإعداد والترحيل — Settings & Migration
"""

import io
import json
import logging
import os
import traceback
from datetime import datetime

import pandas as pd
from PIL import Image

logger = logging.getLogger("HandwrittenOCR")

# استيراد أدوات اللوق المفصّل (backward-compat: src.logger → modules)
try:
    from src.logger import log_step, log_error_full, log_result
except ImportError:
    def log_step(lg, name, data=None):
        lg.info(f"STEP [{name}]")
        if data:
            for k, v in data.items():
                lg.info(f"      {k}: {v}")
    def log_error_full(lg, ctx, err, extra=None):
        lg.error(f"ERROR [{ctx}] {type(err).__name__}: {err}", exc_info=True)
    def log_result(lg, name, result):
        lg.info(f"RESULT [{name}] {result}")


# ==================== حالة المراجعة ====================

_review_state = {"df": pd.DataFrame(), "idx": 0}
_sent_state = {"df": None, "idx": 0}


# ==================== مساعدات مراجعة الكلمات ====================

def _get_db(config):
    """إنشاء/إعادة كائن قاعدة البيانات."""
    try:
        from modules.core.handwriting_db import HandwritingDB
    except ImportError:
        from src.database import HandwritingDB
    return HandwritingDB(config.db_path)


def _get_ocr_engine(config):
    """إنشاء/إعادة محرك التعرف."""
    try:
        from modules.vision.ocr_engine import OCREngine
        return OCREngine.from_legacy_config(config)
    except ImportError:
        from src.recognition import OCREngine
        return OCREngine(
            trocr_model_name=config.trocr_model_name,
            ocr_languages=config.ocr_languages,
            max_text_length=config.max_text_length,
            cache_dir=config.model_cache_dir or config.cache_dir,
            hf_token=config.hf_token,
            trocr_default_confidence=config.trocr_default_confidence,
            easy_conf_threshold=config.easy_conf_threshold,
            num_beams=config.num_beams,
            trocr_batch_size=config.trocr_batch_size,
            lora_save_path=config.lora_save_path,
            skip_trocr=config.skip_trocr,
            use_fp16=config.use_fp16,
        )


def _normalize_text(x) -> str:
    """تنظيف النص من NaN وNone."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return str(x).strip()


# --- مراجعة الكلمات ---

def _word_row(config):
    """جلب صف الكلمة الحالي للعرض."""
    db = _get_db(config)
    df, idx = _review_state["df"], _review_state["idx"]
    if df.empty:
        return None, "", "", "لا توجد كلمات للمراجعة", 0.0, "0/0"
    row = df.iloc[idx]
    pil = Image.open(io.BytesIO(bytes(row["image_data"])))
    conf = float(row["confidence"] or 0)
    info = (
        f"**{idx + 1}/{len(df)}** | صفحة {row['page_num']} "
        f"| {row['model_source']} | id={row['image_id']}"
    )
    return (
        pil,
        str(row["predicted_text"] or ""),
        str(row["raw_text"] or ""),
        info,
        conf,
        f"{idx + 1}/{len(df)}",
    )


def load_word_review(config):
    """تحميل الكلمات غير المراجعة للمراجعة مع تسجيل."""
    log_step(logger, "تحميل مراجعة الكلمات")
    db = _get_db(config)
    words = db.get_unverified(order_by_confidence=True)
    _review_state["df"] = pd.DataFrame(words) if words else pd.DataFrame()
    _review_state["idx"] = 0
    logger.info(f"  تم تحميل {len(words) if words else 0} كلمة غير مراجعة")
    log_result(logger, "تحميل مراجعة الكلمات", {"words": len(words) if words else 0})
    return _word_row(config)


def word_confirm(config, corrected_text: str):
    """تأكيد تصحيح كلمة مع تسجيل مفصّل."""
    df, idx = _review_state["df"], _review_state["idx"]
    if df.empty:
        return _word_row(config)
    db = _get_db(config)
    row = df.iloc[idx]
    rid = int(row["image_id"])
    orig = _normalize_text(row["predicted_text"])
    corr = _normalize_text(corrected_text)
    logger.info(f"word_confirm: id={rid}, '{orig[:40]}' => '{corr[:40]}'")
    db.update_word(rid, predicted_text=corr, status="verified")
    db.log_review(rid, orig, corr, "confirm")
    if orig != corr:
        try:
            from modules.nlp.feedback import append_feedback
        except ImportError:
            from src.correction import append_feedback
        append_feedback(config.feedback_csv, rid, orig, corr, "verified")
        logger.info(f"  تم تسجيل تصحيح في feedback CSV")
    _review_state["df"] = df.drop(df.index[idx]).reset_index(drop=True)
    _review_state["idx"] = min(idx, max(0, len(_review_state["df"]) - 1))
    return _word_row(config)


def word_delete(config):
    """حذف كلمة مع تسجيل."""
    df, idx = _review_state["df"], _review_state["idx"]
    if df.empty:
        return _word_row(config)
    db = _get_db(config)
    rid = int(df.iloc[idx]["image_id"])
    logger.info(f"word_delete: id={rid}, text='{df.iloc[idx]['predicted_text'][:40]}'")
    db.delete_word(rid)
    db.log_review(rid, "", "", "delete")
    _review_state["df"] = df.drop(df.index[idx]).reset_index(drop=True)
    _review_state["idx"] = min(idx, max(0, len(_review_state["df"]) - 1))
    return _word_row(config)


def word_undo(config):
    """التراجع عن آخر تصحيح مع تسجيل."""
    log_step(logger, "word_undo")
    db = _get_db(config)
    evt = db.get_last_review_event()
    if not evt:
        logger.info("  لا يوجد حدث مراجعة للتراجع عنه")
        return _word_row(config)

    image_id = evt.get("image_id")
    original = evt.get("original_text", "")
    action = evt.get("action", "")

    if action in ("confirm", "verify") and image_id and original:
        db.update_word(int(image_id), predicted_text=original, status="unverified")
        db.delete_review_event(int(evt.get("id", 0)))
        logger.info(f"  word_undo: id={image_id}, استرجع '{original[:40]}'")

        # إعادة تحميل القائمة
        words = db.get_unverified(order_by_confidence=True)
        _review_state["df"] = pd.DataFrame(words) if words else pd.DataFrame()
        _review_state["idx"] = 0
    else:
        logger.info(f"  word_undo: لا يمكن التراجع عن action='{action}'")

    return _word_row(config)


def word_prev(config):
    """الانتقال للكلمة السابقة."""
    if not _review_state["df"].empty:
        _review_state["idx"] = max(0, _review_state["idx"] - 1)
    return _word_row(config)


def word_next(config):
    """الانتقال للكلمة التالية."""
    df = _review_state["df"]
    if not df.empty:
        _review_state["idx"] = min(len(df) - 1, _review_state["idx"] + 1)
    return _word_row(config)


# --- مراجعة الجمل ---

def _sent_row(config):
    """جلب صف الجملة الحالية للعرض."""
    sentences, idx = _sent_state["df"], _sent_state["idx"]
    if not sentences:
        return "", "لا توجد جمل", "0/0"
    row = sentences[idx]
    info = (
        f"**{idx + 1}/{len(sentences)}** | صفحة {row['page']} "
        f"| {row['lang']} | {len(row['word_ids'])} كلمة"
    )
    return row["text"], info, f"{idx + 1}/{len(sentences)}"


def load_sent_review(config):
    """تحميل الجمل للمراجعة."""
    try:
        from modules.nlp.reconstruction import reconstruct_sentences
    except ImportError:
        from src.reconstruction import reconstruct_sentences
    db = _get_db(config)
    sentences = reconstruct_sentences(db, verified_only=False) or []
    _sent_state["df"] = sentences
    _sent_state["idx"] = 0
    return _sent_row(config)


def sent_save(config, corrected: str):
    """حفظ تصحيح جملة."""
    sentences, idx = _sent_state["df"], _sent_state["idx"]
    if not sentences:
        return _sent_row(config)
    db = _get_db(config)
    row = sentences[idx]
    orig = _normalize_text(row["text"])
    corr = _normalize_text(corrected)
    ts = datetime.now().isoformat()
    for wid in row["word_ids"]:
        db.update_word(
            int(wid),
            status="sentence_corrected",
        )
    if orig != corr:
        from src.correction import append_feedback
        append_feedback(
            config.feedback_csv, None, orig, corr,
            f"sent_p{row['page']}",
        )
    _sent_state["idx"] = min(idx + 1, max(0, len(sentences) - 1))
    return _sent_row(config)


def sent_prev(config):
    """الانتقال للجملة السابقة."""
    if _sent_state["df"]:
        _sent_state["idx"] = max(0, _sent_state["idx"] - 1)
    return _sent_row(config)


def sent_next(config):
    """الانتقال للجملة التالية."""
    sentences = _sent_state["df"]
    if sentences:
        _sent_state["idx"] = min(len(sentences) - 1, _sent_state["idx"] + 1)
    return _sent_row(config)


# ==================== Dashboard ====================

def build_dashboard_fig(config):
    """بناء الرسوم البيانية للـ Dashboard."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    # 1. توزيع الحالات
    db = _get_db(config)
    counts = db.count_by_status()
    if counts:
        axes[0].bar(
            list(counts.keys()),
            list(counts.values()),
            color=["#4CAF50", "#2196F3", "#FF9800", "#F44336", "#9C27B0"],
        )
        axes[0].set_title("توزيع الحالات")
        axes[0].tick_params(axis="x", rotation=30)
    else:
        axes[0].text(0.5, 0.5, "لا بيانات", ha="center")
        axes[0].set_title("توزيع الحالات")

    # 2. كلمات لكل تشغيل
    runs_csv = config.runs_csv
    if os.path.exists(runs_csv):
        runs = pd.read_csv(runs_csv, encoding="utf-8-sig")
        if not runs.empty:
            vals = pd.to_numeric(runs["words"], errors="coerce").fillna(0)
            axes[1].plot(vals.values, marker="o", color="#2196F3")
            axes[1].set_title("كلمات لكل تشغيل")
        else:
            axes[1].text(0.5, 0.5, "لا سجلات", ha="center")
            axes[1].set_title("كلمات لكل تشغيل")
    else:
        axes[1].text(0.5, 0.5, "لا سجلات", ha="center")
        axes[1].set_title("كلمات لكل تشغيل")

    # 3. WER / CER
    metrics_log = config.metrics_log
    if os.path.exists(metrics_log):
        mdf = pd.read_csv(metrics_log, encoding="utf-8-sig")
        if not mdf.empty:
            axes[2].plot(
                mdf["wer"].dropna().values,
                label="WER",
                color="#E53935",
                marker="o",
            )
            axes[2].plot(
                mdf["cer"].dropna().values,
                label="CER",
                color="#1E88E5",
                marker="s",
            )
            axes[2].set_title("WER / CER")
            axes[2].legend()
            axes[2].set_ylim(0, 1)
        else:
            axes[2].text(0.5, 0.5, "لا مقاييس", ha="center")
            axes[2].set_title("WER / CER")
    else:
        axes[2].text(0.5, 0.5, "لا مقاييس بعد", ha="center")
        axes[2].set_title("WER / CER")

    plt.tight_layout()
    return fig


def get_dashboard_text(config) -> str:
    """جلب نص ملخص الـ Dashboard."""
    db = _get_db(config)
    lines = ["## 📊 ملخص المشروع"]
    counts = db.count_by_status()
    total = sum(counts.values()) if counts else 0
    lines.append(f"**إجمالي الكلمات:** {total}")
    for k, v in counts.items():
        lines.append(f"- {k}: **{v}**")

    if os.path.exists(config.stats_json):
        try:
            with open(config.stats_json, "r", encoding="utf-8") as f:
                s = json.load(f)
            lines.append(
                f"\n**آخر تشغيل:** `{s.get('run_id', '—')}`  \n"
                f"صفحات: {s.get('pages')} | كلمات: {s.get('words')} "
                f"| ثقة: {s.get('avg_confidence')} | مدة: {s.get('duration_sec')}s"
            )
        except Exception:
            pass

    return "\n".join(lines)


# ==================== أغلفة Gradio ====================

def _do_process(config, inp, sp, ep, resume, adaptive, progress=None):
    """تشغيل معالجة PDF مع progress callback وتسجيل مفصّل."""
    log_step(logger, "_do_process (Gradio UI)", {
        "input": str(inp)[:100],
        "pages": f"{sp}-{ep}",
        "resume": str(resume),
        "adaptive": str(adaptive),
    })

    from src.recognition import OCREngine
    from src.pdf_processor import PDFProcessor
    from src.correction import init_correctors

    # تحديث الإعدادات
    if inp and str(inp).strip():
        config.pdf_path = str(inp).strip()
    config.pages_start = int(sp) if sp else 1
    ep_val = int(ep) if ep and str(ep).strip() else config.pages_end
    config.pages_end = ep_val

    # تحميل المدققات
    if not config.skip_spellcheck:
        init_correctors()

    # إنشاء المحرك وقاعدة البيانات
    logger.info("إنشاء محرك التعرف وقاعدة البيانات...")
    ocr = _get_ocr_engine(config)
    db = _get_db(config)
    processor = PDFProcessor(config, ocr, db)

    def cb(cur, tot, msg):
        if progress:
            progress(cur / max(tot, 1), desc=msg)
        logger.debug(f"  [تقدم] {cur}/{tot}: {msg}")

    try:
        stats = processor.process(resume=resume, progress_cb=cb)
        if stats.get("error"):
            log_error_full(logger, "_do_process", Exception(stats.get("error", "خطأ غير معروف")))
            return f"❌ فشلت المعالجة: {stats.get('error', 'خطأ غير معروف')}"
        log_result(logger, "_do_process", stats)
        return (
            f"✅ اكتملت المعالجة\n"
            f"```json\n{json.dumps(stats, ensure_ascii=False, indent=2)}\n```"
        )
    except Exception as e:
        log_error_full(logger, "_do_process", e)
        return f"❌ خطأ: {e}"


def _do_export(config):
    """تصدير تلقائي مع تسجيل."""
    log_step(logger, "_do_export")
    from src.export import auto_export

    stats = {}
    if os.path.exists(config.stats_json):
        try:
            with open(config.stats_json, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            pass
    run_id = stats.get("run_id", f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    db = _get_db(config)
    summary = auto_export(db, run_id, config=config)
    if not summary:
        return "⚠️ لا توجد بيانات للتصدير"
    return f"✅\n```json\n{json.dumps(summary, ensure_ascii=False, indent=2)}\n```"


def _do_backup(config):
    """إنشاء نسخة احتياطية مع تسجيل."""
    log_step(logger, "_do_backup")
    from src.export import create_backup
    try:
        path = create_backup(config)
        logger.info(f"تم إنشاء نسخة احتياطية: {path}")
        return f"✅ نسخة احتياطية: `{path}`"
    except Exception as e:
        log_error_full(logger, "_do_backup", e)
        return f"❌ {e}"


def _do_metrics(config):
    """حساب مقاييس WER/CER مع تسجيل."""
    log_step(logger, "_do_metrics")
    from src.metrics import compute_metrics
    db = _get_db(config)
    m = compute_metrics(db, metrics_log=config.metrics_log)
    if m.get("wer") is None:
        return (
            f"⚠️ عينات غير كافية: {m.get('samples', 0)} "
            "(مطلوب ≥5 عينات مع raw_text)",
            None,
        )
    text = (
        f"**WER:** {m['wer']:.2%} | **CER:** {m['cer']:.2%} "
        f"| **عينات:** {m['samples']}"
    )
    fig = build_dashboard_fig(config)
    return text, fig


def _do_finetune(config, min_s, ep, bs, lr, progress=None):
    """تشغيل LoRA fine-tuning مع تسجيل مفصّل."""
    log_step(logger, "_do_finetune", {
        "min_samples": min_s,
        "epochs": ep,
        "batch_size": bs,
        "learning_rate": lr,
    })
    from src.finetuning import finetune_trocr_lora
    from src.recognition import OCREngine

    ocr = _get_ocr_engine(config)
    db = _get_db(config)

    def cb(cur, tot, msg):
        if progress:
            progress(cur / max(tot, 1), desc=msg)

    success = finetune_trocr_lora(
        ocr_engine=ocr,
        db=db,
        save_path=config.lora_save_path,
        min_samples=int(min_s),
        epochs=int(ep),
        batch_size=int(bs),
        lr=float(lr),
        tensorboard_dir=config.tensorboard_dir,
        use_fp16=config.use_fp16,
    )
    if success:
        logger.info("اكتمل التدريب بنجاح")
        return "✅ اكتمل التدريب بنجاح"
    logger.warning("فشل التدريب")
    return "❌ فشل التدريب — تحقق من السجلات"


def _do_study_guide(config):
    """توليد مرجع دراسي مع تسجيل."""
    log_step(logger, "_do_study_guide")
    from src.study_guide import generate_study_guide_full
    db = _get_db(config)
    study_dir = config.study_guide_dir
    os.makedirs(study_dir, exist_ok=True)
    content = generate_study_guide_full(
        db=db,
        output_dir=study_dir,
        include_mermaid=True,
        include_flashcards=True,
    )
    if not content:
        return "⚠️ لا توجد بيانات لتوليد المرجع الدراسي"
    return (
        f"✅ تم حفظ المرجع في: `{study_dir}`\n\n"
        f"{content[:500]}..."
    )


def _do_migrate(config):
    """ترحيل البيانات من النسخ القديمة مع تسجيل."""
    log_step(logger, "_do_migrate")
    from src.migration import DataMigrator
    migrator = DataMigrator(config)
    report = migrator.scan_and_report()
    if report["projects_found"] == 0:
        return "⚠️ لم يتم العثور على مشاريع قديمة."
    stats = migrator.migrate()
    return (
        f"✅ الترحيل اكتمل:\n"
        f"- سجلات DB: {stats['db_records_migrated']}\n"
        f"- تصحيحات: {stats['feedback_merged']}\n"
        f"- قاموس: {stats['correction_dict_entries']} إدخال"
    )


# ==================== بناء التطبيق ====================

def build_gradio_app(config):
    """
    بناء واجهة Gradio كاملة مع 7 تبويبات.

    Parameters:
        config: كائن Config من config.py

    Returns:
        gr.Blocks app
    """
    import gradio as gr

    with gr.Blocks(
        title="Arabic Handwriting OCR — v5.5 Ultimate",
    ) as app:

        gr.Markdown(
            "# Multilingual Handwriting OCR — v5.5\n"
            "> العربية + الإنجليزية + الألمانية | TrOCR Batch + Beam Search + FP16 + LoRA | Active Learning | "
            "WER/CER | Study Guide | FileLock Multi-Device"
        )

        # ==================== TAB 1: المعالجة ====================
        with gr.Tab("⚙️ المعالجة"):
            gr.Markdown("### معالجة PDF أو صورة")
            with gr.Row():
                inp_path = gr.Textbox(
                    label="مسار الملف", value=config.pdf_path
                )
                start_page = gr.Number(
                    label="من الصفحة", value=config.pages_start, precision=0
                )
                end_page = gr.Textbox(
                    label="إلى الصفحة (فارغ=كل الصفحات)",
                    value=str(config.pages_end),
                )
            with gr.Row():
                resume_cb = gr.Checkbox(
                    label="استئناف من Checkpoint", value=True
                )
                adaptive_cb = gr.Checkbox(
                    label="Adaptive Threshold", value=False
                )
            run_btn = gr.Button("🚀 ابدأ المعالجة", variant="primary")
            run_out = gr.Markdown()
            run_btn.click(
                lambda inp, sp, ep, resume, adaptive, progress=gr.Progress(
                    track_tqdm=True
                ): _do_process(
                    config, inp, sp, ep, resume, adaptive, progress=progress
                ),
                [inp_path, start_page, end_page, resume_cb, adaptive_cb],
                run_out,
            )

        # ==================== TAB 2: مراجعة الكلمات ====================
        with gr.Tab("🔍 مراجعة الكلمات"):
            load_w_btn = gr.Button("📥 تحميل الكلمات")
            word_info = gr.Markdown("—")
            word_prog = gr.Textbox(label="التقدم", interactive=False)
            word_img = gr.Image(label="الصورة", type="pil", height=160)
            word_raw = gr.Textbox(label="النص الخام", interactive=False)
            word_edit = gr.Textbox(label="النص المعدّل ✏️")
            conf_slider = gr.Slider(0, 1, label="الثقة", interactive=False)
            with gr.Row():
                prev_w = gr.Button("⬅ السابق")
                conf_w = gr.Button("✅ تأكيد", variant="primary")
                del_w = gr.Button("🗑 حذف", variant="stop")
                undo_w = gr.Button("↩ تراجع", variant="secondary")
                next_w = gr.Button("التالي ➡")
            _wo = [word_img, word_edit, word_raw, word_info, conf_slider, word_prog]
            load_w_btn.click(lambda: load_word_review(config), outputs=_wo)
            conf_w.click(
                lambda txt: word_confirm(config, txt), [word_edit], _wo
            )
            del_w.click(lambda: word_delete(config), outputs=_wo)
            undo_w.click(lambda: word_undo(config), outputs=_wo)
            prev_w.click(lambda: word_prev(config), outputs=_wo)
            next_w.click(lambda: word_next(config), outputs=_wo)

        # ==================== TAB 3: مراجعة الجمل ====================
        with gr.Tab("📝 مراجعة الجمل"):
            load_s_btn = gr.Button("📥 تحميل الجمل")
            sent_info = gr.Markdown("—")
            sent_prog = gr.Textbox(label="التقدم", interactive=False)
            sent_edit = gr.Textbox(label="الجملة ✏️", lines=3)
            with gr.Row():
                prev_s = gr.Button("⬅ السابق")
                save_s = gr.Button("✅ حفظ", variant="primary")
                next_s = gr.Button("التالي ➡")
            _so = [sent_edit, sent_info, sent_prog]
            load_s_btn.click(lambda: load_sent_review(config), outputs=_so)
            save_s.click(
                lambda txt: sent_save(config, txt), [sent_edit], _so
            )
            prev_s.click(lambda: sent_prev(config), outputs=_so)
            next_s.click(lambda: sent_next(config), outputs=_so)

        # ==================== TAB 4: Dashboard ====================
        with gr.Tab("📊 Dashboard"):
            refresh_btn = gr.Button("🔄 تحديث")
            dash_text = gr.Markdown()
            dash_plot = gr.Plot()
            with gr.Row():
                export_btn = gr.Button(
                    "📤 تصدير", variant="secondary"
                )
                backup_btn = gr.Button(
                    "💾 نسخة احتياطية", variant="secondary"
                )
                metrics_btn = gr.Button(
                    "📐 WER/CER", variant="secondary"
                )
            export_out = gr.Markdown()
            backup_out = gr.Markdown()
            metrics_out = gr.Markdown()
            metrics_plt = gr.Plot()

            def _refresh():
                return (
                    get_dashboard_text(config),
                    build_dashboard_fig(config),
                )

            refresh_btn.click(_refresh, outputs=[dash_text, dash_plot])
            export_btn.click(lambda: _do_export(config), outputs=export_out)
            backup_btn.click(lambda: _do_backup(config), outputs=backup_out)
            metrics_btn.click(
                lambda: _do_metrics(config),
                outputs=[metrics_out, metrics_plt],
            )
            app.load(_refresh, outputs=[dash_text, dash_plot])

        # ==================== TAB 5: Fine-tuning ====================
        with gr.Tab("🧠 Fine-tuning & AL"):
            gr.Markdown("### LoRA Fine-tuning مع TensorBoard + Augmentation")
            with gr.Row():
                ft_min = gr.Number(
                    label="حد أدنى للعينات",
                    value=config.finetune_min_samples,
                    precision=0,
                )
                ft_ep = gr.Number(
                    label="Epochs",
                    value=config.finetune_epochs,
                    precision=0,
                )
                ft_bs = gr.Number(
                    label="Batch size",
                    value=config.finetune_batch_size,
                    precision=0,
                )
                ft_lr = gr.Number(
                    label="Learning rate", value=config.finetune_lr
                )
            ft_btn = gr.Button(
                "🔥 ابدأ Fine-tuning", variant="primary"
            )
            ft_out = gr.Markdown()
            ft_btn.click(
                lambda min_s, ep, bs, lr, progress=gr.Progress(
                    track_tqdm=True
                ): _do_finetune(
                    config, min_s, ep, bs, lr, progress=progress
                ),
                [ft_min, ft_ep, ft_bs, ft_lr],
                ft_out,
            )

            gr.Markdown("---\n### 🔁 Active Learning تلقائي")
            gr.Markdown(
                f"الحد الأدنى: **{config.al_min_new_corrections}** تصحيح"
            )

        # ==================== TAB 6: Study Guide ====================
        with gr.Tab("📚 دليل الدراسة"):
            gr.Markdown(
                "### توليد مرجع دراسي من ملاحظاتك اليدوية\n"
                "يُولّد: جداول المصطلحات (EN↔AR) + جمل مُعادة البناء + "
                "مخطط Mermaid + بطاقات Anki + HTML للطباعة"
            )
            sg_btn = gr.Button(
                "📖 توليد المرجع الدراسي", variant="primary"
            )
            sg_out = gr.Markdown()
            sg_btn.click(lambda: _do_study_guide(config), outputs=sg_out)

        # ==================== TAB 7: الإعداد والترحيل ====================
        with gr.Tab("⚙️ الإعداد"):
            gr.Markdown(
                "### ترحيل البيانات من النسخ القديمة\n"
                "يبحث تلقائياً في: Handwriting_Dataset, "
                "Handwritten_OCR_Integrated, Handwritten_OCR_Pro"
            )
            migrate_btn = gr.Button(
                "🔄 بدء الترحيل", variant="secondary"
            )
            migrate_out = gr.Markdown()
            migrate_btn.click(
                lambda: _do_migrate(config), outputs=migrate_out
            )

    return app


def launch_gradio(config):
    """
    تشغيل واجهة Gradio.

    Parameters:
        config: كائن Config من config.py
    """
    app = build_gradio_app(config)
    logger.info(
        f"تشغيل Gradio UI — port={config.gradio_port}, "
        f"share={config.gradio_share}"
    )
    app.launch(
        share=config.gradio_share,
        server_port=config.gradio_port,
        quiet=False,
    )
    return app
