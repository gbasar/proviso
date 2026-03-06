"""JSON markup adapter backed by orjson."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import orjson


class JsonAdapter:
    """Reads/writes JSON using orjson for speed."""

    @property
    def format_name(self) -> str:
        return "json"

    @property
    def file_extensions(self) -> tuple[str, ...]:
        return (".json",)

    def read_string(self, content: str) -> dict[str, Any]:
        result = orjson.loads(content)
        if not isinstance(result, dict):
            msg = f"Expected JSON object at root, got {type(result).__name__}"
            raise ValueError(msg)
        return result

    def write_string(self, data: dict[str, Any]) -> str:
        return orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode()

    def read_file(self, path: Path) -> dict[str, Any]:
        return self.read_string(path.read_text(encoding="utf-8"))

    def write_file(self, data: dict[str, Any], path: Path) -> None:
        path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
