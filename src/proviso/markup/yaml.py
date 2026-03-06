"""YAML markup adapter backed by pyyaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class YamlAdapter:
    """Reads/writes YAML using pyyaml."""

    @property
    def format_name(self) -> str:
        return "yaml"

    @property
    def file_extensions(self) -> tuple[str, ...]:
        return (".yaml", ".yml")

    def read_string(self, content: str) -> dict[str, Any]:
        result = yaml.safe_load(content)
        if not isinstance(result, dict):
            msg = f"Expected YAML mapping at root, got {type(result).__name__}"
            raise ValueError(msg)
        return result

    def write_string(self, data: dict[str, Any]) -> str:
        return yaml.dump(data, default_flow_style=False, sort_keys=True, allow_unicode=True)

    def read_file(self, path: Path) -> dict[str, Any]:
        return self.read_string(path.read_text(encoding="utf-8"))

    def write_file(self, data: dict[str, Any], path: Path) -> None:
        path.write_text(self.write_string(data), encoding="utf-8")
