"""Action tests — real domain objects, fake shell at the boundary."""

from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from proviso.actions import (
    ActionStatus,
    GitSync,
    PackageInstall,
    ShapeMismatchError,
)
from proviso.providers import DnfProvider, PipProvider, ProviderRegistry
from proviso.provisions import FileProvision, PackageProvision, SourceProvision
from proviso.provisions.models import Symlink
from proviso.shell import FakeShell, ShellResult

# --- Helpers ---


def _make_provider_registry(shell: FakeShell) -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(DnfProvider(shell=shell))
    reg.register(PipProvider(shell=shell))
    return reg


def _make_action(shell: FakeShell | None = None) -> PackageInstall:
    shell = shell or FakeShell()
    return PackageInstall(providers=_make_provider_registry(shell), shell=shell)


def _make_tar_gz(dest: Path, binary_name: str) -> Path:
    """Create a minimal .tar.gz containing a single executable file."""
    binary = dest.parent / binary_name
    binary.write_bytes(b"#!/bin/sh\necho hello")
    binary.chmod(0o755)
    archive = dest
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(binary, arcname=binary_name)
    binary.unlink()
    return archive


def _symlink(frm: str, to: str) -> Symlink:
    return Symlink(**{"from": frm, "to": to})


# --- PackageInstall ---


class TestPackageInstall:
    def test_install_missing_binary(self) -> None:
        shell = FakeShell(
            responses={
                "rpm -q jq": ShellResult(1),
                "dnf install -y jq": ShellResult(0),
            }
        )
        action = _make_action(shell)
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = action.execute(provision)

        assert result.status == ActionStatus.SUCCESS
        assert result.resource_name == "jq"
        assert "dnf install -y jq" in shell.commands_run

    def test_skip_already_installed(self) -> None:
        shell = FakeShell(responses={"rpm -q jq": ShellResult(0, "jq-1.6")})
        action = _make_action(shell)
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = action.execute(provision)

        assert result.status == ActionStatus.SKIPPED
        assert len(shell.commands_run) == 1

    def test_update_when_get_latest(self) -> None:
        shell = FakeShell(responses={"dnf update -y jq": ShellResult(0)})
        action = _make_action(shell)
        provision = PackageProvision(
            name="jq",
            provider="dnf",
            destination=Path("/usr/bin"),
            get_latest=True,
        )

        result = action.execute(provision)

        assert result.status == ActionStatus.SUCCESS
        assert "dnf update -y jq" in shell.commands_run

    def test_install_library_via_pip(self) -> None:
        shell = FakeShell(
            responses={
                "python3 -m pip show requests": ShellResult(1),
                "python3 -m pip install requests": ShellResult(0),
            }
        )
        action = _make_action(shell)
        provision = PackageProvision(name="requests", provider="pip")

        result = action.execute(provision)

        assert result.status == ActionStatus.SUCCESS

    def test_failed_install(self) -> None:
        shell = FakeShell(
            responses={
                "rpm -q jq": ShellResult(1),
                "dnf install -y jq": ShellResult(1, "", "no such package"),
            }
        )
        action = _make_action(shell)
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        result = action.execute(provision)

        assert result.status == ActionStatus.FAILED

    def test_shape_mismatch(self) -> None:
        action = _make_action()
        provision = FileProvision(name="hosts", destination=Path("/etc/hosts"))

        with pytest.raises(ShapeMismatchError):
            action.execute(provision)

    def test_shape_mismatch_source(self) -> None:
        action = _make_action()
        provision = SourceProvision(name="app", repo="git@github.com:org/x.git", destination=Path("/opt"))

        with pytest.raises(ShapeMismatchError):
            action.execute(provision)


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
        provision = SourceProvision(
            name="app",
            repo="git@github.com:org/app.git",
            destination=Path("/opt/app"),
        )

        result = action.execute(provision)

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
        provision = SourceProvision(
            name="app",
            repo="git@github.com:org/app.git",
            destination=Path("/opt/app"),
        )

        result = action.execute(provision)

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
        provision = SourceProvision(
            name="app",
            repo="git@github.com:org/app.git",
            destination=Path("/opt/app"),
            compile_cmd="make install",
        )

        result = action.execute(provision)

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
        provision = SourceProvision(
            name="app",
            repo="git@github.com:org/app.git",
            destination=Path("/opt/app"),
            compile_cmd="make install",
        )

        result = action.execute(provision)

        assert result.status == ActionStatus.FAILED
        assert "compile failed" in result.message

    def test_shape_mismatch(self) -> None:
        action = GitSync(shell=FakeShell())
        provision = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))

        with pytest.raises(ShapeMismatchError):
            action.execute(provision)

    def test_shape_mismatch_file(self) -> None:
        action = GitSync(shell=FakeShell())
        provision = FileProvision(name="hosts", destination=Path("/etc/hosts"))

        with pytest.raises(ShapeMismatchError):
            action.execute(provision)


