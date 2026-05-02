"""
OmniFile AI Processor - FastAPI Backend
========================================
Backend API for the React frontend.
Connects all OCR, NLP, and AI modules via REST API.
"""

import io
import logging
import time
import uuid
import tempfile
import os
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="OmniFile AI Processor API",
    description="نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص والخط اليدوي",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Task Store ===
_task_store: dict[str, dict] = {}

# === Lazy-loaded Modules ===
_ocr_engine = None
_spell_corrector = None
_summarizer = None
_translator = None

def _get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from modules.vision.ocr_engine import OCREngine
        _ocr_engine = OCREngine()
    return _ocr_engine

def _get_spell_corrector():
    global _spell_corrector
    if _spell_corrector is None:
        from modules.nlp.spell_corrector import SpellCorrector
        _spell_corrector = SpellCorrector()
    return _spell_corrector

def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        from modules.nlp.summarizer import TextSummarizer
        _summarizer = TextSummarizer()
    return _summarizer

def _get_translator():
    global _translator
    if _translator is None:
        from modules.nlp.translator import TextTranslator
        _translator = TextTranslator()
    return _translator


# === Request/Response Models ===

class OCRRequest(BaseModel):
    image_base64: Optional[str] = None
    languages: list[str] = ["en", "ar"]
    engines: list[str] = ["easyocr", "trocr"]
    preprocess: bool = True

class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "ar"

class SummarizeRequest(BaseModel):
    text: str
    lang: str = "auto"
    max_length: int = 130
    min_length: int = 30

class SpellCheckRequest(BaseModel):
    text: str
    lang: Optional[str] = None

class EvaluateRequest(BaseModel):
    reference_text: str
    ocr_text: str


# === Health Check ===

@app.get("/")
async def root():
    return {
        "name": "OmniFile AI Processor API",
        "version": "3.0.0",
        "features": ["OCR", "Translation", "Summarization", "Spell Check", "Evaluation"],
        "docs": "/docs",
    }

@app.get("/health")
async def health_check():
    engine = _get_ocr_engine()
    return {
        "status": "healthy",
        "engines": engine.get_available_engines(),
        "uptime": time.time(),
    }

@app.get("/engines")
async def get_engines():
    engine = _get_ocr_engine()
    return {"engines": engine.get_available_engines()}


# === OCR Endpoints ===

