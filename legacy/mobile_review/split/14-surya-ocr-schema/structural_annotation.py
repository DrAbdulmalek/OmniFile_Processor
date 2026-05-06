# structural_annotation.py - Pydantic structural annotation schema

"""
🎯 الهيكل القياسي لبيانات OmniFile_Processor
يدعم: التحقق الآلي، التوثيق الذاتي، والتصدير لـ JSON/CSV
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Dict, Union, Literal
from enum import Enum
import re, json
from datetime import datetime

# 🔹 أنواع الكتل المدعومة
class BlockType(str, Enum):
    TITLE = "title"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    CAPTION = "caption"
    FIGURE = "figure"
    LIST_ITEM = "list_item"
    FOOTNOTE = "footnote"
    FORMULA = "formula"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"
    UNKNOWN = "unknown"

# 🔹 لغات المدخلات
class Language(str, Enum):
    AR = "ar"
    EN = "en"
    DE = "de"
    MIXED = "mixed"
    UNKNOWN = "unknown"

# 🔹 كتلة نصية واحدة مع كل البيانات الهيكلية
class TextBlock(BaseModel):
    id: str = Field(..., description="معرف فريد للكتلة، مثال: blk_001")
    type: BlockType = Field(..., description="نوع الكتلة الهيكلية")
    text: str = Field(..., min_length=1, description="النص المستخرج")

    # الإحداثيات: [x1, y1, x2, y2] أو 4 نقاط مضلع
    bbox: List[float] = Field(..., min_items=4, max_items=4, description="مربع محدد [x1,y1,x2,y2]")
    polygon: Optional[List[List[float]]] = Field(None, description="4 نقاط للمضلع: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]")

    # جودة الاستخراج
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="ثقة النموذج في هذا النص")

    # التحليل اللغوي
    language: Language = Field(Language.UNKNOWN, description="اللغة المكتشفة")
    rtl: Optional[bool] = Field(None, description="هل النص من اليمين لليسار؟ يُحسب تلقائياً إذا لم يُحدد")

    # مصادر متعددة (للدمج)
    source: str = Field(..., description="اسم محرك OCR المصدر: paddle/easyocr/surya/...")
    source_confidences: Optional[Dict[str, float]] = Field(None, description="ثقة كل محرك إذا تم الدمج")

    # محتوى غني (للجداول والعناصر المركبة)
    children: Optional[List['TextBlock']] = Field(None, description="كتل فرعية: خلايا جدول، عناصر قائمة، إلخ")
    metadata: Optional[Dict[str, Union[str, int, float]]] = Field(None, description="بيانات إضافية: رقم الصفحة، اسم الملف، إلخ")

    # روابط هيكلية
    references: Optional[List[str]] = Field(None, description="معرفات الكتل المرتبطة: تسمية ⇄ شكل، جدول ⇄ شرح")
    reading_order: Optional[int] = Field(None, description="ترتيب القراءة المنطقي (1,2,3...)")

    @validator('bbox')
    def validate_bbox_coordinates(cls, v):
        """تأكد أن الإحداثيات منطقية: x1<x2 و y1<y2"""
        if len(v) == 4:
            x1, y1, x2, y2 = v
            if not (x1 < x2 and y1 < y2):
                raise ValueError("bbox يجب أن يكون [x1< x2, y1< y2]")
        return v

    @validator('text')
    def normalize_arabic_text(cls, v):
        """تطبيع النص العربي: إزالة التشكيل الزائد، توحيد الألف"""
        if not v:
            return v
        # إزالة التشكيل الاختياري (يمكن تعطيله إذا لزم)
        v = re.sub(r'[\u064B-\u065B\u0670]', '', v)
        # توحيد الألف المقصورة/الممدودة
        v = re.sub(r'[أإآ]', 'ا', v)
        return v.strip()

    @root_validator(pre=True)
    def auto_detect_rtl(cls, values):
        """كشف تلقائي لاتجاه النص إذا لم يُحدد"""
        if values.get('rtl') is None and 'text' in values:
            text = values['text']
            arabic_ratio = sum(1 for c in text if '\u0600' <= c <= '\u06FF') / max(len(text), 1)
            values['rtl'] = arabic_ratio > 0.5
        return values

    class Config:
        json_schema_extra = {
            "example": {
                "id": "blk_042",
                "type": "caption",
                "text": "شكل 3: توزيع العينات حسب الفئة العمرية",
                "bbox": [120.5, 850.2, 880.1, 920.8],
                "confidence": 0.94,
                "language": "ar",
                "rtl": True,
                "source": "surya",
                "references": ["fig_003"],
                "reading_order": 12
            }
        }

# 🔹 صفحة كاملة مع علاقتها الهيكلية
class PageAnnotation(BaseModel):
    page_id: str = Field(..., description="معرف الصفحة: doc001_p3")
    image_size: List[int] = Field(..., min_items=2, max_items=2, description="[width, height] بالبكسل")

    blocks: List[TextBlock] = Field(..., description="جميع الكتل النصية في الصفحة")

    # رسم بياني للعلاقات المنطقية (اختياري لكن موصى به)
    layout_graph: Optional[Dict[str, List[Dict]]] = Field(None, description={
        "edges": [
            {"from": "blk_002", "to": "fig_003", "relation": "describes"},
            {"from": "blk_001", "to": "blk_003", "relation": "precedes"}
        ]
    })

    metadata: Dict[str, Union[str, int, float]] = Field(default_factory=dict, description={
        "source_file": "medical_report_ar.pdf",
        "page_number": 3,
        "dpi": 300,
        "processing_timestamp": "2024-06-15T10:30:00Z"
    })

    @validator('blocks')
    def ensure_unique_ids(cls, v):
        """منع تكرار معرفات الكتل في نفس الصفحة"""
        ids = [b.id for b in v if hasattr(b, 'id')]
        if len(ids) != len(set(ids)):
            raise ValueError("يجب أن تكون معرفات الكتل فريدة داخل الصفحة")
        return v

    def to_markdown(self) -> str:
        """تصدير الصفحة كـ Markdown مع الحفاظ على الهيكلية"""
        lines = []
        # فرز الكتل حسب ترتيب القراءة أو الموقع الرأسي
        sorted_blocks = sorted(self.blocks, key=lambda b: b.reading_order or b.bbox[1])

        for block in sorted_blocks:
            if block.type == BlockType.TITLE:
                lines.append(f"## {block.text}")
            elif block.type == BlockType.CAPTION:
                lines.append(f"*{block.text}*")
            elif block.type == BlockType.TABLE and block.children:
                # جدول ببنية خلايا
                lines.append("| " + " | ".join(c.text for c in block.children[:5]) + " |")  # أول 5 خلايا كمثال
                lines.append("|" + "---|" * min(len(block.children), 5))
            else:
                # فقرة عادية مع دعم RTL
                dir_attr = 'dir="rtl"' if block.rtl else ''
                lines.append(f'<p {dir_attr}>{block.text}</p>')

        return "\n\n".join(lines)

    def to_correction_dict_entry(self) -> Dict:
        """تحويل الصفحة إلى مدخلات قابلة للإضافة لـ correction_dict"""
        return {
            "page_id": self.page_id,
            "corrections": [
                {
                    "block_id": b.id,
                    "original": b.text,
                    "suggested_fix": None,  # يُملأ يدوياً
                    "confidence_threshold": 0.85  # فقط الكتل الأقل ثقة تُعرض للمراجعة
                }
                for b in self.blocks if b.confidence < 0.85
            ],
            "exported_at": datetime.now().isoformat()
        }

# 🔹 وثيقة كاملة (عدة صفحات)
class DocumentAnnotation(BaseModel):
    doc_id: str = Field(..., description="معرف فريد للوثيقة")
    title: Optional[str] = Field(None, description="عنوان الوثيقة إن وُجد")
    pages: List[PageAnnotation] = Field(..., description="صفحات الوثيقة مرتبة")

    # قاموس تصحيحات مدمج
    correction_dict: Dict[str, str] = Field(default_factory=dict, description={
        "الجرعه": "الجرعة",
        "مستشفي": "مستشفى"
    })

    def apply_corrections(self) -> 'DocumentAnnotation':
        """تطبيق قاموس التصحيحات على جميع الكتل تلقائياً"""
        for page in self.pages:
            for block in page.blocks:
                if block.text in self.correction_dict:
                    block.text = self.correction_dict[block.text]
                    block.metadata = block.metadata or {}
                    block.metadata["auto_corrected"] = True
        return self

    def export_for_training(self, format: Literal["json", "tsv", "hf_dataset"] = "json") -> Union[str, bytes]:
        """تصدير البيانات كمدخلات لتدريب نموذج ترجمة أو تحسين OCR"""
        if format == "json":
            return self.json(indent=2, ensure_ascii=False)

        elif format == "tsv":
            # تنسيق: block_id \t original_text \t corrected_text \t language \t confidence
            lines = ["block_id\toriginal\tcorrected\tlang\tconfidence"]
            for page in self.pages:
                for block in page.blocks:
                    corrected = self.correction_dict.get(block.text, block.text)
                    lines.append(f"{block.id}\t{block.text}\t{corrected}\t{block.language}\t{block.confidence}")
            return "\n".join(lines)

        elif format == "hf_dataset":
            # تنسيق متوافق مع HuggingFace Datasets للتدريب المباشر
            from datasets import Dataset
            data = []
            for page in self.pages:
                for block in page.blocks:
                    data.append({
                        "text": block.text,
                        "language": block.language,
                        "block_type": block.type,
                        "confidence": block.confidence,
                        "page_id": page.page_id
                    })
            return Dataset.from_list(data).to_json()

        raise ValueError(f"تنسيق غير مدعوم: {format}")

# 🔹 دوال مساعدة للتصدير/الاستيراد
def load_annotation(json_path: str) -> DocumentAnnotation:
    """تحميل هيكلية من ملف JSON مع التحقق من الصحة"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return DocumentAnnotation(**data)

def save_annotation(doc: DocumentAnnotation, output_path: str):
    """حفظ الهيكلية مع ضمان الترميز الصحيح للعربية"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(doc.json(indent=2, ensure_ascii=False))
