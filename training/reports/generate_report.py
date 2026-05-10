#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_report.py
==================

توليد تقارير تلقائية للتدريب.

صيغ مدعومة:
- PDF (للطباعة والمشاركة)
- HTML (تفاعلي)
- Markdown (للـ GitHub)
- JSON (للـ API)

المؤلف: Dr. Abdulmalek Al-husseini
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


@dataclass
class TrainingReport:
    """بيانات تقرير التدريب."""
    job_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime]
    config: Dict
    metrics: Dict
    samples: List[Dict]
    error_analysis: Optional[Dict] = None


class ReportGenerator:
    """مولد التقارير."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, report: TrainingReport):
        """توليد جميع الصيغ."""
        paths = {
            'pdf': self.generate_pdf(report),
            'html': self.generate_html(report),
            'markdown': self.generate_markdown(report),
            'json': self.generate_json(report)
        }
        return paths

    def generate_pdf(self, report: TrainingReport) -> Path:
        """توليد تقرير PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
                Table, TableStyle, PageBreak
            )
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            raise ImportError("ثبّت: pip install reportlab")

        # تسجيل خط عربي
        try:
            pdfmetrics.registerFont(TTFont('Arabic', 'fonts/Amiri-Regular.ttf'))
            arabic_style = ParagraphStyle(
                'Arabic',
                fontName='Arabic',
                fontSize=12,
                leading=16,
                alignment=2  # RTL
            )
        except:
            arabic_style = getSampleStyleSheet()['Normal']

        # إنشاء الملف
        output_path = self.output_dir / f"report_{report.job_id}.pdf"
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        # المحتوى
        story = []
        styles = getSampleStyleSheet()

        # عنوان
        story.append(Paragraph(f"تقرير التدريب: {report.name}", styles['Title']))
        story.append(Spacer(1, 0.5*cm))

        # معلومات عامة
        story.append(Paragraph("معلومات عامة", styles['Heading2']))
        info_data = [
            ['المعرف', report.job_id],
            ['تاريخ البدء', report.start_time.strftime('%Y-%m-%d %H:%M')],
            ['تاريخ الانتهاء', report.end_time.strftime('%Y-%m-%d %H:%M') if report.end_time else 'قيد التشغيل'],
            ['الحالة', 'مكتمل' if report.end_time else 'جاري'],
        ]
        info_table = Table(info_data, colWidths=[6*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))

        # المقاييس
        if report.metrics:
            story.append(Paragraph("المقاييس النهائية", styles['Heading2']))
            metrics_data = [
                ['المقياس', 'القيمة'],
                ['CER', f"{report.metrics.get('cer', 0)*100:.2f}%"],
                ['WER', f"{report.metrics.get('wer', 0)*100:.2f}%"],
                ['Accuracy', f"{report.metrics.get('accuracy', 0)*100:.2f}%"],
            ]
            metrics_table = Table(metrics_data, colWidths=[8*cm, 8*cm])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(metrics_table)
            story.append(Spacer(1, 0.5*cm))

        # الرسوم البيانية
        chart_path = self._generate_charts(report)
        if chart_path:
            story.append(PageBreak())
            story.append(Paragraph("الرسوم البيانية", styles['Heading2']))
            story.append(RLImage(str(chart_path), width=16*cm, height=10*cm))

        # بناء PDF
        doc.build(story)

        return output_path

    def generate_html(self, report: TrainingReport) -> Path:
        """توليد تقرير HTML تفاعلي."""
        output_path = self.output_dir / f"report_{report.job_id}.html"

        # توليد الرسوم
        chart_path = self._generate_charts(report)
        chart_base64 = self._image_to_base64(chart_path) if chart_path else ''

        # نماذج HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تقرير التدريب: {report.name}</title>
    <style>
        :root {{
            --primary: #1976D2;
            --success: #4CAF50;
            --warning: #FF9800;
            --danger: #f44336;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: linear-gradient(135deg, var(--primary), #1565C0);
            color: white;
            padding: 40px 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .subtitle {{
            opacity: 0.9;
            font-size: 1.1em;
        }}

        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .metric-card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }}

        .metric-card:hover {{
            transform: translateY(-4px);
        }}

        .metric-value {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }}

        .metric-value.cer {{ color: var(--danger); }}
        .metric-value.wer {{ color: var(--warning); }}
        .metric-value.accuracy {{ color: var(--success); }}

        .metric-label {{
            color: #666;
            font-size: 0.9em;
        }}

        .chart-container {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }}

        .chart-container img {{
            width: 100%;
            height: auto;
            border-radius: 8px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        th, td {{
            padding: 12px;
            text-align: right;
            border-bottom: 1px solid #eee;
        }}

        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }}

        .status-completed {{
            background: #E8F5E9;
            color: #2E7D32;
        }}

        .status-running {{
            background: #E3F2FD;
            color: #1565C0;
        }}

        .config-section {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 16px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
        }}

        @media print {{
            body {{
                background: white;
            }}
            .card {{
                box-shadow: none;
                border: 1px solid #eee;
            }}
        }}

        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 تقرير التدريب</h1>
            <p class="subtitle">{report.name}</p>
            <p class="subtitle">المعرف: {report.job_id}</p>
        </header>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Character Error Rate</div>
                <div class="metric-value cer">
                    {report.metrics.get('cer', 0)*100:.2f}%
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Word Error Rate</div>
                <div class="metric-value wer">
                    {report.metrics.get('wer', 0)*100:.2f}%
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Accuracy</div>
                <div class="metric-value accuracy">
                    {report.metrics.get('accuracy', 0)*100:.2f}%
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📈 رسم بياني للتدريب</h2>
            <div class="chart-container">
                <img src="data:image/png;base64,{chart_base64}" alt="Training Chart">
            </div>
        </div>

        <div class="card">
            <h2>⚙️ الإعدادات</h2>
            <div class="config-section">
                <pre>{json.dumps(report.config, indent=2, ensure_ascii=False)}</pre>
            </div>
        </div>

        <div class="card">
            <h2>📝 معلومات إضافية</h2>
            <table>
                <tr>
                    <th>الحالة</th>
                    <td>
                        <span class="status-badge {'status-completed' if report.end_time else 'status-running'}">
                            {'مكتمل' if report.end_time else 'قيد التشغيل'}
                        </span>
                    </td>
                </tr>
                <tr>
                    <th>تاريخ البدء</th>
                    <td>{report.start_time.strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
                <tr>
                    <th>تاريخ الانتهاء</th>
                    <td>{report.end_time.strftime('%Y-%m-%d %H:%M:%S') if report.end_time else '-'}</td>
                </tr>
                <tr>
                    <th>المدة</th>
                    <td>
                        {str(report.end_time - report.start_time).split('.')[0] if report.end_time else '-'}
                    </td>
                </tr>
            </table>
        </div>
    </div>

    <script>
        // تفاعلية بسيطة
        document.querySelectorAll('.metric-card').forEach(card => {{
            card.addEventListener('click', () => {{
                card.style.transform = 'scale(0.95)';
                setTimeout(() => card.style.transform = '', 150);
            }});
        }});
    </script>
</body>
</html>
        """

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return output_path

    def generate_markdown(self, report: TrainingReport) -> Path:
        """توليد تقرير Markdown."""
        output_path = self.output_dir / f"report_{report.job_id}.md"

        md_content = f"""# 📊 تقرير التدريب: {report.name}

## معلومات عامة

| البيان | القيمة |
|--------|--------|
| المعرف | `{report.job_id}` |
| الحالة | {'✅ مكتمل' if report.end_time else '🔄 قيد التشغيل'} |
| البدء | {report.start_time.strftime('%Y-%m-%d %H:%M')} |
| الانتهاء | {report.end_time.strftime('%Y-%m-%d %H:%M') if report.end_time else '-'} |

## المقاييس

| المقياس | القيمة | التقييم |
|---------|--------|---------|
| CER | {report.metrics.get('cer', 0)*100:.2f}% | {'🟢 جيد' if report.metrics.get('cer', 1) < 0.1 else '🟡 مقبول' if report.metrics.get('cer', 1) < 0.2 else '🔴 يحتاج تحسين'} |
| WER | {report.metrics.get('wer', 0)*100:.2f}% | {'🟢 جيد' if report.metrics.get('wer', 1) < 0.15 else '🟡 مقبول' if report.metrics.get('wer', 1) < 0.3 else '🔴 يحتاج تحسين'} |
| Accuracy | {report.metrics.get('accuracy', 0)*100:.2f}% | {'🟢 ممتاز' if report.metrics.get('accuracy', 0) > 0.95 else '🟡 جيد' if report.metrics.get('accuracy', 0) > 0.9 else '🔴 يحتاج تحسين'} |

## الإعدادات

```json
{json.dumps(report.config, indent=2, ensure_ascii=False)}
```

## ملاحظات

- تم إنشاء هذا التقرير تلقائياً
- للاستفسارات: [GitHub Issues](https://github.com/DrAbdulmalek/OmniFile_Processor/issues)

---

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return output_path

    def generate_json(self, report: TrainingReport) -> Path:
        """توليد تقرير JSON (للـ API)."""
        output_path = self.output_dir / f"report_{report.job_id}.json"

        data = {
            'job_id': report.job_id,
            'name': report.name,
            'metadata': {
                'start_time': report.start_time.isoformat(),
                'end_time': report.end_time.isoformat() if report.end_time else None,
                'status': 'completed' if report.end_time else 'running'
            },
            'config': report.config,
            'metrics': report.metrics,
            'error_analysis': report.error_analysis,
            'generated_at': datetime.now().isoformat()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path

    def _generate_charts(self, report: TrainingReport) -> Optional[Path]:
        """توليد الرسوم البيانية."""
        if not report.metrics.get('history'):
            return None

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f'Training Report: {report.name}', fontsize=16)

        history = report.metrics['history']
        epochs = [h['epoch'] for h in history]

        # Loss
        ax = axes[0, 0]
        ax.plot(epochs, [h['loss'] for h in history], 'b-', label='Loss')
        ax.set_xlabel('Epoch')
        ax.set_ylabel('Loss')
        ax.set_title('Training Loss')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # CER
        ax = axes[0, 1]
        ax.plot(epochs, [h['cer'] for h in history], 'r-', label='CER')
        ax.set_xlabel('Epoch')
        ax.set_ylabel('CER')
        ax.set_title('Character Error Rate')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # WER
        ax = axes[1, 0]
        ax.plot(epochs, [h['wer'] for h in history], 'g-', label='WER')
        ax.set_xlabel('Epoch')
        ax.set_ylabel('WER')
        ax.set_title('Word Error Rate')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Learning Rate
        if 'learning_rate' in history[0]:
            ax = axes[1, 1]
            ax.plot(epochs, [h['learning_rate'] for h in history], 'm-', label='LR')
            ax.set_xlabel('Epoch')
            ax.set_ylabel('Learning Rate')
            ax.set_title('Learning Rate Schedule')
            ax.set_yscale('log')
            ax.legend()
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        chart_path = self.output_dir / f"charts_{report.job_id}.png"
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        plt.close()

        return chart_path

    def _image_to_base64(self, image_path: Path) -> str:
        """تحويل صورة لـ base64."""
        import base64

        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode()


# =============================================================================

def create_training_report(
    job_id: str,
    checkpoint_path: Path,
    output_dir: Path = Path("./reports")
) -> Dict[str, Path]:
    """
    إنشاء تقرير كامل للتدريب.

    Args:
        job_id: معرف المهمة
        checkpoint_path: مسار checkpoint
        output_dir: مجلد الإخراج

    Returns:
        مسارات التقارير المُنشأة
    """
    # قراءة البيانات
    config_path = checkpoint_path / 'config.json'
    metrics_path = checkpoint_path / 'metrics.json'

    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}

    # إنشاء التقرير
    report = TrainingReport(
        job_id=job_id,
        name=config.get('name', 'Untitled'),
        start_time=datetime.fromisoformat(config.get('start_time', datetime.now().isoformat())),
        end_time=datetime.fromisoformat(config.get('end_time')) if config.get('end_time') else None,
        config=config,
        metrics=metrics,
        samples=[]
    )

    # توليد
    generator = ReportGenerator(output_dir)
    return generator.generate_all(report)

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_report.py <checkpoint_dir> [output_dir]")
        sys.exit(1)

    checkpoint = Path(sys.argv[1])
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("./reports")

    reports = create_training_report(
        job_id=checkpoint.name,
        checkpoint_path=checkpoint,
        output_dir=output
    )

    print("✅ تم إنشاء التقارير:")
    for fmt, path in reports.items():
        print(f"  {fmt}: {path}")
