"""
src/correction_trainer_ui.py
══════════════════════════════
واجهة المصحح التدريجي — Word-by-Word Correction Trainer UI
============================================================
واجهة Gradio لمراجعة وتصحيح نصوص OCR كلمةً بكلمة.

الميزات (v5.0):
  ✅ بطاقة تفاعلية لكل كلمة (Predicted ← Correction ← Spell suggestions)
  ✅ اكتشاف اللغة تلقائياً من النص بعد التصحيح (لا اختيار يدوي)
  ✅ تصحيح إملائي (arabic_fixes + DB + pyspellchecker)
  ✅ زر [📋 نسخ] لكل كلمة + زر [💾 حفظ هذه] + زر [🗑️ حذف]
  ✅ [↩️ تراجع] عن آخر دفعة (batch undo)
  ✅ جدول كامل قابل للتحرير في نهاية الصفحة
  ✅ مراجعة قاعدة البيانات + مزامنة GitHub

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import hashlib, json, logging, os, subprocess, time
from datetime import datetime
from pathlib import Path
from typing import Optional
import gradio as gr
import numpy as np
import pandas as pd
from PIL import Image

logger = logging.getLogger(__name__)

# ── استيراد وحدات المشروع ────────────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from modules.core.word_trainer import WordCorrectionDB
    DB = WordCorrectionDB()
    DB_OK = True
except Exception as e:
    DB = None; DB_OK = False
    logger.warning("WordCorrectionDB: %s", e)

try:
    from modules.core.spell_checker import HybridSpellChecker
    SC = HybridSpellChecker()
    SC_OK = True
except Exception as e:
    SC = None; SC_OK = False
    logger.warning("HybridSpellChecker: %s", e)

LANG_FLAGS = {"ar": "🇸🇦 Arabic", "en": "🇬🇧 English",
              "de": "🇩🇪 Deutsch", "mixed": "🌐 Mixed"}

CONF_EMOJI = lambda c: "🟢" if c >= .85 else "🟡" if c >= .60 else "🔴"


# ══════════════════════════════════════════════════════════════════════
# دوال مساعدة
# ══════════════════════════════════════════════════════════════════════

def _img_hash(pil: Image.Image) -> str:
    arr = np.array(pil.convert("L").resize((64, 64)))
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def _detect_lang(text: str) -> str:
    if SC_OK:
        return SC.detect_language(text)
    ar = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
    return "ar" if ar > len(text) * 0.3 else "en"


def _run_ocr(pil: Image.Image, use_gpu: bool = False) -> list[dict]:
    """تشغيل OCR واستخراج الكلمات مع ثقة لكل كلمة."""
    words = []
    # EasyOCR (يعطي word-level results)
    try:
        import easyocr
        langs = ["ar", "en"]
        reader = easyocr.Reader(langs, gpu=use_gpu, verbose=False)
        for bbox, text, conf in reader.readtext(np.array(pil)):
            for w in text.split():
                w = w.strip()
                if not w:
                    continue
                lang = _detect_lang(w)
                # التصحيح المتعلَّم من قاعدة البيانات
                learned = DB.get_best_correction(w, lang) if DB_OK else None
                # التصحيح الإملائي التلقائي
                sp_corrected, _ = SC.auto_correct(w) if SC_OK else (w, lang)
                correction = learned or sp_corrected
                words.append({
                    "idx":        len(words),
                    "word":       w,
                    "correction": correction,
                    "confidence": round(float(conf), 3),
                    "lang":       lang,
                    "learned":    learned is not None,
                    "sp_changed": sp_corrected != w,
                })
        if words:
            return words
    except Exception as e:
        logger.warning("EasyOCR: %s", e)

    # Tesseract fallback
    try:
        import pytesseract
        data = pytesseract.image_to_data(pil, lang="ara+eng",
                                         output_type=pytesseract.Output.DICT)
        for i, w in enumerate(data["text"]):
            w = w.strip()
            if not w:
                continue
            conf = max(int(data["conf"][i]) / 100, 0.0)
            lang = _detect_lang(w)
            learned = DB.get_best_correction(w, lang) if DB_OK else None
            sp_corrected, _ = SC.auto_correct(w) if SC_OK else (w, lang)
            correction = learned or sp_corrected
            words.append({
                "idx": len(words), "word": w,
                "correction": correction,
                "confidence": round(conf, 3), "lang": lang,
                "learned": learned is not None,
                "sp_changed": sp_corrected != w,
            })
    except Exception as e:
        logger.warning("Tesseract: %s", e)

    return words


def _words_to_df(words: list[dict]) -> pd.DataFrame:
    rows = []
    for w in words:
        rows.append({
            "#":          w["idx"] + 1,
            "Predicted":  w["word"],
            "Conf":       f"{CONF_EMOJI(w['confidence'])} {w['confidence']:.0%}",
            "Lang":       LANG_FLAGS.get(w["lang"], w["lang"]),
            "Correction": w["correction"],
            "Learned?":   "🧠" if w["learned"] else ("✏️" if w["sp_changed"] else ""),
            "Delete?":    False,
        })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════
# بناء واجهة Gradio
# ══════════════════════════════════════════════════════════════════════

def build_trainer_tabs(use_gpu: bool = False) -> list:
    """بناء تبويبات المصحح التدريجي — يُستدعى من hf_app.py."""

    # ── State ────────────────────────────────────────────────────────
    sess = gr.State({"words": [], "hash": "", "cur": 0})

    TABS = []

    # ══════════════════════════════════════════════════════════════════
    # ✏️ Word Trainer
    # ══════════════════════════════════════════════════════════════════
    with gr.Tab("✏️ Word Trainer") as tab_a:
        TABS.append(tab_a)

        gr.HTML("""
        <div style="background:#0d1117;border-radius:8px;padding:14px;margin-bottom:10px">
          <h3 style="color:#58a6ff;margin:0">✏️ مصحح التعلم التدريجي</h3>
          <p style="color:#8b949e;margin:4px 0 0">
            رفع صورة → OCR تلقائي → تصحيح كلمة بكلمة → حفظ → يتعلم النظام ويتطور
          </p>
        </div>""")

        with gr.Row():
            # ── يسار: رفع الصورة ────────────────────────────────────
            with gr.Column(scale=1, min_width=280):
                img_in    = gr.Image(label="📷 صورة الخط اليدوي", type="pil",
                                     sources=["upload","clipboard"])
                btn_ocr   = gr.Button("🔍 استخراج الكلمات", variant="primary", size="lg")
                btn_clear = gr.Button("🗑️ مسح", size="sm")
                ocr_stat  = gr.Markdown("_جاهز — ارفع صورة_")

            # ── يمين: بطاقة الكلمة الحالية ───────────────────────────
            with gr.Column(scale=2):
                # بطاقة الكلمة
                word_card = gr.HTML("<div style='background:#161b22;border-radius:8px;"
                                    "padding:20px;text-align:center;color:#8b949e'>"
                                    "نتائج OCR ستظهر هنا</div>")

                with gr.Row():
                    btn_prev  = gr.Button("← السابق",  size="sm")
                    nav_info  = gr.Markdown("", elem_id="nav_info")
                    btn_next  = gr.Button("التالي →",  size="sm")

                corr_box  = gr.Textbox(
                    label="✏️ التصحيح — عدّل إن لزم",
                    lines=2, rtl=True, show_copy_button=True,
                    placeholder="الكلمة المصحَّحة...",
                )
                spell_sugg = gr.Markdown("")

                with gr.Row():
                    btn_copy_pred = gr.Button("📋 نسخ المتوقع",    size="sm")
                    btn_save_word = gr.Button("💾 حفظ هذه الكلمة", variant="primary", size="sm")
                    btn_del_word  = gr.Button("🗑️ حذف هذه الكلمة", variant="stop",    size="sm")

                word_save_stat = gr.Markdown()

        gr.Markdown("---")

        # ── جدول الكلمات الكامل ────────────────────────────────────
        with gr.Accordion("📋 جدول كل الكلمات (قابل للتحرير)", open=False):
            words_df = gr.Dataframe(
                headers=["#","Predicted","Conf","Lang","Correction","Learned?","Delete?"],
                datatype=["number","str","str","str","str","str","bool"],
                col_count=(7,"fixed"),
                interactive=True, wrap=True, height=380,
                label="جميع الكلمات — عدّل عمود Correction مباشرة",
            )
            with gr.Row():
                btn_copy_all  = gr.Button("📋 نسخ كل Predicted → Correction", size="sm")
                btn_spell_all = gr.Button("✨ تصحيح إملائي للكل",              size="sm")
                btn_save_all  = gr.Button("💾 حفظ الكل",  variant="primary",   size="sm")
                btn_undo      = gr.Button("↩️ تراجع",    variant="stop",        size="sm")
            batch_stat = gr.Markdown()

        gr.Markdown("---")
        gr.Markdown("#### ⚡ اقتراح إملائي سريع")
        with gr.Row():
            spell_in   = gr.Textbox(label="اكتب كلمة", placeholder="مثال: مرحبا", max_lines=1, scale=3)
            spell_lang = gr.Markdown("", scale=1)
        spell_out = gr.Textbox(label="الاقتراحات", lines=2, interactive=False)

        # ── Handlers ─────────────────────────────────────────────────

        def _make_word_card(word: dict, idx: int, total: int) -> str:
            lang_label = LANG_FLAGS.get(word["lang"], word["lang"])
            conf_e = CONF_EMOJI(word["confidence"])
            learned = "🧠 تصحيح متعلَّم" if word.get("learned") else (
                      "✏️ تصحيح إملائي"  if word.get("sp_changed") else "")
            return f"""
            <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:18px">
              <div style="display:flex;justify-content:space-between;margin-bottom:10px">
                <span style="color:#8b949e">كلمة {idx+1} / {total}</span>
                <span style="color:#58a6ff">{lang_label}</span>
              </div>
              <div style="font-size:2.2em;text-align:center;color:#e6edf3;
                          font-family:serif;margin:12px 0;direction:rtl">
                {word['word']}
              </div>
              <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
                <span style="background:#21262d;padding:4px 10px;border-radius:4px;color:#8b949e">
                  {conf_e} {word['confidence']:.0%}
                </span>
                {'<span style="background:#1f3228;padding:4px 10px;border-radius:4px;color:#3fb950">' + learned + '</span>' if learned else ''}
              </div>
            </div>"""

        def do_ocr(pil, session):
            if pil is None:
                return (gr.update(), "⚠️ ارفع صورة أولاً",
                        gr.update(), gr.update(), "", "", session)
            t0 = time.time()
            words  = _run_ocr(pil, use_gpu)
            if not words:
                return (gr.update(), "❌ لم يُكتشف نص",
                        gr.update(), gr.update(), "", "", session)
            session = {"words": words, "hash": _img_hash(pil), "cur": 0}
            w0  = words[0]
            df  = _words_to_df(words)
            sugg = SC.get_suggestions(w0["word"], lang=w0["lang"], n=5) if SC_OK else []
            elapsed = time.time() - t0
            learned_n = sum(1 for w in words if w.get("learned"))
            stat = (f"✅ {len(words)} كلمة في {elapsed:.1f}s | "
                    f"🧠 {learned_n} تصحيح مُتعلَّم | "
                    f"🌐 {LANG_FLAGS.get(_detect_lang(' '.join(w['word'] for w in words)),'')}")
            return (
                _make_word_card(w0, 0, len(words)),
                stat,
                df,
                f"كلمة 1 / {len(words)}",
                w0["correction"],
                ("💡 **اقتراحات:** " + " · ".join(sugg)) if sugg else "",
                session,
            )

        btn_ocr.click(
            do_ocr, [img_in, sess],
            [word_card, ocr_stat, words_df, nav_info, corr_box, spell_sugg, sess],
        )

        def navigate(direction, corr_text, session):
            words = session.get("words", [])
            cur   = session.get("cur", 0)
            # حفظ التصحيح الحالي في الـ state
            if 0 <= cur < len(words):
                words[cur]["correction"] = corr_text
            cur = max(0, min(len(words)-1, cur + direction))
            session["cur"] = cur
            if not words:
                return gr.update(), "", "", "", session
            w = words[cur]
            sugg = SC.get_suggestions(w["word"], lang=w["lang"], n=5) if SC_OK else []
            return (
                _make_word_card(w, cur, len(words)),
                f"كلمة {cur+1} / {len(words)}",
                w["correction"],
                ("💡 **اقتراحات:** " + " · ".join(sugg)) if sugg else "",
                session,
            )

        btn_prev.click(lambda c, s: navigate(-1, c, s),
                       [corr_box, sess], [word_card, nav_info, corr_box, spell_sugg, sess])
        btn_next.click(lambda c, s: navigate(+1, c, s),
                       [corr_box, sess], [word_card, nav_info, corr_box, spell_sugg, sess])

        # نسخ المتوقع للتصحيح
        def copy_predicted(session):
            words = session.get("words", [])
            cur   = session.get("cur", 0)
            if 0 <= cur < len(words):
                return words[cur]["word"]
            return ""

        btn_copy_pred.click(copy_predicted, [sess], [corr_box])

        # حفظ كلمة واحدة
        def save_one_word(corr_text, session):
            if not DB_OK:
                return "❌ قاعدة البيانات غير متاحة", session
            words = session.get("words", [])
            cur   = session.get("cur", 0)
            if not (0 <= cur < len(words)):
                return "⚠️ لا توجد كلمة محددة", session
            w = words[cur]
            lang = _detect_lang(corr_text) if corr_text.strip() else w["lang"]
            words[cur]["correction"] = corr_text
            words[cur]["lang"] = lang
            session["words"] = words
            DB.save_batch([{
                "idx": cur, "predicted": w["word"],
                "corrected": corr_text, "lang": lang,
                "confidence": w["confidence"],
            }], image_hash=session.get("hash",""))
            improved = w["word"] != corr_text
            return (
                f"✅ حُفظت: **{w['word']}** → **{corr_text}** "
                f"({'🔧 تحسين' if improved else '✓ تأكيد'}) | 🌐 {LANG_FLAGS.get(lang,lang)}",
                session,
            )

        btn_save_word.click(save_one_word, [corr_box, sess], [word_save_stat, sess])

        # حذف كلمة
        def delete_one_word(session):
            words = session.get("words", [])
            cur   = session.get("cur", 0)
            if 0 <= cur < len(words):
                words[cur]["correction"] = ""
                words[cur]["deleted"] = True
                session["words"] = words
            return f"🗑️ تم تحديد الكلمة #{cur+1} للحذف", session

        btn_del_word.click(delete_one_word, [sess], [word_save_stat, sess])

        # تصحيح إملائي سريع
        def do_spell_quick(word):
            if not word.strip():
                return "", ""
            lang = _detect_lang(word)
            sugg = SC.get_suggestions(word, lang=lang, n=6) if SC_OK else []
            lang_label = LANG_FLAGS.get(lang, lang)
            return lang_label, "\n".join(sugg) if sugg else "لا اقتراحات"

        spell_in.change(do_spell_quick, [spell_in], [spell_lang, spell_out])

        # نسخ الكل / تصحيح إملائي للكل
        def copy_all_predicted(df):
            df = pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df.copy()
            if "Predicted" in df.columns:
                df["Correction"] = df["Predicted"]
            return df

        def spell_all(df):
            df = pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df.copy()
            if "Predicted" not in df.columns or not SC_OK:
                return df
            for i, row in df.iterrows():
                word = str(row.get("Predicted","")).strip()
                if word:
                    corrected, _ = SC.auto_correct(word)
                    df.at[i, "Correction"] = corrected
                    # تحديث Lang تلقائياً من النص المصحَّح
                    df.at[i, "Lang"] = LANG_FLAGS.get(_detect_lang(corrected), corrected)
            return df

        btn_copy_all.click(copy_all_predicted, [words_df], [words_df])
        btn_spell_all.click(spell_all, [words_df], [words_df])

        # حفظ الكل
        def save_all(df, session):
            if not DB_OK:
                return "❌ قاعدة البيانات غير متاحة"
            df = pd.DataFrame(df) if not isinstance(df, pd.DataFrame) else df
            words = session.get("words", [])
            items = []
            for i, row in df.iterrows():
                predicted  = str(row.get("Predicted","")).strip()
                correction = str(row.get("Correction","")).strip()
                deleted    = bool(row.get("Delete?", False))
                # كشف اللغة من النص المصحَّح (ليس من الاختيار اليدوي)
                lang = _detect_lang(correction) if correction else "ar"
                conf = words[i]["confidence"] if i < len(words) else 0.0
                items.append({
                    "idx": i, "predicted": predicted, "corrected": correction,
                    "lang": lang, "confidence": conf, "deleted": deleted,
                })
            saved    = DB.save_batch(items, image_hash=session.get("hash",""))
            improved = sum(1 for it in items if it["predicted"] != it["corrected"] and not it["deleted"])
            deleted  = sum(1 for it in items if it["deleted"])
            return (f"✅ حُفظ {saved} | 🔧 {improved} تحسين | "
                    f"🗑️ {deleted} محذوف | 🧠 القاموس مُحدَّث")

        btn_save_all.click(save_all, [words_df, sess], [batch_stat])

        def do_undo():
            if not DB_OK:
                return "❌ قاعدة البيانات غير متاحة"
            cnt, bid = DB.undo_last_batch()
            return f"↩️ تراجع: حُذف {cnt} تصحيح (batch={bid})" if cnt else "⚠️ لا توجد دفعة للتراجع"

        btn_undo.click(do_undo, [], [batch_stat])

        def do_clear():
            empty = pd.DataFrame(columns=["#","Predicted","Conf","Lang","Correction","Learned?","Delete?"])
            blank = {"words":[],"hash":"","cur":0}
            return (
                "<div style='background:#161b22;border-radius:8px;padding:20px;"
                "text-align:center;color:#8b949e'>نتائج OCR ستظهر هنا</div>",
                "_جاهز_", empty, "", "", "", blank,
            )

        btn_clear.click(do_clear,
            outputs=[word_card, ocr_stat, words_df, nav_info, corr_box, spell_sugg, sess])

    # ══════════════════════════════════════════════════════════════════
    # 📚 Review DB
    # ══════════════════════════════════════════════════════════════════
    with gr.Tab("📚 Review DB") as tab_b:
        TABS.append(tab_b)

        gr.HTML("""<div style="background:#0d1117;border-radius:8px;padding:14px;margin-bottom:10px">
          <h3 style="color:#58a6ff;margin:0">📚 مراجعة قاعدة التصحيحات</h3>
          <p style="color:#8b949e;margin:4px 0 0">استعرض وتحقق واحذف التصحيحات المحفوظة</p>
        </div>""")

        with gr.Row():
            db_lang   = gr.Dropdown(["All","ar","en","de"], value="All", label="اللغة")
            db_impr   = gr.Checkbox(label="تحسينات فقط", value=False)
            db_limit  = gr.Slider(10, 500, value=100, step=10, label="عدد السجلات")
            btn_refresh = gr.Button("🔄 تحديث", variant="primary")

        db_tbl = gr.Dataframe(
            headers=["ID","Predicted","Corrected","Lang","Confidence","Improved?","Date"],
            interactive=False, height=380, wrap=True,
        )
        with gr.Row():
            del_id  = gr.Number(label="ID للحذف", precision=0)
            btn_del = gr.Button("🗑️ حذف سجل", variant="stop")
            del_st  = gr.Markdown()

        gr.Markdown("---")
        db_stats = gr.JSON(label="📊 إحصائيات")

        def refresh_db(lang, impr, limit):
            if not DB_OK:
                return pd.DataFrame(), {}
            lang_arg = None if lang == "All" else lang
            rows  = DB.get_corrections(limit=int(limit), lang=lang_arg, improved_only=impr)
            stats = DB.stats()
            data = [[r["id"],r["predicted"],r["corrected"],r["lang"],
                     f"{r['confidence']:.0%}","✅" if r["improved"] else "—",
                     r["created_at"]] for r in rows]
            df = pd.DataFrame(data,
                columns=["ID","Predicted","Corrected","Lang","Confidence","Improved?","Date"])
            return df, stats

        btn_refresh.click(refresh_db, [db_lang, db_impr, db_limit], [db_tbl, db_stats])

        def del_row(rid):
            if not DB_OK or not rid:
                return "⚠️ أدخل ID صحيح"
            DB.delete_correction(int(rid))
            return f"🗑️ حُذف السجل #{int(rid)}"

        btn_del.click(del_row, [del_id], [del_st])

    # ══════════════════════════════════════════════════════════════════
    # 📤 Sync
    # ══════════════════════════════════════════════════════════════════
    with gr.Tab("📤 Sync") as tab_c:
        TABS.append(tab_c)

        gr.HTML("""<div style="background:#0d1117;border-radius:8px;padding:14px;margin-bottom:10px">
          <h3 style="color:#58a6ff;margin:0">📤 مزامنة قاعدة التصحيحات</h3>
          <p style="color:#8b949e;margin:4px 0 0">رفع إلى GitHub وتحميل JSON للـ Drive</p>
        </div>""")

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### 🐙 GitHub — رفع التصحيحات")
                gh_token = gr.Textbox(label="GitHub Token", type="password",
                                      placeholder="ghp_...", max_lines=1)
                gh_repo  = gr.Textbox(label="Repository",
                                      value="DrAbdulmalek/OmniFile_Processor", max_lines=1)
                btn_push = gr.Button("🚀 Push to GitHub", variant="primary")
                gh_stat  = gr.Markdown()

            with gr.Column():
                gr.Markdown("#### ☁️ تحميل JSON")
                btn_export = gr.Button("⬇️ Export JSON", variant="secondary")
                exp_file   = gr.File(label="الملف")
                exp_stat   = gr.Markdown()

        gr.Markdown("---")
        btn_upd_fixes = gr.Button("🔄 تحديث arabic_fixes.json", variant="secondary")
        fixes_stat = gr.Markdown()

        def push_github(token, repo):
            if not token.strip(): return "❌ أدخل GitHub token"
            if not DB_OK:         return "❌ قاعدة البيانات غير متاحة"
            try:
                DB.export_json("artifacts/corrections_db_export.json")
                DB.update_arabic_fixes()
                repo_dir = Path(__file__).parent.parent
                subprocess.run(["git","add","artifacts/corrections_db_export.json",
                                "data/arabic_fixes.json"], cwd=repo_dir, capture_output=True)
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                r1 = subprocess.run(["git","commit","-m",f"sync: corrections DB {ts}"],
                                    cwd=repo_dir, capture_output=True, text=True)
                r2 = subprocess.run([
                    "git","push",
                    f"https://{token}@github.com/{repo}.git","main"
                ], cwd=repo_dir, capture_output=True, text=True)
                return f"✅ تم الرفع — {ts}" if r2.returncode == 0 else f"⚠️ {r2.stderr[:200]}"
            except Exception as e:
                return f"❌ {e}"

        btn_push.click(push_github, [gh_token, gh_repo], [gh_stat])

        def export_json():
            if not DB_OK: return None, "❌ قاعدة البيانات غير متاحة"
            path  = DB.export_json("/tmp/omnifile_corrections_export.json")
            stats = DB.stats()
            return path, f"✅ {stats['total_corrections']} تصحيح — {os.path.getsize(path):,} bytes"

        btn_export.click(export_json, [], [exp_file, exp_stat])

        def update_fixes():
            if not DB_OK: return "❌ قاعدة البيانات غير متاحة"
            n = DB.update_arabic_fixes()
            if SC_OK: SC.reload_fixes()  # تحميل الإصلاحات الجديدة في الـ spell checker
            return f"✅ arabic_fixes.json مُحدَّث — {n} إدخال جديد | ✨ SpellChecker مُحدَّث"

        btn_upd_fixes.click(update_fixes, [], [fixes_stat])

    return TABS


# ── تشغيل مستقل للاختبار ─────────────────────────────────────────────
if __name__ == "__main__":
    try: import torch; USE_GPU = torch.cuda.is_available()
    except: USE_GPU = False

    with gr.Blocks(title="OmniFile Word Trainer v5.0",
                   theme=gr.themes.Soft(primary_hue="blue"),
                   css=".gradio-container{max-width:1100px!important}") as demo:
        gr.HTML('<div style="text-align:center;padding:16px;background:#0d1117;border-radius:8px">'
                '<h2 style="color:#58a6ff;margin:0">✏️ OmniFile Word Trainer v5.0</h2>'
                '<p style="color:#8b949e;margin:4px 0">Dr. Abdulmalek Al-Husseini | Homs, Syria</p>'
                '</div>')
        build_trainer_tabs(use_gpu=USE_GPU)

    demo.launch(share=True, server_name="0.0.0.0", server_port=7861)
