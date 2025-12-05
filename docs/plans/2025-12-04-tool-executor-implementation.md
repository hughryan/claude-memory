# ToolExecutor Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace brittle ProcessManager with robust ToolExecutor abstraction supporting stateless CLI tools, stateful REPLs with sentinel tokens, and native SDK integrations.

**Architecture:** ToolExecutor interface with SubprocessExecutor (stateless/stateful modes) and NativeExecutor implementations. ToolRegistry routes requests to appropriate executor. Infer execution mode from `prompt_patterns` config presence.

**Tech Stack:** Python 3.8+, asyncio, SQLAlchemy, gitpython (for native git)

---

## Task 1: Create ExecutionResult and ToolExecutor Interface

**Files:**
- Create: `devilmcp/executor.py`
- Test: `tests/test_executor.py`

**Step 1: Create test file with interface contract tests**

```python
# tests/test_executor.py
import pytest
from devilmcp.executor import ExecutionResult, ToolExecutor

def test_execution_result_success():
    result = ExecutionResult(success=True, output="hello world")
    assert result.success is True
    assert result.output == "hello world"
    assert result.error is None
    assert result.return_code is None
    assert result.timed_out is False
    assert result.executor_type == "subprocess"

def test_execution_result_failure():
    result = ExecutionResult(
        success=False,
        output="",
        error="Command not found",
        return_code=127,
        timed_out=False,
        executor_type="subprocess-stateless"
    )
    assert result.success is False
    assert result.return_code == 127
    assert result.error == "Command not found"

def test_execution_result_timeout():
    result = ExecutionResult(
        success=False,
        output="partial output",
        error="Timeout",
        timed_out=True
    )
    assert result.timed_out is True
    assert result.output == "partial output"

def test_tool_executor_is_abstract():
    with pytest.raises(TypeError):
        ToolExecutor()  # Cannot instantiate abstract class
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_executor.py -v`
Expected: FAIL with "No module named 'devilmcp.executor'"

**Step 3: Create executor.py with interface**

```python
# devilmcp/executor.py
"""
Tool Executor Interface
Defines the contract for all tool execution strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class ExecutionResult:
    """Result of executing a tool command."""
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
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Execute a command and return the result."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Release any resources held by the executor."""
        pass
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_executor.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add devilmcp/executor.py tests/test_executor.py
git commit -m "feat: add ToolExecutor interface and ExecutionResult dataclass"
```

---

## Task 2: Create SubprocessExecutor with Stateless Mode

**Files:**
- Create: `devilmcp/subprocess_executor.py`
- Test: `tests/test_subprocess_executor.py`

**Step 1: Create test for stateless execution**

```python
# tests/test_subprocess_executor.py
import pytest
from unittest.mock import MagicMock
from devilmcp.subprocess_executor import SubprocessExecutor
from devilmcp.tool_registry import ToolConfig, ToolCapability

@pytest.fixture
def stateless_config():
    """Config without prompt_patterns = stateless mode."""
    return ToolConfig(
        name="echo-test",
        display_name="Echo Test",
        command="echo",
        args=[],
        capabilities=[],
        enabled=True,
        config={},
        prompt_patterns=[],  # Empty = stateless
        init_timeout=5000,
        command_timeout=10000,
        max_context_size=None,
        supports_streaming=False
    )

@pytest.mark.asyncio
async def test_stateless_executor_echo(stateless_config):
    executor = SubprocessExecutor(stateless_config)
    result = await executor.execute("echo", ["hello", "world"])

    assert result.success is True
    assert "hello world" in result.output
    assert result.executor_type == "subprocess-stateless"
    assert result.timed_out is False

    await executor.cleanup()

@pytest.mark.asyncio
async def test_stateless_executor_returns_exit_code(stateless_config):
    executor = SubprocessExecutor(stateless_config)
    # Run a command that fails
    result = await executor.execute("python", ["-c", "exit(42)"])

    assert result.success is False
    assert result.return_code == 42

    await executor.cleanup()

@pytest.mark.asyncio
async def test_stateless_executor_captures_stderr(stateless_config):
    executor = SubprocessExecutor(stateless_config)
    result = await executor.execute("python", ["-c", "import sys; sys.stderr.write('error msg')"])

    assert "error msg" in result.error or "error msg" in result.output

    await executor.cleanup()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_subprocess_executor.py -v`
