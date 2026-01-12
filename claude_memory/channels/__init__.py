"""
Notification Channels for Claude Memory File Watcher.

This package provides various notification channel implementations
for the proactive file watcher system.

Available Channels:
- SystemNotifyChannel: Desktop notifications via plyer
- LogFileChannel: Writes to a log file for external consumption
- EditorPollChannel: Creates a poll file for editor integration
- LoggingChannel: Simple logging (re-exported from watcher)
- CallbackChannel: Custom callback (re-exported from watcher)

Usage:
    from claude_memory.channels import SystemNotifyChannel, LogFileChannel
    from claude_memory.watcher import FileWatcher

    watcher = FileWatcher(
        project_path=Path("/my/project"),
        memory_manager=memory_manager,
        channels=[
            SystemNotifyChannel(),
            LogFileChannel(Path("/tmp/claude-memory.log"))
        ]
    )
"""

from claude_memory.watcher import (
    NotificationChannel,
    WatcherNotification,
    LoggingChannel,
    CallbackChannel,
)

from .system_notify import SystemNotifyChannel
from .log_notify import LogFileChannel
from .editor_poll import EditorPollChannel

__all__ = [
    # Protocol and data
    "NotificationChannel",
    "WatcherNotification",
    # Channel implementations
    "SystemNotifyChannel",
    "LogFileChannel",
    "EditorPollChannel",
    "LoggingChannel",
    "CallbackChannel",
]
