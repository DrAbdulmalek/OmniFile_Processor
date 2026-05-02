"""
HandwrittenOCR - نظام التسجيل المفصّل v7.0
=============================================
يسجّل كل ما يحدث في التطبيق بالتفصيل:
- كل خطوة معالجة مع الوقت والمكان
- الأخطاء مع traceback كامل
- أحداث منظمة (JSON) لسهولة التحليل
- تقرير HTML تلقائي
- الذاكرة والأداء
"""

import logging
import os
import sys
import json
import traceback
import time
import functools
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


# ===================== الفورمتر المفصّل =====================

class DetailedFormatter(logging.Formatter):
    """فورمتر مفصّل يتضمن: الوقت، المستوى، الملف، الدالة، السطر، الرسالة."""

    COLORS = {
        "DEBUG": "\033[36m",     # سماوي
        "INFO": "\033[32m",      # أخضر
        "WARNING": "\033[33m",   # أصفر
        "ERROR": "\033[31m",     # أحمر
        "CRITICAL": "\033[1;31m", # أحمر عريض
    }
    RESET = "\033[0m"

    def __init__(self, colorize=False):
        super().__init__()
        self.colorize = colorize

    def format(self, record):
        # إضافة traceback كامل للأخطاء
        if record.exc_info and record.exc_info[0] is not None:
            record.exc_text = self.format_exception(record.exc_info)

        # البنية: 2026-05-01 12:34:56 | INFO     | module:function:42 | رسالة
        module = record.module or "unknown"
        func = record.funcName or "?"
        line = record.lineno or 0
        location = f"{module}:{func}:{line}"

        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # اللون (للشاشة فقط)
        level = record.levelname
        if self.colorize and level in self.COLORS:
            level_str = f"{self.COLORS[level]}{level:<8}{self.RESET}"
        else:
            level_str = f"{level:<8}"

        msg = record.getMessage()

        # تنسيق الرسالة النهائي
        result = f"{timestamp} | {level_str} | {location} | {msg}"

        # إلحاق الـ traceback
        if hasattr(record, 'exc_text') and record.exc_text:
            result += "\n" + record.exc_text

        # إلحاق معلومات إضافية
        if hasattr(record, 'extra_data') and record.extra_data:
            result += f"\n    [تفاصيل] {json.dumps(record.extra_data, ensure_ascii=False, default=str)}"

        return result

    def format_exception(self, exc_info):
        """تنسيق traceback كامل ومفصّل."""
        lines = []
        lines.append("    ╔═══════════════════════════════════════════════════════════")
        lines.append("    ║                     تتبع الخطأ الكامل                      ")
        lines.append("    ╠═══════════════════════════════════════════════════════════")
        tb_lines = traceback.format_exception(*exc_info)
        for line in tb_lines:
            for sub in line.rstrip("\n").split("\n"):
                lines.append(f"    ║ {sub}")
        lines.append("    ╚═══════════════════════════════════════════════════════════")
        return "\n".join(lines)


# ===================== مُسجّل الأحداث المنظمة (JSON) =====================

