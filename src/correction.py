"""
src/correction.py — محرك التصحيح الإملائي v6.0
=================================================
إعادة هيكلة كاملة: HybridSpellChecker كـ backend موحَّد
---------------------------------------------------------
التغييرات الجوهرية v6.0:
  ✅ إزالة globals (_ar_corrector, _en_spellchecker, _de_spellchecker)
  ✅ HybridSpellChecker يُدير المحركات داخلياً (lazy + thread-safe)
  ✅ TECHNICAL_KEYWORDS / PYTHON_KEYWORDS تُعاد تصديرها للتوافق
  ✅ correct_text() / spell_correct_word() يفوّضان إلى HybridSpellChecker
  ✅ الجزء الفريد (CorrectionRule, audit, CSV feedback) يبقى هنا

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

import json
import logging
import os
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

logger = logging.getLogger("HandwrittenOCR")

# ── أدوات اللوق (من src/logger أو fallback) ─────────────────────
try:
    from src.logger import log_step, log_error_full, log_result
except ImportError:
    def log_step(lg, name, data=None):
        lg.info(f"STEP [{name}]")
        if data:
            for k, v in data.items():
                lg.info(f"      {k}: {v}")
    def log_error_full(lg, ctx, err, extra=None):
        lg.error(f"ERROR [{ctx}] {type(err).__name__}: {err}", exc_info=True)
    def log_result(lg, name, result):
        lg.info(f"RESULT [{name}] {result}")

# ── HybridSpellChecker كـ backend موحَّد ─────────────────────────
try:
    import sys as _sys, os as _os
    _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    from modules.core.spell_checker import HybridSpellChecker, TECHNICAL_KEYWORDS, PYTHON_KEYWORDS
    _SC = HybridSpellChecker()
    _SC_AVAILABLE = True
    logger.info("correction.py: HybridSpellChecker loaded as backend")
except Exception as _sc_err:
    _SC = None
    _SC_AVAILABLE = False
    TECHNICAL_KEYWORDS = frozenset()
    PYTHON_KEYWORDS    = frozenset()
    logger.warning("correction.py: HybridSpellChecker unavailable — %s", _sc_err)

# ── re-export للتوافق مع الكود القديم ───────────────────────────
__all__ = [
    "TECHNICAL_KEYWORDS", "PYTHON_KEYWORDS",
    "correct_text", "spell_correct_word", "enhance_digit_recognition",
    "init_correctors", "load_custom_vocabulary", "get_protected_words_count",
    "CorrectionRule", "build_correction_dict", "build_correction_dict_v2",
    "load_correction_dict", "apply_correction_dict", "append_feedback",
    "track_correction_usage", "auto_calibrate_dict_thresholds",
    "calculate_rule_indicator", "get_dictionary_audit_queue",
    "archive_correction_rule",
]


# ══════════════════════════════════════════════════════════════════
# الجزء 1: واجهة التصحيح الإملائي — تفويض إلى HybridSpellChecker
# ══════════════════════════════════════════════════════════════════

def init_correctors() -> None:
    """
    تهيئة المدققات.
    v6.0: HybridSpellChecker يُهيّئ نفسه lazily — لا globals.
    """
    global _SC, _SC_AVAILABLE
    if not _SC_AVAILABLE:
        try:
            from modules.core.spell_checker import HybridSpellChecker
            _SC = HybridSpellChecker()
            _SC_AVAILABLE = True
        except Exception as e:
            log_error_full(logger, "init_correctors", e)
            return

    stats = _SC.get_protected_count() if hasattr(_SC, "get_protected_count") else {}
    log_result(logger, "init_correctors", {
        "backend":         "HybridSpellChecker",
        "protected_words": stats.get("total_protected", 0),
        "arabic":          True,
        "english":         True,
        "german":          True,
    })


def load_custom_vocabulary(vocab_list: list) -> None:
    """تحميل مصطلحات إضافية لحمايتها من التصحيح."""
    if not vocab_list:
        return
    if _SC_AVAILABLE:
        _SC.add_protected_words(vocab_list)
        logger.info("load_custom_vocabulary: %d كلمة أُضيفت للحماية", len(vocab_list))
    else:
        logger.warning("load_custom_vocabulary: HybridSpellChecker غير متاح")


def _is_protected_word(word: str) -> bool:
    """التحقق مما إذا كانت الكلمة محمية."""
    if _SC_AVAILABLE:
        return _SC._is_protected(word)
    return word.lower() in {w.lower() for w in TECHNICAL_KEYWORDS | PYTHON_KEYWORDS}


def correct_text(text: str) -> str:
    """
    تصحيح إملائي كامل للنص — يكتشف اللغة تلقائياً.
    v6.0: يفوّض إلى HybridSpellChecker.correct_text().
    """
    if not text or not text.strip():
        return text
    if _SC_AVAILABLE:
        result = _SC.correct_text(text)
        if result != text:
            logger.debug("correct_text: '%s' => '%s'", text[:60], result[:60])
        return enhance_digit_recognition(result)
    # Fallback بسيط إذا لم يكن المحرك متاحاً
    return text


def spell_correct_word(text: str) -> str:
    """
    تصحيح سريع لكلمة أو عبارة قصيرة.
    v6.0: يفوّض إلى HybridSpellChecker.auto_correct().
    """
    text = text.strip()
    if not text:
        return ""
    if _is_protected_word(text):
        logger.debug("spell_correct_word: '%s' محمية — يتجاوز", text)
        return text
    if _SC_AVAILABLE:
        corrected, lang = _SC.auto_correct(text)
        if corrected != text:
            logger.debug("spell_correct_word: '%s' => '%s' [%s]", text, corrected, lang)
        return enhance_digit_recognition(corrected)
    return text


def get_protected_words_count() -> dict:
    """إرجاع عدد الكلمات المحمية لكل فئة."""
    if _SC_AVAILABLE and hasattr(_SC, "get_protected_count"):
        return _SC.get_protected_count()
    return {
        "technical_keywords": len(TECHNICAL_KEYWORDS),
        "python_keywords":    len(PYTHON_KEYWORDS),
        "custom_vocabulary":  0,
        "total_protected":    len(TECHNICAL_KEYWORDS) + len(PYTHON_KEYWORDS),
    }


# ── تحويل الأرقام (unique — يبقى هنا) ──────────────────────────
_DIGIT_CORRECTIONS = {
    "O": "0", "o": "0",
    "I": "1", "l": "1", "|": "1",
    "Z": "2", "z": "2",
    "S": "5", "s": "5",
    "G": "6",
    "T": "7", "t": "7",
    "B": "8",
}


def enhance_digit_recognition(text: str) -> str:
    """
    تصحيح حرفي للأرقام: يحوّل الحروف المشابهة بصرياً للأرقام.
    O→0, I→1, S→5, ... (يعمل فقط على كلمات تبدو كأرقام)
    """
    if not text:
        return text
    words = text.split()
    corrected = []
    for word in words:
        clean = word.strip(".,;:!?\"'()-")
        if clean and all(c.isalnum() or c in "_-/" for c in clean):
            if any(c.isdigit() for c in clean):
                fixed = clean
                for letter, digit in _DIGIT_CORRECTIONS.items():
                    fixed = fixed.replace(letter, digit)
                if fixed != clean and fixed.isdigit():
                    corrected.append(word.replace(clean, fixed))
                    continue
        corrected.append(word)
    return " ".join(corrected)


# ══════════════════════════════════════════════════════════════════
# الجزء 2: قواعد التصحيح (unique — CorrectionRule + audit)
# ══════════════════════════════════════════════════════════════════

@dataclass
class CorrectionRule:
    """قاعدة تصحيح ببيانات وصفية كاملة: ثقة + تصويت + مراجعة + أرشفة."""
    original:      str
    correction:    str
    votes:         int   = 1
    first_seen:    str   = field(default_factory=lambda: datetime.now().isoformat())
    last_used:     str   = None
    usage_count:   int   = 0
    last_reviewed: str   = None
    reviewer:      str   = None
    confidence:    float = 1.0
    contexts:      list  = field(default_factory=list)
    flagged:       bool  = False
    notes:         str   = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data: dict, key: str = "") -> "CorrectionRule":
        if isinstance(data, str):
            return cls(original=key, correction=data)
        return cls(
            original     = data.get("original", key),
            correction   = data.get("correction", data.get(key, "")),
            votes        = data.get("votes", 1),
            first_seen   = data.get("first_seen", datetime.now().isoformat()),
            last_used    = data.get("last_used"),
            usage_count  = data.get("usage_count", 0),
            last_reviewed= data.get("last_reviewed"),
            reviewer     = data.get("reviewer"),
            confidence   = data.get("confidence", 1.0),
            contexts     = data.get("contexts", []),
            flagged      = data.get("flagged", False),
            notes        = data.get("notes", ""),
        )


def calculate_rule_indicator(rule: CorrectionRule, thresholds: dict = None) -> dict:
    """
    مؤشر بصري لصحة قاعدة التصحيح:
    🟢 موثوق | 🟡 مراجعة مقترحة | 🔴 عاجل | ⏳ جديد
    """
    t = thresholds or {
        "conf_low": 0.60, "conf_mid": 0.80,
        "usage_high": 50, "usage_mid": 20,
        "days_critical": 30, "days_warning": 14, "new_days_warning": 3,
    }
    score = 0
    if rule.confidence < t["conf_low"]:   score += 3
    elif rule.confidence < t["conf_mid"]: score += 1
    if rule.flagged:                       score += 2

    days_review = days_seen = 999
    try:
        if rule.last_reviewed:
            days_review = (datetime.now() - datetime.fromisoformat(rule.last_reviewed)).days
        days_seen = (datetime.now() - datetime.fromisoformat(rule.first_seen)).days
    except Exception:
        pass

    if rule.usage_count > t["usage_high"] and days_review > t["days_critical"]:
        score += 2

    if score >= 5:       visual = "🔴 عاجل"
    elif score >= 3:     visual = "🟡 مراجعة مقترحة"
    elif score == 0 and days_seen <= t["new_days_warning"]: visual = "⏳ جديد"
    else:                visual = "🟢 موثوق"

    return {
        "visual": visual, "score": score,
        "confidence": rule.confidence, "usage_count": rule.usage_count,
        "days_since_review": days_review, "days_since_seen": days_seen,
        "votes": rule.votes, "flagged": rule.flagged,
    }


def auto_calibrate_dict_thresholds(path: str, method: str = "percentile") -> dict:
    """معايرة تلقائية لعتبات مؤشرات القاموس بناءً على توزيع البيانات."""
    if not os.path.exists(path):
        return {}
    try:
        import numpy as np
        data = json.loads(open(path, encoding="utf-8").read())
        if not data: return {}
        confs  = [v.get("confidence", 1.0) for v in data.values()]
        usages = [v.get("usage_count", 0)  for v in data.values()]
        if method == "std_dev":
            c_low  = max(0.0, float(np.mean(confs) - np.std(confs)))
            c_mid  = float(np.mean(confs))
            u_mid  = float(np.median(usages))
            u_high = float(np.percentile(usages, 90))
        else:
            c_low, c_mid = np.percentile(confs, [25, 50])
            u_mid, u_high = np.percentile(usages, [75, 90])
        t = {
            "conf_low": round(float(c_low), 3), "conf_mid": round(float(c_mid), 3),
            "usage_high": int(u_high), "usage_mid": int(u_mid), "calibrate_method": method,
        }
        logger.info("auto_calibrate: %s", t)
        return t
    except Exception as e:
        log_error_full(logger, "auto_calibrate_dict_thresholds", e)
        return {}


def get_dictionary_audit_queue(path: str, priority: str = "all", limit: int = 20) -> list:
    """قائمة انتظار مراجعة القاموس مرتبة حسب الأولوية."""
    if not os.path.exists(path): return []
    try:
        data = json.loads(open(path, encoding="utf-8").read())
        rules = []
        for k, v in data.items():
            rule = CorrectionRule.from_dict(v, k)
            rules.append({"key": k, "rule": rule,
                          "indicator": calculate_rule_indicator(rule)})
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
        log_error_full(logger, "get_dictionary_audit_queue", e)
        return []


def archive_correction_rule(path: str, key: str, reason: str = "") -> bool:
    """أرشفة قاعدة بدلاً من حذفها (قابلة للاسترداد)."""
    if not os.path.exists(path): return False
    try:
        data = json.loads(open(path, encoding="utf-8").read())
        if key not in data: return False
        entry = data.pop(key)
        entry["archived_reason"] = reason
        entry["archived_at"]     = datetime.now().isoformat()
        archive_path = path.replace(".json", "_archived.json")
        archive = {}
        if os.path.exists(archive_path):
            archive = json.loads(open(archive_path, encoding="utf-8").read())
        archive[key] = entry
        json.dump(archive, open(archive_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        json.dump(data, open(path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        logger.info("archive_correction_rule: '%s' reason='%s'", key, reason)
        return True
    except Exception as e:
        log_error_full(logger, "archive_correction_rule", e)
        return False


# ══════════════════════════════════════════════════════════════════
# الجزء 3: بناء القاموس من تغذية راجعة CSV
# ══════════════════════════════════════════════════════════════════

def build_correction_dict(
    feedback_csv: str,
    correction_dict_path: str,
    min_votes: int = 1,
) -> dict:
    """بناء قاموس تصحيح بسيط (original→correction) من تصحيحات المستخدم."""
    log_step(logger, "build_correction_dict",
             {"feedback_csv": feedback_csv, "min_votes": min_votes})
    if not os.path.exists(feedback_csv): return {}
    try:
        df = pd.read_csv(feedback_csv, encoding="utf-8-sig")
        if df.empty: return {}
        buckets: dict = defaultdict(Counter)
        for _, row in df.iterrows():
            orig = str(row.get("original_text", "")).strip()
            corr = str(row.get("corrected_text", "")).strip()
            if orig and corr and orig != corr:
                buckets[orig][corr] += 1
        result = {o: c.most_common(1)[0][0]
                  for o, c in buckets.items()
                  if c.most_common(1)[0][1] >= min_votes}
        os.makedirs(os.path.dirname(correction_dict_path) or ".", exist_ok=True)
        json.dump(result, open(correction_dict_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        log_result(logger, "build_correction_dict",
                   {"entries": len(result), "rows": len(df)})
        return result
    except Exception as e:
        log_error_full(logger, "build_correction_dict", e)
        return {}


def build_correction_dict_v2(
    feedback_csv: str,
    correction_dict_path: str,
    min_votes: int = 1,
) -> dict:
    """
    بناء قاموس متقدم مع CorrectionRule (ببيانات وصفية كاملة).
    يدعم الثقة، التصويت، السياق.
    """
    log_step(logger, "build_correction_dict_v2",
             {"feedback_csv": feedback_csv, "min_votes": min_votes})
    if not os.path.exists(feedback_csv): return {}
    try:
        df = pd.read_csv(feedback_csv, encoding="utf-8-sig")
        if df.empty: return {}
        buckets: dict = defaultdict(list)
        for _, row in df.iterrows():
            orig = str(row.get("original_text", "")).strip()
            corr = str(row.get("corrected_text", "")).strip()
            if orig and corr and orig != corr:
                buckets[orig].append({
                    "correction": corr,
                    "timestamp":  str(row.get("timestamp", "")),
                    "image_id":   row.get("image_id"),
                })
        result = {}
        for orig, entries in buckets.items():
            counts = Counter(e["correction"] for e in entries)
            best, best_count = counts.most_common(1)[0]
            if best_count >= min_votes:
                ts_list = [e["timestamp"] for e in entries if e["timestamp"]]
                result[orig] = CorrectionRule(
                    original   = orig,
                    correction = best,
                    votes      = best_count,
                    first_seen = min(ts_list) if ts_list else datetime.now().isoformat(),
                    contexts   = [e["image_id"] for e in entries if e.get("image_id")],
                )
        os.makedirs(os.path.dirname(correction_dict_path) or ".", exist_ok=True)
        json.dump({k: v.to_dict() for k, v in result.items()},
                  open(correction_dict_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        log_result(logger, "build_correction_dict_v2",
                   {"entries": len(result), "rows": len(df)})
        return result
    except Exception as e:
        log_error_full(logger, "build_correction_dict_v2", e)
        return {}


def load_correction_dict(path: str) -> dict:
    """تحميل قاموس التصحيح من ملف JSON."""
    if not os.path.exists(path): return {}
    try:
        result = json.loads(open(path, encoding="utf-8").read())
        logger.info("load_correction_dict: %d كلمة من %s", len(result), path)
        return result
    except Exception as e:
        log_error_full(logger, "load_correction_dict", e)
        return {}


def apply_correction_dict(text: str, correction_dict: dict) -> str:
    """تطبيق قاموس التصحيح على نص."""
    if not correction_dict or not text: return text
    words     = text.split()
    corrected = [correction_dict.get(w, w) for w in words]
    changes   = [(w, corrected[i]) for i, w in enumerate(words) if w != corrected[i]]
    if changes:
        logger.debug("apply_correction_dict: %d تعديل: %s", len(changes), changes[:5])
    return " ".join(corrected)


def track_correction_usage(path: str, word: str) -> None:
    """تحديث عداد الاستخدام لقاعدة تصحيح عند تطبيقها."""
    if not word or not os.path.exists(path): return
    try:
        data = json.loads(open(path, encoding="utf-8").read())
        if word in data:
            data[word]["usage_count"] = data[word].get("usage_count", 0) + 1
            data[word]["last_used"]   = datetime.now().isoformat()
            json.dump(data, open(path, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
    except Exception:
        pass


def append_feedback(
    feedback_csv: str,
    image_id: int,
    original: str,
    corrected: str,
    status: str = "verified",
) -> None:
    """تسجيل تصحيح في ملف CSV للتغذية الراجعة."""
    os.makedirs(os.path.dirname(feedback_csv) or ".", exist_ok=True)
    record = {
        "timestamp":      datetime.now().isoformat(),
        "image_id":       image_id,
        "original_text":  original,
        "corrected_text": corrected,
        "status":         status,
    }
    exists = os.path.exists(feedback_csv)
    pd.DataFrame([record]).to_csv(
        feedback_csv, mode="a", header=not exists,
        index=False, encoding="utf-8-sig",
    )
    logger.debug("append_feedback: id=%s '%s'=>'%s'",
                 image_id, original[:30], corrected[:30])
