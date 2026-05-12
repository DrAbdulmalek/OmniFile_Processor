#!/usr/bin/env python3
"""
Smart Medical Dictionary with Auto-Learning
القاموس الطبي الذكي مع التعلم التلقائي

A comprehensive medical dictionary tool for OCR error correction in
Arabic and English medical handwriting. Supports regex patterns,
interactive term management, category-based organization, and
auto-saving of new corrections.

أداة قاموس طبي شاملة لتصحيح أخطاء OCR في الكتابة الطبية العربية
والإنجليزية. يدعم أنماط regex، وإدارة المصطلحات التفاعلية، والتنظيم
التصنيفي، والحفظ التلقائي للتصحيحات الجديدة.

Features:
- Category-based dictionary (bone_tumors, fractures, medications, etc.)
- Arabic and English medical terms
- Regex pattern support for fuzzy OCR correction
- Interactive add/search/delete via CLI
- Auto-save new entries
- JSON persistence / حفظ بصيغة JSON

Usage:
    # Interactive mode / الوضع التفاعلي
    python smart_dictionary.py

    # Add a term from CLI / إضافة مصطلح من سطر الأوامر
    python smart_dictionary.py --add "Hkstovy" --replace "History" --cat general

    # Correct text / تصحيح نص
    python smart_dictionary.py --correct "Patient Hkstovy: Daignosis of Fibrous elyspasi"

    # Search dictionary / البحث في القاموس
    python smart_dictionary.py --search "tumor"

    # List all categories / عرض جميع التصنيفات
    python smart_dictionary.py --list-categories

    # Export dictionary / تصدير القاموس
    python smart_dictionary.py --export custom_dict.json

    # Import dictionary / استيراد قاموس
    python smart_dictionary.py --import external_dict.json

    # Delete a term / حذف مصطلح
    python smart_dictionary.py --delete "Hkstovy"
"""

import json
import re
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

# ---- Default dictionary file path / مسار ملف القاموس الافتراضي ----
DEFAULT_DICT_PATH = Path("smart_medical_dictionary.json")

# ---- Supported categories / التصنيفات المدعومة ----
VALID_CATEGORIES = [
    "bone_tumors",      # أورام العظام
    "fractures",        # الكسور
    "medications",      # الأدوية
    "lab_values",       # نتائج المختبر
    "procedures",       # الإجراءات
    "anatomy",          # التشريح
    "diagnosis",        # التشخيص
    "general_clinical", # مصطلحات سريرية عامة
    "arabic_medical",   # مصطلحات طبية عربية
    "radiology",        # الأشعة
    "orthopedics",      # جراحة العظام
    "pathology",        # علم الأمراض
    "custom",           # مخصص
]


# ---- Built-in seed dictionary / القاموس المدمج الأولي ----

