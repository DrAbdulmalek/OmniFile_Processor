#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/core/segmenter.py
=======================================

محرك تقسيم الصفحة إلى عناصر نصية ورسومية مع الحفاظ على التخطيط المكاني.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import json

import torch
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


@dataclass
class WordBox:
    """معلومات كلمة محددة."""
    id: str
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    baseline: Tuple[int, int]  # y_start, y_end للخط الأساسي
    font_size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
    is_underlined: bool = False
    script_type: str = "arabic"  # arabic, latin, mixed
    reading_order: int = 0  # الترتيب القرائي
    line_id: int = 0
    paragraph_id: int = 0
    # معلومات التعلم
    user_correction: Optional[str] = None
    correction_count: int = 0
    learned: bool = False


@dataclass
class LineBox:
    """معلومات سطر نصي."""
    id: str
    words: List[WordBox] = field(default_factory=list)
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    baseline: float = 0.0
    line_height: float = 0.0
    spacing: float = 0.0  # المسافة من السطر السابق
    alignment: str = "right"  # right, left, center, justify
    direction: str = "rtl"  # rtl, ltr


@dataclass
class ParagraphBox:
    """معلومات فقرة."""
    id: str
    lines: List[LineBox] = field(default_factory=list)
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    indent: float = 0.0
    spacing_before: float = 0.0
    spacing_after: float = 0.0


@dataclass
class TableCell:
    """خلية جدول."""
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    content: List[WordBox] = field(default_factory=list)
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    is_header: bool = False


@dataclass
class TableBox:
    """معلومات جدول."""
    id: str
    cells: List[TableCell] = field(default_factory=list)
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    num_rows: int = 0
    num_cols: int = 0
    border_style: str = "solid"  # solid, dashed, none
    header_rows: int = 0


@dataclass
class GraphicElement:
    """عنصر رسومي (مخطط، صندوق، سهم)."""
    id: str
    element_type: str  # chart, diagram_box, arrow, image, separator
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    sub_type: str = ""  # bar_chart, pie_chart, flow_box, decision_diamond
    detected_text: List[WordBox] = field(default_factory=list)
    confidence: float = 0.0
    # بيانات لإعادة الرسم
    render_data: Dict = field(default_factory=dict)


@dataclass
class PageLayout:
    """تخطيط كامل للصفحة."""
    page_number: int = 0
    width: int = 0
    height: int = 0
    paragraphs: List[ParagraphBox] = field(default_factory=list)
    tables: List[TableBox] = field(default_factory=list)
    graphics: List[GraphicElement] = field(default_factory=list)
    headers: List[LineBox] = field(default_factory=list)
    footers: List[LineBox] = field(default_factory=list)
    reading_order: List[str] = field(default_factory=list)


