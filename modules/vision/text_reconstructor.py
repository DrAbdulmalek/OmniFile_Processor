"""
مُعيد تجميع النصوص
=====================
إعادة تجميع الكلمات المكتشفة من OCR إلى نصوص مترابطة
مع دعم خاص للنصوص العربية (RTL).

القدرات:
- تجميع الكلمات بناءً على إحداثياتها (x, y)
- تجميع الكلمات في سطور حسب القرب العمودي
- دعم النص العربي RTL باستخدام arabic-reshaper و python-bidi
- التعامل مع النصوص المختلطة (عربي + إنجليزي)
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class TextReconstructor:
    """
    مُعيد تجميع النصوص - يعيد بناء الجمل من نتائج OCR على مستوى الكلمات.

    مثال الاستخدام:
        >>> reconstructor = TextReconstructor(line_threshold=15)
        >>> words = [
        ...     {"text": "مرحبا", "x": 200, "y": 10, "w": 50, "h": 20},
        ...     {"text": "بالعالم", "x": 140, "y": 10, "w": 60, "h": 20},
        ...     {"text": "Hello", "x": 10, "y": 50, "w": 40, "h": 20},
        ... ]
        >>> text = reconstructor.reconstruct(words, direction="rtl")
    """

    def __init__(
        self,
        line_threshold: float = 15.0,
        word_gap_threshold: float = 50.0,
        default_direction: str = "auto",
    ) -> None:
        """
        تهيئة مُعيد التجميع.

        Args:
            line_threshold: أقصى فرق عمودي (Y) لاعتبار كلمتين في نفس السطر
            word_gap_threshold: أقل مسافة أفقية لفصل الكلمات بمسافة
            default_direction: الاتجاه الافتراضي ("auto", "rtl", "ltr")
        """
        self.line_threshold = line_threshold
        self.word_gap_threshold = word_gap_threshold
        self.default_direction = default_direction

        # التحقق من مكتبات إعادة تشكيل العربية
        self._has_reshaper = self._check_library(
            "arabic_reshaper", "arabic-reshaper"
        )
        self._has_bidi = self._check_library(
            "bidi", "python-bidi"
        )

        if not self._has_reshaper:
            logger.warning(
                "arabic-reshaper غير مثبت. النص العربي قد لا يظهر بشكل صحيح. "
                "قم بالتثبيت: pip install arabic-reshaper"
            )
        if not self._has_bidi:
            logger.warning(
                "python-bidi غير مثبت. اتجاه النص قد لا يكون صحيحاً. "
                "قم بالتثبيت: pip install python-bidi"
            )

    @staticmethod
    def _check_library(import_name: str, package_name: str) -> bool:
        """التحقق من توفر مكتبة."""
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # الأساليب العامة (Public API)
    # ------------------------------------------------------------------

    def reconstruct(
        self,
        words: list[dict],
        direction: str = "auto",
    ) -> str:
        """
        إعادة تجميع قائمة كلمات إلى نص مترابط.

        Args:
            words: قائمة كلمات، كل كلمة قاموس يحتوي:
                   - text: النص
                   - x, y: موقع أعلى اليسار
                   - w, h: العرض والارتفاع
            direction: اتجاه النص ("auto", "rtl", "ltr")

        Returns:
            النص المُعاد تجميعه
        """
        if not words:
            return ""

        # تنظيف الكلمات الفارغة
        valid_words = [
            w for w in words
            if w.get("text", "").strip()
            and all(k in w for k in ("x", "y", "w", "h"))
        ]

        if not valid_words:
            return ""

        # تحديد الاتجاه
        detected_direction = self._detect_direction(valid_words, direction)

        # تجميع الكلمات في سطور
        lines = self._group_into_lines(valid_words)

        # ترتيب الكلمات داخل كل سطر
        ordered_lines: list[str] = []
        for line_words in lines:
            line_text = self._order_line(line_words, detected_direction)
            ordered_lines.append(line_text)

        # دمج الأسطر
        full_text = "\n".join(ordered_lines)

        return full_text.strip()

    def reconstruct_with_direction(
        self,
        words: list[dict],
        direction: str = "rtl",
    ) -> str:
        """
        إعادة تجميع النصوص مع تحديد الاتجاه بشكل صريح.

        Args:
            words: قائمة كلمات OCR
            direction: "rtl" أو "ltr"

        Returns:
            النص المُعاد تجميعه مع معالجة الاتجاه
        """
        if direction not in ("rtl", "ltr"):
            logger.warning(
                "اتجاه غير معروف '%s' - سيتم استخدام auto", direction
            )
            return self.reconstruct(words, direction="auto")

        text = self.reconstruct(words, direction=direction)

        # إعادة تشكيل النص العربي إذا توفرت المكتبات
        if direction == "rtl" and self._has_reshaper and self._has_bidi:
            text = self._apply_arabic_reshaping(text)

        return text

    def get_statistics(self, words: list[dict]) -> dict:
        """
        الحصول على إحصائيات حول نتائج OCR.

        Args:
            words: قائمة كلمات OCR

        Returns:
            قاموس يحتوي إحصائيات
        """
        if not words:
            return {"total_words": 0}

        valid_words = [
            w for w in words
            if w.get("text", "").strip()
        ]

        lines = self._group_into_lines(valid_words)

        # اكتشاف نسبة العربية
        arabic_count = sum(
            1 for w in valid_words
            if self._is_arabic_text(w.get("text", ""))
        )

        return {
            "total_words": len(valid_words),
            "total_lines": len(lines),
            "arabic_words": arabic_count,
            "english_words": len(valid_words) - arabic_count,
            "arabic_ratio": arabic_count / max(1, len(valid_words)),
            "direction": self._detect_direction(valid_words, "auto"),
        }

    # ------------------------------------------------------------------
    # الأساليب الداخلية - التجميع والترتيب
    # ------------------------------------------------------------------

    def _group_into_lines(
        self, words: list[dict]
    ) -> list[list[dict]]:
        """
        تجميع الكلمات في أسطر بناءً على القرب العمودي.

        الخوارزمية:
        1. ترتيب الكلمات حسب Y
        2. تجميع الكلمات القريبة عمودياً في نفس السطر
        3. استخدام المتوسط المتحرك لحدود الأسطر

        Args:
            words: قائمة كلمات صالحة

        Returns:
            قائمة أسطر، كل سطر قائمة كلمات
        """
        # ترتيب حسب Y أولاً (الصفوف العلوية أولاً)
        sorted_words = sorted(words, key=lambda w: w["y"])

        lines: list[list[dict]] = []
        current_line: list[dict] = [sorted_words[0]]

        for word in sorted_words[1:]:
            # حساب متوسط Y للسطر الحالي
            avg_y = sum(w["y"] for w in current_line) / len(current_line)
            word_center_y = word["y"] + word["h"] / 2
            current_center_y = avg_y + (current_line[0]["h"] / 2)

            # إذا كانت الكلمة قريبة عمودياً من السطر الحالي
            if abs(word_center_y - current_center_y) <= self.line_threshold:
                current_line.append(word)
            else:
                # سطر جديد
                lines.append(current_line)
                current_line = [word]

        # إضافة السطر الأخير
        if current_line:
            lines.append(current_line)

        # ترتيب كل سطر حسب Y المتوسط (للضمان)
        lines.sort(key=lambda line: sum(w["y"] for w in line) / len(line))

        return lines

    def _order_line(
        self,
        line_words: list[dict],
        direction: str,
    ) -> str:
        """
        ترتيب الكلمات داخل سطر وبناء النص.

        Args:
            line_words: كلمات في نفس السطر
            direction: اتجاه النص

        Returns:
            نص السطر
        """
        if not line_words:
            return ""

        # ترتيب حسب X (اليسار لليمين أولاً)
        sorted_by_x = sorted(line_words, key=lambda w: w["x"])

        if direction == "rtl":
            # للعربية: الكلمات على اليمين تأتي أولاً
            # لكننا نبقي ترتيب X لأن الكلمة اليمنى لها x أكبر
            # نحتاج لعكس الترتيب
            sorted_by_x = sorted(line_words, key=lambda w: -w["x"])

        # بناء النص مع مراعاة المسافات
        result_parts: list[str] = []

        for i, word in enumerate(sorted_by_x):
            text = word["text"].strip()
            if not text:
                continue

            if i == 0:
                result_parts.append(text)
            else:
                # حساب المسافة من الكلمة السابقة
                prev_word = sorted_by_x[i - 1]
                gap = self._calculate_gap(prev_word, word, direction)

                if gap > self.word_gap_threshold:
                    # مسافة كبيرة = مسافة بين كلمات
                    result_parts.append(" ")
                    result_parts.append(text)
                else:
                    # مسافة صغيرة = كلمات متصلة أو مسافة عادية
                    result_parts.append(" ")
                    result_parts.append(text)

        return "".join(result_parts).strip()

    @staticmethod
    def _calculate_gap(
        word1: dict, word2: dict, direction: str
    ) -> float:
        """
        حساب المسافة الأفقية بين كلمتين.

        Args:
            word1: الكلمة الأولى
            word2: الكلمة الثانية
            direction: اتجاه النص

        Returns:
            المسافة بالبكسل
        """
        if direction == "rtl":
            # للعربية: word1 على اليمين و word2 على اليسار
            # word1.x > word2.x (عادةً)
            # المسافة = word1.x - (word2.x + word2.w)
            right_word = word1 if word1["x"] > word2["x"] else word2
            left_word = word2 if word1["x"] > word2["x"] else word1
            return max(0, left_word["x"] - (right_word["x"] + right_word["w"]))
        else:
            # للإنجليزية: word1 على اليسار و word2 على اليمين
            left_word = word1 if word1["x"] < word2["x"] else word2
            right_word = word2 if word1["x"] < word2["x"] else word1
            return max(0, right_word["x"] - (left_word["x"] + left_word["w"]))

    # ------------------------------------------------------------------
    # الأساليب الداخلية - كشف الاتجاه
    # ------------------------------------------------------------------

    def _detect_direction(
        self, words: list[dict], hint: str
    ) -> str:
        """
        اكتشاف اتجاه النص تلقائياً أو استخدام الإشارة المحددة.

        Args:
            words: قائمة الكلمات
            hint: الإشارة ("auto", "rtl", "ltr")

        Returns:
            "rtl" أو "ltr"
        """
        if hint in ("rtl", "ltr"):
            return hint

        # كشف تلقائي
        if hint == "auto" or hint not in ("rtl", "ltr"):
            arabic_chars = 0
            latin_chars = 0

            arabic_ranges = [
                (0x0600, 0x06FF),
                (0x0750, 0x077F),
                (0x08A0, 0x08FF),
                (0xFB50, 0xFDFF),
                (0xFE70, 0xFEFF),
                (0x0660, 0x0669),
            ]

            for word in words:
                text = word.get("text", "")
                if not text.strip():
                    continue

                for char in text:
                    code = ord(char)
                    if any(start <= code <= end for start, end in arabic_ranges):
                        arabic_chars += 1
                    elif ("A" <= char <= "Z") or ("a" <= char <= "z"):
                        latin_chars += 1

            if arabic_chars == 0 and latin_chars == 0:
                return "ltr"

            if arabic_chars > latin_chars:
                logger.debug(
                    "اتجاه RTL مكتشف (حروف عربية: %d، لاتينية: %d)",
                    arabic_chars,
                    latin_chars,
                )
                return "rtl"

            logger.debug(
                "اتجاه LTR مكتشف (حروف عربية: %d، لاتينية: %d)",
                arabic_chars,
                latin_chars,
            )
            return "ltr"

        return "ltr"

    @staticmethod
    def _is_arabic_text(text: str) -> bool:
        """
        التحقق مما إذا كان النص يحتوي على حروف عربية.

        يتحقق من وجود حروف عربية (U+0600–U+06FF) أو أرقام هندية.

        Args:
            text: النص المراد فحصه

        Returns:
            True إذا كان النص يحتوي على عربية
        """
        if not text:
            return False

        # نطاقات اليونيكود العربية
        arabic_ranges = [
            (0x0600, 0x06FF),   # الحروف العربية
            (0x0750, 0x077F),   # امتدادات العربية
            (0x08A0, 0x08FF),   # امتدادات إضافية
            (0xFB50, 0xFDFF),   # أشكال العرض العربية
            (0xFE70, 0xFEFF),   # أشكال العرض العربية - B
            (0x0660, 0x0669),   # الأرقام الهندية
        ]

        for char in text:
            code = ord(char)
            for start, end in arabic_ranges:
                if start <= code <= end:
                    return True

        return False

    @staticmethod
    def _is_latin_text(text: str) -> bool:
        """
        التحقق مما إذا كان النص يحتوي على حروف لاتينية/إنجليزية.

        Args:
            text: النص المراد فحصه

        Returns:
            True إذا كان النص يحتوي على لاتينية
        """
        if not text:
            return False

        for char in text:
            if ("A" <= char <= "Z") or ("a" <= char <= "z"):
                return True

        return False

    # ------------------------------------------------------------------
    # أساليب إعادة تشكيل النص العربي
    # ------------------------------------------------------------------

    def _apply_arabic_reshaping(self, text: str) -> str:
        """
        إعادة تشكيل النص العربي ليظهر بشكل صحيح.

        تستخدم arabic-reshaper لتوصيل الحروف
        و python-bidi لعكس اتجاه العرض.

        Args:
            text: النص العربي الخام

        Returns:
            النص المعاد تشكيله
        """
        if not text:
            return text

        try:
            import arabic_reshaper
            from bidi.algorithm import get_display

            # تقسيم النص إلى أسطر ومعالجة كل سطر
            lines = text.split("\n")
            reshaped_lines: list[str] = []

            for line in lines:
                if not line.strip():
                    reshaped_lines.append(line)
                    continue

                # التعامل مع النص المختلط (عربي + إنجليزي)
                segments = self._split_mixed_text(line)

                reshaped_segments: list[str] = []
                for segment in segments:
                    if segment["type"] == "arabic":
                        reshaped = arabic_reshaper.reshape(segment["text"])
                        displayed = get_display(reshaped)
                        reshaped_segments.append(displayed)
                    else:
                        reshaped_segments.append(segment["text"])

                reshaped_lines.append("".join(reshaped_segments))

            return "\n".join(reshaped_lines)

        except Exception as e:
            logger.warning("فشل في إعادة تشكيل النص العربي: %s", e)
            return text

    @staticmethod
    def _split_mixed_text(text: str) -> list[dict]:
        """
        تقسيم النص المختلط إلى أجزاء عربية وغير عربية.

        Args:
            text: النص المختلط

        Returns:
            قائمة أجزاء: [{"text": "...", "type": "arabic|other"}]
        """
        if not text:
            return []

        segments: list[dict] = []
        current_segment = ""
        current_type = None

        arabic_ranges = [
            (0x0600, 0x06FF),
            (0x0750, 0x077F),
            (0x08A0, 0x08FF),
            (0xFB50, 0xFDFF),
            (0xFE70, 0xFEFF),
        ]

        for char in text:
            code = ord(char)
            is_arabic = any(start <= code <= end for start, end in arabic_ranges)
            is_space = char in (" ", "\t", "\n")

            char_type = "arabic" if is_arabic else "other"

            # المسافات تنضم للنوع الحالي
            if is_space:
                current_segment += char
                continue

            if current_type is None:
                current_type = char_type
                current_segment = char
            elif char_type == current_type:
                current_segment += char
            else:
                # تغيير النوع
                if current_segment.strip():
                    segments.append({
                        "text": current_segment,
                        "type": current_type,
                    })
                current_type = char_type
                current_segment = char

        # إضافة الجزء الأخير
        if current_segment.strip():
            segments.append({
                "text": current_segment,
                "type": current_type,
            })

        return segments

    def reconstruct_mixed_paragraph(
        self,
        words: list[dict],
    ) -> str:
        """
        إعادة تجميع فقرة مختلطة (عربي + إنجليزي) مع معالجة ذكية.

        يحاول فصل الأجزاء العربية عن الإنجليزية ويعالج كل جزء
        حسب اتجاهه المناسب.

        Args:
            words: قائمة كلمات OCR

        Returns:
            النص المُعاد تجميعه
        """
        if not words:
            return ""

        # تجميع في سطور
        valid_words = [
            w for w in words
            if w.get("text", "").strip()
            and all(k in w for k in ("x", "y", "w", "h"))
        ]

        if not valid_words:
            return ""

        lines = self._group_into_lines(valid_words)
        result_lines: list[str] = []

        for line_words in lines:
            # فصل كلمات العربي عن الإنجليزي
            arabic_words = [
                w for w in line_words
                if self._is_arabic_text(w["text"])
            ]
            english_words = [
                w for w in line_words
                if self._is_latin_text(w["text"])
            ]

            # ترتيب كل مجموعة
            arabic_sorted = sorted(
                arabic_words, key=lambda w: -w["x"]
            )
            english_sorted = sorted(
                english_words, key=lambda w: w["x"]
            )

            # دمج حسب الموقع
            line_text = self._merge_mixed_line(
                arabic_sorted, english_sorted, line_words
            )
            result_lines.append(line_text)

        full_text = "\n".join(result_lines)

        # إعادة تشكيل العربي
        if self._has_reshaper and self._has_bidi:
            full_text = self._apply_arabic_reshaping(full_text)

        return full_text.strip()

    @staticmethod
    def _merge_mixed_line(
        arabic_words: list[dict],
        english_words: list[dict],
        all_words: list[dict],
    ) -> str:
        """
        دمج كلمات عربية وإنجليزية في سطر واحد حسب الموقع.

        Args:
            arabic_words: الكلمات العربية (مرتبة RTL)
            english_words: الكلمات الإنجليزية (مرتبة LTR)
            all_words: كل الكلمات (مرتبة حسب الموقع الأصلي)

        Returns:
            نص السطر المدمج
        """
        # إنشاء خريطة الموقع -> النص
        position_map: dict[tuple[int, int], str] = {}
        for w in all_words:
            center_x = w["x"] + w["w"] // 2
            center_y = w["y"] + w["h"] // 2
            position_map[(center_x, center_y)] = w["text"].strip()

        # ترتيب حسب الموقع الأصلي (X تنازلياً للعربية)
        sorted_positions = sorted(
            position_map.keys(),
            key=lambda pos: pos[0],
        )

        # البناء - نعكس النص العربي فقط
        parts: list[str] = []
        for pos in sorted_positions:
            text = position_map[pos]
            parts.append(text)

        return " ".join(parts)
