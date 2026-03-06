"""Scheduler abstraction — platform-specific schedule adapters."""

from proviso.scheduler.crontab import CrontabScheduler
from proviso.scheduler.fake import FakeScheduler
from proviso.scheduler.launchd import LaunchdScheduler
from proviso.scheduler.protocol import ScheduleEntry, Scheduler

__all__ = [
    "CrontabScheduler",
    "FakeScheduler",
    "LaunchdScheduler",
    "ScheduleEntry",
    "Scheduler",
]
