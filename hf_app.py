#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OmniFile AI Processor — HF Spaces Deployment
==============================================
Standalone Gradio application for HuggingFace Spaces.
Multilingual handwriting OCR system supporting Arabic, English, and German.

Tabs:
  1. OCR Processing       — EasyOCR + TrOCR ensemble
  2. Text Correction      — ar-corrector + pyspellchecker + protected words
  3. PDF Processing       — PyMuPDF (fitz) page-by-page extraction
  4. Translation          — Helsinki-NLP MarianMT models + post-MT correction
  5. Text Classification  — Keyword-based multilingual categorization
  6. Evaluation           — CER / WER metrics (Levenshtein + jiwer)
  7. Training Data        — PDF to page/word/character crops for handwriting fine-tuning
  8. Video OCR            — Extract text from video files with timestamps
  9. Data Augmentation    — Expand training data for Arabic handwriting
  10. About               — Project info, links, author

Author:  Dr Abdulmalek Tamer Al-husseini
Email:   Abdulmalek.husseini@gmail.com
Location: Homs, Syria
GitHub:  https://github.com/DrAbdulmalek/OmniFile_Processor
License: MIT
"""

# ====================================================================
# Standard Library Imports
# ====================================================================

import os
import io
import re
import gc
import json
import shutil
import tempfile
import traceback
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

import numpy as np
from PIL import Image

# ====================================================================
# Gradio — imported here (lightweight; ML models are lazy-loaded)
# ====================================================================

import gradio as gr

# ====================================================================
# Logging Setup / إعداد التسجيل
# ====================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("OmniFile_HF")

# ====================================================================
# Environment & HF Spaces Configuration
# ====================================================================
# / إعدادات بيئة HuggingFace Spaces

HF_CACHE_DIR = os.environ.get("HF_HOME", "/data/.cache/huggingface")
os.makedirs(HF_CACHE_DIR, exist_ok=True)
os.environ["TRANSFORMERS_CACHE"] = HF_CACHE_DIR
os.environ["HF_HOME"] = HF_CACHE_DIR
os.environ["TORCH_HOME"] = HF_CACHE_DIR

# HuggingFace token — for gated models (optional)
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# ====================================================================
# GPU Detection / كشف GPU تلقائي
# ====================================================================

DEVICE = "cpu"
USE_GPU = False
GPU_NAME = ""

try:
    import torch
    if torch.cuda.is_available():
        DEVICE = "cuda"
        USE_GPU = True
        GPU_NAME = torch.cuda.get_device_name(0)
        GPU_MEM = torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
        logger.info("GPU detected: %s (%.1f GB)", GPU_NAME, GPU_MEM)
    else:
        logger.info("No GPU detected — running on CPU")
except ImportError:
    logger.warning("PyTorch not installed — ML features will be unavailable")

# ====================================================================
# Lazy-Loaded Model Cache
# ====================================================================
# Models are loaded ONLY when the user first interacts with a tab.
# This ensures fast app startup on HF Spaces.
# / النماذج تُحمّل عند أول استخدام فقط

_model_cache: Dict[str, Any] = {}


def _get_model(key: str) -> Any:
    """Return a cached model, or None."""
    return _model_cache.get(key)


def _set_model(key: str, obj: Any) -> None:
    """Store a model in the cache and free unused memory."""
    _model_cache[key] = obj
    gc.collect()
    if USE_GPU:
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass

# ====================================================================
# Translation Corrector — Post-MT Arabic Correction
# ====================================================================
# / محرّك تصحيح الترجمات العربية بعد الترجمة الآلية

_translation_corrector = None


def _get_translation_corrector():
    """Lazy-load the translation corrector with rules."""
    global _translation_corrector
    if _translation_corrector is not None:
        return _translation_corrector
    try:
        # Try loading from modules first (dev environment)
        base = Path(__file__).parent
        rules_path = base / "data" / "translation_rules.json"
        if not rules_path.is_file():
            rules_path = None  # Will use built-in defaults
        from modules.nlp.translation_corrector import ArabicTranslationProcessor
        _translation_corrector = ArabicTranslationProcessor(rules_file=str(rules_path) if rules_path else None)
        logger.info("Translation corrector loaded (%d rules)", len(_translation_corrector.rules))
    except ImportError:
        # Fallback: inline minimal corrector
        logger.warning("translation_corrector module not found — using inline fallback")
        _translation_corrector = None
    return _translation_corrector


def _correct_translation(english_text: str, arabic_text: str, enable: bool = True) -> str:
    """
    Apply post-MT correction to Arabic translation.
    / تصحيح النص العربي بعد الترجمة الآلية
    """
    if not enable or not arabic_text:
        return arabic_text
    corrector = _get_translation_corrector()
    if corrector is None:
        return arabic_text
    result = corrector.process_translation(english_text, arabic_text)
    if result["improved"]:
        logger.info("Translation corrected: %d rule changes + %d regex changes",
                     len(result["corrections"]), len(result["regex_changes"]))
    return result["corrected"]


# ====================================================================
# Custom CSS — Dark Theme + RTL Arabic Support
# ====================================================================

CUSTOM_CSS = """
/* ===== Container ===== */
.gradio-container {
    font-family: 'Segoe UI', Tahoma, 'Noto Sans Arabic', sans-serif !important;
    max-width: 1280px !important;
}

/* ===== RTL Arabic text helper ===== */
.arabic-text, [dir="rtl"], .rtl {
    direction: rtl;
    text-align: right;
}

