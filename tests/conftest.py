"""Shared pytest fixtures for OmniFile tests."""
import pytest
import json
from pathlib import Path


@pytest.fixture
def sample_arabic_fixes(tmp_path):
    """Create a sample arabic_fixes.json file."""
    fixes = {"مرحبا": "مرحبا", "العالم": "العالم"}
    path = tmp_path / "arabic_fixes.json"
    path.write_text(json.dumps(fixes, ensure_ascii=False), encoding="utf-8")
    return str(path)


@pytest.fixture
def sample_corrections(tmp_path):
    """Create a sample corrections dictionary file."""
    corrections = {"خطأ": "صواب", "اخطاء": "أخطاء"}
    path = tmp_path / "corrections.json"
    path.write_text(json.dumps(corrections, ensure_ascii=False), encoding="utf-8")
    return str(path)


@pytest.fixture
def sample_users(tmp_path):
    """Create a sample users.json file."""
    users = {
        "user1": {"role": "admin", "name": "Admin", "active": True},
        "user2": {"role": "reviewer", "name": "Reviewer", "active": True},
    }
    path = tmp_path / "users.json"
    path.write_text(json.dumps(users, ensure_ascii=False), encoding="utf-8")
    return str(path)
