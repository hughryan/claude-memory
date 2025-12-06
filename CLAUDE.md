# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

DevilMCP is a focused MCP server providing **AI memory and decision trees** with **semantic understanding**. It gives AI agents:
- Persistent memory across sessions (decisions, patterns, warnings, learnings)
- TF-IDF based semantic search (not just keywords)
- Time-weighted recall (recent memories matter more)
- Conflict detection (warns about contradicting decisions)
- Rule-based decision trees for consistent behavior
- Outcome tracking for learning from success/failure

## Commands

```bash
# Install
pip install -e .

# Run the MCP server
python -m devilmcp.server

# Run tests
pytest tests/ -v --asyncio-mode=auto
```

## Architecture

```
devilmcp/
├── server.py      # MCP server, 11 tools (FastMCP)
├── memory.py      # MemoryManager - semantic store/recall with decay
├── rules.py       # RulesEngine - TF-IDF matched decision trees
├── similarity.py  # TF-IDF index, cosine similarity, conflict detection
├── database.py    # DatabaseManager - async SQLite
├── models.py      # SQLAlchemy models (2 tables)
└── config.py      # Pydantic settings
```

**Data Storage:** `<project_root>/.devilmcp/storage/devilmcp.db`

## Database Schema (2 tables)

**memories**: Stores decisions, patterns, warnings, learnings
- category, content, rationale, context, tags, keywords
- outcome tracking (outcome, worked)
- TF-IDF indexed for semantic search

**rules**: Decision tree nodes
- trigger, trigger_keywords (TF-IDF indexed)
- must_do, must_not, ask_first, warnings
- priority, enabled

## Key Patterns

- **Async-first**: All database operations use async/await
- **TF-IDF similarity**: Content is indexed for semantic matching (not just keywords)
- **Memory decay**: Recent memories weighted higher than old ones
- **Conflict detection**: New memories checked against existing for contradictions
- **Failed decision boosting**: Failed outcomes are highlighted in recalls

## MCP Tools (11 total)

Core:
1. `remember` - Store a memory with conflict detection
2. `recall` - Semantic retrieval with decay weighting
3. `add_rule` - Create decision tree node
4. `check_rules` - Semantic matching against rules
5. `record_outcome` - Track if decision worked (failures get boosted)
6. `get_briefing` - Smart session start with focus areas

Utility:
7. `search_memories` - Semantic search across all memories
8. `list_rules` - Show all rules
9. `update_rule` - Modify existing rule
10. `find_related` - Discover connected memories
11. `context_check` - Quick pre-flight check (recall + rules combined)

## Adding New Tools

```python
@mcp.tool()
async def my_tool(param: str) -> Dict[str, Any]:
    """Tool description shown to AI agents."""
    await db_manager.init_db()
    # ... implementation
    return {"result": "..."}
```

## AI Agent Protocol

1. **Session Start**: Call `get_briefing(focus_areas=["topic1", "topic2"])`
2. **Before Changes**: Call `context_check(description)` for quick guidance
3. **Detailed Lookup**: Call `recall(topic)` and `check_rules(action)` separately
4. **Making Decisions**: Call `remember(category, content, rationale)`
5. **After Implementation**: Call `record_outcome(memory_id, outcome, worked)`

## Testing

```bash
pytest tests/ -v --asyncio-mode=auto
```

53 tests covering:
- Memory CRUD and semantic recall
- TF-IDF indexing and similarity
- Memory decay calculations
- Conflict detection
- Rule matching and priority
- All edge cases
