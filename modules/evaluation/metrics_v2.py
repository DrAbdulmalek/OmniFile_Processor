"""
HandwrittenOCR - مقاييس الأداء (WER/CER) v4.0
===============================================
- compute_metrics(): حساب WER و CER الحقيقيين
- plot_metrics_fig(): رسم بياني لتحسّن النموذج عبر الزمن
- يتطلب: jiwer
"""

import os
import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger("HandwrittenOCR")


def compute_metrics(db, metrics_log: str = "") -> dict:
    """
    حساب WER و CER (raw_text مقابل predicted_text).

    Parameters:
        db: كائن قاعدة البيانات
        metrics_log: مسار ملف سجل المقاييس

    Returns:
        {wer, cer, samples, timestamp}
    """
    try:
        from jiwer import wer, cer
    except ImportError:
        return {"error": "pip install jiwer"}

    # جلب البيانات الموثقة التي تحتوي raw_text و predicted_text
    words = db.get_verified()
    words = [w for w in words if w.get("status") in ("verified", "sentence_corrected")]

    valid = [
        w for w in words
        if w.get("raw_text", "").strip() and w.get("predicted_text", "").strip()
    ]

    if len(valid) < 5:
        return {"wer": None, "cer": None, "samples": len(valid)}

    refs = [w["raw_text"].strip() for w in valid]
    hyps = [w["predicted_text"].strip() for w in valid]

    m = {
        "wer": round(wer(refs, hyps), 4),
        "cer": round(cer(refs, hyps), 4),
        "samples": len(valid),
        "timestamp": datetime.now().isoformat(),
    }

    # حفظ في السجل
    if metrics_log:
        os.makedirs(os.path.dirname(metrics_log), exist_ok=True)
        mdf = pd.DataFrame([m])
        if os.path.exists(metrics_log):
            mdf.to_csv(
                metrics_log, mode="a",
                header=False, index=False, encoding="utf-8-sig",
            )
        else:
            mdf.to_csv(metrics_log, index=False, encoding="utf-8-sig")

    logger.info(f"WER={m['wer']}, CER={m['cer']}, samples={m['samples']}")
    return m


def plot_metrics_fig(metrics_log: str = ""):
    """
    رسم بياني لتحسّن WER/CER عبر جلسات التدريب.
    Returns: matplotlib Figure أو None
    """
    if not metrics_log or not os.path.exists(metrics_log):
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    df = pd.read_csv(metrics_log, encoding="utf-8-sig")
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(
        df["wer"].dropna().values,
        label="WER", marker="o", color="#E53935",
    )
    ax.plot(
        df["cer"].dropna().values,
        label="CER", marker="s", color="#1E88E5",
    )
    ax.set_title("تحسّن النموذج عبر الزمن (WER/CER)")
    ax.set_xlabel("جلسة التدريب")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


# === Compatibility aliases for OmniFile_v500_Colab ===
def compute_cer(reference: str, hypothesis: str) -> float:
    """CER wrapper — delegates to metrics.calculate_cer."""
    from modules.evaluation.metrics import calculate_cer
    cer, _, _ = calculate_cer(reference, hypothesis)
    return cer

def compute_wer(reference: str, hypothesis: str) -> float:
    """WER wrapper — delegates to metrics.calculate_wer."""
    from modules.evaluation.metrics import calculate_wer
    wer, _, _ = calculate_wer(reference, hypothesis)
    return wer
