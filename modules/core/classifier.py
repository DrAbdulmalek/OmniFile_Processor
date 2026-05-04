"""
مصنف المحتوى الطبي والعلمي (Medical & Scientific Content Classifier)
=====================================================================
نظام تصنيف احتمالي متخصص في المحتوى الطبي والعلمي.

التصنيفات المدعومة:
- orthopedic: جراحة العظام والمفاصل
- cardiology: أمراض القلب والأوعية الدموية
- neurology: الأمراض العصبية
- general_surgery: الجراحة العامة
- radiology: الأشعة والتصوير الطبي
- pathology: علم الأمراض
- pharmacology: علم الأدوية
- research: أبحاث علمية
- medical_admin: إدارة طبية وتقارير
- engineering: هندسة وتقنية
- general: عام (غير مصنف)

الاستخدام:
    from modules.core.classifier import MedicalClassifier
    clf = MedicalClassifier()
    result = clf.classify("المريض يعاني من كسر في عظم الفخذ")
"""

import json
import logging
import os
import re
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class MedicalClassifier:
    """
    مصنف المحتوى الطبي والعلمي — يعتمد على الكلمات المفتاحية مع نظام أوزان احتمالية.

    كل تصنيف له كلمات مفتاحية بأوزان مختلفة:
    - weight=3: كلمات حاسمة (تحدد التصنيف بقوة)
    - weight=2: كلمات مهمة (تدعم التصنيف)
    - weight=1: كلمات مساعدة (تزيد الثقة)
    """

    # التصنيفات الافتراضية مع الكلمات المفتاحية وأوزانها
    _DEFAULT_CATEGORIES: Dict[str, Dict[str, List[str]]] = {
        "orthopedic": {
            "critical": [
                "كسر", " fracture", "عظم", " bone", "مفصل", " joint",
                "عمود فقري", " spine", "فقرات", " vertebrae",
                "الركبة", " knee", "الحوض", " pelvis",
                "الكتف", " shoulder", "الكاحل", " ankle",
                "الرسغ", " wrist", "المرفق", " elbow",
                "عظم العضد", " humerus", "عظم الساعد", " forearm",
                "الساق", " leg", "الفخذ", " femur",
                "الظنبوب", " tibia", "الشظية", " fibula",
                "الترقوة", " clavicle", "ضلع", " rib",
                "تثبيت", " fixation", "مسمار", " screw",
                "صفيحة", " plate", "سلك", " wire",
                "مسامير", " pins", "دعامة", " implant",
                "بدلة مفصل", " prosthesis", "مفصل صناعي",
                "خشونة", " osteoarthritis", "التهاب المفاصل", " arthritis",
                "انزلاق غضروفي", " disc herniation", "ديسك",
                "التهاب", " tendonitis", "وترة", " tendon",
                "رباط", " ligament", "غضروف", " cartilage",
                "تمزق", " tear", "تمزق الرباط الصليبي", " ACL",
                "إصابة رياضية", " sports injury",
                "استئصال", " excision", "تنظير", " arthroscopy",
                "تقويم", " orthopedic", "جراحة عظام", " orthopaedic",
                "شبكة عظمية", " bone graft", "زراعة عظم",
                "تقويم عظام", " osteotomy", "ربط", " fusion",
                "استبدال المفصل", " joint replacement", "arthroplasty",
                "التهاب العظم والنقي", " osteomyelitis",
                "التهاب المفاصل الروماتويدي", " rheumatoid",
                "النقرس", " gout", "هشاشة العظام", " osteoporosis",
                "انزلاق", " spondylolisthesis", "جنف", " scoliosis",
                "تحدب", " kyphosis", "قدم مسطحة", " flat foot",
                "التهاب الكيس", " bursitis", "التهاب الجراب",
            ],
            "important": [
                "مريض", " patient", "عملية", " surgery", "جراحة",
                "تشخيص", " diagnosis", "علاج", " treatment",
                "أشعة سينية", " x-ray", "رنين مغناطيسي", " MRI",
                "مقطعية", " CT scan", "تصوير", " imaging",
                "تخدير", " anesthesia", "مضاد حيوي", " antibiotic",
                "مستشفى", " hospital", "عيادة", " clinic",
                "جبس", " cast", "حزام", " brace", "رباط طبي",
                "تأهيل", " rehabilitation", "فيزيوترابي", " physiotherapy",
                "علاج طبيعي", " physical therapy",
            ],
            "supporting": [
                "دراسة", " study", "بحث", " research", "تحليل",
                "متابعة", " follow-up", "مراجعة", " review",
                "حالة", " case", "تقرير", " report",
                "توصيات", " recommendations", "خطة علاجية",
            ],
        },
        "cardiology": {
            "critical": [
                "القلب", " heart", "شريان", " artery", "وريد", " vein",
                "أزمة قلبية", " myocardial infarction", "سكتة قلبية",
                "ذبحة", " angina", "قصور قلبي", " heart failure",
                "صمام", " valve", "رجفان أذيني", " atrial fibrillation",
                "تصلب شرايين", " atherosclerosis", "جلطة", " clot",
                "خثرة", " thrombus", "انسداد", " occlusion",
                "ضغط الدم", " blood pressure", "الكولسترول", " cholesterol",
                "ترقق الشرايين", "aneurysm", "قسطرة", " catheter",
                "دعامة قلبية", " stent", "مجازة", " bypass",
                "نظم قلبي", " pacemaker", "صدمة قلبية", " cardiac shock",
                "التهاب التامور", " pericarditis", "التهاب عضلة القلب", " myocarditis",
            ],
            "important": [
                "تخطيط قلب", " ECG", "إيكو قلب", " echocardiography",
                "أشعة قلب", " coronary angiography",
                "مريض", " patient", "عملية", " surgery",
                "علاج", " treatment", "تشخيص", " diagnosis",
            ],
            "supporting": [
                "متابعة", " follow-up", "تقرير", " report",
                "خطر", " risk", "مضاعفات", " complications",
            ],
        },
        "neurology": {
            "critical": [
                "الجهاز العصبي", " nervous system", "الدماغ", " brain",
                "الحبل الشوكي", " spinal cord", "عصب", " nerve",
                "صرع", " epilepsy", "تصلب متعدد", " multiple sclerosis",
                "باركنسون", " Parkinson", "زهايمر", " Alzheimer",
                "سكتة دماغية", " stroke", "شلل", " paralysis",
                "ألم عصبي", " neuropathy", "صداع نصفي", " migraine",
                "ورم دماغي", " brain tumor", "التهاب السحايا", " meningitis",
                "اعتلال الأعصاب", " neuropathy", "ضمور عضلي", " muscular dystrophy",
            ],
            "important": [
                "تشخيص عصبي", " neurological diagnosis",
                "رنين مغناطيسي دماغي", " brain MRI",
                "تخطيط كهربائي", " EEG", "علاج", " treatment",
            ],
            "supporting": [
                "متابعة", " follow-up", "تقرير", " report",
                "حالة", " case", "بحث", " research",
            ],
        },
        "general_surgery": {
            "critical": [
                "استئصال", " excision", "appendectomy", "استئصال زائدة",
                "استئصال مرارة", " cholecystectomy", "فتق", " hernia",
                "جراحة", " surgery", "عملية جراحية", " surgical operation",
                "شق", " incision", "غلق", " closure", "خياطة", " suture",
                "تنظير", " laparoscopy", "منظار البطن",
                "استئصال طحال", " splenectomy",
                "استئصال غدة", " gland excision", "درن", " thyroid",
                "استئصال ثدي", " mastectomy",
            ],
            "important": [
                "مريض", " patient", "تخدير", " anesthesia",
                "مضاد حيوي", " antibiotic", "عناية مركزة", " ICU",
                "مستشفى", " hospital", "تعقيم", " sterilization",
            ],
            "supporting": [
                "تقرير", " report", "متابعة", " follow-up",
                "مضاعفات", " complications", "تشخيص", " diagnosis",
            ],
        },
        "radiology": {
            "critical": [
                "أشعة", " radiology", "x-ray", "تصوير طبي",
                "رنين مغناطيسي", " MRI", "مقطعية", " CT",
                "سونار", " ultrasound", "موجات فوق صوتية",
                "أشعة مقطعية", " CT scan", "تصوير وعائي", " angiography",
                "تصوير الصدر", " chest imaging", "ماموجرام", " mammogram",
                "تصوير نخاعي", " myelography", "بيتيد", " PET scan",
                "فلوروسكوبي", " fluoroscopy", "ديكسا", " DEXA",
            ],
            "important": [
                "صورة شعاعية", " radiograph", "تقرير أشعة",
                "ظل", " opacity", "ارتشاح", " infiltration",
                "ورم", " tumor", "كتلة", " mass", "آفة", " lesion",
            ],
            "supporting": [
                "تشخيص", " diagnosis", "مقارنة", " comparison",
                "توصيات", " recommendations", "متابعة", " follow-up",
            ],
        },
        "pathology": {
            "critical": [
                "علم الأمراض", " pathology", "فحص نسيجي", " biopsy",
                "خزعة", " biopsy", "فحص مجهري", " microscopic",
                "خلايا سرطانية", " cancer cells", "ورم خبيث", " malignant",
                "ورم حميد", " benign", "سرطان", " cancer",
                "نسيج", " tissue", "خلية", " cell",
                "درجة ورمية", " tumor grade", "مرحلة", " stage",
                "انتشار", " metastasis", "غدة لمفاوية", " lymph node",
                "نتائج فحص", " lab results", "تحليل مخبري", " lab analysis",
            ],
            "important": [
                "تشخيص نهائي", " definitive diagnosis",
                "تقرير مرضي", " pathology report",
                "ملون هيماتوكسيلين", " H&E stain",
            ],
            "supporting": [
                "توصيات", " recommendations", "متابعة", " follow-up",
                "دراسة", " study", "بحث", " research",
            ],
        },
        "pharmacology": {
            "critical": [
                "دواء", " drug", "medicine", "عقار", " pharmaceutical",
                "جرعة", " dose", "dosage", "تركيبة", " formulation",
                "تأثير جانبي", " side effect", "تفاعل دوائي", " drug interaction",
                "مضاد حيوي", " antibiotic", "مسكن", " analgesic",
                "مضاد التهاب", " anti-inflammatory", "كورتيزون", " corticosteroid",
                "أدوية القلب", " cardiac drugs", "أدوية الضغط", " antihypertensive",
                "سيولة الدم", " anticoagulant", "أدوية السكري", " antidiabetic",
                "علاج كيميائي", " chemotherapy", "إشعاعي", " radiotherapy",
                "دراسة سريرية", " clinical trial",
            ],
            "important": [
                "صيدلية", " pharmacy", "وصفة طبية", " prescription",
                "موانع استعمال", " contraindication", "تحذير", " warning",
            ],
            "supporting": [
                "تعليمات", " instructions", "معلومات", " information",
                "بحث", " research", "دراسة", " study",
            ],
        },
        "research": {
            "critical": [
                "فرضية", " hypothesis", "منهجية", " methodology",
                "عينة", " sample", "متغير", " variable",
                "دلالة إحصائية", " statistical significance",
                "p-value", "confidence interval", "فترة ثقة",
                "انحراف معياري", " standard deviation",
                "تحليل انحدار", " regression analysis",
                "مجلة علمية", " journal", "نشر", " publication",
                "مراجعة الأقران", " peer review", "مستخلص", " abstract",
                "مرجع", " reference", "استشهاد", " citation",
            ],
            "important": [
                "بحث", " research", "study", "تحليل", " analysis",
                "نتائج", " results", "استنتاج", " conclusion",
                "مناقشة", " discussion", "مقدمة", " introduction",
            ],
            "supporting": [
                "توصيات", " recommendations", "حدود الدراسة", " limitations",
                "عمل مستقبلي", " future work", "شكر وتقدير", " acknowledgments",
            ],
        },
        "engineering": {
            "critical": [
                "خوارزمية", " algorithm", "نظام", " system",
                "برمجة", " programming", "شبكة عصبية", " neural network",
                "تعلم عميق", " deep learning", "تعلم آلي", " machine learning",
                "ذكاء اصطناعي", " artificial intelligence",
                "واجهة", " interface", "تطبيق", " application",
                "قاعدة بيانات", " database", "سيرفر", " server",
                "API", "endpoint", "إطار عمل", " framework",
                "نموذج", " model", "تدريب", " training",
            ],
            "important": [
                "Python", "JavaScript", "React", "Node.js",
                "Docker", "Kubernetes", "Git", "Linux",
                "تصميم", " design", "بنية", " architecture",
                "أداء", " performance", "تحسين", " optimization",
            ],
            "supporting": [
                "كود", " code", "تطوير", " development",
                "اختبار", " testing", "نشر", " deployment",
            ],
        },
        "medical_admin": {
            "critical": [
                "سجل طبي", " medical record", "تقرير طبي", " medical report",
                "إذن دخول", " admission", "خروج", " discharge",
                "إحالة", " referral", "تحويل", " transfer",
                "تأمين طبي", " health insurance", "فاتورة", " bill",
                "موعد", " appointment", "عيادة", " clinic",
                "كشف", " examination", "فحص سريري", " clinical examination",
                "السوابق المرضية", " medical history", "التاريخ المرضي",
            ],
            "important": [
                "مريض", " patient", "طبيب", " doctor", "physician",
                "تمريض", " nursing", "مستشفى", " hospital",
                "قسم", " department", "جناح", " ward",
            ],
            "supporting": [
                "ملاحظات", " notes", "متابعة", " follow-up",
                "تعليمات", " instructions", "توقيع", " signature",
            ],
        },
    }

    def __init__(self, lexicon_path: Optional[str] = None):
        """
        تهيئة مصنف المحتوى الطبي.

        Args:
            lexicon_path: مسار ملف المعجم الإضافي (JSON)
        """
        self.categories: Dict[str, Dict[str, List[str]]] = {}

        # تحميل التصنيفات الافتراضية
        for cat, data in self._DEFAULT_CATEGORIES.items():
            self.categories[cat] = {
                "critical": list(data.get("critical", [])),
                "important": list(data.get("important", [])),
                "supporting": list(data.get("supporting", [])),
            }

        # تحميل المعجم الإضافي إذا وُجد
        if lexicon_path and os.path.exists(lexicon_path):
            self._load_lexicon(lexicon_path)

        # تحميل المعجم الجراحي الافتراضي
        default_lexicon = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "ortho_lexicon.json"
        )
        if os.path.exists(default_lexicon):
            self._load_lexicon(default_lexicon)

        # تجميع أنماط regex لكل فئة
        self._patterns: Dict[str, Dict[str, List[re.Pattern]]] = {}
        self._compile_patterns()

        logger.info("تم تهيئة مصنف المحتوى الطبي (%d تصنيف)", len(self.categories))

    def _load_lexicon(self, path: str):
        """تحميل معجم إضافي من ملف JSON."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                for category, keywords in data.items():
                    if category not in self.categories:
                        self.categories[category] = {
                            "critical": [], "important": [], "supporting": []
                        }
                    if isinstance(keywords, list):
                        self.categories[category]["critical"].extend(keywords)
                    elif isinstance(keywords, dict):
                        for level, words in keywords.items():
                            if level in self.categories[category]:
                                self.categories[category][level].extend(words)

            logger.info("تم تحميل المعجم الإضافي: %s", path)
        except Exception as e:
            logger.warning("فشل تحميل المعجم %s: %s", path, e)

    def _compile_patterns(self):
        """تحويل الكلمات المفتاحية إلى أنماط regex."""
        for category, levels in self.categories.items():
            self._patterns[category] = {}
            for level, keywords in levels.items():
                patterns = []
                for kw in keywords:
                    try:
                        patterns.append(re.compile(re.escape(kw), re.IGNORECASE))
                    except re.error:
                        continue
                self._patterns[category][level] = patterns

    def classify(self, text: str) -> Dict[str, Any]:
        """
        تصنيف النص إلى فئة طبية/علمية.

        Args:
            text: النص المراد تصنيفه

        Returns:
            قاموس يحتوي على:
                - category: الفئة الأساسية
                - confidence: مستوى الثقة (0-1)
                - scores: درجات جميع الفئات
                - keywords_found: الكلمات المفتاحية المكتشفة
                - top_keywords: أهم الكلمات المكتشفة
        """
        if not text or not text.strip():
            return {
                "category": "general",
                "confidence": 0.0,
                "scores": {},
                "keywords_found": {},
                "top_keywords": [],
            }

        text_lower = text.lower()
        scores: Dict[str, float] = {}
        found_keywords: Dict[str, List[str]] = {}

        # الأوزان لكل مستوى أهمية
        weights = {"critical": 3.0, "important": 2.0, "supporting": 1.0}

        for category, levels in self._patterns.items():
            cat_score = 0.0
            cat_keywords: List[str] = []

            for level, patterns in levels.items():
                for pattern in patterns:
                    matches = pattern.findall(text_lower)
                    if matches:
                        weight = weights.get(level, 1.0)
                        cat_score += len(matches) * weight
                        cat_keywords.append(pattern.pattern)

            if cat_score > 0:
                scores[category] = cat_score
                found_keywords[category] = cat_keywords

        if not scores:
            return {
                "category": "general",
                "confidence": 0.0,
                "scores": {},
                "keywords_found": {},
                "top_keywords": [],
            }

        # تطبيع الدرجات
        max_score = max(scores.values())
        normalized = {
            k: round(v / max_score, 4) for k, v in scores.items()
        }

        # اختيار الفئة الأعلى
        top_category = max(normalized, key=normalized.get)
        top_confidence = normalized[top_category]

        # أعلى 10 كلمات مفتاحية
        top_keywords = []
        if top_category in found_keywords:
            top_keywords = found_keywords[top_category][:10]

        return {
            "category": top_category,
            "confidence": min(round(top_confidence, 4), 1.0),
            "scores": normalized,
            "keywords_found": found_keywords,
            "top_keywords": top_keywords,
        }

    def classify_with_fallback(
        self,
        text: str,
        min_confidence: float = 0.15
    ) -> Dict[str, Any]:
        """
        تصنيف مع مستوى ثقة أدنى. إذا كان أقل من الحد، يُصنف كـ "general".

        Args:
            text: النص المراد تصنيفه
            min_confidence: الحد الأدنى للثقة

        Returns:
            نتيجة التصنيف
        """
        result = self.classify(text)
        if result["confidence"] < min_confidence:
            result["category"] = "general"
        return result

    def get_categories(self) -> List[str]:
        """عرض قائمة التصنيفات المتاحة."""
        return list(self.categories.keys()) + ["general"]

    def add_category(
        self,
        category: str,
        critical: List[str] = None,
        important: List[str] = None,
        supporting: List[str] = None
    ):
        """
        إضافة تصنيف جديد.

        Args:
            category: اسم التصنيف
            critical: كلمات حاسمة (وزن 3)
            important: كلمات مهمة (وزن 2)
            supporting: كلمات مساعدة (وزن 1)
        """
        self.categories[category] = {
            "critical": critical or [],
            "important": important or [],
            "supporting": supporting or [],
        }
        # إعادة تجميع الأنماط
        self._patterns[category] = {}
        for level, keywords in self.categories[category].items():
            patterns = []
            for kw in keywords:
                try:
                    patterns.append(re.compile(re.escape(kw), re.IGNORECASE))
                except re.error:
                    continue
            self._patterns[category][level] = patterns
        logger.info("تمت إضافة تصنيف جديد: %s", category)

    def organize_files(
        self,
        files: List[Dict[str, str]],
        base_folder: str,
        move_files: bool = False
    ) -> Dict[str, List[str]]:
        """
        تنظيم الملفات في مجلدات حسب التصنيف.

        Args:
            files: قائمة قواميس {path: مسار, text: نص مستخرج}
            base_folder: المجلد الأساسي
            move_files: نقل الملفات (True) أو نسخها (False)

        Returns:
            قاموس {تصنيف: [مسارات الملفات]}
        """
        import shutil
        organized: Dict[str, List[str]] = {}

        for file_info in files:
            filepath = file_info.get("path", "")
            text = file_info.get("text", "")

            if not filepath or not text:
                continue

            result = self.classify(text)
            category = result["category"]

            target_dir = os.path.join(base_folder, category)
            os.makedirs(target_dir, exist_ok=True)

            filename = os.path.basename(filepath)
            target_path = os.path.join(target_dir, filename)

            try:
                if move_files:
                    shutil.move(filepath, target_path)
                else:
                    shutil.copy2(filepath, target_path)

                if category not in organized:
                    organized[category] = []
                organized[category].append(target_path)
            except Exception as e:
                logger.error("خطأ في تنظيم %s: %s", filename, e)

        return organized
