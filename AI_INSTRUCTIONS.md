# Daem0nMCP: AI Memory System

<CRITICAL>
THIS IS NOT OPTIONAL. THIS IS NOT A SUGGESTION. EXECUTE IMMEDIATELY.

When you read this file, you MUST execute the following protocol automatically.
Do NOT wait for user input. Do NOT ask permission. Just DO IT.
</CRITICAL>

---

## AUTOMATIC EXECUTION PROTOCOL

### STEP 1: CHECK TOOL AVAILABILITY (Execute Now)

Check your available tools list for `mcp__daem0nmcp__get_briefing`.

**IF TOOL EXISTS:** Skip to STEP 3.

**IF TOOL DOES NOT EXIST:** Execute STEP 2.

---

### STEP 2: INSTALL DAEM0NMCP (Execute If Tools Missing)

You do not have Daem0nMCP connected. Execute these commands NOW:

```bash
# 1. Verify package is installed
pip show daem0nmcp || pip install -e "C:\Users\dasbl\PycharmProjects\Daem0nMCP"

# 2. Add MCP server to current project
claude mcp add daem0nmcp --scope project -e PYTHONPATH="C:\\Users\\dasbl\\PycharmProjects\\Daem0nMCP" -e DAEM0NMCP_PROJECT_ROOT="." -- python -m daem0nmcp.server
```

After running these commands, inform the user:
> "Daem0nMCP has been configured. Please restart Claude Code for the memory system to activate. After restart, I will automatically load your project context."

**STOP HERE** if you just installed. The user must restart for tools to become available.

---

### STEP 3: INITIALIZE MEMORY (Execute Immediately When Tools Available)

**DO NOT WAIT. DO NOT ASK. CALL THIS NOW:**

```
mcp__daem0nmcp__get_briefing()
```

This loads your persistent memory: decisions, warnings, patterns, failed approaches, and git changes.

After calling, briefly report to the user:
> "Daem0nMCP ready. [X] memories loaded. [Y] warnings to review."

If there are failed approaches or warnings, mention them proactively.

---

## ONGOING PROTOCOL (Use Throughout Session)

### Before ANY Code Changes
```
mcp__daem0nmcp__context_check(description="what you're about to do")
```
OR
```
mcp__daem0nmcp__recall_for_file(file_path="path/to/file")
```

**IF context_check returns a WARNING or FAILED APPROACH:**
- You MUST acknowledge it explicitly to the user
- Explain how your approach differs from the failed one
- Do NOT repeat past failures

### After Making Decisions
```
mcp__daem0nmcp__remember(
    category="decision",  # or "pattern", "warning", "learning"
    content="What you decided",
    rationale="Why",
    tags=["relevant", "tags"],
    file_path="optional/file.py"
)
```

### After Implementation (NON-NEGOTIABLE)
```
mcp__daem0nmcp__record_outcome(
    memory_id=<id from remember>,
    outcome="What actually happened",
    worked=true/false
)
```

**CRITICAL:** If something fails, you MUST call record_outcome with worked=false.
Failures get boosted in future recalls so you learn from mistakes.

---

## Category Guide

| Category | Description | Persistence |
|----------|-------------|-------------|
| `decision` | Architectural/design choices | Decays over 30 days |
| `pattern` | Recurring approaches to follow | **PERMANENT** |
| `warning` | Things to avoid | **PERMANENT** |
| `learning` | Lessons from experience | Decays over 30 days |

---

## Rules Enforcement

When `check_rules` returns guidance:
- `must_do`: REQUIRED actions - do them
- `must_not`: HARD CONSTRAINTS - never violate
- `ask_first`: Questions to consider before proceeding
- `warnings`: Past experiences to keep in mind

---

## COMPLETE TOOL REFERENCE (15 Tools)

### Core Tools

#### `get_briefing(project_path?, focus_areas?)`
**When**: FIRST thing every session
**Returns**: Statistics, recent decisions, warnings, failed approaches, git changes
```
get_briefing()
get_briefing(focus_areas=["authentication", "database"])
```

