"""Round-trip tests for markup adapters.

Each adapter must faithfully round-trip data: write → read → same data.
Cross-format: read from one format, write to another, read back — same data.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from proviso.markup.hocon import HoconAdapter
from proviso.markup.json import JsonAdapter
from proviso.markup.protocol import MarkupAdapter
from proviso.markup.toml import TomlAdapter
from proviso.markup.yaml import YamlAdapter

from .conftest import SAMPLE_MANIFEST, SAMPLE_RESOURCE


class TestStringRoundTrip:
    """Each adapter round-trips through string serialization."""

    @pytest.mark.parametrize("adapter_cls", [JsonAdapter, HoconAdapter, YamlAdapter, TomlAdapter])
    def test_simple_resource(self, adapter_cls: type) -> None:
        adapter = adapter_cls()
        serialized = adapter.write_string(SAMPLE_RESOURCE)
        restored = adapter.read_string(serialized)
        assert restored == SAMPLE_RESOURCE

    @pytest.mark.parametrize("adapter_cls", [JsonAdapter, HoconAdapter, YamlAdapter, TomlAdapter])
    def test_nested_manifest(self, adapter_cls: type) -> None:
        adapter = adapter_cls()
        serialized = adapter.write_string(SAMPLE_MANIFEST)
        restored = adapter.read_string(serialized)
        assert restored == SAMPLE_MANIFEST


class TestFileRoundTrip:
    """Each adapter round-trips through file I/O."""

    @pytest.mark.parametrize(
        ("adapter_cls", "ext"),
        [
            (JsonAdapter, ".json"),
            (HoconAdapter, ".conf"),
            (YamlAdapter, ".yaml"),
            (TomlAdapter, ".toml"),
        ],
    )
    def test_file_round_trip(self, adapter_cls: type, ext: str, tmp_path: Path) -> None:
        adapter = adapter_cls()
        file_path = tmp_path / f"test{ext}"

        adapter.write_file(SAMPLE_RESOURCE, file_path)
        assert file_path.exists()

        restored = adapter.read_file(file_path)
        assert restored == SAMPLE_RESOURCE


class TestCrossFormat:
    """Read from one format, write to another, read back — data preserved."""

    FORMAT_PAIRS: ClassVar[list[tuple[type, type]]] = [
        (JsonAdapter, YamlAdapter),
        (JsonAdapter, HoconAdapter),
        (JsonAdapter, TomlAdapter),
        (YamlAdapter, HoconAdapter),
        (YamlAdapter, TomlAdapter),
        (HoconAdapter, TomlAdapter),
    ]

    @pytest.mark.parametrize(("source_cls", "target_cls"), FORMAT_PAIRS)
    def test_cross_format_conversion(self, source_cls: type, target_cls: type) -> None:
        source: MarkupAdapter = source_cls()
        target: MarkupAdapter = target_cls()

        serialized = source.write_string(SAMPLE_RESOURCE)
        data = source.read_string(serialized)
        re_serialized = target.write_string(data)
        restored = target.read_string(re_serialized)

        assert restored == SAMPLE_RESOURCE

    @pytest.mark.parametrize(("source_cls", "target_cls"), FORMAT_PAIRS)
    def test_cross_format_nested(self, source_cls: type, target_cls: type) -> None:
        source: MarkupAdapter = source_cls()
        target: MarkupAdapter = target_cls()

        serialized = source.write_string(SAMPLE_MANIFEST)
        data = source.read_string(serialized)
        re_serialized = target.write_string(data)
        restored = target.read_string(re_serialized)

        assert restored == SAMPLE_MANIFEST


class TestProtocolConformance:
    """All adapters satisfy the MarkupAdapter Protocol."""

    @pytest.mark.parametrize("adapter_cls", [JsonAdapter, HoconAdapter, YamlAdapter, TomlAdapter])
    def test_is_markup_adapter(self, adapter_cls: type) -> None:
        adapter = adapter_cls()
        assert isinstance(adapter, MarkupAdapter)


class TestEdgeCases:
    """Boundary conditions and error handling."""

    @pytest.mark.parametrize("adapter_cls", [JsonAdapter, YamlAdapter])
    def test_rejects_non_dict_root(self, adapter_cls: type) -> None:
        adapter = adapter_cls()
        with pytest.raises(ValueError, match="Expected"):
            adapter.read_string("[1, 2, 3]")

    @pytest.mark.parametrize("adapter_cls", [JsonAdapter, HoconAdapter, YamlAdapter, TomlAdapter])
    def test_empty_dict(self, adapter_cls: type) -> None:
        adapter = adapter_cls()
        serialized = adapter.write_string({})
        restored = adapter.read_string(serialized)
        assert restored == {}

    @pytest.mark.parametrize("adapter_cls", [JsonAdapter, HoconAdapter, YamlAdapter, TomlAdapter])
    def test_unicode_values(self, adapter_cls: type) -> None:
        data = {"name": "tëst", "emoji": "🚀", "cjk": "测试"}
        adapter = adapter_cls()
        serialized = adapter.write_string(data)
        restored = adapter.read_string(serialized)
        assert restored == data
