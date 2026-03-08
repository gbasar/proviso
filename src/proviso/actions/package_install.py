"""PackageInstall action — installs or updates any package provision.

Accepts PackageProvision. Resolves provider by name,
delegates the actual work. Idempotent — checks status first.
"""

from __future__ import annotations

from proviso.actions.protocol import ActionResult, ActionStatus, ShapeMismatchError
from proviso.providers.protocol import PackageStatus
from proviso.providers.registry import ProviderRegistry
from proviso.provisions.models import PackageProvision
from proviso.shell.protocol import Shell


class PackageInstall:
    """Install or update a package via its declared provider."""

    def __init__(self, providers: ProviderRegistry, shell: Shell) -> None:
        self._providers = providers
        self._shell = shell

    @property
    def action_name(self) -> str:
        return "package-install"

    def execute(self, provision: PackageProvision) -> ActionResult:
        if not isinstance(provision, PackageProvision):
            raise ShapeMismatchError(
                f"{self.action_name} accepts PackageProvision, got {type(provision).__name__}"
            )

        provider = self._providers.get(provision.provider)
        name = provision.name
        package = provision.package or name

        if provision.get_latest:
            result = provider.update(package)
        else:
            current = provider.status(package)
            if current.status == PackageStatus.INSTALLED:
                return ActionResult(
                    status=ActionStatus.SKIPPED,
                    action_name=self.action_name,
                    resource_name=name,
                    message="already installed",
                )
            result = provider.install(package)

        if result.status == PackageStatus.INSTALLED:
            if provision.post_install:
                post = self._shell.run(provision.post_install)
                if not post.success:
                    return ActionResult(
                        status=ActionStatus.FAILED,
                        action_name=self.action_name,
                        resource_name=name,
                        message=f"post_install failed: {post.stderr}",
                    )
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
