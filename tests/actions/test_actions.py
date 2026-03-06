"""Action tests — real domain objects, fake shell at the boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from proviso.actions import (
    ActionStatus,
    GitSync,
    PackageInstall,
    ShapeMismatchError,
)
from proviso.providers import DnfProvider, PipProvider, ProviderRegistry
from proviso.resources import BinaryResource, FileResource, LibraryResource, SourceResource
from proviso.shell import FakeShell, ShellResult

# --- Helpers ---


def _make_provider_registry(shell: FakeShell) -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(DnfProvider(shell=shell))
    reg.register(PipProvider(shell=shell))
    return reg


# --- PackageInstall ---


class TestPackageInstall:
    def test_install_missing_binary(self) -> None:
        shell = FakeShell(
            responses={
                "rpm -q jq": ShellResult(1),
                "dnf install -y jq": ShellResult(0),
            }
        )
        action = PackageInstall(providers=_make_provider_registry(shell))
        resource = BinaryResource(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = action.execute(resource)

        assert result.status == ActionStatus.SUCCESS
        assert result.resource_name == "jq"
        assert "dnf install -y jq" in shell.commands_run

    def test_skip_already_installed(self) -> None:
        shell = FakeShell(responses={"rpm -q jq": ShellResult(0, "jq-1.6")})
        action = PackageInstall(providers=_make_provider_registry(shell))
        resource = BinaryResource(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = action.execute(resource)

        assert result.status == ActionStatus.SKIPPED
        assert len(shell.commands_run) == 1

    def test_update_when_get_latest(self) -> None:
        shell = FakeShell(responses={"dnf update -y jq": ShellResult(0)})
        action = PackageInstall(providers=_make_provider_registry(shell))
        resource = BinaryResource(
            name="jq",
            provider="dnf",
            destination=Path("/usr/bin"),
            get_latest=True,
        )

        result = action.execute(resource)

        assert result.status == ActionStatus.SUCCESS
        assert "dnf update -y jq" in shell.commands_run

    def test_install_library_via_pip(self) -> None:
        shell = FakeShell(
            responses={
                "pip show requests": ShellResult(1),
                "pip install requests": ShellResult(0),
            }
        )
        action = PackageInstall(providers=_make_provider_registry(shell))
        resource = LibraryResource(name="requests", provider="pip")

        result = action.execute(resource)

        assert result.status == ActionStatus.SUCCESS

    def test_failed_install(self) -> None:
        shell = FakeShell(
            responses={
                "rpm -q jq": ShellResult(1),
                "dnf install -y jq": ShellResult(1, "", "no such package"),
            }
        )
        action = PackageInstall(providers=_make_provider_registry(shell))
        resource = BinaryResource(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = action.execute(resource)

        assert result.status == ActionStatus.FAILED

    def test_shape_mismatch(self) -> None:
        shell = FakeShell()
        action = PackageInstall(providers=_make_provider_registry(shell))
        resource = FileResource(name="hosts", path=Path("/etc/hosts"))

        with pytest.raises(ShapeMismatchError):
            action.execute(resource)

    def test_shape_mismatch_source(self) -> None:
        shell = FakeShell()
        action = PackageInstall(providers=_make_provider_registry(shell))
        resource = SourceResource(name="app", repo="git@x", target=Path("/opt"))

        with pytest.raises(ShapeMismatchError):
            action.execute(resource)


# --- GitSync ---


class TestGitSync:
    def test_clone_new_repo(self) -> None:
        shell = FakeShell(
            responses={
                "test -d /opt/app/.git": ShellResult(1),
                "git clone --branch main git@github.com:org/app.git /opt/app": ShellResult(0),
            }
        )
        action = GitSync(shell=shell)
        resource = SourceResource(
            name="app",
            repo="git@github.com:org/app.git",
            target=Path("/opt/app"),
        )

        result = action.execute(resource)

        assert result.status == ActionStatus.SUCCESS
        assert result.message == "cloned"

    def test_pull_existing_repo(self) -> None:
        shell = FakeShell(
            responses={
                "test -d /opt/app/.git": ShellResult(0),
                "git -C /opt/app fetch origin && git -C /opt/app pull origin main": ShellResult(0),
            }
        )
        action = GitSync(shell=shell)
        resource = SourceResource(
            name="app",
            repo="git@github.com:org/app.git",
            target=Path("/opt/app"),
        )

        result = action.execute(resource)

        assert result.status == ActionStatus.SUCCESS
        assert result.message == "pulled"

    def test_clone_with_compile(self) -> None:
        shell = FakeShell(
            responses={
                "test -d /opt/app/.git": ShellResult(1),
                "git clone --branch main git@github.com:org/app.git /opt/app": ShellResult(0),
                "cd /opt/app && make install": ShellResult(0),
            }
        )
        action = GitSync(shell=shell)
        resource = SourceResource(
            name="app",
            repo="git@github.com:org/app.git",
            target=Path("/opt/app"),
            compile_cmd="make install",
        )

        result = action.execute(resource)

        assert result.status == ActionStatus.SUCCESS
        assert "cd /opt/app && make install" in shell.commands_run

    def test_compile_failure(self) -> None:
        shell = FakeShell(
            responses={
                "test -d /opt/app/.git": ShellResult(1),
                "git clone --branch main git@github.com:org/app.git /opt/app": ShellResult(0),
                "cd /opt/app && make install": ShellResult(1, "", "make: error"),
            }
        )
        action = GitSync(shell=shell)
        resource = SourceResource(
            name="app",
            repo="git@github.com:org/app.git",
            target=Path("/opt/app"),
            compile_cmd="make install",
        )

        result = action.execute(resource)

        assert result.status == ActionStatus.FAILED
        assert "compile failed" in result.message

    def test_shape_mismatch(self) -> None:
        action = GitSync(shell=FakeShell())
        resource = BinaryResource(name="jq", provider="dnf", destination=Path("/usr/bin"))

        with pytest.raises(ShapeMismatchError):
            action.execute(resource)

    def test_shape_mismatch_file(self) -> None:
        action = GitSync(shell=FakeShell())
        resource = FileResource(name="hosts", path=Path("/etc/hosts"))

        with pytest.raises(ShapeMismatchError):
            action.execute(resource)
