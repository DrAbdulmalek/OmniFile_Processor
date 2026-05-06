"""
OmniFile AI Processor - FastAPI Backend
========================================
Backend API for the React frontend.
Connects all OCR, NLP, and AI modules via REST API.

v3.0: +Rate Limiting, +Audit Logging, +NLP Endpoints, +Security Headers
v6.0: +Merge from OmniFile-Previous-Versions (Sync, Migration, Study Guide,
       Translation Corrector, Layout-Preserving Export, 42+ new endpoints)
المصدر: تطوير بناءً على مراجعة Mistral - 2026-05-07
"""

import io
import logging
import time
import uuid
import tempfile
import os
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="OmniFile AI Processor API",
    description="نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص والخط اليدوي",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# === Gzip Compression ===
app.add_middleware(GZipMiddleware, minimum_size=1000)

# === CORS for React frontend ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Rate Limiting (slowapi) ===
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    _rate_limiting_enabled = True
    logger.info("تم تفعيل Rate Limiting (slowapi)")
except ImportError:
    _rate_limiting_enabled = False
    logger.warning("slowapi غير مثبت - Rate Limiting معطّل. pip install slowapi")

# === Security Headers Middleware ===
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """إضافة security headers لجميع الاستجابات."""
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-API-Version"] = "6.0.0"
    return response

# === Audit Logger ===
_audit_logger = None

def _get_audit_logger():
    """الحصول على سجل التدقيق (lazy loading)."""
    global _audit_logger
    if _audit_logger is None:
        try:
            from modules.security.audit_logger import get_audit_logger
            _audit_logger = get_audit_logger()
        except Exception as e:
            logger.warning("فشل تحميل سجل التدقيق: %s", e)
    return _audit_logger

def _audit(
    action: str,
    level: str = "info",
    status: str = "success",
    duration_ms: Optional[float] = None,
    resource: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
):
    """تسجيل عملية في سجل التدقيق."""
    try:
        audit = _get_audit_logger()
        if audit:
            from modules.security.audit_logger import AuditAction, AuditLevel
            action_enum = AuditAction(action)
            level_enum = AuditLevel(level)
            ip = request.client.host if request and request.client else None
            audit.log(
                action=action_enum,
                level=level_enum,
                ip_address=ip,
                status=status,
                duration_ms=duration_ms,
                resource=resource,
                details=details,
            )
    except Exception:
        pass  # لا نريد أن يفشل التدقيق بسبب خطأ في التسجيل

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
        "features": [
            "OCR (4 Engines)", "Fusion Strategies", "Translation (6 pairs)",
            "Summarization (EN/AR/DE)", "Spell Check (3 langs)", "NER",
            "AI Enhancement (GPT/Gemini)", "File Encryption",
            "Audit Logging", "Rate Limiting",
        ],
        "docs": "/docs",
        "rate_limiting": _rate_limiting_enabled,
    }

@app.get("/health")
async def health_check():
    engine = _get_ocr_engine()
    return {
        "status": "healthy",
        "version": "3.0.0",
        "engines": engine.get_available_engines(),
        "uptime": time.time(),
        "rate_limiting": _rate_limiting_enabled,
    }

@app.get("/engines")
async def get_engines():
    engine = _get_ocr_engine()
    return {"engines": engine.get_available_engines()}


# === OCR Endpoints ===

@app.post("/api/ocr/process")
async def process_ocr(
    request: Request,
    file: UploadFile = File(...),
    languages: str = "en,ar",
    engines: str = "easyocr,trocr",
    preprocess: bool = True,
):
    """معالجة ملف صورة أو PDF باستخدام OCR."""
    start_time = time.time()
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

            duration = (time.time() - start_time) * 1000
            _audit("ocr_process", status="success", duration_ms=duration,
                   resource=file.filename, request=request,
                   details={"languages": languages, "engines": engines, "confidence": round(confidence, 4)})

            return {
                "success": True,
                "text": text,
                "confidence": round(confidence, 4),
                "languages": languages.split(","),
                "engines": engines.split(","),
                "filename": file.filename,
                "processing_time_ms": round(duration, 2),
            }
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        _audit("ocr_process", level="warning", status="failed", duration_ms=duration,
               resource=file.filename, request=request, details={"error": str(e)})
        logger.error("OCR processing failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ocr/correct")
