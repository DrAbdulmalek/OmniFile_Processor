"""
Advanced Medical OCR Reviewer — محسن لمعالجة الملاحظات الطبية بخط اليد
يدعم: حماية مصطلحات طبية، عزل أرقام مرجعية، دعم نصوص كثيفة، تصدير بيانات التدريب
"""
import cv2
import numpy as np
import os
import re
import json
import zipfile
from pathlib import Path
from PIL import Image
from typing import List, Dict, Optional, Tuple


class AdvancedMedicalOCR:
    """محرك معالجة متقدم للملاحظات الطبية بخط اليد العربي/الإنجليزي"""

    def __init__(self):
        self.reader = None
        self.dataset = []
        self.current_idx = 0
        self.lines_data = []

        # قائمة حماية المصطلحات الطبية
        self.medical_terms = [
            'CAFFEY', 'ESR', 'CRP', 'AIDS', 'Goucher', 'cranial', 'vault',
            'Flucloxacillin', 'Ciprofloxacin', 'HIV', 'MRI', 'CT', 'X-ray',
            'BID', 'TID', 'PO', 'IV', 'IM', 'mg', 'ml', 'kg',
            'osteomyelitis', 'septic', 'arthritis', 'effusion', 'synovial',
            'CBC', 'WBC', 'RBC', 'HGB', 'PLT', 'BMP', 'LFT',
            'Na', 'K', 'Cl', 'CO2', 'BUN', 'Cr', 'Glu',
            'Ca', 'Mg', 'Phos', 'Albumin', 'Alk Phos', 'AST', 'ALT',
            'Bilirubin', 'INR', 'PT', 'PTT', 'aPTT',
            'Amoxicillin', 'Augmentin', 'Azithromycin', 'Ceftriaxone',
            'Vancomycin', 'Gentamicin', 'Metronidazole', 'Fluconazole',
            'Ibuprofen', 'Acetaminophen', 'Paracetamol', 'Aspirin',
            'Diclofenac', 'Ketorolac', 'Tramadol', 'Morphine',
            'Insulin', 'Glucose', 'HbA1c', 'TSH', 'T3', 'T4',
            'Cortisol', 'ACTH', 'PTH', 'Vitamin D', 'Iron', 'Ferritin',
        ]

        # أنماط الأرقام المرجعية
        self.reference_patterns = [
            r'\d{3,4}\s*$',       # أرقام في نهاية السطر
            r'^\d{3,4}',           # أرقام في بداية السطر
            r'\(\d+\)',            # أرقام بين قوسين
        ]

    def _ensure_reader(self):
        """تهيئة EasyOCR عند الحاجة (lazy loading)"""
        if self.reader is None:
            import easyocr
            self.reader = easyocr.Reader(
                ['ar', 'en'], gpu=False, verbose=False,
                paragraph=False, min_size=10, contrast_ths=0.3
            )

    def preprocess_image(self, img_path: str) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int]]]:
        """إصدار محسّن لإزالة خطوط الدفتر مع الحفاظ على التشكيل"""
        img = cv2.imread(img_path)
        if img is None:
            return None, None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # 1. قص هوامش الصفحة
        margin_x = int(w * 0.05)
        margin_y = int(h * 0.08)
        cropped = gray[margin_y:h - margin_y, margin_x:w - margin_x]

        # 2. إزالة الخطوط الأفقية
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 1))
        detect_horizontal = cv2.morphologyEx(cropped, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        cleaned = cv2.subtract(cropped, detect_horizontal)

        # 3. إزالة الخطوط العمودية
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
        detect_vertical = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
        cleaned = cv2.subtract(cleaned, detect_vertical)

        # 4. CLAHE محسّن للتشكيل
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(10, 10))
        enhanced = clahe.apply(cleaned)

        # 5. إزالة ضوضاء صغيرة
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        noise_mask = np.zeros_like(binary)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= 8:
                noise_mask[labels == i] = 255

        final = cv2.bitwise_and(enhanced, enhanced, mask=noise_mask)

        return final, (margin_x, margin_y)

    def segment_lines(self, image: np.ndarray) -> List[Tuple[int, int]]:
        """تقسيم محسّن للنصوص الكثيفة"""
        _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        projection = np.sum(thresh, axis=1)
        projection_smooth = cv2.GaussianBlur(projection.reshape(-1, 1), (1, 5), 0).flatten()

        lines = []
        in_line = False
        start_y = 0

        avg_density = np.mean(projection[projection > 0]) if np.any(projection > 0) else 100
        threshold = avg_density * 0.2

        for y in range(len(projection_smooth)):
            if projection_smooth[y] > threshold and not in_line:
                in_line = True
                start_y = y
            elif projection_smooth[y] <= threshold and in_line:
                in_line = False
                height = y - start_y
                if height >= 10:
                    lines.append((start_y, y))

        if in_line and image.shape[0] - start_y >= 10:
            lines.append((start_y, image.shape[0]))

        # دمج الأسطر المتقاربة جداً
        merged_lines = []
        if lines:
            current = lines[0]
            for i in range(1, len(lines)):
                if lines[i][0] - current[1] < 5:
                    current = (current[0], lines[i][1])
                else:
                    merged_lines.append(current)
                    current = lines[i]
            merged_lines.append(current)

        return merged_lines

    def protect_medical_terms(self, text: str) -> Tuple[str, Dict[str, str]]:
        """حماية المصطلحات الطبية من التعديل الخاطئ"""
        protected = text
        placeholders = {}

        for i, term in enumerate(self.medical_terms):
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            if pattern.search(protected):
                placeholder = f"{{{{MED_TERM_{i}}}}}"
                placeholders[placeholder] = term
                protected = pattern.sub(placeholder, protected)

        return protected, placeholders

    def restore_medical_terms(self, text: str, placeholders: Dict[str, str]) -> str:
        """استعادة المصطلحات الطبية بعد المعالجة"""
        restored = text
        for placeholder, original in placeholders.items():
            restored = restored.replace(placeholder, original)
        return restored

    def extract_reference_numbers(self, text: str) -> Tuple[str, List[str]]:
        """عزل الأرقام المرجعية عن النص الرئيسي"""
        references = []
        clean_text = text

        for pattern in self.reference_patterns:
            matches = re.findall(pattern, clean_text)
            if matches:
                references.extend(matches)
                clean_text = re.sub(pattern, '', clean_text)

        return clean_text.strip(), references

    def process_file(self, file_path: str) -> str:
        """معالجة ملف وتجهيزه للمراجعة"""
        self._ensure_reader()
        img, margins = self.preprocess_image(file_path)
        if img is None:
            return "خطأ في قراءة الصورة"

        line_coords = self.segment_lines(img)
        self.lines_data = []

        for i, (y1, y2) in enumerate(line_coords):
            line_crop = img[y1:y2, :]

            ocr_result = self.reader.readtext(line_crop, detail=1, paragraph=False)

            if ocr_result:
                sorted_boxes = sorted(ocr_result, key=lambda k: k[0][0][0])
                raw_text = " ".join([box[1] for box in sorted_boxes])
            else:
                raw_text = ""

            protected_text, placeholders = self.protect_medical_terms(raw_text)
            clean_text, references = self.extract_reference_numbers(protected_text)
            final_text = self.restore_medical_terms(clean_text, placeholders)

            self.lines_data.append({
                'image': line_crop,
                'bbox': (y1, y2),
                'predicted_text': final_text,
                'corrected_text': final_text,
                'references': references,
                'line_idx': i,
                'has_medical_term': len(placeholders) > 0
            })

        self.current_idx = 0
        return f"تم تجهيز {len(self.lines_data)} سطر للمراجعة."

    def get_current_line(self) -> Optional[Dict]:
        """إرجاع بيانات السطر الحالي"""
        if not self.lines_data or self.current_idx >= len(self.lines_data):
            return None
        return self.lines_data[self.current_idx]

    def save_correction_and_next(self, corrected_text: str) -> Optional[Dict]:
        """حفظ التعديل والانتقال للتالي"""
        if self.lines_data and self.current_idx < len(self.lines_data):
            self.lines_data[self.current_idx]['corrected_text'] = corrected_text
            self.current_idx += 1
        return self.get_current_line()

    def save_correction_and_prev(self, corrected_text: str) -> Optional[Dict]:
        """حفظ والعودة للخلف"""
        if self.lines_data and self.current_idx < len(self.lines_data):
            self.lines_data[self.current_idx]['corrected_text'] = corrected_text
            if self.current_idx > 0:
                self.current_idx -= 1
        return self.get_current_line()

    def export_dataset(self, output_dir: str = "medical_dataset_export") -> str:
        """تصدير البيانات مع بيانات وصفية"""
        if not self.lines_data:
            return ""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        images_dir = output_path / "images"
        images_dir.mkdir(exist_ok=True)

        labels = []
        metadata = []

        for idx, item in enumerate(self.lines_data):
            filename = f"line_{idx:04d}.png"
            img_path = images_dir / filename
            cv2.imwrite(str(img_path), item['image'])

            labels.append(f"{filename}\t{item['corrected_text']}")
            metadata.append({
                'image': filename,
                'text': item['corrected_text'],
                'has_medical_term': item['has_medical_term'],
                'references': item['references'],
                'bbox': list(item['bbox'])
            })

        with open(output_path / "labels.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(labels))

        with open(output_path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # إنشاء ZIP
        zip_name = str(output_path.parent / f"{output_path.name}.zip")
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            for folder, _, files in os.walk(output_path):
                for file in files:
                    file_path = Path(folder) / file
                    arcname = file_path.relative_to(output_path)
                    zipf.write(file_path, arcname)

        return zip_name

    def get_progress(self) -> Dict:
        """معلومات التقدم الحالي"""
        total = len(self.lines_data)
        medical_count = sum(1 for l in self.lines_data if l.get('has_medical_term', False))
        corrected_count = sum(1 for l in self.lines_data
                            if l['predicted_text'] != l['corrected_text'])

        return {
            'total_lines': total,
            'current_index': self.current_idx,
            'medical_term_lines': medical_count,
            'corrected_lines': corrected_count,
            'is_complete': self.current_idx >= total
        }