class SmartSegmenter:
    """مقسم ذكي للصفحات."""
    
    def __init__(
        self,
        ocr_model: str = "microsoft/trocr-large-handwritten",
        device: str = "auto"
    ):
        self.device = self._setup_device(device)
        
        # تحميل نماذج OCR
        self.processor = TrOCRProcessor.from_pretrained(ocr_model)
        self.model = VisionEncoderDecoderModel.from_pretrained(ocr_model)
        self.model.to(self.device)
        
        # نموذج اكتشاف التخطيط
        self.layout_detector = self._load_layout_detector()
        
        # نموذج اكتشاف الجداول
        self.table_detector = self._load_table_detector()
        
        # نموذج اكتشاف الرسومات
        self.graphics_detector = self._load_graphics_detector()
    
    def _setup_device(self, device: str) -> torch.device:
        """إعداد الجهاز."""
        if device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(device)
    
    def _load_layout_detector(self):
        """تحميل كاشف التخطيط."""
        # يمكن استخدام DiT (Document Image Transformer) أو LayoutLM
        try:
            from transformers import AutoModelForObjectDetection
            model = AutoModelForObjectDetection.from_pretrained(
                "microsoft/dit-base-finetuned-rvlcdip"
            )
            return model.to(self.device)
        except:
            return None
    
    def _load_table_detector(self):
        """تحميل كاشف الجداول."""
        try:
            # استخدام نموذج متخصص في اكتشاف الجداول
            from transformers import DetrForObjectDetection
            model = DetrForObjectDetection.from_pretrained(
                "microsoft/table-transformer-detection"
            )
            return model.to(self.device)
        except:
            return None
    
    def _load_graphics_detector(self):
        """تحميل كاشف الرسومات."""
        # نموذج مخصص لاكتشاف المخططات والرسومات
        return None
    
    def segment_page(self, image_path: Union[str, Path]) -> PageLayout:
        """
        تقسيم الصفحة إلى عناصرها المكونة.
        
        Args:
            image_path: مسار صورة الصفحة
        
        Returns:
            PageLayout كامل
        """
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")
        
        height, width = image.shape[:2]
        
        layout = PageLayout(
            width=width,
            height=height
        )
        
        # الخطوة 1: اكتشاف التخطيط العام
        layout_regions = self._detect_layout_regions(image)
        
        # الخطوة 2: اكتشاف الجداول
        tables = self._detect_tables(image)
        layout.tables = tables
        
        # الخطوة 3: اكتشاف الرسومات
        graphics = self._detect_graphics(image)
        layout.graphics = graphics
        
        # الخطوة 4: استخراج النصوص مع تجاوز مناطق الجداول والرسومات
        text_regions = self._get_text_regions(image, tables, graphics)
        
        # الخطوة 5: تقسيم النص إلى فقرات وأسطر وكلمات
        paragraphs = self._segment_text_regions(image, text_regions)
        layout.paragraphs = paragraphs
        
        # الخطوة 6: تحديد الترتيب القرائي
        layout.reading_order = self._determine_reading_order(layout)
        
        return layout
    
    def _detect_layout_regions(self, image: np.ndarray) -> List[Dict]:
        """اكتشاف مناطق التخطيط."""
        regions = []
        
        if self.layout_detector is None:
            # طريقة بديلة باستخدام التحليل التقليدي
            return self._traditional_layout_detection(image)
        
        # استخدام نموذج التعلم العميق
        # TODO: implement layout detection
        return regions
    
    def _traditional_layout_detection(self, image: np.ndarray) -> List[Dict]:
        """اكتشاف تخطيط تقليدي."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # ثنائية الصورة
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # إزالة الضوضاء
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # اكتشاف المكونات المتصلة
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        
        regions = []
        for i in range(1, num_labels):  # تجاوز الخلفية
            x, y, w, h, area = stats[i]
            if area > 100:  # تجاهل الصغير جداً
                regions.append({
                    'bbox': (x, y, x+w, y+h),
                    'type': 'text',  # سيتم تحديده لاحقاً
                    'area': area
                })
        
        return regions
    
    def _detect_tables(self, image: np.ndarray) -> List[TableBox]:
        """اكتشاف الجداول في الصورة."""
        tables = []
        
        if self.table_detector is not None:
            # استخدام نموذج متخصص
            tables = self._detect_tables_ml(image)
        else:
            # طريقة تقليدية
            tables = self._detect_tables_traditional(image)
        
        return tables
    
    def _detect_tables_traditional(self, image: np.ndarray) -> List[TableBox]:
        """اكتشاف جداول بالطريقة التقليدية."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # اكتشاف الخطوط الأفقية والعمودية
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        # خطوط أفقية
        horizontal = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # خطوط عمودية
        vertical = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # الجمع
        table_structure = cv2.addWeighted(horizontal, 0.5, vertical, 0.5, 0.0)
        
        # اكتشاف التقاطعات
        _, thresh = cv2.threshold(table_structure, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # إيجاد الحدود
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        tables = []
        for i, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 100 and h > 50:  # حد أدنى لحجم الجدول
                # استخراج خلايا الجدول
                table_roi = image[y:y+h, x:x+w]
                cells = self._extract_table_cells(table_roi, (x, y, x+w, y+h))
                
                table = TableBox(
                    id=f"table_{i}",
                    cells=cells,
                    bbox=(x, y, x+w, y+h),
                    num_rows=max(c.row for c in cells) + 1 if cells else 0,
                    num_cols=max(c.col for c in cells) + 1 if cells else 0
                )
                tables.append(table)
        
        return tables
    
    def _extract_table_cells(
        self,
        table_image: np.ndarray,
        table_offset: Tuple[int, int, int, int]
    ) -> List[TableCell]:
        """استخراج خلايا الجدول."""
        gray = cv2.cvtColor(table_image, cv2.COLOR_BGR2GRAY)
        
        # اكتشاف الخطوط
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # العثور على التقاطعات
        horizontal = cv2.reduce(binary, 1, cv2.REDUCE_AVG)
        vertical = cv2.reduce(binary, 0, cv2.REDUCE_AVG)
        
        # نقاط تقسيم الأسطر والأعمدة
        h_points = np.where(horizontal > 100)[0]
        v_points = np.where(vertical > 100)[0]
        
        cells = []
        ox, oy, _, _ = table_offset
        
        # إنشاء الخلايا من التقاطعات
        for i in range(len(h_points) - 1):
            for j in range(len(v_points) - 1):
                y1, y2 = h_points[i], h_points[i+1]
                x1, x2 = v_points[j], v_points[j+1]
                
                # استخراج النص من الخلية
                cell_image = table_image[y1:y2, x1:x2]
                words = self._extract_words_from_region(cell_image, (ox+x1, oy+y1, ox+x2, oy+y2))
                
                cell = TableCell(
                    row=i,
                    col=j,
                    content=words,
                    bbox=(ox+x1, oy+y1, ox+x2, oy+y2),
                    is_header=(i == 0)  # الأولى عادةً رأس
                )
                cells.append(cell)
        
        return cells
    
    def _detect_graphics(self, image: np.ndarray) -> List[GraphicElement]:
        """اكتشاف العناصر الرسومية."""
        graphics = []
        
        # اكتشاف المخططات الصندوقية
        flowcharts = self._detect_flowcharts(image)
        graphics.extend(flowcharts)
        
        # اكتشاف المخططات البيانية
        charts = self._detect_charts(image)
        graphics.extend(charts)
        
        # اكتشاف الأسهم والموصلات
        arrows = self._detect_arrows(image)
        graphics.extend(arrows)
        
        return graphics
    
    def _detect_flowcharts(self, image: np.ndarray) -> List[GraphicElement]:
        """اكتشاف مخططات التدفق."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # اكتشاف الأشكال الهندسية
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        graphics = []
        for i, cnt in enumerate(contours):
            approx = cv2.approxPolyDP(cnt, 0.04 * cv2.arcLength(cnt, True), True)
            
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h
            
            # تحديد نوع الشكل
            shape_type = "unknown"
            if len(approx) == 4:
                if 0.95 <= aspect_ratio <= 1.05:
                    shape_type = "decision_diamond"  # معين للقرار
                else:
                    shape_type = "process_box"  # مستطيل للعملية
            elif len(approx) > 6:
                shape_type = "start_oval"  # بيضاوي للبداية/النهاية
            
            if shape_type != "unknown":
                # استخراج النص داخل الشكل
                roi = image[y:y+h, x:x+w]
                words = self._extract_words_from_region(roi, (x, y, x+w, y+h))
                
                graphic = GraphicElement(
                    id=f"flow_{i}",
                    element_type="diagram_box",
                    bbox=(x, y, x+w, y+h),
                    sub_type=shape_type,
                    detected_text=words,
                    render_data={
                        "shape": shape_type,
                        "vertices": approx.tolist(),
                        "fill_color": self._detect_fill_color(roi),
                        "border_color": self._detect_border_color(roi)
                    }
                )
                graphics.append(graphic)
        
        return graphics
    
    def _detect_charts(self, image: np.ndarray) -> List[GraphicElement]:
        """اكتشاف المخططات البيانية."""
        # اكتشاف أعمدة البيانات
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # البحث عن مناطق تحتوي على أعمدة أو أجزاء دائرية
        # TODO: implement chart detection
        
        return []
    
    def _detect_arrows(self, image: np.ndarray) -> List[GraphicElement]:
        """اكتشاف الأسهم والموصلات."""
        # اكتشاف خطوط مع رؤوس سهمية
        # TODO: implement arrow detection
        
        return []
    
    def _get_text_regions(
        self,
        image: np.ndarray,
        tables: List[TableBox],
        graphics: List[GraphicElement]
    ) -> List[Tuple[int, int, int, int]]:
        """الحصول على مناطق النص مع تجاوز الجداول والرسومات."""
        height, width = image.shape[:2]
        
        # قناع للمناطق المحظورة
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # حظر مناطق الجداول
        for table in tables:
            x1, y1, x2, y2 = table.bbox
            mask[y1:y2, x1:x2] = 255
        
        # حظر مناطق الرسومات
        for graphic in graphics:
            x1, y1, x2, y2 = graphic.bbox
            mask[y1:y2, x1:x2] = 255
        
        # العثور على مناطق النص المتبقية
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # إزالة المناطق المحظورة
        binary = cv2.bitwise_and(binary, cv2.bitwise_not(mask))
        
        # اكتشاف المكونات المتصلة
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        
        regions = []
        for i in range(1, num_labels):
            x, y, w, h, area = stats[i]
            if area > 50:
                regions.append((x, y, x+w, y+h))
        
        return regions
    
    def _segment_text_regions(
        self,
        image: np.ndarray,
        regions: List[Tuple[int, int, int, int]]
    ) -> List[ParagraphBox]:
        """تقسيم مناطق النص إلى فقرات وأسطر وكلمات."""
        paragraphs = []
        
        for idx, region in enumerate(regions):
            x1, y1, x2, y2 = region
            roi = image[y1:y2, x1:x2]
            
            # تقسيم إلى أسطر
            lines = self._segment_lines(roi, region)
            
            # تجميع الأسطر إلى فقرات
            paragraph = self._group_lines_to_paragraph(lines, idx)
            paragraphs.append(paragraph)
        
        return paragraphs
    
    def _segment_lines(
        self,
        region_image: np.ndarray,
        region_offset: Tuple[int, int, int, int]
    ) -> List[LineBox]:
        """تقسيم منطقة إلى أسطر."""
        gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # إسقاط أفقي للعثور على الأسطر
        horizontal_proj = np.sum(binary, axis=1)
        
        # العثور على قمم الأسطر (مناطق النص)
        lines_indices = self._find_peaks(horizontal_proj, min_distance=10)
        
        lines = []
        ox, oy, _, _ = region_offset
        
        for i, (y_start, y_end) in enumerate(lines_indices):
            line_roi = region_image[y_start:y_end, :]
            
            # تقسيم السطر إلى كلمات
            words = self._segment_words(line_roi, (ox, oy+y_start, ox+region_image.shape[1], oy+y_end), i)
            
            line = LineBox(
                id=f"line_{i}",
                words=words,
                bbox=(ox, oy+y_start, ox+region_image.shape[1], oy+y_end),
                baseline=oy + (y_start + y_end) // 2
            )
            lines.append(line)
        
        return lines
    
    def _find_peaks(self, projection: np.ndarray, min_distance: int = 10) -> List[Tuple[int, int]]:
        """العثور على قمم في الإسقاط."""
        # تنعيم
        smoothed = np.convolve(projection, np.ones(5)/5, mode='same')
        
        # العثور على المناطق فوق المتوسط
        mean = np.mean(smoothed)
        above_mean = smoothed > mean * 0.3
        
        # العثور على المناطق المتصلة
        regions = []
        start = None
        
        for i, val in enumerate(above_mean):
            if val and start is None:
                start = i
            elif not val and start is not None:
                if i - start >= min_distance:
                    regions.append((start, i))
                start = None
        
        if start is not None:
            regions.append((start, len(above_mean)))
        
        return regions
    
    def _segment_words(
        self,
        line_image: np.ndarray,
        line_offset: Tuple[int, int, int, int],
        line_id: int
    ) -> List[WordBox]:
        """تقسيم سطر إلى كلمات."""
        gray = cv2.cvtColor(line_image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # إسقاط عمودي للعثور على المسافات بين الكلمات
        vertical_proj = np.sum(binary, axis=0)
        
        # العثور على الفجوات (المسافات البيضاء)
        mean_gap = np.mean(vertical_proj)
        gaps = vertical_proj < mean_gap * 0.3
        
        # تقسيم على الفجوات
        words = []
        start = 0
        word_idx = 0
        
        ox, oy, _, _ = line_offset
        
        for i, is_gap in enumerate(gaps):
            if is_gap:
                if i - start > 5:  # كلمة ذات معنى
                    word_roi = line_image[:, start:i]
                    
                    # التعرف على الكلمة
                    word_text, confidence = self._recognize_word(word_roi)
                    
                    word = WordBox(
                        id=f"word_{line_id}_{word_idx}",
                        text=word_text,
                        confidence=confidence,
                        bbox=(ox+start, oy, ox+i, oy+line_image.shape[0]),
                        baseline=(oy, oy+line_image.shape[0]),
                        line_id=line_id,
                        reading_order=word_idx
                    )
                    words.append(word)
                    word_idx += 1
                
                start = i + 1
        
        # الكلمة الأخيرة
        if start < len(gaps) - 5:
            word_roi = line_image[:, start:]
            word_text, confidence = self._recognize_word(word_roi)
            
            word = WordBox(
                id=f"word_{line_id}_{word_idx}",
                text=word_text,
                confidence=confidence,
                bbox=(ox+start, oy, ox+line_image.shape[1], oy+line_image.shape[0]),
                baseline=(oy, oy+line_image.shape[0]),
                line_id=line_id,
                reading_order=word_idx
            )
            words.append(word)
        
        return words
    
    def _extract_words_from_region(
        self,
        region_image: np.ndarray,
        region_offset: Tuple[int, int, int, int]
    ) -> List[WordBox]:
        """استخراج كلمات من منطقة صورة."""
        if region_image.size == 0:
            return []
        words = []
        try:
            lines = self._segment_lines(region_image, region_offset)
            for line in lines:
                words.extend(line.words)
        except Exception:
            pass
        return words
    
    def _recognize_word(self, word_image: np.ndarray) -> Tuple[str, float]:
        """التعرف على كلمة من صورتها."""
        # تحويل إلى PIL
        rgb = cv2.cvtColor(word_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        
        # معالجة
        pixel_values = self.processor(pil_image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)
        
        # التوليد
        with torch.no_grad():
            generated_ids = self.model.generate(pixel_values)
            generated_text = self.processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]
        
        # حساب الثقة
        confidence = self._calculate_confidence(pixel_values, generated_ids)
        
        return generated_text.strip(), confidence
    
    def _calculate_confidence(
        self,
        pixel_values: torch.Tensor,
        generated_ids: torch.Tensor
    ) -> float:
        """حساب ثقة التعرف."""
        with torch.no_grad():
            outputs = self.model(pixel_values, labels=generated_ids)
            logits = outputs.logits
            
            # حساب الاحتمالات
            probs = torch.softmax(logits, dim=-1)
            max_probs = torch.max(probs, dim=-1).values
            
            # متوسط الثقة
            confidence = max_probs.mean().item()
        
        return confidence
    
    def _group_lines_to_paragraph(
        self,
        lines: List[LineBox],
        paragraph_id: int
    ) -> ParagraphBox:
        """تجميع الأسطر إلى فقرة."""
        if not lines:
            return ParagraphBox(id=f"para_{paragraph_id}")
        
        # حساب الحدود
        x1 = min(l.bbox[0] for l in lines)
        y1 = min(l.bbox[1] for l in lines)
        x2 = max(l.bbox[2] for l in lines)
        y2 = max(l.bbox[3] for l in lines)
        
        # تحديد المحاذاة
        # للعربية: غالباً يمين
        alignment = self._detect_alignment(lines)
        
        for line in lines:
            line.alignment = alignment
        
        paragraph = ParagraphBox(
            id=f"para_{paragraph_id}",
            lines=lines,
            bbox=(x1, y1, x2, y2)
        )
        
        return paragraph
    
    def _detect_alignment(self, lines: List[LineBox]) -> str:
        """اكتشاف محاذاة الفقرة."""
        if not lines:
            return "right"
        
        # للعربية: التحقق من موقع النص
        # إذا كان النص يبدأ من اليمين أكثر
        starts = [l.bbox[0] for l in lines]
        ends = [l.bbox[2] for l in lines]
        
        page_width = max(ends)
        
        # متوسط البداية والنهاية
        avg_start = np.mean(starts)
        avg_end = np.mean(ends)
        
        # التحقق من التباعد
        start_variance = np.var(starts)
        end_variance = np.var(ends)
        
        if start_variance < 50 and end_variance < 50:
            return "justify"
        elif avg_start > page_width * 0.6:
            return "right"
        elif avg_end < page_width * 0.4:
            return "left"
        else:
            return "center"
    
    def _determine_reading_order(self, layout: PageLayout) -> List[str]:
        """تحديد الترتيب القرائي للعناصر."""
        # تجميع جميع العناصر
        elements = []
        
        # الفقرات
        for para in layout.paragraphs:
            elements.append(('paragraph', para.bbox[1], para.id, para.bbox))
        
        # الجداول
        for table in layout.tables:
            elements.append(('table', table.bbox[1], table.id, table.bbox))
        
        # الرسومات
        for graphic in layout.graphics:
            elements.append(('graphic', graphic.bbox[1], graphic.id, graphic.bbox))
        
        # ترتيب من الأعلى إلى الأسفل، ومن اليمين إلى اليسار للعربية
        # ترتيب: أولاً حسب y، ثم حسب x (معكوس للعربية)
        elements.sort(key=lambda e: (e[1], -e[3][0]))
        
        return [e[2] for e in elements]
    
    def _detect_fill_color(self, roi: np.ndarray) -> str:
        """اكتشاف لون التعبئة."""
        # تحليل الألوان في المنطقة
        pixels = roi.reshape(-1, 3)
        # تجاهل الأبيض والأسود
        mask = ~((pixels > 240).all(axis=1) | (pixels < 20).all(axis=1))
        colors = pixels[mask]
        
        if len(colors) == 0:
            return "#FFFFFF"
        
        # اللون السائد
        dominant = np.median(colors, axis=0)
        return f"#{int(dominant[2]):02x}{int(dominant[1]):02x}{int(dominant[0]):02x}"
    
    def _detect_border_color(self, roi: np.ndarray) -> str:
        """اكتشاف لون الحدود."""
        # تحليل الحواف
        edges = cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 50, 150)
        edge_pixels = roi[edges > 0]
        
        if len(edge_pixels) == 0:
            return "#000000"
        
        dominant = np.median(edge_pixels, axis=0)
        return f"#{int(dominant[2]):02x}{int(dominant[1]):02x}{int(dominant[0]):02x}"
    
    def extract_word_image(
        self,
        page_image: np.ndarray,
        word_box: WordBox,
        padding: int = 5
    ) -> np.ndarray:
        """استخراج صورة كلمة مع هوامش."""
        x1, y1, x2, y2 = word_box.bbox
        
        # إضافة هوامش
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(page_image.shape[1], x2 + padding)
        y2 = min(page_image.shape[0], y2 + padding)
        
        return page_image[y1:y2, x1:x2]
    
    def save_layout(self, layout: PageLayout, path: Path):
        """حفظ التخطيط إلى ملف JSON."""
        def serialize(obj):
            if isinstance(obj, (WordBox, LineBox, ParagraphBox, TableCell, TableBox, GraphicElement)):
                return {k: serialize(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [serialize(i) for i in obj]
            elif isinstance(obj, tuple):
                return list(obj)
            return obj
        
        data = serialize(layout)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_layout(self, path: Path) -> PageLayout:
        """تحميل التخطيط من ملف JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # إعادة بناء الكائنات
        # TODO: implement deserialization
        return PageLayout(**data)
