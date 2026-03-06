"""Resource model tests.

Covers: construction, immutability, Protocol conformance,
discriminated union deserialization, registry loading,
filtering, and round-trip through markup subsystem.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from proviso.markup import create_default_registry
from proviso.resources import (
    FileResource,
    PackageResource,
    Resourcelike,
    ResourceRegistry,
    SourceResource,
)

from .conftest import SAMPLE_MANIFEST


class TestConstruction:
    """Resources construct with correct defaults and required fields."""

    def test_package_resource_binary(self) -> None:
        r = PackageResource(name="jq", provider="dnf", destination=Path("/usr/bin"))
        assert r.name == "jq"
        assert r.resource_type == "package"
        assert r.provider == "dnf"
        assert r.destination == Path("/usr/bin")
        assert r.links == ()
        assert r.get_latest is False
        assert r.schedule is None

    def test_package_resource_library(self) -> None:
        r = PackageResource(name="requests", provider="pip", version="2.31.0")
        assert r.resource_type == "package"
        assert r.version == "2.31.0"
        assert r.destination is None

    def test_source_resource(self) -> None:
        r = SourceResource(
            name="my-app",
            repo="git@github.com:org/app.git",
            target=Path("/opt/app"),
        )
        assert r.resource_type == "source"
        assert r.branch == "main"
        assert r.compile_cmd is None

    def test_file_resource(self) -> None:
        r = FileResource(name="hosts", path=Path("/etc/hosts"))
        assert r.resource_type == "file"
        assert r.symlink is False

    def test_file_resource_symlink(self) -> None:
        r = FileResource(
            name="dotfile",
            path=Path("~/.bashrc"),
            source=Path("/opt/dotfiles/.bashrc"),
            symlink=True,
        )
        assert r.symlink is True
        assert r.source == Path("/opt/dotfiles/.bashrc")


class TestImmutability:
    """Frozen models reject mutation."""

    def test_cannot_mutate_package(self) -> None:
        r = PackageResource(name="jq", provider="dnf")
        with pytest.raises(ValidationError):
            r.name = "other"  # type: ignore[misc]

    def test_cannot_mutate_file(self) -> None:
        r = FileResource(name="hosts", path=Path("/etc/hosts"))
        with pytest.raises(ValidationError):
            r.path = Path("/other")  # type: ignore[misc]


class TestProtocolConformance:
    """All resource types satisfy Resourcelike Protocol."""

    def test_package_is_resourcelike(self) -> None:
        r = PackageResource(name="jq", provider="dnf")
        assert isinstance(r, Resourcelike)

    def test_source_is_resourcelike(self) -> None:
        r = SourceResource(name="app", repo="git@x", target=Path("/opt"))
        assert isinstance(r, Resourcelike)

    def test_file_is_resourcelike(self) -> None:
        r = FileResource(name="hosts", path=Path("/etc/hosts"))
        assert isinstance(r, Resourcelike)


class TestExtraFieldsRejected:
    """Strict models reject unknown fields."""

    def test_package_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            PackageResource(name="jq", provider="dnf", bogus="nope")

    def test_file_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            FileResource(name="hosts", path=Path("/etc/hosts"), bogus="nope")


class TestRegistryLoading:
    """ResourceRegistry loads manifests and resolves resources."""

    def test_load_dict(self) -> None:
        reg = ResourceRegistry()
        reg.load_dict(SAMPLE_MANIFEST)
        assert len(reg.resources) == 5

    def test_get_typed_resource(self) -> None:
        reg = ResourceRegistry()
        reg.load_dict(SAMPLE_MANIFEST)

        jq = reg.get("jq")
        assert isinstance(jq, PackageResource)
        assert jq.provider == "dnf"

        hosts = reg.get("trading-hosts")
        assert isinstance(hosts, FileResource)

    def test_unknown_resource_raises(self) -> None:
        reg = ResourceRegistry()
        reg.load_dict(SAMPLE_MANIFEST)
        with pytest.raises(ValueError, match="Unknown resource"):
            reg.get("nonexistent")

    def test_filter_by_type(self) -> None:
        reg = ResourceRegistry()
        reg.load_dict(SAMPLE_MANIFEST)

        files = reg.filter_by_type("file")
        assert len(files) == 2
        assert "trading-hosts" in files
        assert "deploy-key" in files

    def test_filter_by_tag(self) -> None:
        reg = ResourceRegistry()
        reg.load_dict(SAMPLE_MANIFEST)

        ssh = reg.filter_by_tag("ssh")
        assert len(ssh) == 1
        assert "deploy-key" in ssh

    def test_scheduled(self) -> None:
        reg = ResourceRegistry()
        reg.load_dict(SAMPLE_MANIFEST)

        scheduled = reg.scheduled()
        assert "jq" in scheduled
        assert "my-app" in scheduled
        assert "trading-hosts" not in scheduled


class TestDiscriminatedUnion:
    """Pydantic correctly discriminates resource_type."""

    def test_invalid_type_rejected(self) -> None:
        reg = ResourceRegistry()
        with pytest.raises(ValidationError):
            reg.load_dict({"resources": {"bad": {"resource_type": "spaceship"}}})

    def test_missing_required_field(self) -> None:
        reg = ResourceRegistry()
        with pytest.raises(ValidationError):
            reg.load_dict({"resources": {"jq": {"resource_type": "package"}}})
            # missing provider


class TestMarkupRoundTrip:
    """Resources survive serialization through the markup subsystem."""

    def test_manifest_through_json(self, tmp_path: Path) -> None:
        markup = create_default_registry()
        manifest_path = tmp_path / "manifest.json"

        markup.write_file(SAMPLE_MANIFEST, manifest_path)

        reg = ResourceRegistry()
        reg.load_file(manifest_path, markup)

        jq = reg.get("jq")
        assert isinstance(jq, PackageResource)
        assert jq.get_latest is True
        assert jq.schedule == "0 1 * * *"

    def test_manifest_through_yaml(self, tmp_path: Path) -> None:
        markup = create_default_registry()
        manifest_path = tmp_path / "manifest.yaml"

        markup.write_file(SAMPLE_MANIFEST, manifest_path)

        reg = ResourceRegistry()
        reg.load_file(manifest_path, markup)

        app = reg.get("my-app")
        assert isinstance(app, SourceResource)
        assert app.compile_cmd == "make install"

    def test_manifest_through_hocon(self, tmp_path: Path) -> None:
        markup = create_default_registry()
        manifest_path = tmp_path / "manifest.conf"

        markup.write_file(SAMPLE_MANIFEST, manifest_path)

        reg = ResourceRegistry()
        reg.load_file(manifest_path, markup)

        assert len(reg.resources) == 5
