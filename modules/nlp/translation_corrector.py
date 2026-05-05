#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arabic Translation Corrector — Post-MT Correction Engine
==========================================================
محرّك تصحيح الترجمات العربية بعد الترجمة الآلية (Post-MT Correction).

Integrates rule-based corrections, regex patterns, and Arabic-specific
normalization into the OmniFile AI Processor pipeline.

Architecture:
    ArabicTranslationProcessor
    ├── Rule-based corrections (JSON + defaults)
    │   ├── Structural (predicate-subject reordering)
    │   ├── Grammatical (particle corrections)
    │   ├── Lexical (loanword → Arabic term)
    │   ├── Stylistic (idiomatic fixes)
    │   ├── Cultural (contextual fixes)
    │   └── Punctuation (Latin → Arabic)
    ├── Regex corrections (patterns)
    │   ├── Comma spacing normalization
    │   ├── Number merging
    │   ├── Redundant waw removal
    │   ├── Extra whitespace cleanup
    │   ├── Word repeat detection
    │   └── Punctuation spacing
    └── Statistics tracking

Author:  Dr Abdulmalek Tamer Al-husseini
License: MIT
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ====================================================================
# Rule Data Class
# ====================================================================

@dataclass
class TranslationRule:
    """Represents a single translation correction rule."""
    rule_id: str
    category: str
    english_pattern: str
    wrong_arabic: str
    correct_arabic: str
    description: str
    priority: int = 2  # 1=critical, 2=important, 3=cosmetic
    examples: list = field(default_factory=list)

    def applies_to(self, en_text: str, ar_text: str) -> bool:
        """Check if this rule applies to the given English/Arabic pair."""
        en_match = self.english_pattern.lower() in en_text.lower() if self.english_pattern else True
        ar_match = self.wrong_arabic in ar_text if self.wrong_arabic else True
        return en_match and ar_match

    def apply(self, ar_text: str) -> str:
        """Apply the correction rule to Arabic text."""
        if not self.wrong_arabic:
            return ar_text
        return ar_text.replace(self.wrong_arabic, self.correct_arabic)


# ====================================================================
# Main Processor Class
# ====================================================================