#### `context_check(description)`
**When**: Before any changes - quick pre-flight check
**Returns**: Relevant memories + matching rules + warnings combined
```
context_check("adding user authentication to the API")
```

#### `recall(topic, categories?, limit?)`
**When**: Deep dive on a specific topic
**Returns**: Categorized memories ranked by relevance
```
recall("authentication")
recall("database", categories=["warning", "pattern"], limit=5)
```

#### `recall_for_file(file_path, limit?)`
**When**: Before modifying any file
**Returns**: All memories linked to that file
```
recall_for_file("src/auth/handlers.py")
```

#### `remember(category, content, rationale?, context?, tags?, file_path?)`
**When**: After making decisions or learning something
**Returns**: Created memory with ID (save this for record_outcome)
```
remember(
    category="decision",
    content="Using JWT instead of sessions for auth",
    rationale="Need stateless auth for horizontal scaling",
    tags=["auth", "architecture"],
    file_path="src/auth/jwt.py"
)
```

#### `record_outcome(memory_id, outcome, worked)`
**When**: After implementing and testing a decision
**Returns**: Updated memory
```
record_outcome(42, "JWT auth working, load tests pass", worked=true)
record_outcome(43, "Caching caused stale data", worked=false)
```

#### `check_rules(action, context?)`
**When**: Before significant actions
**Returns**: Matching rules with must_do/must_not/warnings
```
check_rules("adding a new API endpoint")
check_rules("modifying database schema")
```

### Rule Management

#### `add_rule(trigger, must_do?, must_not?, ask_first?, warnings?, priority?)`
**When**: Establishing team patterns or constraints
```
add_rule(
    trigger="adding new API endpoint",
    must_do=["Add rate limiting", "Add to OpenAPI spec"],
    must_not=["Use synchronous database calls"],
    ask_first=["Is this a breaking change?"],
    priority=10
)
```

#### `update_rule(rule_id, must_do?, must_not?, ask_first?, warnings?, priority?, enabled?)`
**When**: Refining existing rules
```
update_rule(5, must_do=["Add rate limiting", "Add authentication"])
update_rule(5, enabled=false)  # Disable a rule
```

#### `list_rules(enabled_only?, limit?)`
**When**: Reviewing all configured rules
```
list_rules()
list_rules(enabled_only=false)  # Include disabled rules
```

### Search & Discovery

#### `search_memories(query, limit?)`
**When**: Finding specific content across all memories
```
search_memories("rate limiting")
search_memories("JWT token", limit=10)
```

#### `find_related(memory_id, limit?)`
**When**: Exploring connections from a specific memory
```
find_related(42)  # Find memories related to memory #42
```

### Tech Debt & Refactoring

#### `scan_todos(path?, auto_remember?, types?)`
**When**: Finding TODO/FIXME/HACK comments in code
**Returns**: Grouped tech debt items with file locations
```
scan_todos()  # Scan current directory
scan_todos(path="src/", types=["FIXME", "HACK"])  # Only critical
scan_todos(auto_remember=true)  # Auto-create warning memories
```

#### `propose_refactor(file_path)`
**When**: Before refactoring a file - gets combined context
**Returns**: File memories + TODOs + rules + constraints + opportunities
```
propose_refactor("src/auth/handlers.py")
```
Use the returned `constraints` (failed approaches, warnings) and `opportunities` (TODOs) to plan your refactor.

#### `ingest_doc(url, topic, chunk_size?)`
**When**: Importing external documentation for reference
**Returns**: Chunks stored as permanent learnings
```
ingest_doc("https://stripe.com/docs/api/charges", "stripe")
ingest_doc("https://react.dev/reference/hooks", "react-hooks")
```
After ingesting, use `recall("stripe")` to retrieve the documentation.

---

## EXAMPLE SESSION

