"""
HandwrittenOCR - مولّد المرجع الدراسي v5.3 (محسّن)
======================================================
مبنية على اقتراحات Gemini:
- table_to_markdown(): تحويل الجداول اليدوية إلى Markdown
- generate_study_guide(): توليد مرجع دراسي بصيغة Markdown
  من البيانات المستخرجة من الخط اليدوي
- export_study_guide_html(): تصدير المرجع مع تلوين المصطلحات البرمجية
- generate_mermaid_diagram(): مخطط Mermaid للعلاقات بين المصطلحات
- generate_flashcards(): بطاقات تعليمية من المفردات والملاحظات
- export_flashcards_anki(): تصدير بطاقات بتنسيق Anki CSV

استخدامه:
    from src.study_guide import (
        generate_study_guide, table_to_markdown,
        generate_mermaid_diagram, generate_flashcards,
        export_flashcards_anki, export_study_guide_html,
    )
"""

import os
import json
import csv
import logging
import random
from datetime import datetime
from typing import Optional
from collections import defaultdict

import pandas as pd

logger = logging.getLogger("HandwrittenOCR")


# ===================== تحويل الجداول إلى Markdown =====================

def table_to_markdown(cells_data: list[dict], columns: list[str] = None) -> str:
    """
    تحويل البيانات المقطوعة من الجداول إلى تنسيق Markdown.

    Parameters:
        cells_data: قائمة بأزواج القاموس {english, arabic, context}
        columns: أسماء الأعمدة (اختياري)

    Returns:
        نص Markdown يمثل الجدول
    """
    if not cells_data:
        return ""

    if columns is None:
        # استخراج المفاتيح المتاحة
        available_keys = set()
        for row in cells_data:
            available_keys.update(row.keys())
        columns = [k for k in ["english", "arabic", "context", "page"]
                    if k in available_keys]

    if not columns:
        return ""

    # بناء رأس الجدول
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    # بناء الصفوف
    rows = []
    for row in cells_data:
        cells = [str(row.get(col, "")) for col in columns]
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header, separator] + rows)


# ===================== تلوين المصطلحات البرمجية =====================

# ألوان ANSI للتلوين في Markdown
SYNTAX_COLORS = {
    "keywords": "#2563EB",     # أزرق — الكلمات المحجوزة
    "types": "#16A34A",        # أخضر — أنواع البيانات
    "functions": "#9333EA",    # بنفسجي — الدوال والمكتبات
    "numbers": "#DC2626",      # أحمر — الأرقام
}

PYTHON_BUILTINS_COLOR = {
    "print", "input", "len", "range", "type", "int", "str", "float",
    "list", "dict", "set", "tuple", "bool", "open", "super", "self",
    "append", "extend", "pop", "sort", "join", "split", "strip",
    "enumerate", "zip", "map", "filter", "sorted", "reversed",
}

DATA_TYPES = {
    "integers", "floating", "points", "strings", "boolean", "list",
    "dictionary", "tuple", "none", "mutable", "immutable",
}


def highlight_python_terms(text: str) -> str:
    """
    تمييز المصطلحات البرمجية بالنص.
    يُستخدم لتلوين الكلمات داخل مرجع Markdown.

    Parameters:
        text: النص الأصلي

    Returns:
        النص مع HTML spans للتلوين (يعمل في Markdown)
    """
    if not text:
        return text

    words = text.split()
    highlighted = []
    for word in words:
        clean = word.strip(".,;:!?\"'()-*").lower()

        if clean in PYTHON_BUILTINS_COLOR:
            highlighted.append(
                f'<span style="color:{SYNTAX_COLORS["functions"]}">{word}</span>'
            )
        elif clean in DATA_TYPES:
            highlighted.append(
                f'<span style="color:{SYNTAX_COLORS["types"]}">{word}</span>'
            )
        else:
            highlighted.append(word)

    return " ".join(highlighted)


