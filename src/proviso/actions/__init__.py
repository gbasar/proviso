"""Actions — anything that operates on a resource."""

from proviso.actions.git_sync import GitSync
from proviso.actions.package_install import PackageInstall
from proviso.actions.pipeline import FailMode, Pipeline, PipelineResult
from proviso.actions.protocol import Action, ActionResult, ActionStatus, ShapeMismatchError

__all__ = [
    "Action",
    "ActionResult",
    "ActionStatus",
    "FailMode",
    "GitSync",
    "PackageInstall",
    "Pipeline",
    "PipelineResult",
    "ShapeMismatchError",
]
