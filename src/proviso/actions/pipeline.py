"""Pipeline — composable chain of actions applied to a resource.

A pipeline is itself an Action, so pipelines can nest.
Fail mode controls whether to stop on first failure or continue.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from proviso.actions.protocol import ActionResult, ActionStatus, ShapeMismatchError


class FailMode(StrEnum):
    FAST = "fast"
    CONTINUE = "continue"


@dataclass(frozen=True)
class PipelineResult:
    status: ActionStatus
    pipeline_name: str
    resource_name: str
    results: tuple[ActionResult, ...] = ()
    message: str = ""


class Pipeline:
    """Ordered chain of actions. Resource flows through each one."""

    def __init__(
        self,
        name: str,
        actions: list[Any],
        fail_mode: FailMode = FailMode.FAST,
    ) -> None:
        self._name = name
        self._actions = actions
        self._fail_mode = fail_mode

    @property
    def action_name(self) -> str:
        return self._name

    def execute(self, resource: Any) -> PipelineResult:
        results: list[ActionResult] = []
        failed = False

        for action in self._actions:
            try:
                result = action.execute(resource)
            except ShapeMismatchError as e:
                result = ActionResult(
                    status=ActionStatus.FAILED,
                    action_name=action.action_name,
                    resource_name=getattr(resource, "name", "unknown"),
                    message=str(e),
                )

            results.append(result)

            if result.status == ActionStatus.FAILED:
                failed = True
                if self._fail_mode == FailMode.FAST:
                    break

        return PipelineResult(
            status=ActionStatus.FAILED if failed else ActionStatus.SUCCESS,
            pipeline_name=self._name,
            resource_name=getattr(resource, "name", "unknown"),
            results=tuple(results),
        )
