"""Crontab scheduler adapter — Linux/macOS cron.

Manages proviso entries in the user's crontab. Each entry is tagged
with a comment marker so we can find, update, and remove them.
"""

from __future__ import annotations

from proviso.scheduler.protocol import ScheduleEntry
from proviso.shell.protocol import Shell

# Marker format: # proviso:<resource_name>
_MARKER_PREFIX = "# proviso:"


def _marker(resource_name: str) -> str:
    return f"{_MARKER_PREFIX}{resource_name}"


class CrontabScheduler:
    """Adapter for crontab (Linux and macOS)."""

    def __init__(self, shell: Shell, proviso_bin: str = "proviso") -> None:
        self._shell = shell
        self._proviso_bin = proviso_bin

    @property
    def platform_name(self) -> str:
        return "crontab"

    def is_available(self) -> bool:
        return self._shell.run("which crontab").success

    def enable(self, resource_name: str, schedule: str, command: str) -> ScheduleEntry:
        marker = _marker(resource_name)
        cron_line = f"{schedule} {command} {marker}"

        # Remove existing entry if present, then append
        self._remove_entry(resource_name)
        existing = self._get_crontab()
        new_crontab = f"{existing}\n{cron_line}\n" if existing else f"{cron_line}\n"
        self._set_crontab(new_crontab)

        return ScheduleEntry(
            resource_name=resource_name,
            schedule=schedule,
            command=command,
            platform="crontab",
            location="crontab -l",
        )

    def disable(self, resource_name: str) -> bool:
        existing = self._get_crontab()
        marker = _marker(resource_name)
        if marker not in existing:
            return False
        self._remove_entry(resource_name)
        return True

    def status(self, resource_name: str) -> ScheduleEntry | None:
        existing = self._get_crontab()
        marker = _marker(resource_name)
        for line in existing.splitlines():
            if marker in line:
                parts = line.replace(marker, "").strip()
                # cron format: min hour dom mon dow command
                fields = parts.split(None, 5)
                if len(fields) >= 6:
                    schedule = " ".join(fields[:5])
                    command = fields[5]
                else:
                    schedule = parts
                    command = ""
                return ScheduleEntry(
                    resource_name=resource_name,
                    schedule=schedule,
                    command=command,
                    platform="crontab",
                    location="crontab -l",
                )
        return None

    def list_entries(self) -> list[ScheduleEntry]:
        existing = self._get_crontab()
        entries = []
        for line in existing.splitlines():
            if _MARKER_PREFIX in line:
                # Extract resource name from marker
                marker_start = line.index(_MARKER_PREFIX) + len(_MARKER_PREFIX)
                name = line[marker_start:].strip()
                entry = self.status(name)
                if entry:
                    entries.append(entry)
        return entries

    def _get_crontab(self) -> str:
        result = self._shell.run("crontab -l")
        return result.stdout if result.success else ""

    def _set_crontab(self, content: str) -> None:
        # Strip blank lines and trailing whitespace
        clean = "\n".join(line for line in content.splitlines() if line.strip())
        if clean:
            clean += "\n"
        self._shell.run(f"echo '{clean}' | crontab -")

    def _remove_entry(self, resource_name: str) -> None:
        existing = self._get_crontab()
        marker = _marker(resource_name)
        lines = [line for line in existing.splitlines() if marker not in line]
        self._set_crontab("\n".join(lines))
