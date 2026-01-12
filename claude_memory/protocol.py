"""
Protocol Enforcement for ClaudeMemory.

Implements rigid enforcement decorators for the Protocol:
- requires_init: Blocks tools until get_briefing() called
- requires_context_check: Blocks mutating tools until context_check() called
- PreflightToken: Cryptographic proof of consultation

The Protocol flow is:
    INIT (get_briefing) -> CHECK CONTEXT (context_check) -> RECORD (remember) -> TRACK OUTCOME (record_outcome)
"""

import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, Set

logger = logging.getLogger(__name__)

# TTL for context checks (5 minutes default)
CONTEXT_CHECK_TTL_SECONDS = 300

# Token secret from environment (falls back to a default for testing)
_TOKEN_SECRET = os.environ.get("CLAUDE_MEMORY_TOKEN_SECRET", "claude-memory-protocol-default-secret")


# ============================================================================
# TOOL CLASSIFICATION
# ============================================================================

# Tools exempt from all protocol enforcement (entry points and diagnostics)
PROTOCOL_EXEMPT_TOOLS: Set[str] = {
    "get_briefing",      # Entry point - starts initialization
    "health",            # Diagnostic - always available
    "context_check",     # Part of the protocol flow
    "recall",            # Read-only query
    "recall_for_file",   # Read-only query
    "search_memories",   # Read-only query
    "find_related",      # Read-only query
    "check_rules",       # Read-only query
    "list_rules",        # Read-only query
    "find_code",         # Read-only query
    "analyze_impact",    # Read-only analysis
    "export_data",       # Read-only export
    "scan_todos",        # Read-only scan (unless auto_remember=True)
    "propose_refactor",  # Read-only analysis
    "get_graph",         # Read-only query
    "trace_chain",       # Read-only query
}

# Tools that REQUIRE initialization (must call get_briefing first)
INIT_REQUIRED_TOOLS: Set[str] = {
    "remember",
    "remember_batch",
    "add_rule",
    "update_rule",
    "record_outcome",
    "link_memories",
    "unlink_memories",
    "pin_memory",
    "archive_memory",
    "prune_memories",
    "cleanup_memories",
    "compact_memories",
    "import_data",
    "rebuild_index",
    "index_project",
    "ingest_doc",
}

# Tools that REQUIRE context check (must call context_check before mutating)
CONTEXT_CHECK_REQUIRED_TOOLS: Set[str] = {
    "remember",
    "remember_batch",
    "add_rule",
    "update_rule",
    "prune_memories",
    "cleanup_memories",
    "compact_memories",
    "import_data",
    "ingest_doc",
}


# ============================================================================
# PROTOCOL VIOLATION RESPONSES
# ============================================================================

class ProtocolViolation:
    """
    Standard violation response structures.

    Returns structured dicts that block tool execution and guide
    the AI toward proper protocol adherence.
    """

    @staticmethod
    def init_required(project_path: str) -> Dict[str, Any]:
        """
        Response when tool is called without prior get_briefing().

        The Protocol requires initialization before any meaningful work.
        """
        return {
            "status": "blocked",
            "violation": "INIT_REQUIRED",
            "message": (
                "The Protocol requires initialization before work begins. "
                "You must first call get_briefing() to initialize the memory system "
                "and receive context about this project's memories, warnings, and rules."
            ),
            "project_path": project_path,
            "remedy": {
                "tool": "get_briefing",
                "args": {"project_path": project_path},
                "description": "Initialize the memory system",
            },
        }

    @staticmethod
    def context_check_required(tool_name: str, project_path: str) -> Dict[str, Any]:
        """
        Response when mutating tool is called without prior context_check().

        Before recording new memories, one must check context on what
        already exists to avoid contradictions and duplications.
        """
        return {
            "status": "blocked",
            "violation": "CONTEXT_CHECK_REQUIRED",
            "message": (
                f"The Protocol requires checking context before using '{tool_name}'. "
                f"You must first call context_check() to understand existing memories "
                f"and rules related to your intended action. This prevents contradictions "
                f"and respects existing knowledge."
            ),
            "project_path": project_path,
            "tool_blocked": tool_name,
            "remedy": {
                "tool": "context_check",
                "args": {
                    "description": f"About to use {tool_name}",
                    "project_path": project_path,
                },
                "description": f"Check context before {tool_name}",
            },
        }

    @staticmethod
    def context_check_expired(tool_name: str, project_path: str, age_seconds: int) -> Dict[str, Any]:
        """
        Response when context_check was done but has expired.
        """
        return {
            "status": "blocked",
            "violation": "CONTEXT_CHECK_EXPIRED",
            "message": (
                f"Your context check has expired ({age_seconds}s old, limit is {CONTEXT_CHECK_TTL_SECONDS}s). "
                f"The context may have changed. Please run a fresh context check before '{tool_name}'."
            ),
            "project_path": project_path,
            "tool_blocked": tool_name,
            "remedy": {
                "tool": "context_check",
                "args": {
                    "description": f"Refreshing context before {tool_name}",
                    "project_path": project_path,
                },
                "description": "Run fresh context check",
            },
        }