Expected: FAIL with "No module named 'devilmcp.subprocess_executor'"

**Step 3: Create SubprocessExecutor with stateless mode**

```python
# devilmcp/subprocess_executor.py
"""
Subprocess Executor
Executes CLI tools via subprocess with stateless and stateful modes.
"""

import asyncio
import logging
import uuid
from typing import Optional, Dict, List

from .executor import ToolExecutor, ExecutionResult
from .tool_registry import ToolConfig

logger = logging.getLogger(__name__)


class SubprocessExecutor(ToolExecutor):
    """Executes CLI tools via subprocess."""

    def __init__(self, tool_config: ToolConfig):
        self.config = tool_config
        self._is_stateful = bool(tool_config.prompt_patterns)
        self._process: Optional[asyncio.subprocess.Process] = None
        self._session_id: Optional[str] = None

    async def execute(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Execute command using appropriate mode."""
        if self._is_stateful:
            return await self._execute_stateful(command, args, env)
        else:
            return await self._execute_stateless(command, args, env)

    async def _execute_stateless(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Run once, capture output, exit. No prompt detection needed."""
        timeout_seconds = self.config.command_timeout / 1000

        try:
            proc = await asyncio.create_subprocess_exec(
                command, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds
            )

            return ExecutionResult(
                success=(proc.returncode == 0),
                output=stdout.decode(errors='replace').strip(),
                error=stderr.decode(errors='replace').strip() if stderr else None,
                return_code=proc.returncode,
                timed_out=False,
                executor_type="subprocess-stateless"
            )

        except asyncio.TimeoutError:
            if proc:
                proc.kill()
                await proc.wait()
            return ExecutionResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout_seconds}s",
                timed_out=True,
                executor_type="subprocess-stateless"
            )

        except Exception as e:
            logger.error(f"Stateless execution failed: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                executor_type="subprocess-stateless"
            )

    async def _execute_stateful(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Placeholder for stateful mode - implemented in Task 3."""
        raise NotImplementedError("Stateful mode coming in Task 3")

    async def cleanup(self) -> None:
        """Clean up any running processes."""
        if self._process and self._process.returncode is None:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except ProcessLookupError:
                pass  # Already dead
        self._process = None
        self._session_id = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_subprocess_executor.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add devilmcp/subprocess_executor.py tests/test_subprocess_executor.py
git commit -m "feat: add SubprocessExecutor with stateless mode"
```

---

## Task 3: Add Stateful Mode with Sentinel Tokens

**Files:**
- Modify: `devilmcp/subprocess_executor.py`
- Test: `tests/test_subprocess_executor.py` (add tests)

**Step 1: Add tests for stateful execution**

Add to `tests/test_subprocess_executor.py`:

```python
@pytest.fixture
def stateful_config():
    """Config with prompt_patterns = stateful mode."""
    return ToolConfig(
        name="python-repl",
        display_name="Python REPL",
        command="python",
        args=["-i"],
        capabilities=[],
        enabled=True,
        config={},
        prompt_patterns=[">>> "],  # Has patterns = stateful
        init_timeout=5000,
        command_timeout=10000,
        max_context_size=None,
        supports_streaming=False
    )

@pytest.mark.asyncio
async def test_stateful_executor_python_repl(stateful_config):
    executor = SubprocessExecutor(stateful_config)

    # First command
    result = await executor.execute("print('hello')", [])
    assert "hello" in result.output
    assert result.executor_type == "subprocess-stateful"

    # Second command in same session
    result2 = await executor.execute("print('world')", [])
    assert "world" in result2.output

    await executor.cleanup()

@pytest.mark.asyncio
async def test_stateful_executor_maintains_state(stateful_config):
    executor = SubprocessExecutor(stateful_config)

    # Set a variable
    await executor.execute("x = 42", [])

    # Read it back
    result = await executor.execute("print(x)", [])
    assert "42" in result.output

    await executor.cleanup()

@pytest.mark.asyncio
async def test_stateful_executor_sentinel_not_in_output(stateful_config):
    executor = SubprocessExecutor(stateful_config)

    result = await executor.execute("print('test')", [])

    # Sentinel should be stripped from output
    assert "__DEVILMCP_END_" not in result.output

    await executor.cleanup()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_subprocess_executor.py::test_stateful_executor_python_repl -v`
