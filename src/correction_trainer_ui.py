"""
src/correction_trainer_ui.py
══════════════════════════════
واجهة مصحح التعلم التدريجي — Word-Level Correction Trainer UI
===============================================================
تبويبات Gradio للتصحيح الكلمة بكلمة + مراجعة قاعدة البيانات + المزامنة.

التبويبات:
  ✏️  Word Trainer  — رفع صورة → OCR → تصحيح كلمة بكلمة → حفظ
  📚  Review DB     — مراجعة سجل التصحيحات + حذف + إحصائيات
  📤  Sync          — تصدير JSON + رفع GitHub + تحميل للـ Drive

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import gc
import hashlib
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import gradio as gr
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# ── استيراد محرك التعلم ─────────────────────────────────────────────
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from modules.core.word_trainer import WordCorrectionDB
    DB = WordCorrectionDB()
    TRAINER_AVAILABLE = True
except Exception as e:
    DB = None
    TRAINER_AVAILABLE = False
    logger.warning("WordCorrectionDB not available: %s", e)

# ── ثوابت اللغات ─────────────────────────────────────────────────────
LANG_MAP = {
    "Auto-Detect 🔍":   {"easy": ["ar", "en"], "tess": "ara+eng+deu", "code": "auto"},
    "Arabic 🇸🇦":       {"easy": ["ar"],        "tess": "ara",         "code": "ar"},
    "English 🇬🇧":      {"easy": ["en"],        "tess": "eng",         "code": "en"},
    "German 🇩🇪":       {"easy": ["de", "en"], "tess": "deu+eng",     "code": "de"},
    "Arabic + English": {"easy": ["ar", "en"], "tess": "ara+eng",     "code": "ar"},
}

CONFIDENCE_EMOJI = {
    "high":   "🟢",  # >= 85%
    "medium": "🟡",  # 60-84%
    "low":    "🔴",  # < 60%
}


# ══════════════════════════════════════════════════════════════════════
# ─── دوال المساعدة ───────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════

def _image_hash(pil_image: Image.Image) -> str:
    """بصمة SHA-256 للصورة."""
    arr = np.array(pil_image.convert("L").resize((64, 64)))
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def _conf_label(conf: float) -> str:
    if conf >= 0.85:
        return f"{CONFIDENCE_EMOJI['high']} {conf:.0%}"
    elif conf >= 0.60:
        return f"{CONFIDENCE_EMOJI['medium']} {conf:.0%}"
    else:
        return f"{CONFIDENCE_EMOJI['low']} {conf:.0%}"


def _detect_lang(text: str) -> str:
    """كشف لغة النص."""
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0
        return detect(text)
    except Exception:
        ar_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        return "ar" if ar_chars > len(text) * 0.3 else "en"


def _run_ocr_words(
    image: Image.Image,
    lang_choice: str,
    use_gpu: bool = False,
) -> list[dict]:
    """
    تشغيل OCR واستخراج الكلمات مع الثقة والبُعد الحدودي.

    Returns:
        [{idx, word, confidence, bbox, lang}, ...]
    """
    lang_cfg  = LANG_MAP.get(lang_choice, LANG_MAP["Auto-Detect 🔍"])
    easy_langs = lang_cfg["easy"]
    tess_lang  = lang_cfg["tess"]
    lang_code  = lang_cfg["code"]

    words = []

    # ── محاولة EasyOCR أولاً (يُعطي word-level bboxes) ─────────────
    try:
        import easyocr
        reader = easyocr.Reader(easy_langs, gpu=use_gpu, verbose=False)
        results = reader.readtext(np.array(image))
        for bbox, text, conf in results:
            for w in text.split():
                if w.strip():
                    actual_lang = lang_code if lang_code != "auto" else _detect_lang(w)
                    # استعلم قاعدة البيانات للتصحيح المتعلَّم
                    learned = DB.get_best_correction(w, actual_lang) if DB else None
                    words.append({
                        "idx":        len(words),
                        "word":       w,
                        "correction": learned or w,   # إذا تعلّمنا تصحيحاً نبدأ به
                        "confidence": round(conf, 3),
                        "lang":       actual_lang,
                        "source":     "easyocr",
                        "learned":    learned is not None,
                    })
        if words:
            return words
    except Exception as e:
        logger.warning("EasyOCR failed: %s", e)

    # ── Tesseract fallback (word-level data) ─────────────────────────
    try:
        import pytesseract
        data = pytesseract.image_to_data(
            image, lang=tess_lang,
            output_type=pytesseract.Output.DICT
        )
        n = len(data["text"])
        for i in range(n):
            w    = data["text"][i].strip()
            conf = int(data["conf"][i]) / 100.0
            if w and conf > 0.1:
                actual_lang = lang_code if lang_code != "auto" else _detect_lang(w)
                learned = DB.get_best_correction(w, actual_lang) if DB else None
                words.append({
                    "idx":        len(words),
                    "word":       w,
                    "correction": learned or w,
                    "confidence": round(max(conf, 0.0), 3),
                    "lang":       actual_lang,
                    "source":     "tesseract",
                    "learned":    learned is not None,
                })
    except Exception as e:
        logger.warning("Tesseract failed: %s", e)

    return words


def _words_to_dataframe(words: list[dict]) -> pd.DataFrame:
    """تحويل قائمة الكلمات إلى DataFrame قابل للتحرير."""
    rows = []
    for w in words:
        rows.append({
            "#":           w["idx"] + 1,
            "Predicted":   w["word"],
            "Confidence":  _conf_label(w["confidence"]),
            "Correction":  w["correction"],
            "Delete?":     False,
            "_lang":       w["lang"],
            "_conf_raw":   w["confidence"],
        })
    df = pd.DataFrame(rows)
    return df


# ══════════════════════════════════════════════════════════════════════
# ─── بناء واجهة Gradio ───────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════

def build_trainer_tabs(use_gpu: bool = False) -> list:
    """
    بناء تبويبات المصحح التدريجي.

    Args:
        use_gpu: هل GPU متاح

    Returns:
        قائمة gr.Tab objects
    """

    # ── State مشترك بين العناصر ─────────────────────────────────────
    session_state  = gr.State({"words": [], "image_hash": "", "last_df": None})
    TABS = []

    # ══════════════════════════════════════════════════════════════════
    # Tab A: ✏️ Word Trainer
    # ══════════════════════════════════════════════════════════════════
    with gr.Tab("✏️ Word Trainer") as tab_a:
        TABS.append(tab_a)

        gr.HTML("""
        <div style="background:#0d1117;border-radius:8px;padding:14px;margin-bottom:12px">
          <h3 style="color:#58a6ff;margin:0">✏️ مصحح التعلم التدريجي</h3>
          <p style="color:#8b949e;margin:4px 0">
            ارفع صورة خط يدوي → احصل على التوقع كلمة بكلمة → صحّح → احفظ.
            النظام يتعلم ويتحسن مع كل تصحيح تجريه.
          </p>
        </div>
        """)

        with gr.Row():
            # ── العمود الأيسر: الإدخال ──────────────────────────────
            with gr.Column(scale=1):
                trainer_img = gr.Image(
                    label="📷 الصورة / Image",
                    type="pil",
                    sources=["upload", "clipboard"],
                )
                trainer_lang = gr.Dropdown(
                    label="🌐 اللغة / Language",
                    choices=list(LANG_MAP.keys()),
                    value="Auto-Detect 🔍",
                )
                with gr.Row():
                    btn_ocr   = gr.Button("🔍 OCR", variant="primary", size="lg")
                    btn_clear = gr.Button("🗑️ Clear", size="lg")

                trainer_status = gr.Markdown("_جاهز — ارفع صورة وابدأ_")

                gr.Markdown("---")
                gr.Markdown("#### ⚡ اقتراح إملائي سريع")
                spell_word = gr.Textbox(
                    label="اكتب كلمة للاقتراح",
                    placeholder="مثال: الطبيب",
                    max_lines=1,
                )
                spell_lang = gr.Radio(
                    ["ar", "en", "de"], value="ar", label="اللغة"
                )
                spell_out  = gr.Textbox(
                    label="الاقتراحات", lines=3, interactive=False
                )
                spell_word.change(
                    fn=lambda w, l: "\n".join(
                        DB.get_suggestions(w, l, n=6)
                    ) if DB and w.strip() else "",
                    inputs=[spell_word, spell_lang],
                    outputs=[spell_out],
                )

            # ── العمود الأيمن: جدول التصحيح ─────────────────────────
            with gr.Column(scale=2):
                gr.Markdown(
                    "#### 📝 الكلمات المتوقعة — عدّل عمود **Correction** "
                    "وضع ✓ في **Delete?** للكلمات عديمة المعنى"
                )

                correction_df = gr.Dataframe(
                    headers=["#", "Predicted", "Confidence", "Correction", "Delete?"],
                    datatype=["number", "str", "str", "str", "bool"],
                    col_count=(5, "fixed"),
                    interactive=True,
                    wrap=True,
                    label="جدول التصحيح",
                    height=420,
                )

                with gr.Row():
                    btn_copy_all = gr.Button(
                        "📋 نسخ Predicted → Correction (للكل)",
                        variant="secondary",
                    )
                    btn_save = gr.Button(
                        "💾 حفظ التصحيحات",
                        variant="primary",
                        size="lg",
                    )
                    btn_undo = gr.Button("↩️ تراجع عن آخر حفظ", variant="stop")

                save_status = gr.Markdown()

                gr.Markdown("---")
                gr.Markdown("#### 📊 النص الكامل")
                full_text_out = gr.Textbox(
                    label="النص المُجمَّع",
                    lines=4,
                    interactive=False,
                    show_copy_button=True,
                )

        # ── Handlers: OCR ────────────────────────────────────────────

        def do_ocr(image, lang_choice, session):
            if image is None:
                return (
                    pd.DataFrame(columns=["#","Predicted","Confidence","Correction","Delete?"]),
                    "⚠️ ارفع صورة أولاً",
                    "",
                    session,
                )
            t0 = time.time()
            pil = image if isinstance(image, Image.Image) else Image.fromarray(image)
            img_hash = _image_hash(pil)
            words    = _run_ocr_words(pil, lang_choice, use_gpu)

            if not words:
                return (
                    pd.DataFrame(columns=["#","Predicted","Confidence","Correction","Delete?"]),
                    "❌ لم يُكتشف نص — جرّب صورة أوضح أو لغة مختلفة",
                    "",
                    session,
                )

            df = _words_to_dataframe(words)
            elapsed = time.time() - t0
            learned_count = sum(1 for w in words if w.get("learned"))
            full_text = " ".join(w["word"] for w in words)

            status = (
                f"✅ {len(words)} كلمة مكتشفة في {elapsed:.1f}s | "
                f"🧠 {learned_count} تصحيح مُتعلَّم مُطبَّق"
            )

            session = {
                "words":      words,
                "image_hash": img_hash,
                "last_df":    df,
            }
            return df[["#","Predicted","Confidence","Correction","Delete?"]], status, full_text, session

        btn_ocr.click(
            fn=do_ocr,
            inputs=[trainer_img, trainer_lang, session_state],
            outputs=[correction_df, trainer_status, full_text_out, session_state],
        )

        # ── Handler: نسخ Predicted → Correction ─────────────────────

        def copy_all_predicted(df):
            if df is None or (hasattr(df, "empty") and df.empty):
                return df
            df = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
            if "Predicted" in df.columns and "Correction" in df.columns:
                df["Correction"] = df["Predicted"]
            return df

        btn_copy_all.click(
            fn=copy_all_predicted,
            inputs=[correction_df],
            outputs=[correction_df],
        )

        # ── Handler: حفظ التصحيحات ───────────────────────────────────

        def save_corrections(df, lang_choice, session):
            if df is None or (hasattr(df, "empty") and df.empty):
                return "⚠️ لا توجد بيانات للحفظ — نفّذ OCR أولاً"
            if not TRAINER_AVAILABLE:
                return "❌ قاعدة البيانات غير متاحة"

            df = df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
            words = session.get("words", [])
            lang_cfg = LANG_MAP.get(lang_choice, LANG_MAP["Auto-Detect 🔍"])

            items = []
            try:
                for i, row in df.iterrows():
                    predicted  = str(row.get("Predicted",  "")).strip()
                    correction = str(row.get("Correction", "")).strip()
                    deleted    = bool(row.get("Delete?",    False))
                    conf_raw   = 0.0

                    # استخرج الثقة الخامة من session إن وجدت
                    if i < len(words):
                        conf_raw = words[i].get("confidence", 0.0)
                        lang_code = words[i].get("lang", lang_cfg["code"])
                    else:
                        lang_code = lang_cfg["code"]
                        if lang_code == "auto":
                            lang_code = "ar"

                    items.append({
                        "idx":        i,
                        "predicted":  predicted,
                        "corrected":  correction,
                        "lang":       lang_code,
                        "confidence": conf_raw,
                        "deleted":    deleted,
                    })
            except Exception as e:
                return f"❌ خطأ في قراءة الجدول: {e}"

            img_hash = session.get("image_hash", "")
            saved    = DB.save_batch(items, image_hash=img_hash)

            improved = sum(1 for it in items if it["predicted"] != it["corrected"] and not it["deleted"])
            deleted  = sum(1 for it in items if it["deleted"])

            return (
                f"✅ حُفظ {saved} تصحيح | "
                f"🔧 {improved} تحسين | "
                f"🗑️ {deleted} محذوف | "
                f"🧠 arabic_fixes.json مُحدَّث"
            )

        btn_save.click(
            fn=save_corrections,
            inputs=[correction_df, trainer_lang, session_state],
            outputs=[save_status],
        )

        # ── Handler: تراجع ───────────────────────────────────────────

        def do_undo():
            if not TRAINER_AVAILABLE:
                return "❌ قاعدة البيانات غير متاحة"
            cnt, bid = DB.undo_last_batch()
            if cnt == 0:
                return "⚠️ لا توجد دفعة للتراجع عنها"
            return f"↩️ تم حذف {cnt} تصحيح (batch: {bid})"

        btn_undo.click(fn=do_undo, outputs=[save_status])

        # ── Handler: Clear ────────────────────────────────────────────

        def do_clear():
            empty_df = pd.DataFrame(columns=["#","Predicted","Confidence","Correction","Delete?"])
            return empty_df, "_جاهز_", "", {"words":[],"image_hash":"","last_df":None}

        btn_clear.click(
            fn=do_clear,
            outputs=[correction_df, trainer_status, full_text_out, session_state],
        )

    # ══════════════════════════════════════════════════════════════════
    # Tab B: 📚 Review DB
    # ══════════════════════════════════════════════════════════════════
    with gr.Tab("📚 Review DB") as tab_b:
        TABS.append(tab_b)

        gr.HTML("""
        <div style="background:#0d1117;border-radius:8px;padding:14px;margin-bottom:12px">
          <h3 style="color:#58a6ff;margin:0">📚 مراجعة قاعدة التصحيحات</h3>
          <p style="color:#8b949e;margin:4px 0">
            استعرض، تحقق، واحذف التصحيحات المحفوظة.
          </p>
        </div>
        """)

        with gr.Row():
            db_lang_filter = gr.Dropdown(
                label="فلترة بالغة",
                choices=["All", "ar", "en", "de"],
                value="All",
            )
            db_improved_only = gr.Checkbox(label="التصحيحات فقط (تحسينات)", value=False)
            db_limit = gr.Slider(10, 500, value=100, step=10, label="عدد السجلات")
            btn_refresh_db = gr.Button("🔄 تحديث", variant="primary")

        db_table = gr.Dataframe(
            headers=["ID", "Predicted", "Corrected", "Lang", "Confidence", "Improved?", "Date"],
            interactive=False,
            label="سجلات التصحيح",
            height=400,
            wrap=True,
        )

        with gr.Row():
            del_id_input = gr.Number(label="ID للحذف", precision=0)
            btn_delete   = gr.Button("🗑️ حذف سجل", variant="stop")
            del_status   = gr.Markdown()

        gr.Markdown("---")
        gr.Markdown("#### 📊 إحصائيات قاعدة البيانات")
        db_stats_out = gr.JSON(label="Statistics")

        # ── Handlers ────────────────────────────────────────────────

        def refresh_db(lang_filter, improved_only, limit):
            if not TRAINER_AVAILABLE:
                return pd.DataFrame(), {}
            lang  = None if lang_filter == "All" else lang_filter
            rows  = DB.get_corrections(limit=int(limit), lang=lang, improved_only=improved_only)
            stats = DB.stats()
            data  = [
                [r["id"], r["predicted"], r["corrected"], r["lang"],
                 f"{r['confidence']:.0%}", "✅" if r["improved"] else "—", r["created_at"]]
                for r in rows
            ]
            df = pd.DataFrame(
                data,
                columns=["ID","Predicted","Corrected","Lang","Confidence","Improved?","Date"]
            )
            return df, stats

        btn_refresh_db.click(
            fn=refresh_db,
            inputs=[db_lang_filter, db_improved_only, db_limit],
            outputs=[db_table, db_stats_out],
        )

        def delete_row(row_id):
            if not TRAINER_AVAILABLE or not row_id:
                return "⚠️ أدخل ID صحيح"
            DB.delete_correction(int(row_id))
            return f"🗑️ حُذف السجل #{int(row_id)}"

        btn_delete.click(fn=delete_row, inputs=[del_id_input], outputs=[del_status])

    # ══════════════════════════════════════════════════════════════════
    # Tab C: 📤 Sync (GitHub + Google Drive)
    # ══════════════════════════════════════════════════════════════════
    with gr.Tab("📤 Sync") as tab_c:
        TABS.append(tab_c)

        gr.HTML("""
        <div style="background:#0d1117;border-radius:8px;padding:14px;margin-bottom:12px">
          <h3 style="color:#58a6ff;margin:0">📤 مزامنة قاعدة التصحيحات</h3>
          <p style="color:#8b949e;margin:4px 0">
            احفظ تصحيحاتك على GitHub و Google Drive لتبقى آمنة ومتزامنة.
          </p>
        </div>
        """)

        with gr.Row():
            # ── GitHub ──────────────────────────────────────────────
            with gr.Column():
                gr.Markdown("#### 🐙 GitHub")
                github_token = gr.Textbox(
                    label="GitHub Token (ghp_...)",
                    placeholder="ghp_xxxxxxxxxxxxxxxx",
                    type="password",
                    max_lines=1,
                )
                github_repo = gr.Textbox(
                    label="Repository",
                    value="DrAbdulmalek/OmniFile_Processor",
                    max_lines=1,
                )
                btn_push_gh = gr.Button("🚀 Push to GitHub", variant="primary")
                gh_status   = gr.Markdown()

            # ── Google Drive / Local ────────────────────────────────
            with gr.Column():
                gr.Markdown("#### ☁️ Google Drive / تحميل محلي")
                gr.Markdown(
                    "اضغط **Export** لتحميل ملف JSON ثم ارفعه يدوياً إلى Drive "
                    "أو استخدمه في الـ Colab مع `google.colab.files.download()`"
                )
                btn_export_json = gr.Button("⬇️ Export JSON", variant="secondary")
                export_file     = gr.File(label="ملف التصدير")
                export_status   = gr.Markdown()

        gr.Markdown("---")
        gr.Markdown("#### 🔁 تحديث arabic_fixes.json من التصحيحات المتراكمة")
        btn_update_fixes = gr.Button("🔄 تحديث القاموس العربي", variant="secondary")
        fixes_status     = gr.Markdown()

        # ── Handlers ────────────────────────────────────────────────

        def push_to_github(token, repo):
            if not token.strip():
                return "❌ أدخل GitHub token"
            if not TRAINER_AVAILABLE:
                return "❌ قاعدة البيانات غير متاحة"
            try:
                export_path = DB.export_json("artifacts/corrections_db_export.json")
                repo_dir = Path(__file__).parent.parent
                subprocess.run(["git","add","artifacts/corrections_db_export.json",
                                "data/arabic_fixes.json"], cwd=repo_dir)
                ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
                msg = f"sync: corrections DB export {ts}"
                r1  = subprocess.run(["git","commit","-m",msg], cwd=repo_dir,
                                     capture_output=True, text=True)
                r2  = subprocess.run([
                    "git","push",
                    f"https://{token}@github.com/{repo}.git","main"
                ], cwd=repo_dir, capture_output=True, text=True)
                if r2.returncode == 0:
                    return f"✅ تم الرفع إلى GitHub — {ts}"
                else:
                    return f"⚠️ {r2.stderr[:200]}"
            except Exception as e:
                return f"❌ {e}"

        btn_push_gh.click(
            fn=push_to_github,
            inputs=[github_token, github_repo],
            outputs=[gh_status],
        )

        def export_json_file():
            if not TRAINER_AVAILABLE:
                return None, "❌ قاعدة البيانات غير متاحة"
            path  = DB.export_json("/tmp/omnifile_corrections_export.json")
            size  = os.path.getsize(path)
            stats = DB.stats()
            return path, (
                f"✅ {stats['total_corrections']} تصحيح مُصدَّر — "
                f"{size:,} bytes"
            )

        btn_export_json.click(
            fn=export_json_file,
            outputs=[export_file, export_status],
        )

        def update_fixes():
            if not TRAINER_AVAILABLE:
                return "❌ قاعدة البيانات غير متاحة"
            n = DB.update_arabic_fixes()
            return f"✅ تم تحديث arabic_fixes.json — {n} إدخال جديد مُضاف"

        btn_update_fixes.click(fn=update_fixes, outputs=[fixes_status])

    return TABS


# ══════════════════════════════════════════════════════════════════════
# نقطة التشغيل المستقل (للاختبار)
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    USE_GPU = False
    try:
        import torch
        USE_GPU = torch.cuda.is_available()
    except ImportError:
        pass

    with gr.Blocks(title="OmniFile Word Trainer", theme=gr.themes.Soft()) as demo:
        gr.HTML("<h2 style='text-align:center'>✏️ OmniFile Word Trainer v5.0</h2>")
        build_trainer_tabs(use_gpu=USE_GPU)

    demo.launch(share=True, server_name="0.0.0.0", server_port=7861)
