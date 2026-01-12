# tests/conftest.py
"""
Pytest configuration for ClaudeMemory tests.
"""

import getpass
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

# Register pytest-asyncio plugin
pytest_plugins = ('pytest_asyncio',)


SAFE_TMP_ROOT = Path(__file__).resolve().parent.parent / ".test_tmp"


def _safe_mkdtemp(suffix: str | None = None, prefix: str | None = None, dir: str | None = None) -> str:
    base = Path(dir) if dir else SAFE_TMP_ROOT
    base.mkdir(parents=True, exist_ok=True)
    name_prefix = "tmp" if prefix is None else prefix
    name_suffix = "" if suffix is None else suffix
    unique = uuid.uuid4().hex
    path = base / f"{name_prefix}{unique}{name_suffix}"
    path.mkdir(parents=True, exist_ok=False)
    return str(path)


class _SafeTemporaryDirectory:
    def __init__(self, suffix: str | None = None, prefix: str | None = None, dir: str | None = None):
        self.name = _safe_mkdtemp(suffix=suffix, prefix=prefix, dir=dir)

    def __enter__(self) -> str:
        return self.name

    def cleanup(self) -> None:
        shutil.rmtree(self.name, ignore_errors=True)

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()

    def __del__(self) -> None:
        self.cleanup()


# Override tempfile helpers to avoid restricted temp directories on Windows.
tempfile.tempdir = str(SAFE_TMP_ROOT)
tempfile.mkdtemp = _safe_mkdtemp  # type: ignore[assignment]
tempfile.TemporaryDirectory = _SafeTemporaryDirectory  # type: ignore[assignment]
os.environ["GIT_CEILING_DIRECTORIES"] = str(SAFE_TMP_ROOT)


def pytest_configure(config):
    """Configure custom pytest markers and ensure tmp directories exist."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio test."
    )

    # Ensure pytest's tmp_path base directory exists on all platforms
    # This fixes issues on Windows CI where getpass.getuser() returns "unknown"
    try:
        username = getpass.getuser()
    except Exception:
        username = "unknown"

    pytest_tmp_base = SAFE_TMP_ROOT / f"pytest-of-{username}"
    pytest_tmp_base.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Override tmp_path to use our safe temp root."""
    # Create a unique temp directory under our safe root
    path = Path(_safe_mkdtemp(prefix="pytest_"))
    yield path
    # Cleanup after test
    shutil.rmtree(path, ignore_errors=True)


async def ensure_protocol_compliance(project_path: str):
    """
    Helper to ensure protocol compliance for tests.

    Calls get_briefing() and context_check() to satisfy the Protocol
    requirements for tools that need initialization and/or context check.
    """
    from claude_memory import server

    # Ensure initialization (get_briefing)
    await server.get_briefing(project_path=project_path)

    # Ensure context check (context_check)
    await server.context_check(
        description="Test operation",
        project_path=project_path,
    )


# Backwards compatibility alias
ensure_covenant_compliance = ensure_protocol_compliance


@pytest.fixture
async def protocol_compliant_project(tmp_path):
    """
    Fixture that creates a project and ensures protocol compliance.

    Returns the project path that can be used with tools requiring
    initialization and/or context check.
    """
    from claude_memory.database import DatabaseManager
    from claude_memory import server

    project_path = str(tmp_path)
    storage_path = str(tmp_path / "storage")

    # Initialize database
    db_manager = DatabaseManager(storage_path)
    await db_manager.init_db()

    # Clear any cached contexts
    server._project_contexts.clear()

    # Ensure protocol compliance
    await ensure_protocol_compliance(project_path)

    yield project_path

    # Cleanup
    await db_manager.close()


# Backwards compatibility alias
covenant_compliant_project = protocol_compliant_project