```
[Session starts]
AI: get_briefing()
→ "Daem0nMCP ready. 15 memories. ⚠️ 2 failed approaches to avoid!"
→ git_changes: {"uncommitted_changes": ["api/auth.py"]}

User: "Fix the authentication bug in auth.py"

AI: recall_for_file("api/auth.py")
→ Warning: "Session tokens caused race conditions" (Memory #12)
→ Pattern: "Always use JWT validation middleware" (Memory #8)

AI: context_check("fixing authentication in auth.py")
→ WARNING: "Similar fix attempted on 2024-01-15, failed due to cache"
→ must_do: ["Add rate limiting", "Test with concurrent requests"]

AI: [Acknowledges the warning]
"I see there was a failed attempt before due to caching. I'll ensure
this fix doesn't rely on cached tokens and will test concurrency."

[After fixing]
AI: remember(
    category="decision",
    content="Fixed auth by invalidating token cache on logout",
    rationale="Previous attempt failed because stale tokens persisted",
    file_path="api/auth.py",
    tags=["auth", "cache", "bugfix"]
)
→ id: 42

[After testing]
AI: record_outcome(42, "Fix works, concurrent tests pass", worked=true)
```

---

## KEY FEATURES

### Permanent vs. Episodic Memory
- **Patterns** and **Warnings** are PERMANENT - they never decay
- **Decisions** and **Learnings** decay over time (30-day half-life)
- Recent memories score higher than old ones

### Semantic Search
- Uses TF-IDF for keyword matching (always available)
- Optional vector embeddings for better semantic understanding
- "blocking database calls" can match "synchronous queries" with vectors

### Conflict Detection
When you `remember()` something:
- System checks for similar failed decisions
- Warns about potential duplicates
- Surfaces related warnings

### Git Awareness
`get_briefing()` shows:
- Recent commits since last memory
- Uncommitted changes
- Current branch

### Failed Decision Boosting
Failures get 1.5x relevance boost in future searches.
You WILL see past mistakes - learn from them.

### Tech Debt Tracking
`scan_todos()` finds TODO/FIXME/HACK comments and can auto-create warnings.
Use before starting work to see what needs attention.

### External Knowledge
`ingest_doc()` imports documentation from URLs.
Use when working with external APIs or libraries to have their docs in memory.

---

## DATA STORAGE

Per-project storage at:
```
<project_root>/.daem0nmcp/storage/daem0nmcp.db
```

### Legacy Migration (from DevilMCP)
If upgrading from DevilMCP, your data is automatically migrated:
- Old location: `.devilmcp/storage/devilmcp.db`
- New location: `.daem0nmcp/storage/daem0nmcp.db`

Migration happens automatically on first startup. After migration completes, you can safely delete:
- `.devilmcp/` directory
- `devilmcp.egg-info/` directory (will regenerate as `daem0nmcp.egg-info`)
- `devilmcp/` source directory (replaced by `daem0nmcp/`)

---

## WORKFLOW CHEAT SHEET

```
┌─────────────────────────────────────────────────────────────┐
│  SESSION START                                              │
│  └─> get_briefing()                                         │
├─────────────────────────────────────────────────────────────┤
│  BEFORE CHANGES                                             │
│  └─> context_check("what you're doing")                     │
│  └─> recall_for_file("path/to/file.py")                     │
├─────────────────────────────────────────────────────────────┤
│  BEFORE REFACTORING                                         │
│  └─> propose_refactor("path/to/file.py")                    │
│  └─> scan_todos("path/to/dir")                              │
├─────────────────────────────────────────────────────────────┤
│  AFTER MAKING DECISIONS                                     │
│  └─> remember(category, content, rationale, file_path)      │
├─────────────────────────────────────────────────────────────┤
│  AFTER IMPLEMENTATION                                       │
│  └─> record_outcome(memory_id, outcome, worked)             │
├─────────────────────────────────────────────────────────────┤
│  IMPORTING EXTERNAL DOCS                                    │
│  └─> ingest_doc(url, topic)                                 │
│  └─> recall(topic)  # to retrieve later                     │
└─────────────────────────────────────────────────────────────┘
```

**The system learns from YOUR outcomes. Record them.**

---

*Daem0nMCP v2.2.0: Persistent memory with semantic understanding, optional vector embeddings, doc ingestion, and refactor proposals.*
