"""Launchd scheduler adapter — macOS.

Generates and manages plist files in ~/Library/LaunchAgents.
Each resource gets its own plist: com.proviso.<resource_name>.plist
"""

from __future__ import annotations

from pathlib import Path

from proviso.scheduler.protocol import ScheduleEntry
from proviso.shell.protocol import Shell

_PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
_LABEL_PREFIX = "com.proviso."


def _label(resource_name: str) -> str:
    return f"{_LABEL_PREFIX}{resource_name}"


def _plist_path(resource_name: str) -> Path:
    return _PLIST_DIR / f"{_label(resource_name)}.plist"


def _cron_to_launchd_calendar(schedule: str) -> dict[str, int | str]:
    """Convert a cron expression to a launchd CalendarInterval dict.

    Only handles simple cases: exact values and wildcards.
    """
    parts = schedule.split()
    if len(parts) != 5:
        msg = f"Expected 5-field cron expression, got: {schedule}"
        raise ValueError(msg)

    field_names = ["Minute", "Hour", "Day", "Month", "Weekday"]
    calendar: dict[str, int | str] = {}

    for name, value in zip(field_names, parts):
        if value != "*":
            # Handle */N intervals — launchd doesn't support these natively,
            # so we take the simple path for now
            if value.startswith("*/"):
                calendar[name] = int(value[2:])
            else:
                calendar[name] = int(value)

    return calendar


def _build_plist(resource_name: str, command: str, schedule: str) -> str:
    """Build a launchd plist XML string."""
    label = _label(resource_name)
    calendar = _cron_to_launchd_calendar(schedule)

    calendar_entries = ""
    for key, val in calendar.items():
        calendar_entries += f"\t\t\t<key>{key}</key>\n\t\t\t<integer>{val}</integer>\n"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>Label</key>
\t<string>{label}</string>
\t<key>ProgramArguments</key>
\t<array>
\t\t<string>/bin/sh</string>
\t\t<string>-c</string>
\t\t<string>{command}</string>
\t</array>
\t<key>StartCalendarInterval</key>
\t<dict>
{calendar_entries}\t</dict>
\t<key>StandardOutPath</key>
\t<string>/tmp/{label}.stdout.log</string>
\t<key>StandardErrorPath</key>
\t<string>/tmp/{label}.stderr.log</string>
</dict>
</plist>
"""


class LaunchdScheduler:
    """Adapter for launchd (macOS)."""

    def __init__(self, shell: Shell, proviso_bin: str = "proviso") -> None:
        self._shell = shell
        self._proviso_bin = proviso_bin

    @property
    def platform_name(self) -> str:
        return "launchd"

    def is_available(self) -> bool:
        return self._shell.run("which launchctl").success

    def enable(self, resource_name: str, schedule: str, command: str) -> ScheduleEntry:
        plist = _plist_path(resource_name)
        content = _build_plist(resource_name, command, schedule)

        # Unload if already loaded
        self.disable(resource_name)

        self._shell.run(f"mkdir -p {_PLIST_DIR}")
        self._shell.run(f"cat > {plist} << 'PLIST_EOF'\n{content}PLIST_EOF")
        self._shell.run(f"launchctl load {plist}")

        return ScheduleEntry(
            resource_name=resource_name,
            schedule=schedule,
            command=command,
            platform="launchd",
            location=str(plist),
        )

    def disable(self, resource_name: str) -> bool:
        plist = _plist_path(resource_name)
        label = _label(resource_name)
        result = self._shell.run(f"launchctl list | grep {label}")
        if not result.success:
            return False
        self._shell.run(f"launchctl unload {plist}")
        self._shell.run(f"rm -f {plist}")
        return True

    def status(self, resource_name: str) -> ScheduleEntry | None:
        label = _label(resource_name)
        result = self._shell.run(f"launchctl list | grep {label}")
        if not result.success:
            return None
        return ScheduleEntry(
            resource_name=resource_name,
            schedule="",  # would need to parse the plist to get this
            command="",
            platform="launchd",
            location=str(_plist_path(resource_name)),
            enabled=True,
        )

    def list_entries(self) -> list[ScheduleEntry]:
        result = self._shell.run(f"launchctl list | grep {_LABEL_PREFIX}")
        if not result.success:
            return []
        entries = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[2].startswith(_LABEL_PREFIX):
                name = parts[2][len(_LABEL_PREFIX) :]
                entry = self.status(name)
                if entry:
                    entries.append(entry)
        return entries
