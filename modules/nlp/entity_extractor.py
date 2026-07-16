"""
مستخرج الكيانات المسماة (Named Entity Extractor)
===================================================
يستخرج الكيانات المسماة من النصوص العربية: أشخاص، مؤسسات، أماكن، تواريخ.
يدعم الاستخراج بالأنماط والكلمات المفتاحية (بدون نموذج) أو بنموذج AraBERT NER.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    مستخرج الكيانات المسماة — يستخرج الأشخاص والمؤسسات والأماكن والتواريخ من النصوص.

    أنواع الكيانات المدعومة:
        - PER: شخص (شخص، أسماء أشخاص)
        - ORG: مؤسسة (شركات، جامعات، وزارات)
        - LOC: موقع (مدن، دول، أماكن)
        - DATE: تاريخ (تواريخ، فترات زمنية)

    الخصائص:
        model_name (str, optional): اسم نموذج NER.
        device (str): الجهاز المستخدم.
    """

    # ------------------------------------------------------------------
    # أنماط الكيانات — الأشخاص (PER)
    # ------------------------------------------------------------------
    _PERSON_PREFIXES: list[str] = [
        "السيد", "السيدة", "الأستاذ", "الأستاذة", "الدكتور",
        "الشيخ", "السيد", "المهندس", "القاضي", "الوزير",
        "الأمير", "الملك", "الرئيس", "المدير", "البروفيسور",
        "أ.د", "د.", "م.", "أ.",
    ]

    _KNOWN_PERSONS: list[str] = [
        "محمد", "أحمد", "علي", "حسن", "حسين", "إبراهيم", "يوسف",
        "عمر", "خالد", "عبدالله", "سعود", "فيصل", "ناصر", "سلطان",
        "فاطمة", "خديجة", "عائشة", "مريم", "سارة", "نورة", "هند",
        "محمد رسول الله", "أبو بكر", "عمر بن الخطاب", "عثمان بن عفان",
        "علي بن أبي طالب",
    ]

    # ------------------------------------------------------------------
    # أنماط الكيانات — المؤسسات (ORG)
    # ------------------------------------------------------------------
    _ORG_SUFFIXES: list[str] = [
        "شركة", "مؤسسة", "جامعة", "وزارة", "بنك", "مستشفى",
        "مجلس", "هيئة", "جمعية", "نادي", "معهد", "مختبر",
        "منظمة", "اتحاد", "مكتبة", "متحف", "مسجد",
    ]

    _KNOWN_ORGS: list[str] = [
        "الأمم المتحدة", "جامعة الدول العربية", "منظمة التعاون",
        "أوبك", "ناتو", "اليونسكو", "منظمة الصحة العالمية",
        "صندوق النقد الدولي", "البنك الدولي",
    ]

    # ------------------------------------------------------------------
    # أنماط الكيانات — المواقع (LOC)
    # ------------------------------------------------------------------
    _LOC_SUFFIXES: list[str] = [
        "مدينة", "قرية", "حي", "شارع", "طريق", "ميناء",
        "مطار", "محافظة", "إقليم", "ولاية", "منطقة",
    ]

    _KNOWN_LOCATIONS: list[str] = [
        "الرياض", "مكة", "المدينة", "جدة", "الدمام", "القاهرة",
        "دمشق", "بغداد", "بيروت", "عمان", "الدوحة", "الكويت",
        "المغرب", "تونس", "الجزائر", "السودان", "ليبيا", "اليمن",
        "فلسطين", "الأردن", "الإمارات", "عمان", "البحرين",
        "مصر", "السعودية", "تركيا", "إيران", "العراق", "سوريا",
        "أفغانستان", "باكستان", "الهند", "الصين", "اليابان",
        "أمريكا", "بريطانيا", "فرنسا", "ألمانيا", "إيطاليا",
        "إسبانيا", "روسيا", "كندا", "أستراليا", "البرازيل",
        "أبوظبي", "دبي", "Sharjah", "Ajman",
    ]

    # ------------------------------------------------------------------
    # أنماط الكيانات — التواريخ (DATE)
    # ------------------------------------------------------------------
    _DATE_PATTERNS: list[str] = [
        # هجري: يوم شهر سنة هـ
        # ملاحظة: استخدام [\u0647\u0640]? بدلاً من هـ? لتجنب مشكلة
        # خاصية tatweel في regex مع أنماط Unicode الطويلة
        r"\d{1,2}\s+(يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s+\d{4}\s*[\u0647\u0640]?",
        # ميلادي: يوم/شهر/سنة
        r"\d{1,2}/\d{1,2}/\d{2,4}",
        # سنة بالكلمات
        r"(?:عام|سنة)\s+\d{4}",
        # القرن
        r"القرن\s+(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر"
        r"|الحادي عشر|الثاني عشر|الثالث عشر|الرابع عشر|الخامس عشر|السادس عشر"
        r"|السابع عشر|الثامن عشر|التاسع عشر|العشرين|الواحد والعشرين|الثاني والعشرين)",
        # اليوم / الشهر / السنة
        r"(?:اليوم|الغد|أمس|بالأمس)",
        r"(?:هذا الشهر|الشهر الماضي|الشهر القادم|هذه السنة|السنة الماضية|السنة القادمة)",
    ]

    # كلمات عربية تُستخدم كحدود للأسماء (توقف التوسيع)
    _ARABIC_STOPWORDS: frozenset[str] = frozenset([
        # حروف جر
        "في", "من", "إلى", "على", "عن", "مع", "ب", "ل", "ك",
        # أسماء إشارة وموصولة
        "هذا", "هذه", "ذلك", "تلك", "الذي", "التي", "الذين",
        "اللاتي", "اللواتي", "اللذين", "اللتين",
        # أفعال شائعة
        "كان", "كانت", "يكون", "يوم", "أمس", "غدا",
        "قال", "قالت", "ذهب", "جاء", "زار", "سافر",
        "عمل", "يعمل", "درس", "يلتقي", "التقى", "يتم",
        # حروف عطف وربط
        "ثم", "أو", "و", "ف", "حتى", "بعد", "قبل",
        "بين", "عند", "منذ", "خلال", "عبر", "ضد",
        # أدوات نفي واستفهام
        "لا", "لم", "لن", "ما", "أن", "إن", "هل", "أم",
        "بل", "لكن", "غير", "قد", "سوف", "لقد",
        # أسماء مكان (تُستخدم كفواصل بين الكيانات)
        "مدينة", "قرية", "حي", "شارع", "طريق", "منطقة",
        # كلمات دينية
        "بسم", "الله", "الرحمن", "الرحيم", "الحمد", "لله",
        "سبحان", "والصلاة", "والسلام", "رسول",
        # أخرى
        "حول", "دون", "ذات", "ذو", "ذي",
        "حيث", "كيف", "متى", "أين", "لماذا", "أي",
        "هو", "هي", "هم", "نحن", "أنا", "كل", "بعض",
    ])

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: str = "cpu",
    ) -> None:
        """
        تهيئة مستخرج الكيانات المسماة.

        المعاملات:
            model_name: اسم نموذج NER (اختياري).
                       مثال: "UBC-NLP/ARBERT"
            device: الجهاز المستخدم ('cpu' أو 'cuda').
        """
        self.model_name = model_name
        self.device = device
        self._pipeline = None
        self._model_available = False
        self._tokenizer = None

        # تجميع أنماط التواريخ
        self._compiled_date_patterns: list[re.Pattern] = []
        for pat in self._DATE_PATTERNS:
            try:
                self._compiled_date_patterns.append(re.compile(pat, re.IGNORECASE))
            except re.error:
                logger.debug("نمط تاريخ غير صالح: %s", pat)

        # محاولة تحميل النموذج
        if model_name:
            self._try_load_model()

    def _try_load_model(self) -> None:
        """محاولة تحميل نموذج NER من HuggingFace."""
        try:
            from transformers import pipeline  # type: ignore

            logger.info("جاري تحميل نموذج NER: %s ...", self.model_name)
            self._pipeline = pipeline(
                "ner",
                model=self.model_name,
                device=self.device,
                aggregation_strategy="simple",
            )
            self._model_available = True
            logger.info("تم تحميل نموذج NER بنجاح")
        except ImportError:
            logger.warning(
                "مكتبة transformers غير مثبتة. سيتم الاعتماد على الأنماط فقط. "
                "pip install transformers torch"
            )
        except Exception as e:
            logger.warning("فشل تحميل نموذج NER '%s': %s", self.model_name, e)

    @staticmethod
    def _trim_entity(entity_text: str, stopwords: frozenset[str]) -> str:
        """
        قص الكيان من النهاية عند كلمات التوقف.

        المعاملات:
            entity_text: نص الكيان الخام.
            stopwords: مجموعة كلمات التوقف.

        العائد:
            النص المقصوص.
        """
        words = entity_text.strip().split()
        while len(words) > 1 and words[-1] in stopwords:
            words.pop()
        return " ".join(words)

    # ------------------------------------------------------------------
    # استخراج بالأنماط (يعمل دائماً)
    # ------------------------------------------------------------------
    def _extract_dates(self, text: str) -> list[dict]:
        """
        استخراج التواريخ من النص.

        المعاملات:
            text: النص المراد استخراج التواريخ منه.

        العائد:
            قائمة بقواميس الكيانات.
        """
        entities: list[dict] = []
        seen_spans: set[tuple[int, int]] = set()

        for pattern in self._compiled_date_patterns:
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span not in seen_spans:
                    seen_spans.add(span)
                    entities.append({
                        "entity": match.group().strip(),
                        "type": "DATE",
                        "start": match.start(),
                        "end": match.end(),
                    })

        return entities

    def _extract_locations(self, text: str) -> list[dict]:
        """
        استخراج المواقع من النص.

        المعاملات:
            text: النص المراد استخراج المواقع منه.

        العائد:
            قائمة بقواميس الكيانات.
        """
        entities: list[dict] = []
        seen_spans: set[tuple[int, int]] = set()

        # البحث عن مواقع معروفة
        for loc in self._KNOWN_LOCATIONS:
            for match in re.finditer(re.escape(loc), text, re.IGNORECASE):
                span = (match.start(), match.end())
                if span not in seen_spans:
                    seen_spans.add(span)
                    entities.append({
                        "entity": match.group(),
                        "type": "LOC",
                        "start": match.start(),
                        "end": match.end(),
                    })

        # البحث عن كلمات موقع متبوعة باسم
        for suffix in self._LOC_SUFFIXES:
            # نمط: كلمة موقع متبوعة باسم عربي (حد أقصى كلمتين)
            pattern = re.compile(
                rf"(?:{re.escape(suffix)})\s+[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?"
            )
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span not in seen_spans:
                    trimmed = self._trim_entity(match.group(), self._ARABIC_STOPWORDS)
                    seen_spans.add(span)
                    entities.append({
                        "entity": trimmed,
                        "type": "LOC",
                        "start": match.start(),
                        "end": match.start() + len(trimmed),
                    })

        return entities

    def _extract_organizations(self, text: str) -> list[dict]:
        """
        استخراج المؤسسات من النص.

        المعاملات:
            text: النص المراد استخراج المؤسسات منه.

        العائد:
            قائمة بقواميس الكيانات.
        """
        entities: list[dict] = []
        seen_spans: set[tuple[int, int]] = set()

        # البحث عن مؤسسات معروفة
        for org in self._KNOWN_ORGS:
            for match in re.finditer(re.escape(org), text, re.IGNORECASE):
                span = (match.start(), match.end())
                if span not in seen_spans:
                    seen_spans.add(span)
                    entities.append({
                        "entity": match.group(),
                        "type": "ORG",
                        "start": match.start(),
                        "end": match.end(),
                    })

        # البحث عن كلمات مؤسسة متبوعة باسم
        for suffix in self._ORG_SUFFIXES:
            # نمط: كلمة مؤسسة متبوعة باسم عربي (حد أقصى 3 كلمات)
            pattern = re.compile(
                rf"(?:(?:ال|أل|لل)?{re.escape(suffix)})\s+[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+){{0,2}}"
            )
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span not in seen_spans:
                    trimmed = self._trim_entity(match.group(), self._ARABIC_STOPWORDS)
                    seen_spans.add(span)
                    entities.append({
                        "entity": trimmed,
                        "type": "ORG",
                        "start": match.start(),
                        "end": match.start() + len(trimmed),
                    })

        return entities

    def _extract_persons(self, text: str) -> list[dict]:
        """
        استخراج أسماء الأشخاص من النص.

        المعاملات:
            text: النص المراد استخراج الأشخاص منه.

        العائد:
            قائمة بقواميس الكيانات.
        """
        entities: list[dict] = []
        seen_spans: set[tuple[int, int]] = set()

        # البحث عن أسماء معرفة بـ ألقاب
        for prefix in self._PERSON_PREFIXES:
            # نمط: لقب متبوع باسم عربي (حد أقصى كلمتين)
            pattern = re.compile(
                rf"{re.escape(prefix)}\s+[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?"
            )
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                if span not in seen_spans:
                    trimmed = self._trim_entity(match.group(), self._ARABIC_STOPWORDS)
                    seen_spans.add(span)
                    entities.append({
                        "entity": trimmed,
                        "type": "PER",
                        "start": match.start(),
                        "end": match.start() + len(trimmed),
                    })

        # البحث عن أسماء أشخاص معروفة
        for person in self._KNOWN_PERSONS:
            for match in re.finditer(re.escape(person), text):
                span = (match.start(), match.end())
                if span not in seen_spans:
                    seen_spans.add(span)
                    entities.append({
                        "entity": match.group(),
                        "type": "PER",
                        "start": match.start(),
                        "end": match.end(),
                    })

        return entities

    def _pattern_extract(self, text: str) -> list[dict]:
        """
        استخراج جميع الكيانات باستخدام الأنماط.

        المعاملات:
            text: النص المراد استخراج الكيانات منه.

        العائد:
            قائمة مرتبة بالكيانات المستخرجة.
        """
        all_entities: list[dict] = []

        # استخراج كل نوع
        all_entities.extend(self._extract_persons(text))
        all_entities.extend(self._extract_organizations(text))
        all_entities.extend(self._extract_locations(text))
        all_entities.extend(self._extract_dates(text))

        # ترتيب حسب موضع الظهور
        all_entities.sort(key=lambda e: e["start"])

        # إزالة التداخلات
        cleaned: list[dict] = []
        last_end = -1
        for entity in all_entities:
            if entity["start"] >= last_end:
                cleaned.append(entity)
                last_end = entity["end"]

        return cleaned

    # ------------------------------------------------------------------
    # استخراج بالنموذج (إذا توفر)
    # ------------------------------------------------------------------
    def _model_extract(self, text: str) -> list[dict]:
        """
        استخراج الكيانات باستخدام نموذج NER.

        المعاملات:
            text: النص المراد استخراج الكيانات منه.

        العائد:
            قائمة بقواميس الكيانات.
        """
        if not self._pipeline:
            return self._pattern_extract(text)

        try:
            results = self._pipeline(text)
            entities: list[dict] = []

            for item in results:
                entity_type = item.get("entity_group", item.get("entity", "MISC"))
                # تحويل أنواع الكيانات
                type_map = {
                    "B-PER": "PER", "I-PER": "PER",
                    "B-ORG": "ORG", "I-ORG": "ORG",
                    "B-LOC": "LOC", "I-LOC": "LOC",
                    "B-DATE": "DATE", "I-DATE": "DATE",
                    "PER": "PER", "ORG": "ORG", "LOC": "LOC", "DATE": "DATE",
                }
                mapped_type = type_map.get(entity_type, entity_type)

                entities.append({
                    "entity": item.get("word", "").strip(),
                    "type": mapped_type,
                    "start": item.get("start", 0),
                    "end": item.get("end", 0),
                    "score": round(item.get("score", 0.0), 4),
                })

            return entities
        except Exception as e:
            logger.warning("فشل الاستخراج بالنموذج: %s — يتم الرجوع للأنماط", e)
            return self._pattern_extract(text)

    # ------------------------------------------------------------------
    # الواجهة العامة
    # ------------------------------------------------------------------
    def extract(self, text: str) -> list[dict]:
        """
        استخراج الكيانات المسماة من النص.

        المعاملات:
            text: النص المراد استخراج الكيانات منه.

        العائد:
            قائمة بقواميس الكيانات: {entity, type, start, end}
        """
        if not text or not text.strip():
            return []

        cleaned = text.strip()

        if self._model_available and self._pipeline is not None:
            return self._model_extract(cleaned)

        return self._pattern_extract(cleaned)

    def extract_from_document(self, text: str) -> dict:
        """
        استخراج الكيانات من مستند كامل.

        المعاملات:
            text: نص المستند الكامل.

        العائد:
            قاموس يحتوي على:
                - entities: قائمة جميع الكيانات
                - by_type: كيانات مصنفة حسب النوع
                - unique_entities: الكيانات الفريدة
                - total_count: العدد الإجمالي
        """
        if not text or not text.strip():
            return {
                "entities": [],
                "by_type": {},
                "unique_entities": [],
                "total_count": 0,
            }

        entities = self.extract(text)

        # تصنيف حسب النوع
        by_type: dict[str, list[dict]] = {}
        for entity in entities:
            etype = entity["type"]
            if etype not in by_type:
                by_type[etype] = []
            by_type[etype].append(entity)

        # الكيانات الفريدة
        unique_names: list[str] = []
        seen_names: set[str] = set()
        for entity in entities:
            name = entity["entity"]
            if name not in seen_names:
                seen_names.add(name)
                unique_names.append(name)

        return {
            "entities": entities,
            "by_type": by_type,
            "unique_entities": unique_names,
            "total_count": len(entities),
        }

    def extract_by_type(self, text: str, entity_type: str) -> list[dict]:
        """
        استخراج كيانات من نوع محدد.

        المعاملات:
            text: النص.
            entity_type: نوع الكيان (PER/ORG/LOC/DATE).

        العائد:
            قائمة بالكيانات من النوع المطلوب.
        """
        all_entities = self.extract(text)
        return [e for e in all_entities if e["type"] == entity_type.upper()]

    def get_supported_types(self) -> list[str]:
        """
        عرض أنواع الكيانات المدعومة.

        العائد:
            قائمة بأنواع الكيانات.
        """
        return ["PER", "ORG", "LOC", "DATE"]