SEED_DICTIONARY = {
    "metadata": {
        "version": "1.0.0",
        "description": "Smart Medical Dictionary for Arabic/English OCR Correction",
        "description_ar": "قاموس طبي ذكي لتصحيح OCR العربي/الإنجليزي",
        "created": datetime.now().isoformat(),
        "total_entries": 0,
    },
    "categories": {
        "bone_tumors": {
            "display_name": "Bone Tumors / أورام العظام",
            "description": "Benign and malignant bone tumor terminology",
            "terms": {
                r"\bHkstovy\b": "History",
                r"\baPpslyai\b": "Physical",
                r"\bgslwigeociis\b": "Clinical",
                r"\bFibrous elyspasi\b": "Fibrous Dysplasia",
                r"\bosfochndonwwe\b": "Osteochondroma",
                r"\b5olifaty bons kysfe\b": "Solitary Bone Cyst",
                r"\bAnuerysm bonccge kyste\b": "Aneurysmal Bone Cyst",
                r"\bChenalroblasfa\b": "Chondrosarcoma",
                r"\bFibro AeVans\b": "Fibrosarcoma",
                r"\bchhovelnblasfana\b": "Chondroblastoma",
                r"\benchendrona\b": "Enchondroma",
                r"\bOsteob\(as}oa\b": "Osteoblastoma",
                r"\bfogMActn.*GiGain1cellTuwor\b": "Giant Cell Tumor",
                r"\bOsteosarcoma\b": "Osteosarcoma",
                r"\bEwing sarcoma\b": "Ewing Sarcoma",
                r"\bMultiple Myeloma\b": "Multiple Myeloma",
                r"\bLnkeciioa\b": "Infection",
                r"\bLefournel\b": "Letournel",
            }
        },
        "fractures": {
            "display_name": "Fractures / الكسور",
            "description": "Fracture types and terminology",
            "terms": {
                r"\bFemoral neck fx\b": "Femoral Neck Fracture",
                r"\bIntertrochanteric fx\b": "Intertrochanteric Fracture",
                r"\bSubtrochanteric fx\b": "Subtrochanteric Fracture",
                r"\bTibial plateau fx\b": "Tibial Plateau Fracture",
                r"\bCompression fx\b": "Compression Fracture",
                r"\bSprial fx\b": "Spiral Fracture",
                r"\bGreenstick fx\b": "Greenstick Fracture",
                r"\bPathologic fx\b": "Pathological Fracture",
                r"\bAveolar fx\b": "Alveolar Fracture",
            }
        },
        "medications": {
            "display_name": "Medications / الأدوية",
            "description": "Common medications with OCR-prone spellings",
            "terms": {
                r"\bParacetomal\b": "Paracetamol",
                r"\bIbuprofen\b": "Ibuprofen",
                r"\bAmoxicilin\b": "Amoxicillin",
                r"\bMetmorphin\b": "Metformin",
                r"\bAmlodipne\b": "Amlodipine",
                r"\bOmeprazol\b": "Omeprazole",
                r"\bCiprofloxain\b": "Ciprofloxacin",
                r"\bAzithromycn\b": "Azithromycin",
                r"\bDiclofenac\b": "Diclofenac",
                r"\bTramadlo\b": "Tramadol",
            }
        },
        "lab_values": {
            "display_name": "Lab Values / نتائج المختبر",
            "description": "Laboratory value abbreviations and corrections",
            "terms": {
                r"\bWBC\b": "WBC (White Blood Cell Count)",
                r"\bRBC\b": "RBC (Red Blood Cell Count)",
                r"\bHb\b": "Hb (Hemoglobin)",
                r"\bHct\b": "Hct (Hematocrit)",
                r"\bPLT\b": "PLT (Platelet Count)",
                r"\bESR\b": "ESR (Erythrocyte Sedimentation Rate)",
                r"\bCRP\b": "CRP (C-Reactive Protein)",
                r"\bALT\b": "ALT (Alanine Aminotransferase)",
                r"\bAST\b": "AST (Aspartate Aminotransferase)",
                r"\bBUN\b": "BUN (Blood Urea Nitrogen)",
                r"\bCreatnine\b": "Creatinine",
            }
        },
        "procedures": {
            "display_name": "Procedures / الإجراءات",
            "description": "Surgical and diagnostic procedure names",
            "terms": {
                r"\bORIF\b": "ORIF (Open Reduction Internal Fixation)",
                r"\bTKR\b": "TKR (Total Knee Replacement)",
                r"\bTHR\b": "THR (Total Hip Replacement)",
                r"\bArthoscopy\b": "Arthroscopy",
                r"\bLaminectom\b": "Laminectomy",
                r"\bDiscectom\b": "Discectomy",
                r"\bSpinal Fuson\b": "Spinal Fusion",
                r"\bBiopsy\b": "Biopsy",
                r"\bAspiration\b": "Aspiration",
                r"\bDebridment\b": "Debridement",
            }
        },
        "arabic_medical": {
            "display_name": "Arabic Medical / مصطلحات طبية عربية",
            "description": "Arabic medical term OCR corrections",
            "terms": {
                r'بون سكان': 'المسح العظمي',
                r'كيس عظمي وحيد': 'كيسة عظمية وحيدة',
                r'ورم حبيبي يوزيني': 'ورم حبيبي أيوزيني',
                r'تكلسات جانبية': 'تكلسات جانبية للعمود الفقري',
                r'كسر ضغط': 'كسر انضغاطي',
                r'التهاب مفاصل': 'التهاب المفاصل',
                r'ورم خبيث': 'ورم خبيث (سرطان)',
                r'ورم حميد': 'ورم حميد',
                r'فحص سريري': 'الفحص السريري',
                r'الأشعة السينية': 'صورة الأشعة السينية',
                r'الرنين المغناطيسي': 'الرنين المغناطيسي (MRI)',
            }
        },
        "radiology": {
            "display_name": "Radiology / الأشعة",
            "description": "Radiology and imaging terminology",
            "terms": {
                r"\bRadiograh\b": "Radiograph",
                r"\bX[ -]?ray\b": "X-Ray",
                r"\bMRI\b": "MRI (Magnetic Resonance Imaging)",
                r"\bCT[ -]?sacn\b": "CT Scan",
                r"\bUltrasund\b": "Ultrasound",
                r"\bDexa[ -]?scan\b": "DEXA Scan",
                r"\bBone scintigraf\b": "Bone Scintigraphy",
                r"\bPET[ -]?CT\b": "PET-CT",
                r"\bAngiograf\b": "Angiography",
                r'\bFluoroscopy\b': 'Fluoroscopy',
            }
        },
        "general_clinical": {
            "display_name": "General Clinical / مصطلحات سريرية عامة",
            "description": "Common clinical terms prone to OCR errors",
            "terms": {
                r'\bPatienf\b': 'Patient',
                r'\bDaignosis\b': 'Diagnosis',
                r'\bTreafment\b': 'Treafment',
                r'\bFolow[ -]?up\b': 'Follow-up',
                r'\bAdmisison\b': 'Admission',
                r'\bDischarege\b': 'Discharge',
                r'\bPrognosis\b': 'Prognosis',
                r'\bSymtoms\b': 'Symptoms',
                r'\bSigns\b': 'Signs',
                r'\bExaminaton\b': 'Examination',
                r'\bBlod\b': 'Blood',
                r'\bUirne\b': 'Urine',
                r'\bStool\b': 'Stool',
                r'\by\.?o\.?\s+(\d+)': r'year-old \1',
            }
        },
    }
}