class EventLogger:
    """يسجّل الأحداث بتنسيق JSON منظّم في ملف منفصل."""

    def __init__(self, events_log_path: str):
        self.events_log_path = events_log_path
        os.makedirs(os.path.dirname(events_log_path), exist_ok=True)

    def log_event(self, event_type: str, data: dict = None, status: str = "ok"):
        """تسجيل حدث."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "status": status,
            "data": data or {},
        }
        try:
            with open(self.events_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass


# ===================== إعداد اللوغ =====================

_event_logger = None


def setup_logging(config=None, log_dir=None, log_level="DEBUG"):
    """
    إعداد نظام التسجيل المفصّل.

    Parameters:
        config: كائن الإعدادات (اختياري)
        log_dir: مسار مجلد اللوق (اختياري — يُستخدم بدلاً من config)
        log_level: مستوى التسجيل (افتراضي DEBUG)

    Returns:
        logging.Logger: كائن اللوغ الرئيسي
    """
    global _event_logger

    if config:
        config.ensure_dirs()
        logs_dir = config.logs_dir
        log_file = config.log_file
        events_file = config.events_jsonl
        level = getattr(logging, config.log_level.upper(), logging.DEBUG)
    else:
        logs_dir = log_dir or "/app/data/logs"
        os.makedirs(logs_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(logs_dir, f"ocr_{ts}.log")
        events_file = os.path.join(logs_dir, f"ocr_events_{ts}.jsonl")
        level = getattr(logging, log_level.upper(), logging.DEBUG)

    # اللوغ الرئيسي
    logger = logging.getLogger("HandwrittenOCR")
    logger.setLevel(level)
    logger.handlers.clear()

    # === Handler 1: ملف مفصّل (كل شيء) ===
    detailed_handler = RotatingFileHandler(
        log_file,
        maxBytes=5_000_000,  # 5 MB
        backupCount=10,
        encoding="utf-8",
    )
    detailed_handler.setLevel(logging.DEBUG)
    detailed_handler.setFormatter(DetailedFormatter(colorize=False))
    logger.addHandler(detailed_handler)

    # === Handler 2: ملف الأخطاء فقط ===
    errors_file = log_file.replace(".log", "_errors.log")
    error_handler = RotatingFileHandler(
        errors_file,
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(DetailedFormatter(colorize=False))
    logger.addHandler(error_handler)

    # === Handler 3: الشاشة (مختصر) ===
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(DetailedFormatter(colorize=True))
    logger.addHandler(stream_handler)

    # === مسجّل الأحداث ===
    _event_logger = EventLogger(events_file)

    # تسجيل البداية
    logger.info("=" * 65)
    logger.info("بدء تشغيل HandwrittenOCR — نظام التسجيل المفصّل v7.0")
    logger.info(f"ملف اللوق:   {log_file}")
    logger.info(f"ملف الأخطاء:  {errors_file}")
    logger.info(f"ملف الأحداث:  {events_file}")
    logger.info(f"مستوى التسجيل: {logging.getLevelName(level)}")
    logger.info("=" * 65)

    return logger


def get_event_logger() -> EventLogger:
    """الحصول على مسجّل الأحداث."""
    return _event_logger


# ===================== أدوات مساعدة =====================

def log_function_entry_exit(logger):
    """ديكوراتور يسجّل دخول وخروج الدالة مع الوقت والمعاملات."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            args_str = [repr(a)[:100] for a in args]
            kwargs_str = [f"{k}={repr(v)[:100]}" for k, v in kwargs.items()]
            all_params = ", ".join(args_str + kwargs_str)
            if len(all_params) > 300:
                all_params = all_params[:300] + "..."

            logger.debug(f"ENTER {func_name}({all_params})")
            start = time.time()

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                logger.debug(f"EXIT  {func_name} — نجح في {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(
                    f"FAIL  {func_name} — فشل بعد {elapsed:.3f}s — {type(e).__name__}: {e}",
                    exc_info=True,
                )
                raise
        return wrapper
    return decorator


def log_step(logger, step_name: str, details: dict = None):
    """تسجيل خطوة معالجة مع التفاصيل."""
    logger.info(f"STEP  [{step_name}]")
    if details:
        for key, value in details.items():
            logger.info(f"      {key}: {value}")

    # تسجيل كحدث JSON
    evt = get_event_logger()
    if evt:
        evt.log_event(f"step:{step_name}", data=details)


def log_error_full(logger, context: str, error: Exception, extra: dict = None):
    """تسجيل خطأ بالتفصيل مع السياق و traceback كامل."""
    logger.error(
        f"ERROR [{context}] {type(error).__name__}: {error}",
        exc_info=True,
        extra=extra or {},
    )

    # تسجيل كحدث JSON
    evt = get_event_logger()
    if evt:
        evt.log_event(
            f"error:{context}",
            data={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
                **(extra or {}),
            },
            status="error",
        )


def log_result(logger, step_name: str, result: dict):
    """تسجيل نتيجة خطوة."""
    summary = {k: v for k, v in result.items() if k != "error"}
    logger.info(f"RESULT [{step_name}] {json.dumps(summary, ensure_ascii=False, default=str)}")

    evt = get_event_logger()
    if evt:
        evt.log_event(f"result:{step_name}", data=result)


# ===================== تقرير HTML من اللوق =====================