# ===================== توليد المرجع الدراسي =====================

def generate_study_guide(
    db,
    output_path: Optional[str] = None,
    title: str = "مرجع دراسة — مستخرج من الملاحظات اليدوية",
    y_tolerance: int = 25,
    highlight_terms: bool = True,
) -> str:
    """
    توليد مرجع دراسي بصيغة Markdown من البيانات الموثقة.

    يحوّل الكلمات المكتوبة بخط اليد إلى مستند منظم يحتوي:
    1. عنوان وعنوان فرعي لكل صفحة
    2. جداول المصطلحات (إنجليزي-عربي)
    3. جمل مُعاد بناؤها
    4. تلوين المصطلحات البرمجية (اختياري)

    Parameters:
        db: كائن قاعدة البيانات
        output_path: مسار حفظ الملف (اختياري)
        title: عنوان المرجع
        y_tolerance: حد تباعد Y لنفس السطر
        highlight_terms: تفعيل تلوين المصطلحات البرمجية

    Returns:
        محتوى Markdown الكامل
    """
    # جلب البيانات
    words = db.get_all()
    if not words:
        logger.warning("لا توجد بيانات لتوليد المرجع الدراسي")
        return ""

    df = pd.DataFrame(words)
    pages = sorted(df["page_num"].dropna().unique())

    guide = []
    guide.append(f"# {title}\n")
    guide.append(f"تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    guide.append(f"عدد الصفحات: {len(pages)}\n")
    guide.append("---\n")

    for pg in pages:
        pg_words = df[df["page_num"] == pg].sort_values(["y", "x"])
        if pg_words.empty:
            continue

        guide.append(f"\n## صفحة رقم: {int(pg)}\n")

        # 1. استخراج الجداول (أزواج إنجليزي-عربي)
        table_data = _extract_table_from_page(pg_words, y_tolerance)
        if table_data:
            guide.append("### جداول المصطلحات\n")
            guide.append(table_to_markdown(table_data))
            guide.append("")

        # 2. إعادة بناء الجمل
        sentences = _reconstruct_page_sentences(pg_words, y_tolerance)
        if sentences:
            guide.append("### الملاحظات والشروحات\n")
            for sent in sentences:
                text = sent["text"]
                if highlight_terms:
                    text = highlight_python_terms(text)
                lang_indicator = sent.get("lang", "en")
                if lang_indicator == "ar":
                    guide.append(f"- {text}")
                else:
                    guide.append(f"- {text}  *(EN)*")
            guide.append("")

    content = "\n".join(guide)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"تم حفظ المرجع الدراسي في: {output_path}")

    return content


