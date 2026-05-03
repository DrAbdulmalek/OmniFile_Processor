"""
نظام تسجيل تصحيحات المراجعة (Feedback System)
=================================================
مُرحَّل من src/correction.py إلى modules/nlp/feedback.py
كجزء من خطة ترحيل src/ → modules/ (v4.2.0).

يحتوي:
- append_feedback(): تسجيل تصحيح في ملف CSV
- مُصدَّر من src.correction للحفاظ على التوافق العكسي
"""

import json
import os
import logging
import traceback
import pandas as pd
from datetime import datetime
from collections import Counter, defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("modules.nlp.feedback")


# ===================== قوائم الكلمات المحمية =====================

TECHNICAL_KEYWORDS = {
    # مصطلحات برمجية عامة
    "python", "pythonistas", "scraping", "parsing", "ocr",
    "batch", "programming", "script", "database", "configure",
    "setup", "env", "immutable", "concatenation", "tuples",
    "dictionaries", "debugging", "programmatically", "spreadsheet",
    "integers", "float", "boolean", "syntax", "web",
    "etl", "dataframe", "json", "csv", "yaml", "markdown",
    "mermaid", "repository", "clone", "commit", "push",
    # اختصارات تقنية
    "repl", "dpi", "api", "gpu", "cpu", "ram", "rom",
    "lora", "huggingface", "transformers", "pytorch", "tensorboard",
    # كلمات من ملاحظات المستخدم
    "printouts", "involve", "scattered", "skyrocketed", "stacked",
    "affectionately", "serpentine", "cryptic", "sophisticated",
    "intricate", "throwaway", "surreal", "conventions",
    "trade", "off", "boot", "camps",
    # مفاهيم تقنية
    "comprehensions", "replication", "precedence", "modulo",
    "exponent", "traceback", "overriding",
}

PYTHON_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
    "try", "while", "with", "yield",
    # دوال مدمجة
    "print", "input", "len", "range", "type", "int", "str", "float",
    "list", "dict", "set", "tuple", "bool", "open", "file", "super",
    "self", "cls", "init", "repr", "main", "name", "args", "kwargs",
    "append", "extend", "pop", "sort", "join", "split", "strip",
    "format", "replace", "lower", "upper", "title", "capitalize",
    "enumerate", "zip", "map", "filter", "sorted", "reversed",
    "isinstance", "issubclass", "hasattr", "getattr", "setattr",
    "import", "from", "as", "module", "package",
}

_CUSTOM_VOCAB = set()
_PROTECTED_WORDS_LOWER = set()


def _rebuild_protected_set():
    """إعادة بناء مجموعة الكلمات المحمية."""
    global _PROTECTED_WORDS_LOWER
    _PROTECTED_WORDS_LOWER = (
        {k.lower() for k in TECHNICAL_KEYWORDS}
        | {k.lower() for k in PYTHON_KEYWORDS}
        | {k.lower() for k in _CUSTOM_VOCAB}
    )
    logger.debug(f"أُعيد بناء القائمة المحمية: {len(_PROTECTED_WORDS_LOWER)} كلمة")


def _is_protected_word(word: str) -> bool:
    """التحقق مما إذا كانت الكلمة محمية."""
    result = word.lower() in _PROTECTED_WORDS_LOWER
    if result:
        logger.debug(f"  كلمة محمية: '{word}' — يتجاوز التصحيح")
    return result


def load_custom_vocabulary(vocab_list: list[str]) -> None:
    """تحميل مصطلحات إضافية لحمايتها من التصحيح."""
    global _CUSTOM_VOCAB
    logger.info(f"تحميل {len(vocab_list)} مصطلح إضافي في القائمة المحمية")
    new_words = [w.strip() for w in vocab_list if w.strip()]
    _CUSTOM_VOCAB.update(new_words)
    _rebuild_protected_set()
    logger.info(f"المجموع المحمي الآن: {len(_PROTECTED_WORDS_LOWER)} كلمة")


def get_protected_words_count() -> dict:
    """إرجاع عدد الكلمات المحمية لكل فئة."""
    return {
        "technical_keywords": len(TECHNICAL_KEYWORDS),
        "python_keywords": len(PYTHON_KEYWORDS),
        "custom_vocabulary": len(_CUSTOM_VOCAB),
        "total_protected": len(_PROTECTED_WORDS_LOWER),
    }


