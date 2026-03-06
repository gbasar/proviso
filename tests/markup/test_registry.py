"""Registry tests — adapter lookup and conflict detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from proviso.markup import MarkupRegistry
from proviso.markup.json import JsonAdapter
from proviso.markup.yaml import YamlAdapter

from .conftest import SAMPLE_RESOURCE


class TestRegistryLookup:
    """Resolve adapters by name, extension, and file path."""

    def test_lookup_by_name(self, registry: MarkupRegistry) -> None:
        adapter = registry.get_by_name("json")
        assert adapter.format_name == "json"

    def test_lookup_by_extension(self, registry: MarkupRegistry) -> None:
        adapter = registry.get_by_extension(".yaml")
        assert adapter.format_name == "yaml"

    def test_lookup_by_extension_without_dot(self, registry: MarkupRegistry) -> None:
        adapter = registry.get_by_extension("yaml")
        assert adapter.format_name == "yaml"

    def test_lookup_by_file_path(self, registry: MarkupRegistry) -> None:
        adapter = registry.get_for_file(Path("/etc/app/config.hocon"))
        assert adapter.format_name == "hocon"

    def test_lookup_conf_resolves_to_hocon(self, registry: MarkupRegistry) -> None:
        adapter = registry.get_by_extension(".conf")
        assert adapter.format_name == "hocon"

    def test_lookup_yml_resolves_to_yaml(self, registry: MarkupRegistry) -> None:
        adapter = registry.get_by_extension(".yml")
        assert adapter.format_name == "yaml"

    def test_available_formats(self, registry: MarkupRegistry) -> None:
        formats = registry.available_formats
        assert set(formats) == {"json", "hocon", "yaml", "toml"}


class TestRegistryConvenienceMethods:
    """read_file / write_file auto-detect format."""

    def test_read_write_auto_detect(self, registry: MarkupRegistry, tmp_path: Path) -> None:
        json_path = tmp_path / "resource.json"
        yaml_path = tmp_path / "resource.yaml"

        registry.write_file(SAMPLE_RESOURCE, json_path)
        registry.write_file(SAMPLE_RESOURCE, yaml_path)

        from_json = registry.read_file(json_path)
        from_yaml = registry.read_file(yaml_path)

        assert from_json == SAMPLE_RESOURCE
        assert from_yaml == SAMPLE_RESOURCE


class TestRegistryErrors:
    """Error cases — unknown formats, duplicate registration."""

    def test_unknown_name(self, registry: MarkupRegistry) -> None:
        with pytest.raises(ValueError, match="Unknown format"):
            registry.get_by_name("xml")

    def test_unknown_extension(self, registry: MarkupRegistry) -> None:
        with pytest.raises(ValueError, match="Unknown extension"):
            registry.get_by_extension(".xml")

    def test_duplicate_name_rejected(self) -> None:
        reg = MarkupRegistry()
        reg.register(JsonAdapter())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(JsonAdapter())

    def test_duplicate_extension_rejected(self) -> None:
        reg = MarkupRegistry()
        reg.register(YamlAdapter())

        # Create a fake adapter that claims .yaml
        class ConflictAdapter:
            format_name = "conflict"
            file_extensions = (".yaml",)

            def read_string(self, c: str) -> dict:
                return {}

            def write_string(self, d: dict) -> str:
                return ""

            def read_file(self, p: Path) -> dict:
                return {}

            def write_file(self, d: dict, p: Path) -> None:
                pass

        with pytest.raises(ValueError, match="already registered"):
            reg.register(ConflictAdapter())
