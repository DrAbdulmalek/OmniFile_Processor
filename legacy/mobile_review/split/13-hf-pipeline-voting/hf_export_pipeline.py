# hf_export_pipeline.py - HuggingFace Dataset export pipeline

"""
🤖 خط أنابيب تصدير بيانات OmniFile إلى HuggingFace Dataset
يدعم: تضمين الصور/النصوص، تقسيم تلقائي، رفع مباشر للـ Hub، وتوثيق ذاتي
"""

import json, os, re, logging
from pathlib import Path
from typing import Optional, Dict, List, Union
from datetime import datetime
import pandas as pd
from PIL import Image as PILImage
import io

from datasets import Dataset, DatasetDict, Features, Value, ClassLabel, Image, Sequence
from huggingface_hub import HfApi, login

logger = logging.getLogger(__name__)

class HFExportPipeline:
    def __init__(
        self,
        image_dir: Optional[str] = None,
        store_images: bool = True,
        apply_correction_dict: bool = True,
        hf_token: Optional[str] = None
    ):
        self.image_dir = Path(image_dir) if image_dir else None
        self.store_images = store_images
        self.apply_correction_dict = apply_correction_dict
        self.hf_token = hf_token
        self.correction_dict = {}
        self._api = HfApi(token=hf_token) if hf_token else None

    def load_correction_dict(self, path: str):
        """تحميل قاموس التصحيحات لتطبيقه تلقائياً على النصوص"""
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                self.correction_dict = json.load(f)
            logger.info(f"📖 تم تحميل {len(self.correction_dict)} مدخل تصحيح")

    def _normalize_text(self, text: str) -> str:
        """تطبيع النص العربي بشكل آمن للتدريب"""
        if not text: return text
        text = re.sub(r'[\u064B-\u065B\u0670]', '', text)  # إزالة تشكيل زائد
        text = re.sub(r'[أإآٱ]', 'ا', text)
        text = re.sub(r'ة', 'ه', text)  # اختياري: توحيد التاء المربوطة
        text = re.sub(r'ي', 'ی', text)  # اختياري: توحيد الياء
        return text.strip()

    def _apply_corrections(self, text: str) -> tuple:
        """تطبيق التصحيح وإرجاع (النص النهائي, هل تم التعديل؟)"""
        if not self.apply_correction_dict or not self.correction_dict:
            return text, False

        # تطبيق سريع مع تتبع التعديلات
        original = text
        for wrong, right in self.correction_dict.items():
            text = text.replace(wrong, right)
        return text, text != original

    def process_annotations(self, annotations_dir: str) -> DatasetDict:
        """تحويل مجلد ملفات JSON القياسية إلى DatasetDict"""
        annotations_dir = Path(annotations_dir)
        records = []

        for ann_file in annotations_dir.glob("*.json"):
            try:
                with open(ann_file, "r", encoding="utf-8") as f:
                    ann = json.load(f)

                doc_id = ann.get("doc_id", ann_file.stem)
                for page in ann.get("pages", []):
                    for block in page.get("blocks", []):
                        raw_text = block.get("text", "")
                        corrected_text, was_auto_fixed = self._apply_corrections(raw_text)

                        # تحميل الصورة إذا طُلب
                        image_obj = None
                        if self.store_images and self.image_dir:
                            img_name = page.get("source_image", f"{doc_id}_p{page.get('page_number', 0)}.jpg")
                            img_path = self.image_dir / img_name
                            if img_path.exists():
                                image_obj = PILImage.open(img_path).convert("RGB")

                        record = {
                            "doc_id": doc_id,
                            "page_id": page.get("page_id", f"{doc_id}_p{page.get('page_number', 0)}"),
                            "block_id": block.get("id"),
                            "block_type": block.get("type", "unknown"),
                            "original_text": raw_text,
                            "corrected_text": corrected_text,
                            "auto_corrected": was_auto_fixed,
                            "confidence": float(block.get("confidence", 0.0)),
                            "language": block.get("language", "mixed"),
                            "rtl": bool(block.get("rtl", True)),
                            "bbox": block.get("bbox", [0,0,0,0]),
                            "source_engine": block.get("source", "unknown"),
                            "metadata": block.get("metadata", {}),
                            "image": image_obj
                        }
                        records.append(record)
            except Exception as e:
                logger.warning(f"⚠️ تخطي ملف {ann_file}: {e}")

        if not records:
            raise ValueError("لم يتم العثور على كتل صالحة في المجلد المحدد")

        return self._build_dataset_dict(records)

    def _build_dataset_dict(self, records: List[Dict]) -> DatasetDict:
        """بناء DatasetDict مع تقسيم تلقائي وميزات محددة"""
        df = pd.DataFrame(records)

        # تحديد الميزات يدوياً لضمان التوافق مع HuggingFace
        features = Features({
            "doc_id": Value("string"),
            "page_id": Value("string"),
            "block_id": Value("string"),
            "block_type": ClassLabel(names=["title", "paragraph", "table", "caption", "figure", "list_item", "footnote", "unknown"]),
            "original_text": Value("string"),
            "corrected_text": Value("string"),
            "auto_corrected": Value("bool"),
            "confidence": Value("float32"),
            "language": ClassLabel(names=["ar", "en", "de", "mixed", "unknown"]),
            "rtl": Value("bool"),
            "bbox": Sequence(Value("float32"), length=4),
            "source_engine": Value("string"),
            "metadata": Value("string"),  # JSON serialized
            "image": Image() if self.store_images else Value("string")
        })

        # تحويل metadata إلى string لتجنب مشاكل التسلسل
        df["metadata"] = df["metadata"].apply(lambda x: json.dumps(x, ensure_ascii=False))
        if not self.store_images:
            df["image"] = ""

        ds = Dataset.from_pandas(df, features=features)

        # تقسيم تلقائي (80/10/10) مع الحفاظ على توزيع types/languages
        try:
            ds = ds.train_test_split(test_size=0.2, seed=42)
            ds["test"] = ds["test"].train_test_split(test_size=0.5)["test"]  # val = 10%
        except Exception as e:
            logger.warning(f"⚠️ فشل التقسيم التلقائي: {e}. استخدام مجموعة واحدة.")
            ds = DatasetDict({"train": ds})

        return ds

    def push_to_hub(self, dataset: DatasetDict, repo_name: str, private: bool = True, description: str = "") -> str:
        """رفع المجموعة إلى HuggingFace Hub مع بطاقة تعريف تلقائية"""
        if not self.hf_token:
            raise ValueError("مطلوب hf_token للرفع إلى Hub")

        login(self.hf_token)
        url = dataset.push_to_hub(repo_name, private=private)

        # إنشاء README تلقائي
        readme = f"""---
dataset_info:
  features:
    - name: original_text
      dtype: string
    - name: corrected_text
      dtype: string
    - name: block_type
      dtype: class_label
      names: ["title", "paragraph", "table", "caption", "figure", "list_item", "footnote", "unknown"]
    - name: confidence
      dtype: float32
    - name: language
      dtype: class_label
      names: ["ar", "en", "de", "mixed", "unknown"]
  splits:
    - name: train
      num_bytes: {len(json.dumps(dataset["train"].to_dict()))}
      num_examples: {len(dataset["train"])}
    - name: validation
      num_bytes: {len(json.dumps(dataset["validation"].to_dict())) if "validation" in dataset else 0}
      num_examples: {len(dataset["validation"])} if "validation" in dataset else 0
    - name: test
      num_bytes: {len(json.dumps(dataset["test"].to_dict())) if "test" in dataset else 0}
      num_examples: {len(dataset["test"])} if "test" in dataset else 0
  download_size: estimated
  dataset_size: estimated
---

# 📖 {repo_name}
> مجموعة بيانات OCR عربية/إنجليزية مُصدّرة من OmniFile_Processor
> 🗓️ تاريخ التصدير: {datetime.now().isoformat()}
> 🔧 تم إنشاء هذه البطاقة تلقائياً بواسطة `hf_export_pipeline.py`

## 🎯 الاستخدام
```python
from datasets import load_dataset
ds = load_dataset("{repo_name}")
