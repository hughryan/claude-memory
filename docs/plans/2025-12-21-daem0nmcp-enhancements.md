# Daem0nMCP v2.3 Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add robustness, scalability, and maintenance features to Daem0nMCP including concurrency safety, index freshness, ingestion hardening, search upgrades, and operational tooling.

**Architecture:** Six phases targeting different concerns: (1) concurrency/context management, (2) index consistency, (3) ingestion safety, (4) search performance, (5) operational tools, (6) test coverage and CI. Each phase is independent and can be merged separately.

**Tech Stack:** Python 3.10+, SQLAlchemy 2.0, SQLite FTS5, asyncio, pytest, GitHub Actions

---

## Phase 1: Project Context Management

### Task 1.1: Add asyncio.Lock for Context Initialization

**Files:**
- Modify: `daem0nmcp/server.py:82-98` (ProjectContext dataclass)
- Modify: `daem0nmcp/server.py:126-186` (get_project_context function)
- Test: `tests/test_context.py` (new file)

**Step 1: Write the failing test**

Create `tests/test_context.py`:

```python
"""Tests for project context management."""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from pathlib import Path
import tempfile
import shutil


class TestProjectContextConcurrency:
    """Test concurrent access to project contexts."""

    @pytest.fixture
    def temp_projects(self):
        """Create temporary project directories."""
        dirs = [tempfile.mkdtemp() for _ in range(3)]
        yield dirs
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_concurrent_context_creation_uses_lock(self, temp_projects):
        """Verify that concurrent calls to get_project_context don't race."""
        from daem0nmcp.server import get_project_context, _project_contexts

        # Clear existing contexts
        _project_contexts.clear()

        project_path = temp_projects[0]

        # Track how many times init_db is called
        init_count = 0
        original_init = None

        async def counting_init(self):
            nonlocal init_count
            init_count += 1
            await asyncio.sleep(0.1)  # Simulate slow init
            if original_init:
                await original_init(self)

        # Patch init_db to count calls
        from daem0nmcp.database import DatabaseManager
        original_init = DatabaseManager.init_db

        with patch.object(DatabaseManager, 'init_db', counting_init):
            # Launch concurrent requests
            tasks = [get_project_context(project_path) for _ in range(5)]
            contexts = await asyncio.gather(*tasks)

        # All should return the same context
        assert all(c is contexts[0] for c in contexts)
        # init_db should only be called once due to locking
        assert init_count == 1, f"init_db called {init_count} times, expected 1"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_context.py::TestProjectContextConcurrency::test_concurrent_context_creation_uses_lock -v`
Expected: FAIL (no lock exists yet, init_db called multiple times)

**Step 3: Add lock to ProjectContext and get_project_context**

Modify `daem0nmcp/server.py`:

```python
# At top of file, add import
import asyncio

# Modify ProjectContext dataclass (around line 82)
@dataclass
class ProjectContext:
    """Holds all managers for a specific project."""
    project_path: str
    storage_path: str
    db_manager: DatabaseManager
    memory_manager: MemoryManager
    rules_engine: RulesEngine
    initialized: bool = False
    last_accessed: float = 0.0  # For LRU tracking


# Add module-level lock dict (after _project_contexts)
_project_contexts: Dict[str, ProjectContext] = {}
_context_locks: Dict[str, asyncio.Lock] = {}
_contexts_lock = asyncio.Lock()  # Lock for modifying the dicts themselves


async def get_project_context(project_path: Optional[str] = None) -> ProjectContext:
    """
    Get or create a ProjectContext for the given project path.
    Thread-safe with per-project locking to prevent race conditions.
    """
    import time

    if not project_path:
        project_path = _default_project_path

    if not project_path:
        raise ValueError("project_path is required when DAEM0NMCP_PROJECT_ROOT is not set")

    normalized = _normalize_path(project_path)

    # Fast path: context exists and is initialized
    if normalized in _project_contexts:
        ctx = _project_contexts[normalized]
        if ctx.initialized:
            ctx.last_accessed = time.time()
            return ctx

    # Get or create lock for this project
    async with _contexts_lock:
        if normalized not in _context_locks:
            _context_locks[normalized] = asyncio.Lock()
        lock = _context_locks[normalized]

    # Initialize under project-specific lock
    async with lock:
        # Double-check after acquiring lock
        if normalized in _project_contexts:
            ctx = _project_contexts[normalized]
            if ctx.initialized:
                ctx.last_accessed = time.time()
                return ctx

        # Create new context
        storage_path = _get_storage_for_project(normalized)
        db_mgr = DatabaseManager(storage_path)
        mem_mgr = MemoryManager(db_mgr)
        rules_eng = RulesEngine(db_mgr)

        ctx = ProjectContext(
            project_path=normalized,
            storage_path=storage_path,
            db_manager=db_mgr,
            memory_manager=mem_mgr,
            rules_engine=rules_eng,
            initialized=False,
            last_accessed=time.time()
        )

        # Initialize database
        await db_mgr.init_db()
        ctx.initialized = True

        _project_contexts[normalized] = ctx
        logger.info(f"Created project context for: {normalized}")

        return ctx
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_context.py::TestProjectContextConcurrency::test_concurrent_context_creation_uses_lock -v`
Expected: PASS

**Step 5: Commit**

```bash
git add daem0nmcp/server.py tests/test_context.py
git commit -m "feat: add asyncio.Lock for project context initialization

Prevents race conditions when multiple concurrent requests try to
initialize the same project context simultaneously."
```

---

### Task 1.2: Add LRU/TTL Eviction for Project Contexts

**Files:**
- Modify: `daem0nmcp/server.py` (add eviction logic)
- Modify: `daem0nmcp/config.py` (add config options)
- Test: `tests/test_context.py` (add eviction tests)

**Step 1: Write the failing test**

Add to `tests/test_context.py`:

```python
class TestProjectContextEviction:
    """Test LRU/TTL eviction for project contexts."""

    @pytest.fixture
    def temp_projects(self):
        """Create multiple temporary project directories."""
        dirs = [tempfile.mkdtemp() for _ in range(5)]
        yield dirs
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_lru_eviction_when_max_contexts_exceeded(self, temp_projects):
        """Verify oldest contexts are evicted when max is exceeded."""
        from daem0nmcp.server import (
            get_project_context, _project_contexts,
            evict_stale_contexts, MAX_PROJECT_CONTEXTS
        )

        _project_contexts.clear()

        # Create contexts up to max + 2
        for i, project_path in enumerate(temp_projects[:MAX_PROJECT_CONTEXTS + 2]):
            ctx = await get_project_context(project_path)
            ctx.last_accessed = i  # Simulate access order

        # Evict stale contexts
        evicted = await evict_stale_contexts()

        # Should have evicted oldest contexts
        assert len(_project_contexts) <= MAX_PROJECT_CONTEXTS
        assert evicted >= 2

    @pytest.mark.asyncio
    async def test_ttl_eviction_for_old_contexts(self, temp_projects):
        """Verify contexts older than TTL are evicted."""
        import time
        from daem0nmcp.server import (
            get_project_context, _project_contexts,
            evict_stale_contexts, CONTEXT_TTL_SECONDS
        )

        _project_contexts.clear()

        # Create a context with old last_accessed time
        ctx = await get_project_context(temp_projects[0])
        ctx.last_accessed = time.time() - CONTEXT_TTL_SECONDS - 100

        # Create a recent context
        ctx2 = await get_project_context(temp_projects[1])

        # Evict
        await evict_stale_contexts()

        # Old context should be gone, new one should remain
        assert len(_project_contexts) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_context.py::TestProjectContextEviction -v`
