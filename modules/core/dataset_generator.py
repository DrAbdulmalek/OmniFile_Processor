"""
مولد بيانات التدريب الناعم (Fine-Tuning Dataset Generator)
=============================================================
تحويل النصوص المصحّحة والمعتمدة إلى تنسيقات بيانات التدريب.

يدعم التنسيقات:
- JSONL: ل تدريب نماذج مثل GPT, Llama, Mistral
- JSON: تنسيق HuggingFace datasets
- CSV: للتحليل الإحصائي

الاستخدام:
    from modules.core.dataset_generator import DatasetGenerator
    gen = DatasetGenerator(output_dir="training_data")
    gen.add_entry(
        instruction="صحح المصطلحات الطبية في النص التالي:",
        input_text="المريض يعاني من الم في الرکبة",
        output_text="المريض يعاني من ألم في الركبة",
        specialty="orthopedic",
        quality="verified"
    )
    gen.export("jsonl")
"""

import json
import csv
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DatasetGenerator:
    """
    مولد بيانات التدريب الناعم — يحوّل الأرشيف إلى بيانات جاهزة للتدريب.

    كل إدخال يحتوي على:
    - instruction: التعليمات (مثلاً: "صحح المصطلحات الطبية")
    - input: النص الخام أو الأصلي
    - output: النص المصحح أو المعتمد
    - specialty: التخصص الطبي (اختياري)
    - quality: جودة البيانات (verified / auto / draft)
    - metadata: بيانات وصفية إضافية
    """

    DEFAULT_INSTRUCTION = "صحح الأخطاء والمصطلحات الطبية في النص التالي المتعلق بالجراحة:"

    def __init__(
        self,
        output_dir: str = "training_data",
        filename: str = "medical_training",
        specialty: str = "general",
        max_entries: int = 100000,
    ):
        """
        تهيئة مولد بيانات التدريب.

        Args:
            output_dir: مجلد المخرجات
            filename: اسم الملف الأساسي
            specialty: التخصص الافتراضي
            max_entries: الحد الأقصى للإدخالات
        """
        self.output_dir = output_dir
        self.filename = filename
        self.default_specialty = specialty
        self.max_entries = max_entries

        # قاعدة البيانات في الذاكرة
        self._entries: List[Dict[str, Any]] = []
        self._stats = {
            "total_entries": 0,
            "by_specialty": {},
            "by_quality": {},
            "by_date": {},
        }

        # إنشاء المجلد
        os.makedirs(output_dir, exist_ok=True)

        logger.info("تم تهيئة مولد بيانات التدريب: %s", output_dir)

    def add_entry(
        self,
        instruction: Optional[str] = None,
        input_text: str = "",
        output_text: str = "",
        specialty: Optional[str] = None,
        quality: str = "auto",
        source_file: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        إضافة إدخال جديد إلى قاعدة بيانات التدريب.

        Args:
            instruction: التعليمات (الافتراضي: التصحيح الطبي)
            input_text: النص الأصلي/الخام
            output_text: النص المصحح/المعتمد
            specialty: التخصص الطبي
            quality: جودة البيانات (verified/auto/draft)
            source_file: الملف المصدر
            metadata: بيانات وصفية إضافية

        Returns:
            True إذا تمت الإضافة بنجاح
        """
        if len(self._entries) >= self.max_entries:
            logger.warning("تم بلوغ الحد الأقصى للإدخالات: %d", self.max_entries)
            return False

        entry = {
            "instruction": instruction or self.DEFAULT_INSTRUCTION,
            "input": input_text,
            "output": output_text,
            "specialty": specialty or self.default_specialty,
            "quality": quality,
            "source_file": source_file,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        # التحقق من صحة الإدخال
        if not output_text.strip():
            logger.warning("إدخال فارغ — تم التخطي")
            return False

        self._entries.append(entry)

        # تحديث الإحصائيات
        self._stats["total_entries"] = len(self._entries)
        spec = entry["specialty"]
        self._stats["by_specialty"][spec] = self._stats["by_specialty"].get(spec, 0) + 1
        qual = entry["quality"]
        self._stats["by_quality"][qual] = self._stats["by_quality"].get(qual, 0) + 1

        today = datetime.now().strftime("%Y-%m-%d")
        self._stats["by_date"][today] = self._stats["by_date"].get(today, 0) + 1

        return True

    def add_ocr_pair(
        self,
        raw_text: str,
        corrected_text: str,
        specialty: str = "general",
        ocr_engine: str = "unknown",
        confidence: float = 0.0,
        source_file: str = "",
    ) -> bool:
        """
        إضافة زوج OCR (نص خام + نص مصحح) مباشرة.

        Args:
            raw_text: النص المستخرج من OCR
            corrected_text: النص بعد التصحيح
            specialty: التخصص الطبي
            ocr_engine: محرك OCR المستخدم
            confidence: نسبة الثقة
            source_file: الملف المصدر

        Returns:
            True إذا تمت الإضافة بنجاح
        """
        metadata = {
            "ocr_engine": ocr_engine,
            "ocr_confidence": confidence,
            "type": "ocr_correction",
        }

        quality = "verified" if confidence > 0.85 else "auto"

        return self.add_entry(
            instruction=self.DEFAULT_INSTRUCTION,
            input_text=raw_text,
            output_text=corrected_text,
            specialty=specialty,
            quality=quality,
            source_file=source_file,
            metadata=metadata,
        )

    def add_classification_pair(
        self,
        text: str,
        category: str,
        subcategory: str = "",
        source_file: str = "",
    ) -> bool:
        """
        إضافة زوج تصنيف (نص + تصنيف صحيح).

        Args:
            text: النص
            category: التصنيف الصحيح
            subcategory: التصنيف الفرعي
            source_file: الملف المصدر

        Returns:
            True إذا تمت الإضافة بنجاح
        """
        classification_text = category
        if subcategory:
            classification_text = f"{category} > {subcategory}"

        metadata = {
            "type": "classification",
            "category": category,
            "subcategory": subcategory,
        }

        return self.add_entry(
            instruction="صنف النص الطبي التالي:",
            input_text=text,
            output_text=classification_text,
            specialty=category,
            quality="auto",
            source_file=source_file,
            metadata=metadata,
        )

    def export(
        self,
        format_type: str = "jsonl",
        filename: Optional[str] = None,
        split_ratios: Optional[Dict[str, float]] = None,
    ) -> Dict[str, str]:
        """
        تصدير بيانات التدريب إلى ملف.

        Args:
            format_type: تنسيق التصدير ('jsonl', 'json', 'csv')
            filename: اسم الملف (الافتراضي: الاسم الأساسي)
            split_ratios: نسب التقسيم (مثل {'train': 0.8, 'val': 0.1, 'test': 0.1})

        Returns:
            قاموس {اسم_المجموعة: مسار_الملف}
        """
        if not self._entries:
            logger.warning("لا توجد بيانات للتصدير")
            return {}

        filename = filename or self.filename
        output_files = {}

        if split_ratios:
            # تقسيم البيانات
            splits = self._split_data(split_ratios)
            for split_name, entries in splits.items():
                ext = self._get_extension(format_type)
                out_name = f"{filename}_{split_name}{ext}"
                out_path = os.path.join(self.output_dir, out_name)
                self._write_file(entries, out_path, format_type)
                output_files[split_name] = out_path
                logger.info(
                    "تم تصدير %d إدخال (%s) إلى %s",
                    len(entries), split_name, out_path
                )
        else:
            # تصدير كامل
            ext = self._get_extension(format_type)
            out_name = f"{filename}{ext}"
            out_path = os.path.join(self.output_dir, out_name)
            self._write_file(self._entries, out_path, format_type)
            output_files["full"] = out_path
            logger.info("تم تصدير %d إدخال إلى %s", len(self._entries), out_path)

        # حفظ الإحصائيات
        stats_path = os.path.join(self.output_dir, f"{filename}_stats.json")
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(self._stats, f, ensure_ascii=False, indent=2)

        return output_files

    def _write_file(self, entries: List[Dict], filepath: str, format_type: str):
        """كتابة البيانات إلى ملف بالتنسيق المحدد."""
        if format_type == "jsonl":
            with open(filepath, "w", encoding="utf-8") as f:
                for entry in entries:
                    # إزالة الحقول الوصفية من بيانات التدريب
                    train_entry = {
                        "instruction": entry["instruction"],
                        "input": entry["input"],
                        "output": entry["output"],
                    }
                    if entry.get("specialty"):
                        train_entry["specialty"] = entry["specialty"]
                    f.write(json.dumps(train_entry, ensure_ascii=False) + "\n")

        elif format_type == "json":
            data = []
            for entry in entries:
                data.append({
                    "instruction": entry["instruction"],
                    "input": entry["input"],
                    "output": entry["output"],
                    "specialty": entry.get("specialty", ""),
                })
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif format_type == "csv":
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["instruction", "input", "output", "specialty", "quality"])
                for entry in entries:
                    writer.writerow([
                        entry["instruction"],
                        entry["input"],
                        entry["output"],
                        entry.get("specialty", ""),
                        entry.get("quality", ""),
                    ])

    def _split_data(self, ratios: Dict[str, float]) -> Dict[str, List[Dict]]:
        """تقسيم البيانات حسب النسب المحددة."""
        total = len(self._entries)
        splits = {}
        used = 0

        # ترتيب حسب الجودة (verified أولاً)
        quality_order = {"verified": 0, "auto": 1, "draft": 2}
        sorted_entries = sorted(
            self._entries,
            key=lambda x: quality_order.get(x.get("quality", "draft"), 3)
        )

        for split_name, ratio in ratios.items():
            count = int(total * ratio)
            # تعديل آخر مجموعة لتشمل الباقي
            if split_name == list(ratios.keys())[-1]:
                count = total - used
            splits[split_name] = sorted_entries[used:used + count]
            used += count

        return splits

    @staticmethod
    def _get_extension(format_type: str) -> str:
        """الحصول على امتداد الملف حسب التنسيق."""
        extensions = {"jsonl": ".jsonl", "json": ".json", "csv": ".csv"}
        return extensions.get(format_type, ".jsonl")

    def get_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات بيانات التدريب."""
        stats = dict(self._stats)
        stats["output_dir"] = self.output_dir
        stats["filename"] = self.filename
        stats["max_entries"] = self.max_entries
        stats["current_entries"] = len(self._entries)
        stats["remaining"] = self.max_entries - len(self._entries)
        return stats

    def load_existing(self, filepath: str) -> int:
        """
        تحميل بيانات من ملف JSONL موجود.

        Args:
            filepath: مسار ملف JSONL

        Returns:
            عدد الإدخالات المحملة
        """
        if not os.path.exists(filepath):
            logger.warning("الملف غير موجود: %s", filepath)
            return 0

        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        self._entries.append(entry)
                        count += 1
                    except json.JSONDecodeError:
                        continue

            self._stats["total_entries"] = len(self._entries)
            logger.info("تم تحميل %d إدخال من %s", count, filepath)
        except Exception as e:
            logger.error("خطأ في تحميل الملف: %s", e)

        return count

    def clear(self):
        """مسح جميع الإدخالات."""
        self._entries.clear()
        self._stats = {
            "total_entries": 0,
            "by_specialty": {},
            "by_quality": {},
            "by_date": {},
        }
        logger.info("تم مسح جميع بيانات التدريب")

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return (
            f"DatasetGenerator(entries={len(self._entries)}, "
            f"specialty='{self.default_specialty}')"
        )