Expected: FAIL with "NotImplementedError: Stateful mode coming in Task 3"

**Step 3: Implement stateful mode with sentinel tokens**

Replace the `_execute_stateful` method in `devilmcp/subprocess_executor.py`:

```python
async def _execute_stateful(
    self,
    command: str,
    args: List[str],
    env: Optional[Dict[str, str]] = None
) -> ExecutionResult:
    """Maintain session, use sentinel tokens to detect end of output."""

    # Spawn process if not already running
    if self._process is None or self._process.returncode is not None:
        await self._spawn_session(env)

    sentinel = f"__DEVILMCP_END_{uuid.uuid4().hex[:8]}__"
    sentinel_cmd = self._build_sentinel_command(command, sentinel)

    timeout_seconds = self.config.command_timeout / 1000

    try:
        # Send command + sentinel echo
        self._process.stdin.write(sentinel_cmd.encode())
        await self._process.stdin.drain()

        # Read until sentinel appears
        output_lines = []
        while True:
            line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=timeout_seconds
            )
            if not line:  # EOF - process died
                break
            decoded = line.decode(errors='replace').rstrip()
            if sentinel in decoded:
                break  # Found our marker - done
            # Skip echo of the command itself and empty prompts
            if decoded and not decoded.startswith(">>>") and decoded != command:
                output_lines.append(decoded)

        return ExecutionResult(
            success=True,
            output="\n".join(output_lines),
            executor_type="subprocess-stateful"
        )

    except asyncio.TimeoutError:
        logger.warning(f"Stateful command timed out: {command[:50]}")
        return ExecutionResult(
            success=False,
            output="\n".join(output_lines) if 'output_lines' in locals() else "",
            error=f"Timeout after {timeout_seconds}s",
            timed_out=True,
            executor_type="subprocess-stateful"
        )

    except BrokenPipeError:
        await self._cleanup_dead_process()
        return ExecutionResult(
            success=False,
            output="",
            error="Process terminated unexpectedly",
            executor_type="subprocess-stateful"
        )

async def _spawn_session(self, env: Optional[Dict[str, str]] = None) -> None:
    """Spawn a new interactive process session."""
    self._session_id = str(uuid.uuid4())

    full_command = [self.config.command] + self.config.args

    self._process = await asyncio.create_subprocess_exec(
        *full_command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
        env=env
    )

    # Wait for initial prompt
    init_timeout = self.config.init_timeout / 1000
    try:
        await asyncio.wait_for(
            self._wait_for_prompt(),
            timeout=init_timeout
        )
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for initial prompt, proceeding anyway")

async def _wait_for_prompt(self) -> None:
    """Wait for a prompt pattern to appear."""
    while True:
        line = await self._process.stdout.readline()
        if not line:
            break
        decoded = line.decode(errors='replace')
        for pattern in self.config.prompt_patterns:
            if pattern in decoded:
                return

def _build_sentinel_command(self, command: str, sentinel: str) -> str:
    """Inject sentinel echo after the command."""
    cmd_lower = self.config.command.lower()

    if "python" in cmd_lower:
        return f"{command}\nprint('{sentinel}')\n"
    elif "node" in cmd_lower:
        return f"{command}\nconsole.log('{sentinel}')\n"
    else:
        # Generic shell
        return f"{command}\necho {sentinel}\n"

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

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_subprocess_executor.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add devilmcp/subprocess_executor.py tests/test_subprocess_executor.py
git commit -m "feat: add stateful mode with sentinel tokens to SubprocessExecutor"
```

