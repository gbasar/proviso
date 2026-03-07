"""Go package provider."""

from __future__ import annotations

from proviso.providers.protocol import PackageStatus, ProviderResult
from proviso.shell.protocol import Shell


class GoProvider:
    """Adapter for go install."""

    def __init__(self, shell: Shell) -> None:
        self._shell = shell

    @property
    def provider_name(self) -> str:
        return "go"

    def is_available(self) -> bool:
        return self._shell.run("which go").success

    def _binary_name(self, package_name: str) -> str:
        # github.com/jesseduffield/lazygit → lazygit
        return package_name.rstrip("/").split("/")[-1]

    def status(self, package_name: str) -> ProviderResult:
        binary = self._binary_name(package_name)
        result = self._shell.run(f"which {binary}")
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED)
        return ProviderResult(status=PackageStatus.MISSING)

    def install(self, package_name: str) -> ProviderResult:
        result = self._shell.run(
            f"GOPATH=/go-build GOBIN=/usr/local/bin go install {package_name}@latest"
        )
        if result.success:
            return ProviderResult(status=PackageStatus.INSTALLED, message="installed")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)

    def update(self, package_name: str) -> ProviderResult:
        return self.install(package_name)

    def remove(self, package_name: str) -> ProviderResult:
        binary = self._binary_name(package_name)
        result = self._shell.run(f"rm -f /usr/local/bin/{binary}")
        if result.success:
            return ProviderResult(status=PackageStatus.MISSING, message="removed")
        return ProviderResult(status=PackageStatus.UNKNOWN, message=result.stderr)
