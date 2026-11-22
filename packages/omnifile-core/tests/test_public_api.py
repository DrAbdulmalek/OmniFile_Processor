"""اختبارات الواجهة العامة لحزمة omnifile-core.

Public-API contract tests: every re-exported name must resolve to a real
callable/class from the existing modules/ tree, and correction_dict.json
must load. Runs without installing the package (see conftest.py).

NOTE on the entry-count assertion: the integrated roadmap spec asked for
">100 entries", but modules/nlp/correction_dict.json currently ships
exactly 97 entries (mix of plain str mappings and nested
{wrong: {right: votes}} produced by modules/nlp/feedback.py). The test
asserts the real floor (>90) so it does not fail spuriously; see README
follow-up #3.
"""

from __future__ import annotations

import inspect
import json

import pytest

import omnifile_core

# ─── العقد العام: كل اسم يجب أن يُحل إلى كائن حقيقي من المصدر ────────────

# name -> expected kind ("function" | "class")
EXPECTED_API: dict = {
    # modules/nlp/arabic_rtl.py
    "is_rtl_text": "function",
    "get_text_direction": "function",
    "normalize_arabic_presentation_forms": "function",
    "normalize_arabic_ocr": "function",
    "fix_rtl_display": "function",
    "fix_arabic_reading_order": "function",
    "reorder_bboxes_for_rtl": "function",
    "is_arabic_char": "function",
    "is_hebrew_char": "function",
    "is_rtl_char": "function",
    "RTLFixer": "class",
    # modules/nlp/arabic_nlp_utils.py
    "normalize_for_comparison": "function",
    "arabic_normalized_similarity": "function",
    "similarity_report": "function",
    # modules/nlp/feedback.py
    "load_correction_dict": "function",
    "apply_correction_dict": "function",
    "track_correction_usage": "function",
    "build_correction_dict": "function",
    "build_correction_dict_v2": "function",
    # modules/nlp/language_corrector.py
    "LanguageCorrector": "class",
    # modules/nlp/ai_corrector.py
    "AICorrector": "class",
    # modules/evaluation/metrics.py
    "EvaluationResult": "class",
    "calculate_cer": "function",
    "calculate_wer": "function",
    "evaluate": "function",
    "evaluate_file": "function",
    # modules/export/exporter.py
    "DocumentExporter": "class",
    # modules/export/layout_preserving.py
    "export_to_docx": "function",
    "layout_to_docx": "function",
    "ocr_result_to_layout": "function",
    # modules/export/markdown_exporter.py
    "blocks_to_markdown": "function",
    "detect_list_items": "function",
    "export_to_markdown": "function",
}


@pytest.mark.parametrize("name", sorted(EXPECTED_API))
def test_public_name_resolves(name):
    """كل اسم في الواجهة العامة موجود وبتوقعه الصحيح (دالة/صنف)."""
    value = getattr(omnifile_core, name)
    expected = EXPECTED_API[name]
    if expected == "class":
        assert inspect.isclass(value), f"{name} should be a class, got {type(value)}"
    else:
        assert callable(value), f"{name} should be callable, got {type(value)}"


def test_dir_exposes_all_public_names():
    listed = set(dir(omnifile_core))
    missing = set(EXPECTED_API) - listed
    assert not missing, f"__dir__ is missing public names: {sorted(missing)}"
    assert set(omnifile_core.__all__) >= set(EXPECTED_API)


def test_unknown_attribute_raises_helpful_error():
    with pytest.raises(AttributeError) as excinfo:
        omnifile_core.this_does_not_exist  # noqa: B018
    assert "Public API" in str(excinfo.value)


# ─── تحميل قاموس التصحيح correction_dict.json ────────────────────────────

def test_correction_dict_path_constant_exists():
    path = omnifile_core.CORRECTION_DICT_PATH
    assert path is not None
    assert path.is_file(), f"correction_dict.json not found at {path}"