# --- FileInstall (method=file) ---


class TestFileInstall:
    def test_missing_loc_fails(self, tmp_path: Path) -> None:
        link_dest = tmp_path / "bin" / "mytool"
        provision = PackageProvision(
            name="mytool", provider="file",
            destination=tmp_path,
            symlinks=(_symlink("mytool", str(link_dest)),),
        )
        result = _make_action().execute(provision)
        assert result.status == ActionStatus.FAILED
        assert "loc" in result.message

    def test_src_not_found_fails(self, tmp_path: Path) -> None:
        link_dest = tmp_path / "bin" / "mytool"
        provision = PackageProvision(
            name="mytool", provider="file",
            loc=str(tmp_path / "missing.tar.gz"),
            destination=tmp_path / "install",
            symlinks=(_symlink("mytool", str(link_dest)),),
        )
        result = _make_action().execute(provision)
        assert result.status == ActionStatus.FAILED
        assert "not found" in result.message

    def test_extracts_tar_gz_and_symlinks(self, tmp_path: Path) -> None:
        archive = _make_tar_gz(tmp_path / "mytool.tar.gz", "mytool")
        install_dir = tmp_path / "install"
        link_dest = tmp_path / "bin" / "mytool"

        provision = PackageProvision(
            name="mytool", provider="file",
            loc=str(archive),
            destination=install_dir,
            symlinks=(_symlink("mytool", str(link_dest)),),
        )
        result = _make_action().execute(provision)

        assert result.status == ActionStatus.SUCCESS
        assert link_dest.is_symlink()
        assert link_dest.resolve().name == "mytool"

    def test_skips_if_symlink_targets_exist(self, tmp_path: Path) -> None:
        archive = _make_tar_gz(tmp_path / "mytool.tar.gz", "mytool")
        link_dest = tmp_path / "bin" / "mytool"
        link_dest.parent.mkdir(parents=True)
        link_dest.write_text("already here")

        provision = PackageProvision(
            name="mytool", provider="file",
            loc=str(archive),
            destination=tmp_path / "install",
            symlinks=(_symlink("mytool", str(link_dest)),),
        )
        result = _make_action().execute(provision)

        assert result.status == ActionStatus.SKIPPED

    def test_binary_not_in_archive_fails(self, tmp_path: Path) -> None:
        archive = _make_tar_gz(tmp_path / "mytool.tar.gz", "mytool")
        link_dest = tmp_path / "bin" / "other"

        provision = PackageProvision(
            name="mytool", provider="file",
            loc=str(archive),
            destination=tmp_path / "install",
            symlinks=(_symlink("other", str(link_dest)),),
        )
        result = _make_action().execute(provision)

        assert result.status == ActionStatus.FAILED
        assert "not found in archive" in result.message

    def test_post_install_runs_on_success(self, tmp_path: Path) -> None:
        archive = _make_tar_gz(tmp_path / "mytool.tar.gz", "mytool")
        link_dest = tmp_path / "bin" / "mytool"
        shell = FakeShell(responses={"echo done": ShellResult(0)})

        provision = PackageProvision(
            name="mytool", provider="file",
            loc=str(archive),
            destination=tmp_path / "install",
            symlinks=(_symlink("mytool", str(link_dest)),),
            post_install="echo done",
        )
        result = _make_action(shell).execute(provision)

        assert result.status == ActionStatus.SUCCESS
        assert "echo done" in shell.commands_run

    def test_post_install_failure_reported(self, tmp_path: Path) -> None:
        archive = _make_tar_gz(tmp_path / "mytool.tar.gz", "mytool")
        link_dest = tmp_path / "bin" / "mytool"
        shell = FakeShell(responses={"bad cmd": ShellResult(1, "", "oops")})

        provision = PackageProvision(
            name="mytool", provider="file",
            loc=str(archive),
            destination=tmp_path / "install",
            symlinks=(_symlink("mytool", str(link_dest)),),
            post_install="bad cmd",
        )
        result = _make_action(shell).execute(provision)

        assert result.status == ActionStatus.FAILED
        assert "post_install failed" in result.message