class ArabicTranslationProcessor:
    """
    Core Arabic translation post-processing engine.

    Usage:
        processor = ArabicTranslationProcessor(rules_file="data/translation_rules.json")
        result = processor.process_translation("Hello", "مرحبا")
        print(result["corrected"])
    """

    # Default rules file path (relative to OmniFile_Processor root)
    DEFAULT_RULES_FILE = "data/translation_rules.json"

    def __init__(self, rules_file: Optional[str] = None):
        self.rules: List[TranslationRule] = []
        self._stats = {
            "total_processed": 0,
            "total_corrected": 0,
            "corrections_by_category": {},
            "rule_hits": {},
        }
        self._regex_patterns = self._compile_regex_patterns()

        if rules_file and os.path.isfile(rules_file):
            self.load_rules_from_file(rules_file)
            logger.info("Loaded rules from %s (%d rules)", rules_file, len(self.rules))
        else:
            self._initialize_default_rules()
            logger.info("Using %d default rules", len(self.rules))

    # ----------------------------------------------------------------
    # Regex Patterns
    # ----------------------------------------------------------------

    @staticmethod
    def _compile_regex_patterns() -> Dict[str, re.Pattern]:
        """Pre-compile all regex patterns used in corrections."""
        return {
            "comma_spacing": re.compile(r"\s*,\s*"),
            "arabic_comma": re.compile(r"،\s*"),
            "number_spacing": re.compile(r"(\d)\s+(\d)"),
            "number_comma": re.compile(r"(\d+),(\d+)"),
            "redundant_ba": re.compile(r"بواسطة\s+"),
            "redundant_waw": re.compile(r"(رغم|خاصة|سبق)\s+وأن"),
            "word_repeat": re.compile(r"\b(\w{2,})\s+\1\b"),
            "tanween_alif": re.compile(r"([بتثجحخدذرزسشصضطظعغفقكلمنهي])ا(?!\w)"),
            "space_before_punct": re.compile(r"\s+([،؛؟!.])"),
            "extra_spaces": re.compile(r"\s{2,}"),
            "latin_comma_in_arabic": re.compile(r"([\u0600-\u06FF])\s*,\s*([\u0600-\u06FF])"),
            "latin_question_in_arabic": re.compile(r"([\u0600-\u06FF])\s*\?\s*"),
        }

    # ----------------------------------------------------------------
    # Default Rules (fallback when JSON file not found)
    # ----------------------------------------------------------------

    def _initialize_default_rules(self):
        """Hardcode the essential default correction rules."""
        defaults = [
            # Structural — predicate-subject reordering
            TranslationRule("STRUCT_001", "structural",
                            "no smoking", "ممنوع التدخين", "التدخين ممنوع",
                            "تقديم المبتدأ على الخبر في الجملة الاسمية", 1),
            TranslationRule("STRUCT_002", "structural",
                            "no parking", "ممنوع الوقوف", "الوقوف ممنوع",
                            "تقديم المبتدأ على الخبر", 1),
            TranslationRule("STRUCT_003", "structural",
                            "no entry", "ممنوع الدخول", "الدخول ممنوع",
                            "تقديم المبتدأ على الخبر", 1),

            # Grammatical
            TranslationRule("GRAM_001", "grammatical",
                            "by", "بواسطة", "",
                            "حذف 'بواسطة' المترجمة حرفياً — تحويل للمبني للمعلوم", 2),
            TranslationRule("GRAM_002", "grammatical",
                            "met with", "التقى ب", "لقي",
                            "تصحيح تعدية الفعل 'لقي' — لا يحتاج حرف جر", 2),
            TranslationRule("GRAM_003", "grammatical",
                            "and that", "وأن", "أن",
                            "حذف الواو الزائدة قبل 'أن'", 2),
            TranslationRule("GRAM_004", "grammatical",
                            "despite that", "رغم وأن", "رغم أن",
                            "حذف الواو الزائدة بعد 'رغم'", 2),
            TranslationRule("GRAM_005", "grammatical",
                            "especially that", "خاصة وأن", "خاصة أن",
                            "حذف الواو الزائدة بعد 'خاصة'", 2),

            # Lexical — loanword replacement
            TranslationRule("LEX_001", "lexical",
                            "ladies and gentlemen", "السيدات والسادة", "السادة والسيدات",
                            "تقديم المذكر على المؤنث في التحية العربية", 1),
            TranslationRule("LEX_002", "lexical",
                            "computer", "كمبيوتر", "حاسوب",
                            "استخدام المصطلح العربي الفصيح", 1),
            TranslationRule("LEX_003", "lexical",
                            "internet", "إنترنت", "الشابكة",
                            "استخدام المصطلح العربي للإنترنت", 2),
            TranslationRule("LEX_004", "lexical",
                            "mobile", "موبايل", "هاتف محمول",
                            "استخدام المصطلح العربي للهاتف المحمول", 2),
            TranslationRule("LEX_005", "lexical",
                            "email", "إيميل", "بريد إلكتروني",
                            "استخدام المصطلح العربي", 2),
            TranslationRule("LEX_006", "lexical",
                            "website", "ويب سايت", "موقع إلكتروني",
                            "استخدام المصطلح العربي", 2),

            # Stylistic — idiomatic corrections
            TranslationRule("STYLE_001", "stylistic",
                            "played a role", "لعب دوراً", "قام بدور",
                            "استخدام الفعل المناسب في السياق", 2),
            TranslationRule("STYLE_002", "stylistic",
                            "covered the event", "غطى الحدث", "تابع الحدث",
                            "استخدام الفعل المناسب في السياق الإعلامي", 2),
            TranslationRule("STYLE_003", "stylistic",
                            "took place", "أخذ مكاناً", "وقع",
                            "استخدام الفعل العربي الصحيح", 2),
            TranslationRule("STYLE_004", "stylistic",
                            "make a decision", "يصنع قراراً", "يتخذ قراراً",
                            "استخدام التعبير العربي الصحيح", 2),
            TranslationRule("STYLE_005", "stylistic",
                            "pay attention", "يدفع انتباهاً", "ينتبه",
                            "استخدام الفعل العربي المباشر", 2),

            # Cultural
            TranslationRule("CULT_001", "cultural",
                            "god", "جود", "الله",
                            "استخدام اللفظ الإسلامي المناسب", 1),
            TranslationRule("CULT_002", "cultural",
                            "christmas", "عيد الميلاد المجيد", "عيد الميلاد",
                            "استخدام التعبير المحايد", 2),

            # Punctuation
            TranslationRule("PUNCT_001", "punctuation",
                            ",", ",", "،",
                            "استخدام الفاصلة العربية", 3),
            TranslationRule("PUNCT_002", "punctuation",
                            "?", "?", "؟",
                            "استخدام علامة الاستفهام العربية", 3),
        ]
        self.rules = defaults

    # ----------------------------------------------------------------
    # Load Rules from JSON
    # ----------------------------------------------------------------

    def load_rules_from_file(self, filepath: str):
        """Load correction rules from a JSON file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                self.rules = []
                for entry in data:
                    rule = TranslationRule(
                        rule_id=entry.get("rule_id", "UNKNOWN"),
                        category=entry.get("category", "general"),
                        english_pattern=entry.get("english_pattern", ""),
                        wrong_arabic=entry.get("wrong_arabic", ""),
                        correct_arabic=entry.get("correct_arabic", ""),
                        description=entry.get("rule_description", entry.get("description", "")),
                        priority=entry.get("priority", 2),
                        examples=entry.get("examples", []),
                    )
                    self.rules.append(rule)
                logger.info("Loaded %d rules from %s", len(self.rules), filepath)
            else:
                logger.warning("Rules file %s has unexpected format (expected list)", filepath)
                self._initialize_default_rules()

        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.error("Failed to load rules from %s: %s — using defaults", filepath, e)
            self._initialize_default_rules()

    # ----------------------------------------------------------------
    # Regex Corrections
    # ----------------------------------------------------------------

    def apply_regex_corrections(self, text: str) -> Tuple[str, List[str]]:
        """
        Apply regex-based corrections to Arabic text.

        Returns: (corrected_text, list_of_changes)
        """
        changes = []

        # 1. Normalize comma spacing: "،  " → "، "
        new_text = self._regex_patterns["arabic_comma"].sub("، ", text)
        if new_text != text:
            changes.append("normalized_arabic_comma_spacing")
            text = new_text

        # 2. Merge split numbers: "1 234" → "1234"
        new_text = self._regex_patterns["number_spacing"].sub(r"\1\2", text)
        if new_text != text:
            changes.append("merged_split_numbers")
            text = new_text

        # 3. Remove redundant waw: "رغم وأن" → "رغم أن"
        new_text = self._regex_patterns["redundant_waw"].sub(r"\1 أن", text)
        if new_text != text:
            changes.append("removed_redundant_waw")
            text = new_text

        # 4. Remove duplicate words: "ذهب ذهب" → "ذهب"
        new_text = self._regex_patterns["word_repeat"].sub(r"\1", text)
        if new_text != text:
            changes.append("removed_duplicate_word")
            text = new_text

        # 5. Latin comma between Arabic chars → Arabic comma
        new_text = self._regex_patterns["latin_comma_in_arabic"].sub(r"\1،\2", text)
        if new_text != text:
            changes.append("latin_comma_to_arabic")
            text = new_text

        # 6. Latin question mark after Arabic → Arabic question mark
        new_text = self._regex_patterns["latin_question_in_arabic"].sub(r"\1؟", text)
        if new_text != text:
            changes.append("latin_question_to_arabic")
            text = new_text

        # 7. Collapse extra spaces: "   " → " "
        new_text = self._regex_patterns["extra_spaces"].sub(" ", text)
        if new_text != text:
            changes.append("collapsed_extra_spaces")
            text = new_text

        # 8. Space before punctuation: " text ،" → " text،"
        new_text = self._regex_patterns["space_before_punct"].sub(r"\1", text)
        if new_text != text:
            changes.append("removed_space_before_punctuation")
            text = new_text

        return text, changes

    # ----------------------------------------------------------------
    # Main Processing
    # ----------------------------------------------------------------

    def process_translation(
        self,
        english_text: str,
        arabic_text: str,
        apply_rules: bool = True,
        apply_regex: bool = True,
    ) -> Dict:
        """
        Process a single English→Arabic translation pair.

        Args:
            english_text: The original English source text
            arabic_text: The machine-translated Arabic text
            apply_rules: Whether to apply rule-based corrections
            apply_regex: Whether to apply regex corrections

        Returns:
            dict with keys: original, corrected, corrections, rule_ids, regex_changes,
                           improved, stats
        """
        self._stats["total_processed"] += 1

        if not arabic_text or not arabic_text.strip():
            return {
                "original": arabic_text,
                "corrected": arabic_text,
                "corrections": [],
                "rule_ids": [],
                "regex_changes": [],
                "improved": False,
            }

        corrected = arabic_text
        rule_corrections = []
        applied_rule_ids = []

        # Phase 1: Rule-based corrections
        if apply_rules:
            sorted_rules = sorted(self.rules, key=lambda r: r.priority)
            for rule in sorted_rules:
                if rule.applies_to(english_text, corrected):
                    before = corrected
                    corrected = rule.apply(corrected)
                    if corrected != before:
                        rule_corrections.append({
                            "rule_id": rule.rule_id,
                            "category": rule.category,
                            "change": f"{rule.wrong_arabic} → {rule.correct_arabic}",
                            "description": rule.description,
                        })
                        applied_rule_ids.append(rule.rule_id)

                        # Update stats
                        cat = rule.category
                        self._stats["corrections_by_category"][cat] = \
                            self._stats["corrections_by_category"].get(cat, 0) + 1
                        self._stats["rule_hits"][rule.rule_id] = \
                            self._stats["rule_hits"].get(rule.rule_id, 0) + 1

        # Phase 2: Regex corrections
        regex_changes = []
        if apply_regex:
            corrected, regex_changes = self.apply_regex_corrections(corrected)

        improved = corrected != arabic_text
        if improved:
            self._stats["total_corrected"] += 1

        return {
            "original": arabic_text,
            "corrected": corrected,
            "corrections": rule_corrections,
            "rule_ids": applied_rule_ids,
            "regex_changes": regex_changes,
            "improved": improved,
        }

    # ----------------------------------------------------------------
    # Batch Processing
    # ----------------------------------------------------------------

    def process_batch(
        self,
        pairs: List[Tuple[str, str]],
        apply_rules: bool = True,
        apply_regex: bool = True,
    ) -> List[Dict]:
        """Process multiple translation pairs at once."""
        return [
            self.process_translation(en, ar, apply_rules, apply_regex)
            for en, ar in pairs
        ]

    # ----------------------------------------------------------------
    # Statistics
    # ----------------------------------------------------------------

    def get_statistics(self) -> Dict:
        """Return a copy of processing statistics."""
        stats = dict(self._stats)
        if stats["total_processed"] > 0:
            stats["improvement_rate"] = stats["total_corrected"] / stats["total_processed"]
        else:
            stats["improvement_rate"] = 0.0
        return stats

    def reset_statistics(self):
        """Reset all counters to zero."""
        self._stats = {
            "total_processed": 0,
            "total_corrected": 0,
            "corrections_by_category": {},
            "rule_hits": {},
        }

    # ----------------------------------------------------------------
    # Rules Management
    # ----------------------------------------------------------------

    def add_rule(self, rule: TranslationRule):
        """Add a new correction rule."""
        self.rules.append(rule)
        logger.info("Added rule %s (%s): %s", rule.rule_id, rule.category, rule.description)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if found and removed."""
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        removed = len(self.rules) < before
        if removed:
            logger.info("Removed rule %s", rule_id)
        return removed

    def get_rules_table(self) -> List[Dict]:
        """Get all rules as a list of dicts (for display in Gradio/DataFrame)."""
        return [
            {
                "Rule ID": r.rule_id,
                "Category": r.category,
                "English Pattern": r.english_pattern,
                "Wrong Arabic": r.wrong_arabic,
                "Correct Arabic": r.correct_arabic,
                "Priority": r.priority,
                "Description": r.description,
            }
            for r in self.rules
        ]

    def get_rules_summary(self) -> str:
        """Get a human-readable summary of all rules grouped by category."""
        from collections import Counter
        cat_counts = Counter(r.category for r in self.rules)
        lines = [f"Total: {len(self.rules)} rules\n"]
        for cat, count in sorted(cat_counts.items()):
            lines.append(f"  {cat}: {count} rules")
        return "\n".join(lines)