---

## Task 4: Create NativeExecutor Base and GitNativeExecutor

**Files:**
- Create: `devilmcp/native_executors/__init__.py`
- Create: `devilmcp/native_executors/git.py`
- Test: `tests/test_native_executors.py`

**Step 1: Create tests for GitNativeExecutor**

```python
# tests/test_native_executors.py
import pytest
import tempfile
import os
from pathlib import Path
from devilmcp.native_executors.git import GitNativeExecutor

@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository."""
    import subprocess
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, capture_output=True)

    # Create a file and commit
    (repo_path / "test.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_path, capture_output=True)

    return repo_path

@pytest.mark.asyncio
async def test_git_executor_status(git_repo):
    executor = GitNativeExecutor(str(git_repo))
    result = await executor.execute("status", [])

    assert result.success is True
    assert "nothing to commit" in result.output or "clean" in result.output
    assert result.executor_type == "native-git"

    await executor.cleanup()

@pytest.mark.asyncio
async def test_git_executor_log(git_repo):
    executor = GitNativeExecutor(str(git_repo))
    result = await executor.execute("log", ["--oneline", "-1"])

    assert result.success is True
    assert "initial" in result.output

    await executor.cleanup()

@pytest.mark.asyncio
async def test_git_executor_diff(git_repo):
    # Modify the file
    (git_repo / "test.txt").write_text("modified")

    executor = GitNativeExecutor(str(git_repo))
    result = await executor.execute("diff", [])

    assert result.success is True
    assert "modified" in result.output or "-hello" in result.output

    await executor.cleanup()

@pytest.mark.asyncio
async def test_git_executor_unsupported_command(git_repo):
    executor = GitNativeExecutor(str(git_repo))
    result = await executor.execute("unsupported-command", [])

    assert result.success is False
    assert "not supported" in result.error.lower() or "unsupported" in result.error.lower()

    await executor.cleanup()

def test_git_executor_supported_commands(git_repo):
    executor = GitNativeExecutor(str(git_repo))
    commands = executor.get_supported_commands()

    assert "status" in commands
    assert "diff" in commands
    assert "log" in commands
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_native_executors.py -v`
Expected: FAIL with "No module named 'devilmcp.native_executors'"

**Step 3: Create native_executors package**

```python
# devilmcp/native_executors/__init__.py
"""
Native Executors Package
Python SDK integrations that bypass subprocess entirely.
"""

from .git import GitNativeExecutor

__all__ = ["GitNativeExecutor"]
```

```python
# devilmcp/native_executors/git.py
"""
Git Native Executor
Uses gitpython library instead of spawning git CLI.
"""

import logging
from typing import Optional, Dict, List

try:
    import git
    from git import Repo, GitCommandError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

from ..executor import ToolExecutor, ExecutionResult

logger = logging.getLogger(__name__)


class GitNativeExecutor(ToolExecutor):
    """Git operations via gitpython - no subprocess."""

    SUPPORTED_COMMANDS = [
        "status", "diff", "log", "add", "commit",
        "branch", "checkout", "fetch", "pull", "push"
    ]

    def __init__(self, repo_path: str):
        if not GIT_AVAILABLE:
            raise ImportError("gitpython is required for GitNativeExecutor. Install with: pip install gitpython")
        self.repo_path = repo_path
        self.repo = Repo(repo_path)

    def get_supported_commands(self) -> List[str]:
        """Return list of commands this executor handles."""
        return self.SUPPORTED_COMMANDS.copy()

    async def execute(
        self,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Execute git command using gitpython."""
        if command not in self.SUPPORTED_COMMANDS:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Command '{command}' not supported. Supported: {', '.join(self.SUPPORTED_COMMANDS)}",
                executor_type="native-git"
            )

        try:
            output = self._run_command(command, args)
            return ExecutionResult(
                success=True,
                output=output,
                executor_type="native-git"
            )
        except GitCommandError as e:
            return ExecutionResult(
                success=False,
                output=e.stdout or "",
                error=e.stderr or str(e),
                return_code=e.status,
                executor_type="native-git"
            )
        except Exception as e:
            logger.error(f"Git command failed: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                executor_type="native-git"
            )

    def _run_command(self, command: str, args: List[str]) -> str:
        """Run git command and return output."""
        git_cmd = self.repo.git

        if command == "status":
            return git_cmd.status(*args)
        elif command == "diff":
            return git_cmd.diff(*args)
        elif command == "log":
            return git_cmd.log(*args)
        elif command == "add":
            return git_cmd.add(*args)
        elif command == "commit":
            return git_cmd.commit(*args)
        elif command == "branch":
            return git_cmd.branch(*args)
        elif command == "checkout":
            return git_cmd.checkout(*args)
        elif command == "fetch":
            return git_cmd.fetch(*args)
        elif command == "pull":
            return git_cmd.pull(*args)
        elif command == "push":
            return git_cmd.push(*args)
        else:
            raise ValueError(f"Unhandled command: {command}")

    async def cleanup(self) -> None:
        """Clean up repository handle."""
        if hasattr(self, 'repo') and self.repo:
            self.repo.close()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_native_executors.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add devilmcp/native_executors/ tests/test_native_executors.py
git commit -m "feat: add GitNativeExecutor using gitpython"
```

