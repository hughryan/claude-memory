# Daem0n-MCP Cognitive Architecture Upgrade

**Date:** 2026-01-02
**Status:** Proposed
**Author:** Claude (with user collaboration)

## Executive Summary

This plan evolves Daem0n-MCP from a "Reactive Semantic Engine" to a full "Cognitive Architecture" with:

1. **Scalable vector infrastructure** (Qdrant backend)
2. **Proactive alerting** (file watcher + notification channels)
3. **Code understanding** (AST indexing + entity linking)
4. **Team knowledge sharing** (git-based sync)

**Key design decision:** Enhance the existing architecture rather than replace it with off-the-shelf components (like Mem0). The current system has domain-specific features (Sacred Covenant, Rules, graph relationships, decay/reinforcement) that generic tools don't provide.

---

## Background

### Current Architecture (v2.7)

| Component | Implementation |
|-----------|----------------|
| Storage | SQLite + SQLAlchemy (async) |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`), stored as packed bytes in SQLite |
| Search | Hybrid: TF-IDF + Vector similarity + FTS5 fallback |
| Memory Model | 4 categories, episodic/semantic distinction, decay logic, graph relationships |
| Interface | MCP (request/response only) |

### Limitations

1. **Reactive only** - waits for LLM to ask; never proactively warns
2. **No code understanding** - knows about files but not structure/dependencies
3. **Single-user** - no team knowledge sharing
4. **Vector storage in SQLite** - works but doesn't scale elegantly

---

## Proposed Architecture

### The Three Layers

```
+-------------------------------------------------------------------+
|                     DAEM0N COGNITIVE STACK                        |
+-------------------------------------------------------------------+
|  Layer 3: CODE UNDERSTANDING (new)                                |
|  +-------------+  +-------------+  +---------------------------+  |
|  |  AST/Graph  |  |  LSP/Symbols|  |  Call Graph Indexer       |  |
|  |  Indexer    |  |  (live)     |  |  (dependencies)           |  |
|  +------+------+  +------+------+  +-----------+---------------+  |
|         +----------------+-----------------------+                |
|                          v                                        |
|                   Code Entity Store                               |
|              (files, symbols, relationships)                      |
+-------------------------------------------------------------------+
|  Layer 2: MEMORY SYSTEM (enhanced current)                        |
|  +-------------+  +-------------+  +---------------------------+  |
|  |  Memories   |  |   Rules     |  |  Memory Relationships     |  |
|  |  (SQLite)   |  |  (SQLite)   |  |  (Graph edges)            |  |
|  +------+------+  +------+------+  +-----------+---------------+  |
|         +----------------+-----------------------+                |
|                          v                                        |
|  +-----------------------------------------------------------+   |
|  |              Qdrant Vector Store (new)                    |   |
|  |   - Memory embeddings (migrated from SQLite blobs)        |   |
|  |   - Code entity embeddings (linked from Layer 3)          |   |
|  |   - Fast filtered search + metadata                       |   |
|  +-----------------------------------------------------------+   |
+-------------------------------------------------------------------+
|  Layer 1: INTERFACE (extended)                                    |
|  +-------------+  +-------------+  +---------------------------+  |
|  |  MCP Server |  |  Watcher    |  |  Sync Service             |  |
|  |  (reactive) |  |  (proactive)|  |  (team sharing)           |  |
|  +-------------+  +-------------+  +---------------------------+  |
+-------------------------------------------------------------------+
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite stays for structured data | Memories, rules, relationships - relational data that benefits from ACID, migrations, joins |
| Qdrant for vectors only | Embeddings move out of SQLite blobs; enables fast ANN search, metadata filtering, scalability |
| Code understanding is separate layer | Indexes YOUR PROJECTS, not Daem0n itself. Links to memories via `code_refs` |
| Three interface modes | Reactive (current MCP), Proactive (watcher), Sync (team sharing) |
| Git-based sync first | Works with existing workflows; cloud sync can come later |

