# review_dashboard.py - Gradio review dashboard

import gradio as gr
import difflib
from core.voting_tracker import CorrectionVoter
from models.inference_corrector import ArabicSpellCorrector

def build_review_dashboard(voter_path="voting_cache.json", model_path="qwen2.5-0.5b-ar-corrector"):
    voter = CorrectionVoter(storage_path=voter_path)
    corrector = ArabicSpellCorrector(model_path)

    def _highlight_diff(original: str, candidate: str) -> str:
        """تمييز الفروق بين نصين بلون أخضر/أحمر داخل HTML"""
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

        ai_corrected = corrector.correct(text, fallback_to_voting=True, voter=voter)
        consensus = voter.get_consensus(text)
        consensus_text = f"✅ {consensus[0]} (توافق: {consensus[1]:.0%})" if consensus else "⚠️ لا يوجد إجماع حالياً"

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
        # اعتماد التصحيح الآلي أو الإجماع حسب الاختيار الضمني
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
