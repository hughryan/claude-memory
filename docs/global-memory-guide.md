# Global Memory Guide

## Overview

Global Memory is Claude Memory's cross-project knowledge base. It automatically stores universal patterns, best practices, and security guidelines that apply across all your projects.

## How It Works

### Automatic Classification

When you store a memory, Claude automatically decides whether it should be:
- **Local only**: Project-specific knowledge
- **Global + Local**: Universal knowledge (stored in both locations)

**Classification Signals:**

| Type | Indicators | Example |
|------|------------|---------|
| **Local** | • Has file path<br>• Mentions "this repo", "our codebase"<br>• References project structure<br>• Ticket/PR numbers | "Use Redis for caching in src/cache.py" |
| **Global** | • No file path<br>• Uses "always", "never" language<br>• Best practice tags<br>• Language-specific patterns | "Always validate input in Python web apps" |

### Storage Locations

```
Project Memory (Local):
  /your/project/.claude-memory/storage/

Global Memory (Universal):
  ~/.claude-memory/storage/  (default)
```

**Important**: Add `.claude-memory/` to your project's `.gitignore` to avoid committing local database files.

## Usage Examples

### Storing Memories

**Universal Pattern (goes to global):**
```bash
# Via CLI
remember --category pattern \
  --content "Always use environment variables for secrets" \
  --tags security best-practice

# Via MCP tool
{
  "category": "pattern",
  "content": "Never use == for floating point comparisons",
  "tags": ["best-practice", "general"]
}

→ Result: Stored in BOTH local and global
→ Available to all projects
```

**Project-Specific Decision (stays local):**
```bash
# Has file path = automatic local classification
remember --category decision \
  --content "Use JWT tokens for API authentication" \
  --file src/auth/middleware.py

→ Result: Stored in local only
→ Only available in this project
```

### Recalling Memories

Recall automatically searches **both** local and global:

```bash
recall "input validation"

→ Returns:
  - Local memories from this project
  - Global memories from ~/.claude-memory
  - Local memories take precedence (duplicates filtered)
```

**Results are tagged:**
- Local memories: No special tag
- Global memories: `_from_global: true`

### Understanding Precedence

When similar memories exist in both local and global:

**Local Always Wins:**
```
Global: "Always validate user input"
Local:  "In this app, validate input using Joi library"

→ Recall shows: Local version only (global filtered as duplicate)
```

**Why?** Project-specific knowledge is more relevant than generic advice.

## Configuration

### Environment Variables

```bash
# Enable/disable global memory
export CLAUDE_MEMORY_GLOBAL_ENABLED=true  # default

# Custom global storage location
export CLAUDE_MEMORY_GLOBAL_PATH="/shared/team-memory/storage"

# Disable writing to global (read-only mode)
export CLAUDE_MEMORY_GLOBAL_WRITE_ENABLED=false
```

### Per-Project Opt-Out

Create `.claude-memory/config.json` in your project:
```json
{
  "global_enabled": false
}
```

## Team Collaboration

### Shared Global Memory

For teams to share global patterns:

```bash
# Point all team members to shared storage
export CLAUDE_MEMORY_GLOBAL_PATH="/mnt/shared-drive/team-memory/storage"

# Or use a git-synced location
export CLAUDE_MEMORY_GLOBAL_PATH="$HOME/team-patterns/storage"
cd ~/team-patterns
git pull  # Get latest patterns
```

### Seeding Global Patterns

Create a bootstrap script:

```python
# scripts/seed_global_patterns.py
import asyncio
from claude_memory.server import _get_global_memory_manager

UNIVERSAL_PATTERNS = [
    {
        "category": "pattern",
        "content": "Always use parameterized queries to prevent SQL injection",
        "rationale": "Security best practice across all languages",
        "tags": ["security", "database", "best-practice"]
    },
    {
        "category": "warning",
        "content": "Avoid storing secrets in environment variables in containerized environments",
        "rationale": "Secrets in env vars are visible in docker inspect",
        "tags": ["security", "docker", "anti-pattern"]
    },
    # ... more patterns
]

async def seed():
    global_mgr = await _get_global_memory_manager()
    for pattern in UNIVERSAL_PATTERNS:
        result = await global_mgr.remember(**pattern)
        print(f"Stored: {result['id']} - {pattern['content'][:50]}...")

asyncio.run(seed())
```

