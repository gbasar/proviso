"""Provision model tests.

Covers: construction, immutability, Protocol conformance,
discriminated union deserialization, registry loading,
filtering, and round-trip through markup subsystem.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from proviso.markup import create_default_registry
from proviso.provisions import (
    FileProvision,
    PackageProvision,
    Provisionlike,
    ProvisionRegistry,
    SourceProvision,
)

from .conftest import SAMPLE_MANIFEST


class TestConstruction:
    """Provisions construct with correct defaults and required fields."""

    def test_package_provision_binary(self) -> None:
        r = PackageProvision(name="jq", provider="dnf", destination=Path("/usr/bin"))
        assert r.name == "jq"
        assert r.provision_type == "package"
        assert r.provider == "dnf"
        assert r.destination == Path("/usr/bin")
        assert r.symlinks == ()
        assert r.get_latest is False
        assert r.schedule is None

    def test_package_provision_library(self) -> None:
        r = PackageProvision(name="requests", provider="pip", version="2.31.0")
        assert r.provision_type == "package"
        assert r.version == "2.31.0"
        assert r.destination is None

    def test_source_provision(self) -> None:
        r = SourceProvision(
            name="my-app",
            repo="git@github.com:org/app.git",
            destination=Path("/opt/app"),
        )
        assert r.provision_type == "source"
        assert r.branch == "main"
        assert r.compile_cmd is None

    def test_file_provision(self) -> None:
        r = FileProvision(name="hosts", destination=Path("/etc/hosts"))
        assert r.provision_type == "file"
        assert r.mode is None

    def test_file_provision_symlink(self) -> None:
        r = FileProvision(
            name="dotfile",
            destination=Path("~/.bashrc"),
            src=Path("/opt/dotfiles/.bashrc"),
            mode="SYMLINK",
        )
        assert r.mode == "SYMLINK"
        assert r.src == Path("/opt/dotfiles/.bashrc")


class TestImmutability:
    """Frozen models reject mutation."""

    def test_cannot_mutate_package(self) -> None:
        r = PackageProvision(name="jq", provider="dnf")
        with pytest.raises(ValidationError):
            r.name = "other"  # type: ignore[misc]

    def test_cannot_mutate_file(self) -> None:
        r = FileProvision(name="hosts", destination=Path("/etc/hosts"))
        with pytest.raises(ValidationError):
            r.destination = Path("/other")  # type: ignore[misc]


class TestProtocolConformance:
    """All provision types satisfy Provisionlike Protocol."""

    def test_package_is_provisionlike(self) -> None:
        r = PackageProvision(name="jq", provider="dnf")
        assert isinstance(r, Provisionlike)

    def test_source_is_provisionlike(self) -> None:
        r = SourceProvision(name="app", repo="git@github.com:org/x.git", destination=Path("/opt"))
        assert isinstance(r, Provisionlike)

    def test_file_is_provisionlike(self) -> None:
        r = FileProvision(name="hosts", destination=Path("/etc/hosts"))
        assert isinstance(r, Provisionlike)


class TestExtraFieldsRejected:
    """Strict models reject unknown fields."""

    def test_package_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            PackageProvision(name="jq", provider="dnf", bogus="nope")

    def test_file_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            FileProvision(name="hosts", destination=Path("/etc/hosts"), bogus="nope")


class TestRegistryLoading:
    """ProvisionRegistry loads manifests and resolves provisions."""

    def test_load_dict(self) -> None:
        reg = ProvisionRegistry()
        reg.load_dict(SAMPLE_MANIFEST)
        assert len(reg.provisions) == 5

    def test_get_typed_provision(self) -> None:
        reg = ProvisionRegistry()
        reg.load_dict(SAMPLE_MANIFEST)

        jq = reg.get("jq")
        assert isinstance(jq, PackageProvision)
        assert jq.provider == "dnf"

        hosts = reg.get("trading-hosts")
        assert isinstance(hosts, FileProvision)

    def test_unknown_provision_raises(self) -> None:
        reg = ProvisionRegistry()
        reg.load_dict(SAMPLE_MANIFEST)
        with pytest.raises(ValueError, match="Unknown provision"):
            reg.get("nonexistent")

    def test_filter_by_type(self) -> None:
        reg = ProvisionRegistry()
        reg.load_dict(SAMPLE_MANIFEST)

        files = reg.filter_by_type("file")
        assert len(files) == 2
        assert "trading-hosts" in files
        assert "deploy-key" in files

    def test_filter_by_tag(self) -> None:
        reg = ProvisionRegistry()
        reg.load_dict(SAMPLE_MANIFEST)

        ssh = reg.filter_by_tag("ssh")
        assert len(ssh) == 1
        assert "deploy-key" in ssh

    def test_scheduled(self) -> None:
        reg = ProvisionRegistry()
        reg.load_dict(SAMPLE_MANIFEST)

        scheduled = reg.scheduled()
        assert "jq" in scheduled
        assert "my-app" in scheduled
        assert "trading-hosts" not in scheduled


class TestDiscriminatedUnion:
    """Pydantic correctly discriminates provision_type."""

    def test_invalid_type_rejected(self) -> None:
        reg = ProvisionRegistry()
        with pytest.raises(ValidationError):
            reg.load_dict({"provisions": {"bad": {"provision_type": "spaceship"}}})

    def test_missing_required_field(self) -> None:
        reg = ProvisionRegistry()
        with pytest.raises(ValidationError):
            reg.load_dict({"provisions": {"jq": {"provision_type": "package"}}})
            # missing provider


class TestMarkupRoundTrip:
    """Provisions survive serialization through the markup subsystem."""

    def test_manifest_through_json(self, tmp_path: Path) -> None:
        markup = create_default_registry()
        manifest_path = tmp_path / "manifest.json"

        markup.write_file(SAMPLE_MANIFEST, manifest_path)

        reg = ProvisionRegistry()
        reg.load_file(manifest_path, markup)

        jq = reg.get("jq")
        assert isinstance(jq, PackageProvision)
        assert jq.get_latest is True
        assert jq.schedule == "0 1 * * *"

    def test_manifest_through_yaml(self, tmp_path: Path) -> None:
        markup = create_default_registry()
        manifest_path = tmp_path / "manifest.yaml"

        markup.write_file(SAMPLE_MANIFEST, manifest_path)

        reg = ProvisionRegistry()
        reg.load_file(manifest_path, markup)

        app = reg.get("my-app")
        assert isinstance(app, SourceProvision)
        assert app.compile_cmd == "make install"
        assert app.repo == "git@github.com:myorg/my-app.git"

    def test_manifest_through_hocon(self, tmp_path: Path) -> None:
        markup = create_default_registry()
        manifest_path = tmp_path / "manifest.conf"

        markup.write_file(SAMPLE_MANIFEST, manifest_path)

        reg = ProvisionRegistry()
        reg.load_file(manifest_path, markup)

        assert len(reg.provisions) == 5