---

## Phase 0: Foundation (Qdrant Integration)

**Goal:** Replace SQLite blob storage with Qdrant without breaking anything.

### New File: `daem0nmcp/qdrant_store.py`

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter

class QdrantVectorStore:
    """Vector storage backend - replaces SQLite blob storage."""

    COLLECTION_MEMORIES = "daem0n_memories"
    COLLECTION_CODE = "daem0n_code_entities"  # For Layer 3

    def __init__(self, path: str = "./storage/qdrant"):
        # Local mode - no server needed for single-user
        self.client = QdrantClient(path=path)
        self._ensure_collections()

    def _ensure_collections(self):
        collections = [c.name for c in self.client.get_collections().collections]

        if self.COLLECTION_MEMORIES not in collections:
            self.client.create_collection(
                collection_name=self.COLLECTION_MEMORIES,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    def upsert_memory(self, memory_id: int, embedding: list[float], metadata: dict):
        """Store/update a memory's vector."""
        self.client.upsert(
            collection_name=self.COLLECTION_MEMORIES,
            points=[PointStruct(
                id=memory_id,
                vector=embedding,
                payload=metadata  # category, tags, file_path, worked, etc.
            )]
        )

    def search(
        self,
        query_vector: list[float],
        limit: int = 20,
        category_filter: list[str] = None,
        tags_filter: list[str] = None,
        file_path: str = None
    ) -> list[tuple[int, float]]:
        """Search with metadata filtering - much faster than SQLite."""
        from qdrant_client.models import FieldCondition, MatchAny, MatchValue

        filters = []
        if category_filter:
            filters.append(FieldCondition(key="category", match=MatchAny(any=category_filter)))
        if tags_filter:
            filters.append(FieldCondition(key="tags", match=MatchAny(any=tags_filter)))
        if file_path:
            filters.append(FieldCondition(key="file_path", match=MatchValue(value=file_path)))

        results = self.client.search(
            collection_name=self.COLLECTION_MEMORIES,
            query_vector=query_vector,
            query_filter=Filter(must=filters) if filters else None,
            limit=limit
        )

        return [(hit.id, hit.score) for hit in results]

    def delete_memory(self, memory_id: int):
        """Remove a memory's vector."""
        self.client.delete(
            collection_name=self.COLLECTION_MEMORIES,
            points_selector=[memory_id]
        )
```

### Migration Script

```python
# daem0nmcp/migrations/migrate_vectors.py

async def migrate_vectors_to_qdrant(db: DatabaseManager, qdrant: QdrantVectorStore):
    """One-time migration of existing vectors from SQLite to Qdrant."""
    from daem0nmcp.models import Memory
    from daem0nmcp import vectors
    from sqlalchemy import select

    async with db.get_session() as session:
        result = await session.execute(
            select(Memory).where(Memory.vector_embedding.isnot(None))
        )
        memories = result.scalars().all()

        migrated = 0
        for mem in memories:
            embedding = vectors.decode(mem.vector_embedding)
            if embedding:
                qdrant.upsert_memory(
                    memory_id=mem.id,
                    embedding=embedding,
                    metadata={
                        "category": mem.category,
                        "tags": mem.tags or [],
                        "file_path": mem.file_path,
                        "worked": mem.worked,
                        "is_permanent": mem.is_permanent
                    }
                )
                migrated += 1

        return {"migrated": migrated, "total": len(memories)}
```

### Tasks

| Task | Files | Notes |
|------|-------|-------|
| Add Qdrant dependency | `pyproject.toml` | `qdrant-client` |
| Create `QdrantVectorStore` class | `daem0nmcp/qdrant_store.py` | New file |
| Add Qdrant config options | `daem0nmcp/config.py` | Path, optional remote URL |
| Modify `MemoryManager` to use Qdrant | `daem0nmcp/memory.py` | Replace `VectorIndex` calls |
| Update `HybridSearch` | `daem0nmcp/vectors.py` | Use Qdrant for vector half |
| Write migration script | `daem0nmcp/migrations/migrate_vectors.py` | One-time SQLite -> Qdrant |
| Add Qdrant collection for code entities | `daem0nmcp/qdrant_store.py` | Prep for Phase 2 |
| Update tests | `tests/test_vectors.py` | Mock Qdrant or use local |

### Verification

- All existing tests pass
- `recall` and `search` return same results
- Performance improved for large memory sets

---

## Phase 1: Proactive Layer

**Goal:** Daem0n watches files and alerts before mistakes.

### New File: `daem0nmcp/watcher.py`

```python
"""
Proactive file watcher - detects pattern violations before they're committed.

Notification channels (priority order):
1. MCP notifications (if client supports)
2. Editor extension API (VSCode, Cursor)
3. System notifications (fallback)
4. Log file (last resort)
"""

import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DaemonWatcher(FileSystemEventHandler):
    def __init__(self, memory_manager, qdrant_store, project_path: str):
        self.memory = memory_manager
        self.qdrant = qdrant_store
        self.project_path = Path(project_path)
        self.notification_channels = []
        self._debounce_timers = {}

    def on_modified(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)

        # Skip non-code files
        if path.suffix not in {'.py', '.js', '.ts', '.tsx', '.go', '.rs', '.java'}:
            return

        # Debounce rapid saves
        self._schedule_analysis(path)

    def _schedule_analysis(self, path: Path, delay: float = 1.0):
        """Debounce analysis to avoid spam on rapid saves."""
        key = str(path)
        if key in self._debounce_timers:
            self._debounce_timers[key].cancel()

        loop = asyncio.get_event_loop()
        timer = loop.call_later(
            delay,
            lambda: asyncio.create_task(self._analyze_change(path))
        )
        self._debounce_timers[key] = timer

    async def _analyze_change(self, path: Path):
        """Core analysis: does this change violate any known patterns?"""
        from daem0nmcp import vectors

        relative_path = path.relative_to(self.project_path)

        # 1. Get memories associated with this file
        file_memories = await self.memory.recall_for_file(
            str(relative_path),
            project_path=str(self.project_path)
        )

        # 2. Check for warnings or failed approaches
        warnings = file_memories.get('warnings', [])
        failed = [m for cat in file_memories.values()
                  if isinstance(cat, list)
                  for m in cat if m.get('worked') is False]

        if not warnings and not failed:
            return  # No concerns

        # 3. Read the changed content
        try:
            content = path.read_text()
        except Exception:
            return

        # 4. Semantic similarity check against warnings
        content_embedding = vectors.encode(content[:2000])  # First 2k chars

        if content_embedding:
            decoded = vectors.decode(content_embedding)
            if decoded:
                # Search for similar warning patterns
                similar = self.qdrant.search(
                    query_vector=decoded,
                    limit=5,
                    category_filter=['warning']
                )

                # High similarity to a warning = potential violation
                violations = [(mid, score) for mid, score in similar if score > 0.7]

                if violations:
                    await self._emit_notification(
                        level="warning",
                        file=str(relative_path),
                        message=f"Code similar to {len(violations)} known problem pattern(s)",
                        memory_ids=[mid for mid, _ in violations]
                    )

    async def _emit_notification(self, level: str, **data):
        """Send notification through available channels."""
        notification = {"level": level, **data}

        for channel in self.notification_channels:
            try:
                await channel.send(notification)
            except Exception as e:
                logger.debug(f"Channel {channel} failed: {e}")

    def add_channel(self, channel):
        """Register a notification channel."""
        self.notification_channels.append(channel)


def start_watcher(project_path: str, memory_manager, qdrant_store) -> Observer:
    """Start the file watcher daemon."""
    handler = DaemonWatcher(memory_manager, qdrant_store, project_path)

    observer = Observer()
    observer.schedule(handler, project_path, recursive=True)
    observer.start()

    logger.info(f"Watcher started for {project_path}")
    return observer
```

### Notification Channels

```python
# daem0nmcp/channels/mcp_notify.py

class MCPNotificationChannel:
    """Send notifications via MCP protocol."""

    def __init__(self, server):
        self.server = server

    async def send(self, notification: dict):
        await self.server.send_notification(
            method="daem0n/warning",
            params={
                "type": notification["level"],
                "file": notification.get("file"),
                "message": notification["message"],
                "memory_ids": notification.get("memory_ids", []),
            }
        )


# daem0nmcp/channels/system_notify.py

class SystemNotificationChannel:
    """Send system tray notifications."""

    async def send(self, notification: dict):
        try:
            from plyer import notification as plyer_notify
            plyer_notify.notify(
                title=f"Daem0n: {notification['level'].upper()}",
                message=notification["message"],
                app_name="Daem0n-MCP"
            )
        except ImportError:
            pass  # plyer not installed


# daem0nmcp/channels/log_notify.py

import logging

class LogNotificationChannel:
    """Log notifications to file (last resort)."""

    def __init__(self, log_path: str = ".daem0n/notifications.log"):
        self.logger = logging.getLogger("daem0n.notifications")
        handler = logging.FileHandler(log_path)
        self.logger.addHandler(handler)

    async def send(self, notification: dict):
        self.logger.warning(f"{notification['level']}: {notification['message']}")
```

### Tasks

| Task | Files | Notes |
|------|-------|-------|
| Create watcher daemon | `daem0nmcp/watcher.py` | New file |
| Define notification protocol | `daem0nmcp/channels/__init__.py` | Abstract base |
| MCP notification channel | `daem0nmcp/channels/mcp_notify.py` | If client supports |
| System notification channel | `daem0nmcp/channels/system_notify.py` | Fallback |
| Log file channel | `daem0nmcp/channels/log_notify.py` | Last resort |
| Enhance git hook integration | `daem0nmcp/hooks.py` | Pre-commit checks |
| Add CLI command to start watcher | `daem0nmcp/cli.py` | `daem0n watch` |
| Add watcher config | `daem0nmcp/config.py` | Patterns, debounce, channels |
| Integration tests | `tests/test_watcher.py` | New file |

### New CLI Commands

```bash
daem0n watch                    # Start watcher daemon
daem0n watch --background       # Daemonize
daem0n hook install             # Install git hooks
daem0n hook check               # Manual pre-commit check
```

---

## Phase 2: Code Understanding

**Goal:** Daem0n understands project structure and can answer "what depends on X?"

### New Models

```python
# daem0nmcp/models.py (additions)

class CodeEntity(Base):
    """
    A code element from an indexed project.

    Types: file, class, function, method, variable, import, module
    """
    __tablename__ = "code_entities"

    id = Column(String, primary_key=True)  # hash of project+path+name+type
    project_path = Column(String, nullable=False, index=True)

    entity_type = Column(String, nullable=False)  # file, class, function, etc.
    name = Column(String, nullable=False)
    qualified_name = Column(String)  # e.g., "myapp.models.User.save"
    file_path = Column(String, nullable=False, index=True)
    line_start = Column(Integer)
    line_end = Column(Integer)

    signature = Column(Text)
    docstring = Column(Text)

    # Structural relationships
    calls = Column(JSON, default=list)
    called_by = Column(JSON, default=list)
    imports = Column(JSON, default=list)
    inherits = Column(JSON, default=list)

    indexed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MemoryCodeRef(Base):
    """Links memories to code entities."""
    __tablename__ = "memory_code_refs"

    id = Column(Integer, primary_key=True)
    memory_id = Column(Integer, ForeignKey("memories.id", ondelete="CASCADE"), index=True)
    code_entity_id = Column(String, index=True)

    # Snapshot (survives reindex)
    entity_type = Column(String)
    entity_name = Column(String)
    file_path = Column(String)
    line_number = Column(Integer)

    relationship = Column(String)  # "about", "modifies", "introduces", "deprecates"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### Code Indexer

```python
# daem0nmcp/code_indexer.py

import ast
import hashlib
from pathlib import Path
from typing import Generator

class PythonIndexer:
    """Extract entities from Python files using AST."""

    def index_file(self, file_path: Path, project_path: Path) -> Generator:
        try:
            source = file_path.read_text()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            return

        relative_path = file_path.relative_to(project_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                yield self._make_entity(
                    project_path=str(project_path),
                    entity_type="class",
                    name=node.name,
                    file_path=str(relative_path),
                    line_start=node.lineno,
                    line_end=node.end_lineno,
                    signature=f"class {node.name}",
                    docstring=ast.get_docstring(node)
                )

            elif isinstance(node, ast.FunctionDef):
                yield self._make_entity(
                    project_path=str(project_path),
                    entity_type="function",
                    name=node.name,
                    file_path=str(relative_path),
                    line_start=node.lineno,
                    line_end=node.end_lineno,
                    signature=self._get_function_signature(node),
                    docstring=ast.get_docstring(node)
                )

    def _make_entity(self, **kwargs):
        from daem0nmcp.models import CodeEntity
        id_string = f"{kwargs['project_path']}:{kwargs['file_path']}:{kwargs['name']}:{kwargs['entity_type']}"
        entity_id = hashlib.sha256(id_string.encode()).hexdigest()[:16]
        return CodeEntity(id=entity_id, **kwargs)

    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        args = [arg.arg for arg in node.args.args]
        return f"def {node.name}({', '.join(args)})"


class CodeIndexManager:
    """Manages code indexing across a project."""

    def __init__(self, db, qdrant):
        self.db = db
        self.qdrant = qdrant
        self.indexers = {'.py': PythonIndexer()}

    async def index_project(self, project_path: str, patterns: list = None):
        """Full project index."""
        from daem0nmcp import vectors
        from daem0nmcp.models import CodeEntity
        from sqlalchemy import delete

        project = Path(project_path)
        patterns = patterns or ['**/*.py']

        entities = []

        for pattern in patterns:
            for file_path in project.glob(pattern):
                if self._should_skip(file_path):
                    continue

                suffix = file_path.suffix
                if suffix in self.indexers:
                    for entity in self.indexers[suffix].index_file(file_path, project):
                        entities.append(entity)

        # Store in SQLite
        async with self.db.get_session() as session:
            await session.execute(
                delete(CodeEntity).where(CodeEntity.project_path == project_path)
            )
            for entity in entities:
                session.add(entity)

        # Index in Qdrant
        for entity in entities:
            text = f"{entity.signature or ''} {entity.docstring or ''}"
            if text.strip():
                embedding = vectors.encode(text)
                if embedding:
                    self.qdrant.client.upsert(
                        collection_name="daem0n_code_entities",
                        points=[{
                            "id": entity.id,
                            "vector": vectors.decode(embedding),
                            "payload": {
                                "entity_type": entity.entity_type,
                                "name": entity.name,
                                "file_path": entity.file_path,
                            }
                        }]
                    )

        return {"indexed": len(entities), "project": project_path}

    def _should_skip(self, path: Path) -> bool:
        skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}
        return any(part in skip_dirs for part in path.parts)
```

### New MCP Tools

```python
@mcp.tool()
async def index_project(path: str = None, patterns: list = None) -> dict:
    """Index a project's code structure."""
    path = path or os.getcwd()
    return await code_index.index_project(path, patterns)

@mcp.tool()
async def analyze_impact(entity_name: str, project_path: str = None) -> dict:
    """Analyze what would be affected by changing a code entity."""
    # Implementation as described in design
    pass

@mcp.tool()
async def find_code(query: str, project_path: str = None) -> dict:
    """Semantic search across code entities."""
    pass
```

### Tasks

| Task | Files | Notes |
|------|-------|-------|
| Add `CodeEntity` model | `daem0nmcp/models.py` | New table |
| Add `MemoryCodeRef` model | `daem0nmcp/models.py` | Link table |
| Create migration | `daem0nmcp/migrations/` | New tables |
| Python AST indexer | `daem0nmcp/code_indexer.py` | New file |
| Code index manager | `daem0nmcp/code_indexer.py` | Orchestrates indexing |
| Auto-link symbols in `remember` | `daem0nmcp/memory.py` | Parse backticks |
| Add `analyze_impact` tool | `daem0nmcp/server.py` | New MCP tool |
| Add `index_project` tool | `daem0nmcp/server.py` | New MCP tool |
| CLI for indexing | `daem0nmcp/cli.py` | `daem0n index` |
| Tests | `tests/test_code_indexer.py` | New file |

---

## Phase 3: Team Sync

**Goal:** Team can share patterns, warnings, and key decisions.

### Memory Visibility Model

```python
# daem0nmcp/models.py (additions)

class MemoryVisibility(str, Enum):
    PRIVATE = "private"      # Only on this machine
    TEAM = "team"            # Syncs to team store
    PUBLIC = "public"        # Future: cross-team/community patterns

# Add to Memory model:
visibility = Column(String, default="private", index=True)
origin_id = Column(String, nullable=True)     # UUID from original creator
origin_user = Column(String, nullable=True)   # Who created this
synced_at = Column(DateTime, nullable=True)   # Last sync time
sync_hash = Column(String, nullable=True)     # Content hash for conflict detection
```

### Git-Based Sync

```python
# daem0nmcp/sync/git_sync.py

import yaml
import hashlib
from pathlib import Path

class GitSyncManager:
    """
    Git-based team memory sync.

    Structure:
        .daem0n-team/
        +-- memories/
        |   +-- patterns/
        |   +-- warnings/
        |   +-- decisions/
        +-- rules/
    """

    def __init__(self, repo_path: str, memory_manager):
        self.repo_path = Path(repo_path)
        self.memory = memory_manager
        self.memories_dir = self.repo_path / "memories"

    async def export_for_sync(self, visibility: str = "team") -> dict:
        """Export team-visible memories to YAML files."""
        # Implementation as described in design
        pass

    async def import_from_sync(self, dry_run: bool = True) -> dict:
        """Import team memories from YAML files."""
        # Implementation as described in design
        pass

    def _compute_hash(self, mem) -> str:
        content = f"{mem.content}|{mem.rationale or ''}|{mem.outcome or ''}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
```

### Configuration

```yaml
# .daem0n/config.yaml

sync:
  enabled: true
  repo: "../.daem0n-team"

  include_categories:
    - pattern
    - warning
    - decision

  auto_export_on:
    - record_outcome
    - add_rule

  default_visibility: private
  conflict_strategy: prompt
```

### Tasks

| Task | Files | Notes |
|------|-------|-------|
| Add visibility field to Memory | `daem0nmcp/models.py` | + migration |
| Add sync metadata fields | `daem0nmcp/models.py` | origin_id, etc. |
| Create migration | `daem0nmcp/migrations/` | New columns |
| Git sync manager | `daem0nmcp/sync/git_sync.py` | New file |
| YAML export/import | `daem0nmcp/sync/git_sync.py` | Serialize memories |
| Conflict detection | `daem0nmcp/sync/git_sync.py` | Hash comparison |
| Add `sync_push` tool | `daem0nmcp/server.py` | Export to repo |
| Add `sync_pull` tool | `daem0nmcp/server.py` | Import from repo |
| Add sync config | `daem0nmcp/config.py` | Repo path, auto-sync |
| CLI commands | `daem0nmcp/cli.py` | `daem0n sync` |
| Tests | `tests/test_sync.py` | New file |

### New CLI Commands

```bash
daem0n sync init <repo-path>    # Initialize sync repo
daem0n sync push                # Export team memories
daem0n sync pull                # Import (dry-run first)
daem0n sync pull --apply        # Actually import
daem0n sync status              # Show pending conflicts
```

---

## Implementation Order

```
                    +------------------+
                    |    Phase 0       |
                    |    Qdrant        |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
      +------------+  +------------+  +------------+
      |  Phase 1   |  |  Phase 2   |  |  Phase 3   |
      |  Watcher   |  |   Code     |  |   Sync     |
      +------------+  +------------+  +------------+
```

Phases 1, 2, and 3 can be done in parallel after Phase 0, or in any order based on priority.

---

## Final File Structure

```
daem0nmcp/
+-- __init__.py
+-- __main__.py
+-- server.py              # MCP server (enhanced)
+-- cli.py                 # CLI commands (enhanced)
+-- config.py              # Configuration (enhanced)
+-- database.py            # SQLite manager (unchanged)
+-- models.py              # SQLAlchemy models (enhanced)
+-- memory.py              # Memory manager (enhanced)
+-- similarity.py          # TF-IDF (unchanged)
+-- vectors.py             # Embedding utils (simplified)
+-- rules.py               # Rule engine (unchanged)
+-- enforcement.py         # Git enforcement (enhanced)
+-- cache.py               # Caching (unchanged)
+-- hooks.py               # Git hooks (enhanced)
|
+-- qdrant_store.py        # NEW: Qdrant vector backend
+-- watcher.py             # NEW: File watcher daemon
+-- code_indexer.py        # NEW: Code understanding
|
+-- channels/              # NEW: Notification channels
|   +-- __init__.py
|   +-- mcp_notify.py
|   +-- system_notify.py
|   +-- log_notify.py
|
+-- sync/                  # NEW: Team sync
|   +-- __init__.py
|   +-- git_sync.py
|   +-- cloud_sync.py      # Future
|
+-- migrations/
    +-- __init__.py
    +-- migrate_vectors.py # NEW: SQLite -> Qdrant
    +-- ...
```

---

## Success Criteria

| Phase | Verification |
|-------|--------------|
| Phase 0 | All existing tests pass; same search results; better perf at scale |
| Phase 1 | File change triggers notification; commit blocked on failed patterns |
| Phase 2 | `analyze_impact` returns callers + related memories |
| Phase 3 | Export/import round-trips correctly; conflicts detected |

---

## Open Questions

1. **MCP notification support** - Does Claude Code support `notifications/` methods? If not, what's the fallback?
2. **Tree-sitter for JS/TS** - Should Phase 2 include TypeScript indexing, or defer?
3. **Cloud sync** - Is git-based sync sufficient for initial release, or is cloud sync needed sooner?
4. **GraphRAG** - When does AST-based indexing become insufficient? What triggers GraphRAG adoption?

---

## Appendix: Why Not Mem0?

The recommendation suggested replacing the custom memory system with Mem0. After analysis:

| Feature | Daem0n-MCP (current) | Mem0 |
|---------|---------------------|------|
| Memory categories | 4 types with different decay | Generic "memories" |
| Sacred Covenant / Rules | Built-in enforcement | Not supported |
| Graph relationships | `MemoryRelationship` table | Not supported |
| Outcome tracking | `worked`/`failed` with boost | Not supported |
| Decay logic | Configurable per-category | Generic decay |
| Conflict detection | Semantic + polarity analysis | Basic dedup |

**Conclusion:** Mem0 would require reimplementing most of Daem0n's features on top of it. Better to keep the domain-specific logic and just upgrade the vector storage to Qdrant.
