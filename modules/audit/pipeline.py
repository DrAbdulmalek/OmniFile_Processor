# ══════════════════════════════════════════════════════════╗
#  Dual-OCR Verification Pipeline with Audit Logging - v6.0
#  Automated processing | Confidence sorting | Selective review
# ══════════════════════════════════════════════════════════╝

import cv2
from pathlib import Path
from typing import Dict, List, Optional

from modules.vision.dual_ocr_verifier import DualOCRVerifier
from modules.audit.audit_logger import AuditLogger


class DualOCRVerificationPipeline:
    """
    خط المعالجة المتكامل مع التحقق المزدوج وتسجيل التدقيق.

    Workflow:
        1. رفع صفحة جديدة
        2. Dual-OCR Engine يفحص كل سطر (TrOCR + EasyOCR)
        3. مقارنة النتائج
           - التشابه >= threshold + لا تناقض حرج -> حفظ تلقائي
           - التشابه < threshold أو تناقض حرج -> إرسال للمراجعة البشرية
        4. المراجعة البشرية (للأسطر المشبوهة فقط)
        5. تحديث العداد -> عند الحد المطلوب -> إعادة تدريب تلقائي
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        log_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        auto_save_threshold: float = 0.85,
        reviewer_id: str = "DrUser",
    ):
        # Initialize verifier
        self.verifier = DualOCRVerifier(model_path=model_path)

        # Initialize audit logger
        self.verifier.audit_logger = AuditLogger(log_dir=log_dir, reviewer_id=reviewer_id)

        # Output directory for auto-saved training data
        if output_dir is None:
            output_dir = str(Path(__file__).parent.parent.parent / 'data' / 'continuous_data')
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / 'images'
        self.images_dir.mkdir(exist_ok=True, parents=True)
        self.labels_file = self.output_dir / 'labels.txt'
        self.count_file = self.output_dir / 'count.txt'

        self.auto_save_threshold = auto_save_threshold

    # ────────────────────────────────────────────────────────
    # Main Processing
    # ────────────────────────────────────────────────────────

    def process_page(self, file_path: str) -> Dict:
        """
        معالجة صفحة كاملة مع التحقق المزدوج وتسجيل التدقيق.

        - التشابه >= threshold: حفظ تلقائي
        - التشابه < threshold أو تناقض حرج: إرسال للمراجعة البشرية

        Returns:
            Dict with stats: total_lines, auto_saved, manual_review_needed, critical_alerts, auto_save_rate
        """
        img = cv2.imread(file_path)
        if img is None:
            return {"error": "Failed to read image"}

        lines = self.verifier.extract_lines(img)
        page_id = Path(file_path).name

        auto_saved = 0
        manual_review: List[Dict] = []
        critical_alerts: List[Dict] = []

        stats = {"total": len(lines), "auto": 0, "manual": 0, "critical": 0}

        for i, (y1, y2) in enumerate(lines):
            line_img = img[y1:y2]
            result = self.verifier.verify_line(line_img, i)

            # ─── Log the decision ───
            action = (
                "AUTO_ACCEPT"
                if result['recommendation'] == 'AUTO_ACCEPT'
                else "PENDING_REVIEW"
            )

            self.verifier.audit_logger.log_decision(
                page_id=page_id,
                line_idx=i,
                trocr_text=result['trocr_text'],
                easyocr_text=result['easyocr_text'],
                similarity=result['similarity'],
                recommendation=result['recommendation'],
                critical_alerts=result['critical_warnings'],
                final_text=result['final_text'] or "",
                action=action,
                confidence=result['confidence'],
                model_version=self.verifier.model_version,
            )

            # ─── Save or queue for review ───
            if result['recommendation'] == 'AUTO_ACCEPT':
                fn = f"auto_L{i:03d}.png"
                cv2.imwrite(str(self.images_dir / fn), line_img)
                with open(self.labels_file, 'a', encoding='utf-8') as f:
                    f.write(f"{fn}\t{result['final_text']}\n")
                auto_saved += 1
                stats["auto"] += 1
            else:
                manual_review.append(result)
                stats["manual"] += 1
                if result['has_critical_mismatch']:
                    stats["critical"] += 1
                    critical_alerts.append({
                        'line': i,
                        'warnings': result['critical_warnings'],
                        'trocr': result['trocr_text'],
                        'easyocr': result['easyocr_text'],
                    })

        # ─── Update counter ───
        current_count = 0
        if self.count_file.exists():
            try:
                current_count = int(self.count_file.read_text().strip())
            except (ValueError, IOError):
                pass
        self.count_file.write_text(str(current_count + auto_saved))

        return {
            'total_lines': len(lines),
            'auto_saved': auto_saved,
            'manual_review_needed': len(manual_review),
            'critical_alerts': critical_alerts,
            'auto_save_rate': auto_saved / len(lines) if lines else 0,
            'manual_review_results': manual_review,
            'stats': stats,
        }

    # ────────────────────────────────────────────────────────
    # Manual Review Actions (logged to audit)
    # ────────────────────────────────────────────────────────

    def log_user_action(self, result: Dict, action_type: str, final_text: str) -> str:
        """
        تسجيل قرار المستخدم يدوياً عند المراجعة.

        Args:
            result: The verification result dict for the line being reviewed.
            action_type: USER_CONFIRM, USER_OVERRIDE, or USER_CORRECT.
            final_text: The final accepted text after user action.

        Returns:
            Confirmation message string.
        """
        if not result:
            return "No current line data"

        self.verifier.audit_logger.log_decision(
            page_id="manual_review_session",
            line_idx=result['line_idx'],
            trocr_text=result['trocr_text'],
            easyocr_text=result['easyocr_text'],
            similarity=result['similarity'],
            recommendation=result['recommendation'],
            critical_alerts=result['critical_warnings'],
            final_text=final_text,
            action=action_type,
            confidence=result['confidence'],
            model_version=self.verifier.model_version,
        )

        # Also save corrected data for continuous learning
        fn = f"manual_L{result['line_idx']:03d}.png"
        cv2.imwrite(str(self.images_dir / fn), result['image'])
        with open(self.labels_file, 'a', encoding='utf-8') as f:
            f.write(f"{fn}\t{final_text}\n")

        return f"Decision logged: {action_type} | Text: {final_text[:40]}..."

    # ────────────────────────────────────────────────────────
    # Get Counter
    # ────────────────────────────────────────────────────────

    def get_auto_saved_count(self) -> int:
        """قراءة عدد الأسطر المحفوظة تلقائياً."""
        if self.count_file.exists():
            try:
                return int(self.count_file.read_text().strip())
            except (ValueError, IOError):
                pass
        return 0
