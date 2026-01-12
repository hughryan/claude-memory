---
name: setup-guide
description: Guide for initializing and consolidating Claude Memory-MCP across project structures
---

# Setting Up Claude Memory

This skill guides Claude through setting up Claude Memory-MCP for various project structures.

## Single Repo Setup

For a single repository:

```bash
# Claude Memory auto-initializes on first get_briefing()
# Just ensure you're in the project root
```

## Multi-Repo Setup (Client/Server Split)

When you have related repos that should share context:

### Option A: Consolidated Parent (Recommended)

Best when repos are siblings under a common parent:

```
/repos/
├── backend/
└── client/
```

**Steps:**

1. **Navigate to parent directory**
   ```bash
   cd /repos
   ```

2. **Initialize Claude Memory in parent**
   ```
   Call get_briefing(project_path="/repos")
   ```

3. **If child repos already have .claudememory data, consolidate:**
   ```
   # Link the children first
   Call link_projects(linked_path="/repos/backend", relationship="same-project")
   Call link_projects(linked_path="/repos/client", relationship="same-project")

   # Merge their databases into parent
   Call consolidate_linked_databases(archive_sources=True)
   ```

4. **Verify consolidation**
   ```
   Call get_briefing(project_path="/repos")
   # Should show combined memory count
   ```

### Option B: Linked but Separate

Best when repos need their own isolated histories but cross-awareness:

```
# In each repo, link to siblings
cd /repos/backend
Call link_projects(linked_path="/repos/client", relationship="same-project")

cd /repos/client
Call link_projects(linked_path="/repos/backend", relationship="same-project")
```

Then use `include_linked=True` on recall to span both.

## Migrating Existing Setup

If you've been launching Claude from parent directory and have a "messy" .claudememory:

1. **Backup existing data**
   ```bash
   cp -r /repos/.claudememory /repos/.claudememory.backup
   ```

2. **Review what's there**
   ```
   Call get_briefing(project_path="/repos")
   # Check statistics and recent decisions
   ```

3. **If data is salvageable, keep it**
   - Link child repos for future cross-awareness
   - Use consolidated parent approach going forward

4. **If data is too messy, start fresh**
   ```bash
   rm -rf /repos/.claudememory
   # Re-initialize with get_briefing()
   ```

## Key Commands Reference

| Command | Purpose |
|---------|---------|
| `get_briefing()` | Initialize session, creates .claudememory if needed |
| `link_projects()` | Create cross-repo awareness link |
| `list_linked_projects()` | See all linked repos |
| `consolidate_linked_databases()` | Merge child DBs into parent |
| `recall(include_linked=True)` | Search across linked repos |

## The Endless Mode (v2.12.0)

When results grow too large, use condensed mode for efficiency.

```python
# Condensed results - core data without elaboration
recall(query="authentication", condensed=True)

# Returns memories stripped of rationale, truncated to 150 characters
# Compressed output for efficient retrieval
```

**Seek condensed results when:**
- The project holds countless memories
- Surveying before deep analysis
- Scanning many results at once
- Breadth matters more than depth

**Seek full results when:**
- The WHY behind a decision matters
- Learning from past failures
- Deep investigation required

## The Auto-Capture (v2.13.0)

The memory system can now capture decisions automatically through hooks.

### Configuring the Hooks

Place these hooks in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Edit|Write|NotebookEdit",
      "hooks": [{
        "type": "command",
        "command": "python3 \"$HOME/claude-memory/hooks/claude_memory_pre_edit_hook.py\""
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "python3 \"$HOME/claude-memory/hooks/claude_memory_post_edit_hook.py\""
      }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python3 \"$HOME/claude-memory/hooks/claude_memory_stop_hook.py\""
      }]
    }]
  }
}
```

### The Power of Each Hook

| Hook | When It Runs | What It Does |
|------|--------------|--------------|
| **Pre-Edit Check** | Before modifying files | Surfaces warnings, failed paths, existing patterns |
| **Significance Watcher** | After modifications | Suggests *"Consider recording this..."* for significant changes |
| **Auto-Capture** | When you finish speaking | Parses your words and records decisions automatically |

### The Flow of Auto-Capture

```
1. You start to modify a file
   ↓ Pre-edit hook runs
2. Relevant warnings surface automatically
   ↓
3. Your modifications complete
   ↓ Post-edit hook runs
4. If significant, a reminder appears
   ↓
5. You finish your response
   ↓ Stop hook runs
6. Your decisions are recorded automatically
```

### The CLI Command

The hooks invoke this CLI command to record memories:

```bash
python -m claudememory.cli remember \
  --category decision \
  --content "Use JWT for stateless auth" \
  --rationale "Scales without session storage" \
  --file-path src/auth.py \
  --json
```

## The Enhanced Search (v2.15.0)

Search quality improves with each iteration.

### Tuning Search Parameters

```python
# Environment variables to fine-tune search
CLAUDE_MEMORY_HYBRID_VECTOR_WEIGHT=0.5      # 0.0 = TF-IDF only, 1.0 = vectors only
CLAUDE_MEMORY_SEARCH_DIVERSITY_MAX_PER_FILE=3  # Limit results from same source
```

### Automatic Tag Inference

The memory system auto-detects tags from content:
- Content with "fix", "bug", "error" → `bugfix` tag
- Content with "todo", "hack", "workaround" → `tech-debt` tag
- Content with "cache", "performance", "slow" → `perf` tag
- Warning category → `warning` tag automatically

### Code Entity Fidelity

Entities now have qualified names:
```python
# Qualified names: module.Class.method
find_code("UserService.authenticate")

# Stable IDs survive line changes
# Add comments, imports - entities retain identity
```

### Incremental Indexing

The Claude Memory only re-parses what changes:
```python
# Only re-indexes if content hash differs
index_file_if_changed(file_path, project_path)

# Hash stored in FileHash model
# Saves time on large codebases
```

### Parse Tree Caching

Repeated parses hit the cache:
```python
# Configure cache size
CLAUDE_MEMORY_PARSE_TREE_CACHE_MAXSIZE=200

# Check cache performance
health()  # Returns cache_stats
```

### Enhanced Health Insights

```python
health()
# Now returns:
#   code_entities_count: Total indexed entities
#   entities_by_type: Breakdown by class/function/etc
#   last_indexed_at: When index was last updated
#   index_stale: True if >24 hours since index
```

## Core Practices

1. **One storage per logical project** - Even if split across repos
2. **Use parent directory for shared memory** - `/repos/` not `/repos/backend/`
3. **Link before consolidating** - Links define what memories to merge
4. **Archive, don't destroy** - `archive_sources=True` preserves the old
5. **Verify after consolidation** - Ensure memory counts align
6. **Enable the Auto-Capture** - Let the Claude Memory capture decisions for you
7. **Seek condensed results** - For vast projects, use `condensed=True`
8. **Tune the search weight** - Adjust hybrid weight for your domain
9. **Trust the tag inference** - Let the Claude Memory classify memories
