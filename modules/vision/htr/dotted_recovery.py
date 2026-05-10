"""
استرداد النقاط والحركات العربية (Arabic Dotted Recovery).

يوفر فئة ArabicDottedRecovery لاستعادة النقاط والحركات التشكيلية
في النصّ العربي المُتعَرَّف عليه بدون نقط.

استراتيجية الاسترداد:
  1. البحث في القاموس عن تطابق كامل.
  2. البحث عن أنماط شائعة (بسم الله، إن شاء الله، ...).
  3. توليد المتغيرات المُنقَّطة لكل حرف غير مُنقَّط.
  4. ترتيب المتغيرات حسب: تواجد في القاموس ← درجة النموذج اللغوي ← تشابه الطول.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from unicodedata import normalize

logger = logging.getLogger(__name__)


# ============================================================
# الأزواج المُنقَّطة للحروف العربية
# ============================================================
# المفتاح هو الحرف بدون نقاط، والقيمة هي الحروف المُنقَّطة المحتملة.
# يُستخدم في توليد المتغيرات المُنقَّطة للاسترداد.
DOTTED_PAIRS: Dict[str, str] = {
    "ب": "تث",
    "ت": "بث",
    "ث": "بت",
    "ج": "حخ",
    "ح": "جخ",
    "خ": "جح",
    "د": "ذ",
    "ذ": "د",
    "ر": "ز",
    "ز": "ر",
    "س": "شصض",
    "ش": "سصض",
    "ص": "سشض",
    "ض": "سشص",
    "ط": "ظ",
    "ظ": "ط",
    "ع": "غ",
    "غ": "ع",
    "ف": "ق",
    "ق": "ف",
    # ن → ب (في بعض الخطوط العربية قد تُقرأ النقاط بشكل خاطئ)
    "ن": "ب",
}

# الأزواج العكسية: من الحروف الأساسية إلى جميع المتغيرات
UNDOT_TO_DOTTED: Dict[str, List[str]] = {}
for _dotted, _base_variants in DOTTED_PAIRS.items():
    _undotted = _dotted  # الحرف نفسه
    for _ch in _base_variants:
        UNDOT_TO_DOTTED.setdefault(_ch, []).append(_dotted)
    UNDOT_TO_DOTTED.setdefault(_dotted, [_dotted])


# ============================================================
# الأنماط الشائعة (Common Patterns)
# ============================================================
COMMON_PATTERNS: Dict[str, str] = {
    # عبارات دينية شائعة
    "بسم الله الرحمن الرحيم": "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
    "الحمد لله": "الْحَمْدُ لِلَّهِ",
    "الله اكبر": "اللَّهُ أَكْبَرُ",
    "لا اله الا الله": "لَا إِلَهَ إِلَّا اللَّهُ",
    "صلى الله عليه وسلم": "صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ",
    "ان شاء الله": "إِنْ شَاءَ اللَّهُ",
    "سبحان الله": "سُبْحَانَ اللَّهِ",
    "الحمد لله رب العالمين": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
    "السلام عليكم": "السَّلَامُ عَلَيْكُمْ",
    "وعليكم السلام": "وَعَلَيْكُمُ السَّلَامُ",
    # عبارات شائعة أخرى
    "الذي": "الَّذِي",
    "التي": "الَّتِي",
    "اللذين": "اللَّذَيْنِ",
    "هذا": "هَذَا",
    "هذه": "هَذِهِ",
    "ذلك": "ذَلِكَ",
    "عليه": "عَلَيْهِ",
    "منه": "مِنْهُ",
    "فيه": "فِيهِ",
    "اليه": "إِلَيْهِ",
    "عنه": "عَنْهُ",
    "بعد": "بَعْدَ",
    "قبل": "قَبْلَ",
    "كل": "كُلُّ",
    "بين": "بَيْنَ",
    "ذلك": "ذَٰلِكَ",
    "الناس": "النَّاسِ",
    "العالمين": "الْعَالَمِينَ",
    "يوم": "يَوْمَ",
    "الكتاب": "الْكِتَابِ",
    "الصلاة": "الصَّلَاةِ",
    "الزكاة": "الزَّكَاةِ",
    "الصيام": "الصِّيَامِ",
    "الحج": "الْحَجِّ",
}


# ============================================================
# ArabicDottedRecovery
# ============================================================
class ArabicDottedRecovery:
    """استرداد النقاط والحركات العربية.

    يستخدم القاموس والأنماط الشائعة وتوليد المتغيرات لاستعادة النقاط
    المفقودة في النصّ المُتعَرَّف عليه يدويًا.

    Args:
        dictionary_path: مسار ملف القاموس (اختياري). كل سطر يحتوي كلمة واحدة.
            إذا لم يُحدَّد، يُستخدم القاموس المُدمَج.
        use_lm: استخدام نموذج لغوي للترتيب (حالياً وهمي — placeholder).
    """

    # نطاق الحركات العربية (Tashkeel)
    _DIACRITICS_RANGE = (0x064B, 0x065F)
    #还包括 شدة ومَدّة
    _SHADDA = "\u0651"
    _TATWEEL = "\u0640"
    _HAMZA_ABOVE = "\u0654"
    _HAMZA_BELOW = "\u0655"

    def __init__(
        self,
        dictionary_path: Optional[str] = None,
        use_lm: bool = False,
    ) -> None:
        self._use_lm = use_lm
        self._dictionary: Dict[str, float] = {}  # كلمة ← تكرار/وزن

        # تحميل القاموس
        if dictionary_path:
            self._load_dictionary(dictionary_path)
        else:
            self._load_builtin_dictionary()

        # بناء قاموس بدون حركات (للبحث السريع)
        self._dict_no_diacritics: Dict[str, List[str]] = {}
        for word, weight in self._dictionary.items():
            stripped = self._remove_diacritics(word)
            self._dict_no_diacritics.setdefault(stripped, []).append(word)

        # تحضير الأنماط بدون حركات
        self._pattern_keys: Dict[str, str] = {}
        for pattern, replacement in COMMON_PATTERNS.items():
            stripped = self._remove_diacritics(pattern)
            self._pattern_keys[stripped] = replacement

        logger.info(
            "تمّ تهيئة وحدة الاسترداد — حجم القاموس: %d كلمة.",
            len(self._dictionary),
        )

    # ----------------------------------------------------------
    # recover — استرداد كامل النصّ
    # ----------------------------------------------------------
    def recover(self, text: str) -> str:
        """استرداد النقاط والحركات للنصّ الكامل.

        Args:
            text: النصّ المُتعَرَّف عليه (قد يكون بدون نقاط/حركات).

        Returns:
            النصّ بعد استرداد النقاط والحركات.
        """
        if not text.strip():
            return text

        # أولاً: محاولة مطابقة أنماط شائعة
        text = self._match_common_patterns(text)

        # ثانيًا: معالجة كلمة بكلمة
        words = text.split()
        recovered_words: List[str] = []

        for word in words:
            recovered = self._recover_word(word)
            recovered_words.append(recovered)

        result = " ".join(recovered_words)

        # إعادة المطابقة لأنماط العبارات متعددة الكلمات
        result = self._match_common_patterns(result)

        logger.debug("تمّ استرداد النقاط للنصّ: '%s'", result)
        return result

    # ----------------------------------------------------------
    # _recover_word — استرداد كلمة واحدة
    # ----------------------------------------------------------
    def _recover_word(self, word: str) -> str:
        """استرداد النقاط لكلمة واحدة.

        خطوات الاسترداد:
            1. البحث في القاموس (مع/بدون حركات).
            2. البحث عن أنماط شائعة.
            3. توليد المتغيرات المُنقَّطة.
            4. ترتيب المتغيرات واختيار الأفضل.

        Args:
            word: الكلمة المُدخَلة.

        Returns:
            الكلمة بعد الاسترداد.
        """
        if not word:
            return word

        # إزالة علامات الترقيم المعروفة
        clean_word = word.strip("،؛:!؟.()-\"\'")
        punctuation_prefix = word[: len(word) - len(word.lstrip("،؛:!؟.()-\"\'"))]
        punctuation_suffix = word[len(word.rstrip("،؛:!؟.()-\"\'")):]

        # 1. البحث المباشر في القاموس
        if clean_word in self._dictionary:
            return punctuation_prefix + clean_word + punctuation_suffix

        # 2. البحث بدون حركات
        stripped = self._remove_diacritics(clean_word)
        if stripped in self._dict_no_diacritics:
            candidates = self._dict_no_diacritics[stripped]
            if len(candidates) == 1:
                return punctuation_prefix + candidates[0] + punctuation_suffix
            # اختر الأكثر تكرارًا
            best = max(candidates, key=lambda w: self._dictionary.get(w, 0))
            return punctuation_prefix + best + punctuation_suffix

        # 3. البحث في الأنماط الشائعة
        if stripped in self._pattern_keys:
            return punctuation_prefix + self._pattern_keys[stripped] + punctuation_suffix

        # 4. توليد المتغيرات المُنقَّطة
        variants = self._generate_dotted_variants(stripped)
        if len(variants) <= 1:
            return word  # لا يوجد متغيرات

        # 5. ترتيب واختيار الأفضل
        ranked = self._rank_variants(variants, clean_word)
        best_variant = ranked[0] if ranked else clean_word

        return punctuation_prefix + best_variant + punctuation_suffix

    # ----------------------------------------------------------
    # _match_common_patterns — مطابقة الأنماط الشائعة
    # ----------------------------------------------------------
    def _match_common_patterns(self, text: str) -> str:
        """مطابقة الأنماط الشائعة في النصّ واستبدالها.

        Args:
            text: النصّ المُدخَل.

        Returns:
            النصّ بعد الاستبدال.
        """
        text_no_diac = self._remove_diacritics(text)
        result = text

        for pattern_stripped, replacement in self._pattern_keys.items():
            if pattern_stripped in text_no_diac:
                # نبحث عن المطابقة في النصّ الأصلي
                idx = text_no_diac.find(pattern_stripped)
                if idx != -1:
                    original_part = text[idx: idx + len(pattern_stripped)]
                    if self._remove_diacritics(original_part) == pattern_stripped:
                        # إذا كان النصّ الأصلي بدون حركات، نستبدله بالنسخة المُشكَّلة
                        if original_part == pattern_stripped:
                            result = text[:idx] + replacement + text[idx + len(pattern_stripped):]
                            text = result
                            text_no_diac = self._remove_diacritics(text)

        return result

    # ----------------------------------------------------------
    # _fuzzy_match — مطابقة ضبابية
    # ----------------------------------------------------------
    def _fuzzy_match(self, word1: str, word2: str) -> float:
        """مقارنة ضبابية بين كلمتين (مع تجاهل الحركات).

        يُستخدم مقياس مسافة ليفنشتاين (Levenshtein) المعدّل.

        Args:
            word1: الكلمة الأولى.
            word2: الكلمة الثانية.

        Returns:
            درجة التشابه (0–1)، حيث 1 = تطابق كامل.
        """
        s1 = self._remove_diacritics(word1)
        s2 = self._remove_diacritics(word2)

        if s1 == s2:
            return 1.0

        # مسافة ليفنشتاين
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],      # حذف
                        dp[i][j - 1],      # إدراج
                        dp[i - 1][j - 1],  # استبدال
                    )

        max_len = max(m, n)
        if max_len == 0:
            return 1.0

        return 1.0 - dp[m][n] / max_len

    # ----------------------------------------------------------
    # _remove_diacritics — إزالة الحركات
    # ----------------------------------------------------------
    def _remove_diacritics(self, text: str) -> str:
        """إزالة حركات التشكيل العربية من النصّ.

        يُزيل الحركات في النطاق U+064B إلى U+065F بالإضافة إلى
        الشدة والمدّة.

        Args:
            text: النصّ المُدخَل.

        Returns:
            النصّ بدون حركات.
        """
        diacritics = set()
        lo, hi = self._DIACRITICS_RANGE
        for code in range(lo, hi + 1):
            diacritics.add(chr(code))
        diacritics.update([self._SHADDA, self._TATWEEL, self._HAMZA_ABOVE, self._HAMZA_BELOW])

        return "".join(ch for ch in text if ch not in diacritics)

    # ----------------------------------------------------------
    # _generate_dotted_variants — توليد المتغيرات
    # ----------------------------------------------------------
    def _generate_dotted_variants(self, word: str) -> List[str]:
        """توليد جميع المتغيرات المُنقَّطة الممكنة لكلمة.

        لكل حرف في الكلمة، يُنشئ نسخة بكل بديل مُنقَّط محتمل.

        Args:
            word: الكلمة بدون نقاط.

        Returns:
            قائمة بجميع المتغيرات المُنقَّطة المحتملة.
        """
        if not word:
            return []

        # بناء المتغيرات تدريجيًا
        # لكل حرف، نحصل على البدائل
        char_alternatives: List[List[str]] = []
        for ch in word:
            alternatives = list(UNDOT_TO_DOTTED.get(ch, [ch]))
            # إزالة التكرارات مع الحفاظ على الترتيب
            seen = set()
            unique = []
            for a in alternatives:
                if a not in seen:
                    seen.add(a)
                    unique.append(a)
            char_alternatives.append(unique)

        # توليد المنتج الديكارتي
        results = [""]  # نبدأ بسلسلة فارغة
        for alts in char_alternatives:
            new_results = []
            for prefix in results:
                for alt in alts:
                    new_results.append(prefix + alt)
            results = new_results

        # إزالة التكرارات
        seen = set()
        unique_results = []
        for r in results:
            if r not in seen:
                seen.add(r)
                unique_results.append(r)

        # تحديد حدّ أقصى لتجنّب الانفجار التوافقي
        MAX_VARIANTS = 512
        if len(unique_results) > MAX_VARIANTS:
            unique_results = unique_results[:MAX_VARIANTS]
            logger.debug(
                "تمّ اقتصاص المتغيرات إلى %d (من %d).", MAX_VARIANTS, len(seen)
            )

        return unique_results

    # ----------------------------------------------------------
    # _rank_variants — ترتيب المتغيرات
    # ----------------------------------------------------------
    def _rank_variants(
        self, variants: List[str], original_word: str
    ) -> List[str]:
        """ترتيب المتغيرات المُنقَّطة حسب مدى ملاءمتها.

        معايير الترتيب:
            1. تواجد في القاموس (مع الحركات).
            2. تواجد في القاموس (بدون حركات).
            3. درجة النموذج اللغوي (إذا مُفعَّل).
            4. تشابه الطول مع الكلمة الأصلية.

        Args:
            variants: قائمة المتغيرات المُنقَّطة.
            original_word: الكلمة الأصلية (للمقارنة).

        Returns:
            المتغيرات مُرتَّبة من الأفضل إلى الأسوأ.
        """
        def score(variant: str) -> Tuple[int, int, float, float]:
            # 1. تواجد في القاموس مباشرة
            if variant in self._dictionary:
                dict_score = 2
            elif self._remove_diacritics(variant) in self._dict_no_diacritics:
                dict_score = 1
            else:
                dict_score = 0

            # 2. درجة القاموس
            weight = self._dictionary.get(variant, 0)

            # 3. درجة النموذج اللغوي (وهمي حاليًا)
            lm_score = 0.5 if self._use_lm else 0.0

            # 4. تشابه الطول
            length_ratio = min(len(variant), max(len(original_word), 1)) / max(len(original_word), 1)

            # العودة: dict_score (عكسي), weight (مباشر), lm_score (مباشر), length_ratio (مباشر)
            return (-dict_score, -weight, -lm_score, -length_ratio)

        ranked = sorted(variants, key=score)
        return ranked

    # ----------------------------------------------------------
    # batch_recover — استرداد دفعة
    # ----------------------------------------------------------
    def batch_recover(self, texts: List[str]) -> List[str]:
        """استرداد النقاط لمجموعة من النصوص.

        Args:
            texts: قائمة النصوص.

        Returns:
            قائمة النصوص بعد الاسترداد.
        """
        logger.info("بدء استرداد النقاط لدفعة من %d نصّ.", len(texts))
        return [self.recover(text) for text in texts]

    # ----------------------------------------------------------
    # add_to_dictionary — إضافة كلمات للقاموس
    # ----------------------------------------------------------
    def add_to_dictionary(self, words: List[str], weight: float = 1.0) -> None:
        """إضافة كلمات إلى القاموس في وقت التشغيل.

        Args:
            words: قائمة الكلمات المُراد إضافتها.
            weight: وزن الكلمات الجديدة (للترتيب).
        """
        for word in words:
            clean = word.strip()
            if clean:
                self._dictionary[clean] = max(self._dictionary.get(clean, 0), weight)
                stripped = self._remove_diacritics(clean)
                if clean not in self._dict_no_diacritics.get(stripped, []):
                    self._dict_no_diacritics.setdefault(stripped, []).append(clean)

        logger.info("تمّ إضافة %d كلمة إلى القاموس. الحجم الجديد: %d.", len(words), len(self._dictionary))

    # ----------------------------------------------------------
    # _load_dictionary — تحميل القاموس من ملف
    # ----------------------------------------------------------
    def _load_dictionary(self, path: str) -> None:
        """تحميل القاموس من ملف نصّي.

        كل سطر: كلمة [tabulation] وزن_اختياري.
        إذا لم يُحدَّد الوزن، يُفترَض 1.0.

        Args:
            path: مسار ملف القاموس.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    word = parts[0].strip()
                    weight = float(parts[1]) if len(parts) > 1 else 1.0
                    if word:
                        self._dictionary[word] = max(
                            self._dictionary.get(word, 0), weight
                        )
            logger.info("تمّ تحميل القاموس من: %s (%d كلمة).", path, len(self._dictionary))
        except FileNotFoundError:
            logger.warning("ملف القاموس غير موجود: %s — سيُستخدم القاموس المُدمَج.", path)
            self._load_builtin_dictionary()
        except Exception as exc:
            logger.error("خطأ في تحميل القاموس: %s — سيُستخدم القاموس المُدمَج.", exc)
            self._load_builtin_dictionary()

    # ----------------------------------------------------------
    # _load_builtin_dictionary — القاموس المُدمَج
    # ----------------------------------------------------------
    def _load_builtin_dictionary(self) -> None:
        """تحميل قاموس مُدمَج بكلمات عربية شائعة."""
        builtin_words = [
            # أسماء الله الحسنى وعبارات دينية
            "الله", "اللَّهُ", "الرحمن", "الرحيم", "بسم", "بِسْمِ",
            "الحمد", "الْحَمْدُ", "رب", "رَبِّ", "العالمين", "الْعَالَمِينَ",
            "الملك", "الْمَلِكِ", "قدوس", "قُدُّوسٌ", "سلام", "سَلَامٌ",
            "مؤمن", "مُؤْمِنٌ", "مهيمن", "مُهَيْمِنُ", "عزيز", "عَزِيزٌ",
            "جبار", "جَبَّارٌ", "متكبر", "مُتَكَبِّرٌ", "خالق", "خَالِقٌ",
            "بارئ", "بَارِئٌ", "مصور", "مُصَوِّرٌ",
            # أسماء شائعة
            "محمد", "مُحَمَّدٌ", "علي", "عَلِيٌّ", "حسن", "حَسَنٌ",
            "حسين", "حُسَيْنٌ", "أحمد", "أَحْمَدُ", "إبراهيم", "إِبْرَاهِيمُ",
            "عمر", "عُمَرُ", "عثمان", "عُثْمَانُ", "خالد", "خَالِدٌ",
            "يوسف", "يُوسُفُ", "موسى", "مُوسَى", "عيسى", "عِيسَى",
            # كلمات شائعة
            "قال", "قَالَ", "في", "فِي", "من", "مِنْ", "إلى", "إِلَى",
            "على", "عَلَى", "عن", "عَنْ", "مع", "مَعَ", "هذا", "هَذَا",
            "هذه", "هَذِهِ", "ذلك", "ذَلِكَ", "الذي", "الَّذِي",
            "التي", "الَّتِي", "اللذين", "اللَّذَيْنِ", "اللواتي", "اللَّوَاتِي",
            "كان", "كَانَ", "يكون", "يَكُونُ", "ليس", "لَيْسَ",
            "ليس", "لَيْسَ", "كل", "كُلُّ", "بعض", "بَعْضٌ",
            "أو", "أَوْ", "و", "وَ", "ثم", "ثُمَّ", "ف", "فَ",
            "أن", "أَنَّ", "إن", "إِنَّ", "لا", "لَا", "لم", "لَمْ",
            "ما", "مَا", "قد", "قَدْ", "لن", "لَنْ", "قد", "قَدْ",
            "الكتاب", "الْكِتَابُ", "القرآن", "الْقُرْآنُ",
            "الصلاة", "الصَّلَاةُ", "الزكاة", "الزَّكَاةُ",
            "الصيام", "الصِّيَامُ", "الحج", "الْحَجُّ",
            "الناس", "النَّاسُ", "يوم", "يَوْمُ",
            "الدنيا", "الدُّنْيَا", "الآخرة", "الْآخِرَةُ",
            "الجنة", "الْجَنَّةُ", "النار", "النَّارُ",
            "الحسنى", "الْحُسْنَى", "العظمى", "الْعُظْمَى",
            # أفعال شائعة
            "قرأ", "قَرَأَ", "كتب", "كَتَبَ", "علم", "عَلِمَ",
            "فهم", "فَهِمَ", "ذهب", "ذَهَبَ", "جاء", "جَاءَ",
            "رأى", "رَأَى", "أعطى", "أَعْطَى", "أخذ", "أَخَذَ",
            "جعل", "جَعَلَ", "أمر", "أَمَرَ", "نهى", "نَهَى",
            "علم", "عَلِمَ", "درس", "دَرَسَ", "تعلم", "تَعَلَّمَ",
            "عمل", "عَمِلَ", "أكل", "أَكَلَ", "شرب", "شَرِبَ",
            "نام", "نَامَ", "جلس", "جَلَسَ", "وقف", "وَقَفَ",
            "فتح", "فَتَحَ", "أغلق", "أَغْلَقَ", "دخل", "دَخَلَ",
            "خرج", "خَرَجَ", "صلى", "صَلَّى", "صام", "صَامَ",
            "زكى", "زَكَّى", "حج", "حَجَّ",
            # أسماء مكان وزمان
            "مصر", "مِصْرُ", "الشام", "الشَّامُ", "العراق", "الْعِرَاقُ",
            "المدينة", "الْمَدِينَةُ", "مكة", "مَكَّةُ",
            "اليوم", "الْيَوْمَ", "غدًا", "أمسِ", "الآن", "الآنَ",
            "هنا", "هُنَا", "هناك", "هُنَاكَ", "حيث", "حَيْثُ",
            "كيف", "كَيْفَ", "أين", "أَيْنَ", "متى", "مَتَى",
            "لماذا", "لِمَاذَا", "هل", "هَلْ",
            # أرقام (بالحروف)
            "واحد", "وَاحِدٌ", "اثنان", "اثْنَانِ", "ثلاثة", "ثَلَاثَةٌ",
            "أربعة", "أَرْبَعَةٌ", "خمسة", "خَمْسَةٌ", "ستة", "سِتَّةٌ",
            "سبعة", "سَبْعَةٌ", "ثمانية", "ثَمَانِيَةٌ", "تسعة", "تِسْعَةٌ",
            "عشرة", "عَشَرَةٌ", "مئة", "مِئَةٌ", "ألف", "أَلْفٌ",
        ]

        for word in builtin_words:
            self._dictionary[word] = 1.0

        # إعادة بناء القاموس بدون حركات
        self._dict_no_diacritics.clear()
        for word, weight in self._dictionary.items():
            stripped = self._remove_diacritics(word)
            self._dict_no_diacritics.setdefault(stripped, []).append(word)

        logger.info("تمّ تحميل القاموس المُدمَج (%d كلمة).", len(self._dictionary))
