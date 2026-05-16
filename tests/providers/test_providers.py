"""Provider tests — scripted shell responses, no real package managers."""

from __future__ import annotations

import pytest

from proviso.commons import maybe_sudo
from proviso.providers import (
    AptProvider,
    DnfProvider,
    PackageProvider,
    PackageStatus,
    PipProvider,
    ProviderRegistry,
)
from proviso.shell import FakeShell, ShellResult


class TestDnfProvider:
    def test_protocol_conformance(self) -> None:
        provider = DnfProvider(shell=FakeShell())
        assert isinstance(provider, PackageProvider)

    def test_status_installed(self) -> None:
        shell = FakeShell(responses={"rpm -q jq": ShellResult(0, "jq-1.6-1.fc39")})
        provider = DnfProvider(shell=shell)
        result = provider.status("jq")
        assert result.status == PackageStatus.INSTALLED

    def test_status_missing(self) -> None:
        shell = FakeShell(responses={"rpm -q jq": ShellResult(1, "", "not installed")})
        provider = DnfProvider(shell=shell)
        result = provider.status("jq")
        assert result.status == PackageStatus.MISSING

    def test_install_when_missing(self) -> None:
        shell = FakeShell(
            responses={
                "rpm -q jq": ShellResult(1),
                maybe_sudo("dnf install -y jq"): ShellResult(0),
            }
        )
        provider = DnfProvider(shell=shell)
        result = provider.install("jq")
        assert result.status == PackageStatus.INSTALLED
        assert shell.commands_run == ["rpm -q jq", maybe_sudo("dnf install -y jq")]

    def test_install_idempotent(self) -> None:
        shell = FakeShell(responses={"rpm -q jq": ShellResult(0, "jq-1.6")})
        provider = DnfProvider(shell=shell)
        result = provider.install("jq")
        assert result.message == "already installed"
        assert len(shell.commands_run) == 1  # only status check, no install

    def test_is_available(self) -> None:
        shell = FakeShell(responses={"which dnf": ShellResult(0, "/usr/bin/dnf")})
        assert DnfProvider(shell=shell).is_available()

    def test_is_not_available(self) -> None:
        shell = FakeShell(responses={"which dnf": ShellResult(1)})
        assert not DnfProvider(shell=shell).is_available()


class TestAptProvider:
    def test_protocol_conformance(self) -> None:
        assert isinstance(AptProvider(shell=FakeShell()), PackageProvider)

    def test_status_installed(self) -> None:
        shell = FakeShell(
            responses={
                "dpkg -s curl": ShellResult(0, "Status: install ok installed\nVersion: 7.88"),
            }
        )
        result = AptProvider(shell=shell).status("curl")
        assert result.status == PackageStatus.INSTALLED

    def test_status_missing(self) -> None:
        shell = FakeShell(responses={"dpkg -s curl": ShellResult(1)})
        result = AptProvider(shell=shell).status("curl")
        assert result.status == PackageStatus.MISSING


class TestPipProvider:
    def test_protocol_conformance(self) -> None:
        assert isinstance(PipProvider(shell=FakeShell()), PackageProvider)

    def test_install(self) -> None:
        shell = FakeShell(
            responses={
                "pip show requests": ShellResult(1),
                "pip install requests": ShellResult(0),
            }
        )
        result = PipProvider(shell=shell).install("requests")
        assert result.status == PackageStatus.INSTALLED


class TestProviderRegistry:
    def test_register_and_get(self) -> None:
        reg = ProviderRegistry()
        provider = DnfProvider(shell=FakeShell())
        reg.register(provider)
        assert reg.get("dnf") is provider

    def test_unknown_raises(self) -> None:
        reg = ProviderRegistry()
        with pytest.raises(ValueError, match="Unknown provider"):
            reg.get("brew")

    def test_duplicate_rejected(self) -> None:
        reg = ProviderRegistry()
        reg.register(DnfProvider(shell=FakeShell()))
        with pytest.raises(ValueError, match="already registered"):
            reg.register(DnfProvider(shell=FakeShell()))

    def test_available_filters(self) -> None:
        available_shell = FakeShell(responses={"which dnf": ShellResult(0, "/usr/bin/dnf")})
        missing_shell = FakeShell(responses={"which apt-get": ShellResult(1)})
        reg = ProviderRegistry()
        reg.register(DnfProvider(shell=available_shell))
        reg.register(AptProvider(shell=missing_shell))
        avail = reg.available()
        assert "dnf" in avail
        assert "apt" not in avail
