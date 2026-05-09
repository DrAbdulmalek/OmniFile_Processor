# review_dashboard.py - Gradio review dashboard v2.0
# ================================================
# الإصلاحات:
# - استيراد CorrectionVoter من المسار الصحيح (tools.voting_tracker)
# - استبدال ArabicSpellCorrector غير الموجود بـ HybridSpellChecker + src.correction
# - توافق كامل مع البنية الحالية للمشروع

import sys
from pathlib import Path

# إضافة الجذر للـ imports
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import gradio as gr
import difflib
from tools.voting_tracker import CorrectionVoter

# استيراد المدقق الإملائي الهجين (البديل الموحد)
try:
    from modules.core.spell_checker import HybridSpellChecker
    _HAS_HYBRID = True
except ImportError:
    _HAS_HYBRID = False

# استيراد correct_text كـ fallback
try:
    from src.correction import correct_text as _correct_text_fallback
    _HAS_CORRECTION = True
except ImportError:
    _HAS_CORRECTION = False


def build_review_dashboard(voter_path="voting_cache.json", model_path=None):
    """
    بناء لوحة مراجعة Gradio للمقارنة بين التصحيح الآلي والأصوات البشرية والإجماع.

    Args:
        voter_path: مسار تخزين أصوات التصويت
        model_path: محجوز للاستخدام المستقبلي (غير مطلوب حالياً)
    """
    voter = CorrectionVoter(storage_path=voter_path)

    # إنشاء المدقق الهجين
    checker = HybridSpellChecker() if _HAS_HYBRID else None

    def _correct_with_fallback(text: str) -> str:
        """تصحيح النص باستخدام HybridSpellChecker أو src.correction."""
        if checker:
            return checker.correct_text(text)
        elif _HAS_CORRECTION:
            return _correct_text_fallback(text)
        return text  # لا يوجد مدقق متاح

    def _highlight_diff(original: str, candidate: str) -> str:
        """تمييز الفروق بين نصين بلون أخضر/أحمر داخل HTML"""
        if not original or not candidate:
            return ""
        diff = difflib.ndiff(original.split(), candidate.split())
        html_parts = []
        for d in diff:
            if d.startswith('- '):
                html_parts.append(f'<span style="background:#fecaca;color:#b91c1c;padding:2px 4px;border-radius:4px">{d[2:]}</span>')
            elif d.startswith('+ '):
                html_parts.append(f'<span style="background:#bbf7d0;color:#15803d;padding:2px 4px;border-radius:4px">{d[2:]}</span>')
            else:
                html_parts.append(d[2:])
        return ' '.join(html_parts)

    def analyze_text(text: str):
        if not text.strip():
            return "", "أدخل نصاً للمقارنة", "", "", ""

        # تصحيح آلي باستخدام الهجين أو src.correction
        ai_corrected = _correct_with_fallback(text)

        # استخراج الإجماع من نظام التصويت
        consensus = voter.get_consensus(text)
        consensus_text = ""
        if consensus:
            agreed_text, agreement_pct = consensus
            consensus_text = f"✅ {agreed_text} (توافق: {agreement_pct:.0%})"
        else:
            consensus_text = "⚠️ لا يوجد إجماع حالياً"

        # جمع أصوات المستخدمين
        norm = voter._normalizer.normalize(text)
        votes_html = "<ul style='margin:0;padding-right:18px;'>"
        if norm in voter.votes:
            for corr, vote_list in voter.votes[norm].items():
                votes_html += f"<li><b>{corr}</b> <span style='color:#64748b'>({len(vote_list)} صوت)</span></li>"
        else:
            votes_html += "<li>لا توجد أصوات سابقة</li>"
        votes_html += "</ul>"

        diff_html = _highlight_diff(text, ai_corrected)
        return ai_corrected, votes_html, consensus_text, diff_html, text

    def approve_correction(ai_out, consensus_text):
        """اعتماد التصحيح الآلي أو الإجماع حسب الاختيار الضمني."""
        if not ai_out or not ai_out.strip():
            return "⚠️ لا يوجد تصحيح لاعتماده"
        chosen = ai_out if consensus_text.startswith("⚠️") else consensus_text.split(" ")[1]
        voter.add_vote(chosen, chosen, voter_id="gradio_curator", confidence=1.0)
        return f"✅ تم اعتماد: {chosen}\n📥 أُضيف كمرجع عالي الثقة في نظام التصويت"

    with gr.Blocks(title="OmniFile Review Dashboard", css="textarea {direction: rtl !important;}") as dashboard:
        gr.Markdown("## 🔍 مقارنة التصحيح: النموذج الآلي vs الأصوات البشرية vs الإجماع")

        with gr.Row():
            with gr.Column(scale=2):
                inp = gr.Textbox(label="📝 نص OCR الأصلي", lines=3, placeholder="الصق النص المستخرج هنا...")
                btn = gr.Button("🔍 تحليل ومقارنة", variant="primary")

            with gr.Column(scale=3):
                with gr.Group():
                    ai_out = gr.Textbox(label="🤖 تصحيح النموذج", interactive=False)
                    human_votes = gr.HTML(label="🗣️ أصوات المستخدمين")
                    consensus = gr.Textbox(label="🎯 الإجماع الحالي", interactive=False)
                    diff_view = gr.HTML(label="🔎 الفرق البصري (أحمر=حذف، أخضر=إضافة)")

        status = gr.Textbox(label="📢 حالة الاعتماد", lines=2)
        approve_btn = gr.Button("✅ اعتماد التصحيح المختار", variant="secondary")

        btn.click(analyze_text, inp, [ai_out, human_votes, consensus, diff_view, status])
        approve_btn.click(approve_correction, [ai_out, consensus], status)

    return dashboard