## Classification Heuristics

### What Makes a Memory Global?

**Content Analysis:**
- Keywords: "always", "never", "avoid", "best practice"
- Language mentions: "in Python", "in JavaScript", "in Rust"
- Universal concepts: "design pattern", "algorithm", "security"

**Tag Analysis:**
- Global tags: `best-practice`, `design-pattern`, `anti-pattern`, `security`, `architecture`

**File Association:**
- Has file path → **Local**
- No file path → **Could be Global** (if other signals match)

### Edge Cases

**Uncertain Classification → Defaults to Local:**
```
"Use async/await for better performance"
→ Local (safer default, prevents pollution)
```

**Override if needed:**
Manually store to global by removing file path and adding global tags.

## Monitoring & Debugging

### Check Classification

After storing a memory:
```json
{
  "id": 42,
  "scope": "global",
  "_also_stored_globally": 17,  // ID in global storage
  "content": "..."
}
```

- `scope: "local"` → Local only
- `scope: "global"` → Stored in both
- `scope: "local_only"` → Tried global but failed

### View Global Memories

```bash
# List global memories
recall --project-path "__global__" "security"

# Or set env var
export CLAUDE_MEMORY_PROJECT_ROOT="__global__"
recall "best practices"
```

### Troubleshooting

**Global memories not appearing?**
1. Check: `echo $CLAUDE_MEMORY_GLOBAL_ENABLED`
2. Verify global storage exists: `ls ~/.claude-memory/storage/`
3. Check logs for errors: Search for "global" in server logs

**Too many false positives?**
Adjust classification by adding project-specific language to keep memories local.

**Want read-only global?**
```bash
export CLAUDE_MEMORY_GLOBAL_WRITE_ENABLED=false
```

## Best Practices

### DO:
✅ Use global tags (`best-practice`, `security`) for universal patterns
✅ Add `.claude-memory/` to your `.gitignore`
✅ Store security guidelines globally
✅ Store language-specific patterns globally
✅ Review global memories periodically

### DON'T:
❌ Store API keys or secrets (they'll be in global!)
❌ Store project-specific decisions without file paths
❌ Manually edit database files
❌ Commit `.claude-memory/` to git
❌ Use global for debugging notes

## Advanced Usage

### Manual Promotion to Global

If a local memory should be global:

```python
# Future feature: promote_to_global tool
promote_to_global(memory_id=42)
→ Copies to global, archives local copy
```

### Cleanup

```bash
# Prune old global memories (manual)
# Global memories with worked=True and old age
python -m claude_memory.cli prune \
  --project-path "__global__" \
  --older-than-days 180 \
  --dry-run
```

## FAQs

**Q: Can I disable global memory for a project?**
A: Yes, create `.claude-memory/config.json` with `{"global_enabled": false}`

**Q: Where is global memory stored?**
A: Default: `~/.claude-memory/storage/`. Override with `CLAUDE_MEMORY_GLOBAL_PATH`

**Q: Does global memory sync across machines?**
A: No, it's local to your machine. Use a shared folder or git for team sync.

**Q: What if local and global have similar memories?**
A: Local always takes precedence. Global duplicates are automatically filtered.

**Q: Can I see which memories are global?**
A: Yes, look for `_from_global: true` in recall results.

**Q: How much storage does global memory use?**
A: SQLite database, typically < 50MB for thousands of memories.

## Migration Guide

### From Project-Only to Global

1. **Identify universal patterns** in your project memory
2. **Tag them with global markers**: `best-practice`, `security`, `design-pattern`
3. **Remove file paths** if they were added incorrectly
4. **Re-store** them - they'll now go to global

### From Shared Linked Projects

If you were using linked projects for pattern sharing:

```python
# Consolidate linked patterns to global
# 1. List patterns from linked projects
# 2. Store them with global tags
# 3. Unlink projects
```

## See Also

- [Multi-Repo Setup Guide](multi-repo-setup.md) - For project linking
- [README.md](../README.md) - Main documentation
- [Setup.md](../Setup.md) - Installation and configuration