@app.post("/api/ocr/process")
async def process_ocr(file: UploadFile = File(...), languages: str = "en,ar", engines: str = "easyocr,trocr", preprocess: bool = True):
    """معالجة ملف صورة أو PDF باستخدام OCR."""
    try:
        engine = _get_ocr_engine()

        # Save uploaded file temporarily
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Determine if PDF
            if suffix.lower() == ".pdf":
                results = engine.recognize_pdf(tmp_path, languages=languages.split(","))
                text = "\n\n".join(r.get("text", "") for r in results)
                confidence = sum(r.get("ocr_result", {}).get("confidence", 0) for r in results) / max(len(results), 1)
            else:
                result = engine.recognize(tmp_path, languages=languages.split(","))
                text = result.get("text", "")
                confidence = result.get("confidence", 0)

            return {
                "success": True,
                "text": text,
                "confidence": round(confidence, 4),
                "languages": languages.split(","),
                "engines": engines.split(","),
                "filename": file.filename,
            }
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        logger.error("OCR processing failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ocr/correct")
async def correct_ocr_text(request: SpellCheckRequest):
    """تصحيح نص OCR."""
    try:
        corrector = _get_spell_corrector()
        result = corrector.correct_text(request.text)
        return {
            "success": True,
            "original_text": request.text,
            "corrected_text": result["corrected_text"],
            "corrections": result["corrections"],
            "total_corrections": result["total_corrections"],
        }
    except Exception as e:
        logger.error("Spell correction failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === NLP Endpoints ===

@app.post("/api/nlp/translate")
async def translate_text(request: TranslateRequest):
    """ترجمة نص بين اللغات المدعومة."""
    try:
        translator = _get_translator()
        result = translator.translate(request.text, source_lang=request.source_lang, target_lang=request.target_lang)
        return {
            "success": True,
            "original_text": request.text,
            "translated_text": result.get("translated_text", result.get("text", "")),
            "source_lang": request.source_lang,
            "target_lang": request.target_lang,
            "model": "Helsinki-NLP/opus-mt",
        }
    except Exception as e:
        logger.error("Translation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nlp/summarize")
async def summarize_text(request: SummarizeRequest):
    """تلخيص نص."""
    try:
        summarizer = _get_summarizer()
        result = summarizer.summarize(request.text, lang=request.lang, max_length=request.max_length, min_length=request.min_length)
        return {
            "success": True,
            "original_text": request.text,
            "summary": result,
            "lang": request.lang,
        }
    except Exception as e:
        logger.error("Summarization failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Evaluation ===

@app.post("/api/evaluate")
async def evaluate_ocr(request: EvaluateRequest):
    """تقييم دقة OCR باستخدام CER/WER."""
    try:
        from modules.evaluation.metrics import evaluate
        result = evaluate(request.reference_text, request.ocr_text)
        return {
            "success": True,
            "cer": round(result.cer, 4),
            "wer": round(result.wer, 4),
            "accuracy": round(result.accuracy, 2),
            "quality_grade": result.quality_grade,
            "recommendations": result.recommendations if hasattr(result, 'recommendations') else [],
        }
    except Exception as e:
        logger.error("Evaluation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === AI Enhancement ===

@app.post("/api/ai/improve")
async def ai_improve_text(text: str = Form(...), language: str = Form("ar"), context: Optional[str] = Form(None)):
    """تحسين نص OCR باستخدام AI (GPT/Gemini)."""
    try:
        from modules.nlp.ai_corrector import AICorrector

        corrector = AICorrector()
        if not corrector.is_available():
            raise HTTPException(status_code=503, detail="AI correction not available - check OPENAI_API_KEY")

        result = corrector.correct_text(text, language=language, context=context)
        return {
            "success": True,
            "original_text": text,
            "corrected_text": result.get("corrected_text", ""),
            "changes": result.get("changes", []),
            "confidence": result.get("confidence", 0),
            "model": result.get("model", "gpt-3.5-turbo"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI improvement failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Batch Processing ===

@app.post("/api/batch/process")
async def batch_process(files: list[UploadFile] = File(...), languages: str = "en,ar"):
    """معالجة مجموعة ملفات."""
    task_id = str(uuid.uuid4())[:8]
    _task_store[task_id] = {"status": "processing", "total": len(files), "completed": 0, "results": []}

    results = []
    for file in files:
        try:
            engine = _get_ocr_engine()
            suffix = os.path.splitext(file.filename)[1] if file.filename else ".png"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            try:
                if suffix.lower() == ".pdf":
                    pdf_results = engine.recognize_pdf(tmp_path)
                    text = "\n\n".join(r.get("text", "") for r in pdf_results)
                else:
                    result = engine.recognize(tmp_path, languages=languages.split(","))
                    text = result.get("text", "")

                results.append({"filename": file.filename, "text": text, "success": True})
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e), "success": False})

    _task_store[task_id]["status"] = "completed"
    _task_store[task_id]["results"] = results
    return {"task_id": task_id, "results": results}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """حالة مهمة معالجة."""
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_store[task_id]


# === Static Files (React Frontend) ===

@app.get("/api/config")
async def get_config():
    """إعدادات النظام."""
    from config import OmniFileConfig
    cfg = OmniFileConfig()
    return {
        "supported_languages": cfg.supported_languages,
        "enable_summarization": cfg.enable_summarization,
        "enable_translation": cfg.enable_translation,
        "dark_mode": cfg.dark_mode,
        "ocr_engines": ["trocr", "easyocr", "tesseract", "paddleocr"],
    }


# === Entry Point ===

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=5001, reload=True)
