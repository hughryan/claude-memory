# Tool Executor Architecture Refactor

**Date:** 2025-12-04
**Status:** Approved
**Scope:** Replace brittle ProcessManager with robust ToolExecutor abstraction

---

## Problem Statement

The current `process_manager.py` uses "screen scraping" to detect command completion:

```python
# Current approach - brittle
if decoded_line.endswith(pattern):  # e.g., ">>>"
    break
```

**Failure modes:**
- Prompt changes break detection (e.g., `>` → `➜`)
- Prompts appearing in output cause premature termination
- All tools forced into long-running sessions (even stateless ones)
- Hanging pipes when detection fails

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | ToolExecutor interface with implementations | Enables native SDK swap-ins without API changes |
| Stateless vs Stateful | Infer from `prompt_patterns` in config | Backwards compatible, zero migration |
| Output detection | Sentinel tokens + timeout fallback | Reliable for known shells, graceful degradation for unknown |
| Native SDKs | Build interface now, implement incrementally | Clean abstraction ready for gitpython, etc. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ToolRegistry                         │
│  - Routes requests to appropriate executor              │
│  - Caches executors per tool                            │
│  - Native executors take priority when available        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────────────┐       ┌─────────────────┐        │
│   │  NativeExecutor │       │SubprocessExecutor│        │
│   │  (gitpython,    │       │                 │        │
│   │   future SDKs)  │       │ ┌─────────────┐ │        │
│   └─────────────────┘       │ │  Stateless  │ │        │
│                             │ │ (run once)  │ │        │
│                             │ ├─────────────┤ │        │
│                             │ │  Stateful   │ │        │
│                             │ │ (sentinel)  │ │        │
│                             │ └─────────────┘ │        │
│                             └─────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

---

## Interface Definition

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: Optional[str] = None
    return_code: Optional[int] = None
    timed_out: bool = False
    executor_type: str = "subprocess"

class ToolExecutor(ABC):
    """Base interface for all tool execution strategies."""

    @abstractmethod
    async def execute(
        self,
        command: str,
        args: list[str],
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Execute a command and return the result."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Release any resources held by the executor."""
        pass
```

---

## SubprocessExecutor: Stateless Mode

For tools **without** `prompt_patterns` in config. Covers ~90% of CLI tools.

```python
async def _execute_stateless(
    self,
    command: str,
    args: list[str],
    env: Optional[Dict[str, str]] = None
) -> ExecutionResult:
    """Run once, capture output, exit. No prompt detection needed."""
    proc = await asyncio.create_subprocess_exec(
        command, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(),
        timeout=self.config.command_timeout / 1000
    )
    return ExecutionResult(
        success=(proc.returncode == 0),
        output=stdout.decode(errors='replace'),
        error=stderr.decode(errors='replace') if stderr else None,
        return_code=proc.returncode,
        executor_type="subprocess-stateless"
    )
```

**Key insight:** `proc.communicate()` waits for natural process exit. No prompt matching needed.

---

## SubprocessExecutor: Stateful Mode

For tools **with** `prompt_patterns` in config (REPLs, database shells).

```python
async def _execute_stateful(
    self,
    command: str,
    args: list[str],
    env: Optional[Dict[str, str]] = None
) -> ExecutionResult:
    """Maintain session, use sentinel tokens to detect end of output."""

    if self._process is None:
        await self._spawn_session(args, env)

    sentinel = f"__DEVILMCP_END_{uuid.uuid4().hex[:8]}__"
    sentinel_cmd = self._build_sentinel_command(command, sentinel)

    self._process.stdin.write(sentinel_cmd.encode())
    await self._process.stdin.drain()

    output_lines = []
    try:
        while True:
            line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=self.config.command_timeout / 1000
            )
            if not line:  # EOF
                break
            decoded = line.decode(errors='replace').rstrip()
            if sentinel in decoded:
                break  # Found our marker
            output_lines.append(decoded)

    except asyncio.TimeoutError:
        return ExecutionResult(
            success=False,
            output="\n".join(output_lines),
            error="Timeout waiting for command completion",
            timed_out=True,
            executor_type="subprocess-stateful"
        )

    return ExecutionResult(
        success=True,
        output="\n".join(output_lines),
        executor_type="subprocess-stateful"
    )

def _build_sentinel_command(self, command: str, sentinel: str) -> str:
    """Inject sentinel echo after the command."""
    if "python" in self.config.command.lower():
        return f"{command}\nprint('{sentinel}')\n"
    elif "node" in self.config.command.lower():
        return f"{command}\nconsole.log('{sentinel}')\n"
    else:
        return f"{command}\necho {sentinel}\n"
