"""Scheduler tests — protocol conformance, crontab with fake shell, launchd calendar conversion."""

from __future__ import annotations

import pytest

from proviso.scheduler import (
    CrontabScheduler,
    FakeScheduler,
    LaunchdScheduler,
    ScheduleEntry,
    Scheduler,
)
from proviso.scheduler.launchd import _cron_to_launchd_calendar
from proviso.shell import FakeShell, ShellResult


class TestProtocolConformance:
    def test_fake_is_scheduler(self) -> None:
        assert isinstance(FakeScheduler(), Scheduler)

    def test_crontab_is_scheduler(self) -> None:
        assert isinstance(CrontabScheduler(shell=FakeShell()), Scheduler)

    def test_launchd_is_scheduler(self) -> None:
        assert isinstance(LaunchdScheduler(shell=FakeShell()), Scheduler)


class TestFakeScheduler:
    def test_enable_and_status(self) -> None:
        sched = FakeScheduler()
        entry = sched.enable("jq", "0 1 * * *", "proviso sync jq")
        assert entry.resource_name == "jq"
        assert entry.schedule == "0 1 * * *"
        assert sched.status("jq") is not None

    def test_disable(self) -> None:
        sched = FakeScheduler()
        sched.enable("jq", "0 1 * * *", "proviso sync jq")
        assert sched.disable("jq") is True
        assert sched.status("jq") is None

    def test_disable_nonexistent(self) -> None:
        sched = FakeScheduler()
        assert sched.disable("jq") is False

    def test_list_entries(self) -> None:
        sched = FakeScheduler()
        sched.enable("jq", "0 1 * * *", "proviso sync jq")
        sched.enable("rg", "0 2 * * *", "proviso sync rg")
        assert len(sched.list_entries()) == 2

    def test_unavailable(self) -> None:
        sched = FakeScheduler(available=False)
        assert not sched.is_available()


class TestCrontabScheduler:
    def test_is_available(self) -> None:
        shell = FakeShell(responses={"which crontab": ShellResult(0, "/usr/bin/crontab")})
        assert CrontabScheduler(shell=shell).is_available()

    def test_not_available(self) -> None:
        shell = FakeShell(responses={"which crontab": ShellResult(1)})
        assert not CrontabScheduler(shell=shell).is_available()

    def test_enable_creates_entry(self) -> None:
        shell = FakeShell(
            responses={
                "crontab -l": ShellResult(0, ""),
            }
        )
        sched = CrontabScheduler(shell=shell)
        entry = sched.enable("jq", "0 1 * * *", "proviso sync jq")

        assert entry.resource_name == "jq"
        assert entry.platform == "crontab"
        # Verify crontab was written
        set_cmds = [c for c in shell.commands_run if "crontab -" in c and "crontab -l" not in c]
        assert len(set_cmds) > 0
        # The written content should contain our marker
        assert any("# proviso:jq" in c for c in shell.commands_run)

    def test_enable_preserves_existing(self) -> None:
        existing = "0 5 * * * /usr/bin/backup"
        shell = FakeShell(
            responses={
                "crontab -l": ShellResult(0, existing),
            }
        )
        sched = CrontabScheduler(shell=shell)
        sched.enable("jq", "0 1 * * *", "proviso sync jq")

        # The set command should contain both the existing and new entry
        set_cmds = [c for c in shell.commands_run if "crontab -" in c and "crontab -l" not in c]
        assert any("backup" in c and "proviso:jq" in c for c in set_cmds)

    def test_disable_removes_entry(self) -> None:
        existing = "0 1 * * * proviso sync jq # proviso:jq\n0 5 * * * /usr/bin/backup"
        shell = FakeShell(
            responses={
                "crontab -l": ShellResult(0, existing),
            }
        )
        sched = CrontabScheduler(shell=shell)
        assert sched.disable("jq") is True

        # The remaining crontab should not contain the jq entry
        set_cmds = [c for c in shell.commands_run if "crontab -" in c and "crontab -l" not in c]
        assert any("backup" in c for c in set_cmds)
        # But should not contain proviso:jq
        assert not any("proviso:jq" in c for c in set_cmds if "backup" in c)

    def test_disable_nonexistent(self) -> None:
        shell = FakeShell(
            responses={
                "crontab -l": ShellResult(0, ""),
            }
        )
        sched = CrontabScheduler(shell=shell)
        assert sched.disable("jq") is False

    def test_status_found(self) -> None:
        existing = "0 1 * * * proviso sync jq # proviso:jq"
        shell = FakeShell(
            responses={
                "crontab -l": ShellResult(0, existing),
            }
        )
        sched = CrontabScheduler(shell=shell)
        entry = sched.status("jq")
        assert entry is not None
        assert entry.schedule == "0 1 * * *"

    def test_status_not_found(self) -> None:
        shell = FakeShell(
            responses={
                "crontab -l": ShellResult(0, ""),
            }
        )
        sched = CrontabScheduler(shell=shell)
        assert sched.status("jq") is None

    def test_list_entries(self) -> None:
        existing = (
            "0 1 * * * proviso sync jq # proviso:jq\n"
            "0 2 * * * proviso sync rg # proviso:rg\n"
            "0 5 * * * /usr/bin/backup"
        )
        shell = FakeShell(
            responses={
                "crontab -l": ShellResult(0, existing),
            }
        )
        sched = CrontabScheduler(shell=shell)
        entries = sched.list_entries()
        assert len(entries) == 2
        names = {e.resource_name for e in entries}
        assert names == {"jq", "rg"}


class TestLaunchdCalendarConversion:
    def test_simple_daily(self) -> None:
        result = _cron_to_launchd_calendar("0 1 * * *")
        assert result == {"Minute": 0, "Hour": 1}

    def test_weekly(self) -> None:
        result = _cron_to_launchd_calendar("0 3 * * 0")
        assert result == {"Minute": 0, "Hour": 3, "Weekday": 0}

    def test_every_n_hours(self) -> None:
        result = _cron_to_launchd_calendar("0 */12 * * *")
        assert result == {"Minute": 0, "Hour": 12}

    def test_specific_day(self) -> None:
        result = _cron_to_launchd_calendar("30 2 15 * *")
        assert result == {"Minute": 30, "Hour": 2, "Day": 15}

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Expected 5-field"):
            _cron_to_launchd_calendar("bad")


class TestScheduleEntry:
    def test_frozen(self) -> None:
        entry = ScheduleEntry(
            resource_name="jq",
            schedule="0 1 * * *",
            command="proviso sync jq",
            platform="crontab",
            location="crontab -l",
        )
        assert entry.enabled is True
        with pytest.raises(AttributeError):
            entry.enabled = False  # type: ignore[misc]