def generate_study_guide_full(
    db,
    output_dir: Optional[str] = None,
    title: str = "مرجع دراسة شامل — مستخرج من الملاحظات اليدوية",
    y_tolerance: int = 25,
    highlight_terms: bool = True,
    include_mermaid: bool = True,
    mermaid_type: str = "mindmap",
    include_flashcards: bool = True,
    flashcard_type: str = "bilingual",
    max_flashcards: int = 100,
) -> str:
    """
    توليد مرجع دراسي شامل بصيغة Markdown يتضمن:
    1. المرجع الأساسي (جداول + ملاحظات)
    2. مخطط Mermaid للعلاقات بين المصطلحات
    3. بطاقات تعليمية (Flashcards)

    هذا هو الإصدار المحسّن من generate_study_guide() الذي يجمع
    كل الميزات الجديدة في ملف واحد.

    Parameters:
        db: كائن قاعدة البيانات
        output_dir: مجلد الحفظ (اختياري)
        title: عنوان المرجع
        y_tolerance: حد تباعد Y لنفس السطر
        highlight_terms: تفعيل تلوين المصطلحات البرمجية
        include_mermaid: تضمين مخطط Mermaid
        mermaid_type: نوع المخطط ("mindmap" | "flowchart" | "graph")
        include_flashcards: تضمين البطاقات التعليمية
        flashcard_type: نوع البطاقات ("bilingual" | "concept" | "fill_blank")
        max_flashcards: الحد الأقصى للبطاقات

    Returns:
        محتوى Markdown الشامل
    """
    # المرجع الأساسي
    content = generate_study_guide(
        db=db,
        title=title,
        y_tolerance=y_tolerance,
        highlight_terms=highlight_terms,
    )

    if not content:
        return ""

    # إضافة مخطط Mermaid
    if include_mermaid:
        mermaid_code = generate_mermaid_diagram(db, diagram_type=mermaid_type)
        if mermaid_code:
            content += "\n\n---\n\n"
            content += "## خريطة المفردات (Mermaid)\n\n"
            content += f"```mermaid\n{mermaid_code}\n```\n"

    # إضافة البطاقات التعليمية
    if include_flashcards:
        cards = generate_flashcards(
            db=db,
            card_type=flashcard_type,
            max_cards=max_flashcards,
        )
        if cards:
            content += "\n\n---\n\n"
            content += flashcards_to_markdown(cards, title="البطاقات التعليمية")

    # حفظ الملفات
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

        # حفظ Markdown الشامل
        md_path = os.path.join(output_dir, "study_guide_full.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"تم حفظ المرجع الشامل في: {md_path}")

        # حفظ Mermaid منفصل
        if include_mermaid:
            mermaid_code = generate_mermaid_diagram(db, diagram_type=mermaid_type)
            if mermaid_code:
                mermaid_path = os.path.join(output_dir, "vocab_diagram.mmd")
                with open(mermaid_path, "w", encoding="utf-8") as f:
                    f.write(mermaid_code)
                logger.info(f"تم حفظ مخطط Mermaid في: {mermaid_path}")

        # حفظ Flashcards بصيغة Anki
        if include_flashcards:
            cards = generate_flashcards(
                db=db,
                card_type=flashcard_type,
                max_cards=max_flashcards,
            )
            if cards:
                anki_path = os.path.join(output_dir, "flashcards_anki.csv")
                export_flashcards_anki(cards, anki_path)

        # حفظ HTML
        html_path = os.path.join(output_dir, "study_guide_full.html")
        export_study_guide_html(content, html_path, title=title)

    return content


def _extract_table_from_page(
    df_page: pd.DataFrame,
    y_tolerance: int = 25,
) -> list[dict]:
    """
    استخراج أزواج المفردات (إنجليزي-عربي) من صفحة واحدة.
    يحاول ربط الكلمات الإنجليزية بالعربية على نفس السطر.
    """
    table_rows = []

    # تقسيم إلى أسطر
    lines = []
    current = [df_page.iloc[0].to_dict()]
    for i in range(1, len(df_page)):
        row = df_page.iloc[i].to_dict()
        if abs(row["y"] - current[-1]["y"]) <= y_tolerance:
            current.append(row)
        else:
            lines.append(current)
            current = [row]
    lines.append(current)

    for line in lines:
        en_words = []
        ar_words = []

        for w in line:
            text = str(w.get("predicted_text", "")).strip()
            if not text:
                continue

            # تمييز: إنجليزي (ASCII) مقابل عربي
            if all(ord(c) < 128 for c in text.replace(" ", "")):
                en_words.append(text)
            elif any("\u0600" <= c <= "\u06FF" for c in text):
                ar_words.append(text)

        if en_words or ar_words:
            table_rows.append({
                "english": " | ".join(en_words) if en_words else "",
                "arabic": " | ".join(ar_words) if ar_words else "",
            })

    return table_rows


def _extract_all_vocabulary(
    db,
) -> list[dict]:
    """
    استخراج جميع أزواج المفردات (إنجليزي-عربي) من قاعدة البيانات.
    يُستخدم لتوليد المخططات والبطاقات التعليمية.

    Returns:
        قائمة بأزواج {"english": ..., "arabic": ..., "page": ..., "context": ...}
    """
    words = db.get_all()
    if not words:
        return []

    df = pd.DataFrame(words)
    all_vocab = []
    pages = sorted(df["page_num"].dropna().unique())

    for pg in pages:
        pg_words = df[df["page_num"] == pg].sort_values(["y", "x"])
        if pg_words.empty:
            continue

        table_rows = _extract_table_from_page(pg_words)
        for row in table_rows:
            if row.get("english") or row.get("arabic"):
                row["page"] = int(pg)
                all_vocab.append(row)

    return all_vocab


def _reconstruct_page_sentences(
    df_page: pd.DataFrame,
    y_tolerance: int = 25,
) -> list[dict]:
    """إعادة بناء جمل من صفحة واحدة"""
    sentences = []

    lines = []
    current = [df_page.iloc[0].to_dict()]
    for i in range(1, len(df_page)):
        row = df_page.iloc[i].to_dict()
        if abs(row["y"] - current[-1]["y"]) <= y_tolerance:
            current.append(row)
        else:
            lines.append(current)
            current = [row]
    lines.append(current)

    for line in lines:
        texts = [
            str(w.get("predicted_text", "")).strip()
            for w in line
            if w.get("predicted_text") and str(w["predicted_text"]).strip()
        ]
        if not texts:
            continue

        text_preview = " ".join(texts)
        lang = "en"
        try:
            from langdetect import detect
            lang = detect(text_preview)
        except Exception:
            pass

        # ترتيب حسب اللغة
        sorted_line = sorted(line, key=lambda k: k["x"], reverse=(lang == "ar"))
        sentence = " ".join(
            str(w.get("predicted_text", "")) for w in sorted_line
        ).strip()

        if sentence:
            sentences.append({"text": sentence, "lang": lang})

    return sentences


# ===================== مخططات Mermaid =====================

def _sanitize_mermaid_id(text: str) -> str:
    """تنظيف النص ليكون معرّفاً صالحاً في Mermaid."""
    clean = text.strip()
    # استبدال الأحرف غير المسموحة
    for ch in ['"', "'", '(', ')', '{', '}', '[', ']', '<', '>', '/', '\\', '&', '#', '|', ';']:
        clean = clean.replace(ch, "_")
    clean = clean.replace(" ", "_")
    # إزالة التشكيل العربي
    arabic_diacritics = set("\u0610\u0611\u0612\u0613\u0614\u0615\u0616\u0617\u0618\u0619\u061A"
                          "\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652")
    clean = "".join(c for c in clean if c not in arabic_diacritics)
    if not clean:
        clean = "term"
    # التأكد من أن المعرّف لا يبدأ برقم
    if clean[0].isdigit():
        clean = "t_" + clean
    return clean[:40]  # حد أقصى للطول


def generate_mermaid_diagram(
    db,
    diagram_type: str = "mindmap",
    max_terms: int = 50,
) -> str:
    """
    توليد مخطط Mermaid من المفردات المستخرجة.

    يدعم ثلاثة أنواع من المخططات:
    - "mindmap": خريطة ذهنية للمصطلحات الإنجليزية مع ترجماتها العربية
    - "flowchart": مخطط انسيابي يربط المصطلحات حسب الصفحات
    - "graph": رسم بياني يعرض العلاقات بين المفردات

    Parameters:
        db: كائن قاعدة البيانات
        diagram_type: نوع المخطط ("mindmap" | "flowchart" | "graph")
        max_terms: الحد الأقصى للمصطلحات المعروضة

    Returns:
        نص Mermaid جاهز للتضمين في Markdown
    """
    vocab = _extract_all_vocabulary(db)
    if not vocab:
        logger.warning("لا توجد مفردات لتوليد مخطط Mermaid")
        return ""

    vocab = vocab[:max_terms]

    if diagram_type == "mindmap":
        return _generate_mindmap(vocab)
    elif diagram_type == "flowchart":
        return _generate_flowchart(vocab)
    elif diagram_type == "graph":
        return _generate_graph(vocab)
    else:
        logger.warning(f"نوع مخطط غير مدعوم: {diagram_type}")
        return _generate_mindmap(vocab)


def _generate_mindmap(vocab: list[dict]) -> str:
    """
    خريطة ذهنية: المصطلح الإنجليزي في الفرع الرئيسي، الترجمة العربية في الفرع الفرعي.
    يُجمّع المصطلحات حسب الصفحة المصدر.
    """
    lines = ["mindmap", "  root((المصطلحات))"]

    # تجميع حسب الصفحة
    by_page = defaultdict(list)
    for v in vocab:
        page_key = f"صفحة {v.get('page', '?')}"
        by_page[page_key].append(v)

    for page_label, terms in by_page.items():
        page_id = _sanitize_mermaid_id(page_label)
        lines.append(f"    {page_id}[{page_label}]")

        for term in terms:
            en = term.get("english", "").strip()
            ar = term.get("arabic", "").strip()

            if en and ar:
                en_id = _sanitize_mermaid_id(en)
                ar_id = _sanitize_mermaid_id(ar)
                lines.append(f"      {en_id}[{en}]")
                lines.append(f"        {ar_id}[{ar}]")
            elif en:
                en_id = _sanitize_mermaid_id(en)
                lines.append(f"      {en_id}[{en}]")
            elif ar:
                ar_id = _sanitize_mermaid_id(ar)
                lines.append(f"      {ar_id}[{ar}]")

    return "\n".join(lines)


def _generate_flowchart(vocab: list[dict]) -> str:
    """
    مخطط انسيابي: يربط المصطلحات حسب الصفحة المصدر.
    كل صفحة تمثل عقدة رئيسية، والمصطلحات تخرج منها.
    """
    lines = ["flowchart LR"]

    by_page = defaultdict(list)
    for v in vocab:
        page_key = f"صفحة {v.get('page', '?')}"
        by_page[page_key].append(v)

    page_ids = []
    for page_label, terms in by_page.items():
        page_id = _sanitize_mermaid_id(page_label)
        page_ids.append(page_id)
        lines.append(f"    {page_id}[{page_label}]")

        for term in terms:
            en = term.get("english", "").strip()
            ar = term.get("arabic", "").strip()
            label = f"{en} = {ar}" if en and ar else (en or ar)
            if label:
                term_id = _sanitize_mermaid_id(label)
                lines.append(f"    {page_id} --> {term_id}[{label}]")

    # ربط الصفحات ببعضها
    for i in range(len(page_ids) - 1):
        lines.append(f"    {page_ids[i]} -.-> {page_ids[i + 1]}")

    return "\n".join(lines)


def _generate_graph(vocab: list[dict]) -> str:
    """
    رسم بياني يعرض المصطلحات كعقد مرتبطة.
    يربط المصطلحات الإنجليزية بالعربية بخطوط متجهة.
    """
    lines = ["graph LR"]

    node_count = 0
    for v in vocab:
        en = v.get("english", "").strip()
        ar = v.get("arabic", "").strip()

        if en and ar:
            en_id = _sanitize_mermaid_id(en)
            ar_id = _sanitize_mermaid_id(ar)
            # تجنب تكرار العقد بنفس المعرّف
            lines.append(f"    {en_id}[{en}]")
            lines.append(f"    {ar_id}[{ar}]")
            lines.append(f"    {en_id} -->|ترجمة| {ar_id}")
            node_count += 1
        elif en:
            en_id = _sanitize_mermaid_id(en)
            lines.append(f"    {en_id}[{en}]")
            node_count += 1
        elif ar:
            ar_id = _sanitize_mermaid_id(ar)
            lines.append(f"    {ar_id}[{ar}]")
            node_count += 1

    return "\n".join(lines)


# ===================== البطاقات التعليمية (Flashcards) =====================

def generate_flashcards(
    db,
    card_type: str = "bilingual",
    max_cards: int = 100,
    shuffle: bool = True,
) -> list[dict]:
    """
    توليد بطاقات تعليمية (Flashcards) من البيانات المستخرجة.

    يدعم عدة أنواع من البطاقات:
    - "bilingual": بطاقات ثنائية اللغة (وجه إنجليزي / ظهر عربي)
    - "concept": بطاقات مفاهيمية (مصطلح / شرح من السياق)
    - "fill_blank": بطاقات ملء الفراغ (جملة مع كلمة محجوبة)

    Parameters:
        db: كائن قاعدة البيانات
        card_type: نوع البطاقات ("bilingual" | "concept" | "fill_blank")
        max_cards: الحد الأقصى للبطاقات
        shuffle: خلط البطاقات عشوائياً

    Returns:
        قائمة بطاقات، كل بطاقة dict{"front": ..., "back": ..., "tags": ...}
    """
    words = db.get_all()
    if not words:
        logger.warning("لا توجد بيانات لتوليد البطاقات التعليمية")
        return []

    df = pd.DataFrame(words)
    pages = sorted(df["page_num"].dropna().unique())

    if card_type == "bilingual":
        cards = _generate_bilingual_flashcards(df, pages)
    elif card_type == "concept":
        cards = _generate_concept_flashcards(df, pages)
    elif card_type == "fill_blank":
        cards = _generate_fill_blank_flashcards(df, pages)
    else:
        logger.warning(f"نوع بطاقات غير مدعوم: {card_type}")
        cards = _generate_bilingual_flashcards(df, pages)

    if shuffle:
        random.shuffle(cards)

    return cards[:max_cards]


def _generate_bilingual_flashcards(
    df: pd.DataFrame,
    pages: list,
) -> list[dict]:
    """
    بطاقات ثنائية اللغة: الوجه بالإنجليزية والظهر بالعربية (أو العكس).
    يُنشئ بطاقتين لكل زوج (EN→AR و AR→EN) لضمان التعلّم في الاتجاهين.
    """
    cards = []

    for pg in pages:
        pg_words = df[df["page_num"] == pg].sort_values(["y", "x"])
        if pg_words.empty:
            continue

        table_rows = _extract_table_from_page(pg_words)
        for row in table_rows:
            en = row.get("english", "").strip()
            ar = row.get("arabic", "").strip()

            if en and ar:
                # بطاقة EN → AR
                cards.append({
                    "front": en,
                    "back": ar,
                    "tags": [f"page_{int(pg)}", "EN-AR"],
                })
                # بطاقة AR → EN
                cards.append({
                    "front": ar,
                    "back": en,
                    "tags": [f"page_{int(pg)}", "AR-EN"],
                })

    return cards


def _generate_concept_flashcards(
    df: pd.DataFrame,
    pages: list,
) -> list[dict]:
    """
    بطاقات مفاهيمية: الوجه يحتوي مصطلح، والظهر يحتوي السياق
    أو الجملة التي ظهر فيها المصطلح في الملاحظات.
    """
    cards = []

    for pg in pages:
        pg_words = df[df["page_num"] == pg].sort_values(["y", "x"])
        if pg_words.empty:
            continue

        # استخراج المصطلحات من الجداول
        table_rows = _extract_table_from_page(pg_words)
        for row in table_rows:
            en = row.get("english", "").strip()
            ar = row.get("arabic", "").strip()

            if en:
                cards.append({
                    "front": en,
                    "back": f"الترجمة العربية: {ar}" if ar else "(بدون ترجمة عربية)",
                    "tags": [f"page_{int(pg)}", "concept"],
                })

        # استخراج الجمل التي تحتوي مصطلحات مفيدة
        sentences = _reconstruct_page_sentences(pg_words)
        for sent in sentences:
            text = sent.get("text", "").strip()
            if not text or len(text.split()) < 3:
                continue

            # إنشاء بطاقة من الجملة: الوجه = أول كلمتين، الظهر = بقية الجملة
            words_list = text.split()
            if len(words_list) >= 4:
                front = " ".join(words_list[:2]) + " ___"
                back = text
                cards.append({
                    "front": front,
                    "back": back,
                    "tags": [f"page_{int(pg)}", "sentence", sent.get("lang", "unknown")],
                })

    return cards


def _generate_fill_blank_flashcards(
    df: pd.DataFrame,
    pages: list,
) -> list[dict]:
    """
    بطاقات ملء الفراغ: تحجب كلمة عشوائية من الجملة.
    الوجه = الجملة مع فراغ، الظهر = الكلمة المحجوبة.
    """
    cards = []

    for pg in pages:
        pg_words = df[df["page_num"] == pg].sort_values(["y", "x"])
        if pg_words.empty:
            continue

        sentences = _reconstruct_page_sentences(pg_words)
        for sent in sentences:
            text = sent.get("text", "").strip()
            if not text or len(text.split()) < 3:
                continue

            words_list = text.split()
            # حجب كلمة عشوائية (ليس الأولى أو الأخيرة)
            blank_idx = random.randint(1, len(words_list) - 2) if len(words_list) > 2 else 0
            blanked_word = words_list[blank_idx]
            words_list[blank_idx] = "______"
            front = " ".join(words_list)

            cards.append({
                "front": front,
                "back": blanked_word,
                "tags": [f"page_{int(pg)}", "fill_blank", sent.get("lang", "unknown")],
            })

    return cards


def export_flashcards_anki(
    cards: list[dict],
    output_path: str,
    deck_name: str = "HandwrittenOCR::Study",
    include_tags: bool = True,
) -> str:
    """
    تصدير البطاقات التعليمية بتنسيق CSV متوافق مع Anki.

    تنسيق Anki CSV:
        front;back;tags (مع فاصل منقوطة إذا لم يُحدد)

    يمكن استيراد هذا الملف مباشرة في Anki عبر:
    File > Import > اختيار الملف > نوع: "Separated by Semicolon"

    Parameters:
        cards: قائمة البطاقات من generate_flashcards()
        output_path: مسار حفظ ملف CSV
        deck_name: اسم الباقة في Anki
        include_tags: تضمين الوسوم

    Returns:
        مسار الملف المحفوظ
    """
    if not cards:
        logger.warning("لا توجد بطاقات للتصدير")
        return ""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        # رأس Anki
        if include_tags:
            writer.writerow(["front", "back", "tags"])
        else:
            writer.writerow(["front", "back"])

        for card in cards:
            front = card.get("front", "").replace(";", ",").replace("\n", " ")
            back = card.get("back", "").replace(";", ",").replace("\n", " ")

            if include_tags:
                tags_str = " ".join(card.get("tags", []))
                writer.writerow([front, back, tags_str])
            else:
                writer.writerow([front, back])

    logger.info(f"تم حفظ {len(cards)} بطاقة في: {output_path}")
    return output_path


def flashcards_to_markdown(cards: list[dict], title: str = "بطاقات تعليمية") -> str:
    """
    تحويل البطاقات التعليمية إلى تنسيق Markdown.
    يمكن استخدام هذا مع أدوات مثل Obsidian أو Markdeep.

    Parameters:
        cards: قائمة البطاقات
        title: عنوان القسم

    Returns:
        نص Markdown يحتوي البطاقات
    """
    if not cards:
        return ""

    lines = [f"### {title}\n"]
    lines.append(f"العدد الإجمالي: {len(cards)} بطاقة\n")

    for i, card in enumerate(cards, 1):
        front = card.get("front", "")
        back = card.get("back", "")
        tags = card.get("tags", [])

        tags_str = f" `{'`, `'.join(tags)}`" if tags else ""
        lines.append(f"#### بطاقة {i}{tags_str}\n")
        lines.append(f"**الوجه:** {front}\n")
        lines.append(f"**الظهر:** ||{back}||\n")

    return "\n".join(lines)


# ===================== تصدير HTML (نسخة مطبوعة) =====================

def export_study_guide_html(
    markdown_content: str,
    output_path: str,
    title: str = "مرجع دراسة",
) -> str:
    """
    تحويل المرجع من Markdown إلى HTML أنيق للطباعة.
    يتضمن تنسيق CSS احترافي مع دعم RTL.
    """
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Amiri', 'Simplified Arabic', 'Segoe UI', sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 30px;
            line-height: 1.8;
            color: #1a1a2e;
            background: #ffffff;
        }}
        h1 {{
            text-align: center;
            color: #16213e;
            border-bottom: 3px solid #0f3460;
            padding-bottom: 15px;
        }}
        h2 {{
            color: #0f3460;
            border-right: 4px solid #e94560;
            padding-right: 15px;
        }}
        h3 {{
            color: #533483;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            font-size: 14px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px 15px;
            text-align: right;
        }}
        th {{
            background: #0f3460;
            color: white;
        }}
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        code {{
            background: #f4f4f8;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
        }}
        @media print {{
            body {{ padding: 0; }}
            h2 {{ page-break-before: auto; }}
            table {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
"""

    # تحويل Markdown بسيط إلى HTML
    lines = markdown_content.split("\n")
    in_table = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("# "):
            html += f"<h1>{stripped[2:]}</h1>\n"
        elif stripped.startswith("## "):
            html += f"<h2>{stripped[3:]}</h2>\n"
        elif stripped.startswith("### "):
            html += f"<h3>{stripped[4:]}</h3>\n"
        elif stripped.startswith("---"):
            html += "<hr>\n"
        elif stripped.startswith("|"):
            # جدول Markdown
            cells = [c.strip() for c in stripped.split("|") if c.strip()]
            if all(set(c) <= {"-"} for c in cells):
                continue  # فاصل الجدول
            if not in_table:
                html += "<table>\n"
                in_table = True
            html += "<tr>"
            for cell in cells:
                html += f"<td>{cell}</td>"
            html += "</tr>\n"
        else:
            if in_table:
                html += "</table>\n"
                in_table = False
            if stripped.startswith("- "):
                html += f"<li>{stripped[2:]}</li>\n"
            else:
                html += f"<p>{stripped}</p>\n"

    if in_table:
        html += "</table>\n"

    html += "</body>\n</html>"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"تم حفظ المرجع HTML في: {output_path}")

    return output_path


# === Compatibility class for OmniFile_v500_Colab ===
class StudyGuideGenerator:
    """واجهة متوافقة مع الـ notebook — تغلف الدوال المستقلة في class."""
    def __init__(self, db=None):
        self._db = db

    def generate(self, db=None, output_path=None, title=None, **kwargs):
        """توليد مرجع دراسي."""
        db = db or self._db
        if db is None:
            raise ValueError("Database object required")
        return generate_study_guide(db=db, output_path=output_path,
                                     title=title or "مرجع دراسة", **kwargs)

    def generate_full(self, db=None, output_dir=None, **kwargs):
        """توليد مرجع شامل مع Mermaid + Flashcards."""
        db = db or self._db
        if db is None:
            raise ValueError("Database object required")
        return generate_study_guide_full(db=db, output_dir=output_dir, **kwargs)

    def generate_flashcards(self, db=None, **kwargs):
        return generate_flashcards(db=db or self._db, **kwargs)

    def export_html(self, content, output_path, title=None):
        return export_study_guide_html(content, output_path, title=title or "مرجع دراسة")

    def export_anki(self, cards, output_path, **kwargs):
        return export_flashcards_anki(cards, output_path, **kwargs)
