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
