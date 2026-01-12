"""Tests for Protocol enforcement."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from claude_memory.protocol import (
    ProtocolEnforcer,
    ProtocolViolation,
    PreflightToken,
    PROTOCOL_EXEMPT_TOOLS,
    INIT_REQUIRED_TOOLS,
    CONTEXT_CHECK_REQUIRED_TOOLS,
)


class TestProtocolViolation:
    """Test the ProtocolViolation response structure."""

    def test_init_required_response(self):
        """INIT_REQUIRED should include remedy."""
        response = ProtocolViolation.init_required("test_project")
        assert response["status"] == "blocked"
        assert response["violation"] == "INIT_REQUIRED"
        assert "remedy" in response
        assert response["remedy"]["tool"] == "get_briefing"

    def test_context_check_required_response(self):
        """CONTEXT_CHECK_REQUIRED should include action description."""
        response = ProtocolViolation.context_check_required("remember", "test_project")
        assert response["status"] == "blocked"
        assert response["violation"] == "CONTEXT_CHECK_REQUIRED"
        assert "remember" in response["message"]
        assert response["remedy"]["tool"] == "context_check"


class TestPreflightToken:
    """Test preflight token generation and validation."""

    def test_token_generation(self):
        """Token should be generated with signature."""
        token = PreflightToken.issue(
            action="editing src/auth.py",
            session_id="abc123-2025010112",
            project_path="/test/project",
        )
        assert token.action == "editing src/auth.py"
        assert token.session_id == "abc123-2025010112"
        assert token.signature is not None
        assert len(token.signature) == 64  # SHA256 hex

    def test_token_expiry(self):
        """Token should expire after TTL."""
        token = PreflightToken.issue(
            action="test",
            session_id="abc123",
            project_path="/test",
            ttl_seconds=1,
        )
        assert not token.is_expired()

        # Manually expire
        token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert token.is_expired()

    def test_token_verification(self):
        """Valid token should verify successfully."""
        token = PreflightToken.issue(
            action="editing src/auth.py",
            session_id="abc123",
            project_path="/test",
        )
        serialized = token.serialize()

        verified = PreflightToken.verify(serialized, project_path="/test")
        assert verified is not None
        assert verified.action == "editing src/auth.py"

    def test_token_tamper_detection(self):
        """Tampered token should fail verification."""
        token = PreflightToken.issue(
            action="editing src/auth.py",
            session_id="abc123",
            project_path="/test",
        )
        serialized = token.serialize()

        # Tamper with the token
        import json
        data = json.loads(serialized)
        data["action"] = "malicious action"
        tampered = json.dumps(data)

        verified = PreflightToken.verify(tampered, project_path="/test")
        assert verified is None


class TestProtocolEnforcer:
    """Test the enforcement decorators."""

    @pytest.fixture
    def mock_session_state(self):
        """Create mock session state."""
        return {
            "session_id": "abc123-2025010112",
            "project_path": "/test/project",
            "briefed": False,
            "context_checks": [],
            "pending_decisions": [],
        }

    @pytest.fixture
    def briefed_session_state(self, mock_session_state):
        """Session that has been briefed."""
        mock_session_state["briefed"] = True
        return mock_session_state

    @pytest.fixture
    def context_checked_session_state(self, briefed_session_state):
        """Session with context check performed."""
        briefed_session_state["context_checks"] = [
            {"topic": "remember", "timestamp": datetime.now(timezone.utc).isoformat()}
        ]
        return briefed_session_state

    @pytest.mark.asyncio
    async def test_requires_init_blocks_unbriefed(self, mock_session_state):
        """Tool should be blocked if not briefed."""
        enforcer = ProtocolEnforcer()

        with patch.object(enforcer, '_get_session_state', return_value=mock_session_state):
            result = await enforcer.check_init("/test/project")

        assert result is not None
        assert result["violation"] == "INIT_REQUIRED"

    @pytest.mark.asyncio
    async def test_requires_init_allows_briefed(self, briefed_session_state):
        """Tool should be allowed if briefed."""
        enforcer = ProtocolEnforcer()

        with patch.object(enforcer, '_get_session_state', return_value=briefed_session_state):
            result = await enforcer.check_init("/test/project")

        assert result is None  # No violation

    @pytest.mark.asyncio
    async def test_requires_context_check_blocks_without_check(self, briefed_session_state):
        """Tool should be blocked if no recent context_check."""
        enforcer = ProtocolEnforcer()

        with patch.object(enforcer, '_get_session_state', return_value=briefed_session_state):
            result = await enforcer.check_context("remember", "/test/project")

        assert result is not None
        assert result["violation"] == "CONTEXT_CHECK_REQUIRED"

    @pytest.mark.asyncio
    async def test_requires_context_check_allows_with_check(self, context_checked_session_state):
        """Tool should be allowed with recent context_check."""
        enforcer = ProtocolEnforcer()

        with patch.object(enforcer, '_get_session_state', return_value=context_checked_session_state):
            result = await enforcer.check_context("remember", "/test/project")

        assert result is None  # No violation

    def test_exempt_tools_list(self):
        """get_briefing and health should be exempt."""
        assert "get_briefing" in PROTOCOL_EXEMPT_TOOLS
        assert "health" in PROTOCOL_EXEMPT_TOOLS

    def test_init_required_tools_list(self):
        """Mutating tools should require initialization."""
        assert "remember" in INIT_REQUIRED_TOOLS
        assert "remember_batch" in INIT_REQUIRED_TOOLS
        assert "add_rule" in INIT_REQUIRED_TOOLS
        assert "update_rule" in INIT_REQUIRED_TOOLS
        assert "record_outcome" in INIT_REQUIRED_TOOLS
        assert "prune_memories" in INIT_REQUIRED_TOOLS

    def test_context_check_required_tools_list(self):
        """Mutating tools should require context check."""
        assert "remember" in CONTEXT_CHECK_REQUIRED_TOOLS
        assert "remember_batch" in CONTEXT_CHECK_REQUIRED_TOOLS
        assert "add_rule" in CONTEXT_CHECK_REQUIRED_TOOLS
        assert "prune_memories" in CONTEXT_CHECK_REQUIRED_TOOLS


class TestPreflightTokenIntegration:
    """Test preflight token in context_check response."""

    @pytest.fixture
    def db_manager(self, tmp_path):
        from claude_memory.database import DatabaseManager
        return DatabaseManager(str(tmp_path / "storage"))

    @pytest.mark.asyncio
    async def test_context_check_returns_preflight_token(self, db_manager):
        """context_check should include a preflight_token."""
        await db_manager.init_db()

        from claude_memory import server
        server._project_contexts.clear()

        project_path = str(db_manager.storage_path.parent.parent)

        # Briefing first
        await server.get_briefing(project_path=project_path)

        # context_check should return token
        result = await server.context_check(
            description="About to edit auth.py",
            project_path=project_path,
        )

        assert "preflight_token" in result

        # Verify token is valid
        from claude_memory.protocol import PreflightToken
        token = PreflightToken.verify(result["preflight_token"], project_path)
        assert token is not None
        assert token.action == "About to edit auth.py"