class SmartMedicalDictionary:
    """
    Smart medical dictionary with auto-learning capabilities.
    قاموس طبي ذكي مع قدرات التعلم التلقائي.

    Manages a JSON-backed dictionary of regex pattern -> replacement pairs,
    organized by medical category. Supports adding, searching, deleting,
    and applying corrections to OCR text.
    """

    def __init__(self, dict_path: Optional[str] = None, auto_save: bool = True):
        """
        Initialize the dictionary manager.
        تهيئة مدير القاموس.

        Args:
            dict_path: Path to JSON dictionary file (default: smart_medical_dictionary.json)
                       مسار ملف القاموس بصيغة JSON
            auto_save: Automatically save changes to disk (default: True)
                       حفظ التغييرات تلقائياً على القرص
        """
        self.dict_path = Path(dict_path) if dict_path else DEFAULT_DICT_PATH
        self.auto_save = auto_save
        self._data = None

        # Load existing or initialize from seed
        if self.dict_path.exists():
            self._load()
        else:
            self._data = json.loads(json.dumps(SEED_DICTIONARY))
            self._update_metadata()
            if self.auto_save:
                self._save()
            print(f"[معلومات] Created new dictionary at: {self.dict_path}")

    def _load(self):
        """Load dictionary from JSON file. تحميل القاموس من ملف JSON."""
        try:
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            print(f"[معلومات] Loaded dictionary from: {self.dict_path}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"[خطأ] Failed to load dictionary: {e}")
            print("       Initializing with built-in seed dictionary...")
            self._data = json.loads(json.dumps(SEED_DICTIONARY))
            self._update_metadata()

    def _save(self):
        """Save dictionary to JSON file. حفظ القاموس في ملف JSON."""
        self._update_metadata()
        try:
            with open(self.dict_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[خطأ] Failed to save dictionary: {e}")

    def _update_metadata(self):
        """Update metadata with current statistics. تحديث البيانات الوصفية."""
        total = sum(
            len(cat_data.get("terms", {}))
            for cat_data in self._data.get("categories", {}).values()
        )
        self._data.setdefault("metadata", {})
        self._data["metadata"]["total_entries"] = total
        self._data["metadata"]["last_modified"] = datetime.now().isoformat()

    # ---- Core operations / العمليات الأساسية ----

    def add_term(self, pattern: str, replacement: str,
                 category: str = "custom") -> bool:
        """
        Add a new term to the dictionary.
        إضافة مصطلح جديد إلى القاموس.

        Args:
            pattern: Regex pattern for OCR error / نمط regex للخطأ
            replacement: Correct replacement text / النص الصحيح البديل
            category: Category name (default: custom) / اسم التصنيف

        Returns:
            True if added successfully / صحيح إذا تمت الإضافة بنجاح
        """
        if not pattern.strip() or not replacement.strip():
            print("[خطأ] Pattern and replacement cannot be empty")
            return False

        if category not in VALID_CATEGORIES:
            print(f"[خطأ] Invalid category: '{category}'")
            print(f"       Valid categories: {', '.join(VALID_CATEGORIES)}")
            return False

        # Validate regex
        try:
            re.compile(pattern)
        except re.error as e:
            print(f"[خطأ] Invalid regex pattern '{pattern}': {e}")
            return False

        # Initialize category if needed
        categories = self._data.setdefault("categories", {})
        if category not in categories:
            categories[category] = {
                "display_name": category.replace("_", " ").title(),
                "description": f"Custom category: {category}",
                "terms": {},
            }

        # Check if pattern already exists
        existing = categories[category]["terms"].get(pattern)
        if existing:
            print(f"[تحذير] Pattern '{pattern}' already exists in '{category}'")
            print(f"         Old value: {existing}")
            print(f"         Updating to: {replacement}")

        categories[category]["terms"][pattern] = replacement

        if self.auto_save:
            self._save()

        print(f"[تم] Added: '{pattern}' -> '{replacement}' "
              f"[{category}]")
        return True

    def delete_term(self, pattern: str,
                    category: Optional[str] = None) -> bool:
        """
        Delete a term from the dictionary.
        حذف مصطلح من القاموس.

        Args:
            pattern: Regex pattern to delete / نمط regex للحذف
            category: Category to search in (None = search all)
                      التصنيف للبحث فيه (بلا = البحث في الكل)

        Returns:
            True if deleted / صحيح إذا تم الحذف
        """
        categories = self._data.get("categories", {})
        found = False

        cats_to_search = {category} if category else set(categories.keys())

        for cat_name in cats_to_search:
            if cat_name in categories and pattern in categories[cat_name]["terms"]:
                old_val = categories[cat_name]["terms"].pop(pattern)
                found = True
                print(f"[تم] Deleted: '{pattern}' (was: '{old_val}') "
                      f"[{cat_name}]")

        if not found:
            print(f"[تحذير] Pattern '{pattern}' not found in dictionary")
            return False

        if self.auto_save:
            self._save()
        return True

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search dictionary for terms matching a query string.
        البحث في القاموس عن مصطلحات تطابق نص البحث.

        Args:
            query: Search string (matches patterns, replacements, and category names)
                   نص البحث

        Returns:
            List of matching entries with category info
            قائمة الإدخالات المطابقة مع معلومات التصنيف
        """
        results = []
        query_lower = query.lower()
        categories = self._data.get("categories", {})

        for cat_name, cat_data in categories.items():
            for pattern, replacement in cat_data.get("terms", {}).items():
                if (query_lower in pattern.lower() or
                        query_lower in replacement.lower() or
                        query_lower in cat_name.lower()):
                    results.append({
                        "category": cat_name,
                        "category_display": cat_data.get("display_name", cat_name),
                        "pattern": pattern,
                        "replacement": replacement,
                    })

        return results

    def correct_text(self, text: str,
                     categories: Optional[List[str]] = None) -> str:
        """
        Apply all dictionary corrections to text.
        تطبيق جميع تصحيحات القاموس على النص.

        Args:
            text: Input text to correct / نص مدخل للتصحيح
            categories: Optional list of categories to use (None = all)
                        قائمة اختيارية بالتصنيفات للاستخدام (بلا = الكل)

        Returns:
            Corrected text / نص مصحح
        """
        categories_data = self._data.get("categories", {})
        corrections_made = 0

        for cat_name, cat_data in categories_data.items():
            if categories and cat_name not in categories:
                continue
            for pattern, replacement in cat_data.get("terms", {}).items():
                try:
                    new_text = re.sub(
                        pattern, replacement, text, flags=re.IGNORECASE
                    )
                    if new_text != text:
                        corrections_made += 1
                        text = new_text
                except re.error:
                    # Skip invalid patterns silently during correction
                    pass

        if corrections_made > 0:
            print(f"[معلومات] Applied {corrections_made} correction(s)")

        return text

    def get_flat_dict(self) -> Dict[str, str]:
        """
        Get flat dictionary of all pattern -> replacement pairs.
        الحصول على قاموس مسطح لجميع أزواج نمط -> استبدال.

        Returns:
            Dict mapping patterns to replacements
        """
        flat = {}
        for cat_data in self._data.get("categories", {}).values():
            flat.update(cat_data.get("terms", {}))
        return flat

    def list_categories(self) -> Dict[str, Dict[str, Any]]:
        """
        List all categories with entry counts.
        عرض جميع التصنيفات مع عدد الإدخالات.

        Returns:
            Dict of category_name -> {display_name, count, description}
        """
        result = {}
        for cat_name, cat_data in self._data.get("categories", {}).items():
            result[cat_name] = {
                "display_name": cat_data.get("display_name", cat_name),
                "count": len(cat_data.get("terms", {})),
                "description": cat_data.get("description", ""),
            }
        return result

    def export_to(self, filepath: str):
        """
        Export dictionary to a JSON file.
        تصدير القاموس إلى ملف JSON.

        Args:
            filepath: Output file path / مسار ملف الإخراج
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

        print(f"[تم] Exported dictionary to: {filepath}")
        print(f"     Entries: {self._data['metadata']['total_entries']}")

    def import_from(self, filepath: str,
                    merge: bool = True):
        """
        Import dictionary from a JSON file.
        استيراد قاموس من ملف JSON.

        Args:
            filepath: Source JSON file path / مسار ملف JSON المصدر
            merge: If True, merge with existing entries. If False, replace all.
                   إذا صحيح، دمج مع الإدخالات الموجودة. إذا لا، استبدال الكل.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            print(f"[خطأ] Import file not found: {filepath}")
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[خطأ] Invalid JSON: {e}")
            return

        if not isinstance(imported, dict):
            print("[خطأ] Import file must contain a JSON object")
            return

        if not merge:
            self._data = imported
        else:
            # Merge categories
            imported_cats = imported.get("categories", {})
            self_cats = self._data.setdefault("categories", {})

            for cat_name, cat_data in imported_cats.items():
                if cat_name in self_cats:
                    merged_terms = {
                        **self_cats[cat_name].get("terms", {}),
                        **cat_data.get("terms", {}),
                    }
                    self_cats[cat_name]["terms"] = merged_terms
                else:
                    self_cats[cat_name] = cat_data

        if self.auto_save:
            self._save()

        print(f"[تم] Imported dictionary from: {filepath}")
        print(f"     Mode: {'merge' if merge else 'replace'}")
        print(f"     Total entries: {self._data['metadata']['total_entries']}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get dictionary statistics.
        الحصول على إحصائيات القاموس.

        Returns:
            Dict with statistics / قاموس بالإحصائيات
        """
        categories = self._data.get("categories", {})
        cat_stats = {
            name: len(data.get("terms", {}))
            for name, data in categories.items()
        }
        return {
            "total_entries": self._data.get("metadata", {}).get(
                "total_entries", 0
            ),
            "total_categories": len(categories),
            "categories": cat_stats,
            "dict_path": str(self.dict_path),
            "last_modified": self._data.get("metadata", {}).get(
                "last_modified", "unknown"
            ),
        }


# ---- Interactive CLI Mode / الوضع التفاعلي ----

def interactive_mode(dictionary: SmartMedicalDictionary):
    """
    Run interactive CLI for dictionary management.
    تشغيل واجهة سطر أوامر تفاعلية لإدارة القاموس.
    """
    print("\n" + "=" * 60)
    print("  Smart Medical Dictionary - Interactive Mode")
    print("  القاموس الطبي الذكي - الوضع التفاعلي")
    print("=" * 60)

    while True:
        print("\n" + "-" * 40)
        print("Commands / الأوامر:")
        print("  1. add      - Add a new term / إضافة مصطلح جديد")
        print("  2. delete   - Delete a term / حذف مصطلح")
        print("  3. search   - Search terms / البحث عن مصطلحات")
        print("  4. correct  - Correct text / تصحيح نص")
        print("  5. list     - List categories / عرض التصنيفات")
        print("  6. stats    - Show statistics / عرض الإحصائيات")
        print("  7. export   - Export dictionary / تصدير القاموس")
        print("  8. quit     - Exit / خروج")
        print("-" * 40)

        choice = input("\n> Enter command / أدخل الأمر: ").strip().lower()

        if choice in ('quit', 'exit', 'q', '8'):
            print("\n[خروج] Goodbye! مع السلامة!")
            break

        elif choice in ('add', '1'):
            print("\n--- Add New Term / إضافة مصطلح جديد ---")
            pattern = input("  Pattern (regex) / النمط: ").strip()
            replacement = input("  Replacement / البديل: ").strip()
            print(f"  Available categories / التصنيفات المتاحة:")
            print(f"    {', '.join(VALID_CATEGORIES)}")
            category = input(
                "  Category (default: custom) / التصنيف: "
            ).strip() or "custom"
            dictionary.add_term(pattern, replacement, category)

        elif choice in ('delete', '3'):  # Note: 'delete' starts with 'd', not '3'
            # Actually this is command 2 / هذا الأمر رقم 2
            pass  # handled below

        elif choice in ('del', 'delete', 'remove', '2'):
            pattern = input("  Pattern to delete / نمط للحذف: ").strip()
            cat = input(
                "  Category (leave blank for all) / التصنيف (فارغ = الكل): "
            ).strip() or None
            dictionary.delete_term(pattern, category)

        elif choice in ('search', 'find', '4'):
            query = input("  Search query / نص البحث: ").strip()
            if query:
                results = dictionary.search(query)
                if results:
                    print(f"\n  Found {len(results)} result(s):")
                    for i, r in enumerate(results, 1):
                        print(f"  {i}. [{r['category_display']}] "
                              f"'{r['pattern']}' -> '{r['replacement']}'")
                else:
                    print("  No results found / لا توجد نتائج")

        elif choice in ('correct', 'fix', '3'):
            text = input("  Text to correct / نص للتصحيح: ").strip()
            if text:
                corrected = dictionary.correct_text(text)
                print(f"\n  Original / الأصل:     {text}")
                print(f"  Corrected / المصحح:  {corrected}")

        elif choice in ('list', 'categories', '5'):
            cats = dictionary.list_categories()
            print(f"\n  Categories ({len(cats)}):")
            for name, info in cats.items():
                print(f"  - {info['display_name']} ({info['count']} terms)")

        elif choice in ('stats', 'statistics', '6'):
            stats = dictionary.get_stats()
            print(f"\n  Dictionary Statistics / إحصائيات القاموس:")
            print(f"  File: {stats['dict_path']}")
            print(f"  Last modified: {stats['last_modified']}")
            print(f"  Total entries: {stats['total_entries']}")
            print(f"  Categories: {stats['total_categories']}")
            for cat, count in stats['categories'].items():
                print(f"    - {cat}: {count}")

        elif choice in ('export', 'save', '7'):
            filepath = input(
                "  Export path (default: medical_dict_export.json): "
            ).strip() or "medical_dict_export.json"
            dictionary.export_to(filepath)

        else:
            print(f"  [خطأ] Unknown command: '{choice}'")


# ---- CLI Entry Point / نقطة دخول سطر الأوامر ----

def parse_args():
    """Parse command line arguments / تحليل معاملات سطر الأوامر"""
    parser = argparse.ArgumentParser(
        description='Smart Medical Dictionary with Auto-Learning\n'
                    'القاموس الطبي الذكي مع التعلم التلقائي',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--dict-path', '-f',
        type=str, default=None,
        help=f'Dictionary JSON file path (default: {DEFAULT_DICT_PATH})\n'
             f'مسار ملف القاموس JSON'
    )
    parser.add_argument(
        '--no-auto-save',
        action='store_true',
        help='Disable auto-save / تعطيل الحفظ التلقائي'
    )

    # Action arguments
    parser.add_argument(
        '--add',
        type=str, default=None, metavar='PATTERN',
        help='Add a new term pattern / إضافة نمط مصطلح جديد'
    )
    parser.add_argument(
        '--replace',
        type=str, default=None,
        help='Replacement text (used with --add) / نص البديل'
    )
    parser.add_argument(
        '--cat', '-c',
        type=str, default='custom',
        help='Category for --add (default: custom) / التصنيف'
    )
    parser.add_argument(
        '--delete',
        type=str, default=None, metavar='PATTERN',
        help='Delete a term by pattern / حذف مصطلح بالنمط'
    )
    parser.add_argument(
        '--search', '-s',
        type=str, default=None,
        help='Search dictionary / البحث في القاموس'
    )
    parser.add_argument(
        '--correct',
        type=str, default=None,
        help='Correct text using dictionary / تصحيح نص بالقاموس'
    )
    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='List all categories / عرض جميع التصنيفات'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show dictionary statistics / عرض إحصائيات القاموس'
    )
    parser.add_argument(
        '--export',
        type=str, default=None, metavar='FILE',
        help='Export dictionary to JSON file / تصدير القاموس'
    )
    parser.add_argument(
        '--import',
        type=str, default=None, metavar='FILE', dest='import_file',
        help='Import dictionary from JSON file / استيراد قاموس'
    )
    parser.add_argument(
        '--import-replace',
        action='store_true',
        help='Replace (not merge) when importing / استبدال بدل الدمج عند الاستيراد'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Launch interactive mode / تشغيل الوضع التفاعلي'
    )

    return parser.parse_args()


def main():
    """Main entry point for CLI usage."""
    args = parse_args()

    # Initialize dictionary
    dictionary = SmartMedicalDictionary(
        dict_path=args.dict_path,
        auto_save=not args.no_auto_save,
    )

    # If no action flags, enter interactive mode
    has_action = any([
        args.add, args.delete, args.search, args.correct,
        args.list_categories, args.stats, args.export, args.import_file,
    ])

    if not has_action or args.interactive:
        interactive_mode(dictionary)
        return

    # Handle individual CLI actions
    if args.add:
        if not args.replace:
            print("[خطأ] --replace is required with --add")
            print("       --replace مطلوب مع --add")
            sys.exit(1)
        dictionary.add_term(args.add, args.replace, args.cat)

    if args.delete:
        dictionary.delete_term(args.delete)

    if args.search:
        results = dictionary.search(args.search)
        if results:
            print(f"Found {len(results)} result(s) / {len(results)} نتيجة:")
            for i, r in enumerate(results, 1):
                print(f"  {i}. [{r['category_display']}] "
                      f"'{r['pattern']}' -> '{r['replacement']}'")
        else:
            print("No results found / لا توجد نتائج")

    if args.correct:
        corrected = dictionary.correct_text(args.correct)
        print(f"Original / الأصل:     {args.correct}")
        print(f"Corrected / المصحح:  {corrected}")

    if args.list_categories:
        cats = dictionary.list_categories()
        print(f"\nCategories ({len(cats)}):")
        for name, info in sorted(cats.items()):
            print(f"  {name:25s} | {info['display_name']:40s} | {info['count']} terms")

    if args.stats:
        stats = dictionary.get_stats()
        print(f"\nDictionary Statistics / إحصائيات القاموس:")
        print(f"  File / الملف:          {stats['dict_path']}")
        print(f"  Last modified / آخر تعديل: {stats['last_modified']}")
        print(f"  Total entries / الإدخالات الكلية: {stats['total_entries']}")
        print(f"  Categories / التصنيفات: {stats['total_categories']}")
        for cat, count in stats['categories'].items():
            print(f"    - {cat}: {count}")

    if args.export:
        dictionary.export_to(args.export)

    if args.import_file:
        dictionary.import_from(args.import_file, merge=not args.import_replace)


if __name__ == "__main__":
    main()
