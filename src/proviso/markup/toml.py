"""TOML markup adapter backed by tomllib (stdlib) and tomli-w."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import tomli_w


class TomlAdapter:
    """Reads TOML via stdlib tomllib, writes via tomli-w."""

    @property
    def format_name(self) -> str:
        return "toml"

    @property
    def file_extensions(self) -> tuple[str, ...]:
        return (".toml",)

    def read_string(self, content: str) -> dict[str, Any]:
        return tomllib.loads(content)

    def write_string(self, data: dict[str, Any]) -> str:
        return tomli_w.dumps(data)

    def read_file(self, path: Path) -> dict[str, Any]:
        with path.open("rb") as f:
            return tomllib.load(f)

    def write_file(self, data: dict[str, Any], path: Path) -> None:
        with path.open("wb") as f:
            tomli_w.dump(data, f)
