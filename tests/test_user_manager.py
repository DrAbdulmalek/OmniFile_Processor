"""Tests for modules.core.user_manager.UserManager"""
import pytest
import json

class TestUserManager:
    """Test UserManager with temp files."""
    
    def _make_manager(self, tmp_path):
        from modules.core.user_manager import UserManager
        users_file = str(tmp_path / "users.json")
        return UserManager(users_file=users_file)
    
    def test_add_user(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.add_user("user1", role="reviewer", name="Alice") is True
    
    def test_get_role(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add_user("user1", role="admin")
        assert mgr.get_role("user1") == "admin"
    
    def test_get_role_unknown(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.get_role("nobody") is None
    
    def test_is_active(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add_user("user1", role="reviewer")
        assert mgr.is_active("user1") is True
        assert mgr.is_active("nobody") is False
    
    def test_can_escalate_admin(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add_user("admin1", role="admin")
        assert mgr.can_escalate("admin1") is True
    
    def test_can_escalate_reviewer(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add_user("rev1", role="reviewer")
        assert mgr.can_escalate("rev1") is False
    
    def test_can_review(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        for role in ["admin", "curator", "reviewer"]:
            mgr.add_user(f"{role}_user", role=role)
            assert mgr.can_review(f"{role}_user") is True
        mgr.add_user("viewer1", role="viewer")
        assert mgr.can_review("viewer1") is False
    
    def test_list_reviewers(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add_user("rev1", role="reviewer")
        mgr.add_user("rev2", role="reviewer")
        mgr.add_user("admin1", role="admin")
        reviewers = mgr.list_reviewers()
        assert len(reviewers) == 3
    
    def test_deactivate(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add_user("user1", role="reviewer")
        assert mgr.deactivate("user1") is True
        assert mgr.is_active("user1") is False
    
    def test_persistence(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.add_user("user1", role="admin")
        # Reload
        mgr2 = self._make_manager(tmp_path)
        assert mgr2.get_role("user1") == "admin"