```

**Key insight:** Sentinel is a UUID - cannot appear in real output. Timeout is fallback, not primary.

---

## NativeExecutor Pattern

For tools with Python SDK equivalents. Direct API calls, no subprocess.

```python
class NativeExecutor(ToolExecutor):
    """Base class for native Python SDK integrations."""

    @abstractmethod
    def get_supported_commands(self) -> list[str]:
        """Return list of commands this executor handles."""
        pass


class GitNativeExecutor(NativeExecutor):
    """Git operations via gitpython."""

    def __init__(self, repo_path: str):
        self.repo = git.Repo(repo_path)

    def get_supported_commands(self) -> list[str]:
        return ["status", "diff", "log", "add", "commit", "branch"]

    async def execute(
        self,
        command: str,
        args: list[str],
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        try:
            if command == "status":
                output = self.repo.git.status()
            elif command == "diff":
                output = self.repo.git.diff(*args)
            elif command == "log":
                output = self.repo.git.log(*args)
            # ... etc
            return ExecutionResult(
                success=True,
                output=output,
                executor_type="native-git"
            )
        except git.GitCommandError as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                executor_type="native-git"
            )

    async def cleanup(self) -> None:
        self.repo.close()
```

---

## ToolRegistry Routing

```python
class ToolRegistry:
    """Routes tool requests to the appropriate executor."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._executors: Dict[str, ToolExecutor] = {}
        self._native_registry: Dict[str, type[NativeExecutor]] = {
            "git": GitNativeExecutor,
        }

    async def get_executor(self, tool_name: str) -> ToolExecutor:
        if tool_name in self._executors:
            return self._executors[tool_name]

        # Native executor takes priority
        if tool_name in self._native_registry:
            executor = self._native_registry[tool_name]()
            self._executors[tool_name] = executor
            return executor

        # Fallback to subprocess
        tool_config = await self._load_tool_config(tool_name)
        executor = SubprocessExecutor(tool_config)
        self._executors[tool_name] = executor
        return executor

    async def execute_tool(
        self,
        tool_name: str,
        command: str,
        args: list[str] = []
    ) -> ExecutionResult:
        """Main entry point."""
        executor = await self.get_executor(tool_name)
        return await executor.execute(command, args)
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Timeout (stateless) | Kill process, return error |
| Timeout (stateful) | Return partial output, keep process alive |
| Broken pipe | Clean up dead process, next call spawns fresh |
| Process crash | Detect via EOF, reset state, report error |
| Unknown tool | Fallback to subprocess with generic `echo` sentinel |

```python
async def _cleanup_dead_process(self) -> None:
    """Reset state when process dies."""
    if self._process:
        try:
            self._process.kill()
            await self._process.wait()
        except ProcessLookupError:
            pass
    self._process = None
    self._session_id = None
```

---

## Migration Plan

1. **Create new files** - Don't modify `process_manager.py` yet
   - `devilmcp/executor.py` - Interface + ExecutionResult
   - `devilmcp/subprocess_executor.py` - Stateless + stateful modes
   - `devilmcp/native_executors/git.py` - First native impl

2. **Update ToolRegistry** - Route through new executors

3. **Update server.py** - Use new `execute_tool()` API

4. **Deprecate ProcessManager** - Keep for one release, then remove

5. **Remove Playwright** - Separate cleanup task

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `devilmcp/executor.py` | CREATE - Interface + result dataclass |
| `devilmcp/subprocess_executor.py` | CREATE - Stateless + stateful impl |
| `devilmcp/native_executors/__init__.py` | CREATE - Package |
| `devilmcp/native_executors/git.py` | CREATE - GitNativeExecutor |
| `devilmcp/tool_registry.py` | MODIFY - Add routing logic |
| `devilmcp/server.py` | MODIFY - Use new API |
| `devilmcp/process_manager.py` | DEPRECATE - Mark for removal |
| `devilmcp/browser.py` | DELETE - Remove Playwright |

---

## Success Criteria

- [ ] Stateless tools (git, linters) complete without hanging
- [ ] Stateful tools (Python REPL) maintain session correctly
- [ ] Sentinel tokens detect command completion reliably
- [ ] Timeout fallback prevents infinite hangs
- [ ] Existing `tools.toml` configs work without changes
- [ ] Native git executor passes same tests as subprocess
