"""HOCON markup adapter backed by pyhocon."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyhocon import ConfigFactory, HOCONConverter
from pyhocon.config_tree import ConfigTree


def _tree_to_dict(tree: ConfigTree) -> dict[str, Any]:
    """Recursively convert a pyhocon ConfigTree to a plain dict."""
    result: dict[str, Any] = {}
    for key in tree:
        val = tree[key]
        if isinstance(val, ConfigTree):
            result[key] = _tree_to_dict(val)
        elif isinstance(val, list):
            result[key] = [_tree_to_dict(v) if isinstance(v, ConfigTree) else v for v in val]
        else:
            result[key] = val
    return result


class HoconAdapter:
    """Reads/writes HOCON using pyhocon."""

    @property
    def format_name(self) -> str:
        return "hocon"

    @property
    def file_extensions(self) -> tuple[str, ...]:
        return (".conf", ".hocon")

    def read_string(self, content: str) -> dict[str, Any]:
        tree = ConfigFactory.parse_string(content)
        return _tree_to_dict(tree)

    def write_string(self, data: dict[str, Any]) -> str:
        tree = ConfigFactory.from_dict(data)
        return HOCONConverter.to_hocon(tree)

    def read_file(self, path: Path) -> dict[str, Any]:
        tree = ConfigFactory.parse_file(str(path))
        return _tree_to_dict(tree)

    def write_file(self, data: dict[str, Any], path: Path) -> None:
        path.write_text(self.write_string(data), encoding="utf-8")
