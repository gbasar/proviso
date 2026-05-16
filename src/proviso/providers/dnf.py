"""DNF package provider."""

from __future__ import annotations

from proviso.commons import maybe_sudo
from proviso.providers.protocol import PackageStatus, ProviderResult
from proviso.shell.protocol import Shell


class DnfProvider:
    """Adapter for DNF (Fedora, RHEL, UBI)."""

    def __init__(self, shell: Shell) -> None:
        self._shell = shell

    @property
    def provider_name(self) -> str:
        return "dnf"

    def is_available(self) -> bool:
        return self._shell.run("which dnf").success

    def status(self, package_name: str) -> ProviderResult:
        result = self._shell.run(f"rpm -q {package_name}")
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED, version=result.stdout)
        return ProviderResult(status=PackageStatus.MISSING)

    def install(self, package_name: str) -> ProviderResult:
        current = self.status(package_name)
        if current.status == PackageStatus.INSTALLED:
            return ProviderResult(status=PackageStatus.INSTALLED, message="already installed")
        result = self._shell.run(maybe_sudo(f"dnf install -y {package_name}"))
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED, message="installed")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)

    def update(self, package_name: str) -> ProviderResult:
        result = self._shell.run(maybe_sudo(f"dnf update -y {package_name}"))
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED, message="updated")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)

    def remove(self, package_name: str) -> ProviderResult:
        result = self._shell.run(maybe_sudo(f"dnf remove -y {package_name}"))
        if result.success:
            return ProviderResult(status=PackageStatus.MISSING, message="removed")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)

    def is_in_repo(self, package_name: str) -> bool:
        """Check if package is available in configured repos without installing it."""
        return self._shell.run(f"dnf info --quiet {package_name}").success
