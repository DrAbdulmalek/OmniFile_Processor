# ══════════════════════════════════════════════════════════╗
#  Automatic Dataset Builder - From Corrected Text to Images
#  Reads corrected text + source images -> produces training dataset
# ══════════════════════════════════════════════════════════╝

import cv2
import json
import numpy as np
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DatasetBuilder:
    """
    محول تلقائي من نص مصحح إلى بيانات تدريب.

    يقرأ ملف النص المصحح والصور الأصلية، يقص الأسطر بدقة،
    ويربط كل قصاصة بصورة بالنص المصحح corresponding.

    صيغة ملف النص المتوقعة:
        --- filename.jpg ---
        سطر نص مصحح 1
        سطر نص مصحح 2
        --- filename2.jpg ---
        سطر نص مصحح 3
        ...
    """

    def __init__(
        self,
        text_file: str,
        images_dir: str,
        output_dir: str,
    ):
        """
        Args:
            text_file: Path to the corrected text file.
            images_dir: Directory containing source page images.
            output_dir: Output directory for the dataset.
        """
        self.text_file = Path(text_file)
        self.images_dir = Path(images_dir)
        self.output_dir = Path(output_dir)
        self.images_out = self.output_dir / 'images'
        self.labels_file = self.output_dir / 'labels.txt'
        self.images_out.mkdir(parents=True, exist_ok=True)

    # ────────────────────────────────────────────────────────
    # Image Cleaning (Scribble Removal)
    # ────────────────────────────────────────────────────────

    @staticmethod
    def clean_scribbles(img_gray: np.ndarray) -> np.ndarray:
        """إزالة الشطب من الصورة."""
        _, binary = cv2.threshold(img_gray, 50, 255, cv2.THRESH_BINARY_INV)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )
        mask = np.ones_like(img_gray) * 255

        for i in range(1, num_labels):
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            area = stats[i, cv2.CC_STAT_AREA]
            fill_ratio = area / max(1, w * h)

            # Hide dense small blocks (scribbles)
            if 100 < area < 5000 and fill_ratio > 0.6:
                cv2.rectangle(mask, (x, y), (x + w, y + h), 0, -1)

        return cv2.bitwise_and(img_gray, img_gray, mask=mask)

    # ────────────────────────────────────────────────────────
    # Line Segmentation
    # ────────────────────────────────────────────────────────

    @staticmethod
    def get_line_crops(img_gray: np.ndarray) -> List[np.ndarray]:
        """
        تقسيم الصورة إلى أسطر مع هامش بسيط.

        Returns:
            List of cropped line images.
        """
        _, thresh = cv2.threshold(
            img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        proj = np.sum(thresh, axis=1)
        lines = []
        in_line, start = False, 0
        thr = np.percentile(proj[proj > 0], 15) if np.any(proj > 0) else 30

        for y in range(len(proj)):
            if proj[y] > thr and not in_line:
                in_line, start = True, y
            elif proj[y] <= thr and in_line:
                in_line = False
                if y - start >= 10:
                    lines.append((start, y))

        if in_line and len(proj) - start >= 10:
            lines.append((start, len(proj)))

        crops = []
        for y1, y2 in lines:
            crops.append(img_gray[max(0, y1 - 5):y2 + 5, :])
        return crops

    # ────────────────────────────────────────────────────────
    # Parse Corrected Text File
    # ────────────────────────────────────────────────────────

    @staticmethod
    def parse_text_file(text_file: Path) -> List[Tuple[str, str]]:
        """
        تحليل ملف النص المصحح إلى (اسم_الصورة, النص).

        Returns:
            List of (image_filename, text_block) tuples.
        """
        if not text_file.exists():
            raise FileNotFoundError(f"Text file not found: {text_file}")

        content = text_file.read_text(encoding='utf-8')

        # Split by page markers: --- filename.jpg ---
        parts = re.split(r'---\s*(.+?\.\w+)\s*---\n', content)

        # parts = [before, img1, text1, img2, text2, ...]
        pages = []
        if len(parts) > 1:
            pages_iter = iter(parts[1:])
            while True:
                try:
                    img_name = next(pages_iter)
                    text_block = next(pages_iter)
                    pages.append((img_name.strip(), text_block.strip()))
                except StopIteration:
                    break
        else:
            # No markers - treat entire file as belonging to first image
            pages.append(("unknown", content.strip()))

        return pages

    # ────────────────────────────────────────────────────────
    # Build Dataset (Main Method)
    # ────────────────────────────────────────────────────────

    def build(self) -> Dict:
        """
        بناء الداتاسيت: قراءة النص المصحح + قص الأسطر من الصور.

        Returns:
            Dict with stats: total_lines, pages_processed, output_dir.
        """
        pages = self.parse_text_file(self.text_file)
        labels_content = []
        total_lines = 0
        pages_processed = 0

        for img_name, text_block in pages:
            # Find image file
            img_path = None
            for ext in ['*.jpg', '*.png', '*.jpeg', '*.bmp', '*.tiff']:
                matches = list(self.images_dir.glob(f"{img_name}.{ext[2:]}"))
                # Also try with the exact name
                exact = self.images_dir / img_name
                if exact.exists():
                    img_path = exact
                    break
                if matches:
                    img_path = matches[0]
                    break

            if img_path is None or not img_path.exists():
                print(f"Warning: Image not found for '{img_name}', skipping.")
                continue

            # Load and clean image
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            clean_img = self.clean_scribbles(img)
            line_crops = self.get_line_crops(clean_img)

            # Split text into lines
            text_lines = [t.strip() for t in text_block.split('\n') if t.strip()]

            # Match (1 line crop = 1 text line)
            count = min(len(line_crops), len(text_lines))

            stem = img_path.stem
            for i in range(count):
                crop = line_crops[i]
                text = text_lines[i]
                new_name = f"{stem}_L{i:03d}.png"
                save_path = self.images_out / new_name

                cv2.imwrite(str(save_path), crop)
                labels_content.append(f"{new_name}\t{text}")
                total_lines += 1

            pages_processed += 1
            print(f"Processed {img_name}: {count} lines")

        # Save labels file
        self.labels_file.write_text('\n'.join(labels_content), encoding='utf-8')

        stats = {
            'total_lines': total_lines,
            'pages_processed': pages_processed,
            'output_dir': str(self.output_dir),
            'labels_file': str(self.labels_file),
            'images_count': len(labels_content),
        }

        print(f"\nDataset built successfully!")
        print(f"  Location: {self.output_dir}")
        print(f"  Total lines: {total_lines}")
        print(f"  Pages: {pages_processed}")

        return stats

    # ────────────────────────────────────────────────────────
    # Build from JSON (from BatchMedicalOCR output)
    # ────────────────────────────────────────────────────────

    def build_from_json(
        self,
        json_file: str,
        corrected_json: Optional[str] = None,
    ) -> Dict:
        """
        بناء الداتاسيت من مخرجات JSON لـ BatchMedicalOCR.

        Args:
            json_file: Path to raw_output.json or final_corrected.json.
            corrected_json: If provided, uses corrected text from this file.

        Returns:
            Stats dict.
        """
        data_file = Path(corrected_json) if corrected_json else Path(json_file)
        if not data_file.exists():
            raise FileNotFoundError(f"JSON file not found: {data_file}")

        data = json.loads(data_file.read_text(encoding='utf-8'))
        labels_content = []
        total_lines = 0

        for page in data:
            page_name = page.get('page', 'unknown')
            for line in page.get('lines', []):
                idx = line.get('idx', 0)
                text = line.get('text', '')
                crop = line.get('crop')

                if not text:
                    continue

                new_name = f"{page_name}_L{idx:03d}.png"
                save_path = self.images_out / new_name

                if crop is not None:
                    # crop might be stored as list (from JSON) or numpy array
                    if isinstance(crop, list):
                        crop = np.array(crop, dtype=np.uint8)
                    if len(crop.shape) == 2:
                        cv2.imwrite(str(save_path), crop)

                labels_content.append(f"{new_name}\t{text}")
                total_lines += 1

        self.labels_file.write_text('\n'.join(labels_content), encoding='utf-8')

        stats = {
            'total_lines': total_lines,
            'output_dir': str(self.output_dir),
            'labels_file': str(self.labels_file),
        }

        print(f"Dataset built from JSON: {total_lines} lines")
        return stats