# ============================================================================
# PREFLIGHT TOKEN
# ============================================================================

@dataclass
class PreflightToken:
    """
    Cryptographic proof that context_check was performed.

    Tokens are issued after context_check() and can be validated
    before mutating operations to prove counsel was sought.

    The token includes:
    - action: What the AI intends to do
    - session_id: Links to the current session
    - issued_at: When counsel was sought
    - expires_at: When the counsel becomes stale
    - signature: HMAC signature to detect tampering
    """

    action: str
    session_id: str
    project_path: str
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: str = ""

    @classmethod
    def issue(
        cls,
        action: str,
        session_id: str,
        project_path: str,
        ttl_seconds: int = CONTEXT_CHECK_TTL_SECONDS,
    ) -> "PreflightToken":
        """
        Issue a new preflight token after context_check.

        Args:
            action: Description of what the AI intends to do
            session_id: Current session identifier
            project_path: Project this token is for
            ttl_seconds: How long until the token expires

        Returns:
            Signed PreflightToken
        """
        now = datetime.now(timezone.utc)
        token = cls(
            action=action,
            session_id=session_id,
            project_path=project_path,
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        token.signature = token._compute_signature()
        return token

    def _compute_signature(self) -> str:
        """Compute HMAC signature for the token data."""
        payload = f"{self.action}|{self.session_id}|{self.project_path}|{self.issued_at.isoformat()}|{self.expires_at.isoformat()}"
        return hmac.new(
            _TOKEN_SECRET.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """Check if the token is valid (not expired and signature matches)."""
        if self.is_expired():
            return False
        return hmac.compare_digest(self.signature, self._compute_signature())

    def serialize(self) -> str:
        """Serialize the token to JSON for storage/transmission."""
        return json.dumps({
            "action": self.action,
            "session_id": self.session_id,
            "project_path": self.project_path,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "signature": self.signature,
        })

    @classmethod
    def verify(cls, serialized: str, project_path: str) -> Optional["PreflightToken"]:
        """
        Verify and deserialize a token.

        Args:
            serialized: JSON-serialized token
            project_path: Expected project path

        Returns:
            PreflightToken if valid, None if invalid/tampered/expired
        """
        try:
            data = json.loads(serialized)
            token = cls(
                action=data["action"],
                session_id=data["session_id"],
                project_path=data["project_path"],
                issued_at=datetime.fromisoformat(data["issued_at"]),
                expires_at=datetime.fromisoformat(data["expires_at"]),
                signature=data["signature"],
            )

            # Verify project path matches
            if token.project_path != project_path:
                logger.warning(f"Token project mismatch: {token.project_path} != {project_path}")
                return None

            # Verify signature and expiry
            if not token.is_valid():
                logger.warning("Token invalid: signature mismatch or expired")
                return None

            return token

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Token verification failed: {e}")
            return None


# ============================================================================
# PROTOCOL ENFORCER
# ============================================================================

class ProtocolEnforcer:
    """
    Enforces the Protocol for MCP tool calls.

    The enforcer checks session state to ensure:
    1. Initialization (get_briefing) was performed before work
    2. Context check (context_check) was done before mutations

    Usage:
        enforcer = ProtocolEnforcer()

        # In tool implementation:
        violation = await enforcer.check_init(project_path)
        if violation:
            return violation

        violation = await enforcer.check_context(tool_name, project_path)
        if violation:
            return violation
    """

    def __init__(self, session_manager=None):
        """
        Initialize the enforcer.

        Args:
            session_manager: Optional SessionManager instance for state lookup.
                           If not provided, uses a mock for testing.
        """
        self._session_manager = session_manager

    async def _get_session_state(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        Get current session state.

        This is a separate method to allow mocking in tests.
        """
        if self._session_manager is None:
            # No session manager - return None (will be treated as unbriefed)
            return None
        return await self._session_manager.get_session_state(project_path)

    async def check_init(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        Check if initialization (get_briefing) was performed.

        Args:
            project_path: Project to check

        Returns:
            None if initialization complete, violation dict if not
        """
        state = await self._get_session_state(project_path)

        if state is None or not state.get("briefed", False):
            logger.info(f"Initialization required for project: {project_path}")
            return ProtocolViolation.init_required(project_path)

        return None  # Initialization complete

    async def check_context(
        self,
        tool_name: str,
        project_path: str,
        ttl_seconds: int = CONTEXT_CHECK_TTL_SECONDS,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if context check (context_check) was done recently.

        Args:
            tool_name: Name of the tool being called
            project_path: Project to check
            ttl_seconds: How old the context check can be

        Returns:
            None if context check is fresh, violation dict if not
        """
        # First check initialization
        init_violation = await self.check_init(project_path)
        if init_violation:
            return init_violation

        state = await self._get_session_state(project_path)
        if state is None:
            return ProtocolViolation.context_check_required(tool_name, project_path)

        context_checks = state.get("context_checks", [])

        if not context_checks:
            logger.info(f"Context check required before {tool_name} for project: {project_path}")
            return ProtocolViolation.context_check_required(tool_name, project_path)

        # Find the most recent context check
        now = datetime.now(timezone.utc)
        most_recent = None
        most_recent_age = None

        for check in context_checks:
            # Handle both dict format (with timestamp) and string format (legacy)
            if isinstance(check, dict) and "timestamp" in check:
                try:
                    check_time = datetime.fromisoformat(check["timestamp"])
                    if check_time.tzinfo is None:
                        check_time = check_time.replace(tzinfo=timezone.utc)
                    age = (now - check_time).total_seconds()
                    if most_recent_age is None or age < most_recent_age:
                        most_recent = check
                        most_recent_age = age
                except (ValueError, TypeError):
                    continue
            elif isinstance(check, str):
                # Legacy format - treat as valid (no timestamp to check)
                return None  # Allow through

        if most_recent is None:
            # No valid timestamped checks found, but we have legacy checks
            if context_checks:
                return None  # Allow through for backwards compatibility
            return ProtocolViolation.context_check_required(tool_name, project_path)

        # Check if the most recent context check is still fresh
        if most_recent_age > ttl_seconds:
            logger.info(f"Context check expired ({most_recent_age:.0f}s old) for {tool_name}")
            return ProtocolViolation.context_check_expired(tool_name, project_path, int(most_recent_age))

        return None  # Context check is fresh


# ============================================================================
# DECORATOR FUNCTIONS
# ============================================================================

# Callback to get project context from server (set by server.py at import time)
_get_project_context_callback: Optional[Callable[[str], Any]] = None


def set_context_callback(callback: Callable[[str], Any]) -> None:
    """Register the callback to get project context from server."""
    global _get_project_context_callback
    _get_project_context_callback = callback


def _get_context_state(project_path: str) -> Optional[Dict[str, Any]]:
    """
    Get session state for a project using the registered callback.

    Returns a dict with 'briefed' and 'context_checks' keys, or None if
    no context is available.
    """
    if _get_project_context_callback is None:
        return None

    try:
        ctx = _get_project_context_callback(project_path)
        if ctx is None:
            return None
        return {
            "briefed": getattr(ctx, "briefed", False),
            "context_checks": getattr(ctx, "context_checks", []),
        }
    except Exception as e:
        logger.warning(f"Failed to get context for {project_path}: {e}")
        return None


def requires_init(func: Callable) -> Callable:
    """
    Decorator that enforces initialization (get_briefing) before tool execution.

    Usage:
        @requires_init
        async def remember(content: str, project_path: str, ...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract project_path from kwargs or args
        project_path = kwargs.get("project_path")
        if project_path is None and args:
            # Try to find project_path in positional args
            # This is fragile - prefer explicit kwargs
            pass

        if project_path is None:
            # Can't enforce without project_path
            logger.warning(f"Cannot enforce initialization for {func.__name__}: no project_path")
            return await func(*args, **kwargs)

        # Check state via callback
        state = _get_context_state(project_path)
        if state is None or not state.get("briefed", False):
            logger.info(f"Initialization required for {func.__name__}")
            return ProtocolViolation.init_required(project_path)

        return await func(*args, **kwargs)

    return wrapper


def requires_context_check(func: Callable) -> Callable:
    """
    Decorator that enforces context check (context_check) before tool execution.

    This also implicitly enforces initialization.

    Usage:
        @requires_context_check
        async def remember(content: str, project_path: str, ...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract project_path from kwargs or args
        project_path = kwargs.get("project_path")
        if project_path is None and args:
            # Try to find project_path in positional args
            pass

        if project_path is None:
            # Can't enforce without project_path
            logger.warning(f"Cannot enforce context check for {func.__name__}: no project_path")
            return await func(*args, **kwargs)

        # Check state via callback
        state = _get_context_state(project_path)

        # First check initialization
        if state is None or not state.get("briefed", False):
            logger.info(f"Initialization required before {func.__name__}")
            return ProtocolViolation.init_required(project_path)

        # Then check context
        context_checks = state.get("context_checks", [])
        if not context_checks:
            logger.info(f"Context check required before {func.__name__}")
            return ProtocolViolation.context_check_required(func.__name__, project_path)

        # Check if the most recent context check is still fresh
        now = datetime.now(timezone.utc)
        most_recent_age = None

        for check in context_checks:
            if isinstance(check, dict) and "timestamp" in check:
                try:
                    check_time = datetime.fromisoformat(check["timestamp"])
                    if check_time.tzinfo is None:
                        check_time = check_time.replace(tzinfo=timezone.utc)
                    age = (now - check_time).total_seconds()
                    if most_recent_age is None or age < most_recent_age:
                        most_recent_age = age
                except (ValueError, TypeError):
                    continue

        if most_recent_age is None:
            # No valid timestamped checks
            logger.info(f"Context check required (no valid checks) before {func.__name__}")
            return ProtocolViolation.context_check_required(func.__name__, project_path)

        if most_recent_age > CONTEXT_CHECK_TTL_SECONDS:
            logger.info(f"Context check expired ({most_recent_age:.0f}s old) for {func.__name__}")
            return ProtocolViolation.context_check_expired(func.__name__, project_path, int(most_recent_age))

        return await func(*args, **kwargs)

    return wrapper
