"""Port definition for markup adapters.

Every format adapter (HOCON, YAML, JSON, TOML) implements this Protocol.
The domain core only depends on this — never on concrete adapters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MarkupAdapter(Protocol):
    """Structural type for markup format adapters.

    Adapters convert between a specific markup format and Python dicts.
    The engine only works with dicts (serialized via orjson internally).
    """

    @property
    def format_name(self) -> str:
        """Short identifier: 'json', 'hocon', 'yaml', 'toml'."""
        ...

    @property
    def file_extensions(self) -> tuple[str, ...]:
        """File extensions this adapter handles, e.g. ('.yaml', '.yml')."""
        ...

    def read_string(self, content: str) -> dict[str, Any]:
        """Parse a string in this format into a dict."""
        ...

    def write_string(self, data: dict[str, Any]) -> str:
        """Serialize a dict into a string in this format."""
        ...

    def read_file(self, path: Path) -> dict[str, Any]:
        """Read and parse a file."""
        ...

    def write_file(self, data: dict[str, Any], path: Path) -> None:
        """Serialize a dict and write to a file."""
        ...
