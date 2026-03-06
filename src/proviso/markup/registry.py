"""Markup adapter registry.

Resolves the correct adapter by format name or file extension.
New formats are registered, not hardcoded into lookup logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from proviso.markup.protocol import MarkupAdapter


class MarkupRegistry:
    """Central registry for markup adapters.

    Adapters register themselves by format name and file extensions.
    Lookup by either. Thread-safe for read-after-init usage.
    """

    def __init__(self) -> None:
        self._by_name: dict[str, MarkupAdapter] = {}
        self._by_ext: dict[str, MarkupAdapter] = {}

    def register(self, adapter: MarkupAdapter) -> None:
        """Register an adapter. Raises if name or extension conflicts."""
        name = adapter.format_name
        if name in self._by_name:
            msg = f"Format '{name}' already registered"
            raise ValueError(msg)

        for ext in adapter.file_extensions:
            normalized = ext if ext.startswith(".") else f".{ext}"
            if normalized in self._by_ext:
                msg = f"Extension '{normalized}' already registered"
                raise ValueError(msg)
            self._by_ext[normalized] = adapter

        self._by_name[name] = adapter

    def get_by_name(self, name: str) -> MarkupAdapter:
        """Resolve adapter by format name ('json', 'hocon', etc.)."""
        try:
            return self._by_name[name]
        except KeyError:
            msg = f"Unknown format: '{name}'. Available: {list(self._by_name.keys())}"
            raise ValueError(msg) from None

    def get_by_extension(self, ext: str) -> MarkupAdapter:
        """Resolve adapter by file extension ('.yaml', '.conf', etc.)."""
        normalized = ext if ext.startswith(".") else f".{ext}"
        try:
            return self._by_ext[normalized]
        except KeyError:
            msg = f"Unknown extension: '{normalized}'. Available: {list(self._by_ext.keys())}"
            raise ValueError(msg) from None

    def get_for_file(self, path: Path) -> MarkupAdapter:
        """Resolve adapter by inspecting a file's extension."""
        return self.get_by_extension(path.suffix)

    def read_file(self, path: Path) -> dict[str, Any]:
        """Convenience: auto-detect format and read."""
        return self.get_for_file(path).read_file(path)

    def write_file(self, data: dict[str, Any], path: Path) -> None:
        """Convenience: auto-detect format and write."""
        self.get_for_file(path).write_file(data, path)

    @property
    def available_formats(self) -> list[str]:
        return list(self._by_name.keys())


def create_default_registry() -> MarkupRegistry:
    """Wire up the standard adapters. This is the composition root for markup."""
    from proviso.markup.hocon import HoconAdapter
    from proviso.markup.json import JsonAdapter
    from proviso.markup.toml import TomlAdapter
    from proviso.markup.yaml import YamlAdapter

    registry = MarkupRegistry()
    registry.register(JsonAdapter())
    registry.register(HoconAdapter())
    registry.register(YamlAdapter())
    registry.register(TomlAdapter())
    return registry
