# ══════════════════════════════════════════════════════════╗
#  Rejected Lines Manager & Logger - v6.1
#  Intelligent rejection storage | Classification by reason | Review log
# ══════════════════════════════════════════════════════════╝

import json
import datetime
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional


class RejectedLinesManager:
    """
    نظام إدارة الأسطر المرفوضة - يحفظ ويصنف الأسطر التي تم تجاهلها أثناء المعالجة.

    يصنف الأسطر المرفوضة حسب السبب:
    - 'crossed_out': أسطر مشطوبة بخط أفقي
    - 'low_confidence': ثقة منخفضة جداً أو تناقض حرج لم يُحل
    - 'rotation_error': مشاكل دوران/قلب في النص

    الاستراتيجية (Active Learning):
    الأسطر المرفوضة تمثل "حالات صعبة" (Hard Examples) يمكن مراجعتها يدوياً
    وإضافتها إلى بيانات التدريب لتحسين النموذج بشكل مستهدف.
    """

    VALID_REASONS = ('crossed_out', 'low_confidence', 'rotation_error')

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = str(Path(__file__).parent.parent.parent / 'data')

        self.base_dir = Path(base_dir)
        self.rejected_dir = self.base_dir / 'logs' / 'rejected_lines'
        self.rejected_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for each rejection category
        for category in self.VALID_REASONS:
            (self.rejected_dir / category).mkdir(exist_ok=True)

        self.log_file = self.rejected_dir / 'rejected_log.json'
        self.logs: List[Dict] = self._load_log()

    # ────────────────────────────────────────────────────────
    # Log Persistence
    # ────────────────────────────────────────────────────────

    def _load_log(self) -> List[Dict]:
        """تحميل سجل الرفض من الملف."""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_log(self):
        """حفظ سجل الرفض في الملف."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, ensure_ascii=False, indent=2)

    # ────────────────────────────────────────────────────────
    # Core: Save Rejected Line
    # ────────────────────────────────────────────────────────

    def save_rejected(
        self,
        image_crop: np.ndarray,
        reason: str,
        page_id: str,
        line_idx: int,
        context_text: str = "",
    ) -> str:
        """
        حفظ صورة السطر المرفوض وتسجيل السبب.

        Args:
            image_crop: Cropped image of the rejected line.
            reason: Rejection reason - one of 'crossed_out', 'low_confidence', 'rotation_error'.
            page_id: Source page identifier (filename).
            line_idx: Line index on the page.
            context_text: OCR text hint (what the engine read before rejecting).

        Returns:
            Filename of the saved image.

        Raises:
            ValueError: If reason is not a valid category.
        """
        if reason not in self.VALID_REASONS:
            raise ValueError(
                f"Invalid reason '{reason}'. Must be one of: {self.VALID_REASONS}"
            )

        # 1. Save image to categorized subdirectory
        filename = f"{page_id}_L{line_idx:03d}_{reason}.png"
        save_path = self.rejected_dir / reason / filename
        cv2.imwrite(str(save_path), image_crop)

        # 2. Add to log
        entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'page_id': page_id,
            'line_idx': line_idx,
            'reason': reason,
            'image_path': str(save_path),
            'context_hint': context_text,
        }

        self.logs.append(entry)
        self._save_log()

        return filename

    # ────────────────────────────────────────────────────────
    # Batch Save (from pipeline)
    # ────────────────────────────────────────────────────────

    def save_batch_rejected(
        self,
        rejected_lines: List[Dict],
        page_id: str,
    ) -> Dict[str, int]:
        """
        حفظ دفعة من الأسطر المرفوضة.

        Args:
            rejected_lines: List of dicts from segment_lines_v3 or verify_page_v3.
                Each must have: 'reason', 'idx', 'image'.
            page_id: Source page identifier.

        Returns:
            Dict with count per reason: {'crossed_out': N, 'low_confidence': M, ...}
        """
        counts: Dict[str, int] = {}
        for rl in rejected_lines:
            reason = rl.get('reason', 'low_confidence')
            image = rl.get('image')
            idx = rl.get('idx', 0)
            context = rl.get('context_hint', '')

            if image is not None and len(image.shape) >= 2:
                self.save_rejected(
                    image_crop=image,
                    reason=reason,
                    page_id=page_id,
                    line_idx=idx,
                    context_text=context,
                )
                counts[reason] = counts.get(reason, 0) + 1

        return counts

    # ────────────────────────────────────────────────────────
    # Query & Statistics
    # ────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        """إحصائيات الأسطر المرفوضة حسب السبب."""
        stats = {r: 0 for r in self.VALID_REASONS}
        for entry in self.logs:
            reason = entry.get('reason', 'unknown')
            if reason in stats:
                stats[reason] += 1

        stats['total'] = sum(stats.values())
        return stats

    def get_rejected_by_reason(self, reason: str) -> List[Dict]:
        """استرجاع جميع الأسطر المرفوضة بسبب معين."""
        return [e for e in self.logs if e.get('reason') == reason]

    # ────────────────────────────────────────────────────────
    # Recovery: Move rejected to training data
    # ────────────────────────────────────────────────────────

    def recover_for_training(
        self,
        reason: Optional[str] = None,
        target_dir: Optional[str] = None,
        labels_file: Optional[str] = None,
        corrections: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        استرداد أسطر مرفوضة لتصحيحها يدوياً وإضافتها لبيانات التدريب.

        Args:
            reason: Specific reason to recover, or None for all.
            target_dir: Target images directory. Defaults to continuous_data/images.
            labels_file: Target labels file. Defaults to continuous_data/labels.txt.
            corrections: Dict mapping filename -> corrected_text.
                        If provided, only copies files with corrections.

        Returns:
            Number of lines recovered.
        """
        if target_dir is None:
            target_dir = str(self.base_dir / 'continuous_data' / 'images')
        if labels_file is None:
            labels_file = str(self.base_dir / 'continuous_data' / 'labels.txt')

        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        entries = self.logs if reason is None else self.get_rejected_by_reason(reason)
        recovered = 0

        with open(labels_file, 'a', encoding='utf-8') as lf:
            for entry in entries:
                img_path = entry.get('image_path', '')
                if not img_path or not Path(img_path).exists():
                    continue

                # If corrections dict provided, only process entries with corrections
                if corrections is not None:
                    filename = Path(img_path).name
                    if filename not in corrections:
                        continue
                    corrected_text = corrections[filename]
                else:
                    corrected_text = entry.get('context_hint', '[NEEDS_MANUAL_CORRECTION]')

                # Copy image to target
                import shutil
                dest = target_path / Path(img_path).name
                shutil.copy2(img_path, str(dest))

                # Write label
                lf.write(f"{dest.name}\t{corrected_text}\n")
                recovered += 1

        return recovered