---

## Task 5: Add Executor Routing to ToolRegistry

**Files:**
- Modify: `devilmcp/tool_registry.py`
- Test: `tests/test_tool_registry.py`

**Step 1: Create tests for executor routing**

```python
# tests/test_tool_registry.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from devilmcp.tool_registry import ToolRegistry, ToolConfig, ToolCapability
from devilmcp.executor import ExecutionResult
from devilmcp.subprocess_executor import SubprocessExecutor

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_session = MagicMock(return_value=AsyncMock())
    return db

@pytest.fixture
def sample_tool_config():
    return ToolConfig(
        name="echo",
        display_name="Echo",
        command="echo",
        args=[],
        capabilities=[],
        enabled=True,
        config={},
        prompt_patterns=[],
        init_timeout=5000,
        command_timeout=10000,
        max_context_size=None,
        supports_streaming=False
    )

@pytest.mark.asyncio
async def test_get_executor_returns_subprocess_by_default(mock_db, sample_tool_config):
    registry = ToolRegistry(mock_db)
    registry._tools_cache["echo"] = sample_tool_config

    executor = await registry.get_executor("echo")

    assert isinstance(executor, SubprocessExecutor)

@pytest.mark.asyncio
async def test_get_executor_caches_executors(mock_db, sample_tool_config):
    registry = ToolRegistry(mock_db)
    registry._tools_cache["echo"] = sample_tool_config

    executor1 = await registry.get_executor("echo")
    executor2 = await registry.get_executor("echo")

    assert executor1 is executor2  # Same instance

@pytest.mark.asyncio
async def test_execute_tool_routes_correctly(mock_db, sample_tool_config):
    registry = ToolRegistry(mock_db)
    registry._tools_cache["echo"] = sample_tool_config

    result = await registry.execute_tool("echo", "echo", ["hello"])

    assert result.success is True
    assert "hello" in result.output

@pytest.mark.asyncio
async def test_execute_tool_unknown_tool(mock_db):
    registry = ToolRegistry(mock_db)

    result = await registry.execute_tool("nonexistent", "test", [])

    assert result.success is False
    assert "not found" in result.error.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_tool_registry.py -v`
Expected: FAIL with "AttributeError: 'ToolRegistry' object has no attribute 'get_executor'"

**Step 3: Add executor routing to ToolRegistry**

Add these methods to `devilmcp/tool_registry.py`:

