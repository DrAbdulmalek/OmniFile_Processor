"""
modules/core/spell_checker_singleton.py
========================================
Singleton instance of HybridSpellChecker for project-wide use.
Prevents duplicate instances across modules.

Usage:
    from modules.core.spell_checker_singleton import get_spell_checker
    
    checker = get_spell_checker()
    corrected = checker.correct_text("النص المراد تصحيحه")
"""

import threading
from typing import Optional

_instance = None
_lock = threading.Lock()


def get_spell_checker(arabic_fixes_path: Optional[str] = None) -> "HybridSpellChecker":
    """
    Get the global HybridSpellChecker singleton.
    
    Args:
        arabic_fixes_path: Only used on first call (subsequent calls ignore it)
    
    Returns:
        HybridSpellChecker instance
    """
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                from modules.core.spell_checker import HybridSpellChecker
                kwargs = {}
                if arabic_fixes_path:
                    kwargs["arabic_fixes_path"] = arabic_fixes_path
                _instance = HybridSpellChecker(**kwargs)
    return _instance


def reset_spell_checker():
    """Reset the singleton (for testing)."""
    global _instance
    with _lock:
        _instance = None
