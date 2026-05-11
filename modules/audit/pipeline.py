# ══════════════════════════════════════════════════════════╗
#  Dual-OCR Verification Pipeline with Audit Logging - v6.1
#  v6.1: Integrated v3.1 preprocessing, rejected lines manager,
#        reference extraction, strike-through detection
# ══════════════════════════════════════════════════════════╝

import cv2
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from modules.vision.dual_ocr_verifier import DualOCRVerifier
from modules.audit.audit_logger import AuditLogger
from modules.audit.rejected_lines_manager import RejectedLinesManager


class DualOCRVerificationPipeline:
    """
    خط المعالجة المتكامل مع التحقق المزدوج وتسجيل التدقيق.

    v6.1 Workflow:
        1. رفع صفحة جديدة
        2. preprocess_for_ocr_v3: تصحيح دوران، إزالة خطوط دفتر، فلترة ذكية
        3. segment_lines_v3: تقسيم مع كشف المشطوب
        4. Dual-OCR Engine يفحص كل سطر (TrOCR + EasyOCR)
        5. extract_references_v3: عزل المراجع من النص
        6. مقارنة النتائج:
           - تشابه >= threshold + لا تناقض حرج -> حفظ تلقائي
           - مشطوب -> حفظ في rejected_lines
           - ثقة منخفضة -> حفظ في rejected_lines + إرسال للمراجعة
        7. المراجعة البشرية (للأسطر المشبوهة فقط)
        8. تحديث العداد -> عند الحد المطلوب -> إعادة تدريب تلقائي
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        log_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        auto_save_threshold: float = 0.85,
        reviewer_id: str = "DrUser",
        use_v3: bool = True,
    ):
        """
        Args:
            model_path: Path to trained TrOCR model or None for default.
            log_dir: Directory for audit logs.
            output_dir: Directory for auto-saved training data.
            auto_save_threshold: Similarity threshold for auto-accept (default 0.85).
            reviewer_id: Identifier of the human reviewer.
            use_v3: If True, uses v3.1 preprocessing/segmentation (default True).
        """
        # Initialize verifier
        self.verifier = DualOCRVerifier(model_path=model_path)

        # Initialize audit logger
        self.verifier.audit_logger = AuditLogger(log_dir=log_dir, reviewer_id=reviewer_id)

        # Initialize rejected lines manager
        if log_dir is None:
            log_dir = str(Path(__file__).parent.parent.parent / 'data' / 'audit_logs')
        self.rejected_manager = RejectedLinesManager(base_dir=str(Path(log_dir).parent))

        # Output directory for auto-saved training data
        if output_dir is None:
            output_dir = str(Path(__file__).parent.parent.parent / 'data' / 'continuous_data')
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / 'images'
        self.images_dir.mkdir(exist_ok=True, parents=True)
        self.labels_file = self.output_dir / 'labels.txt'
        self.count_file = self.output_dir / 'count.txt'

        self.auto_save_threshold = auto_save_threshold
        self.use_v3 = use_v3

    # ────────────────────────────────────────────────────────
    # Main Processing (v6.1 - Full Pipeline)
    # ────────────────────────────────────────────────────────

    def process_page(self, file_path: str) -> Dict:
        """
        معالجة صفحة كاملة مع التحقق المزدوج وتسجيل التدقيق (v6.1).

        Uses v3.1 preprocessing, segmentation, reference extraction,
        and rejected lines management.

        Returns:
            Dict with stats: total_lines, auto_saved, manual_review_needed,
            critical_alerts, rejected_counts, auto_save_rate
        """
        img = cv2.imread(file_path)
        if img is None:
            return {"error": "Failed to read image"}

        page_id = Path(file_path).name
        auto_saved = 0
        manual_review: List[Dict] = []
        critical_alerts: List[Dict] = []

        stats = {
            "total": 0, "auto": 0, "manual": 0,
            "critical": 0, "crossed_out": 0, "rejected": 0,
        }

        if self.use_v3:
            # ─── v3.1 Pipeline ───
            # verify_page_v3 handles: preprocessing, segmentation, strike-through,
            # and returns (results, rejected)
            results, rejected_lines = self.verifier.verify_page_v3(img)

            # Save rejected lines (crossed-out, etc.)
            for rl in rejected_lines:
                reason = rl.get('reason', 'low_confidence')
                self.rejected_manager.save_rejected(
                    image_crop=rl['image'],
                    reason=reason,
                    page_id=page_id,
                    line_idx=rl['idx'],
                    context_text="[Crossed-Out Line]" if reason == 'crossed_out' else "",
                )
                stats['crossed_out'] += 1

            verification_results = results
        else:
            # ─── Legacy v1 Pipeline ───
            lines = self.verifier.extract_lines(img)
            verification_results = []
            for i, (y1, y2) in enumerate(lines):
                line_img = img[y1:y2]
                result = self.verifier.verify_line(line_img, i, use_v3=False)
                verification_results.append(result)

        stats['total'] = len(verification_results) + stats.get('crossed_out', 0)

        for result in verification_results:
            i = result['line_idx']

            # ─── Log the decision ───
            if result['recommendation'] == 'AUTO_ACCEPT':
                action = "AUTO_ACCEPT"
            elif result['confidence'] == 'LOW':
                action = "PENDING_REVIEW"
            else:
                action = "PENDING_REVIEW"

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

            # ─── Route based on recommendation ───
            if result['recommendation'] == 'AUTO_ACCEPT':
                # Save cleaned text (references already extracted)
                final_text = result['final_text'] or result.get('trocr_clean', '')
                fn = f"auto_L{i:03d}.png"
                line_img = result.get('image')
                if line_img is not None and len(line_img.shape) >= 2:
                    cv2.imwrite(str(self.images_dir / fn), line_img)
                with open(self.labels_file, 'a', encoding='utf-8') as f:
                    f.write(f"{fn}\t{final_text}\n")
                auto_saved += 1
                stats["auto"] += 1

            elif result['confidence'] == 'LOW':
                # Reject: very low confidence or unresolved critical mismatch
                self.rejected_manager.save_rejected(
                    image_crop=result.get('image', result['image']),
                    reason='low_confidence',
                    page_id=page_id,
                    line_idx=i,
                    context_text=f"TrOCR: {result['trocr_text']} | EasyOCR: {result['easyocr_text']}",
                )
                stats["rejected"] += 1
                stats["manual"] += 1
                if result['has_critical_mismatch']:
                    stats["critical"] += 1
                    critical_alerts.append({
                        'line': i,
                        'warnings': result['critical_warnings'],
                        'trocr': result['trocr_text'],
                        'easyocr': result['easyocr_text'],
                    })
                manual_review.append(result)

            else:
                # QUICK_CHECK: needs human review but not rejected
                manual_review.append(result)
                stats["manual"] += 1

        # ─── Update counter ───
        current_count = 0
        if self.count_file.exists():
            try:
                current_count = int(self.count_file.read_text().strip())
            except (ValueError, IOError):
                pass
        self.count_file.write_text(str(current_count + auto_saved))

        return {
            'total_lines': stats['total'],
            'auto_saved': auto_saved,
            'manual_review_needed': len(manual_review),
            'critical_alerts': critical_alerts,
            'auto_save_rate': auto_saved / max(1, stats['total'] - stats.get('crossed_out', 0)),
            'rejected_counts': self.rejected_manager.get_stats(),
            'manual_review_results': manual_review,
            'stats': stats,
        }

    # ────────────────────────────────────────────────────────
    # Process with Rotation Error Detection
    # ────────────────────────────────────────────────────────

    def process_page_with_rotation_check(self, file_path: str) -> Dict:
        """
        معالجة مع كشف أخطاء الدوران الإضافية.

        مثل process_page لكنه يفحص أيضاً أسطر الهيدر المقلوبة
        ويحفظها في rejected_lines/rotation_error.
        """
        img = cv2.imread(file_path)
        if img is None:
            return {"error": "Failed to read image"}

        page_id = Path(file_path).name

        # Check header for rotation issues
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h = gray.shape[0]
        header_region = gray[0:int(h * 0.15), :]
        _, bin_h = cv2.threshold(header_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = []
        if np.any(bin_h > 0):
            coords = np.column_stack(np.where(bin_h > 0))

        has_rotation_issue = False
        if len(coords) > 50:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            if abs(angle) > 150:
                has_rotation_issue = True
                # Save header as rotation error for review
                self.rejected_manager.save_rejected(
                    image_crop=header_region,
                    reason='rotation_error',
                    page_id=page_id,
                    line_idx=-1,  # -1 indicates header
                    context_text="[Inverted header detected]",
                )

        # Process normally (v3.1 handles rotation internally)
        result = self.process_page(file_path)
        result['has_rotation_issue'] = has_rotation_issue
        return result

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
        img_data = result.get('image')
        if img_data is not None and len(img_data.shape) >= 2:
            cv2.imwrite(str(self.images_dir / fn), img_data)
        with open(self.labels_file, 'a', encoding='utf-8') as f:
            f.write(f"{fn}\t{final_text}\n")

        return f"Decision logged: {action_type} | Text: {final_text[:40]}..."

    # ────────────────────────────────────────────────────────
    # Recovery: Recover rejected lines for retraining
    # ────────────────────────────────────────────────────────

    def recover_rejected_for_training(
        self,
        corrections: Optional[Dict[str, str]] = None,
        reason: Optional[str] = None,
    ) -> int:
        """
        استرداد أسطر مرفوضة مصححة يدوياً وإضافتها لبيانات التدريب.

        Args:
            corrections: Dict mapping filename -> corrected_text.
                        If None, all rejected lines are recovered (need manual correction later).
            reason: Specific reason to recover, or None for all.

        Returns:
            Number of lines recovered.
        """
        return self.rejected_manager.recover_for_training(
            reason=reason,
            target_dir=str(self.images_dir),
            labels_file=str(self.labels_file),
            corrections=corrections,
        )

    # ────────────────────────────────────────────────────────
    # Get Counters
    # ────────────────────────────────────────────────────────

    def get_auto_saved_count(self) -> int:
        """قراءة عدد الأسطر المحفوظة تلقائياً."""
        if self.count_file.exists():
            try:
                return int(self.count_file.read_text().strip())
            except (ValueError, IOError):
                pass
        return 0

    def get_rejected_stats(self) -> Dict:
        """إحصائيات الأسطر المرفوضة."""
        return self.rejected_manager.get_stats()