```python
# Add imports at top of file
from .executor import ToolExecutor, ExecutionResult
from .subprocess_executor import SubprocessExecutor

# Add to ToolRegistry class:

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._tools_cache: Dict[str, ToolConfig] = {}
        self._executors: Dict[str, ToolExecutor] = {}
        self._native_registry: Dict[str, type] = {}

        # Register native executors
        try:
            from .native_executors.git import GitNativeExecutor
            self._native_registry["git"] = GitNativeExecutor
        except ImportError:
            logger.warning("GitNativeExecutor not available (gitpython not installed)")

    async def get_executor(self, tool_name: str) -> ToolExecutor:
        """Get or create the appropriate executor for a tool."""

        # Return cached executor if exists
        if tool_name in self._executors:
            return self._executors[tool_name]

        # Check if native executor available
        if tool_name in self._native_registry:
            try:
                import os
                repo_path = os.getenv('PROJECT_ROOT', os.getcwd())
                executor = self._native_registry[tool_name](repo_path)
                self._executors[tool_name] = executor
                logger.info(f"Using native executor for {tool_name}")
                return executor
            except Exception as e:
                logger.warning(f"Failed to create native executor for {tool_name}: {e}")

        # Fall back to subprocess executor
        tool_config = self.get_tool(tool_name)
        if not tool_config:
            raise ValueError(f"Tool '{tool_name}' not found")

        executor = SubprocessExecutor(tool_config)
        self._executors[tool_name] = executor
        return executor

    async def execute_tool(
        self,
        tool_name: str,
        command: str,
        args: List[str] = None
    ) -> ExecutionResult:
        """Main entry point - routes to correct executor."""
        args = args or []

        try:
            executor = await self.get_executor(tool_name)
            return await executor.execute(command, args)
        except ValueError as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution failed: {e}"
            )

    async def cleanup_executors(self) -> None:
        """Clean up all cached executors."""
        for executor in self._executors.values():
            try:
                await executor.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up executor: {e}")
        self._executors.clear()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tool_registry.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add devilmcp/tool_registry.py tests/test_tool_registry.py
git commit -m "feat: add executor routing to ToolRegistry"
```

---

## Task 6: Update server.py to Use New API

**Files:**
- Modify: `devilmcp/server.py`

**Step 1: Update imports and add execute_tool MCP endpoint**

Add to `devilmcp/server.py` after existing tool management tools:

```python
@mcp.tool()
async def execute_tool(
    tool_name: str,
    command: str,
    args: Optional[List[str]] = None
) -> Dict:
    """
    Execute a command using the appropriate executor (native or subprocess).

    For stateless tools (no prompt_patterns): runs command and returns when complete.
    For stateful tools (has prompt_patterns): maintains session between calls.
    """
    result = await tool_registry.execute_tool(tool_name, command, args or [])
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "return_code": result.return_code,
        "timed_out": result.timed_out,
        "executor_type": result.executor_type
    }
```

**Step 2: Add cleanup on shutdown**

Find the `main()` function and ensure cleanup happens:

```python
# At module level, before main():
import atexit

async def cleanup():
    """Cleanup resources on shutdown."""
    await tool_registry.cleanup_executors()
    await browser_manager.close()

# In or after main(), register cleanup
def main():
    import asyncio

    async def run_server():
        await db_manager.initialize()
        await tool_registry.load_tools()
        await mcp.run(transport='stdio')
        await cleanup()

    asyncio.run(run_server())
```

**Step 3: Verify server still starts**

Run: `python -m devilmcp.server --help` (or just start it briefly)
Expected: Server initializes without errors

**Step 4: Commit**

```bash
git add devilmcp/server.py
git commit -m "feat: add execute_tool MCP endpoint using new executor system"
```

---

## Task 7: Deprecate ProcessManager

**Files:**
- Modify: `devilmcp/process_manager.py`

**Step 1: Add deprecation warnings**

Add at the top of `process_manager.py`:

```python
import warnings

warnings.warn(
    "ProcessManager is deprecated and will be removed in v2.0. "
    "Use ToolRegistry.execute_tool() instead.",
    DeprecationWarning,
    stacklevel=2
)
```

Add to each public method:

```python
async def spawn_process(self, ...):
    """..."""
    warnings.warn(
        "spawn_process is deprecated. Use ToolRegistry.execute_tool() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # ... rest of method
```

**Step 2: Update docstrings**