/* ===== Tabs ===== */
.tab-nav button {
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
    border-radius: 8px 8px 0 0 !important;
    transition: all 0.2s ease;
}
.tab-nav button.selected {
    background: linear-gradient(135deg, #1a73e8, #0d47a1) !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3);
}

/* ===== Primary Button ===== */
button.primary, .gr-button-primary {
    background: linear-gradient(135deg, #1a73e8, #0d47a1) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.2s ease !important;
}
button.primary:hover, .gr-button-primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(26, 115, 232, 0.4);
}

/* ===== Cards / Panels ===== */
.gr-box, .gr-panel, .gr-form {
    border-radius: 12px !important;
    border: 1px solid #2a2a3e !important;
    background: #1e1e2e !important;
}

/* ===== Textarea & Input ===== */
.gr-textarea textarea, .gr-input input, textarea, input {
    background: #12121e !important;
    border: 1px solid #3a3a5e !important;
    color: #e0e0e0 !important;
    border-radius: 8px !important;
}

/* ===== Markdown Headings ===== */
.gr-markdown h1, .gr-markdown h2, .gr-markdown h3 {
    color: #90caf9 !important;
}
.gr-markdown p, .gr-markdown li {
    color: #c0c0d0 !important;
    line-height: 1.8 !important;
}

/* ===== Progress Bar ===== */
.prog .progress-bar {
    background: linear-gradient(90deg, #1a73e8, #4fc3f7) !important;
    border-radius: 10px !important;
}

/* ===== File Upload ===== */
.gr-upload {
    border: 2px dashed #3a3a5e !important;
    border-radius: 12px !important;
    background: #12121e !important;
}

/* ===== Dataframe ===== */
.gr-dataframe table { border-radius: 8px !important; overflow: hidden; }
.gr-dataframe th { background: #0d47a1 !important; color: white !important; }

/* ===== Hide footer ===== */
footer { display: none !important; }
"""


# ====================================================================
# Helper: Language Detection
# ====================================================================

def detect_language(text: str) -> str:
    """
    Detect language of a text.
    Returns: 'ar', 'en', 'de', or 'other'.
    / كشف لغة النص
    """
    if not text or not text.strip():
        return "other"

    try:
        from langdetect import detect, LangDetectException
        lang = detect(text[:500])
        return lang if lang in ("ar", "en", "de") else "other"
    except LangDetectException:
        return _char_based_lang_detect(text)
    except ImportError:
        logger.warning("langdetect not installed — using character-based detection")
        return _char_based_lang_detect(text)


def _char_based_lang_detect(text: str) -> str:
    """Character-based fallback language detection."""
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    german = sum(1 for c in text if c in "äöüÄÖÜß")
    latin = sum(1 for c in text if c.isalpha() and c.isascii())
    total = arabic + german + latin
    if total == 0:
        return "other"
    ratios = {
        "ar": arabic / total,
        "de": (german + 0.01) / total,
        "en": max(0, (latin - german)) / total,
    }
    return max(ratios, key=ratios.get)


# ====================================================================
# Tab 1 — OCR Processing
# / معالجة OCR باستخدام EasyOCR + TrOCR
# ====================================================================

def _load_easyocr(languages: Optional[List[str]] = None):
    """Lazy-load EasyOCR reader."""
    langs = sorted(languages or ["en"])
    cache_key = "easyocr_" + "_".join(langs)
    if _get_model(cache_key):
        return _get_model(cache_key)

    logger.info("Loading EasyOCR (langs=%s) on %s ...", langs, DEVICE)
    try:
        import easyocr
        reader = easyocr.Reader(langs, gpu=USE_GPU, verbose=False, download_enabled=True)
        _set_model(cache_key, reader)
        return reader
    except Exception as e:
        logger.error("EasyOCR load failed: %s", e)
        return None


def _load_trocr():
    """Lazy-load TrOCR processor and model."""
    if _get_model("trocr_processor") and _get_model("trocr_model"):
        return _get_model("trocr_processor"), _get_model("trocr_model")

    model_name = "microsoft/trocr-base-handwritten"
    logger.info("Loading TrOCR (%s) on %s ...", model_name, DEVICE)
    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        processor = TrOCRProcessor.from_pretrained(
            model_name, cache_dir=HF_CACHE_DIR, token=HF_TOKEN or None,
        )
        model = VisionEncoderDecoderModel.from_pretrained(
            model_name, cache_dir=HF_CACHE_DIR, token=HF_TOKEN or None,
        )
        model.to(DEVICE)
        model.eval()
        if USE_GPU:
            model.half()

        _set_model("trocr_processor", processor)
        _set_model("trocr_model", model)
        return processor, model
    except Exception as e:
        logger.error("TrOCR load failed: %s", e)
        return None, None


def _run_easyocr(image: Image.Image, languages: List[str]) -> Tuple[str, float]:
    """Run EasyOCR on an image. Returns (text, avg_confidence)."""
    reader = _load_easyocr(languages)
    if reader is None:
        return "", 0.0

    img_arr = np.array(image)
    results = reader.readtext(img_arr)

    texts, total_conf = [], 0.0
    for _bbox, text, conf in results:
        texts.append(text)
        total_conf += conf

    return "\n".join(texts), (total_conf / len(results) if results else 0.0)


def _run_trocr(image: Image.Image) -> Tuple[str, float]:
    """Run TrOCR on a single image. Returns (text, confidence)."""
    processor, model = _load_trocr()
    if processor is None or model is None:
        return "", 0.0

    try:
        import torch
        pv = processor(image, return_tensors="pt").pixel_values.to(DEVICE)
        with torch.no_grad():
            ids = model.generate(pv, max_new_tokens=300)
        text = processor.batch_decode(ids, skip_special_tokens=True)[0]
        return text, 0.90
    except Exception as e:
        logger.error("TrOCR inference failed: %s", e)
        return "", 0.0


def _ocr_ensemble(
    image: Image.Image,
    languages: List[str],
    engine: str,
    progress=None,
) -> Tuple[str, str]:
    """Run selected OCR engine(s). Returns (text, info)."""
    parts_text, parts_info = [], []

    if engine in ("EasyOCR", "Both"):
        if progress:
            progress(0.4, desc="Running EasyOCR…")
        txt, conf = _run_easyocr(image, languages)
        if txt:
            parts_text.append(txt)
            parts_info.append(f"EasyOCR: {len(txt)} chars, conf={conf:.1%}")
        else:
            parts_info.append("EasyOCR: no text detected")

    if engine in ("TrOCR", "Both"):
        if progress:
            progress(0.8, desc="Running TrOCR…")
        txt, _ = _run_trocr(image)
        prefix = "[TrOCR] " if engine == "Both" else ""
        if txt:
            parts_text.append(prefix + txt)
            parts_info.append(f"TrOCR: {len(txt)} chars")
        else:
            parts_info.append("TrOCR: no text detected")

    return "\n\n".join(parts_text), " | ".join(parts_info) or "No results"


def _process_pdf_ocr(
    pdf_path: str,
    languages: List[str],
    engine: str,
    progress=None,
) -> Tuple[str, str]:
    """Process every page of a PDF through OCR."""
    try:
        import fitz
    except ImportError:
        return "❌ PyMuPDF not installed. Run: pip install PyMuPDF", ""

    doc = fitz.open(pdf_path)
    n = len(doc)
    pages_text, info = [], [f"PDF: {n} pages"]

    for i in range(n):
        if progress:
            progress((i + 1) / n, desc=f"Page {i+1}/{n}…")
        page = doc[i]
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        txt, _ = _ocr_ensemble(img, languages, engine)
        if txt.strip():
            pages_text.append(f"--- Page {i+1} ---\n{txt}")

    doc.close()

    if not pages_text:
        return "⚠️ No text extracted from the PDF.", " | ".join(info)

    full = "\n\n".join(pages_text)
    info.append(f"Extracted: {len(full)} chars total")
    return full, " | ".join(info)


# --- Gradio handler for Tab 1 ---

def process_ocr(file, language, engine, progress=gr.Progress()):
    """
    Tab 1 handler — OCR processing.
    Accepts PDF or image, runs selected engine(s).
    / معالجة OCR — رفع صورة أو PDF واستخراج النص
    """
    if file is None:
        return "⚠️ Please upload a PDF or image file.", ""

    lang_map = {
        "Arabic (ar)": ["ar"],
        "English (en)": ["en"],
        "German (de)": ["de"],
        "Arabic + English (ar+en)": ["ar", "en"],
    }
    languages = lang_map.get(language, ["en"])

    try:
        path = file if isinstance(file, str) else file.name
        if path.lower().endswith(".pdf"):
            return _process_pdf_ocr(path, languages, engine, progress)
        else:
            image = Image.open(path).convert("RGB")
            txt, info = _ocr_ensemble(image, languages, engine, progress)
            return txt, info
    except Exception as e:
        logger.error("OCR error: %s", traceback.format_exc())
        return f"❌ Error: {e}", ""


# ====================================================================
# Tab 2 — Text Correction
# / تصحيح النصوص الإملائية — ar-corrector + pyspellchecker
# ====================================================================

def _load_ar_corrector():
    """Lazy-load ar-corrector."""
    if _get_model("ar_corrector"):
        return _get_model("ar_corrector")
    try:
        from ar_corrector import corrector
        c = corrector()
        _set_model("ar_corrector", c)
        return c
    except ImportError:
        logger.warning("ar-corrector not installed")
        return None
    except Exception as e:
        logger.error("ar-corrector load failed: %s", e)
        return None


def _load_en_spellchecker(lang: str = "en"):
    """Lazy-load pyspellchecker for English or German."""
    cache_key = f"spellchecker_{lang}"
    if _get_model(cache_key):
        return _get_model(cache_key)
    try:
        from spellchecker import SpellChecker
        sc = SpellChecker(language=lang)
        _set_model(cache_key, sc)
        return sc
    except ImportError:
        logger.warning("pyspellchecker not installed")
        return None
    except Exception as e:
        logger.error("pyspellchecker load failed: %s", e)
        return None


# --- Gradio handler for Tab 2 ---

def correct_text(text: str, language: str, method: str) -> Tuple[str, str]:
    """
    Tab 2 handler — spell-checking & correction.
    / تصحيح إملائي للنصوص
    """
    if not text or not text.strip():
        return "⚠️ Please enter text to correct.", ""

    result = text
    msgs = []

    # Determine effective language
    if language == "Auto":
        eff_lang = detect_language(text)
        msgs.append(f"Auto-detected: {eff_lang}")
    else:
        eff_lang = {"Arabic (ar)": "ar", "English (en)": "en", "German (de)": "de"}.get(language, "en")

    # ---- Arabic correction (ar-corrector) ----
    if eff_lang == "ar" and method in ("ar-corrector (Arabic)", "Both"):
        corrector = _load_ar_corrector()
        if corrector:
            try:
                corrected = corrector.correct(text)
                if corrected and corrected != text:
                    result = corrected
                    msgs.append("ar-corrector: ✅ corrections applied")
                else:
                    msgs.append("ar-corrector: no changes needed")
            except Exception as e:
                msgs.append(f"ar-corrector: error — {e}")
        else:
            msgs.append("ar-corrector: not available (install ar-corrector)")

    # ---- English/German correction (pyspellchecker) ----
    if eff_lang in ("en", "de") and method in ("pyspellchecker (EN/DE)", "Both"):
        sc = _load_en_spellchecker(eff_lang)
        if sc:
            words = re.findall(r"\b[\w'äöüÄÖÜß]+\b", text)
            fixes = 0
            for w in words:
                if w.lower() not in sc.word_frequency:
                    c = sc.correction(w)
                    if c and c.lower() != w.lower():
                        # Preserve case
                        if w.isupper():
                            c = c.upper()
                        elif w and w[0].isupper():
                            c = c.capitalize()
                        result = re.sub(r"\b" + re.escape(w) + r"\b", c, result, count=1)
                        fixes += 1
            msgs.append(f"pyspellchecker: {fixes} words corrected" if fixes else "pyspellchecker: no errors found")
        else:
            msgs.append("pyspellchecker: not available (install pyspellchecker)")

    if eff_lang == "ar" and method == "pyspellchecker (EN/DE)":
        msgs.append("pyspellchecker: Arabic not supported (use ar-corrector)")
    if eff_lang in ("en", "de") and method == "ar-corrector (Arabic)":
        msgs.append("ar-corrector: only supports Arabic")

    return result, " | ".join(msgs) if msgs else "No corrections applied"


# ====================================================================
# Tab 3 — PDF Processing
# / معالجة ملفات PDF — استخراج نص صفحة بصفحة
# ====================================================================

# --- Gradio handler for Tab 3 ---

def process_pdf(pdf_file):
    """
    Tab 3 handler — extract text from a PDF page by page.
    / استخراج نصوص من PDF صفحة بصفحة مع إمكانية التنزيل
    """
    if pdf_file is None:
        return "⚠️ Please upload a PDF file.", None

    try:
        import fitz
    except ImportError:
        return "❌ PyMuPDF (fitz) not installed. Run: pip install PyMuPDF", None

    try:
        path = pdf_file if isinstance(pdf_file, str) else pdf_file.name
        doc = fitz.open(path)
        n = len(doc)
        pages = []

        for i in range(n):
            page = doc[i]
            text = page.get_text("text").strip()

            # If no embedded text, fall back to OCR
            if not text or len(text) < 10:
                try:
                    pix = page.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                    ocr_txt, _ = _run_easyocr(img, ["en", "ar", "de"])
                    text = ocr_txt if ocr_txt else "(No text detected on this page)"
                except Exception:
                    text = "(Could not extract text — OCR unavailable)"

            pages.append(
                f"{'=' * 60}\n"
                f"Page {i + 1} / {n}\n"
                f"{'=' * 60}\n\n{text}"
            )

        doc.close()
        full = "\n\n".join(pages)

        header = (
            f"📄 File: {os.path.basename(path)}\n"
            f"📊 Pages: {n}\n"
            f"📝 Characters: {len(full)}\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"{'─' * 60}\n\n"
        )

        # Create a temp file for download
        tmp = tempfile.mktemp(suffix=".txt", prefix="omnifile_")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(header + full)

        return header + full, tmp

    except Exception as e:
        logger.error("PDF error: %s", traceback.format_exc())
        return f"❌ Error: {e}", None


# ====================================================================
# Tab 4 — Translation
# / الترجمة باستخدام نماذج Helsinki-NLP
# ====================================================================

TRANSLATION_MODELS = {
    "English → Arabic":  "Helsinki-NLP/opus-mt-en-ar",
    "Arabic → English":  "Helsinki-NLP/opus-mt-ar-en",
    "English → German":  "Helsinki-NLP/opus-mt-en-de",
    "German → English":  "Helsinki-NLP/opus-mt-de-en",
    "Arabic → German":   "Helsinki-NLP/opus-mt-ar-de",
    "German → Arabic":   "Helsinki-NLP/opus-mt-de-ar",
}


def _load_translator(model_name: str):
    """Lazy-load Helsinki-NLP MarianMT model."""
    cache_key = f"trans_{model_name}"
    if _get_model(cache_key):
        return _get_model(cache_key)

    logger.info("Loading translation model: %s", model_name)
    try:
        from transformers import MarianMTModel, MarianTokenizer
        tok = MarianTokenizer.from_pretrained(model_name, cache_dir=HF_CACHE_DIR, token=HF_TOKEN or None)
        mdl = MarianMTModel.from_pretrained(model_name, cache_dir=HF_CACHE_DIR, token=HF_TOKEN or None)
        mdl.to(DEVICE)
        mdl.eval()
        if USE_GPU:
            mdl.half()
        _set_model(cache_key, (tok, mdl))
        return tok, mdl
    except Exception as e:
        logger.error("Translation model load failed: %s", e)
        return None, None


# --- Gradio handler for Tab 4 ---

def translate_text(text: str, direction: str, correct_output: bool = True, progress=gr.Progress()) -> str:
    """
    Tab 4 handler — translate text between Arabic/English/German.
    Optionally applies post-MT correction for Arabic output.
    / ترجمة النصوص بين العربية والإنجليزية والألمانية مع تصحيح اختياري
    """
    if not text or not text.strip():
        return "⚠️ Please enter text to translate."

    model_name = TRANSLATION_MODELS.get(direction)
    if not model_name:
        return f"❌ Unsupported direction: {direction}"

    progress(0.2, desc=f"Loading model ({direction})…")
    tok, mdl = _load_translator(model_name)
    if tok is None or mdl is None:
        return "❌ Failed to load model. Check logs for details."

    try:
        import torch

        # Chunk long text at paragraph boundaries
        chunks: List[str] = []
        cur = ""
        for para in re.split(r"\n\s*\n", text.strip()):
            if len(cur) + len(para) + 2 <= 400:
                cur += ("\n\n" if cur else "") + para
            else:
                if cur:
                    chunks.append(cur)
                cur = para
        if cur:
            chunks.append(cur)

        parts: List[str] = []
        for i, chunk in enumerate(chunks):
            progress(0.3 + 0.7 * ((i + 1) / len(chunks)), desc=f"Translating chunk {i+1}/{len(chunks)}…")
            inputs = tok(chunk, return_tensors="pt", truncation=True, max_length=512, padding=True)
            inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            with torch.no_grad():
                gen = mdl.generate(**inputs, max_length=512)
            parts.append(tok.decode(gen[0], skip_special_tokens=True))

        translated = "\n\n".join(parts)

        # Apply post-MT correction for Arabic output
        correction_note = ""
        if correct_output and "Arabic" in direction:
            corrected = _correct_translation(text, translated)
            if corrected != translated:
                correction_note = "\n\n**✅ Post-MT Correction Applied** — Grammar, style, and punctuation improved.\n"
                translated = corrected

        return (
            f"## 🌐 Translation Result ({direction})\n\n"
            f"{translated}\n\n"
            f"{correction_note}"
            f"---\n"
            f"**Model**: `{model_name}`  |  **Device**: `{DEVICE}`  |  "
            f"**Chars**: {len(text)} → {len(translated)}"
        )
    except Exception as e:
        logger.error("Translation error: %s", traceback.format_exc())
        return f"❌ Translation failed: {e}"


# ====================================================================
# Tab 7 — Training Data Generator
# / إنشاء بيانات تدريب من PDF
# ====================================================================

def generate_training_data(
    pdf_file,
    pages: str = "1-5",
    level: str = "word",
    dpi: int = 300,
    enable_augmentation: bool = False,
    val_split: float = 0.1,
    enable_ocr: bool = True,
    progress=gr.Progress(),
) -> Tuple[str, Optional[str]]:
    """
    Tab 7 handler — Generate training data from uploaded PDF.
    / إنشاء بيانات تدريب من ملف PDF مرفوع
    """
    if pdf_file is None:
        return "⚠️ Please upload a PDF file.", None

    progress(0.1, desc="Saving uploaded PDF…")
    # Save uploaded file to temp location
    tmp_dir = tempfile.mkdtemp(prefix="omnifile_train_")
    pdf_path = os.path.join(tmp_dir, "input.pdf")
    with open(pdf_path, "wb") as f:
        shutil.copy2(pdf_file.name, pdf_path)

    progress(0.2, desc="Initializing training data generator…")
    try:
        from modules.vision.pdf_to_training_data import TrainingDataGenerator, TrainingDataConfig

        config = TrainingDataConfig(
            output_dir=os.path.join(tmp_dir, "output"),
            dpi=dpi,
            pages=pages,
            max_image_height=64 if level == "character" else 0,
            enable_augmentation=enable_augmentation,
            val_ratio=val_split,
        )

        gen = TrainingDataGenerator(config=config)

        progress(0.3, desc="Loading OCR engine for text labels…")
        # Try to get OCR engine for word labels
        ocr_engine = None
        if enable_ocr:
            try:
                import easyocr
                ocr_engine = easyocr.Reader(["ar", "en"], gpu=USE_GPU, verbose=False)
            except Exception as e:
                logger.warning("EasyOCR not available for labeling: %s", e)

        progress(0.4, desc="Processing PDF pages…")
        stats = gen.process_pdf(
            pdf_path=pdf_path,
            pages=pages,
            level=level,
            ocr_engine=ocr_engine,
        )

        if "error" in stats:
            return f"❌ {stats['error']}", None

        progress(0.9, desc="Packaging results…")

        # Create zip of output
        import zipfile
        zip_path = os.path.join(tmp_dir, "training_data.zip")
        output_base = stats.get("output_dir", tmp_dir)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(output_base):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    arcname = os.path.relpath(fpath, output_base)
                    zf.write(fpath, arcname)

        # Build summary
        summary = (
            f"## 🧪 Training Data Generated Successfully!\n\n"
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| **Pages Processed** | {stats.get('pages_processed', 0)} |\n"
            f"| **Page Images** | {stats.get('page_images', 0)} |\n"
            f"| **Word Crops** | {stats.get('word_crops', 0)} |\n"
            f"| **Character Crops** | {stats.get('char_crops', 0)} |\n"
            f"| **Train Samples** | {stats.get('train_samples', 0)} |\n"
            f"| **Val Samples** | {stats.get('val_samples', 0)} |\n"
            f"| **Level** | {level} |\n"
            f"| **DPI** | {dpi} |\n"
            f"| **Augmentation** | {'✅ Enabled' if enable_augmentation else '❌ Disabled'} |\n"
            f"| **Validation Split** | {val_split:.0%} |\n"
            f"| **OCR Labels** | {'✅ Enabled' if enable_ocr else '❌ Disabled'} |\n\n"
            f"📥 Download the ZIP file containing:\n"
            f"- `page_images/` — Full page renders\n"
            f"- `word_crops/` — Individual word images\n"
            f"- `char_crops/` — Individual character images\n"
            f"- `train.jsonl` — Training labels\n"
            f"- `val.jsonl` — Validation labels\n"
            f"- `generation_summary.json` — Full statistics\n"
        )

        return summary, zip_path

    except ImportError as e:
        return f"❌ Missing module: {e}. Training data generator requires the full OmniFile Processor.", None
    except Exception as e:
        logger.error("Training data generation error: %s", traceback.format_exc())
        return f"❌ Error: {e}", None


# ====================================================================
# Tab 5 — Text Classification
# / تصنيف النصوص إلى فئات
# ====================================================================

CATEGORY_KEYWORDS = {
    "💻 Technical / Code": [
        "def ", "class ", "import ", "function(", "return ", "async ",
        "var ", "let ", "const ", "console.log", "=> ", "#include",
        "SELECT ", "API", "REST", "HTTP", "JSON", "endpoint",
        "algorithm", "framework", "database", "server", "deploy",
        "الخوارزمية", "الإطار", "الخادم", "التطبيق", "قاعدة البيانات",
    ],
    "📝 General / Notes": [
        "TODO", "NOTE", "important", "remember", "idea", "think",
        "ملاحظة", "فكرة", "مهم", "تذكر", "يوميات",
    ],
    "🔬 Scientific / Academic": [
        "hypothesis", "analysis", "methodology", "research",
        "experiment", "statistical", "journal", "abstract",
        "الفرضية", "التحليل", "المنهجية", "البحث", "النتائج", "الاستنتاج",
    ],
    "📖 Literary / Poetry": [
        "poem", "poetry", "verse", "metaphor", "narrative",
        "قال الشاعر", "قصيدة", "شعر", "رواية", "قصة",
    ],
    "🕌 Religious": [
        "Quran", "Bible", "hadith", "prayer", "prophet",
        "القرآن", "الكريم", "الحديث", "النبوي", "الصلاة", "سورة", "آية",
    ],
}


# --- Gradio handler for Tab 5 ---

def classify_text(text: str) -> str:
    """
    Tab 5 handler — classify text into a category.
    / تصنيف النص إلى فئة (تقنية، عامة، أكاديمية، أدبية، دينية)
    """
    if not text or not text.strip():
        return "⚠️ Please enter text to classify."

    scores: Dict[str, Dict] = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        cnt, matched = 0, []
        for kw in keywords:
            m = re.findall(re.escape(kw), text, re.IGNORECASE)
            if m:
                cnt += len(m)
                matched.append(kw)
        if cnt > 0:
            scores[cat] = {"score": cnt, "keywords": matched}

    lang = detect_language(text)
    lang_names = {"ar": "Arabic 🇸🇦", "en": "English 🇬🇧", "de": "German 🇩🇪", "other": "Unknown 🌍"}

    if not scores:
        top_cat, top_score, top_kw = "📝 General / Notes", 0, []
    else:
        sorted_c = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
        top_cat, top_score = sorted_c[0][0], sorted_c[0][1]["score"]
        top_kw = sorted_c[0][1]["keywords"][:10]

    total = sum(d["score"] for d in scores.values()) or 1

    out = "## 🏷️ Classification Result\n\n"
    out += "| Property | Value |\n|---|---|\n"
    out += f"| **Category** | **{top_cat}** |\n"
    out += f"| **Confidence** | {top_score / total:.1%} |\n"
    out += f"| **Language** | {lang_names.get(lang, lang)} |\n"
    out += f"| **Characters** | {len(text)} |\n"
    out += f"| **Words** | {len(text.split())} |\n"

    if top_kw:
        out += "\n### Matched Keywords\n"
        for kw in top_kw:
            out += f"- `{kw}`\n"

    if len(scores) > 1:
        out += "\n### All Scores\n"
        for cat, d in sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True):
            bar_len = int(d["score"] / total * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            out += f"- **{cat}**: {bar} {d['score'] / total:.1%}\n"

    return out


# ====================================================================
# Tab 6 — Evaluation (CER / WER)
# / حساب معدل خطأ الأحرف والكلمات
# ====================================================================

def _normalize_text(text: str) -> str:
    """Normalize text for fair comparison — Arabic-aware."""
    if not text:
        return ""
    # Remove Arabic diacritics
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    # Normalize Alef
    text = text.replace("إ", "ا").replace("أ", "ا").replace("ٱ", "ا")
    # Normalize Alef Maqsura
    text = text.replace("ى", "ي")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _levenshtein(s1, s2) -> int:
    """Compute Levenshtein edit distance."""
    m, n = len(s1), len(s2)
    if m == 0:
        return n
    if n == 0:
        return m
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if s1[i - 1] == s2[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


# --- Gradio handler for Tab 6 ---

def calculate_metrics(reference: str, hypothesis: str) -> str:
    """
    Tab 6 handler — compute CER and WER.
    / حساب CER و WER بين النص المرجعي ونص OCR
    """
    if not reference.strip() or not hypothesis.strip():
        return "⚠️ Please provide both reference and OCR output text."

    ref = _normalize_text(reference)
    hyp = _normalize_text(hypothesis)

    # CER
    cer_val = _levenshtein(ref, hyp) / max(len(ref), 1)
    # WER
    ref_w, hyp_w = ref.split(), hyp.split()
    wer_val = _levenshtein(ref_w, hyp_w) / max(len(ref_w), 1)

    # Grade
    if cer_val <= 0.02:
        grade = "A+ (Near Perfect) ⭐"
    elif cer_val <= 0.05:
        grade = "A (Excellent) ✅"
    elif cer_val <= 0.10:
        grade = "B (Good) 👍"
    elif cer_val <= 0.20:
        grade = "C (Acceptable) ⚠️"
    elif cer_val <= 0.40:
        grade = "D (Poor) ❌"
    else:
        grade = "F (Unusable) 🚫"

    out = "## 📊 OCR Evaluation Results\n\n"
    out += "| Metric | Value |\n|---|---|\n"
    out += f"| **CER** (Character Error Rate) | **{cer_val:.2%}** |\n"
    out += f"| **WER** (Word Error Rate) | **{wer_val:.2%}** |\n"
    out += f"| **Character Accuracy** | **{(1 - cer_val) * 100:.1f}%** |\n"
    out += f"| **Quality Grade** | **{grade}** |\n\n"
    out += "| Detail | Value |\n|---|---|\n"
    out += f"| Reference chars | {len(ref)} |\n"
    out += f"| Reference words | {len(ref_w)} |\n"
    out += f"| Char edit distance | {_levenshtein(ref, hyp)} |\n"
    out += f"| Word edit distance | {_levenshtein(ref_w, hyp_w)} |\n"

    # Cross-check with jiwer if available
    try:
        import jiwer
        out += "\n### jiwer Cross-Check\n"
        out += f"| Metric | Value |\n|---|---|\n"
        out += f"| CER | {jiwer.cer(reference, hypothesis):.2%} |\n"
        out += f"| WER | {jiwer.wer(reference, hypothesis):.2%} |\n"
    except ImportError:
        out += "\n> ℹ️ Install `jiwer` for independent verification."
    except Exception:
        pass

    return out


# ====================================================================
# Tab 7 — About
# / حول المشروع
# ====================================================================

ABOUT_MD = """
# 🧠 OmniFile AI Processor
## Multilingual Handwriting OCR System

---

### 🌍 Supported Languages
| Language | Code | OCR | Translation | Spell Check |
|---|---|---|---|---|
| **Arabic** 🇸🇦 | `ar` | ✅ EasyOCR + TrOCR | ✅ | ✅ ar-corrector |
| **English** 🇬🇧 | `en` | ✅ EasyOCR + TrOCR | ✅ | ✅ pyspellchecker |
| **German** 🇩🇪 | `de` | ✅ EasyOCR + TrOCR | ✅ | ✅ pyspellchecker |
| **Mixed** 🇸🇦🇬🇧 | `ar+en` | ✅ EasyOCR | ✅ | — |

### 🛠️ Core Technologies
| Component | Technology |
|---|---|
| **OCR** | TrOCR (Microsoft) + EasyOCR |
| **PDF** | PyMuPDF (fitz) |
| **Translation** | Helsinki-NLP MarianMT |
| **Correction** | ar-corrector + pyspellchecker |
| **Language Detection** | langdetect |
| **Evaluation** | jiwer + Custom Levenshtein |
| **UI** | Gradio (Soft theme) |

### ✨ Features
- 🔤 **Multilingual OCR** — Arabic, English, German handwriting
- 📄 **PDF Processing** — Page-by-page extraction with OCR fallback
- ✏️ **Spell Correction** — Arabic & English/German
- 🌐 **Translation** — 6 language directions
- 🏷️ **Classification** — Auto-categorize text (code, notes, academic, poetry, religious)
- 📊 **Evaluation** — CER/WER with quality grades
- 🖥️ **GPU** — Auto-detect with CPU fallback
- 📱 **RTL** — Full Arabic right-to-left support
- ⚡ **Lazy Loading** — Fast startup, models load on demand

### 👨‍💻 Author
**Dr Abdulmalek Tamer Al-husseini**

📍 **Location:** Homs, Syria
📧 **Email:** [Abdulmalek.husseini@gmail.com](mailto:Abdulmalek.husseini@gmail.com)
🐙 **GitHub:** [DrAbdulmalek](https://github.com/DrAbdulmalek)

### 🔗 Links
- 📂 [GitHub — DrAbdulmalek/OmniFile_Processor](https://github.com/DrAbdulmalek/OmniFile_Processor)
- 🤗 [HuggingFace Spaces](https://huggingface.co/spaces/DrAbdulmalek/OmniFile_Processor)

### 📜 License
**MIT License**

---

### 🙏 Acknowledgments
- [Microsoft TrOCR](https://huggingface.co/microsoft/trocr-base-handwritten)
- [EasyOCR](https://github.com/JaidedAI/EasyOCR)
- [Helsinki-NLP](https://huggingface.co/Helsinki-NLP)
- [PyMuPDF](https://pymupdf.readthedocs.io/)
- [ar-corrector](https://github.com/mshakir/ar-corrector)
- [jiwer](https://github.com/jitsi/jiwer)

---

*Built with ❤️ by Dr Abdulmalek Tamer Al-husseini | OmniFile AI Processor v4.3.0*
*📍 Homs, Syria | 📧 Abdulmalek.husseini@gmail.com*
"""


# ====================================================================
# Tab 8 — Video OCR
# / استخراج النصوص من مقاطع الفيديو
# ====================================================================

def process_video_ocr(
    video_file,
    frame_interval: int = 30,
    progress=gr.Progress(),
) -> str:
    """
    Tab 8 handler — Extract text from video file.
    / استخراج النصوص من ملف فيديو
    """
    if video_file is None:
        return "⚠️ Please upload a video file."

    progress(0.1, desc="Saving video file…")
    tmp_dir = tempfile.mkdtemp(prefix="omnifile_video_")
    video_path = os.path.join(tmp_dir, "input.mp4")
    shutil.copy2(video_file.name, video_path)

    progress(0.2, desc="Initializing Video OCR…")
    try:
        from modules.vision.video_ocr import VideoOCR

        vid_ocr = VideoOCR(frame_interval=frame_interval)

        progress(0.3, desc="Extracting frames and running OCR…")
        timeline = vid_ocr.process_video(
            video_path=video_path,
            progress_callback=lambda cur, tot, msg: progress(0.3 + 0.6 * cur / max(tot, 1), desc=msg),
        )

        if timeline.error:
            return f"❌ {timeline.error}"

        progress(0.95, desc="Building results…")

        # Build output
        out = "## 🎬 Video OCR Results\n\n"
        out += f"| Metric | Value |\n|--------|-------|\n"
        out += f"| **Total Frames Processed** | {timeline.total_frames} |\n"
        out += f"| **Frames with Text** | {timeline.frames_with_text} |\n"
        out += f"| **Average Confidence** | {timeline.avg_confidence:.1%} |\n"
        out += f"| **Frame Interval** | Every {frame_interval} frames |\n"
        out += f"| **Duration** | {timeline.total_frames / 30:.1f}s (estimated at 30fps) |\n\n"

        if timeline.frames:
            out += "### 📝 Timeline\n\n"
            for frame in timeline.frames[:50]:  # Limit display
                ts = frame.timestamp
                text = frame.text[:100] + ("..." if len(frame.text) > 100 else "")
                conf = frame.confidence
                out += f"- **[{ts}]** ({conf:.0%}) {text}\n"

            if len(timeline.frames) > 50:
                out += f"\n*... and {len(timeline.frames) - 50} more frames*\n"

        if timeline.full_text:
            out += "\n### 📄 Full Extracted Text\n\n"
            out += f"```\n{timeline.full_text[:2000]}\n```"
            if len(timeline.full_text) > 2000:
                out += "\n*(text truncated)*"

        return out

    except ImportError:
        return "❌ Video OCR module not available. Run with full OmniFile Processor installation."
    except Exception as e:
        logger.error("Video OCR error: %s", traceback.format_exc())
        return f"❌ Error: {e}"


# ====================================================================
# Tab 9 — Data Augmentation
# / توسيع بيانات التدريب للخط العربي
# ====================================================================

def augment_training_data(
    input_images,
    num_augmented: int = 5,
    rotation: float = 5.0,
    noise: float = 0.02,
    blur: bool = True,
    brightness: float = 0.2,
    progress=gr.Progress(),
) -> Tuple[str, Optional[str]]:
    """
    Tab 9 handler — Augment training images for better model training.
    / توسيع صور التدريب لتحسين أداء النموذج
    """
    if input_images is None:
        return "⚠️ Please upload training images.", None

    progress(0.1, desc="Setting up augmentation…")
    tmp_dir = tempfile.mkdtemp(prefix="omnifile_aug_")

    try:
        from modules.vision.data_augmentation import DataAugmentor

        # Save uploaded images
        image_paths = []
        for img_info in input_images:
            img_path = os.path.join(tmp_dir, os.path.basename(img_info.name))
            shutil.copy2(img_info.name, img_path)
            image_paths.append(img_path)

        progress(0.2, desc="Processing images…")
        augmentor = DataAugmentor(
            rotation_max=rotation,
            noise_std=noise,
            blur_kernel=5 if blur else 0,
            brightness_range=brightness,
        )

        progress(0.3, desc="Generating augmented images…")

        results = []
        for i, img_path in enumerate(image_paths):
            aug_results = augmentor.augment_image(
                img_path,
                num_augmentations=num_augmented,
                output_dir=os.path.join(tmp_dir, "augmented"),
            )
            results.extend(aug_results)
            progress(0.3 + 0.5 * (i + 1) / len(image_paths),
                       desc=f"Image {i+1}/{len(image_paths)}…")

        progress(0.85, desc="Packaging results…")

        # Create zip
        import zipfile
        zip_path = os.path.join(tmp_dir, "augmented_data.zip")
        aug_dir = os.path.join(tmp_dir, "augmented")
        if os.path.exists(aug_dir):
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(aug_dir):
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        zf.write(fpath, os.path.relpath(fpath, aug_dir))

        progress(1.0, desc="Done!")

        out = "## 🔄 Data Augmentation Complete!\n\n"
        out += f"| Metric | Value |\n|--------|-------|\n"
        out += f"| **Original Images** | {len(image_paths)} |\n"
        out += f"| **Augmented Images** | {len(results)} |\n"
        out += f"| **Multiplication Factor** | {num_augmented}x |\n"
        out += f"| **Rotation Range** | ±{rotation}° |\n"
        out += f"| **Noise Level** | {noise} |\n"
        out += f"| **Blur** | {'Enabled' if blur else 'Disabled'} |\n"
        out += f"| **Brightness Range** | ±{brightness} |\n\n"
        out += "📥 Download the ZIP file containing augmented images."

        return out, zip_path if os.path.exists(zip_path) else None

    except ImportError:
        return "❌ Data Augmentation module not available.", None
    except Exception as e:
        logger.error("Augmentation error: %s", traceback.format_exc())
        return f"❌ Error: {e}", None


# ====================================================================
# Build & Launch Gradio Application
# ====================================================================

def build_app() -> gr.Blocks:
    """
    Build the full Gradio Blocks application with 10 tabs.
    / بناء واجهة Gradio الكاملة مع 10 تبويبات
    """

    with gr.Blocks(
        title="OmniFile AI Processor",
    ) as app:

        # ==================== Header ====================
        gr.HTML(
            """
            <div style="text-align:center; padding:24px 0 12px;">
                <h1 style="font-size:2.2em; margin-bottom:6px;">🧠 OmniFile AI Processor</h1>
                <h3 style="color:#90caf9; font-weight:400; margin:0;">
                    Multilingual Handwriting OCR — Arabic 🇸🇦 &nbsp;+&nbsp; English 🇬🇧 &nbsp;+&nbsp; German 🇩🇪
                </h3>
                <p style="color:#888; font-size:0.92em; margin-top:4px;">
                    TrOCR + EasyOCR Ensemble &nbsp;·&nbsp; PDF Processing &nbsp;·&nbsp;
                    Translation &nbsp;·&nbsp; Text Classification &nbsp;·&nbsp; CER/WER Evaluation
                </p>
            </div>
            """
        )

        # ================================================================
        # Tab 1 — OCR Processing
        # / التبويب الأول: معالجة OCR
        # ================================================================
        with gr.Tab("🔍 OCR Processing"):

            gr.Markdown(
                "### Upload a PDF or image to extract text with OCR.  "
                "### رفع ملف PDF أو صورة لاستخراج النصوص."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    ocr_file = gr.File(
                        label="📁 Upload File / رفع ملف",
                        file_types=[".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"],
                        type="filepath",
                    )
                    ocr_lang = gr.Dropdown(
                        label="🌐 Language / اللغة",
                        choices=["Arabic (ar)", "English (en)", "German (de)", "Arabic + English (ar+en)"],
                        value="Arabic (ar)",
                    )
                    ocr_engine = gr.Dropdown(
                        label="⚙️ OCR Engine / محرك OCR",
                        choices=["EasyOCR", "TrOCR", "Both"],
                        value="EasyOCR",
                    )
                    ocr_btn = gr.Button("🚀 Process / معالجة", variant="primary", size="lg")
                    ocr_info = gr.Markdown("")

                with gr.Column(scale=2):
                    ocr_output = gr.Textbox(
                        label="📋 Extracted Text / النص المستخرج",
                        lines=15,
                        placeholder="OCR results will appear here…",
                    )
                    with gr.Row():
                        gr.Button("🗑️ Clear").click(
                            fn=lambda: ("", ""), outputs=[ocr_output, ocr_info]
                        )

            ocr_btn.click(
                fn=process_ocr,
                inputs=[ocr_file, ocr_lang, ocr_engine],
                outputs=[ocr_output, ocr_info],
            )

        # ================================================================
        # Tab 2 — Text Correction
        # / التبويب الثاني: تصحيح النصوص
        # ================================================================
        with gr.Tab("✏️ Text Correction"):

            gr.Markdown(
                "### Spell-check & correct Arabic and English/German text.  "
                "### تصحيح إملائي للنصوص العربية والإنجليزية والألمانية."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    corr_input = gr.Textbox(
                        label="📝 Input Text / النص المدخل",
                        lines=8,
                        placeholder="Enter text to correct… / أدخل النص المراد تصحيحه…",
                    )
                    corr_lang = gr.Dropdown(
                        label="🌐 Language / اللغة",
                        choices=["Auto", "Arabic (ar)", "English (en)", "German (de)"],
                        value="Auto",
                    )
                    corr_method = gr.Dropdown(
                        label="🔧 Method / الطريقة",
                        choices=["ar-corrector (Arabic)", "pyspellchecker (EN/DE)", "Both"],
                        value="ar-corrector (Arabic)",
                    )
                    corr_btn = gr.Button("✨ Correct / تصحيح", variant="primary", size="lg")

                with gr.Column(scale=2):
                    corr_output = gr.Textbox(
                        label="✅ Corrected Text / النص المصحح",
                        lines=8,
                        placeholder="Corrected text…",
                    )
                    corr_info = gr.Markdown("")

            corr_btn.click(
                fn=correct_text,
                inputs=[corr_input, corr_lang, corr_method],
                outputs=[corr_output, corr_info],
            )

        # ================================================================
        # Tab 3 — PDF Processing
        # / التبويب الثالث: معالجة ملفات PDF
        # ================================================================
        with gr.Tab("📄 PDF Processing"):

            gr.Markdown(
                "### Upload a PDF to extract text page by page (with OCR fallback).  "
                "### رفع PDF لاستخراج النصوص صفحة بصفحة مع دعم OCR."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    pdf_file = gr.File(
                        label="📁 Upload PDF / رفع PDF",
                        file_types=[".pdf"],
                        type="filepath",
                    )
                    pdf_btn = gr.Button("📄 Extract Text / استخراج", variant="primary", size="lg")

                with gr.Column(scale=2):
                    pdf_output = gr.Textbox(
                        label="📋 Extracted Text / النص المستخرج",
                        lines=20,
                        placeholder="PDF text…",
                    )
                    pdf_download = gr.File(label="💾 Download / تنزيل", interactive=False)

            pdf_btn.click(
                fn=process_pdf,
                inputs=[pdf_file],
                outputs=[pdf_output, pdf_download],
            )

        # ================================================================
        # Tab 4 — Translation
        # / التبويب الرابع: الترجمة
        # ================================================================
        with gr.Tab("🌐 Translation"):

            gr.Markdown(
                "### Translate between Arabic, English, and German using Helsinki-NLP.  "
                "### ترجمة بين العربية والإنجليزية والألمانية."
            )
            gr.Markdown(
                "🇸🇾 **Post-MT Correction** is enabled by default for Arabic output — "
                "fixes grammar, style, and punctuation automatically.  "
                "التصحيح التلقائي مفعّل افتراضياً للنص العربي — يصلح القواعد والأسلوب والترقيم."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    trans_dir = gr.Dropdown(
                        label="➡️ Direction / الاتجاه",
                        choices=list(TRANSLATION_MODELS.keys()),
                        value="English → Arabic",
                    )
                    trans_correct = gr.Checkbox(
                        label="✅ Post-MT Correction / تصحيح الترجمة",
                        value=True,
                        info="Fix grammar, style & punctuation after translation (Arabic output only)",
                    )
                    trans_btn = gr.Button("🌐 Translate / ترجم", variant="primary", size="lg")

                with gr.Column(scale=2):
                    trans_input = gr.Textbox(
                        label="📝 Source / المصدر",
                        lines=8,
                        placeholder="Enter text to translate… / أدخل النص المراد ترجمته…",
                    )
                    trans_output = gr.Markdown("")

            trans_btn.click(
                fn=translate_text,
                inputs=[trans_input, trans_dir, trans_correct],
                outputs=[trans_output],
            )

        # ================================================================
        # Tab 5 — Text Classification
        # / التبويب الخامس: تصنيف النصوص
        # ================================================================
        with gr.Tab("🏷️ Text Classification"):

            gr.Markdown(
                "### Classify text into categories: Technical, Notes, Academic, Poetry, Religious.  "
                "### تصنيف النصوص إلى فئات: تقنية، ملاحظات، أكاديمية، أدبية، دينية."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    cls_input = gr.Textbox(
                        label="📝 Input Text / النص",
                        lines=10,
                        placeholder="Enter text to classify…",
                    )
                    cls_btn = gr.Button("🏷️ Classify / صنّف", variant="primary", size="lg")

                with gr.Column(scale=2):
                    cls_output = gr.Markdown("")

            cls_btn.click(
                fn=classify_text,
                inputs=[cls_input],
                outputs=[cls_output],
            )

        # ================================================================
        # Tab 6 — Evaluation
        # / التبويب السادس: تقييم دقة OCR
        # ================================================================
        with gr.Tab("📊 Evaluation"):

            gr.Markdown(
                "### Calculate CER & WER between reference text and OCR output.  "
                "### حساب معدل خطأ الأحرف والكلمات."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    eval_ref = gr.Textbox(
                        label="📜 Reference (Ground Truth) / النص المرجعي",
                        lines=6,
                        placeholder="Correct text…",
                    )
                    eval_hyp = gr.Textbox(
                        label="🔍 OCR Output / نص OCR",
                        lines=6,
                        placeholder="OCR output…",
                    )
                    eval_btn = gr.Button("📊 Calculate / احسب", variant="primary", size="lg")

                with gr.Column(scale=2):
                    eval_output = gr.Markdown("")

            eval_btn.click(
                fn=calculate_metrics,
                inputs=[eval_ref, eval_hyp],
                outputs=[eval_output],
            )

            gr.Examples(
                examples=[
                    [
                        "مرحبا بكم في نظام التعرف على الخط اليدوي",
                        "مرحبا بكم في نظام التعرف على الخظ اليدوي",
                    ],
                    [
                        "The quick brown fox jumps over the lazy dog",
                        "The quik brown fox jumps over the lasy dog",
                    ],
                ],
                inputs=[eval_ref, eval_hyp],
                outputs=[eval_output],
                fn=calculate_metrics,
                label="📝 Examples / أمثلة",
            )

        # ================================================================
        # Tab 7 — Training Data Generator
        # / التبويب السابع: إنشاء بيانات التدريب
        # ================================================================
        with gr.Tab("🧪 Training Data"):

            gr.Markdown(
                "### Generate Training Data from PDF for Handwriting Model Fine-tuning  "
                "### إنشاء بيانات تدريب من ملفات PDF لتدريب نموذج التعرف على الخط اليدوي"
            )
            gr.Markdown(
                "📤 Upload a handwritten PDF → Get page images, word crops, and character crops  "
                "with JSONL labels ready for TrOCR LoRA fine-tuning."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    train_file = gr.File(
                        label="📤 Upload PDF / رفع ملف PDF",
                        file_types=[".pdf"],
                        interactive=True,
                    )
                    train_pages = gr.Textbox(
                        label="📄 Pages / الصفحات",
                        value="1-5",
                        placeholder="e.g. 'all', '1-10', '1,3,5'",
                    )
                    train_level = gr.Dropdown(
                        label="📊 Level / المستوى",
                        choices=["page", "word", "character"],
                        value="word",
                        info="page=full pages, word=word crops, character=individual characters",
                    )
                    train_dpi = gr.Slider(
                        label="🔍 DPI",
                        minimum=72, maximum=600, value=300, step=12,
                    )
                    train_augment = gr.Checkbox(
                        label="🔄 Enable Augmentation / تفعيل التوسيع",
                        value=False,
                        info="Random rotation and brightness changes for more training variety",
                    )
                    train_val_split = gr.Slider(
                        label="📊 Validation Split / نسبة البيانات التحققية",
                        minimum=0.05, maximum=0.3, value=0.1, step=0.05,
                    )
                    train_enable_ocr = gr.Checkbox(
                        label="🔍 Enable OCR for Labels / تفعيل التعرف للتصنيف",
                        value=True,
                        info="Use EasyOCR to generate text labels for each crop",
                    )
                    train_btn = gr.Button(
                        "🚀 Generate Training Data / إنشاء بيانات التدريب",
                        variant="primary", size="lg",
                    )

                with gr.Column(scale=2):
                    train_output = gr.Markdown("")
                    train_gallery = gr.Gallery(
                        label="🖼️ Sample Crops Preview / معاينة العينات",
                        columns=4,
                        height=300,
                        show_label=True,
                    )
                    train_files = gr.File(
                        label="📥 Download Results / تنزيل النتائج",
                        interactive=False,
                    )

            train_btn.click(
                fn=generate_training_data,
                inputs=[train_file, train_pages, train_level, train_dpi,
                        train_augment, train_val_split, train_enable_ocr],
                outputs=[train_output, train_files],
            )

        # ================================================================
        # Tab 8 — Video OCR
        # / التبويب الثامن: استخراج النصوص من الفيديو
        # ================================================================
        with gr.Tab("🎬 Video OCR"):
            gr.Markdown(
                "### Extract Text from Video Files  "
                "### استخراج النصوص من مقاطع الفيديو"
            )
            gr.Markdown(
                "📤 Upload a video → Get timestamped text from frames  "
                "Supports MP4, AVI, MOV, MKV and more."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    video_file = gr.File(
                        label="📤 Upload Video / رفع فيديو",
                        file_types=[".mp4", ".avi", ".mov", ".mkv", ".webm"],
                        interactive=True,
                    )
                    video_interval = gr.Slider(
                        label="⏱️ Frame Interval / فاصل الإطارات",
                        minimum=5, maximum=120, value=30, step=5,
                        info="Extract text every N frames (30 = ~1 sec at 30fps)",
                    )
                    video_btn = gr.Button(
                        "🎬 Extract Text / استخراج النص",
                        variant="primary", size="lg",
                    )

                with gr.Column(scale=2):
                    video_output = gr.Markdown("")

            video_btn.click(
                fn=process_video_ocr,
                inputs=[video_file, video_interval],
                outputs=[video_output],
            )

        # ================================================================
        # Tab 9 — Data Augmentation
        # / التبويب التاسع: توسيع بيانات التدريب
        # ================================================================
        with gr.Tab("🔄 Data Augmentation"):
            gr.Markdown(
                "### Augment Training Images for Better Handwriting Recognition  "
                "### توسيع صور التدريب لتحسين التعرف على الخط اليدوي"
            )
            gr.Markdown(
                "📤 Upload training images → Get augmented copies with rotation, noise, blur, and brightness variations."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    aug_files = gr.File(
                        label="📤 Upload Images / رفع صور",
                        file_types=[".png", ".jpg", ".jpeg", ".bmp", ".webp"],
                        interactive=True,
                        multiple=True,
                    )
                    aug_count = gr.Slider(
                        label="🔢 Augmentations per Image / عدد النسخ لكل صورة",
                        minimum=1, maximum=20, value=5, step=1,
                    )
                    aug_rotation = gr.Slider(
                        label="🔄 Rotation (degrees) / الدوران",
                        minimum=0, maximum=15, value=5, step=1,
                    )
                    aug_noise = gr.Slider(
                        label="📡 Noise Level / مستوى الضوضاء",
                        minimum=0, maximum=0.1, value=0.02, step=0.01,
                    )
                    aug_blur = gr.Checkbox(
                        label="🌫️ Enable Blur / تفعيل الضبابية",
                        value=True,
                    )
                    aug_brightness = gr.Slider(
                        label="💡 Brightness Range / نطاق السطوع",
                        minimum=0, maximum=0.5, value=0.2, step=0.05,
                    )
                    aug_btn = gr.Button(
                        "🔄 Augment Images / توسيع الصور",
                        variant="primary", size="lg",
                    )

                with gr.Column(scale=2):
                    aug_output = gr.Markdown("")
                    aug_download = gr.File(
                        label="📥 Download Augmented Data / تنزيل البيانات الموسعة",
                        interactive=False,
                    )

            aug_btn.click(
                fn=augment_training_data,
                inputs=[aug_files, aug_count, aug_rotation, aug_noise, aug_blur, aug_brightness],
                outputs=[aug_output, aug_download],
            )

        # ================================================================
        # Tab 10 — About
        # / التبويب العاشر: حول المشروع
        # ================================================================
        with gr.Tab("ℹ️ About"):
            dev = f"**Runtime**: `{DEVICE.upper()}`"
            if USE_GPU:
                dev += f" · **GPU**: `{GPU_NAME}`"
            gr.Markdown(dev)
            gr.Markdown(ABOUT_MD)

    return app


# ====================================================================
# Entry Point
# ====================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  OmniFile AI Processor — HF Spaces")
    logger.info("  Device : %s  |  GPU: %s", DEVICE, GPU_NAME or "N/A")
    logger.info("  Cache  : %s", HF_CACHE_DIR)
    logger.info("=" * 60)

    demo = build_app()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        max_threads=4,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
        ),
        css=CUSTOM_CSS,
    )
