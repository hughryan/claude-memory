"""Integration tests for Protocol enforcement on MCP tools."""

import pytest
from unittest.mock import patch, AsyncMock

from claude_memory.protocol import INIT_REQUIRED_TOOLS, CONTEXT_CHECK_REQUIRED_TOOLS


class TestProtocolIntegration:
    """Test that tools are properly decorated with enforcement."""

    @pytest.fixture
    def db_manager(self, tmp_path):
        from claude_memory.database import DatabaseManager
        return DatabaseManager(str(tmp_path / "storage"))

    @pytest.fixture
    def memory_mgr(self, db_manager):
        from claude_memory.memory import MemoryManager
        return MemoryManager(db_manager)

    @pytest.mark.asyncio
    async def test_remember_blocked_without_briefing(self, db_manager, memory_mgr):
        """remember() should be blocked if get_briefing not called."""
        await db_manager.init_db()

        from claude_memory import server
        server._project_contexts.clear()

        result = await server.remember(
            category="decision",
            content="Test decision",
            project_path=str(db_manager.storage_path.parent.parent),
        )

        assert result.get("status") == "blocked"
        assert result.get("violation") == "INIT_REQUIRED"

    @pytest.mark.asyncio
    async def test_remember_blocked_without_context_check(self, db_manager, memory_mgr):
        """remember() should be blocked if context_check not called after briefing."""
        await db_manager.init_db()

        from claude_memory import server
        server._project_contexts.clear()

        project_path = str(db_manager.storage_path.parent.parent)

        await server.get_briefing(project_path=project_path)

        result = await server.remember(
            category="decision",
            content="Test decision",
            project_path=project_path,
        )

        assert result.get("status") == "blocked"
        assert result.get("violation") == "CONTEXT_CHECK_REQUIRED"

    @pytest.mark.asyncio
    async def test_remember_allowed_with_full_protocol(self, db_manager, memory_mgr):
        """remember() should work after briefing + context_check."""
        await db_manager.init_db()

        from claude_memory import server
        server._project_contexts.clear()

        project_path = str(db_manager.storage_path.parent.parent)

        await server.get_briefing(project_path=project_path)
        await server.context_check(
            description="About to record a decision",
            project_path=project_path,
        )

        result = await server.remember(
            category="decision",
            content="Test decision",
            project_path=project_path,
        )

        assert "id" in result
        assert result.get("status") != "blocked"

    @pytest.mark.asyncio
    async def test_recall_allowed_with_briefing_only(self, db_manager, memory_mgr):
        """recall() should work after briefing (no context check required)."""
        await db_manager.init_db()

        from claude_memory import server
        server._project_contexts.clear()

        project_path = str(db_manager.storage_path.parent.parent)

        await server.get_briefing(project_path=project_path)

        result = await server.recall(
            topic="test",
            project_path=project_path,
        )

        assert result.get("status") != "blocked"

    @pytest.mark.asyncio
    async def test_health_always_allowed(self, db_manager):
        """health() should work without any protocol compliance."""
        await db_manager.init_db()

        from claude_memory import server
        server._project_contexts.clear()

        project_path = str(db_manager.storage_path.parent.parent)

        result = await server.health(project_path=project_path)

        assert "version" in result
        assert result.get("status") != "blocked"
