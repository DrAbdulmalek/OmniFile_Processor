# ══════════════════════════════════════════════════════════╗
#  Audit Report & Analytics Dashboard Generator - v6.0
#  Transforms JSONL audit log into actionable Markdown reports
# ══════════════════════════════════════════════════════════╝

import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional


class AuditReportGenerator:
    """
    مولّد تقارير التدقيق والأداء - يحول سجل JSONL إلى تقارير Markdown
    تتضمن مؤشرات KPIs وتوصيات تحسين النظام.
    """

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            log_dir = str(Path(__file__).parent.parent.parent / 'data' / 'audit_logs')

        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "audit_log.jsonl"

    # ────────────────────────────────────────────────────────
    # Load Data
    # ────────────────────────────────────────────────────────

    def load_logs(self) -> List[Dict]:
        """تحميل جميع السجلات من ملف JSONL."""
        if not self.log_file.exists():
            return []

        logs = []
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        return logs

    # ────────────────────────────────────────────────────────
    # Generate Markdown Report
    # ────────────────────────────────────────────────────────

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """
        إنشاء تقرير أداء ومراجعة التدقيق الطبي بصيغة Markdown.

        Args:
            output_path: Path to save the report. If None, saves in log_dir.

        Returns:
            The full report text as string.
        """
        logs = self.load_logs()

        if not logs:
            return "No audit records found. Process some pages first."

        if output_path is None:
            output_path = str(self.log_dir / "audit_report.md")

        # ─── Compute Metrics ───
        total = len(logs)
        auto_count = sum(1 for l in logs if l.get('action') == 'AUTO_ACCEPT')
        auto_rate = (auto_count / total) * 100
        manual_rate = 100 - auto_rate
        critical_count = sum(1 for l in logs if len(l.get('critical_alerts', [])) > 0)
        critical_rate = (critical_count / total) * 100

        model_versions = {}
        for l in logs:
            v = l.get('model_version', 'unknown')
            model_versions[v] = model_versions.get(v, 0) + 1

        action_dist: Dict[str, int] = {}
        for l in logs:
            act = l.get('action', 'UNKNOWN')
            action_dist[act] = action_dist.get(act, 0) + 1

        # ─── Build Report ───
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        report_lines = [
            f"# Audit Report & Performance Dashboard",
            f"**Date**: {now_str}  ",
            f"**Total Decisions Logged**: {total}  ",
            "",
            "## Key Performance Indicators (KPIs)",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Auto-Accept Rate | {auto_rate:.1f}% |",
            f"| Manual Review Rate | {manual_rate:.1f}% |",
            f"| Critical Alert Rate | {critical_rate:.1f}% |",
            f"| Model Versions Used | {', '.join(model_versions.keys())} |",
            "",
            "## Action Distribution",
            "",
        ]

        for k, v in action_dist.items():
            report_lines.append(f"- **{k}**: {v} ({v / total * 100:.1f}%)")

        report_lines.extend([
            "",
            "## Last 10 Decisions",
            "",
            "| Time | Page | Line | Action | Confidence | Reason |",
            "|------|------|------|--------|------------|--------|",
        ])

        for entry in logs[-10:]:
            ts = entry.get('timestamp', '')[:16]
            page = entry.get('page_id', '')[:15]
            line = entry.get('line_idx', '')
            action = entry.get('action', '')
            conf = entry.get('confidence', '')
            reason = entry.get('decision_reason', '')[:40] + ("..." if len(entry.get('decision_reason', '')) > 40 else "")
            report_lines.append(f"| {ts} | {page} | {line} | {action} | {conf} | {reason} |")

        report_lines.extend([
            "",
            "## Recommendations",
            "",
        ])

        # ─── System Recommendations ───
        if auto_rate < 60:
            report_lines.append(
                "- LOW auto-accept rate. Consider collecting 50+ manually corrected lines and retraining."
            )
        if critical_rate > 15:
            report_lines.append(
                "- HIGH critical alert rate. Review `protected_terms.json` and verify dosage accuracy."
            )
        if manual_rate > 50:
            report_lines.append(
                "- HIGH manual workload. Consider adjusting `auto_save_threshold` or improving scan quality."
            )
        if auto_rate >= 80 and critical_rate < 5:
            report_lines.append(
                "- System is stable and efficient. Ready for routine clinical use with periodic weekly review."
            )

        report_text = "\n".join(report_lines)

        # ─── Save Report ───
        Path(output_path).parent.mkdir(exist_ok=True, parents=True)
        Path(output_path).write_text(report_text, encoding='utf-8')
        print(f"Report saved: {output_path}")

        return report_text

    # ────────────────────────────────────────────────────────
    # Summary Stats (for programmatic use)
    # ────────────────────────────────────────────────────────

    def get_summary(self) -> Dict:
        """إرجاع ملخص إحصائي قصير (للاستخدام البرمجي)."""
        logs = self.load_logs()
        if not logs:
            return {"total": 0, "auto_rate": 0, "critical_rate": 0}

        total = len(logs)
        auto = sum(1 for l in logs if l.get('action') == 'AUTO_ACCEPT')
        critical = sum(1 for l in logs if len(l.get('critical_alerts', [])) > 0)

        return {
            "total": total,
            "auto_rate": round((auto / total) * 100, 1),
            "critical_rate": round((critical / total) * 100, 1),
            "last_entry": logs[-1].get('timestamp', '') if logs else None,
        }
