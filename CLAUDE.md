# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DevilMCP is an MCP (Model Context Protocol) server that provides long-term memory and context management for AI agents. It solves "AI amnesia" by persisting architectural decisions, tracking code change impacts, detecting cascade failures, and managing tasks across sessions.

## Commands

```bash
# Install (editable mode)
pip install -e .

# Install browser binaries (required for browser tools)
playwright install

# Run the MCP server
python -m devilmcp.server
# Or via console script:
devilmcp

# Run tests
pytest devilmcp/
pytest -v --asyncio-mode=auto  # For async tests
```

## Architecture

```
┌─────────────────────────────────────┐
│  FastMCP Server (server.py)         │  ← Entry point, exposes 50+ MCP tools
├─────────────────────────────────────┤
│  Feature Modules                    │
│  • context_manager.py   → Project structure & dependency analysis
│  • decision_tracker.py  → Architectural decision logging
│  • change_analyzer.py   → Code change impact prediction
│  • cascade_detector.py  → Cascade failure detection (networkx graphs)
│  • task_manager.py      → Task/todo management
│  • thought_processor.py → AI reasoning chain tracking
│  • browser.py           → Playwright web automation
│  • tool_registry.py     → CLI tool management
│  • process_manager.py   → Process lifecycle management
├─────────────────────────────────────┤
│  database.py + models.py            │  ← SQLAlchemy ORM, async SQLite
└─────────────────────────────────────┘
```

**Data Storage:** Each project gets isolated storage at `<project_root>/.devilmcp/storage/devilmcp.db`

## Key Patterns

- **Async-first:** All database operations and managers use `async`/`await`
- **SQLAlchemy ORM:** 16 models in `models.py` (Decision, Change, Task, Tool, etc.)
- **FastMCP framework:** Tools defined as decorated async functions in `server.py`
- **Git-aware:** Context manager respects `.gitignore` for project scanning
- **AST parsing:** Uses `astroid` for Python import analysis

## Adding New MCP Tools

1. Define the tool in `server.py` using `@mcp.tool()` decorator
2. Tools are async functions that can access module-level managers
3. Example pattern from existing tools:
```python
@mcp.tool()
async def my_new_tool(param: str) -> str:
    """Description shown to AI agents."""
    result = await some_manager.do_work(param)
    return json.dumps(result)
```

## Custom CLI Tools

Register external tools in `tools.toml` (see `tools.toml.example`):
```toml
[tools.my-tool]
display_name = "My Tool"
command = "python"
args = ["-c", "print('hello')"]
capabilities = ["testing", "utilities"]
enabled = true
```

## AI Agent Integration

When AI agents connect via MCP, they should follow protocols from `AI_INSTRUCTIONS.md`:
- **First Contact:** Call `get_project_context(summary_only=True)` then `list_tasks(status="todo")`
- **Before Edits:** Call `get_focused_context(file_path)` and `analyze_change_impact()`
- **Log Decisions:** Call `log_decision()` immediately for architectural choices