# ===================== قواعد التصحيح المتقدمة =====================

@dataclass
class CorrectionRule:
    """قاعدة تصحيح ببيانات وصفية كاملة لتتبع الاستخدام والمراجعة."""
    original: str
    correction: str
    votes: int = 1
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = None
    usage_count: int = 0
    last_reviewed: str = None
    reviewer: str = None
    confidence: float = 1.0
    contexts: list = field(default_factory=list)
    flagged: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "original": self.original, "correction": self.correction,
            "votes": self.votes, "first_seen": self.first_seen,
            "last_used": self.last_used, "usage_count": self.usage_count,
            "last_reviewed": self.last_reviewed, "reviewer": self.reviewer,
            "confidence": self.confidence, "contexts": self.contexts,
            "flagged": self.flagged, "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict, key: str = "") -> "CorrectionRule":
        if isinstance(data, str):
            return cls(original=key, correction=data)
        return cls(
            original=data.get("original", key), correction=data.get("correction", data.get(key, "")),
            votes=data.get("votes", 1), first_seen=data.get("first_seen", datetime.now().isoformat()),
            last_used=data.get("last_used"), usage_count=data.get("usage_count", 0),
            last_reviewed=data.get("last_reviewed"), reviewer=data.get("reviewer"),
            confidence=data.get("confidence", 1.0), contexts=data.get("contexts", []),
            flagged=data.get("flagged", False), notes=data.get("notes", ""),
        )


# ===================== تسجيل التصحيحات (Feedback) =====================

def append_feedback(
    feedback_csv: str,
    image_id: int,
    original: str,
    corrected: str,
    status: str = "verified",
) -> None:
    """تسجيل تصحيح في ملف CSV مع تسجيل."""
    os.makedirs(os.path.dirname(feedback_csv), exist_ok=True)
    ts = datetime.now().isoformat()
    record = {
        "timestamp": ts,
        "image_id": image_id,
        "original_text": original,
        "corrected_text": corrected,
        "status": status,
    }
    file_exists = os.path.exists(feedback_csv)
    pd.DataFrame([record]).to_csv(
        feedback_csv, mode="a",
        header=not file_exists,
        index=False, encoding="utf-8-sig",
    )
    logger.debug(f"append_feedback: image_id={image_id}, '{original[:30]}' => '{corrected[:30]}', status={status}")


# ===================== بناء وتحميل قاموس التصحيح =====================

def build_correction_dict(
    feedback_csv: str,
    correction_dict_path: str,
    min_votes: int = 1,
) -> dict:
    """بناء قاموس تصحيح من تصحيحات المستخدم مع تسجيل مفصّل."""
    logger.info(f"بناء قاموس التصحيح: csv={feedback_csv}, dict={correction_dict_path}, min_votes={min_votes}")

    if not os.path.exists(feedback_csv):
        logger.info("  ملف feedback غير موجود — قاموس فارغ")
        return {}

    try:
        df_fb = pd.read_csv(feedback_csv, encoding="utf-8-sig")
        if df_fb.empty:
            logger.info("  ملف feedback فارغ — قاموس فارغ")
            return {}

        buckets = defaultdict(Counter)
        for _, row in df_fb.iterrows():
            orig = str(row.get("original_text", "")).strip()
            corr = str(row.get("corrected_text", "")).strip()
            if orig and corr and orig != corr:
                buckets[orig][corr] += 1

        result = {
            orig: cnt.most_common(1)[0][0]
            for orig, cnt in buckets.items()
            if cnt.most_common(1)[0][1] >= min_votes
        }

        os.makedirs(os.path.dirname(correction_dict_path), exist_ok=True)
        with open(correction_dict_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"تم تحديث قاموس التصحيح: {len(result)} كلمة من {len(df_fb)} سجل")
        return result

    except Exception as e:
        logger.error(f"بناء قاموس التصحيح فشل: {e}", exc_info=True)
        return {}


