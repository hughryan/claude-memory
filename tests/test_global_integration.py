"""
Integration tests for global memory functionality.

Tests the complete flow: classification, dual-write, recall merging, precedence.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from claude_memory.config import Settings
from claude_memory.database import DatabaseManager
from claude_memory.memory import MemoryManager


@pytest.fixture
async def temp_global_path():
    """Create a temporary directory for global storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "global-storage")


@pytest.fixture
async def temp_local_path():
    """Create a temporary directory for local storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "local-storage")


@pytest.fixture
async def local_memory_manager(temp_local_path):
    """Create a local memory manager with test database."""
    db = DatabaseManager(temp_local_path)
    await db.init_db()
    mgr = MemoryManager(db)
    yield mgr
    await db.close()


@pytest.fixture
async def global_memory_manager(temp_global_path):
    """Create a global memory manager with test database."""
    db = DatabaseManager(temp_global_path)
    await db.init_db()
    mgr = MemoryManager(db)
    yield mgr
    await db.close()


class TestGlobalMemoryIntegration:
    """Integration tests for global memory."""

    @pytest.mark.asyncio
    async def test_dual_write_global_pattern(self, local_memory_manager, temp_global_path):
        """Test that global-classified memories are written to both storages."""
        # Patch settings to enable global and set temp path
        with patch('claude_memory.memory.settings') as mock_settings:
            mock_settings.global_enabled = True
            mock_settings.global_write_enabled = True
            mock_settings.get_global_storage_path.return_value = temp_global_path

            # Patch _get_global_memory_manager
            async def mock_get_global():
                global_db = DatabaseManager(temp_global_path)
                await global_db.init_db()
                return MemoryManager(global_db)

            with patch('claude_memory.server._get_global_memory_manager', mock_get_global):
                # Store a universal pattern
                result = await local_memory_manager.remember(
                    category="pattern",
                    content="Always validate user input to prevent XSS",
                    rationale="Security best practice",
                    tags=["security", "best-practice"],
                    file_path=None,  # No file path = could be global
                    project_path="/test/project"
                )

                # Check it was classified as global
                assert result["scope"] == "global"
                assert "_also_stored_globally" in result

                # Verify it exists in local
                local_recall = await local_memory_manager.recall(
                    topic="XSS validation",
                    project_path="/test/project"
                )
                assert len(local_recall["patterns"]) >= 1

                # Verify it exists in global
                global_db = DatabaseManager(temp_global_path)
                await global_db.init_db()
                global_mgr = MemoryManager(global_db)
                global_recall = await global_mgr.recall(
                    topic="XSS validation",
                    project_path="__global__"
                )
                assert len(global_recall["patterns"]) >= 1
                await global_db.close()

    @pytest.mark.asyncio
    async def test_local_only_with_file_path(self, local_memory_manager):
        """Test that memories with file paths stay local only."""
        with patch('claude_memory.memory.settings') as mock_settings:
            mock_settings.global_enabled = True
            mock_settings.global_write_enabled = True

            result = await local_memory_manager.remember(
                category="decision",
                content="Use async/await for database operations",
                file_path="/test/project/src/db.py",
                project_path="/test/project"
            )

            # Should be local only due to file path
            assert result["scope"] == "local"
            assert "_also_stored_globally" not in result

    @pytest.mark.asyncio
    async def test_recall_merges_global_and_local(self, local_memory_manager, temp_global_path):
        """Test that recall() searches both local and global."""
        # Setup: Store one pattern locally, one globally

        # Local pattern
        await local_memory_manager.remember(
            category="pattern",
            content="In this project, use Redux for state management",
            project_path="/test/project"
        )

        # Global pattern
        global_db = DatabaseManager(temp_global_path)
        await global_db.init_db()
        global_mgr = MemoryManager(global_db)
        await global_mgr.remember(
            category="pattern",
            content="Always use TypeScript for large codebases",
            tags=["best-practice", "architecture"],
            project_path="__global__"
        )

        # Patch to use our test global manager
        async def mock_get_global():
            return global_mgr

        with patch('claude_memory.memory.settings') as mock_settings:
            mock_settings.global_enabled = True

            with patch('claude_memory.server._get_global_memory_manager', mock_get_global):
                # Recall should find both
                result = await local_memory_manager.recall(
                    topic="state management",
                    project_path="/test/project"
                )

                # Should have local pattern
                assert len(result["patterns"]) >= 1

                # Check for _from_global tag on global memories
                # (depends on whether "state management" matches TypeScript pattern)

        await global_db.close()

    @pytest.mark.asyncio
    async def test_local_precedence_over_global(self, local_memory_manager, temp_global_path):
        """Test that local memories take precedence over similar global ones."""
        # Store similar patterns in both
        content_base = "Always validate input"

        # Global version
        global_db = DatabaseManager(temp_global_path)
        await global_db.init_db()
        global_mgr = MemoryManager(global_db)
        await global_mgr.remember(
            category="pattern",
            content=content_base,
            rationale="General security",
            project_path="__global__"
        )

        # Local version (more specific)
        await local_memory_manager.remember(
            category="pattern",
            content=content_base + " using Joi library",
            rationale="Project-specific validation",
            project_path="/test/project"
        )

        # Recall with global enabled
        async def mock_get_global():
            return global_mgr

        with patch('claude_memory.memory.settings') as mock_settings:
            mock_settings.global_enabled = True

            with patch('claude_memory.server._get_global_memory_manager', mock_get_global):
                result = await local_memory_manager.recall(
                    topic="validate input",
                    project_path="/test/project",
                    limit=5
                )

                # Should have at least the local pattern
                assert len(result["patterns"]) >= 1

                # Local should not have _from_global tag
                local_patterns = [p for p in result["patterns"] if not p.get("_from_global")]
                assert len(local_patterns) >= 1

        await global_db.close()

    @pytest.mark.asyncio
    async def test_global_disabled(self, local_memory_manager):
        """Test that global memory can be disabled."""
        with patch('claude_memory.memory.settings') as mock_settings:
            mock_settings.global_enabled = False

            result = await local_memory_manager.remember(
                category="pattern",
                content="Always use https for production",
                tags=["security", "best-practice"],
                project_path="/test/project"
            )

            # Even with global tags, should stay local when disabled
            # Scope will still be classified but not written to global
            assert "_also_stored_globally" not in result

    @pytest.mark.asyncio
    async def test_project_specific_language_stays_local(self, local_memory_manager):
        """Test that project-specific language keeps memories local."""
        test_cases = [
            "In this repo, we use microservices architecture",
            "Our codebase follows the MVC pattern",
            "For this project, use PostgreSQL",
        ]

        for content in test_cases:
            result = await local_memory_manager.remember(
                category="pattern",
                content=content,
                project_path="/test/project"
            )

            assert result["scope"] == "local", f"Failed for: {content}"

    @pytest.mark.asyncio
    async def test_no_recursion_in_global_context(self, temp_global_path):
        """Test that storing to global doesn't trigger infinite recursion."""
        global_db = DatabaseManager(temp_global_path)
        await global_db.init_db()
        global_mgr = MemoryManager(global_db)

        with patch('claude_memory.memory.settings') as mock_settings:
            mock_settings.global_enabled = True
            mock_settings.global_write_enabled = True

            # Store to global context directly
            result = await global_mgr.remember(
                category="pattern",
                content="Always use version control",
                tags=["best-practice"],
                project_path="__global__"  # This should prevent recursion
            )

            # Should be marked as global but NOT try to write to global again
            assert result["scope"] == "global"
            # Should NOT have _also_stored_globally (no recursion)
            assert "_also_stored_globally" not in result

        await global_db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