def log_health_snapshot(logger, extra: dict = None) -> dict:
    """تسجيل لقطة صحة النظام (Platform, CUDA, RAM, Python)."""
    import platform
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    # CUDA
    try:
        import torch
        snapshot["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            snapshot["gpu_name"] = props.name
            snapshot["gpu_vram_gb"] = round(props.total_mem / 1e9, 1)
    except Exception:
        snapshot["cuda_available"] = False
    # RAM
    try:
        import psutil
        mem = psutil.virtual_memory()
        snapshot["ram_total_gb"] = round(mem.total / 1e9, 1)
        snapshot["ram_available_gb"] = round(mem.available / 1e9, 1)
    except Exception:
        pass
    # Disk
    try:
        import shutil
        usage = shutil.disk_usage("/")
        snapshot["disk_free_gb"] = round(usage.free / 1e9, 1)
    except Exception:
        pass
    if extra:
        snapshot.update(extra)

    log_step(logger, "لقطة صحة النظام", snapshot)
    return snapshot


def generate_log_report(log_file: str, output_html: str = None) -> str:
    """
    توليد تقرير HTML مفصّل من ملف اللوق.

    Parameters:
        log_file: مسار ملف اللوق
        output_html: مسار ملف HTML الناتج (اختياري)

    Returns:
        str: مسار ملف HTML
    """
    if not os.path.exists(log_file):
        return ""

    if output_html is None:
        output_html = log_file.replace(".log", "_report.html")

    # قراءة اللوق
    lines = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return ""

    # تحليل اللوق
    errors = []
    warnings = []
    steps = []
    info_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if "ERROR" in stripped or "FAIL" in stripped:
            errors.append(stripped)
        elif "WARNING" in stripped:
            warnings.append(stripped)
        elif "STEP" in stripped:
            steps.append(stripped)
        elif "RESULT" in stripped:
            info_lines.append(stripped)

    # إنشاء HTML
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تقرير اللوق — HandwrittenOCR</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f5f5f5; padding: 20px; direction: rtl; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #333; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; justify-content: center; }}
        .stat-card {{ background: white; border-radius: 10px; padding: 15px 25px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); min-width: 150px; }}
        .stat-card .number {{ font-size: 2em; font-weight: bold; }}
        .stat-card .label {{ color: #666; font-size: 0.9em; }}
        .stat-errors .number {{ color: #e74c3c; }}
        .stat-warnings .number {{ color: #f39c12; }}
        .stat-steps .number {{ color: #3498db; }}
        .stat-results .number {{ color: #2ecc71; }}
        .section {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .section h2 {{ margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #eee; }}
        .section.errors h2 {{ color: #e74c3c; }}
        .section.warnings h2 {{ color: #f39c12; }}
        .section.steps h2 {{ color: #3498db; }}
        pre {{ background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 0.85em; line-height: 1.6; direction: ltr; text-align: left; white-space: pre-wrap; word-wrap: break-word; }}
        .error-line {{ color: #ff6b6b; }}
        .warning-line {{ color: #ffd93d; }}
        .step-line {{ color: #6bcbff; }}
        .result-line {{ color: #6bff6b; }}
        .meta {{ text-align: center; color: #999; font-size: 0.85em; margin-top: 20px; }}
    </style>
</head>
<body>
<div class="container">
    <h1>HandwrittenOCR — تقرير اللوق المفصّل</h1>
    <div class="meta">تم الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ملف اللوق: {os.path.basename(log_file)}</div>

    <div class="stats">
        <div class="stat-card stat-errors">
            <div class="number">{len(errors)}</div>
            <div class="label">خطأ</div>
        </div>
        <div class="stat-card stat-warnings">
            <div class="number">{len(warnings)}</div>
            <div class="label">تحذير</div>
        </div>
        <div class="stat-card stat-steps">
            <div class="number">{len(steps)}</div>
            <div class="label">خطوة معالجة</div>
        </div>
        <div class="stat-card stat-results">
            <div class="number">{len(info_lines)}</div>
            <div class="label">نتيجة</div>
        </div>
    </div>
"""

    if errors:
        html += '<div class="section errors"><h2>الأخطاء ({})</h2><pre>'.format(len(errors))
        for e in errors:
            escaped = e.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html += f'<span class="error-line">{escaped}</span>\n'
        html += '</pre></div>'

    if warnings:
        html += '<div class="section warnings"><h2>التحذيرات ({})</h2><pre>'.format(len(warnings))
        for w in warnings:
            escaped = w.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html += f'<span class="warning-line">{escaped}</span>\n'
        html += '</pre></div>'

    if steps:
        html += '<div class="section steps"><h2>خطوات المعالجة ({})</h2><pre>'.format(len(steps))
        for s in steps:
            escaped = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html += f'<span class="step-line">{escaped}</span>\n'
        html += '</pre></div>'

    html += '<div class="section"><h2>النتائج ({})</h2><pre>'.format(len(info_lines))
    for r in info_lines:
        escaped = r.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html += f'<span class="result-line">{escaped}</span>\n'
    html += '</pre></div>'

    html += """
    <div class="section">
        <h2>اللوق الكامل</h2>
        <pre>"""
    for line in lines:
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html += escaped
    html += """</pre>
    </div>
</div>
</body>
</html>"""

    try:
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception:
        pass

    return output_html