def build_correction_dict_v2(feedback_csv: str, correction_dict_path: str, min_votes: int = 1) -> dict:
    """بناء قاموس تصحيح متقدم مع CorrectionRule ببيانات وصفية."""
    logger.info(f"build_correction_dict_v2: csv={feedback_csv}, min_votes={min_votes}")
    if not os.path.exists(feedback_csv):
        return {}
    try:
        df_fb = pd.read_csv(feedback_csv, encoding="utf-8-sig")
        if df_fb.empty:
            return {}
        buckets = defaultdict(list)
        for _, row in df_fb.iterrows():
            orig = str(row.get("original_text", "")).strip()
            corr = str(row.get("corrected_text", "")).strip()
            if orig and corr and orig != corr:
                buckets[orig].append({
                    "correction": corr,
                    "timestamp": str(row.get("timestamp", "")),
                    "image_id": row.get("image_id"),
                    "status": row.get("status"),
                })
        result = {}
        for orig, entries in buckets.items():
            counts = Counter(e["correction"] for e in entries)
            best_corr, best_count = counts.most_common(1)[0]
            if best_count >= min_votes:
                rule = CorrectionRule(
                    original=orig, correction=best_corr,
                    votes=best_count,
                    first_seen=min(e["timestamp"] for e in entries if e["timestamp"]) or datetime.now().isoformat(),
                    contexts=[e["image_id"] for e in entries if e.get("image_id")],
                )
                result[orig] = rule
        os.makedirs(os.path.dirname(correction_dict_path), exist_ok=True)
        with open(correction_dict_path, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in result.items()}, f, ensure_ascii=False, indent=2)
        logger.info(f"build_correction_dict_v2: {len(result)} قاعدة من {len(df_fb)} سجل")
        return result
    except Exception as e:
        logger.error(f"build_correction_dict_v2 فشل: {e}", exc_info=True)
        return {}


