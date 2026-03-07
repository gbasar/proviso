"""GitSync action — clones or pulls a git repository.

Accepts SourceProvision. Idempotent — clones if missing, pulls if present.
Optionally runs compile command after sync.
"""

from __future__ import annotations

from proviso.actions.protocol import ActionResult, ActionStatus, ShapeMismatchError
from proviso.provisions.models import SourceProvision
from proviso.shell.protocol import Shell


class GitSync:
    """Clone or pull a git repository."""

    def __init__(self, shell: Shell) -> None:
        self._shell = shell

    @property
    def action_name(self) -> str:
        return "git-sync"

    def execute(self, provision: SourceProvision) -> ActionResult:
        if not isinstance(provision, SourceProvision):
            raise ShapeMismatchError(
                f"{self.action_name} accepts SourceProvision, got {type(provision).__name__}"
            )

        target = str(provision.target)
        exists = self._shell.run(f"test -d {target}/.git")

        if exists.success:
            result = self._shell.run(
                f"git -C {target} fetch origin && git -C {target} pull origin {provision.branch}"
            )
            verb = "pulled"
        else:
            result = self._shell.run(
                f"git clone --branch {provision.branch} {provision.repo} {target}"
            )
            verb = "cloned"

        if not result.success:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.action_name,
                resource_name=provision.name,
                message=result.stderr,
            )

        if provision.compile_cmd:
            compile_result = self._shell.run(f"cd {target} && {provision.compile_cmd}")
            if not compile_result.success:
                return ActionResult(
                    status=ActionStatus.FAILED,
                    action_name=self.action_name,
                    resource_name=provision.name,
                    message=f"{verb} but compile failed: {compile_result.stderr}",
                )

        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.action_name,
            resource_name=provision.name,
            message=verb,
        )
