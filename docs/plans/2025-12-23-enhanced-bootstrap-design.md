# Enhanced Bootstrap Design

**Date:** 2025-12-23
**Status:** Approved
**Author:** Brainstorming session

## Problem Statement

The current bootstrap creates only 2 memories on first run (CLAUDE.md + git history). Users want richer initial context automatically to enable:
- Faster AI session onboarding
- Decision continuity (understanding existing patterns)
- Warning prevention (knowing pitfalls upfront)

## Design Decisions

| Aspect | Decision |
|--------|----------|
| Goal | Comprehensive awareness (onboarding, continuity, warnings) |
| Depth | Moderate (5-10 seconds) |
| Structure | Categorized memories by type |
| Sources | Balanced mix (docs, structure, issues) |
| Missing files | Graceful fallback (use what's available) |

## Memory Categories

| Category | Memory Type | Purpose |
|----------|-------------|---------|
| `pattern` | Project Identity | Tech stack, language, framework from manifests |
| `pattern` | Architecture Overview | Directory structure, module organization |
| `pattern` | Conventions | Code style, naming patterns, from docs/config |
| `pattern` | Project Instructions | CLAUDE.md content (existing) |
| `learning` | Git Evolution | Recent commit patterns (existing, enhanced) |
| `warning` | Known Issues | TODO/FIXME/HACK scan results |
| `learning` | Entry Points | Main files, API routes, key exports |

## Sources & Extraction

### Documentation Sources

| File | What's Extracted | Memory |
|------|------------------|--------|
| `CLAUDE.md` | Full content (first 3000 chars) | Project Instructions |
| `README.md` | First 2000 chars (overview, install, usage) | Architecture Overview |
| `CONTRIBUTING.md` | Code style / PR guidelines sections | Conventions |
| `AGENTS.md` | Agent-specific instructions | Project Instructions (appended) |

### Manifest Sources (first one found wins)

| File | What's Extracted | Memory |
|------|------------------|--------|
| `package.json` | name, description, scripts, key dependencies | Project Identity |
| `pyproject.toml` | project name, description, dependencies | Project Identity |
| `Cargo.toml` | package name, description, dependencies | Project Identity |
| `go.mod` | module name, go version, key requires | Project Identity |
| `*.csproj` / `*.sln` | project type, target framework | Project Identity |

### Structure Sources

| Source | What's Extracted | Memory |
|--------|------------------|--------|
| Directory tree | Top 2 levels, excluding noise dirs | Architecture Overview |
| Entry points | main.py, index.ts, app.py, etc. | Entry Points |
| Config files | .eslintrc, prettier, ruff.toml | Conventions |

### Issue Sources

| Source | What's Extracted | Memory |
|--------|------------------|--------|
| `scan_todos()` | TODO/FIXME/HACK comments (limit 20) | Known Issues |

## Implementation Approach

```python
async def _bootstrap_project_context(ctx: ProjectContext) -> Dict[str, Any]:
    results = {"bootstrapped": True, "memories_created": 0, "sources": {}}

    # Run extraction functions (each returns content or None)
    project_identity = _extract_project_identity(ctx.project_path)
    architecture = _extract_architecture(ctx.project_path)
    conventions = _extract_conventions(ctx.project_path)
    instructions = _extract_project_instructions(ctx.project_path)
    git_evolution = _get_git_history_summary(ctx.project_path)
    known_issues = await _scan_todos_for_bootstrap(ctx)
    entry_points = _extract_entry_points(ctx.project_path)

    # Create memories for each non-None result
    for name, content, category, tags in [
        ("project_identity", project_identity, "pattern", ["bootstrap", "tech-stack"]),
        ("architecture", architecture, "pattern", ["bootstrap", "architecture"]),
        # ... etc
    ]:
        if content:
            await ctx.memory_manager.remember(...)
            results["memories_created"] += 1
            results["sources"][name] = "ingested"
```

### Key Implementation Details

- Extraction functions are synchronous (just file reads)
- Each extractor is isolated (failure in one doesn't affect others)
- Content limits enforced (2000-3000 chars per memory)
- Existing `scan_todos` reused with limit parameter
- Tags enable targeted recall (`recall(topic, tags=["bootstrap"])`)

## Error Handling

### Graceful Degradation

```python
def _extract_project_identity(project_path: str) -> Optional[str]:
    """Try manifests in priority order, return first found."""
    manifests = [
        ("package.json", _parse_package_json),
        ("pyproject.toml", _parse_pyproject),
        ("Cargo.toml", _parse_cargo),
        ("go.mod", _parse_go_mod),
    ]
    for filename, parser in manifests:
        path = Path(project_path) / filename
        if path.exists():
            try:
                return parser(path.read_text(encoding='utf-8', errors='ignore'))
            except Exception as e:
                logger.debug(f"Failed to parse {filename}: {e}")
                continue
    return None
```

### Edge Cases

| Case | Behavior |
|------|----------|
| Empty project (no files) | Only git history if available |
| Binary/non-text files | Skipped via `errors='ignore'` |
| Huge README (>50KB) | Truncated to first 2000 chars |
| No git repo | Git-related memories skipped |
| Encoding issues | UTF-8 with ignore fallback |
| Permission errors | Logged, memory skipped |
| Timeout on large dirs | Scan limited to 2 levels |

### Excluded Directories

```python
EXCLUDED_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv',
    'dist', 'build', '.next', 'target', '.idea', '.vscode'
}
```

## Briefing Output Changes

### Current Format
```python
"bootstrap": {
    "bootstrapped": True,
    "claude_md": "ingested",
    "git_history": "ingested",
    "memories_created": 2
}
```

### Enhanced Format
```python
"bootstrap": {
    "bootstrapped": True,
    "memories_created": 6,
    "sources": {
        "project_identity": "ingested",
        "architecture": "ingested",
        "conventions": "skipped",
        "project_instructions": "ingested",
        "git_evolution": "ingested",
        "known_issues": "ingested",
        "entry_points": "ingested"
    }
}
```

### Message Enhancement

```
Current:  "Daem0nMCP ready. 2 memories stored. [BOOTSTRAP] First run - ingested: CLAUDE.md, git history"

Enhanced: "Daem0nMCP ready. 6 memories stored. [BOOTSTRAP] First run - ingested:
           project identity (Python/FastAPI), architecture, instructions,
           git history, 12 known issues, 3 entry points"
```

## Files to Modify

1. `daem0nmcp/server.py` - Main bootstrap logic and extractors
2. `tests/test_bootstrap.py` - New test file for bootstrap functionality

## Implementation Tasks

1. Add extractor functions for each source type
2. Update `_bootstrap_project_context()` to call all extractors
3. Update `get_briefing()` response format
4. Add tests for each extractor
5. Add integration test for full bootstrap flow
