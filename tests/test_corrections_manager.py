"""Tests for modules.core.corrections_manager.CorrectionsDictManager"""
import pytest
import json

class TestCorrectionsDictManager:
    """Test CorrectionsDictManager with temp files."""
    
    def _make_manager(self, tmp_path):
        from modules.core.corrections_manager import CorrectionsDictManager
        corrections_path = str(tmp_path / "corrections.json")
        arabic_fixes_path = str(tmp_path / "arabic_fixes.json")
        backup_dir = str(tmp_path / "backups")
        
        # Create minimal arabic_fixes
        Path(tmp_path / "arabic_fixes.json").write_text(
            json.dumps({"مرحبا": "مرحبا"}), encoding="utf-8"
        )
        
        return CorrectionsDictManager(
            corrections_path=corrections_path,
            arabic_fixes_path=arabic_fixes_path,
            backup_dir=backup_dir
        )
    
    def test_add_and_load(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add("wrong1", "correct1")
        data = mgr.load()
        assert data.get("wrong1") == "correct1"
    
    def test_remove(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add("temp", "fixed")
        assert mgr.remove("temp") is True
        assert "temp" not in mgr.load()
    
    def test_stats(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add("w1", "c1")
        mgr.add("w2", "c2")
        stats = mgr.stats()
        assert stats["total"] == 2
    
    def test_export(self, tmp_path):
        from modules.core.corrections_manager import CorrectionsDictManager
        mgr = self._make_manager(tmp_path)
        mgr.add("w1", "c1")
        export_path = str(tmp_path / "exported.json")
        result = mgr.export(export_path, include_arabic_fixes=False)
        assert Path(result).exists()
        data = json.loads(Path(result).read_text(encoding="utf-8"))
        assert "w1" in data
    
    def test_import_and_merge(self, tmp_path):
        from modules.core.corrections_manager import CorrectionsDictManager
        mgr = self._make_manager(tmp_path)
        
        # Create import file
        import_data = {"import1": "correct1", "import2": "correct2"}
        import_path = str(tmp_path / "import.json")
        Path(import_path).write_text(json.dumps(import_data), encoding="utf-8")
        
        count = mgr.import_and_merge(import_path)
        assert count == 2
        assert mgr.load().get("import1") == "correct1"