```python
class ProcessManager:
    """
    DEPRECATED: Manages lifecycle of CLI tool processes.

    This class is deprecated and will be removed in v2.0.
    Use ToolRegistry.execute_tool() for new code.
    """
```

**Step 3: Commit**

```bash
git add devilmcp/process_manager.py
git commit -m "chore: deprecate ProcessManager in favor of ToolExecutor system"
```

---

## Task 8: Remove Playwright Browser Integration

**Files:**
- Delete: `devilmcp/browser.py`
- Modify: `devilmcp/server.py` (remove browser imports and tools)
- Modify: `requirements.txt` (remove playwright)

**Step 1: Remove browser imports from server.py**

Remove these lines:
```python
from devilmcp.browser import BrowserManager
browser_manager = BrowserManager()
```

**Step 2: Remove all browser_* MCP tools**

Search for and remove all functions starting with `@mcp.tool()` followed by `async def browser_`:
- `browser_navigate`
- `browser_click`
- `browser_type`
- `browser_get_content`
- `browser_screenshot`
- `browser_run_script`

**Step 3: Remove from cleanup**

Remove `await browser_manager.close()` from cleanup function.

**Step 4: Delete browser.py**

```bash
rm devilmcp/browser.py
```

**Step 5: Update requirements.txt**

Remove the `playwright>=1.40.0` line.

**Step 6: Update CLAUDE.md**

Remove browser.py from architecture diagram and references.

**Step 7: Commit**

```bash
git add -A
git commit -m "chore: remove Playwright browser integration

Users who need browser automation can install the official Playwright MCP server separately."
```

---

## Task 9: Final Integration Test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Create integration test**

```python
# tests/test_integration.py
import pytest
import tempfile
import subprocess
from pathlib import Path

@pytest.mark.asyncio
async def test_full_tool_execution_flow():
    """Test the complete flow from ToolRegistry to execution."""
    from devilmcp.tool_registry import ToolRegistry, ToolConfig
    from unittest.mock import MagicMock, AsyncMock

    # Setup mock DB
    mock_db = MagicMock()
    mock_db.get_session = MagicMock(return_value=AsyncMock())

    registry = ToolRegistry(mock_db)

    # Register a test tool
    registry._tools_cache["test-echo"] = ToolConfig(
        name="test-echo",
        display_name="Test Echo",
        command="echo",
        args=[],
        capabilities=[],
        enabled=True,
        config={},
        prompt_patterns=[],
        init_timeout=5000,
        command_timeout=10000,
        max_context_size=None,
        supports_streaming=False
    )

    # Execute
    result = await registry.execute_tool("test-echo", "echo", ["integration", "test"])

    assert result.success is True
    assert "integration test" in result.output
    assert result.executor_type == "subprocess-stateless"

    # Cleanup
    await registry.cleanup_executors()

@pytest.mark.asyncio
async def test_git_native_executor_in_real_repo(tmp_path):
    """Test GitNativeExecutor with a real git repo."""
    from devilmcp.native_executors.git import GitNativeExecutor

    # Create temp repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    (tmp_path / "file.txt").write_text("content")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

    executor = GitNativeExecutor(str(tmp_path))

    # Test status
    result = await executor.execute("status", [])
    assert result.success is True
    assert result.executor_type == "native-git"

    await executor.cleanup()
```

**Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for ToolExecutor system"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Create ToolExecutor interface | `executor.py`, `test_executor.py` |
| 2 | SubprocessExecutor stateless mode | `subprocess_executor.py`, `test_subprocess_executor.py` |
| 3 | SubprocessExecutor stateful mode | `subprocess_executor.py` |
| 4 | GitNativeExecutor | `native_executors/`, `test_native_executors.py` |
| 5 | ToolRegistry routing | `tool_registry.py`, `test_tool_registry.py` |
| 6 | server.py integration | `server.py` |
| 7 | Deprecate ProcessManager | `process_manager.py` |
| 8 | Remove Playwright | `browser.py`, `server.py`, `requirements.txt` |
| 9 | Integration tests | `test_integration.py` |

**Total: 9 tasks, ~45 steps**
