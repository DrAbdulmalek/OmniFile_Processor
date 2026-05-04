"""اختبارات modules/export/layout_preserving.py"""
import os
import pytest
from modules.export.layout_preserving import export_to_docx, ocr_result_to_layout


@pytest.fixture
def basic_layout():
    return {"blocks": [
        {"type": "header",    "bbox": [0,0,1,.1],  "text": "عنوان الاختبار"},
        {"type": "paragraph", "bbox": [0,.1,1,.5], "text": "نص عربي تجريبي للاختبار."},
        {"type": "caption",   "bbox": [0,.5,1,.6], "text": "تسمية توضيحية"},
    ]}

@pytest.fixture
def table_layout():
    return {"blocks": [
        {"type": "table", "bbox": [0,0,1,1],
         "cells": [["الوحدة","الحالة"],["OCR","✅"],["NLP","✅"]]}
    ]}

def test_export_creates_file(basic_layout, tmp_path):
    out = str(tmp_path / "out.docx")
    result = export_to_docx(basic_layout, out)
    assert result == out
    assert os.path.exists(out)
    assert os.path.getsize(out) > 1000

def test_export_with_table(table_layout, tmp_path):
    out = str(tmp_path / "table.docx")
    export_to_docx(table_layout, out)
    assert os.path.exists(out)

def test_export_empty(tmp_path):
    out = str(tmp_path / "empty.docx")
    export_to_docx({"blocks": []}, out)
    assert os.path.exists(out)

def test_ocr_to_layout():
    ocr = {"blocks": [
        {"type": "paragraph", "bbox": [0,0,1,1], "text": "نص"},
        {"type": "table", "bbox": [0,0,1,1], "cells": [["أ","ب"]]},
    ]}
    layout = ocr_result_to_layout(ocr, "img.jpg")
    assert layout["image_path"] == "img.jpg"
    assert len(layout["blocks"]) == 2
    assert layout["blocks"][1]["cells"] == [["أ","ب"]]

def test_ocr_to_layout_empty():
    assert ocr_result_to_layout({})["blocks"] == []
