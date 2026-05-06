"""
HandwrittenOCR - إعادة تجميع الجمل v4.0
============================================
- إعادة بناء الجمل مع RTL للعربية
- استخراج المفردات ثنائية اللغة (إنجليزي-عربي)
- يتعامل مع DB v3 (verified + sentence_corrected)
"""

import logging
import pandas as pd
from langdetect import detect

logger = logging.getLogger("HandwrittenOCR")


def reconstruct_sentences(
    db,
    y_tolerance: int = 25,
    verified_only: bool = True,
) -> list[dict] | None:
    """
    إعادة تجميع الكلمات إلى جمل حسب الصفحة والسطر.
    يدعم RTL للعربية.
    """
    if verified_only:
        words = db.get_verified()
    else:
        words = db.get_all()

    if not words:
        logger.info("لا توجد بيانات لإعادة التجمع")
        return None

    all_sentences = []

    for page in set(w["page_num"] for w in words if w["page_num"]):
        p_words = [w for w in words if w["page_num"] == page]
        p_words.sort(key=lambda k: (k["y"], k["x"]))

        if not p_words:
            continue

        lines = []
        curr_line = [p_words[0]]
        for i in range(1, len(p_words)):
            row = p_words[i]
            if abs(row["y"] - curr_line[-1]["y"]) <= y_tolerance:
                curr_line.append(row)
            else:
                lines.append(curr_line)
                curr_line = [row]
        lines.append(curr_line)

        for line in lines:
            text_preview = " ".join(str(w["predicted_text"]) for w in line)
            try:
                lang = detect(text_preview)
            except Exception:
                lang = "en"

            sorted_line = sorted(
                line, key=lambda k: k["x"], reverse=(lang == "ar")
            )
            sentence = " ".join(str(w["predicted_text"]) for w in sorted_line)
            word_ids = [w["image_id"] for w in sorted_line]

            all_sentences.append({
                "page": page,
                "y_anchor": line[0]["y"],
                "lang": lang,
                "text": sentence,
                "word_ids": word_ids,
            })

    if not all_sentences:
        return None

    logger.info(f"تم تجميع {len(all_sentences)} جملة")
    return all_sentences


def reconstruct_sentences_direct(df: pd.DataFrame, y_tolerance: int = 25) -> list[str]:
    """
    إعادة بناء الجمل مباشرة من DataFrame.
    يُستخدم في auto_export لإنشاء النص الكامل.
    """
    try:
        from langdetect import detect
    except ImportError:
        detect = lambda _: "en"

    lines_out = []
    for pg in sorted(df["page_num"].dropna().unique()):
        pw = df[df["page_num"] == pg].sort_values(["y", "x"])
        if pw.empty:
            continue

        curr = [pw.iloc[0].to_dict()]
        line_groups = []
        for i in range(1, len(pw)):
            row = pw.iloc[i].to_dict()
            if abs(row["y"] - curr[-1]["y"]) <= y_tolerance:
                curr.append(row)
            else:
                line_groups.append(curr)
                curr = [row]
        line_groups.append(curr)

        for lg in line_groups:
            preview = " ".join(
                str(w.get("predicted_text", "")) for w in lg
            )
            try:
                lang = detect(preview)
            except Exception:
                lang = "en"
            sl = sorted(lg, key=lambda k: k["x"], reverse=(lang == "ar"))
            lines_out.append(
                " ".join(str(w.get("predicted_text", "")) for w in sl).strip()
            )

    return lines_out


def extract_bilingual_vocab(
    db,
    y_tolerance: int = 30,
    output_path: str | None = None,
) -> pd.DataFrame | None:
    """
    استخراج أزواج المفردات الإنجليزية-العربية من البيانات الموثقة.
    يربط الكلمات الإنجليزية والعربية على نفس السطر.

    Parameters:
        db: كائن قاعدة البيانات
        y_tolerance: حد تباعد Y لنفس السطر
        output_path: مسار حفظ CSV (اختياري)

    Returns:
        DataFrame بالأزواج [{english, arabic, page}, ...] أو None
    """
    words = db.get_verified()
    words = [
        w for w in words
        if w.get("status") in ("verified", "sentence_corrected")
    ]

    if not words:
        logger.warning("لا توجد كلمات موثقة لاستخراج القاموس")
        return None

    vocab_pairs = []

    for page in set(w["page_num"] for w in words if w["page_num"]):
        p_words = [w for w in words if w["page_num"] == page]
        p_words.sort(key=lambda k: (k["y"], k["x"]))

        if not p_words:
            continue

        # تقسيم إلى أسطر
        lines = []
        curr_line = [p_words[0]]
        for i in range(1, len(p_words)):
            row = p_words[i]
            if abs(row["y"] - curr_line[-1]["y"]) <= y_tolerance:
                curr_line.append(row)
            else:
                lines.append(curr_line)
                curr_line = [row]
        lines.append(curr_line)

        for line in lines:
            texts = [
                str(w["predicted_text"])
                for w in line
                if w["predicted_text"] and str(w["predicted_text"]).strip()
            ]

            # فلترة: كلمات إنجليزية (ASCII) وعربية (Unicode Arabic)
            en_words = [
                t for t in texts
                if t and all(ord(c) < 128 for c in t.replace(" ", ""))
            ]
            ar_words = [
                t for t in texts
                if t and any("\u0600" <= c <= "\u06FF" for c in t)
            ]

            if en_words or ar_words:
                vocab_pairs.append({
                    "english": " | ".join(en_words) if en_words else "",
                    "arabic": " | ".join(ar_words) if ar_words else "",
                    "page": page,
                })

    if not vocab_pairs:
        logger.warning("لم يتم العثور على أزواج مفردات")
        return None

    df = pd.DataFrame(vocab_pairs)
    logger.info(f"تم استخراج {len(df)} زوج من المفردات")

    if output_path:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(f"تم حفظ القاموس في: {output_path}")

    return df


def derive_word_corrections(original: str, corrected: str) -> list[dict]:
    """
    استخراج تصحيحات كلمة بكلمة من تصحيح جملة.
    يعمل فقط عندما يتطابق عدد الكلمات.
    """
    orig_words = original.split()
    corr_words = corrected.split()

    if len(orig_words) != len(corr_words):
        return []

    return [
        {"original": o, "corrected": c}
        for o, c in zip(orig_words, corr_words)
        if o != c
    ]
