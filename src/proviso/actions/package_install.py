"""PackageInstall action — installs or updates any package resource.

Accepts PackageResource. Resolves provider by name,
delegates the actual work. Idempotent — checks status first.
"""

from __future__ import annotations

from proviso.actions.protocol import ActionResult, ActionStatus, ShapeMismatchError
from proviso.providers.protocol import PackageStatus
from proviso.providers.registry import ProviderRegistry
from proviso.resources.models import PackageResource


class PackageInstall:
    """Install or update a package via its declared provider."""

    def __init__(self, providers: ProviderRegistry) -> None:
        self._providers = providers

    @property
    def action_name(self) -> str:
        return "package-install"

    def execute(self, resource: PackageResource) -> ActionResult:
        if not isinstance(resource, PackageResource):
            raise ShapeMismatchError(
                f"{self.action_name} accepts PackageResource, got {type(resource).__name__}"
            )

        provider = self._providers.get(resource.provider)
        name = resource.name

        if resource.get_latest:
            result = provider.update(name)
        else:
            current = provider.status(name)
            if current.status == PackageStatus.INSTALLED:
                return ActionResult(
                    status=ActionStatus.SKIPPED,
                    action_name=self.action_name,
                    resource_name=name,
                    message="already installed",
                )
            result = provider.install(name)

        if result.status == PackageStatus.INSTALLED:
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action_name=self.action_name,
                resource_name=name,
                message=result.message,
            )

        return ActionResult(
            status=ActionStatus.FAILED,
            action_name=self.action_name,
            resource_name=name,
            message=result.message,
        )
