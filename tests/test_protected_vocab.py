"""Tests for modules.core.protected_vocab.ProtectedVocab"""
import pytest

class TestProtectedVocab:
    """Test ProtectedVocab singleton."""
    
    def setup_method(self):
        from modules.core.protected_vocab import ProtectedVocab
        ProtectedVocab.reset()
    
    def teardown_method(self):
        from modules.core.protected_vocab import ProtectedVocab
        ProtectedVocab.reset()
    
    def test_singleton(self):
        from modules.core.protected_vocab import ProtectedVocab
        v1 = ProtectedVocab()
        v2 = ProtectedVocab()
        assert v1 is v2
    
    def test_python_keywords_protected(self):
        from modules.core.protected_vocab import ProtectedVocab
        vocab = ProtectedVocab()
        assert vocab.is_protected("def") is True
        assert vocab.is_protected("class") is True
        assert vocab.is_protected("import") is True
    
    def test_custom_words(self):
        from modules.core.protected_vocab import ProtectedVocab
        vocab = ProtectedVocab()
        vocab.add("my_custom_term")
        assert vocab.is_protected("my_custom_term") is True
    
    def test_remove_word(self):
        from modules.core.protected_vocab import ProtectedVocab
        vocab = ProtectedVocab()
        vocab.add("temp_word")
        assert vocab.is_protected("temp_word") is True
        assert vocab.remove("temp_word") is True
        assert vocab.is_protected("temp_word") is False
    
    def test_stats(self):
        from modules.core.protected_vocab import ProtectedVocab
        vocab = ProtectedVocab()
        stats = vocab.stats()
        assert "python_keywords" in stats
        assert "total" in stats
        assert stats["total"] > 0
    
    def test_add_many(self):
        from modules.core.protected_vocab import ProtectedVocab
        vocab = ProtectedVocab()
        count = vocab.add_many(["word1", "word2", "word3"])
        assert count == 3
        for w in ["word1", "word2", "word3"]:
            assert vocab.is_protected(w)
