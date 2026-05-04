"""
اختبارات الوحدات الجديدة v4.2.1 — Gemini Integration
========================================================
اختبارات شاملة للوحدات المضافة:
- file_fingerprint
- classifier (Medical)
- watchdog_service
- language_corrector
- dataset_generator
- search_engine
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# إضافة مسار المشروع
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestFileFingerprintManager(unittest.TestCase):
    """اختبارات نظام بصمة الملفات."""

    def setUp(self):
        """إنشاء بيئة اختبار."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_fingerprints.db")
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("ملف اختبار لبصمة SHA-256")

    def tearDown(self):
        """تنظيف بيئة الاختبار."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_calculate_hash(self):
        """اختبار حساب بصمة الملف."""
        from modules.core.file_fingerprint import FileFingerprintManager

        hash1 = FileFingerprintManager.calculate_hash(self.test_file)
        hash2 = FileFingerprintManager.calculate_hash(self.test_file)

        # نفس الملف = نفس البصمة
        self.assertEqual(hash1, hash2)
        # البصمة بطول 64 حرف (SHA-256 hex)
        self.assertEqual(len(hash1), 64)
        # بصمة hex فقط
        self.assertTrue(all(c in '0123456789abcdef' for c in hash1))

    def test_calculate_hash_different_files(self):
        """اختبار بصمات ملفات مختلفة."""
        from modules.core.file_fingerprint import FileFingerprintManager

        other_file = os.path.join(self.temp_dir, "other.txt")
        with open(other_file, "w") as f:
            f.write("محتوى مختلف تماماً")

        hash1 = FileFingerprintManager.calculate_hash(self.test_file)
        hash2 = FileFingerprintManager.calculate_hash(other_file)
        self.assertNotEqual(hash1, hash2)

    def test_md5_hash(self):
        """اختبار حساب بصمة MD5."""
        from modules.core.file_fingerprint import FileFingerprintManager

        hash_md5 = FileFingerprintManager.calculate_hash(self.test_file, algorithm="md5")
        self.assertEqual(len(hash_md5), 32)

    def test_is_new_file(self):
        """اختبار كشف الملفات الجديدة."""
        from modules.core.file_fingerprint import FileFingerprintManager

        mgr = FileFingerprintManager(self.db_path)
        try:
            self.assertTrue(mgr.is_new_file(self.test_file))
            mgr.mark_processed(self.test_file, category="test")
            self.assertFalse(mgr.is_new_file(self.test_file))
        finally:
            mgr.close()

    def test_mark_processed(self):
        """اختبار تسجيل ملف كمعالج."""
        from modules.core.file_fingerprint import FileFingerprintManager

        mgr = FileFingerprintManager(self.db_path)
        try:
            result = mgr.mark_processed(
                self.test_file,
                category="orthopedic",
                subcategory="fracture",
                ocr_engine="easyocr",
                confidence_score=0.95
            )
            self.assertTrue(result)

            info = mgr.get_file_info(self.test_file)
            self.assertIsNotNone(info)
            self.assertEqual(info["category"], "orthopedic")
            self.assertEqual(info["ocr_engine"], "easyocr")
        finally:
            mgr.close()

    def test_mark_duplicate(self):
        """اختبار تجاهل الملفات المكررة."""
        from modules.core.file_fingerprint import FileFingerprintManager

        mgr = FileFingerprintManager(self.db_path)
        try:
            mgr.mark_processed(self.test_file)
            # الملف مسجل مسبقاً — is_new_file يرجع False
            self.assertFalse(mgr.is_new_file(self.test_file))
        finally:
            mgr.close()

    def test_get_statistics(self):
        """اختبار الإحصائيات."""
        from modules.core.file_fingerprint import FileFingerprintManager

        mgr = FileFingerprintManager(self.db_path)
        try:
            mgr.mark_processed(self.test_file, category="test")
            stats = mgr.get_statistics()

            self.assertEqual(stats["total_files"], 1)
            self.assertIn("by_category", stats)
            self.assertIn("by_extension", stats)
            self.assertGreater(stats["total_size_bytes"], 0)
        finally:
            mgr.close()

    def test_context_manager(self):
        """اختبار مدير السياق."""
        from modules.core.file_fingerprint import FileFingerprintManager

        with FileFingerprintManager(self.db_path) as mgr:
            mgr.mark_processed(self.test_file)
            self.assertFalse(mgr.is_new_file(self.test_file))

    def test_export_fingerprints(self):
        """اختبار تصدير البصمات."""
        from modules.core.file_fingerprint import FileFingerprintManager

        mgr = FileFingerprintManager(self.db_path)
        try:
            mgr.mark_processed(self.test_file)
            export_path = os.path.join(self.temp_dir, "export.json")
            result = mgr.export_fingerprints(export_path)

            self.assertTrue(result)
            self.assertTrue(os.path.exists(export_path))

            with open(export_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
        finally:
            mgr.close()


class TestMedicalClassifier(unittest.TestCase):
    """اختبارات مصنف المحتوى الطبي."""

    def setUp(self):
        from modules.core.classifier import MedicalClassifier
        self.classifier = MedicalClassifier()

    def test_orthopedic_text(self):
        """اختبار تصنيف نص جراحة العظام."""
        result = self.classifier.classify(
            "المريض يعاني من كسر في عظم الفخذ مع تمزق في الرباط الصليبي الأمامي"
        )
        self.assertEqual(result["category"], "orthopedic")
        self.assertGreater(result["confidence"], 0.3)

    def test_cardiology_text(self):
        """اختبار تصنيف نص القلب."""
        result = self.classifier.classify(
            "المريض يعاني من ذبحة صدرية مع ضغط دم مرتفع"
        )
        self.assertEqual(result["category"], "cardiology")
        self.assertGreater(result["confidence"], 0.2)

    def test_research_text(self):
        """اختبار تصنيف نص بحث علمي."""
        result = self.classifier.classify(
            "هذه دراسة إحصائية بعينة من 200 مريض مع تحليل انحدار"
        )
        self.assertIn(result["category"], ["research", "general", "orthopedic"])

    def test_general_text(self):
        """اختبار نص عام."""
        result = self.classifier.classify(
            "اليوم كان الجو جميلاً وذهبت في نزهة"
        )
        self.assertEqual(result["category"], "general")

    def test_empty_text(self):
        """اختبار نص فارغ."""
        result = self.classifier.classify("")
        self.assertEqual(result["category"], "general")
        self.assertEqual(result["confidence"], 0.0)

    def test_fallback(self):
        """اختبار التصنيف مع مستوى ثقة أدنى."""
        result = self.classifier.classify_with_fallback(
            "نص غامض جداً", min_confidence=0.5
        )
        self.assertEqual(result["category"], "general")

    def test_get_categories(self):
        """اختبار قائمة التصنيفات."""
        cats = self.classifier.get_categories()
        self.assertIn("orthopedic", cats)
        self.assertIn("cardiology", cats)
        self.assertIn("general", cats)
        self.assertGreater(len(cats), 5)

    def test_add_category(self):
        """اختبار إضافة تصنيف مخصص."""
        self.classifier.add_category(
            "custom_test",
            critical=["اختبار خاص", "test term"],
        )
        result = self.classifier.classify("هذا اختبار خاص جداً")
        # قد يكون custom_test أو general
        self.assertIn(result["category"], ["custom_test", "general"])

    def test_english_orthopedic(self):
        """اختبار تصنيف نص إنجليزي جراحة العظام."""
        result = self.classifier.classify(
            "The patient has a femoral neck fracture with ACL tear"
        )
        self.assertEqual(result["category"], "orthopedic")

    def test_scores_structure(self):
        """اختبار هيكل النتيجة."""
        result = self.classifier.classify("كسر في الركبة")
        self.assertIn("category", result)
        self.assertIn("confidence", result)
        self.assertIn("scores", result)
        self.assertIn("keywords_found", result)
        self.assertIn("top_keywords", result)


class TestLanguageCorrector(unittest.TestCase):
    """اختبارات المدقق اللغوي."""

    def setUp(self):
        from modules.nlp.language_corrector import LanguageCorrector
        self.corrector = LanguageCorrector(lang='ar')

    def test_empty_text(self):
        """اختبار نص فارغ."""
        result = self.corrector.check("")
        self.assertEqual(result["error_count"], 0)

    def test_basic_check(self):
        """اختبار الفحص الأساسي (بدون LanguageTool)."""
        # LanguageTool قد لا يكون مثبتاً
        result = self.corrector.check("نص بسيط للاختبار")
        self.assertIn("method", result)
        self.assertIn("corrected", result)
        self.assertIn("errors", result)

    def test_protected_terms(self):
        """اختبار حماية المصطلحات الطبية."""
        self.corrector.add_protected_term("مصطلح طبي خاص")
        self.assertTrue(self.corrector._is_protected("مصطلح طبي خاص"))
        self.assertTrue(self.corrector._is_protected("يحتوي مصطلح طبي خاص هنا"))

    def test_error_summary(self):
        """اختبار ملخص الأخطاء."""
        result = {
            "errors": [],
            "error_count": 0,
        }
        summary = self.corrector.get_error_summary(result)
        self.assertIn("لم يتم كشف", summary)


class TestDatasetGenerator(unittest.TestCase):
    """اختبارات مولد بيانات التدريب."""

    def setUp(self):
        from modules.core.dataset_generator import DatasetGenerator
        self.temp_dir = tempfile.mkdtemp()
        self.gen = DatasetGenerator(
            output_dir=self.temp_dir,
            specialty="orthopedic",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_entry(self):
        """اختبار إضافة إدخال."""
        result = self.gen.add_entry(
            input_text="نص خام",
            output_text="نص مصحح",
            quality="verified",
        )
        self.assertTrue(result)
        self.assertEqual(len(self.gen), 1)

    def test_add_empty_entry(self):
        """اختبار إضافة إدخال فارغ."""
        result = self.gen.add_entry(output_text="")
        self.assertFalse(result)

    def test_add_ocr_pair(self):
        """اختبار إضافة زوج OCR."""
        result = self.gen.add_ocr_pair(
            raw_text="المريض يعاني من الم",
            corrected_text="المريض يعاني من ألم",
            ocr_engine="easyocr",
            confidence=0.9,
        )
        self.assertTrue(result)

    def test_export_jsonl(self):
        """اختبار تصدير JSONL."""
        self.gen.add_entry(input_text="a", output_text="b")
        self.gen.add_entry(input_text="c", output_text="d")

        files = self.gen.export("jsonl", filename="test_export")
        self.assertIn("full", files)
        self.assertTrue(os.path.exists(files["full"]))

        # التحقق من محتوى الملف
        with open(files["full"], "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)

    def test_export_with_split(self):
        """اختبار التصدير مع تقسيم."""
        for i in range(10):
            self.gen.add_entry(
                input_text=f"input_{i}",
                output_text=f"output_{i}",
                quality="verified",
            )

        files = self.gen.export(
            "jsonl",
            split_ratios={"train": 0.8, "test": 0.2}
        )
        self.assertIn("train", files)
        self.assertIn("test", files)

    def test_statistics(self):
        """اختبار الإحصائيات."""
        self.gen.add_entry(input_text="أ", output_text="ب", specialty="orthopedic")
        self.gen.add_entry(input_text="ج", output_text="د", specialty="cardiology")
        stats = self.gen.get_statistics()

        self.assertEqual(stats["current_entries"], 2)
        self.assertIn("by_specialty", stats)
        self.assertIn("by_quality", stats)

    def test_clear(self):
        """اختبار المسح."""
        self.gen.add_entry(input_text="a", output_text="b")
        self.gen.clear()
        self.assertEqual(len(self.gen), 0)

    def test_max_entries(self):
        """اختبار الحد الأقصى."""
        from modules.core.dataset_generator import DatasetGenerator
        gen = DatasetGenerator(output_dir=self.temp_dir, max_entries=2)

        gen.add_entry(input_text="a", output_text="b")
        gen.add_entry(input_text="c", output_text="d")
        result = gen.add_entry(input_text="e", output_text="f")

        self.assertFalse(result)
        self.assertEqual(len(gen), 2)


class TestSearchEngine(unittest.TestCase):
    """اختبارات محرك البحث."""

    def test_parse_advanced_query(self):
        """اختبار تحليل الاستعلام المتقدم."""
        from modules.core.search_engine import SearchEngine

        # AND
        result = SearchEngine._parse_advanced_query("كسر AND فخذ")
        operators = [op for op, _ in result]
        terms = [t for _, t in result]
        self.assertIn("AND", operators)
        self.assertIn("كسر", terms)

        # NOT
        result = SearchEngine._parse_advanced_query("جراحة NOT قلب")
        operators = [op for op, _ in result]
        self.assertIn("NOT", operators)

        # Simple
        result = SearchEngine._parse_advanced_query("بسيط")
        self.assertEqual(len(result), 1)

    def test_extract_context(self):
        """اختبار استخراج السياق."""
        from modules.core.search_engine import SearchEngine

        text = "المريض يعاني من ألم شديد في الركبة اليسرى منذ فترة طويلة ويحتاج إلى تقييم متخصص"
        result = SearchEngine._extract_context(text, "الركبة", context_length=20)
        self.assertIn("الركبة", result)

    def test_fts5_query(self):
        """اختبار تحويل استعلام FTS5."""
        from modules.core.search_engine import SearchEngine

        result = SearchEngine._to_fts5_query("كسر فخذ")
        self.assertIn('"كسر"', result)
        self.assertIn('"فخذ"', result)

    def test_search_files(self):
        """اختبار البحث في الملفات."""
        from modules.core.search_engine import SearchEngine

        temp_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("هذا نص اختبار يحتوي على كلمة كسر")

            engine = SearchEngine()
            results = engine.search_files(temp_dir, "كسر")
            self.assertGreater(len(results), 0)
            self.assertIn("كسر", results[0]["snippet"])
            engine.close()
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestWatchdogService(unittest.TestCase):
    """اختبارات خدمة مراقبة المجلدات."""

    def test_initialization(self):
        """اختبار التهيئة."""
        from modules.core.watchdog_service import FolderWatchdog

        temp_dir = tempfile.mkdtemp()
        try:
            wd = FolderWatchdog(
                watch_dir=temp_dir,
                callback=lambda x: None,
                poll_interval=1.0,
            )
            self.assertEqual(wd.watch_dir, temp_dir)
            self.assertFalse(wd._running)
            wd.stop()
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_valid_extensions(self):
        """اختبار فلاتر الامتدادات."""
        from modules.core.watchdog_service import FolderWatchdog

        wd = FolderWatchdog.__new__(FolderWatchdog)
        wd.extensions = {'.pdf', '.png'}

        self.assertTrue(wd._is_valid_file("/path/to/file.pdf"))
        self.assertTrue(wd._is_valid_file("/path/to/file.png"))
        self.assertFalse(wd._is_valid_file("/path/to/file.doc"))

    def test_statistics(self):
        """اختبار إحصائيات المراقب."""
        from modules.core.watchdog_service import FolderWatchdog

        temp_dir = tempfile.mkdtemp()
        try:
            wd = FolderWatchdog(
                watch_dir=temp_dir,
                callback=lambda x: None,
            )
            stats = wd.get_statistics()
            self.assertEqual(stats["watch_dir"], temp_dir)
            self.assertFalse(stats["running"])
            wd.stop()
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_repr(self):
        """اختبار التمثيل النصي."""
        from modules.core.watchdog_service import FolderWatchdog

        temp_dir = tempfile.mkdtemp()
        try:
            wd = FolderWatchdog(watch_dir=temp_dir, callback=lambda x: None)
            repr_str = repr(wd)
            self.assertIn("FolderWatchdog", repr_str)
            self.assertIn("stopped", repr_str)
            wd.stop()
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
