"""اختبارات modules/export/markdown_exporter.py"""
import pytest
from modules.export.markdown_exporter import (
    blocks_to_markdown, export_to_markdown, detect_list_items, _table_to_markdown
)


@pytest.fixture
def sample_layout():
    return {"blocks": [
        {"type": "header",    "text": "عنوان الاختبار"},
        {"type": "paragraph", "text": "نص عربي تجريبي."},
        {"type": "caption",   "text": "تسمية صورة"},
        {"type": "table",     "cells": [["الاسم","القيمة"],["أ","1"],["ب","2"]]},
    ]}


def test_basic_markdown(sample_layout):
    md = blocks_to_markdown(sample_layout)
    assert "## " in md
    assert "عنوان الاختبار" in md
    assert "نص عربي" in md
    assert "|" in md  # table


def test_table_markdown():
    cells = [["الوحدة","الحالة"],["OCR","✅"],["NLP","✅"]]
    md = _table_to_markdown(cells)
    assert "الوحدة" in md
    assert "---:" in md   # RTL alignment
    assert md.count("|") >= 6


def test_export_to_file(sample_layout, tmp_path):
    out = str(tmp_path / "test.md")
    result = export_to_markdown(sample_layout, out)
    import os
    assert os.path.exists(out)
    assert len(result) > 10


def test_export_returns_string(sample_layout):
    result = export_to_markdown(sample_layout)
    assert isinstance(result, str)
    assert len(result) > 0


def test_detect_list_items():
    text = "• عنصر أول\n- عنصر ثانٍ\n1. عنصر رقمي\nنص عادي"
    items = detect_list_items(text)
    list_items = [i for i in items if i["type"] == "list_item"]
    assert len(list_items) == 3


def test_empty_layout():
    md = blocks_to_markdown({"blocks": []})
    assert md == ""


def test_rtl_false():
    layout = {"blocks": [{"type": "paragraph", "text": "Hello"}]}
    md = blocks_to_markdown(layout, rtl=False)
    assert "\u202b" not in md
