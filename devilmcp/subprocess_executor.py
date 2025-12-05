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
