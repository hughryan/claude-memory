"""
ClaudeMemory Core Package
"""

try:
    from importlib.metadata import version as _get_version
    __version__ = _get_version("claude_memory")
except Exception:
    # Fallback for development or if package not installed
    __version__ = "2.16.0"