def load_correction_dict(correction_dict_path: str) -> dict:
    """تحميل قاموس التصحيح من الملف مع تسجيل."""
    if not os.path.exists(correction_dict_path):
        logger.debug(f"load_correction_dict: الملف غير موجود: {correction_dict_path}")
        return {}
    try:
        with open(correction_dict_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        logger.info(f"تم تحميل قاموس التصحيح: {len(result)} كلمة من {correction_dict_path}")
        return result
    except Exception as e:
        logger.error(f"تحميل قاموس التصحيح فشل: {e}", exc_info=True)
        return {}


def apply_correction_dict(text: str, correction_dict: dict) -> str:
    """تطبيق قاموس التصحيح على نص مع تسجيل التعديلات."""
    if not correction_dict or not text:
        return text
    words = text.split()
    corrected = [correction_dict.get(w, w) for w in words]
    changes = [(w, corrected[i]) for i, w in enumerate(words) if w != corrected[i]]
    if changes:
        logger.debug(f"apply_correction_dict: {len(changes)} تعديل من القاموس: {changes[:5]}")
    return " ".join(corrected)


def track_correction_usage(correction_dict_path: str, word: str) -> None:
    """تحديث عداد الاستخدام لقاعدة تصحيح عند تطبيقها."""
    if not word or not os.path.exists(correction_dict_path):
        return
    try:
        with open(correction_dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if word in data:
            entry = data[word]
            entry["usage_count"] = entry.get("usage_count", 0) + 1
            entry["last_used"] = datetime.now().isoformat()
            with open(correction_dict_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def calculate_rule_indicator(rule: CorrectionRule, thresholds: dict = None) -> dict:
    """حساب مؤشر بصري لقاعدة تصحيح: 🟢 موثوق / 🟡 مراجعة / 🔴 عاجل / ⏳ جديد."""
    if thresholds is None:
        thresholds = {
            "conf_low": 0.60, "conf_mid": 0.80,
            "usage_high": 50, "usage_mid": 20,
            "days_critical": 30, "days_warning": 14, "new_days_warning": 3,
        }
    score = 0
    if rule.confidence < thresholds.get("conf_low", 0.60):
        score += 3
    elif rule.confidence < thresholds.get("conf_mid", 0.80):
        score += 1
    if rule.flagged:
        score += 2

    days_review = 999
    if rule.last_reviewed:
        try:
            days_review = (datetime.now() - datetime.fromisoformat(rule.last_reviewed)).days
        except Exception:
            pass
    if rule.usage_count > thresholds.get("usage_high", 50) and days_review > thresholds.get("days_critical", 30):
        score += 2

    days_seen = 999
    try:
        days_seen = (datetime.now() - datetime.fromisoformat(rule.first_seen)).days
    except Exception:
        pass

    if score >= 5:
        visual = "🔴 عاجل"
    elif score >= 3:
        visual = "🟡 مراجعة مقترحة"
    elif score == 0 and days_seen <= thresholds.get("new_days_warning", 3):
        visual = "⏳ جديد"
    else:
        visual = "🟢 موثوق"

    return {
        "visual": visual, "score": score,
        "confidence": rule.confidence, "usage_count": rule.usage_count,
        "days_since_review": days_review, "days_since_seen": days_seen,
        "votes": rule.votes, "flagged": rule.flagged,
    }


def get_dictionary_audit_queue(correction_dict_path: str, priority: str = "all", limit: int = 20) -> list:
    """جلب قائمة انتظار مراجعة القاموس."""
    if not os.path.exists(correction_dict_path):
        return []
    try:
        with open(correction_dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return []
        rules = []
        for k, v in data.items():
            rule = CorrectionRule.from_dict(v, k)
            indicator = calculate_rule_indicator(rule)
            rules.append({"key": k, "rule": rule, "indicator": indicator})

        if priority == "flagged":
            rules = [r for r in rules if r["rule"].flagged]
        elif priority == "new":
            rules = sorted(rules, key=lambda r: r["indicator"]["days_since_seen"], reverse=True)
        elif priority == "low_conf":
            rules = sorted(rules, key=lambda r: r["rule"].confidence)
        else:
            rules = sorted(rules, key=lambda r: r["indicator"]["score"], reverse=True)

        return rules[:limit]
    except Exception as e:
        logger.error(f"get_dictionary_audit_queue فشل: {e}", exc_info=True)
        return []


def archive_correction_rule(correction_dict_path: str, key: str, reason: str = "") -> bool:
    """أرشفة قاعدة تصحيح بدلاً من حذفها."""
    if not os.path.exists(correction_dict_path):
        return False
    try:
        with open(correction_dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if key not in data:
            return False
        rule_data = data.pop(key)
        rule_data["archived_reason"] = reason
        rule_data["archived_at"] = datetime.now().isoformat()
        archive_path = correction_dict_path.replace(".json", "_archived.json")
        archive = {}
        if os.path.exists(archive_path):
            with open(archive_path, "r", encoding="utf-8") as f:
                archive = json.load(f)
        archive[key] = rule_data
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)
        with open(correction_dict_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"archive_correction_rule: '{key}' reason='{reason}'")
        return True
    except Exception as e:
        logger.error(f"archive_correction_rule فشل: {e}", exc_info=True)
        return False


def auto_calibrate_dict_thresholds(correction_dict_path: str, method: str = "percentile") -> dict:
    """معايرة تلقائية لعتبات مؤشرات القاموس."""
    if not os.path.exists(correction_dict_path):
        return {}
    try:
        with open(correction_dict_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return {}
        confs = [v.get("confidence", 1.0) for v in data.values()]
        usages = [v.get("usage_count", 0) for v in data.values()]
        if not confs:
            return {}
        if method == "std_dev":
            import numpy as np
            c_low = max(0.0, float(np.mean(confs) - np.std(confs)))
            c_mid = float(np.mean(confs))
            u_mid = float(np.median(usages))
            u_high = float(np.percentile(usages, 90)) if usages else 50
        else:
            import numpy as np
            c_low, c_mid = np.percentile(confs, [25, 50])
            u_mid, u_high = np.percentile(usages, [75, 90]) if usages else (20, 50)

        thresholds = {
            "conf_low": round(c_low, 3), "conf_mid": round(c_mid, 3),
            "usage_high": int(u_high), "usage_mid": int(u_mid),
            "calibrate_method": method,
        }
        logger.info(f"auto_calibrate: {thresholds}")
        return thresholds
    except Exception as e:
        logger.error(f"auto_calibrate_dict_thresholds فشل: {e}", exc_info=True)
        return {}
