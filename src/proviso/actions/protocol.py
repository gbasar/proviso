"""Action port — anything that operates on a resource.

Actions declare what resource shape they accept.
They check shape, act, and return a result.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class ActionStatus(StrEnum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class ActionResult:
    status: ActionStatus
    action_name: str
    resource_name: str
    message: str = ""
    details: dict[str, Any] | None = None


class ShapeMismatchError(TypeError):
    """Raised when a resource doesn't match an action's expected shape."""


@runtime_checkable
class Action(Protocol):
    @property
    def action_name(self) -> str: ...

    def execute(self, resource: Any) -> ActionResult: ...
