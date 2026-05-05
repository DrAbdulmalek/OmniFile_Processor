"""
مولّد المرجع الدراسي — Study Guide Generator Module
======================================================
مولّد شامل للمراجع الدراسية من نتائج OCR.

القدرات:
- توليد مراجع Markdown منظمة من نتائج OCR
- مخططات Mermaid (خريطة ذهنية، مخطط انسيابي) من المفردات
- بطاقات Anki متوافقة (ثنائية اللغة، مفاهيمية، ملء فراغ)
- تصدير HTML أنيق مع دعم RTL و CSS للطباعة
- تعقيم التشكيل العربي لمعرّفات Mermaid صالحة
- تلوين المصطلحات البرمجية في Markdown

مثال الاستخدام:
    >>> generator = StudyGuideGenerator()
    >>> # من بيانات OCR مباشرة
    >>> ocr_data = [
    ...     {"text": "Python is great", "confidence": 0.95, "page": 1},
    ...     {"text": "الثعبان رائع", "confidence": 0.88, "page": 1},
    ... ]
    >>> md = generator.generate_markdown(ocr_data, title="My Notes")
    >>> # مخطط Mermaid
    >>> mermaid = generator.generate_mermaid(vocab, diagram_type="mindmap")
    >>> # بطاقات Anki
    >>> cards = generator.generate_flashcards(vocab, card_type="bilingual")
    >>> generator.export_anki(cards, "flashcards.csv")
    >>> # HTML
    >>> generator.export_html(md_content, "guide.html")
"""

from __future__ import annotations

import csv
import json
import logging
import os
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ======================================================================
# أدوات مساعدة
# ======================================================================

# ألوان التلوين للمصطلحات البرمجية
SYNTAX_COLORS = {
    "keywords": "#2563EB",
    "types": "#16A34A",
    "functions": "#9333EA",
    "numbers": "#DC2626",
}

PYTHON_BUILTINS = {
    "print", "input", "len", "range", "type", "int", "str", "float",
    "list", "dict", "set", "tuple", "bool", "open", "super", "self",
    "append", "extend", "pop", "sort", "join", "split", "strip",
    "enumerate", "zip", "map", "filter", "sorted", "reversed",
}

DATA_TYPES = {
    "integers", "floating", "points", "strings", "boolean", "list",
    "dictionary", "tuple", "none", "mutable", "immutable",
}


def sanitize_mermaid_id(text: str) -> str:
    """تعقيم النص ليكون معرّفاً صالحاً في Mermaid.

    يزيل التشكيل العربي والرموز الخاصة ويضمن بدءاً بحرف.

    Args:
        text: النص الأصلي.

    Returns:
        معرّف Mermaid صالح (بحد أقصى 40 حرفاً).
    """
    clean = text.strip()

    # استبدال الرموز غير المسموحة
    for ch in ['"', "'", '(', ')', '{', '}', '[', ']', '<', '>',
               '/', '\\', '&', '#', '|', ';', ':', ',', '.', '!', '?']:
        clean = clean.replace(ch, "_")

    # إزالة التشكيل العربي (Tashkeel / Diacritics)
    arabic_diacritics = set(
        "\u0610\u0611\u0612\u0613\u0614\u0615\u0616\u0617\u0618\u0619\u061A"
        "\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652"
    )
    clean = "".join(c for c in clean if c not in arabic_diacritics)

    # استبدال المسافات
    clean = clean.replace(" ", "_")

    # التأكد من أن المعرّف ليس فارغاً
    if not clean:
        clean = "term"

    # لا يبدأ برقم
    if clean[0].isdigit():
        clean = "t_" + clean

    # حد أقصى للطول
    return clean[:40]


def highlight_python_terms(text: str) -> str:
    """تلوين المصطلحات البرمجية في النص (HTML spans).

    Args:
        text: النص الأصلي.

    Returns:
        النص مع HTML spans للتلوين.
    """
    if not text:
        return text

    words = text.split()
    highlighted = []

    for word in words:
        clean = word.strip(".,;:!?\"'()-*").lower()

        if clean in PYTHON_BUILTINS:
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