Expected: FAIL (evict_stale_contexts, MAX_PROJECT_CONTEXTS, CONTEXT_TTL_SECONDS don't exist)

**Step 3: Add eviction configuration and function**

Add to `daem0nmcp/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Context management
    max_project_contexts: int = 10  # Maximum cached project contexts
    context_ttl_seconds: int = 3600  # 1 hour TTL for unused contexts
```

Add to `daem0nmcp/server.py` after get_project_context:

```python
# Configuration constants (read from settings)
MAX_PROJECT_CONTEXTS = settings.max_project_contexts if hasattr(settings, 'max_project_contexts') else 10
CONTEXT_TTL_SECONDS = settings.context_ttl_seconds if hasattr(settings, 'context_ttl_seconds') else 3600


async def evict_stale_contexts() -> int:
    """
    Evict stale project contexts based on LRU and TTL policies.

    Returns the number of contexts evicted.
    """
    import time

    evicted = 0
    now = time.time()

    async with _contexts_lock:
        # First pass: TTL eviction
        ttl_expired = [
            path for path, ctx in _project_contexts.items()
            if (now - ctx.last_accessed) > CONTEXT_TTL_SECONDS
        ]

        for path in ttl_expired:
            ctx = _project_contexts.pop(path)
            try:
                await ctx.db_manager.close()
            except Exception as e:
                logger.warning(f"Error closing context for {path}: {e}")
            evicted += 1
            logger.info(f"Evicted TTL-expired context: {path}")

        # Second pass: LRU eviction if still over limit
        while len(_project_contexts) > MAX_PROJECT_CONTEXTS:
            # Find oldest context
            oldest_path = min(
                _project_contexts.keys(),
                key=lambda p: _project_contexts[p].last_accessed
            )
            ctx = _project_contexts.pop(oldest_path)
            try:
                await ctx.db_manager.close()
            except Exception as e:
                logger.warning(f"Error closing context for {oldest_path}: {e}")
            evicted += 1
            logger.info(f"Evicted LRU context: {oldest_path}")

        # Clean up orphaned locks
        orphaned_locks = set(_context_locks.keys()) - set(_project_contexts.keys())
        for path in orphaned_locks:
            del _context_locks[path]

    return evicted
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_context.py::TestProjectContextEviction -v`
Expected: PASS

**Step 5: Commit**

```bash
git add daem0nmcp/server.py daem0nmcp/config.py tests/test_context.py
git commit -m "feat: add LRU/TTL eviction for project contexts

- Add MAX_PROJECT_CONTEXTS (default 10) and CONTEXT_TTL_SECONDS (default 3600)
- Add evict_stale_contexts() to clean up unused contexts
- Prevents unbounded memory growth in long-running servers"
```

---

## Phase 2: Index Freshness

### Task 2.1: Track Database Modification Timestamps

**Files:**
- Modify: `daem0nmcp/database.py` (add timestamp tracking)
- Modify: `daem0nmcp/memory.py` (check freshness before using index)
- Modify: `daem0nmcp/rules.py` (check freshness before using index)
- Test: `tests/test_index_freshness.py` (new file)

**Step 1: Write the failing test**

Create `tests/test_index_freshness.py`:

```python
"""Tests for index freshness tracking."""

import pytest
import tempfile
import shutil
from datetime import datetime, timezone


class TestIndexFreshness:
    """Test that indexes are rebuilt when DB changes."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_memory_index_rebuilds_after_external_change(self, temp_storage):
        """Verify TF-IDF index rebuilds when DB is modified externally."""
        from daem0nmcp.database import DatabaseManager
        from daem0nmcp.memory import MemoryManager

        db = DatabaseManager(temp_storage)
        await db.init_db()
        manager = MemoryManager(db)

        # Add a memory and trigger index build
        await manager.remember(
            category="decision",
            content="Use PostgreSQL for database",
            tags=["database"]
        )
        result1 = await manager.recall("PostgreSQL")
        assert result1["found"] >= 1

        # Simulate external modification (another process added a memory)
        import sqlite3
        conn = sqlite3.connect(str(db.db_path))
        conn.execute("""
            INSERT INTO memories (category, content, keywords, tags, context, created_at, updated_at)
            VALUES ('decision', 'Use Redis for caching', 'redis caching', '["cache"]', '{}',
                    datetime('now'), datetime('now'))
        """)
        conn.commit()
        conn.close()

        # Force freshness check - should detect change and rebuild
        await manager._check_index_freshness()

        # Now search should find the new memory
        result2 = await manager.recall("Redis caching")
        assert result2["found"] >= 1

        await db.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_index_freshness.py -v`
Expected: FAIL (_check_index_freshness doesn't exist)

**Step 3: Add freshness tracking to DatabaseManager**

Modify `daem0nmcp/database.py`:

```python
class DatabaseManager:
    def __init__(self, storage_path: str = "./storage", db_name: str = "daem0nmcp.db"):
        # ... existing init ...
        self._last_known_update: Optional[datetime] = None

    async def get_last_update_time(self) -> Optional[datetime]:
        """Get the most recent updated_at from memories and rules."""
        async with self.get_session() as session:
            from sqlalchemy import select, func
            from .models import Memory, Rule

            # Get max updated_at from memories
            mem_result = await session.execute(
                select(func.max(Memory.updated_at))
            )
            mem_time = mem_result.scalar()

            # Get max created_at from rules (rules don't have updated_at)
            rule_result = await session.execute(
                select(func.max(Rule.created_at))
            )
            rule_time = rule_result.scalar()

            # Return the most recent
            times = [t for t in [mem_time, rule_time] if t is not None]
            return max(times) if times else None

    async def has_changes_since(self, since: Optional[datetime]) -> bool:
        """Check if database has changes since the given timestamp."""
        if since is None:
            return True

        current = await self.get_last_update_time()
        if current is None:
            return False

        return current > since
```

**Step 4: Add freshness check to MemoryManager**

Modify `daem0nmcp/memory.py`:

```python
class MemoryManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._index: Optional[TFIDFIndex] = None
        self._vector_index: Optional[vectors.VectorIndex] = None
        self._index_loaded = False
        self._vectors_enabled = vectors.is_available()
        self._index_built_at: Optional[datetime] = None  # Track when index was built

    async def _check_index_freshness(self) -> bool:
        """
        Check if index needs rebuilding due to external DB changes.
        Returns True if index was rebuilt.
        """
        if not self._index_loaded:
            return False

        if await self.db.has_changes_since(self._index_built_at):
            logger.info("Database changed since index was built, rebuilding...")
            self._index_loaded = False
            self._index = None
            self._vector_index = None
            await self._ensure_index()
            return True

        return False

    async def _ensure_index(self) -> TFIDFIndex:
        """Ensure the TF-IDF index is loaded with all memories."""
        if self._index is None:
            self._index = TFIDFIndex()

        if self._vector_index is None:
            self._vector_index = vectors.VectorIndex()

        if not self._index_loaded:
            from datetime import datetime, timezone

            async with self.db.get_session() as session:
                result = await session.execute(select(Memory))
                memories = result.scalars().all()

                for mem in memories:
                    text = mem.content
                    if mem.rationale:
                        text += " " + mem.rationale
                    self._index.add_document(mem.id, text, mem.tags)

                    if self._vectors_enabled and mem.vector_embedding:
                        self._vector_index.add_from_bytes(mem.id, mem.vector_embedding)

                self._index_loaded = True
                self._index_built_at = datetime.now(timezone.utc)
                vector_count = len(self._vector_index) if self._vector_index else 0
                logger.info(f"Loaded {len(memories)} memories into TF-IDF index ({vector_count} with vectors)")

        return self._index
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_index_freshness.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add daem0nmcp/database.py daem0nmcp/memory.py tests/test_index_freshness.py
git commit -m "feat: add index freshness tracking

- Track last update time from memories and rules tables
- Rebuild TF-IDF/vector indexes when external changes detected
- Enables consistent multi-process usage"
```

---

### Task 2.2: Add rebuild_index Tool

**Files:**
- Modify: `daem0nmcp/server.py` (add rebuild_index tool)
- Test: `tests/test_index_freshness.py` (add tool test)

**Step 1: Write the failing test**

Add to `tests/test_index_freshness.py`:

```python
@pytest.mark.asyncio
async def test_rebuild_index_tool(self, temp_storage):
    """Test the rebuild_index MCP tool."""
    from daem0nmcp.database import DatabaseManager
    from daem0nmcp.memory import MemoryManager
    from daem0nmcp.rules import RulesEngine

    db = DatabaseManager(temp_storage)
    await db.init_db()
    memory = MemoryManager(db)
    rules = RulesEngine(db)

    # Add some data
    await memory.remember(category="decision", content="Test memory")
    await rules.add_rule(trigger="test trigger", must_do=["test action"])

    # Force index build
    await memory.recall("test")
    await rules.check_rules("test")

    # Rebuild should work
    result = await memory.rebuild_index()
    assert result["memories_indexed"] >= 1

    result = await rules.rebuild_index()
    assert result["rules_indexed"] >= 1

    await db.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_index_freshness.py::TestIndexFreshness::test_rebuild_index_tool -v`
Expected: FAIL (rebuild_index method doesn't exist)

**Step 3: Add rebuild_index methods**

Add to `daem0nmcp/memory.py`:

```python
async def rebuild_index(self) -> Dict[str, Any]:
    """
    Force rebuild of TF-IDF and vector indexes.

    Returns statistics about the rebuild.
    """
    from datetime import datetime, timezone

    # Clear existing index
    self._index = TFIDFIndex()
    self._vector_index = vectors.VectorIndex() if self._vectors_enabled else None
    self._index_loaded = False

    # Rebuild
    async with self.db.get_session() as session:
        result = await session.execute(select(Memory))
        memories = result.scalars().all()

        for mem in memories:
            text = mem.content
            if mem.rationale:
                text += " " + mem.rationale
            self._index.add_document(mem.id, text, mem.tags)

            if self._vectors_enabled and self._vector_index and mem.vector_embedding:
                self._vector_index.add_from_bytes(mem.id, mem.vector_embedding)

    self._index_loaded = True
    self._index_built_at = datetime.now(timezone.utc)

    return {
        "memories_indexed": len(memories),
        "vectors_indexed": len(self._vector_index) if self._vector_index else 0,
        "built_at": self._index_built_at.isoformat()
    }
```

Add to `daem0nmcp/rules.py`:

```python
async def rebuild_index(self) -> Dict[str, Any]:
    """Force rebuild of TF-IDF index for rules."""
    from datetime import datetime, timezone

    self._index = TFIDFIndex()
    self._index_loaded = False

    async with self.db.get_session() as session:
        result = await session.execute(
            select(Rule).where(Rule.enabled == True)
        )
        rules = result.scalars().all()

        for rule in rules:
            self._index.add_document(rule.id, rule.trigger)

    self._index_loaded = True

    return {
        "rules_indexed": len(rules),
        "built_at": datetime.now(timezone.utc).isoformat()
    }
```

**Step 4: Add MCP tool in server.py**

Add after existing tools:

```python
@mcp.tool()
async def rebuild_index(
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Force rebuild of all search indexes.

    Use this if search results seem stale or after bulk database operations.
    Rebuilds both memory TF-IDF/vector indexes and rule indexes.

    Args:
        project_path: Project root path

    Returns:
        Statistics about the rebuild
    """
    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    ctx = await get_project_context(project_path)

    memory_stats = await ctx.memory_manager.rebuild_index()
    rules_stats = await ctx.rules_engine.rebuild_index()

    return {
        "status": "rebuilt",
        "memories": memory_stats,
        "rules": rules_stats,
        "message": f"Rebuilt indexes: {memory_stats['memories_indexed']} memories, {rules_stats['rules_indexed']} rules"
    }
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_index_freshness.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add daem0nmcp/memory.py daem0nmcp/rules.py daem0nmcp/server.py tests/test_index_freshness.py
git commit -m "feat: add rebuild_index tool for manual index refresh

- Add rebuild_index() method to MemoryManager and RulesEngine
- Add rebuild_index MCP tool for manual triggering
- Useful after bulk operations or when search seems stale"
```

---

## Phase 3: Ingestion Hardening

### Task 3.1: Add URL Scheme Allowlist and Request Limits

**Files:**
- Modify: `daem0nmcp/server.py` (harden ingest_doc)
- Modify: `daem0nmcp/config.py` (add config options)
- Test: `tests/test_ingest.py` (new file)

**Step 1: Write the failing test**

Create `tests/test_ingest.py`:

```python
"""Tests for document ingestion hardening."""

import pytest
from unittest.mock import patch, MagicMock


class TestIngestDocHardening:
    """Test ingestion security and limits."""

    @pytest.mark.asyncio
    async def test_rejects_non_http_schemes(self):
        """Verify that file://, ftp://, etc. are rejected."""
        from daem0nmcp.server import ingest_doc

        # These should all be rejected
        bad_urls = [
            "file:///etc/passwd",
            "ftp://example.com/file.txt",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
        ]

        for url in bad_urls:
            result = await ingest_doc(
                url=url,
                topic="test",
                project_path="/tmp/test"
            )
            assert "error" in result, f"Should reject {url}"
            assert "scheme" in result["error"].lower() or "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_enforces_content_size_limit(self):
        """Verify large responses are truncated."""
        from daem0nmcp.server import _fetch_and_extract, MAX_CONTENT_SIZE

        # Mock a response that's too large
        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = "x" * (MAX_CONTENT_SIZE + 1000)
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = _fetch_and_extract("https://example.com/large")

            # Should be truncated
            assert result is None or len(result) <= MAX_CONTENT_SIZE

    @pytest.mark.asyncio
    async def test_enforces_chunk_limit(self):
        """Verify total chunks are limited."""
        from daem0nmcp.server import ingest_doc, MAX_CHUNKS

        with patch('daem0nmcp.server._fetch_and_extract') as mock_fetch:
            # Return content that would create many chunks
            mock_fetch.return_value = "word " * 100000  # Lots of words

            result = await ingest_doc(
                url="https://example.com/huge",
                topic="test",
                chunk_size=100,
                project_path="/tmp/test"
            )

            if "error" not in result:
                assert result["chunks_created"] <= MAX_CHUNKS
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest.py -v`
Expected: FAIL (MAX_CONTENT_SIZE, MAX_CHUNKS don't exist, no URL validation)

**Step 3: Add configuration constants**

Add to `daem0nmcp/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Ingestion limits
    max_content_size: int = 1_000_000  # 1MB max content
    max_chunks: int = 50  # Maximum chunks per ingestion
    ingest_timeout: int = 30  # Request timeout in seconds
    allowed_url_schemes: List[str] = ["http", "https"]
```

**Step 4: Harden _fetch_and_extract and ingest_doc**

Modify `daem0nmcp/server.py`:

```python
# Add constants after imports
MAX_CONTENT_SIZE = getattr(settings, 'max_content_size', 1_000_000)
MAX_CHUNKS = getattr(settings, 'max_chunks', 50)
INGEST_TIMEOUT = getattr(settings, 'ingest_timeout', 30)
ALLOWED_URL_SCHEMES = getattr(settings, 'allowed_url_schemes', ['http', 'https'])


def _validate_url(url: str) -> Optional[str]:
    """
    Validate URL for ingestion.
    Returns error message if invalid, None if valid.
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL format"

    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        return f"Invalid URL scheme '{parsed.scheme}'. Allowed: {ALLOWED_URL_SCHEMES}"

    if not parsed.netloc:
        return "URL must have a host"

    return None


def _fetch_and_extract(url: str) -> Optional[str]:
    """Fetch URL and extract text content with size limits."""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    try:
        with httpx.Client(timeout=float(INGEST_TIMEOUT), follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

            # Check content length header first
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_CONTENT_SIZE:
                logger.warning(f"Content too large: {content_length} bytes")
                return None

            # Truncate if response is too large
            text = response.text
            if len(text) > MAX_CONTENT_SIZE:
                logger.warning(f"Truncating content from {len(text)} to {MAX_CONTENT_SIZE}")
                text = text[:MAX_CONTENT_SIZE]

            soup = BeautifulSoup(text, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Get text
            text = soup.get_text(separator='\n', strip=True)

            # Clean up whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)

    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


# Modify ingest_doc tool
@mcp.tool()
async def ingest_doc(
    url: str,
    topic: str,
    chunk_size: int = 2000,
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """..."""  # Keep existing docstring

    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    # Validate URL
    url_error = _validate_url(url)
    if url_error:
        return {"error": url_error, "url": url}

    ctx = await get_project_context(project_path)
    content = _fetch_and_extract(url)

    if content is None:
        return {
            "error": "Failed to fetch URL. Ensure httpx and beautifulsoup4 are installed, "
                     f"content is under {MAX_CONTENT_SIZE} bytes, and URL is accessible.",
            "url": url
        }

    if not content.strip():
        return {"error": "No text content found at URL", "url": url}

    # Chunk with limit
    chunks = []
    words = content.split()
    current_chunk = []
    current_size = 0

    for word in words:
        word_len = len(word) + 1
        if current_size + word_len > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            if len(chunks) >= MAX_CHUNKS:
                logger.warning(f"Reached max chunks ({MAX_CHUNKS}), stopping")
                break
            current_chunk = [word]
            current_size = word_len
        else:
            current_chunk.append(word)
            current_size += word_len

    if current_chunk and len(chunks) < MAX_CHUNKS:
        chunks.append(' '.join(current_chunk))

    # Store chunks
    memories_created = []
    for i, chunk in enumerate(chunks):
        memory = await ctx.memory_manager.remember(
            category='learning',
            content=chunk[:500] + "..." if len(chunk) > 500 else chunk,
            rationale=f"Ingested from {url} (chunk {i+1}/{len(chunks)})",
            tags=['docs', 'ingested', topic],
            context={'source_url': url, 'chunk_index': i, 'total_chunks': len(chunks)}
        )
        memories_created.append(memory)

    return {
        "status": "success",
        "url": url,
        "topic": topic,
        "chunks_created": len(chunks),
        "total_chars": len(content),
        "truncated": len(chunks) >= MAX_CHUNKS,
        "message": f"Ingested {len(chunks)} chunks from {url}. Use recall('{topic}') to retrieve.",
        "memory_ids": [m.get('id') for m in memories_created if 'id' in m]
    }
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_ingest.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add daem0nmcp/server.py daem0nmcp/config.py tests/test_ingest.py
git commit -m "feat: harden ingest_doc with URL validation and limits

- Validate URL scheme (http/https only)
- Add MAX_CONTENT_SIZE (1MB) limit
- Add MAX_CHUNKS (50) limit
- Add configurable timeout (30s default)
- Prevents runaway memory usage and security issues"
```

---

## Phase 4: Search Upgrades

### Task 4.1: Add SQLite FTS5 Support

**Files:**
- Modify: `daem0nmcp/models.py` (add FTS table)
- Modify: `daem0nmcp/migrations.py` (add FTS migration)
- Modify: `daem0nmcp/memory.py` (use FTS for fast fallback)
- Test: `tests/test_fts.py` (new file)

**Step 1: Write the failing test**

Create `tests/test_fts.py`:

```python
"""Tests for FTS5 full-text search."""

import pytest
import tempfile
import shutil


class TestFTS5Search:
    """Test FTS5 full-text search functionality."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_fts_search_finds_content(self, temp_storage):
        """Verify FTS5 search works for content."""
        from daem0nmcp.database import DatabaseManager
        from daem0nmcp.memory import MemoryManager

        db = DatabaseManager(temp_storage)
        await db.init_db()
        manager = MemoryManager(db)

        # Add memories
        await manager.remember(
            category="decision",
            content="Use PostgreSQL for the database layer",
            tags=["database", "architecture"]
        )
        await manager.remember(
            category="warning",
            content="MySQL has issues with JSON columns",
            tags=["database"]
        )

        # FTS search
        results = await manager.fts_search("PostgreSQL database")
        assert len(results) >= 1
        assert any("PostgreSQL" in r["content"] for r in results)

        await db.close()

    @pytest.mark.asyncio
    async def test_fts_search_with_tag_filter(self, temp_storage):
        """Verify FTS search can filter by tags."""
        from daem0nmcp.database import DatabaseManager
        from daem0nmcp.memory import MemoryManager

        db = DatabaseManager(temp_storage)
        await db.init_db()
        manager = MemoryManager(db)

        await manager.remember(
            category="decision",
            content="Use Redis for caching",
            tags=["cache", "performance"]
        )
        await manager.remember(
            category="decision",
            content="Use Redis for session storage",
            tags=["auth", "sessions"]
        )

        # Search with tag filter
        results = await manager.fts_search("Redis", tags=["cache"])
        assert len(results) == 1
        assert "caching" in results[0]["content"]

        await db.close()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_fts.py -v`
Expected: FAIL (fts_search method doesn't exist)

**Step 3: Add FTS5 migration**

Add to `daem0nmcp/migrations.py`:

```python
MIGRATIONS: List[Tuple[int, str, List[str]]] = [
    (1, "Add vector_embedding column", [
        "ALTER TABLE memories ADD COLUMN vector_embedding BLOB;"
    ]),
    (2, "Create FTS5 virtual table for full-text search", [
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content,
            rationale,
            tags,
            content='memories',
            content_rowid='id'
        );
        """,
        """
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content, rationale, tags)
            VALUES (new.id, new.content, new.rationale, json_extract(new.tags, '$'));
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, rationale, tags)
            VALUES ('delete', old.id, old.content, old.rationale, json_extract(old.tags, '$'));
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, rationale, tags)
            VALUES ('delete', old.id, old.content, old.rationale, json_extract(old.tags, '$'));
            INSERT INTO memories_fts(rowid, content, rationale, tags)
            VALUES (new.id, new.content, new.rationale, json_extract(new.tags, '$'));
        END;
        """
    ]),
]
```

**Step 4: Add fts_search method**

Add to `daem0nmcp/memory.py`:

```python
async def fts_search(
    self,
    query: str,
    tags: Optional[List[str]] = None,
    file_path: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Fast full-text search using SQLite FTS5.

    Falls back to LIKE search if FTS5 is not available.

    Args:
        query: Search query (supports FTS5 syntax)
        tags: Optional tag filter
        file_path: Optional file path filter
        limit: Maximum results

    Returns:
        List of matching memories with relevance info
    """
    async with self.db.get_session() as session:
        try:
            # Try FTS5 search
            from sqlalchemy import text

            sql = """
                SELECT m.*, bm25(memories_fts) as rank
                FROM memories m
                JOIN memories_fts ON m.id = memories_fts.rowid
                WHERE memories_fts MATCH :query
            """
            params = {"query": query}

            # Add tag filter
            if tags:
                tag_conditions = " AND ".join(
                    f"json_extract(m.tags, '$') LIKE :tag{i}"
                    for i in range(len(tags))
                )
                sql += f" AND ({tag_conditions})"
                for i, tag in enumerate(tags):
                    params[f"tag{i}"] = f"%{tag}%"

            # Add file path filter
            if file_path:
                sql += " AND m.file_path = :file_path"
                params["file_path"] = file_path

            sql += " ORDER BY rank LIMIT :limit"
            params["limit"] = limit

            result = await session.execute(text(sql), params)
            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "category": row.category,
                    "content": row.content,
                    "rationale": row.rationale,
                    "tags": row.tags,
                    "file_path": row.file_path,
                    "relevance": abs(row.rank),  # bm25 returns negative scores
                    "created_at": row.created_at.isoformat() if row.created_at else None
                }
                for row in rows
            ]

        except Exception as e:
            # FTS5 not available, fall back to LIKE search
            logger.debug(f"FTS5 not available, using LIKE search: {e}")
            return await self.search(query, limit=limit)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_fts.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add daem0nmcp/migrations.py daem0nmcp/memory.py tests/test_fts.py
git commit -m "feat: add SQLite FTS5 for fast full-text search

- Add FTS5 virtual table with triggers for sync
- Add fts_search() method with tag/file filters
- Falls back to LIKE search if FTS5 unavailable"
```

---

### Task 4.2: Add Filter Parameters to recall Tool

**Files:**
- Modify: `daem0nmcp/server.py` (add filters to recall)
- Modify: `daem0nmcp/memory.py` (support filters in recall)
- Test: `tests/test_memory.py` (add filter tests)

**Step 1: Write the failing test**

Add to `tests/test_memory.py`:

```python
@pytest.mark.asyncio
async def test_recall_with_tag_filter(self, memory_manager):
    """Test recall with tag filtering."""
    await memory_manager.remember(
        category="decision",
        content="Use Redis for caching",
        tags=["cache", "performance"]
    )
    await memory_manager.remember(
        category="decision",
        content="Use Redis for sessions",
        tags=["auth"]
    )

    result = await memory_manager.recall("Redis", tags=["cache"])

    # Should only find the caching decision
    assert result["found"] >= 1
    all_tags = [tag for m in result.get("decisions", []) for tag in m.get("tags", [])]
    assert "cache" in all_tags

@pytest.mark.asyncio
async def test_recall_with_file_filter(self, memory_manager):
    """Test recall with file path filtering."""
    await memory_manager.remember(
        category="warning",
        content="Don't use sync calls here",
        file_path="api/handlers.py"
    )
    await memory_manager.remember(
        category="warning",
        content="Watch for race conditions",
        file_path="worker/tasks.py"
    )

    result = await memory_manager.recall("calls", file_path="api/handlers.py")

    # Should only find the handlers warning
    assert result["found"] >= 1
    all_files = [m.get("file_path") for cat in ["warnings", "decisions"] for m in result.get(cat, [])]
    assert all(f is None or "handlers" in f for f in all_files)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py::TestMemoryManager::test_recall_with_tag_filter -v`
Expected: FAIL (tags parameter not supported)

**Step 3: Add filter support to recall**

Modify `daem0nmcp/memory.py` recall method signature and implementation:

```python
async def recall(
    self,
    topic: str,
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,  # NEW
    file_path: Optional[str] = None,   # NEW
    limit: int = 10,
    include_warnings: bool = True,
    decay_half_life_days: float = 30.0
) -> Dict[str, Any]:
    """
    Recall memories relevant to a topic using semantic similarity.

    Args:
        topic: What you're looking for
        categories: Limit to specific categories
        tags: Filter to memories with these tags
        file_path: Filter to memories for this file
        limit: Max memories per category
        include_warnings: Always include warnings
        decay_half_life_days: Decay rate
    """
    index = await self._ensure_index()

    # ... existing search logic ...

    # After getting memories dict, apply filters
    async with self.db.get_session() as session:
        result = await session.execute(
            select(Memory).where(Memory.id.in_(memory_ids))
        )
        memories = {m.id: m for m in result.scalars().all()}

    # Filter by tags if specified
    if tags:
        memories = {
            mid: mem for mid, mem in memories.items()
            if mem.tags and any(t in mem.tags for t in tags)
        }

    # Filter by file_path if specified
    if file_path:
        memories = {
            mid: mem for mid, mem in memories.items()
            if mem.file_path and (
                mem.file_path == file_path or
                mem.file_path.endswith(file_path) or
                file_path.endswith(mem.file_path)
            )
        }

    # ... rest of existing logic ...
```

**Step 4: Update server.py recall tool**

```python
@mcp.tool()
async def recall(
    topic: str,
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    file_path: Optional[str] = None,
    limit: int = 10,
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Recall memories relevant to a topic using SEMANTIC SIMILARITY.

    Args:
        topic: What you're looking for
        categories: Limit to specific categories
        tags: Filter to memories with specific tags
        file_path: Filter to memories for a specific file
        limit: Max memories per category
        project_path: Project root path
    """
    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    ctx = await get_project_context(project_path)
    return await ctx.memory_manager.recall(
        topic=topic,
        categories=categories,
        tags=tags,
        file_path=file_path,
        limit=limit
    )
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_memory.py::TestMemoryManager::test_recall_with_tag_filter tests/test_memory.py::TestMemoryManager::test_recall_with_file_filter -v`
Expected: PASS

**Step 6: Commit**

```bash
git add daem0nmcp/memory.py daem0nmcp/server.py tests/test_memory.py
git commit -m "feat: add tag and file_path filters to recall

- Add tags parameter to filter by memory tags
- Add file_path parameter to filter by file association
- Reduces noise in search results"
```

---

## Phase 5: UX and Operations Tools

### Task 5.1: Add Health/Version Tool

**Files:**
- Modify: `daem0nmcp/server.py` (add health tool)
- Modify: `daem0nmcp/__init__.py` (add version)
- Test: `tests/test_ops.py` (new file)

**Step 1: Write the failing test**

Create `tests/test_ops.py`:

```python
"""Tests for operational tools."""

import pytest


class TestHealthTool:
    """Test health and version reporting."""

    @pytest.mark.asyncio
    async def test_health_returns_version(self):
        """Verify health tool returns version info."""
        from daem0nmcp import __version__
        from daem0nmcp.server import health

        result = await health(project_path="/tmp/test")

        assert "version" in result
        assert result["version"] == __version__
        assert "status" in result

    @pytest.mark.asyncio
    async def test_health_returns_statistics(self):
        """Verify health tool returns memory statistics."""
        import tempfile
        from daem0nmcp.server import health, get_project_context

        with tempfile.TemporaryDirectory() as temp_dir:
            result = await health(project_path=temp_dir)

            assert "memories_count" in result
            assert "rules_count" in result
            assert "storage_path" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ops.py -v`
Expected: FAIL (health tool doesn't exist, __version__ not defined)

**Step 3: Add version to __init__.py**

Modify `daem0nmcp/__init__.py`:

```python
"""
Daem0nMCP Core Package
"""

__version__ = "2.3.0"
```

**Step 4: Add health tool**

Add to `daem0nmcp/server.py`:

```python
from daem0nmcp import __version__

@mcp.tool()
async def health(
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get server health and version information.

    Returns version, statistics, and configuration info.
    Useful for debugging and monitoring.

    Args:
        project_path: Project root path

    Returns:
        Health status with version and statistics
    """
    import time

    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    ctx = await get_project_context(project_path)
    stats = await ctx.memory_manager.get_statistics()

    # Get rule count
    rules = await ctx.rules_engine.list_rules(enabled_only=False, limit=1000)

    return {
        "status": "healthy",
        "version": __version__,
        "project_path": ctx.project_path,
        "storage_path": ctx.storage_path,
        "memories_count": stats.get("total_memories", 0),
        "rules_count": len(rules),
        "by_category": stats.get("by_category", {}),
        "contexts_cached": len(_project_contexts),
        "vectors_enabled": vectors.is_available() if 'vectors' in dir() else False,
        "timestamp": time.time()
    }
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_ops.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add daem0nmcp/__init__.py daem0nmcp/server.py tests/test_ops.py
git commit -m "feat: add health tool for version and status info

- Add __version__ = '2.3.0' to package
- Add health MCP tool returning version, stats, config
- Useful for debugging and monitoring"
```

---

### Task 5.2: Add Export/Import Tools

**Files:**
- Modify: `daem0nmcp/server.py` (add export_data, import_data tools)
- Test: `tests/test_ops.py` (add export/import tests)

**Step 1: Write the failing test**

Add to `tests/test_ops.py`:

```python
class TestExportImport:
    """Test data export and import."""

    @pytest.mark.asyncio
    async def test_export_returns_json_structure(self):
        """Verify export returns proper JSON structure."""
        import tempfile
        from daem0nmcp.database import DatabaseManager
        from daem0nmcp.memory import MemoryManager
        from daem0nmcp.rules import RulesEngine
        from daem0nmcp.server import export_data, get_project_context, _project_contexts

        with tempfile.TemporaryDirectory() as temp_dir:
            _project_contexts.clear()

            ctx = await get_project_context(temp_dir)
            await ctx.memory_manager.remember(
                category="decision",
                content="Test export"
            )
            await ctx.rules_engine.add_rule(
                trigger="test trigger",
                must_do=["test action"]
            )

            result = await export_data(project_path=temp_dir)

            assert "memories" in result
            assert "rules" in result
            assert "version" in result
            assert len(result["memories"]) >= 1
            assert len(result["rules"]) >= 1

    @pytest.mark.asyncio
    async def test_import_restores_data(self):
        """Verify import restores exported data."""
        import tempfile
        from daem0nmcp.server import export_data, import_data, get_project_context, _project_contexts

        with tempfile.TemporaryDirectory() as temp_dir1:
            with tempfile.TemporaryDirectory() as temp_dir2:
                _project_contexts.clear()

                # Create data in first project
                ctx1 = await get_project_context(temp_dir1)
                await ctx1.memory_manager.remember(
                    category="decision",
                    content="Imported memory test"
                )

                # Export
                exported = await export_data(project_path=temp_dir1)

                # Import to second project
                _project_contexts.clear()
                result = await import_data(
                    data=exported,
                    project_path=temp_dir2
                )

                assert result["memories_imported"] >= 1

                # Verify data exists
                ctx2 = await get_project_context(temp_dir2)
                recall_result = await ctx2.memory_manager.recall("Imported memory")
                assert recall_result["found"] >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ops.py::TestExportImport -v`
Expected: FAIL (export_data, import_data don't exist)

**Step 3: Add export_data tool**

Add to `daem0nmcp/server.py`:

```python
@mcp.tool()
async def export_data(
    project_path: Optional[str] = None,
    include_vectors: bool = False
) -> Dict[str, Any]:
    """
    Export all memories and rules as JSON.

    Use for backup, migration, or sharing project knowledge.

    Args:
        project_path: Project root path
        include_vectors: Include vector embeddings (large, default False)

    Returns:
        JSON structure with all memories and rules
    """
    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    ctx = await get_project_context(project_path)

    async with ctx.db_manager.get_session() as session:
        # Export memories
        from sqlalchemy import select
        result = await session.execute(select(Memory))
        memories = [
            {
                "id": m.id,
                "category": m.category,
                "content": m.content,
                "rationale": m.rationale,
                "context": m.context,
                "tags": m.tags,
                "file_path": m.file_path,
                "keywords": m.keywords,
                "is_permanent": m.is_permanent,
                "outcome": m.outcome,
                "worked": m.worked,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                # Optionally include vectors (base64 encoded)
                "vector_embedding": (
                    base64.b64encode(m.vector_embedding).decode()
                    if include_vectors and m.vector_embedding else None
                )
            }
            for m in result.scalars().all()
        ]

        # Export rules
        result = await session.execute(select(Rule))
        rules = [
            {
                "id": r.id,
                "trigger": r.trigger,
                "trigger_keywords": r.trigger_keywords,
                "must_do": r.must_do,
                "must_not": r.must_not,
                "ask_first": r.ask_first,
                "warnings": r.warnings,
                "priority": r.priority,
                "enabled": r.enabled,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in result.scalars().all()
        ]

    return {
        "version": __version__,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project_path": ctx.project_path,
        "memories": memories,
        "rules": rules
    }
```

**Step 4: Add import_data tool**

```python
import base64

@mcp.tool()
async def import_data(
    data: Dict[str, Any],
    project_path: Optional[str] = None,
    merge: bool = True
) -> Dict[str, Any]:
    """
    Import memories and rules from exported JSON.

    Args:
        data: Exported data structure (from export_data)
        project_path: Project root path
        merge: If True, add to existing data. If False, replace all.

    Returns:
        Import statistics
    """
    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    if "memories" not in data or "rules" not in data:
        return {"error": "Invalid data format. Expected 'memories' and 'rules' keys."}

    ctx = await get_project_context(project_path)

    memories_imported = 0
    rules_imported = 0

    async with ctx.db_manager.get_session() as session:
        # Import memories
        for mem_data in data.get("memories", []):
            # Decode vector if present
            vector_bytes = None
            if mem_data.get("vector_embedding"):
                try:
                    vector_bytes = base64.b64decode(mem_data["vector_embedding"])
                except Exception:
                    pass

            memory = Memory(
                category=mem_data["category"],
                content=mem_data["content"],
                rationale=mem_data.get("rationale"),
                context=mem_data.get("context", {}),
                tags=mem_data.get("tags", []),
                file_path=mem_data.get("file_path"),
                keywords=mem_data.get("keywords"),
                is_permanent=mem_data.get("is_permanent", False),
                outcome=mem_data.get("outcome"),
                worked=mem_data.get("worked"),
                vector_embedding=vector_bytes
            )
            session.add(memory)
            memories_imported += 1

        # Import rules
        for rule_data in data.get("rules", []):
            rule = Rule(
                trigger=rule_data["trigger"],
                trigger_keywords=rule_data.get("trigger_keywords"),
                must_do=rule_data.get("must_do", []),
                must_not=rule_data.get("must_not", []),
                ask_first=rule_data.get("ask_first", []),
                warnings=rule_data.get("warnings", []),
                priority=rule_data.get("priority", 0),
                enabled=rule_data.get("enabled", True)
            )
            session.add(rule)
            rules_imported += 1

    # Rebuild indexes
    await ctx.memory_manager.rebuild_index()
    await ctx.rules_engine.rebuild_index()

    return {
        "status": "imported",
        "memories_imported": memories_imported,
        "rules_imported": rules_imported,
        "message": f"Imported {memories_imported} memories and {rules_imported} rules"
    }
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_ops.py::TestExportImport -v`
Expected: PASS

**Step 6: Commit**

```bash
git add daem0nmcp/server.py tests/test_ops.py
git commit -m "feat: add export_data and import_data tools

- export_data: Export all memories and rules as JSON
- import_data: Import from exported JSON
- Supports backup, migration, and project knowledge sharing"
```

---

### Task 5.3: Add Prune/Archive/Pin Tools

**Files:**
- Modify: `daem0nmcp/server.py` (add prune, archive, pin tools)
- Modify: `daem0nmcp/models.py` (add archived/pinned fields)
- Modify: `daem0nmcp/migrations.py` (add migration)
- Test: `tests/test_ops.py` (add maintenance tests)

**Step 1: Write the failing test**

Add to `tests/test_ops.py`:

```python
class TestMaintenanceTools:
    """Test prune, archive, and pin operations."""

    @pytest.mark.asyncio
    async def test_pin_memory_prevents_decay(self):
        """Verify pinned memories don't decay."""
        import tempfile
        from daem0nmcp.server import pin_memory, recall, get_project_context, _project_contexts

        with tempfile.TemporaryDirectory() as temp_dir:
            _project_contexts.clear()
            ctx = await get_project_context(temp_dir)

            mem = await ctx.memory_manager.remember(
                category="decision",
                content="Important decision to pin"
            )

            result = await pin_memory(
                memory_id=mem["id"],
                pinned=True,
                project_path=temp_dir
            )

            assert result.get("pinned") == True

    @pytest.mark.asyncio
    async def test_prune_removes_old_memories(self):
        """Verify prune removes old, low-relevance memories."""
        import tempfile
        from datetime import datetime, timedelta
        from daem0nmcp.server import prune_memories, get_project_context, _project_contexts

        with tempfile.TemporaryDirectory() as temp_dir:
            _project_contexts.clear()
            ctx = await get_project_context(temp_dir)

            # Add some memories
            await ctx.memory_manager.remember(
                category="learning",
                content="Old learning to prune"
            )

            # Prune with dry_run first
            result = await prune_memories(
                older_than_days=0,  # Prune everything for test
                dry_run=True,
                project_path=temp_dir
            )

            assert "would_prune" in result
            assert result["would_prune"] >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ops.py::TestMaintenanceTools -v`
Expected: FAIL (pin_memory, prune_memories don't exist)

**Step 3: Add pinned field to Memory model**

Add to `daem0nmcp/models.py`:

```python
class Memory(Base):
    # ... existing fields ...

    # Pinned memories are never pruned and have boosted relevance
    pinned = Column(Boolean, default=False)

    # Archived memories are hidden from normal recall but kept for history
    archived = Column(Boolean, default=False)
```

**Step 4: Add migration**

Add to `daem0nmcp/migrations.py`:

```python
MIGRATIONS: List[Tuple[int, str, List[str]]] = [
    # ... existing migrations ...
    (3, "Add pinned and archived columns to memories", [
        "ALTER TABLE memories ADD COLUMN pinned BOOLEAN DEFAULT 0;",
        "ALTER TABLE memories ADD COLUMN archived BOOLEAN DEFAULT 0;"
    ]),
]
```

**Step 5: Add maintenance tools**

Add to `daem0nmcp/server.py`:

```python
@mcp.tool()
async def pin_memory(
    memory_id: int,
    pinned: bool = True,
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pin or unpin a memory.

    Pinned memories:
    - Never pruned automatically
    - Get relevance boost in recall
    - Treated as permanent project knowledge

    Args:
        memory_id: Memory to pin/unpin
        pinned: True to pin, False to unpin
        project_path: Project root path
    """
    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    ctx = await get_project_context(project_path)

    async with ctx.db_manager.get_session() as session:
        result = await session.execute(
            select(Memory).where(Memory.id == memory_id)
        )
        memory = result.scalar_one_or_none()

        if not memory:
            return {"error": f"Memory {memory_id} not found"}

        memory.pinned = pinned
        memory.is_permanent = pinned  # Pinned = permanent

        return {
            "id": memory_id,
            "pinned": pinned,
            "content": memory.content[:100],
            "message": f"Memory {'pinned' if pinned else 'unpinned'}"
        }


@mcp.tool()
async def prune_memories(
    older_than_days: int = 90,
    categories: Optional[List[str]] = None,
    dry_run: bool = True,
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prune old, low-value memories.

    By default, only affects episodic memories (decisions, learnings).
    Permanent memories (patterns, warnings), pinned, and memories with
    outcomes are protected.

    Args:
        older_than_days: Only prune memories older than this
        categories: Limit to these categories (default: decision, learning)
        dry_run: If True, just report what would be pruned
        project_path: Project root path
    """
    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    ctx = await get_project_context(project_path)

    if categories is None:
        categories = ["decision", "learning"]

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

    async with ctx.db_manager.get_session() as session:
        # Find prunable memories
        query = select(Memory).where(
            Memory.category.in_(categories),
            Memory.created_at < cutoff,
            Memory.is_permanent == False,
            Memory.pinned == False,
            Memory.outcome == None,  # Don't prune memories with outcomes
            Memory.archived == False
        )

        result = await session.execute(query)
        to_prune = result.scalars().all()

        if dry_run:
            return {
                "dry_run": True,
                "would_prune": len(to_prune),
                "categories": categories,
                "older_than_days": older_than_days,
                "samples": [
                    {"id": m.id, "content": m.content[:50], "created_at": m.created_at.isoformat()}
                    for m in to_prune[:5]
                ]
            }

        # Actually delete
        for memory in to_prune:
            await session.delete(memory)

        return {
            "pruned": len(to_prune),
            "categories": categories,
            "older_than_days": older_than_days,
            "message": f"Pruned {len(to_prune)} old memories"
        }


@mcp.tool()
async def archive_memory(
    memory_id: int,
    archived: bool = True,
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Archive or unarchive a memory.

    Archived memories are hidden from recall but preserved for history.

    Args:
        memory_id: Memory to archive/unarchive
        archived: True to archive, False to restore
        project_path: Project root path
    """
    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    ctx = await get_project_context(project_path)

    async with ctx.db_manager.get_session() as session:
        result = await session.execute(
            select(Memory).where(Memory.id == memory_id)
        )
        memory = result.scalar_one_or_none()

        if not memory:
            return {"error": f"Memory {memory_id} not found"}

        memory.archived = archived

        return {
            "id": memory_id,
            "archived": archived,
            "content": memory.content[:100],
            "message": f"Memory {'archived' if archived else 'restored'}"
        }
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_ops.py::TestMaintenanceTools -v`
Expected: PASS

**Step 7: Commit**

```bash
git add daem0nmcp/models.py daem0nmcp/migrations.py daem0nmcp/server.py tests/test_ops.py
git commit -m "feat: add prune, archive, and pin tools for maintenance

- pin_memory: Protect important memories from decay/prune
- archive_memory: Hide memories without deleting
- prune_memories: Clean old, low-value episodic memories
- Add pinned/archived columns to memories table"
```

---

## Phase 6: Coverage and CI

### Task 6.1: Add Multi-Project Path Resolution Tests

**Files:**
- Modify: `tests/test_context.py` (add path resolution tests)

**Step 1: Write the tests**

Add to `tests/test_context.py`:

```python
class TestPathResolution:
    """Test path normalization and resolution."""

    def test_normalize_path_handles_windows_paths(self):
        """Verify Windows-style paths are normalized."""
        from daem0nmcp.server import _normalize_path

        # Test various path formats
        paths = [
            "C:\\Users\\test\\project",
            "C:/Users/test/project",
            "/home/user/project",
        ]

        for path in paths:
            result = _normalize_path(path)
            assert result is not None
            assert len(result) > 0

    def test_normalize_path_resolves_relative(self):
        """Verify relative paths are resolved."""
        from daem0nmcp.server import _normalize_path
        import os

        result = _normalize_path(".")
        assert os.path.isabs(result)

    @pytest.mark.asyncio
    async def test_different_projects_get_different_contexts(self):
        """Verify each project gets its own context."""
        import tempfile
        from daem0nmcp.server import get_project_context, _project_contexts

        _project_contexts.clear()

        with tempfile.TemporaryDirectory() as dir1:
            with tempfile.TemporaryDirectory() as dir2:
                ctx1 = await get_project_context(dir1)
                ctx2 = await get_project_context(dir2)

                assert ctx1 is not ctx2
                assert ctx1.project_path != ctx2.project_path
                assert len(_project_contexts) == 2
```

**Step 2: Run tests**

Run: `pytest tests/test_context.py::TestPathResolution -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_context.py
git commit -m "test: add multi-project path resolution tests"
```

---

### Task 6.2: Add Git Context Tests

**Files:**
- Create: `tests/test_git.py`

**Step 1: Write the tests**

Create `tests/test_git.py`:

```python
"""Tests for git integration."""

import pytest
import tempfile
import subprocess
from pathlib import Path


class TestGitContext:
    """Test git-related functionality."""

    @pytest.fixture
    def git_repo(self):
        """Create a temporary git repository."""
        temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=temp_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=temp_dir, capture_output=True
        )

        # Create initial commit
        Path(temp_dir, "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=temp_dir, capture_output=True
        )

        yield temp_dir

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_git_changes_with_project_path(self, git_repo):
        """Verify git changes are read from correct directory."""
        from daem0nmcp.server import _get_git_changes

        result = _get_git_changes(project_path=git_repo)

        assert result is not None
        assert "branch" in result

    def test_get_git_changes_detects_uncommitted(self, git_repo):
        """Verify uncommitted changes are detected."""
        from daem0nmcp.server import _get_git_changes

        # Create uncommitted change
        Path(git_repo, "new_file.txt").write_text("new content")

        result = _get_git_changes(project_path=git_repo)

        assert result is not None
        assert "uncommitted_changes" in result
        assert len(result["uncommitted_changes"]) >= 1

    def test_get_git_changes_returns_none_for_non_repo(self):
        """Verify None is returned for non-git directories."""
        from daem0nmcp.server import _get_git_changes

        with tempfile.TemporaryDirectory() as temp_dir:
            result = _get_git_changes(project_path=temp_dir)
            assert result is None
```

**Step 2: Run tests**

Run: `pytest tests/test_git.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_git.py
git commit -m "test: add git context tests

- Test git changes with explicit project_path
- Test uncommitted change detection
- Test non-repo handling"
```

---

### Task 6.3: Add Mocked HTTP Tests for ingest_doc

**Files:**
- Modify: `tests/test_ingest.py` (add mocked HTTP tests)

**Step 1: Write the tests**

Add to `tests/test_ingest.py`:

```python
class TestIngestDocMocked:
    """Test ingest_doc with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_ingest_success_with_mocked_response(self):
        """Verify successful ingestion with mocked HTTP."""
        import tempfile
        from unittest.mock import patch, MagicMock
        from daem0nmcp.server import ingest_doc, _project_contexts

        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <p>This is documentation about API usage.</p>
                <p>Use the /users endpoint for user operations.</p>
            </body>
        </html>
        """
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        with tempfile.TemporaryDirectory() as temp_dir:
            _project_contexts.clear()

            with patch('httpx.Client') as mock_client:
                mock_client.return_value.__enter__.return_value.get.return_value = mock_response

                result = await ingest_doc(
                    url="https://example.com/docs",
                    topic="api-docs",
                    project_path=temp_dir
                )

            assert result.get("status") == "success"
            assert result["chunks_created"] >= 1
            assert result["topic"] == "api-docs"

    @pytest.mark.asyncio
    async def test_ingest_handles_timeout(self):
        """Verify timeout is handled gracefully."""
        import tempfile
        from unittest.mock import patch
        import httpx
        from daem0nmcp.server import ingest_doc, _project_contexts

        with tempfile.TemporaryDirectory() as temp_dir:
            _project_contexts.clear()

            with patch('httpx.Client') as mock_client:
                mock_client.return_value.__enter__.return_value.get.side_effect = httpx.TimeoutException("timeout")

                result = await ingest_doc(
                    url="https://slow.example.com/docs",
                    topic="slow-docs",
                    project_path=temp_dir
                )

            assert "error" in result

    @pytest.mark.asyncio
    async def test_ingest_handles_http_error(self):
        """Verify HTTP errors are handled gracefully."""
        import tempfile
        from unittest.mock import patch, MagicMock
        import httpx
        from daem0nmcp.server import ingest_doc, _project_contexts

        with tempfile.TemporaryDirectory() as temp_dir:
            _project_contexts.clear()

            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock()
            )

            with patch('httpx.Client') as mock_client:
                mock_client.return_value.__enter__.return_value.get.return_value = mock_response

                result = await ingest_doc(
                    url="https://example.com/missing",
                    topic="missing",
                    project_path=temp_dir
                )

            assert "error" in result
```

**Step 2: Run tests**

Run: `pytest tests/test_ingest.py::TestIngestDocMocked -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_ingest.py
git commit -m "test: add mocked HTTP tests for ingest_doc

- Test successful ingestion
- Test timeout handling
- Test HTTP error handling"
```

---

### Task 6.4: Add Migration Tests

**Files:**
- Create: `tests/test_migrations.py`

**Step 1: Write the tests**

Create `tests/test_migrations.py`:

```python
"""Tests for database migrations."""

import pytest
import tempfile
import sqlite3
from pathlib import Path


class TestMigrations:
    """Test migration functionality."""

    @pytest.fixture
    def legacy_db(self):
        """Create a legacy database without new columns."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "daem0nmcp.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                rationale TEXT,
                context TEXT DEFAULT '{}',
                tags TEXT DEFAULT '[]',
                file_path TEXT,
                keywords TEXT,
                is_permanent BOOLEAN DEFAULT 0,
                outcome TEXT,
                worked BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE rules (
                id INTEGER PRIMARY KEY,
                trigger TEXT NOT NULL,
                trigger_keywords TEXT,
                must_do TEXT DEFAULT '[]',
                must_not TEXT DEFAULT '[]',
                ask_first TEXT DEFAULT '[]',
                warnings TEXT DEFAULT '[]',
                priority INTEGER DEFAULT 0,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        yield str(db_path)

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_migration_adds_vector_embedding(self, legacy_db):
        """Verify migration adds vector_embedding column."""
        from daem0nmcp.migrations import run_migrations

        count, applied = run_migrations(legacy_db)

        # Check column exists
        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute("PRAGMA table_info(memories)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "vector_embedding" in columns
        assert count >= 1

    def test_migration_is_idempotent(self, legacy_db):
        """Verify running migrations twice is safe."""
        from daem0nmcp.migrations import run_migrations

        count1, _ = run_migrations(legacy_db)
        count2, _ = run_migrations(legacy_db)

        # Second run should do nothing
        assert count2 == 0

    def test_migration_creates_fts_table(self, legacy_db):
        """Verify FTS5 table is created."""
        from daem0nmcp.migrations import run_migrations

        run_migrations(legacy_db)

        conn = sqlite3.connect(legacy_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories_fts'"
        )
        result = cursor.fetchone()
        conn.close()

        # FTS table should exist
        assert result is not None
```

**Step 2: Run tests**

Run: `pytest tests/test_migrations.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_migrations.py
git commit -m "test: add migration tests

- Test vector_embedding column migration
- Test idempotency
- Test FTS5 table creation"
```

---

### Task 6.5: Set Up GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest tests/ -v --asyncio-mode=auto

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff

      - name: Lint with ruff
        run: |
          ruff check daem0nmcp/

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
          pip install mypy

      - name: Type check
        run: |
          mypy daem0nmcp/ --ignore-missing-imports || true
```

**Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow

- Test on Python 3.10, 3.11, 3.12
- Test on Ubuntu, Windows, macOS
- Add linting with ruff
- Add type checking with mypy"
```

---

## Summary

### New MCP Tools (7)
1. `rebuild_index` - Force rebuild search indexes
2. `health` - Version and status info
3. `export_data` - Export memories/rules as JSON
4. `import_data` - Import from JSON
5. `pin_memory` - Protect important memories
6. `archive_memory` - Hide without deleting
7. `prune_memories` - Clean old memories

### Schema Changes
- Add `vector_embedding` column (migration 1)
- Add FTS5 virtual table (migration 2)
- Add `pinned`, `archived` columns (migration 3)

### Configuration Options
- `max_project_contexts` (default: 10)
- `context_ttl_seconds` (default: 3600)
- `max_content_size` (default: 1MB)
- `max_chunks` (default: 50)
- `ingest_timeout` (default: 30s)
- `allowed_url_schemes` (default: http, https)

### Test Files (New)
- `tests/test_context.py`
- `tests/test_index_freshness.py`
- `tests/test_ingest.py`
- `tests/test_fts.py`
- `tests/test_ops.py`
- `tests/test_git.py`
- `tests/test_migrations.py`

---

## Phase 7: Performance and Reliability

### Task 7.1: SQLite PRAGMA Tuning

**Files:**
- Modify: `daem0nmcp/database.py` (add PRAGMA settings)
- Test: `tests/test_database.py` (new file)

**Step 1: Write the failing test**

Create `tests/test_database.py`:

```python
"""Tests for database configuration."""

import pytest
import tempfile


class TestSQLitePragmas:
    """Test SQLite PRAGMA settings."""

    @pytest.mark.asyncio
    async def test_wal_mode_enabled(self):
        """Verify WAL mode is enabled."""
        from daem0nmcp.database import DatabaseManager

        with tempfile.TemporaryDirectory() as temp_dir:
            db = DatabaseManager(temp_dir)
            await db.init_db()

            async with db.get_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("PRAGMA journal_mode"))
                mode = result.scalar()
                assert mode.lower() == "wal"

            await db.close()

    @pytest.mark.asyncio
    async def test_foreign_keys_enabled(self):
        """Verify foreign keys are enabled."""
        from daem0nmcp.database import DatabaseManager

        with tempfile.TemporaryDirectory() as temp_dir:
            db = DatabaseManager(temp_dir)
            await db.init_db()

            async with db.get_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("PRAGMA foreign_keys"))
                enabled = result.scalar()
                assert enabled == 1

            await db.close()
```

**Step 2: Add PRAGMA configuration**

Modify `daem0nmcp/database.py`:

```python
from sqlalchemy import event

class DatabaseManager:
    def _get_engine(self):
        if self._engine is None:
            self._engine = create_async_engine(
                self.db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                pool_pre_ping=True,
            )

            # Configure SQLite PRAGMAs for performance and reliability
            @event.listens_for(self._engine.sync_engine, "connect")
            def set_sqlite_pragmas(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                # WAL mode for better concurrent access
                cursor.execute("PRAGMA journal_mode=WAL")
                # Faster syncs (still safe with WAL)
                cursor.execute("PRAGMA synchronous=NORMAL")
                # 30 second busy timeout
                cursor.execute("PRAGMA busy_timeout=30000")
                # Enable foreign keys
                cursor.execute("PRAGMA foreign_keys=ON")
                # Use memory for temp tables
                cursor.execute("PRAGMA temp_store=MEMORY")
                # Larger cache
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB
                cursor.close()

            self._session_factory = async_sessionmaker(...)
```

**Step 3: Commit**

```bash
git add daem0nmcp/database.py tests/test_database.py
git commit -m "feat: add SQLite PRAGMA tuning for performance

- Enable WAL mode for better concurrency
- Set synchronous=NORMAL for faster writes
- Add busy_timeout to reduce locking errors
- Enable foreign_keys for referential integrity"
```

---

### Task 7.2: Path Normalization with Relative Storage

**Files:**
- Modify: `daem0nmcp/models.py` (add file_path_relative column)
- Modify: `daem0nmcp/memory.py` (store both absolute and relative paths)
- Modify: `daem0nmcp/migrations.py` (add migration)
- Test: `tests/test_memory.py` (add path tests)

**Step 1: Add file_path_relative column**

Add to `daem0nmcp/models.py`:

```python
class Memory(Base):
    # ... existing fields ...

    # Relative file path (for portability across machines)
    file_path_relative = Column(String, nullable=True, index=True)
```

**Step 2: Normalize paths on store**

Modify `daem0nmcp/memory.py`:

```python
import sys

def _normalize_file_path(file_path: str, project_path: str) -> Tuple[str, str]:
    """
    Normalize a file path to both absolute and project-relative forms.

    On Windows, also case-folds for consistent matching.
    """
    from pathlib import Path

    if not file_path:
        return None, None

    path = Path(file_path)

    # Make absolute if not already
    if not path.is_absolute():
        path = Path(project_path) / path

    absolute = str(path.resolve())

    # Compute relative path from project root
    try:
        relative = str(path.resolve().relative_to(Path(project_path).resolve()))
    except ValueError:
        relative = str(path.name)  # Fallback to just filename

    # Case-fold on Windows for consistent matching
    if sys.platform == 'win32':
        absolute = absolute.lower()
        relative = relative.lower()

    return absolute, relative
```

**Step 3: Commit**

```bash
git add daem0nmcp/models.py daem0nmcp/memory.py daem0nmcp/migrations.py
git commit -m "feat: add path normalization with relative storage

- Store both absolute and project-relative file paths
- Case-fold on Windows for consistent matching
- Improves recall accuracy and dedup"
```

---

### Task 7.3: Pagination for recall and search_memories

**Files:**
- Modify: `daem0nmcp/memory.py` (add offset/cursor params)
- Modify: `daem0nmcp/server.py` (expose pagination in tools)
- Test: `tests/test_memory.py` (add pagination tests)

**Step 1: Add pagination to recall**

Modify `daem0nmcp/memory.py`:

```python
async def recall(
    self,
    topic: str,
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    file_path: Optional[str] = None,
    since: Optional[datetime] = None,  # NEW: date filter
    until: Optional[datetime] = None,  # NEW: date filter
    offset: int = 0,  # NEW: pagination
    limit: int = 10,
    include_warnings: bool = True,
    decay_half_life_days: float = 30.0
) -> Dict[str, Any]:
    """..."""
    # Apply offset/limit to final results
    # Include total_count for pagination metadata

    return {
        'topic': topic,
        'found': total,
        'offset': offset,
        'limit': limit,
        'has_more': total > offset + limit,
        # ... rest of response
    }
```

**Step 2: Commit**

```bash
git add daem0nmcp/memory.py daem0nmcp/server.py tests/test_memory.py
git commit -m "feat: add pagination and date filters to recall/search

- Add offset parameter for pagination
- Add since/until for date range filtering
- Return has_more flag for pagination UX"
```

---

### Task 7.4: Observability with Structured Logging

**Files:**
- Modify: `daem0nmcp/server.py` (add request IDs and timing)
- Create: `daem0nmcp/logging_config.py` (structured logging setup)

**Step 1: Create logging configuration**

Create `daem0nmcp/logging_config.py`:

```python
"""Structured logging configuration for Daem0nMCP."""

import logging
import time
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable

# Context variable for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(''),
        }

        # Add extra fields
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'tool_name'):
            log_data['tool_name'] = record.tool_name

        return json.dumps(log_data)


def with_request_id(func: Callable) -> Callable:
    """Decorator to add request ID to tool calls."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request_id = str(uuid.uuid4())[:8]
        token = request_id_var.set(request_id)
        start = time.perf_counter()

        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            logger = logging.getLogger('daem0nmcp.server')
            logger.info(
                f"Tool completed",
                extra={'duration_ms': round(duration_ms, 2), 'tool_name': func.__name__}
            )
            request_id_var.reset(token)

    return wrapper
```

**Step 2: Commit**

```bash
git add daem0nmcp/logging_config.py daem0nmcp/server.py
git commit -m "feat: add structured logging with request IDs

- Add request ID tracking per tool call
- Log timing for performance diagnosis
- JSON-structured logs for parsing"
```

---

## Phase 8: CLI and Data Quality

### Task 8.1: CLI --json and --project-path Flags

**Files:**
- Modify: `daem0nmcp/cli.py` (add global flags)

**Step 1: Add global arguments**

Modify `daem0nmcp/cli.py`:

```python
def main():
    parser = argparse.ArgumentParser(description="Daem0nMCP CLI")

    # Global options
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--project-path", help="Project root path")

    subparsers = parser.add_subparsers(dest="command")
    # ... existing subparsers ...

    args = parser.parse_args()

    # Set project path if provided
    if args.project_path:
        os.environ['DAEM0NMCP_PROJECT_ROOT'] = args.project_path

    # ... rest of command handling ...

    # Output formatting
    if args.json:
        import json
        print(json.dumps(result, default=str))
    else:
        # Human-readable output
        ...
```

**Step 2: Commit**

```bash
git add daem0nmcp/cli.py
git commit -m "feat: add --json and --project-path to CLI

- --json for automation/scripting output
- --project-path for explicit project selection
- Useful for pre-commit hooks and CI"
```

---

### Task 8.2: TODO Scanner Improvements

**Files:**
- Modify: `daem0nmcp/server.py` (_scan_for_todos function)
- Modify: `daem0nmcp/config.py` (add config options)

**Step 1: Add configuration**

Add to `daem0nmcp/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # TODO scanner config
    todo_skip_dirs: List[str] = [
        "node_modules", ".git", ".venv", "venv", "__pycache__",
        "dist", "build", ".tox", ".mypy_cache"
    ]
    todo_skip_extensions: List[str] = [".pyc", ".pyo", ".so", ".dylib"]
    todo_max_files: int = 500
```

**Step 2: Enhance scanner**

Modify `_scan_for_todos` in `daem0nmcp/server.py`:

```python
import hashlib

def _scan_for_todos(
    directory: str,
    max_files: int = 500,
    skip_dirs: Optional[List[str]] = None,
    skip_extensions: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Scan for TODO/FIXME/HACK comments with dedup.

    Supports:
    - Single-line comments (# // --)
    - Multi-line block comments (/* */ ''' \""")
    - Content hashing to avoid duplicates
    """
    from pathlib import Path

    skip_dirs = skip_dirs or settings.todo_skip_dirs
    skip_extensions = skip_extensions or settings.todo_skip_extensions

    todos = []
    seen_hashes = set()
    files_scanned = 0

    for path in Path(directory).rglob("*"):
        if files_scanned >= max_files:
            break

        # Skip directories and filtered paths
        if path.is_dir():
            continue
        if any(skip in path.parts for skip in skip_dirs):
            continue
        if path.suffix in skip_extensions:
            continue

        try:
            content = path.read_text(errors='ignore')
            files_scanned += 1

            # Multi-line pattern for block comments
            import re
            patterns = [
                r'#\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+?)$',
                r'//\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+?)$',
                r'--\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+?)$',
                r'/\*\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+?)\*/',
                r'"""\s*(TODO|FIXME|HACK|XXX)[\s:]+(.+?)"""',
            ]

            for i, line in enumerate(content.split('\n'), 1):
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE | re.MULTILINE)
                    if match:
                        todo_type = match.group(1).upper()
                        todo_content = match.group(2).strip()

                        # Dedupe by content hash
                        content_hash = hashlib.md5(
                            f"{path.name}:{todo_content}".encode()
                        ).hexdigest()[:8]

                        if content_hash not in seen_hashes:
                            seen_hashes.add(content_hash)
                            todos.append({
                                "file": str(path.relative_to(directory)),
                                "line": i,
                                "type": todo_type,
                                "content": todo_content,
                                "hash": content_hash
                            })
                        break

        except Exception:
            continue

    return todos
```

**Step 3: Commit**

```bash
git add daem0nmcp/server.py daem0nmcp/config.py
git commit -m "feat: enhance TODO scanner with config and dedup

- Configurable skip_dirs and skip_extensions
- Multi-line block comment support
- Content hash deduplication
- Respect max_files limit"
```

---

### Task 8.3: Data Quality - Cleanup and Dedupe Tool

**Files:**
- Modify: `daem0nmcp/server.py` (add cleanup tool)
- Modify: `daem0nmcp/memory.py` (add dedupe logic)

**Step 1: Add cleanup tool**

Add to `daem0nmcp/server.py`:

```python
@mcp.tool()
async def cleanup_memories(
    dry_run: bool = True,
    merge_duplicates: bool = True,
    project_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Clean up stale and duplicate memories.

    Identifies duplicates by:
    - Same category + normalized content + file_path

    Args:
        dry_run: Preview what would be cleaned
        merge_duplicates: Merge duplicate memories (keep newest, preserve outcomes)
        project_path: Project root path
    """
    if not project_path and not _default_project_path:
        return _missing_project_path_error()

    ctx = await get_project_context(project_path)

    async with ctx.db_manager.get_session() as session:
        result = await session.execute(select(Memory))
        all_memories = result.scalars().all()

        # Group by (category, normalized_content, file_path)
        groups = {}
        for mem in all_memories:
            # Normalize content for comparison
            normalized = ' '.join(mem.content.lower().split())
            key = (mem.category, normalized, mem.file_path or '')

            if key not in groups:
                groups[key] = []
            groups[key].append(mem)

        # Find duplicates
        duplicates = {k: v for k, v in groups.items() if len(v) > 1}

        if dry_run:
            return {
                "dry_run": True,
                "duplicate_groups": len(duplicates),
                "total_duplicates": sum(len(v) - 1 for v in duplicates.values()),
                "samples": [
                    {
                        "content": mems[0].content[:50],
                        "count": len(mems),
                        "ids": [m.id for m in mems]
                    }
                    for mems in list(duplicates.values())[:5]
                ]
            }

        # Merge duplicates: keep newest, preserve outcomes
        merged = 0
        for key, mems in duplicates.items():
            # Sort by created_at descending
            mems.sort(key=lambda m: m.created_at or datetime.min, reverse=True)
            keeper = mems[0]

            # Merge outcomes from others
            for dupe in mems[1:]:
                if dupe.outcome and not keeper.outcome:
                    keeper.outcome = dupe.outcome
                    keeper.worked = dupe.worked

                await session.delete(dupe)
                merged += 1

        return {
            "merged": merged,
            "duplicate_groups": len(duplicates),
            "message": f"Merged {merged} duplicate memories"
        }
```

**Step 2: Commit**

```bash
git add daem0nmcp/server.py daem0nmcp/memory.py
git commit -m "feat: add cleanup_memories tool for data quality

- Identify duplicates by (category, content, file_path)
- Merge duplicates preserving outcomes
- dry_run mode for safe preview"
```

---

## Updated Summary

### New MCP Tools (9 total)
1. `rebuild_index` - Force rebuild search indexes
2. `health` - Version and status info
3. `export_data` - Export memories/rules as JSON
4. `import_data` - Import from JSON
5. `pin_memory` - Protect important memories
6. `archive_memory` - Hide without deleting
7. `prune_memories` - Clean old memories
8. `cleanup_memories` - Dedupe and merge duplicates

### Schema Changes
- Add `vector_embedding` column (migration 1)
- Add FTS5 virtual table (migration 2)
- Add `pinned`, `archived` columns (migration 3)
- Add `file_path_relative` column (migration 4)

### Configuration Options
- `max_project_contexts` (default: 10)
- `context_ttl_seconds` (default: 3600)
- `max_content_size` (default: 1MB)
- `max_chunks` (default: 50)
- `ingest_timeout` (default: 30s)
- `allowed_url_schemes` (default: http, https)
- `todo_skip_dirs` (default: node_modules, .git, etc.)
- `todo_skip_extensions` (default: .pyc, .pyo, etc.)
- `todo_max_files` (default: 500)

### SQLite PRAGMAs
- `journal_mode=WAL`
- `synchronous=NORMAL`
- `busy_timeout=30000`
- `foreign_keys=ON`
- `temp_store=MEMORY`
- `cache_size=-64000`

### Test Files (New)
- `tests/test_context.py`
- `tests/test_index_freshness.py`
- `tests/test_ingest.py`
- `tests/test_fts.py`
- `tests/test_ops.py`
- `tests/test_git.py`
- `tests/test_migrations.py`
- `tests/test_database.py`

---

**Plan complete and saved to `docs/plans/2025-12-21-daem0nmcp-enhancements.md`.**

**Two execution options:**

1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Open new session in worktree with executing-plans, batch execution with checkpoints

**Which approach?**
