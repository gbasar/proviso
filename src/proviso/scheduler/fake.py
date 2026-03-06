"""In-memory scheduler for tests."""

from __future__ import annotations

from proviso.scheduler.protocol import ScheduleEntry


class FakeScheduler:
    """Test double: stores entries in memory."""

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self._entries: dict[str, ScheduleEntry] = {}

    @property
    def platform_name(self) -> str:
        return "fake"

    def is_available(self) -> bool:
        return self._available

    def enable(self, resource_name: str, schedule: str, command: str) -> ScheduleEntry:
        entry = ScheduleEntry(
            resource_name=resource_name,
            schedule=schedule,
            command=command,
            platform="fake",
            location=f"fake://{resource_name}",
        )
        self._entries[resource_name] = entry
        return entry

    def disable(self, resource_name: str) -> bool:
        if resource_name in self._entries:
            del self._entries[resource_name]
            return True
        return False

    def status(self, resource_name: str) -> ScheduleEntry | None:
        return self._entries.get(resource_name)

    def list_entries(self) -> list[ScheduleEntry]:
        return list(self._entries.values())
