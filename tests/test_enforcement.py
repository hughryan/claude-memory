"""Tests for enforcement models and session tracking."""

import pytest
from datetime import datetime, timezone

from daem0nmcp.models import SessionState, EnforcementBypassLog


class TestEnforcementModels:
    """Test the enforcement-related database models."""

    def test_session_state_model_exists(self):
        """SessionState model should exist with required fields."""
        session = SessionState(
            session_id="abc123-2025010112",
            project_path="/path/to/project",
            briefed=True,
            context_checks=["auth.py", "database"],
            pending_decisions=[1, 2, 3],
        )
        assert session.session_id == "abc123-2025010112"
        assert session.project_path == "/path/to/project"
        assert session.briefed is True
        assert session.context_checks == ["auth.py", "database"]
        assert session.pending_decisions == [1, 2, 3]

    def test_enforcement_bypass_log_model_exists(self):
        """EnforcementBypassLog model should exist with required fields."""
        log = EnforcementBypassLog(
            pending_decisions=[42, 43],
            staged_files_with_warnings=["src/auth.py"],
            reason="Emergency hotfix",
        )
        assert log.pending_decisions == [42, 43]
        assert log.staged_files_with_warnings == ["src/auth.py"]
        assert log.reason == "Emergency hotfix"
