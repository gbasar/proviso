"""Cargo package provider."""

from __future__ import annotations

from proviso.commons import maybe_sudo
from proviso.providers.protocol import PackageStatus, ProviderResult
from proviso.shell.protocol import Shell


class CargoProvider:
    """Adapter for cargo (Rust crates)."""

    def __init__(self, shell: Shell) -> None:
        self._shell = shell

    @property
    def provider_name(self) -> str:
        return "cargo"

    def is_available(self) -> bool:
        return self._shell.run("which cargo").success

    def status(self, package_name: str) -> ProviderResult:
        result = self._shell.run("cargo install --list --root /usr/local")
        if result.success and f"\n{package_name} v" in f"\n{result.stdout}":
            return ProviderResult(status=PackageStatus.INSTALLED)
        return ProviderResult(status=PackageStatus.MISSING)

    def install(self, package_name: str) -> ProviderResult:
        result = self._shell.run(
            maybe_sudo(f"cargo install --locked --root /usr/local {package_name}")
        )
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED, message="installed")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)

    def update(self, package_name: str) -> ProviderResult:
        result = self._shell.run(
            maybe_sudo(f"cargo install --locked --root /usr/local {package_name}")
        )
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED, message="updated")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)

    def remove(self, package_name: str) -> ProviderResult:
        result = self._shell.run(f"cargo uninstall {package_name}")
        if result.success:
            return ProviderResult(status=PackageStatus.MISSING, message="removed")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)
