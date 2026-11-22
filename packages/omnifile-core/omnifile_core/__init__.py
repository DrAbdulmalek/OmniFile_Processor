"""omnifile_core — الطبقة الرقيقة لإعادة تصدير الوحدات القابلة لإعادة الاستخدام.

Thin lazy re-export layer over the EXISTING ``modules/`` tree of
OmniFile_Processor. Nothing here duplicates logic: every public name is
resolved on first access from the real source file under ``modules/``.

Why lazy (PEP 562 module-level ``__getattr__``)?
    - Importing ``omnifile_core`` costs nothing and pulls no third-party
      dependency (pandas / python-docx / openai are only imported when a
      name that needs them is actually accessed).
    - ``modules/nlp/__init__.py`` currently fails at import time (it imports
      the missing ``modules/nlp/spell_corrector.py``), so plain
      ``import modules.nlp.arabic_rtl`` raises ModuleNotFoundError. This
      layer bypasses the broken package ``__init__`` by loading the source
      file directly (importlib.util.spec_from_file_location) when the
      canonical import fails, without polluting the ``modules`` package.

Path resolution (must be finalized by the maintainer — see README.md):
    1. ``OMNIFILE_CORE_MODULES_DIR`` environment variable, if it points to a
       valid ``modules/`` tree (contains ``nlp/arabic_rtl.py``).
    2. The repository checkout this package lives in
       (``<repo>/modules`` relative to this file).
    3. ``<cwd>/modules`` or any ``modules/`` directory on ``sys.path``.

Usage:
    import omnifile_core
    omnifile_core.is_rtl_text("مرحبا")            # -> True
    omnifile_core.calculate_cer(ref, hyp)         # -> (cer, errors, total)
    corrections = omnifile_core.load_correction_dict(
        omnifile_core.CORRECTION_DICT_PATH)
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Location of the existing modules/ tree
# ---------------------------------------------------------------------------

_SENTINEL_RELPATH = Path("nlp") / "arabic_rtl.py"

_MODULES_DIR_CACHE: Optional[Path] = None


def _is_modules_dir(candidate: Path) -> bool:
    try:
        return (candidate / _SENTINEL_RELPATH).is_file()
    except OSError:
        return False


def _find_modules_dir() -> Optional[Path]:
    """Locate the existing ``modules/`` tree (cheap, no imports)."""
    env = os.environ.get("OMNIFILE_CORE_MODULES_DIR")
    if env:
        candidate = Path(env).expanduser().resolve()
        if _is_modules_dir(candidate):
            return candidate

    here = Path(__file__).resolve().parent  # .../packages/omnifile-core/omnifile_core
    candidates = [
        here.parents[2] / "modules",  # repository checkout: <repo>/modules
        Path.cwd() / "modules",
    ]
    for base in sys.path:
        try:
            candidates.append(Path(base).resolve() / "modules")
        except OSError:
            continue

    for candidate in candidates:
        if _is_modules_dir(candidate):
            return candidate
    return None


def _get_modules_dir() -> Path:
    global _MODULES_DIR_CACHE
    if _MODULES_DIR_CACHE is None or not _is_modules_dir(_MODULES_DIR_CACHE):
        _MODULES_DIR_CACHE = _find_modules_dir()
    if _MODULES_DIR_CACHE is None:
        raise ImportError(
            "omnifile_core: could not locate the existing 'modules/' tree of "
            "OmniFile_Processor. Run from the repository root, or set the "
            "OMNIFILE_CORE_MODULES_DIR environment variable to the directory "
            "containing nlp/arabic_rtl.py. (Path mapping must be finalized by "
            "the maintainer — see packages/omnifile-core/README.md.)"
        )
    return _MODULES_DIR_CACHE


# ---------------------------------------------------------------------------
# Lazy source loading
# ---------------------------------------------------------------------------

def _load_source_module(relpath: str) -> ModuleType:
    """Return the module object for e.g. ``"nlp/arabic_rtl.py"``.

    Tries the canonical ``modules.<dotted>`` import first (works for
    ``modules.evaluation`` / ``modules.export`` whose ``__init__.py`` are
    healthy, and keeps a single shared module object with the app). If that
    fails — currently the case for ``modules.nlp`` whose ``__init__.py``
    imports the missing ``spell_corrector.py`` — the file is loaded
    directly as a standalone module, bypassing the broken parent package.
    """
    mod_key = "omnifile_core._src." + relpath[:-3].replace("/", ".")
    if mod_key in sys.modules:
        return sys.modules[mod_key]

    canonical_dotted = "modules." + relpath[:-3].replace("/", ".")
    try:
        canonical = importlib.import_module(canonical_dotted)
        sys.modules[mod_key] = canonical
        return canonical
    except Exception:
        # Broken/absent parent package __init__ -> load the file directly.
        pass

    source_path = _get_modules_dir() / relpath
    spec = importlib.util.spec_from_file_location(mod_key, source_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"omnifile_core: cannot load source file {source_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_key] = module
    spec.loader.exec_module(module)
    return module


# name -> source file relative to the modules/ tree (all real, existing names)
_EXPORTS: dict = {
    # ── modules/nlp/arabic_rtl.py — تطبيع وتصحيح اتجاه النص العربي ──
    "is_rtl_text": "nlp/arabic_rtl.py",
    "get_text_direction": "nlp/arabic_rtl.py",
    "normalize_arabic_presentation_forms": "nlp/arabic_rtl.py",
    "normalize_arabic_ocr": "nlp/arabic_rtl.py",
    "fix_rtl_display": "nlp/arabic_rtl.py",
    "fix_arabic_reading_order": "nlp/arabic_rtl.py",
    "reorder_bboxes_for_rtl": "nlp/arabic_rtl.py",
    "is_arabic_char": "nlp/arabic_rtl.py",
    "is_hebrew_char": "nlp/arabic_rtl.py",
    "is_rtl_char": "nlp/arabic_rtl.py",
    "RTLFixer": "nlp/arabic_rtl.py",
    # ── modules/nlp/arabic_nlp_utils.py — مقارنة النصوص العربية ──
    "normalize_for_comparison": "nlp/arabic_nlp_utils.py",
    "arabic_normalized_similarity": "nlp/arabic_nlp_utils.py",
    "similarity_report": "nlp/arabic_nlp_utils.py",
    # ── modules/nlp/feedback.py — قاموس التصحيح correction_dict.json ──
    "load_correction_dict": "nlp/feedback.py",
    "apply_correction_dict": "nlp/feedback.py",
    "track_correction_usage": "nlp/feedback.py",
    "build_correction_dict": "nlp/feedback.py",
    "build_correction_dict_v2": "nlp/feedback.py",
    # ── modules/nlp/language_corrector.py — التدقيق النحوي/الإملائي ──
    "LanguageCorrector": "nlp/language_corrector.py",
    # ── modules/nlp/ai_corrector.py — التصحيح بالذكاء الاصطناعي ──
    "AICorrector": "nlp/ai_corrector.py",
    # ── modules/evaluation/metrics.py — CER / WER ──
    "EvaluationResult": "evaluation/metrics.py",
    "calculate_cer": "evaluation/metrics.py",
    "calculate_wer": "evaluation/metrics.py",
    "evaluate": "evaluation/metrics.py",
    "evaluate_file": "evaluation/metrics.py",
    # ── modules/export/exporter.py ──
    "DocumentExporter": "export/exporter.py",
    # ── modules/export/layout_preserving.py ──
    "export_to_docx": "export/layout_preserving.py",
    "layout_to_docx": "export/layout_preserving.py",
    "ocr_result_to_layout": "export/layout_preserving.py",
    # ── modules/export/markdown_exporter.py ──
    "blocks_to_markdown": "export/markdown_exporter.py",
    "detect_list_items": "export/markdown_exporter.py",
    "export_to_markdown": "export/markdown_exporter.py",
}

__all__ = ["CORRECTION_DICT_PATH", "__version__"] + sorted(_EXPORTS)


def _correction_dict_path() -> Path:
    return _get_modules_dir() / "nlp" / "correction_dict.json"


def __getattr__(name: str):
    """PEP 562 lazy re-export: resolve public names on first access."""
    if name == "CORRECTION_DICT_PATH":
        value = _correction_dict_path()
        globals()[name] = value
        return value

    relpath = _EXPORTS.get(name)
    if relpath is None:
        raise AttributeError(
            f"omnifile_core has no attribute {name!r}. "
            f"Public API: {', '.join(sorted(_EXPORTS))}"
        )

    module = _load_source_module(relpath)
    try:
        value = getattr(module, name)
    except AttributeError as exc:  # upstream renamed/removed the symbol
        raise AttributeError(
            f"omnifile_core: {name!r} is missing from source file "
            f"modules/{relpath} (upstream API changed?)"
        ) from exc
    globals()[name] = value  # cache for subsequent accesses
    return value


def __dir__() -> list:
    return sorted(set(globals()) | set(_EXPORTS))