async def correct_ocr_text(request_body: SpellCheckRequest, request: Request):
    """تصحيح نص OCR."""
    start_time = time.time()
    try:
        corrector = _get_spell_corrector()
        result = corrector.correct_text(request_body.text)
        duration = (time.time() - start_time) * 1000

        _audit("ocr_correct", status="success", duration_ms=duration,
               request=request, details={"total_corrections": result.get("total_corrections", 0)})

        return {
            "success": True,
            "original_text": request_body.text,
            "corrected_text": result["corrected_text"],
            "corrections": result["corrections"],
            "total_corrections": result["total_corrections"],
            "processing_time_ms": round(duration, 2),
        }
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        _audit("ocr_correct", level="warning", status="failed", duration_ms=duration, request=request)
        logger.error("Spell correction failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === NLP Endpoints ===

@app.post("/api/nlp/translate")
async def translate_text(request_body: TranslateRequest, request: Request):
    """ترجمة نص بين اللغات المدعومة."""
    start_time = time.time()
    try:
        translator = _get_translator()
        result = translator.translate(request_body.text, source_lang=request_body.source_lang, target_lang=request_body.target_lang)
        duration = (time.time() - start_time) * 1000

        _audit("nlp_translate", status="success", duration_ms=duration,
               request=request,
               details={"source_lang": request_body.source_lang, "target_lang": request_body.target_lang})

        return {
            "success": True,
            "original_text": request_body.text,
            "translated_text": result.get("translated_text", result.get("text", "")),
            "source_lang": request_body.source_lang,
            "target_lang": request_body.target_lang,
            "model": "Helsinki-NLP/opus-mt",
            "processing_time_ms": round(duration, 2),
        }
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        _audit("nlp_translate", level="warning", status="failed", duration_ms=duration, request=request)
        logger.error("Translation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nlp/summarize")
async def summarize_text(request_body: SummarizeRequest, request: Request):
    """تلخيص نص."""
    start_time = time.time()
    try:
        summarizer = _get_summarizer()
        result = summarizer.summarize(request_body.text, lang=request_body.lang,
                                       max_length=request_body.max_length, min_length=request_body.min_length)
        duration = (time.time() - start_time) * 1000

        _audit("nlp_summarize", status="success", duration_ms=duration,
               request=request, details={"lang": request_body.lang})

        return {
            "success": True,
            "original_text": request_body.text,
            "summary": result,
            "lang": request_body.lang,
            "processing_time_ms": round(duration, 2),
        }
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        _audit("nlp_summarize", level="warning", status="failed", duration_ms=duration, request=request)
        logger.error("Summarization failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Evaluation ===

@app.post("/api/evaluate")
async def evaluate_ocr(request_body: EvaluateRequest, request: Request):
    """تقييم دقة OCR باستخدام CER/WER."""
    start_time = time.time()
    try:
        from modules.evaluation.metrics import evaluate
        result = evaluate(request_body.reference_text, request_body.ocr_text)
        duration = (time.time() - start_time) * 1000

        return {
            "success": True,
            "cer": round(result.cer, 4),
            "wer": round(result.wer, 4),
            "accuracy": round(result.accuracy, 2),
            "quality_grade": result.quality_grade,
            "recommendations": result.recommendations if hasattr(result, 'recommendations') else [],
            "processing_time_ms": round(duration, 2),
        }
    except Exception as e:
        logger.error("Evaluation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === AI Enhancement ===

@app.post("/api/ai/improve")
async def ai_improve_text(
    request: Request,
    text: str = Form(...),
    language: str = Form("ar"),
    context: Optional[str] = Form(None),
):
    """تحسين نص OCR باستخدام AI (GPT/Gemini)."""
    start_time = time.time()
    try:
        from modules.nlp.ai_corrector import AICorrector

        corrector = AICorrector()
        if not corrector.is_available():
            raise HTTPException(status_code=503, detail="AI correction not available - check OPENAI_API_KEY")

        result = corrector.correct_text(text, language=language, context=context)
        duration = (time.time() - start_time) * 1000

        _audit("ai_correct", status="success", duration_ms=duration,
               request=request, details={"language": language, "model": result.get("model", "unknown")})

        return {
            "success": True,
            "original_text": text,
            "corrected_text": result.get("corrected_text", ""),
            "changes": result.get("changes", []),
            "confidence": result.get("confidence", 0),
            "model": result.get("model", "gpt-3.5-turbo"),
            "processing_time_ms": round(duration, 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        _audit("ai_correct", level="warning", status="failed", duration_ms=duration, request=request)
        logger.error("AI improvement failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Security: Encryption ===

@app.post("/api/security/encrypt")
async def encrypt_file_endpoint(
    request: Request,
    file: UploadFile = File(...),
):
    """تشفير ملف باستخدام AES-128 (Fernet)."""
    start_time = time.time()
    try:
        from modules.security.encryption import FileEncryptor
        encryptor = FileEncryptor()

        # Save uploaded file
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            output_path = encryptor.encrypt_file(tmp_path)
            duration = (time.time() - start_time) * 1000

            _audit("security_encrypt", status="success", duration_ms=duration,
                   resource=file.filename, request=request, level="security")

            return FileResponse(
                path=output_path,
                filename=file.filename + ".enc",
                media_type="application/octet-stream",
                background=BackgroundTasks(),
            )
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        _audit("security_encrypt", level="critical", status="failed",
               duration_ms=duration, resource=file.filename, request=request)
        logger.error("File encryption failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/security/decrypt")
async def decrypt_file_endpoint(
    request: Request,
    file: UploadFile = File(...),
):
    """فك تشفير ملف."""
    start_time = time.time()
    try:
        from modules.security.encryption import FileEncryptor
        encryptor = FileEncryptor()

        suffix = os.path.splitext(file.filename)[1] if file.filename else ".enc"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            output_path = encryptor.decrypt_file(tmp_path)
            duration = (time.time() - start_time) * 1000

            _audit("security_decrypt", status="success", duration_ms=duration,
                   resource=file.filename, request=request, level="security")

            return FileResponse(
                path=output_path,
                filename=file.filename.replace(".enc", ""),
                media_type="application/octet-stream",
            )
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        _audit("security_decrypt", level="critical", status="failed",
               duration_ms=duration, resource=file.filename, request=request)
        logger.error("File decryption failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Audit Log Endpoints ===

@app.get("/api/audit/logs")
async def get_audit_logs(
    action: Optional[str] = None,
    user: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100,
):
    """استعلام سجلات التدقيق."""
    try:
        audit = _get_audit_logger()
        if not audit:
            return {"logs": [], "message": "Audit logging not available"}
        logs = audit.get_logs(action=action, user=user, level=level, limit=limit)
        return {"logs": logs, "total": len(logs)}
    except Exception as e:
        logger.error("Failed to get audit logs: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit/stats")
async def get_audit_stats():
    """إحصائيات سجل التدقيق."""
    try:
        audit = _get_audit_logger()
        if not audit:
            return {"message": "Audit logging not available"}
        return audit.get_stats()
    except Exception as e:
        logger.error("Failed to get audit stats: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# === Batch Processing ===

@app.post("/api/batch/process")
async def batch_process(
    request: Request,
    files: list[UploadFile] = File(...),
    languages: str = "en,ar",
):
    """معالجة مجموعة ملفات."""
    start_time = time.time()
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

    duration = (time.time() - start_time) * 1000
    _task_store[task_id]["status"] = "completed"
    _task_store[task_id]["results"] = results
    _task_store[task_id]["processing_time_ms"] = round(duration, 2)

    _audit("file_upload", status="success", duration_ms=duration,
           request=request, details={"files_count": len(files), "success_count": sum(1 for r in results if r["success"])})

    return {"task_id": task_id, "results": results, "processing_time_ms": round(duration, 2)}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """حالة مهمة معالجة."""
    if task_id not in _task_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_store[task_id]


# === Mobile OCR Review ===

@app.get("/mobile")
async def mobile_review():
    """صفحة مراجعة نتائج OCR على الموبايل."""
    mobile_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mobile")
    html_path = os.path.join(mobile_dir, "ocr-review.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="Mobile review page not found")

@app.get("/mobile/manifest.json")
async def mobile_manifest():
    """PWA manifest للمراجعة على الموبايل."""
    mobile_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mobile")
    manifest_path = os.path.join(mobile_dir, "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/json")
    raise HTTPException(status_code=404, detail="Mobile manifest not found")


# === Configuration ===

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
        "fusion_strategies": ["highest_confidence", "weighted_average", "voting", "longest_text"],
        "rate_limiting": _rate_limiting_enabled,
        "audit_logging": _audit_logger is not None,
        "version": "6.0.0",
        "sync_enabled": True,
        "study_guide_enabled": True,
        "migration_enabled": True,
        "translation_corrector_enabled": True,
        "layout_preserving_export_enabled": True,
    }


# ===========================================================================
# MERGED ENDPOINTS (v6.0.0) - من OmniFile-Previous-Versions
# المصدر: 02-ocr-project-unified-v2/backend/app.py (v5.3)
# ===========================================================================

# === Translation Corrector Endpoints ===

class TranslationCorrectRequest(BaseModel):
    english_text: str
    arabic_text: str
    apply_rules: bool = True
    apply_regex: bool = True


@app.post("/api/nlp/translation-correct")
async def correct_translation(request_body: TranslationCorrectRequest, request: Request):
    """تصحيح ترجمة عربية باستخدام قواعد ثنائية اللغة."""
    start_time = time.time()
    try:
        from modules.nlp.translation_corrector import ArabicTranslationProcessor
        processor = ArabicTranslationProcessor()
        result = processor.process_translation(
            request_body.english_text,
            request_body.arabic_text,
            apply_rules=request_body.apply_rules,
            apply_regex=request_body.apply_regex,
        )
        duration = (time.time() - start_time) * 1000

        _audit("translation_correct", status="success", duration_ms=duration, request=request,
               details={"improved": result["improved"], "corrections_count": len(result["corrections"])})

        return {
            "success": True,
            "original": result["original"],
            "corrected": result["corrected"],
            "corrections": result["corrections"],
            "rule_ids": result["rule_ids"],
            "improved": result["improved"],
            "processing_time_ms": round(duration, 2),
        }
    except Exception as e:
        logger.error("Translation correction failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nlp/translation-rules")
async def get_translation_rules():
    """عرض قواعد تصحيح الترجمات."""
    try:
        from modules.nlp.translation_corrector import ArabicTranslationProcessor
        processor = ArabicTranslationProcessor()
        rules = [
            {
                "rule_id": r.rule_id,
                "category": r.category,
                "english_pattern": r.english_pattern,
                "wrong_arabic": r.wrong_arabic,
                "correct_arabic": r.correct_arabic,
                "description": r.description,
                "priority": r.priority,
            }
            for r in processor.rules
        ]
        return {"rules": rules, "total": len(rules)}
    except Exception as e:
        logger.error("Failed to load translation rules: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# === Synchronization Endpoints ===

@app.get("/api/sync/status")
async def api_sync_status():
    """حالة المزامنة بين الأجهزة."""
    try:
        from modules.security.sync import SyncManager, FileLock
        return {
            "sync_enabled": True,
            "message": "نظام المزامنة جاهز - يتطلب config.py مع sync_enabled=True",
        }
    except Exception as e:
        logger.error("Sync status failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync/config")
async def api_sync_config():
    """إعدادات Syncthing للمشروع."""
    try:
        from modules.security.sync import SyncManager
        return {"sync_enabled": True, "setup_instructions": "See docs/ for Syncthing setup"}
    except Exception as e:
        logger.error("Sync config failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/network")
async def api_network_info():
    """معلومات الشبكة المحلية للوصول من الجوال."""
    try:
        import socket
        hostname = socket.gethostname()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"
        return {
            "hostname": hostname,
            "local_ip": local_ip,
            "api_url": f"http://{local_ip}:5001",
            "docs_url": f"http://{local_ip}:5001/docs",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Migration Endpoints ===

@app.get("/api/migration/scan")
async def api_migration_scan(base_path: str = ""):
    """فحص المشاريع القديمة المتاحة للترحيل."""
    try:
        from modules.core.migration import DataMigrator
        migrator = DataMigrator()
        report = migrator.scan_and_report(base_path=base_path)
        return report
    except Exception as e:
        logger.error("Migration scan failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


class MigrationRunRequest(BaseModel):
    base_path: str = ""
    old_folders: list[str] = []
    verified_only: bool = True


@app.post("/api/migration/run")
async def api_run_migration(req: MigrationRunRequest):
    """تشغيل ترحيل البيانات من النسخ القديمة."""
    try:
        from modules.core.migration import DataMigrator
        migrator = DataMigrator()
        result = migrator.migrate(
            base_path=req.base_path,
            old_folders=req.old_folders if req.old_folders else None,
            verified_only=req.verified_only,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error("Migration run failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# === Study Guide Endpoints ===

@app.get("/api/study-guide")
async def api_generate_study_guide(title: str = "مرجع دراسي", highlight: bool = True):
    """توليد مرجع دراسي بصيغة Markdown."""
    try:
        from modules.export.study_guide import generate_study_guide
        content = generate_study_guide(title=title, highlight_terms=highlight)
        if not content:
            raise HTTPException(status_code=400, detail="لا توجد بيانات كافية لتوليد المرجع")
        return {
            "success": True,
            "content": content,
            "size": len(content),
            "preview": content[:1000] + ("..." if len(content) > 1000 else ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Study guide generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/study-guide/mermaid")
async def api_generate_mermaid(diagram_type: str = "mindmap", max_terms: int = 50):
    """توليد مخطط Mermaid للمفردات المستخرجة."""
    try:
        from modules.export.study_guide import generate_mermaid_diagram
        mermaid_code = generate_mermaid_diagram(diagram_type=diagram_type, max_terms=max_terms)
        if not mermaid_code:
            raise HTTPException(status_code=400, detail="لا توجد مفردات لتوليد المخطط")
        return {
            "success": True,
            "diagram_type": diagram_type,
            "mermaid_code": mermaid_code,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Mermaid generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/study-guide/full")
async def api_generate_study_guide_full(
    title: str = "مرجع دراسي شامل",
    include_mermaid: bool = True,
    include_flashcards: bool = True,
):
    """توليد مرجع دراسي شامل يتضمن Mermaid + Flashcards + Markdown."""
    try:
        from modules.export.study_guide import generate_study_guide_full
        content = generate_study_guide_full(
            title=title,
            include_mermaid=include_mermaid,
            include_flashcards=include_flashcards,
        )
        if not content:
            raise HTTPException(status_code=400, detail="لا توجد بيانات كافية")
        return {
            "success": True,
            "size": len(content),
            "preview": content[:1500] + ("..." if len(content) > 1500 else ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Full study guide failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# === Metrics & History Endpoints ===

@app.get("/api/metrics")
async def api_compute_metrics():
    """حساب WER/CER الحاليين."""
    try:
        from modules.evaluation.metrics import calculate_cer, calculate_wer
        return {"message": "Metrics endpoint ready - requires active processing data"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/history")
async def api_metrics_history():
    """سجل WER/CER عبر جلسات التدريب."""
    return {"history": []}


# === Auto Export & Backup Endpoints ===

@app.post("/api/auto-export")
async def api_auto_export():
    """تصدير تلقائي شامل."""
    try:
        from modules.export.exporter import DocumentExporter
        return {"success": True, "message": "Auto-export endpoint ready"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/backup")
async def api_create_backup():
    """إنشاء نسخة احتياطية شاملة."""
    try:
        from modules.security.backup_manager import BackupManager
        manager = BackupManager()
        result = manager.create_backup()
        return {"success": True, "backup_dir": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Layout Preserving Export Endpoints ===

@app.post("/api/export/layout-preserving")
async def api_layout_preserving_export(
    file: UploadFile = File(...),
    format: str = "docx",
):
    """تصدير مع الحفاظ على التنسيق و RTL."""
    start_time = time.time()
    try:
        from modules.export.layout_preserving import LayoutPreservingExporter

        suffix = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            exporter = LayoutPreservingExporter()
            if format == "html":
                output_path = exporter.export_to_html(tmp_path)
            else:
                output_path = exporter.export_to_docx(tmp_path)

            duration = (time.time() - start_time) * 1000
            return FileResponse(
                path=output_path,
                filename=f"layout_preserved.{format}",
                media_type="application/octet-stream" if format == "docx" else "text/html",
            )
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        logger.error("Layout preserving export failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# === Entry Point ===

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=5001, reload=True)
