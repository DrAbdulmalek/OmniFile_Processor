"""
إعادة تجميع الجمل (Sentence Reconstruction)
==============================================
مُرحَّل من src/reconstruction.py إلى modules/nlp/reconstruction.py
كجزء من خطة ترحيل src/ → modules/ (v4.2.0).

- إعادة بناء الجمل مع RTL للعربية
- استخراج المفردات ثنائية اللغة (إنجليزي-عربي)
- تسجيل مفصّل لكل خطوة تجميع وقرار اتجاه
"""

import logging
import traceback
import pandas as pd
from langdetect import detect

logger = logging.getLogger("modules.nlp.reconstruction")


def reconstruct_sentences(db, y_tolerance=25, verified_only=True) -> list[dict] | None:
    """
    إعادة تجميع الجمل من كلمات قاعدة البيانات مع تسجيل مفصّل.

    يكتشف اللغة لكل سطر ويقرر الاتجاه:
    - العربي: RTL (من اليمين لليسار)
    - الإنجليزي/الألماني: LTR (من اليسار لليمين)

    Args:
        db: كائن HandwritingDB (modules.core.handwriting_db أو src.database)
        y_tolerance: التسامح الرأسي لتجميع الكلمات في سطر واحد
        verified_only: هل يجلب الكلمات المؤكدة فقط

    Returns:
        قائمة جمل أو None
    """
    logger.info(f"reconstruct_sentences: y_tolerance={y_tolerance}, verified_only={verified_only}")

    if verified_only:
        words = db.get_verified()
        logger.debug(f"  get_verified(): {len(words) if words else 0} كلمة")
    else:
        words = db.get_all()
        logger.debug(f"  get_all(): {len(words) if words else 0} كلمة")

    if not words:
        logger.info("reconstruct_sentences: لا توجد كلمات في قاعدة البيانات")
        return None

    all_sentences = []
    pages = set(w["page_num"] for w in words if w["page_num"])
    logger.info(f"  {len(pages)} صفحة للمعالجة: {sorted(pages)}")

    for page in sorted(pages):
        p_words = [w for w in words if w["page_num"] == page]
        p_words.sort(key=lambda k: (k["y"], k["x"]))
        logger.debug(f"  صفحة {page}: {len(p_words)} كلمة")

        if not p_words:
            continue

        # تقسيم الكلمات إلى أسطر
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

        logger.debug(f"  صفحة {page}: {len(lines)} سطر")

        # تجميع كل سطر
        for line_idx, line in enumerate(lines):
            text_preview = " ".join(str(w["predicted_text"]) for w in line)
            logger.debug(f"    سطر {line_idx}: {len(line)} كلمة, preview='{text_preview[:60]}'")

            # كشف اللغة
            try:
                lang = detect(text_preview)
            except Exception:
                lang = "en"
                logger.debug(f"    فشل كشف اللغة — افتراضي: en")

            # ترتيب حسب اللغة
            is_rtl = (lang == "ar")
            sorted_line = sorted(line, key=lambda k: k["x"], reverse=is_rtl)

            sentence = " ".join(str(w["predicted_text"]) for w in sorted_line)
            word_ids = [w["image_id"] for w in sorted_line]

            all_sentences.append({
                "page": page,
                "y_anchor": line[0]["y"],
                "lang": lang,
                "text": sentence,
                "word_ids": word_ids,
            })

            direction = "RTL" if is_rtl else "LTR"
            logger.debug(f"    سطر {line_idx}: lang='{lang}', dir={direction}, text='{sentence[:50]}'")

    if not all_sentences:
        logger.info("reconstruct_sentences: لم يتم تجميع أي جملة")
        return None

    # إحصائيات
    langs = {}
    for s in all_sentences:
        langs[s["lang"]] = langs.get(s["lang"], 0) + 1

    logger.info(f"reconstruct_sentences: {len(all_sentences)} جملة, لغات={langs}")

    return all_sentences


def reconstruct_sentences_direct(df, y_tolerance=25) -> list[str]:
    """
    إعادة تجميع الجمل مباشرة من DataFrame مع تسجيل مفصّل.
    """
    logger.debug(f"reconstruct_sentences_direct: {len(df)} صف, y_tolerance={y_tolerance}")

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

        for lg_idx, lg in enumerate(line_groups):
            preview = " ".join(str(w.get("predicted_text", "")) for w in lg)
            try:
                lang = detect(preview)
            except Exception:
                lang = "en"
            sl = sorted(lg, key=lambda k: k["x"], reverse=(lang == "ar"))
            sentence = " ".join(str(w.get("predicted_text", "")) for w in sl).strip()
            lines_out.append(sentence)

    logger.debug(f"reconstruct_sentences_direct: {len(lines_out)} سطر ناتج")
    return lines_out


def extract_bilingual_vocab(db, y_tolerance=30, output_path=None) -> pd.DataFrame | None:
    """
    استخراج المفردات ثنائية اللغة مع تسجيل مفصّل.
    """
    logger.info(f"extract_bilingual_vocab: y_tolerance={y_tolerance}, output_path={output_path}")

    words = db.get_verified()
    words = [w for w in words if w.get("status") in ("verified", "sentence_corrected")]

    if not words:
        logger.info("extract_bilingual_vocab: لا توجد كلمات مؤكدة")
        return None

    logger.debug(f"  {len(words)} كلمة مؤكدة")

    vocab_pairs = []
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
            texts = [str(w["predicted_text"]) for w in line if w["predicted_text"] and str(w["predicted_text"]).strip()]
            en_words = [t for t in texts if t and all(ord(c) < 128 for c in t.replace(" ", ""))]
            ar_words = [t for t in texts if t and any("\u0600" <= c <= "\u06FF" for c in t)]

            if en_words or ar_words:
                vocab_pairs.append({
                    "english": " | ".join(en_words) if en_words else "",
                    "arabic": " | ".join(ar_words) if ar_words else "",
                    "page": page,
                })

    if not vocab_pairs:
        logger.info("extract_bilingual_vocab: لم يتم استخراج أي أزواج مفردات")
        return None

    df = pd.DataFrame(vocab_pairs)
    if output_path:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(f"  تم حفظ المفردات: {output_path} ({len(vocab_pairs)} زوج)")

    return df


def derive_word_corrections(original, corrected) -> list[dict]:
    """اشتقاق تصحيحات الكلمات من الأصل والنص المصحّح مع تسجيل."""
    orig_words = original.split()
    corr_words = corrected.split()

    if len(orig_words) != len(corr_words):
        logger.debug(f"derive_word_corrections: عدد الكلمات مختلف ({len(orig_words)} vs {len(corr_words)})")
        return []

    corrections = [{"original": o, "corrected": c} for o, c in zip(orig_words, corr_words) if o != c]
    if corrections:
        logger.debug(f"derive_word_corrections: {len(corrections)} تعديل: {corrections}")

    return corrections
