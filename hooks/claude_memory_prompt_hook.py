#!/usr/bin/env python3
"""
Claude Memory UserPromptSubmit Hook - Injects context reminder into every prompt

This hook runs when the user submits a prompt.
For UserPromptSubmit hooks, stdout is added as context to Claude's input.

This provides a subtle, persistent reminder about the Claude Memory protocol.
"""

import json
import os
import sys
from pathlib import Path

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", "")


def has_cm_tools() -> bool:
    """Check if this project likely has Claude Memory set up."""
    if not PROJECT_DIR:
        return False

    # Check for .claude-memory directory or skill
    cm_dir = Path(PROJECT_DIR) / ".claude-memory"
    skill_dir = Path(PROJECT_DIR) / ".claude" / "skills" / "claude_memory-protocol"

    return cm_dir.exists() or skill_dir.exists()


def main():
    """Output context reminder if Claude Memory is set up."""
    if not has_cm_tools():
        # No Claude Memory setup detected, don't add reminder
        sys.exit(0)

    # This output gets added as context to Claude's input
    reminder = (
        "[Claude Memory Protocol Reminder] "
        "When completing tasks: (1) record decisions with remember(), "
        "(2) record outcomes with record_outcome() when done. "
        "Failures are valuable - always record them."
    )

    print(reminder)
    sys.exit(0)


if __name__ == "__main__":
    main()
