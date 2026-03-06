"""Scheduler port — platform-specific schedule adapters.

Adapters generate cron entries, launchd plists, or systemd timers
from a resource's schedule field. The manifest is the single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ScheduleEntry:
    """What got written to the platform scheduler."""

    resource_name: str
    schedule: str
    command: str
    platform: str
    location: str  # file path or crontab identifier
    enabled: bool = True


@runtime_checkable
class Scheduler(Protocol):
    """Structural type for platform scheduler adapters."""

    @property
    def platform_name(self) -> str: ...

    def is_available(self) -> bool:
        """Can this scheduler run on the current system?"""
        ...

    def enable(self, resource_name: str, schedule: str, command: str) -> ScheduleEntry:
        """Create or update a scheduled entry."""
        ...

    def disable(self, resource_name: str) -> bool:
        """Remove a scheduled entry. Returns True if it existed."""
        ...

    def status(self, resource_name: str) -> ScheduleEntry | None:
        """Check if a schedule entry exists for this resource."""
        ...

    def list_entries(self) -> list[ScheduleEntry]:
        """List all proviso-managed schedule entries."""
        ...