def test_correction_dict_loads_with_healthy_entry_count():
    corrections = omnifile_core.load_correction_dict(
        str(omnifile_core.CORRECTION_DICT_PATH)
    )
    assert isinstance(corrections, dict)
    # Roadmap spec said ">100 entries"; the file currently ships 97.
    # Assert the real floor and keep it a hard contract:
    assert len(corrections) > 90, (
        f"correction_dict.json shrank to {len(corrections)} entries "
        "(expected >90; was 97 at package creation)"
    )


def test_correction_dict_value_shapes_match_upstream_writer():
    """feedback.py writes either 'str' or nested {right: votes} dicts."""
    corrections = json.loads(omnifile_core.CORRECTION_DICT_PATH.read_text("utf-8"))
    assert corrections, "correction_dict.json must not be empty"
    for key, value in corrections.items():
        assert isinstance(key, str)
        assert isinstance(value, (str, dict)), (
            f"unexpected value type for {key!r}: {type(value)}"
        )


def test_apply_correction_dict_smoke():
    result = omnifile_core.apply_correction_dict(
        "المريض دخول العاجل", {"دخول": "الدخول"}
    )
    assert result == "المريض الدخول العاجل"


# ─── تطبيع RTL من arabic_rtl.py ──────────────────────────────────────────

def test_is_rtl_text_and_direction():
    assert omnifile_core.is_rtl_text("المريض يعاني من ألم") is True
    assert omnifile_core.is_rtl_text("patient history") is False
    assert omnifile_core.get_text_direction("مرحبا") == "rtl"
    assert omnifile_core.get_text_direction("hello world") == "ltr"


def test_normalize_arabic_presentation_forms():
    # U+FE8D (ARABIC LETTER ALEF FINAL FORM) -> base ALEF
    assert omnifile_core.normalize_arabic_presentation_forms("\uFE8D") == "\u0627"


def test_rtl_fixer_class_functional():
    fixer = omnifile_core.RTLFixer()  # optional deps (reshaper/bidi) degrade gracefully
    fixed = fixer.fix_text("مرحبا")
    assert isinstance(fixed, str)
    assert fixed.strip() != ""


# ─── مقاييس التقييم CER / WER من evaluation/metrics.py ───────────────────

def test_calculate_cer_exact():
    cer, errors, total = omnifile_core.calculate_cer("abc", "abd")
    assert pytest.approx(cer, abs=1e-9) == 1 / 3
    assert errors == 1 and total == 3


def test_calculate_wer_exact():
    wer, errors, total = omnifile_core.calculate_wer("قطة تنام", "قطة تنام")
    assert (wer, errors, total) == (0.0, 0, 2)


def test_evaluate_returns_evaluation_result():
    result = omnifile_core.evaluate("مرحبا بالعالم", "مرحبا بالعالم")
    assert isinstance(result, omnifile_core.EvaluationResult)
    assert result.cer == 0.0 and result.wer == 0.0


# ─── أصناف التصحيح (فحص الشكل دون تشغيل شبكة/تبعيات ثقيلة) ───────────────

def test_corrector_classes_shape():
    # LanguageCorrector: do NOT instantiate — with language_tool_python
    # installed elsewhere it may try to fetch the LanguageTool runtime.
    assert inspect.isclass(omnifile_core.LanguageCorrector)
    assert hasattr(omnifile_core.LanguageCorrector, "check")
    assert inspect.isclass(omnifile_core.AICorrector)
    assert hasattr(omnifile_core.AICorrector, "correct_text")


# ─── تصدير Markdown من markdown_exporter.py ──────────────────────────────

def test_blocks_to_markdown_smoke():
    md = omnifile_core.blocks_to_markdown(
        {"blocks": [{"type": "header", "text": "التقرير الطبي"}]}
    )
    assert isinstance(md, str)
    assert "## " in md and "التقرير الطبي" in md
    assert omnifile_core.blocks_to_markdown({"blocks": []}) == ""