def detect_language_simple(text: str) -> str:
    """كشف لغة النص ببساطة (عربي/إنجليزي/مختلط).

    Args:
        text: النص المراد فحصه.

    Returns:
        "ar", "en", أو "mixed".
    """
    if not text:
        return "unknown"

    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())

    if arabic_chars == 0 and latin_chars > 0:
        return "en"
    if latin_chars == 0 and arabic_chars > 0:
        return "ar"
    if arabic_chars > 0 and latin_chars > 0:
        return "mixed"
    return "unknown"


# ======================================================================
# فئة مولّد المرجع الدراسي
# ======================================================================

class StudyGuideGenerator:
    """مولّد شامل للمراجع الدراسية من نتائج OCR.

    يدعم:
    - Markdown مع تلوين المصطلحات
    - مخططات Mermaid (mindmap, flowchart)
    - بطاقات Anki متوافقة
    - HTML مع RTL و CSS للطباعة

    Attributes:
        highlight_terms: تفعيل تلوين المصطلحات البرمجية.
    """

    def __init__(
        self,
        highlight_terms: bool = True,
        default_language: str = "ar",
    ) -> None:
        """تهيئة مولّد المرجع الدراسي.

        Args:
            highlight_terms: تفعيل تلوين المصطلحات البرمجية في Markdown.
            default_language: اللغة الافتراضية ("ar" أو "en").
        """
        self.highlight_terms = highlight_terms
        self.default_language = default_language

    # ------------------------------------------------------------------
    # توليد Markdown
    # ------------------------------------------------------------------

    def generate_markdown(
        self,
        ocr_results: list[dict[str, Any]],
        title: str = "مرجع دراسة — مستخرج من الملاحظات",
        highlight: Optional[bool] = None,
        page_grouping: bool = True,
    ) -> str:
        """توليد مرجع دراسي بصيغة Markdown من نتائج OCR.

        Args:
            ocr_results: قائمة نتائج OCR، كل عنصر قاموس يحتوي:
                        - text: النص المستخرج
                        - confidence: الثقة (اختياري)
                        - page: رقم الصفحة (اختياري)
                        - source: المحرك (اختياري)
            title: عنوان المرجع.
            highlight: تفعيل التلوين (None = استخدام الإعداد الافتراضي).
            page_grouping: تجميع النتائج حسب الصفحات.

        Returns:
            محتوى Markdown الكامل.

        Example:
            >>> results = [
            ...     {"text": "Python programming", "page": 1, "confidence": 0.95},
            ...     {"text": "متغيرات", "page": 1, "confidence": 0.88},
            ... ]
            >>> md = generator.generate_markdown(results)
        """
        if not ocr_results:
            logger.warning("لا توجد بيانات OCR لتوليد المرجع الدراسي")
            return ""

        if highlight is None:
            highlight = self.highlight_terms

        lines: list[str] = []
        lines.append(f"# {title}\n")
        lines.append(f"تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        lines.append(f"عدد النتائج: {len(ocr_results)}\n")
        lines.append("---\n")

        if page_grouping:
            # تجميع حسب الصفحات
            pages: dict[Any, list[dict]] = defaultdict(list)
            for item in ocr_results:
                page = item.get("page", "غير محدد")
                pages[page].append(item)

            for page_num in sorted(
                pages.keys(),
                key=lambda p: int(p) if isinstance(p, (int, float)) else 0,
            ):
                items = pages[page_num]
                lines.append(f"\n## صفحة رقم: {page_num}\n")

                # استخراج المصطلحات (أزواج إنجليزي-عربي)
                vocab = self._extract_vocabulary_from_items(items)
                if vocab:
                    lines.append("### المصطلحات\n")
                    lines.append("| الإنجليزية | العربية |")
                    lines.append("| --- | --- |")
                    for v in vocab:
                        en = v.get("english", "").strip()
                        ar = v.get("arabic", "").strip()
                        if en or ar:
                            lines.append(f"| {en} | {ar} |")
                    lines.append("")

                # الملاحظات
                text_items = [i for i in items if i.get("text", "").strip()]
                if text_items:
                    lines.append("### الملاحظات والشروحات\n")
                    for item in text_items:
                        text = str(item["text"]).strip()
                        conf = item.get("confidence", 0)

                        if highlight:
                            text = highlight_python_terms(text)

                        lang_indicator = detect_language_simple(text)
                        conf_str = f" *(ثقة: {conf:.0%})*" if conf else ""

                        if lang_indicator == "ar":
                            lines.append(f"- {text}{conf_str}")
                        else:
                            lines.append(f"- {text} *(EN)*{conf_str}")

                    lines.append("")
        else:
            # بدون تجميع حسب الصفحات
            lines.append("\n## الملاحظات\n")
            for item in ocr_results:
                text = str(item.get("text", "")).strip()
                if not text:
                    continue

                if highlight:
                    text = highlight_python_terms(text)

                lang = detect_language_simple(text)
                if lang == "ar":
                    lines.append(f"- {text}")
                else:
                    lines.append(f"- {text} *(EN)*")

            lines.append("")

        content = "\n".join(lines)
        logger.info("تم توليد مرجع Markdown: %d سطر", len(lines))
        return content

    # ------------------------------------------------------------------
    # مخططات Mermaid
    # ------------------------------------------------------------------

    def generate_mermaid(
        self,
        vocabulary: list[dict[str, str]],
        diagram_type: str = "mindmap",
        max_terms: int = 50,
        title: str = "المصطلحات",
    ) -> str:
        """توليد مخطط Mermaid من المفردات.

        Args:
            vocabulary: قائمة أزواج {"english": ..., "arabic": ...}.
            diagram_type: نوع المخطط ("mindmap", "flowchart").
            max_terms: أقصى عدد مصطلحات.
            title: عنوان المخطط.

        Returns:
            نص Mermaid جاهز للتضمين.

        Example:
            >>> vocab = [
            ...     {"english": "variable", "arabic": "متغير"},
            ...     {"english": "function", "arabic": "دالة"},
            ... ]
            >>> mermaid = generator.generate_mermaid(vocab, diagram_type="mindmap")
            >>> print(f"```mermaid\\n{mermaid}\\n```")
        """
        if not vocabulary:
            logger.warning("لا توجد مفردات لتوليد مخطط Mermaid")
            return ""

        vocab = vocabulary[:max_terms]

        if diagram_type == "mindmap":
            return self._generate_mindmap(vocab, title)
        elif diagram_type == "flowchart":
            return self._generate_flowchart(vocab, title)
        else:
            logger.warning("نوع مخطط غير مدعوم: '%s' — استخدام mindmap", diagram_type)
            return self._generate_mindmap(vocab, title)

    def _generate_mindmap(
        self,
        vocab: list[dict[str, str]],
        title: str,
    ) -> str:
        """توليد خريطة ذهنية Mermaid."""
        lines = ["mindmap", f"  root(({title}))"]

        for v in vocab:
            en = v.get("english", "").strip()
            ar = v.get("arabic", "").strip()

            if en and ar:
                en_id = sanitize_mermaid_id(en)
                ar_id = sanitize_mermaid_id(ar)
                lines.append(f"    {en_id}[{en}]")
                lines.append(f"      {ar_id}[{ar}]")
            elif en:
                en_id = sanitize_mermaid_id(en)
                lines.append(f"    {en_id}[{en}]")
            elif ar:
                ar_id = sanitize_mermaid_id(ar)
                lines.append(f"    {ar_id}[{ar}]")

        return "\n".join(lines)

    def _generate_flowchart(
        self,
        vocab: list[dict[str, str]],
        title: str,
    ) -> str:
        """توليد مخطط انسيابي Mermaid."""
        lines = ["flowchart LR"]
        root_id = sanitize_mermaid_id(title)
        lines.append(f"    {root_id}[{title}]")

        for v in vocab:
            en = v.get("english", "").strip()
            ar = v.get("arabic", "").strip()

            if en and ar:
                en_id = sanitize_mermaid_id(en)
                ar_id = sanitize_mermaid_id(ar)
                label = f"{en} = {ar}"
                term_id = sanitize_mermaid_id(label)
                lines.append(f"    {root_id} --> {term_id}[{label}]")
            elif en:
                en_id = sanitize_mermaid_id(en)
                lines.append(f"    {root_id} --> {en_id}[{en}]")
            elif ar:
                ar_id = sanitize_mermaid_id(ar)
                lines.append(f"    {root_id} --> {ar_id}[{ar}]")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # بطاقات تعليمية (Flashcards)
    # ------------------------------------------------------------------

    def generate_flashcards(
        self,
        vocabulary: list[dict[str, str]],
        card_type: str = "bilingual",
        max_cards: int = 200,
        shuffle: bool = True,
    ) -> list[dict[str, Any]]:
        """توليد بطاقات تعليمية من المفردات.

        أنواع البطاقات:
        - "bilingual": ثنائية اللغة (وجه إنجليزي / ظهر عربي والعكس)
        - "concept": مفاهيمية (مصطلح / ترجمة)
        - "fill_blank": ملء فراغ (جملة مع كلمة محجوبة)

        Args:
            vocabulary: قائمة أزواج {"english": ..., "arabic": ...}.
            card_type: نوع البطاقات.
            max_cards: أقصى عدد بطاقات.
            shuffle: خلط البطاقات.

        Returns:
            قائمة بطاقات: [{"front": ..., "back": ..., "tags": ...}].

        Example:
            >>> vocab = [
            ...     {"english": "variable", "arabic": "متغير"},
            ...     {"english": "loop", "arabic": "حلقة"},
            ... ]
            >>> cards = generator.generate_flashcards(vocab, card_type="bilingual")
        """
        if not vocabulary:
            logger.warning("لا توجد مفردات لتوليد بطاقات تعليمية")
            return []

        if card_type == "bilingual":
            cards = self._generate_bilingual_cards(vocabulary)
        elif card_type == "concept":
            cards = self._generate_concept_cards(vocabulary)
        elif card_type == "fill_blank":
            cards = self._generate_fill_blank_cards(vocabulary)
        else:
            logger.warning("نوع بطاقات غير مدعوم: '%s' — استخدام bilingual", card_type)
            cards = self._generate_bilingual_cards(vocabulary)

        if shuffle:
            random.shuffle(cards)

        return cards[:max_cards]

    @staticmethod
    def _generate_bilingual_cards(vocab: list[dict[str, str]]) -> list[dict[str, Any]]:
        """بطاقات ثنائية اللغة: EN→AR و AR→EN."""
        cards = []

        for v in vocab:
            en = v.get("english", "").strip()
            ar = v.get("arabic", "").strip()

            if en and ar:
                # بطاقة EN → AR
                cards.append({
                    "front": en,
                    "back": ar,
                    "tags": ["EN-AR", "bilingual"],
                })
                # بطاقة AR → EN
                cards.append({
                    "front": ar,
                    "back": en,
                    "tags": ["AR-EN", "bilingual"],
                })

        return cards

    @staticmethod
    def _generate_concept_cards(vocab: list[dict[str, str]]) -> list[dict[str, Any]]:
        """بطاقات مفاهيمية: المصطلح والترجمة."""
        cards = []

        for v in vocab:
            en = v.get("english", "").strip()
            ar = v.get("arabic", "").strip()

            if en:
                cards.append({
                    "front": en,
                    "back": f"الترجمة العربية: {ar}" if ar else "(بدون ترجمة)",
                    "tags": ["concept"],
                })

            if ar and en:
                cards.append({
                    "front": ar,
                    "back": f"English: {en}",
                    "tags": ["concept"],
                })

        return cards

    @staticmethod
    def _generate_fill_blank_cards(vocab: list[dict[str, str]]) -> list[dict[str, Any]]:
        """بطاقات ملء فراغ: جملة بسيطة مع كلمة محجوبة."""
        cards = []

        for v in vocab:
            en = v.get("english", "").strip()
            ar = v.get("arabic", "").strip()

            if en:
                # جملة بسيطة: "The term ___ means ..."
                cards.append({
                    "front": f"The term ___ in English refers to: {ar}" if ar else f"Fill in: ___",
                    "back": en,
                    "tags": ["fill_blank", "EN"],
                })

            if ar:
                cards.append({
                    "front": f"المصطلح ___ بالإنجليزية يعني: {en}" if en else "أكمل: ___",
                    "back": ar,
                    "tags": ["fill_blank", "AR"],
                })

        return cards

    # ------------------------------------------------------------------
    # تصدير Anki
    # ------------------------------------------------------------------

    def export_anki(
        self,
        cards: list[dict[str, Any]],
        output_path: str | Path,
        deck_name: str = "OmniFile::Study",
        include_tags: bool = True,
    ) -> str:
        """تصدير بطاقات تعليمية بتنسيق CSV متوافق مع Anki.

        تنسيق Anki: front;back;tags (مع فاصل منقوطة).

        Args:
            cards: قائمة البطاقات من generate_flashcards().
            output_path: مسار حفظ ملف CSV.
            deck_name: اسم الباقة في Anki (يُكتب في التعليق).
            include_tags: تضمين الوسوم.

        Returns:
            مسار الملف المحفوظ.

        Example:
            >>> generator.export_anki(cards, "my_flashcards.csv")
            >>> # استيراد في Anki: File > Import > نوع: "Separated by Semicolon"
        """
        if not cards:
            logger.warning("لا توجد بطاقات للتصدير")
            return ""

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")

            # رأس مع تعليق اسم الباقة
            if include_tags:
                writer.writerow(["front", "back", "tags"])
            else:
                writer.writerow(["front", "back"])

            for card in cards:
                front = str(card.get("front", "")).replace(";", ",").replace("\n", " ")
                back = str(card.get("back", "")).replace(";", ",").replace("\n", " ")

                if include_tags:
                    tags_str = " ".join(card.get("tags", []))
                    writer.writerow([front, back, tags_str])
                else:
                    writer.writerow([front, back])

        logger.info(
            "تم تصدير %d بطاقة Anki إلى: %s (الباقة: %s)",
            len(cards), output_path, deck_name,
        )
        return str(output_path)

    # ------------------------------------------------------------------
    # تصدير HTML
    # ------------------------------------------------------------------

    def export_html(
        self,
        markdown_content: str,
        output_path: str | Path,
        title: str = "مرجع دراسة",
        include_print_css: bool = True,
    ) -> str:
        """تصدير المرجع إلى HTML أنيق مع دعم RTL و CSS للطباعة.

        Args:
            markdown_content: محتوى Markdown.
            output_path: مسار حفظ ملف HTML.
            title: عنوان الصفحة.
            include_print_css: تضمين أنماط الطباعة.

        Returns:
            مسار الملف المحفوظ.

        Example:
            >>> generator.export_html(markdown_text, "study_guide.html")
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print_css = ""
        if include_print_css:
            print_css = """
        @media print {
            body { padding: 0; margin: 0; }
            h2 { page-break-before: auto; }
            table { page-break-inside: avoid; }
            .no-print { display: none; }
        }"""

        html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        /* === خطوط === */
        @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Noto+Sans+Arabic:wght@400;700&display=swap');

        /* === أساسيات === */
        body {{
            font-family: 'Amiri', 'Noto Sans Arabic', 'Segoe UI', sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 30px;
            line-height: 1.9;
            color: #1a1a2e;
            background: #ffffff;
            direction: rtl;
        }}

        /* === عناوين === */
        h1 {{
            text-align: center;
            color: #16213e;
            border-bottom: 3px solid #0f3460;
            padding-bottom: 15px;
            font-size: 1.8em;
        }}
        h2 {{
            color: #0f3460;
            border-right: 4px solid #e94560;
            padding-right: 15px;
            margin-top: 2em;
            font-size: 1.4em;
        }}
        h3 {{
            color: #533483;
            font-size: 1.2em;
        }}

        /* === جداول === */
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
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        tr:hover {{
            background: #e8f0fe;
        }}

        /* === كود === */
        code {{
            background: #f4f4f8;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.9em;
            color: #d63384;
        }}
        pre {{
            background: #1e1e2e;
            color: #cdd6f4;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            direction: ltr;
            text-align: left;
        }}
        pre code {{
            background: none;
            color: inherit;
            padding: 0;
        }}

        /* === قوائم === */
        ul, ol {{
            padding-right: 25px;
        }}
        li {{
            margin-bottom: 5px;
        }}

        /* === فاصل === */
        hr {{
            border: none;
            height: 2px;
            background: linear-gradient(to right, #0f3460, #e94560, #0f3460);
            margin: 2em 0;
        }}

        /* === روابط === */
        a {{
            color: #2563eb;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}

        /* === ملخص === */
        .metadata {{
            background: #f0f4ff;
            border-right: 3px solid #2563eb;
            padding: 10px 15px;
            margin: 15px 0;
            font-size: 0.9em;
            color: #4a5568;
        }}

        /* === بطاقات === */
        .flashcard {{
            background: #fafafa;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        .flashcard-front {{
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 8px;
        }}
        .flashcard-back {{
            color: #718096;
            border-top: 1px dashed #cbd5e0;
            padding-top: 8px;
        }}
        .flashcard-tags {{
            font-size: 0.8em;
            color: #a0aec0;
            margin-top: 5px;
        }}

        /* === طباعة === */
        {print_css}
    </style>
</head>
<body>
"""

        # تحويل Markdown إلى HTML
        html += self._markdown_to_html(markdown_content)

        html += f"""
    <div class="no-print" style="text-align: center; margin-top: 30px; color: #999; font-size: 0.8em;">
        <p>تم الإنشاء بواسطة OmniFile Processor — {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
</body>
</html>
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("تم تصدير مرجع HTML إلى: %s", output_path)
        return str(output_path)

    # ------------------------------------------------------------------
    # أدوات مساعدة
    # ------------------------------------------------------------------

    @staticmethod
    def _markdown_to_html(md_content: str) -> str:
        """تحويل Markdown بسيط إلى HTML.

        يدعم: العناوين، الجداول، القوائم، الفواصل، الأكواد.
        """
        if not md_content:
            return ""

        html_lines: list[str] = []
        lines = md_content.split("\n")
        in_table = False
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            # كود
            if stripped.startswith("```"):
                if in_code_block:
                    html_lines.append("</code></pre>")
                    in_code_block = False
                else:
                    lang = stripped[3:].strip()
                    html_lines.append(f"<pre><code class=\"language-{lang}\">" if lang else "<pre><code>")
                    in_code_block = True
                continue

            if in_code_block:
                html_lines.append(stripped)
                continue

            # العناوين
            if stripped.startswith("# "):
                html_lines.append(f"<h1>{stripped[2:]}</h1>")
            elif stripped.startswith("## "):
                html_lines.append(f"<h2>{stripped[3:]}</h2>")
            elif stripped.startswith("### "):
                html_lines.append(f"<h3>{stripped[4:]}</h3>")
            elif stripped.startswith("#### "):
                html_lines.append(f"<h4>{stripped[5:]}</h4>")

            # فاصل
            elif stripped.startswith("---"):
                if in_table:
                    html_lines.append("</table>")
                    in_table = False
                html_lines.append("<hr>")

            # جدول
            elif stripped.startswith("|"):
                cells = [c.strip() for c in stripped.split("|") if c.strip()]

                # فاصل الجدول
                if all(set(c) <= {"-", ":"} for c in cells):
                    continue

                if not in_table:
                    html_lines.append("<table>")
                    # أول صف = رأس
                    header_cells = "".join(f"<th>{c}</th>" for c in cells)
                    html_lines.append(f"<tr>{header_cells}</tr>")
                    in_table = True
                else:
                    row_cells = "".join(f"<td>{c}</td>" for c in cells)
                    html_lines.append(f"<tr>{row_cells}</tr>")

            # قوائم
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if in_table:
                    html_lines.append("</table>")
                    in_table = False
                html_lines.append(f"<li>{stripped[2:]}</li>")
            else:
                # فحص قوائم مرقمة
                import re
                numbered_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
                if numbered_match:
                    if in_table:
                        html_lines.append("</table>")
                        in_table = False
                    html_lines.append(f"<li>{numbered_match.group(2)}</li>")
                else:
                    if in_table:
                        html_lines.append("</table>")
                        in_table = False
                    # فقرات عادية
                    html_lines.append(f"<p>{stripped}</p>")

        if in_table:
            html_lines.append("</table>")
        if in_code_block:
            html_lines.append("</code></pre>")

        return "\n".join(html_lines)

    @staticmethod
    def _extract_vocabulary_from_items(
        items: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        """استخراج أزواج المفردات (إنجليزي-عربي) من نتائج OCR.

        Args:
            items: قائمة نتائج OCR.

        Returns:
            قائمة أزواج {"english": ..., "arabic": ...}.
        """
        vocab = []

        for item in items:
            text = str(item.get("text", "")).strip()
            if not text:
                continue

            # فصل المكونات الإنجليزية والعربية
            en_parts = []
            ar_parts = []

            words = text.split()
            for word in words:
                clean = word.strip(".,;:!?\"'()-*")
                if not clean:
                    continue

                arabic_chars = sum(1 for c in clean if "\u0600" <= c <= "\u06FF")
                latin_chars = sum(1 for c in clean if c.isascii() and c.isalpha())

                if arabic_chars > latin_chars:
                    ar_parts.append(clean)
                elif latin_chars > 0:
                    en_parts.append(clean)

            if en_parts or ar_parts:
                vocab.append({
                    "english": " ".join(en_parts),
                    "arabic": " ".join(ar_parts),
                })

        return vocab

    # ------------------------------------------------------------------
    # توليد شامل
    # ------------------------------------------------------------------

    def generate_full_guide(
        self,
        ocr_results: list[dict[str, Any]],
        output_dir: str | Path,
        title: str = "مرجع دراسة شامل",
        include_mermaid: bool = True,
        include_flashcards: bool = True,
        card_type: str = "bilingual",
        max_cards: int = 200,
        mermaid_type: str = "mindmap",
    ) -> dict[str, str]:
        """توليد مرجع دراسي شامل بكل المخرجات.

        يُنشئ:
        1. Markdown شامل
        2. مخطط Mermaid
        3. بطاقات Anki
        4. HTML للطباعة

        Args:
            ocr_results: نتائج OCR.
            output_dir: مجلد الحفظ.
            title: عنوان المرجع.
            include_mermaid: تضمين مخطط Mermaid.
            include_flashcards: تضمين البطاقات.
            card_type: نوع البطاقات.
            max_cards: أقصى عدد بطاقات.
            mermaid_type: نوع المخطط.

        Returns:
            قاموس بمسارات الملفات المُنشأة.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        paths: dict[str, str] = {}

        # 1. Markdown
        md_content = self.generate_markdown(ocr_results, title=title)
        if md_content:
            md_path = output_dir / "study_guide.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            paths["markdown"] = str(md_path)
            logger.info("تم حفظ المرجع Markdown: %s", md_path)

        # استخراج المفردات
        vocab = self._extract_vocabulary_from_items(ocr_results)

        # 2. Mermaid
        if include_mermaid and vocab:
            mermaid_code = self.generate_mermaid(
                vocab, diagram_type=mermaid_type, title=title,
            )
            if mermaid_code:
                mermaid_path = output_dir / "vocab_diagram.mmd"
                with open(mermaid_path, "w", encoding="utf-8") as f:
                    f.write(mermaid_code)
                paths["mermaid"] = str(mermaid_path)

                # تضمين Mermaid في Markdown
                md_content += "\n\n---\n\n## خريطة المفردات (Mermaid)\n\n"
                md_content += f"```mermaid\n{mermaid_code}\n```\n"

                # إعادة حفظ Markdown المُحدَّث
                md_path = output_dir / "study_guide_full.md"
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                paths["markdown_full"] = str(md_path)

        # 3. Flashcards + Anki
        if include_flashcards and vocab:
            cards = self.generate_flashcards(
                vocab, card_type=card_type, max_cards=max_cards,
            )
            if cards:
                anki_path = output_dir / "flashcards_anki.csv"
                self.export_anki(cards, anki_path)
                paths["anki"] = str(anki_path)

                # تضمين البطاقات في Markdown
                md_content += "\n\n---\n\n## البطاقات التعليمية\n\n"
                md_content += f"العدد: {len(cards)} بطاقة\n\n"
                for i, card in enumerate(cards[:50], 1):
                    md_content += (
                        f"**{i}.** الوجه: `{card['front']}`\n"
                        f"   الظهر: ||{card['back']}||\n\n"
                    )

                # إعادة حفظ
                md_path = output_dir / "study_guide_full.md"
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                paths["markdown_full"] = str(md_path)

        # 4. HTML
        html_path = output_dir / "study_guide.html"
        self.export_html(md_content, html_path, title=title)
        paths["html"] = str(html_path)

        logger.info(
            "تم توليد مرجع شامل في: %s (%d ملف)",
            output_dir, len(paths),
        )

        return paths
