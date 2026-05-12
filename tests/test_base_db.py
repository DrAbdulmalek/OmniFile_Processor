"""Tests for modules.core.base_db.BaseDB"""
import pytest
import tempfile
import os
from pathlib import Path

class TestBaseDB:
    """Test BaseDB shared SQLite class."""
    
    def _make_db(self, tmp_path):
        """Create a test database subclass."""
        from modules.core.base_db import BaseDB
        
        class TestDB(BaseDB):
            def _create_schema(self, conn):
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        value REAL DEFAULT 0
                    )
                """)
        
        db_path = str(tmp_path / "test.db")
        return TestDB(db_path)
    
    def test_init_creates_db(self, tmp_path):
        db = self._make_db(tmp_path)
        assert Path(db.db_path).exists()
    
    def test_create_schema(self, tmp_path):
        db = self._make_db(tmp_path)
        assert db.table_exists("users")
        assert db.table_exists("items")
    
    def test_execute_write_and_read(self, tmp_path):
        db = self._make_db(tmp_path)
        row_id = db.execute_write(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("Alice", "alice@test.com")
        )
        assert row_id > 0
        
        rows = db.execute("SELECT * FROM users")
        assert len(rows) == 1
        assert rows[0]["name"] == "Alice"
    
    def test_execute_one(self, tmp_path):
        db = self._make_db(tmp_path)
        db.execute_write("INSERT INTO users (name, email) VALUES (?, ?)", ("Bob", "bob@test.com"))
        row = db.execute_one("SELECT * FROM users WHERE name=?", ("Bob",))
        assert row is not None
        assert row["email"] == "bob@test.com"
    
    def test_execute_one_not_found(self, tmp_path):
        db = self._make_db(tmp_path)
        row = db.execute_one("SELECT * FROM users WHERE name=?", ("Nobody",))
        assert row is None
    
    def test_executemany_write(self, tmp_path):
        db = self._make_db(tmp_path)
        data = [("Item1", 10.0), ("Item2", 20.0), ("Item3", 30.0)]
        count = db.executemany_write(
            "INSERT INTO items (name, value) VALUES (?, ?)", data
        )
        assert count == 3
        assert db.count("items") == 3
    
    def test_count(self, tmp_path):
        db = self._make_db(tmp_path)
        assert db.count("users") == 0
        db.execute_write("INSERT INTO users (name) VALUES (?)", ("A",))
        db.execute_write("INSERT INTO users (name) VALUES (?)", ("B",))
        assert db.count("users") == 2
    
    def test_count_with_where(self, tmp_path):
        db = self._make_db(tmp_path)
        db.execute_write("INSERT INTO items (name, value) VALUES (?, ?)", ("A", 10))
        db.execute_write("INSERT INTO items (name, value) VALUES (?, ?)", ("B", 20))
        assert db.count("items", "value > ?", (15,)) == 1
    
    def test_table_exists_false(self, tmp_path):
        db = self._make_db(tmp_path)
        assert not db.table_exists("nonexistent")
    
    def test_unique_constraint_raises(self, tmp_path):
        db = self._make_db(tmp_path)
        db.execute_write("INSERT INTO users (name, email) VALUES (?, ?)", ("A", "a@t.com"))
        with pytest.raises(Exception):  # UNIQUE constraint
            db.execute_write("INSERT INTO users (name, email) VALUES (?, ?)", ("B", "a@t.com"))
        # Original should still be there (rollback)
        assert db.count("users") == 1
    
    def test_migrate(self, tmp_path):
        db = self._make_db(tmp_path)
        applied = db.migrate(1, "ALTER TABLE users ADD COLUMN age INTEGER DEFAULT 0")
        assert applied is True
        # Second call should not re-apply
        applied2 = db.migrate(1, "ALTER TABLE users ADD COLUMN age INTEGER DEFAULT 0")
        assert applied2 is False
    
    def test_vacuum(self, tmp_path):
        db = self._make_db(tmp_path)
        db.vacuum()  # Should not raise
    
    def test_stats(self, tmp_path):
        db = self._make_db(tmp_path)
        db.execute_write("INSERT INTO users (name) VALUES (?)", ("A",))
        stats = db.stats()
        assert "db_path" in stats
        assert "tables" in stats
        assert stats["tables"]["users"] == 1
