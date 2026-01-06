"""Tests for memory community clustering and hierarchical summaries."""

import pytest
import tempfile
import shutil
from datetime import datetime, timezone

from daem0nmcp.models import MemoryCommunity


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestMemoryCommunityModel:
    """Test the MemoryCommunity model structure."""

    def test_memory_community_has_required_fields(self):
        """MemoryCommunity should have all required fields."""
        community = MemoryCommunity(
            project_path="/test/project",
            name="Authentication",
            summary="Decisions and patterns related to user authentication",
            tags=["auth", "security", "jwt"],
            member_count=5,
            level=0
        )

        assert community.project_path == "/test/project"
        assert community.name == "Authentication"
        assert community.summary == "Decisions and patterns related to user authentication"
        assert "auth" in community.tags
        assert community.member_count == 5
        assert community.level == 0

    def test_memory_community_default_values(self):
        """MemoryCommunity should have correct default values for optional fields."""
        community = MemoryCommunity(
            project_path="/test/project",
            name="Test Community",
            summary="Test summary"
        )

        # Check default values
        # Note: SQLAlchemy defaults apply at database level, not at object instantiation
        # So we check that these fields can be None or are set to their defaults
        assert community.member_ids == [] or community.member_ids is None, \
            "member_ids should default to empty list or None"
        assert community.parent_id is None, \
            "parent_id should be None by default"
        assert community.vector_embedding is None, \
            "vector_embedding should be None by default"
        # member_count and level may be None until persisted to database
        assert community.member_count is None or community.member_count == 0, \
            "member_count should be None or 0 by default"
        assert community.level is None or community.level == 0, \
            "level should be None or 0 by default"
        assert community.tags == [] or community.tags is None, \
            "tags should default to empty list or None"


@pytest.mark.asyncio
async def test_memory_communities_table_created(temp_storage):
    """Verify memory_communities table is created during database initialization."""
    from daem0nmcp.database import DatabaseManager

    db = DatabaseManager(temp_storage)
    await db.init_db()

    async with db.get_session() as session:
        from sqlalchemy import text
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_communities'")
        )
        tables = result.fetchall()

    await db.close()
    assert len(tables) == 1
    assert tables[0][0] == "memory_communities"
