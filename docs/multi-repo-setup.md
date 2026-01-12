# Multi-Repository Setup Guide

Claude Memory supports projects split across multiple repositories while maintaining
a unified memory context.

## Architecture Options

### Option 1: Consolidated Parent (Recommended)

All memories stored in parent directory's `.claude_memory/`:

```
/workspace/
├── .claude_memory/        ← All memories here
├── backend/
│   └── (no .claude_memory)
└── client/
    └── (no .claude_memory)
```

**Pros:**
- Single source of truth
- No cross-repo query overhead
- Simpler backup/restore

**Setup:**
```python
# Always use parent as project_path
get_briefing(project_path="/workspace")
remember(content="...", project_path="/workspace")
```

### Option 2: Linked Repositories

Each repo has its own `.claude_memory/` but can read from linked repos:

```
/workspace/
├── backend/
│   └── .claude_memory/    ← Backend memories
└── client/
    └── .claude_memory/    ← Client memories (linked to backend)
```

**Pros:**
- Repository independence
- Can work offline on single repo
- Clear ownership of decisions

**Setup:**
```python
# In backend
link_projects(linked_path="/workspace/client", relationship="same-project")

# Query spans both
recall(topic="auth", include_linked=True)
```

## Migrating to Consolidated

If you have existing separate `.claude_memory/` directories:

```python
# 1. Initialize parent
get_briefing(project_path="/workspace")

# 2. Link children
link_projects(linked_path="/workspace/backend")
link_projects(linked_path="/workspace/client")

# 3. Merge databases
consolidate_linked_databases(archive_sources=True)

# 4. Verify
get_briefing(project_path="/workspace")
# Check: memories_merged count matches expectations
```

## Relationship Types

| Type | Use Case |
|------|----------|
| `same-project` | Client/server pair, monorepo split |
| `upstream` | Shared library your project depends on |
| `downstream` | App that depends on your library |
| `related` | Loosely associated projects |

## FAQ

**Q: Can I undo consolidation?**
A: If you used `archive_sources=True`, original databases are at `.claude_memory.archived/`.

**Q: What happens to file paths after merge?**
A: They're preserved. A memory about `backend/src/auth.py` keeps that path.

**Q: Does consolidation copy or move?**
A: Copy. Source data remains unless you archive.
