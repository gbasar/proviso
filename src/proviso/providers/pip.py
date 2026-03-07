"""Pip package provider."""

from __future__ import annotations

from proviso.providers.protocol import PackageStatus, ProviderResult
from proviso.shell.protocol import Shell


class PipProvider:
    """Adapter for pip (Python packages)."""

    def __init__(self, shell: Shell) -> None:
        self._shell = shell

    @property
    def provider_name(self) -> str:
        return "pip"

    def is_available(self) -> bool:
        return self._shell.run("python3 -m pip --version").success

    def status(self, package_name: str) -> ProviderResult:
        result = self._shell.run(f"python3 -m pip show {package_name}")
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED, version=result.stdout)
        return ProviderResult(status=PackageStatus.MISSING)

    def install(self, package_name: str) -> ProviderResult:
        current = self.status(package_name)
        if current.status == PackageStatus.INSTALLED:
            return ProviderResult(status=PackageStatus.INSTALLED, message="already installed")
        result = self._shell.run(f"python3 -m pip install {package_name}")
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED, message="installed")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)

    def update(self, package_name: str) -> ProviderResult:
        result = self._shell.run(f"python3 -m pip install --upgrade {package_name}")
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED, message="updated")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)

    def remove(self, package_name: str) -> ProviderResult:
        result = self._shell.run(f"python3 -m pip uninstall -y {package_name}")
        if result.success:
            return ProviderResult(status=PackageStatus.MISSING, message="removed")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)
