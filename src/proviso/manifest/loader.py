"""Manifest loader — reads the modern-linux-utils.conf catalog into typed provisions.

The .conf format is a HOCON file with a nested category → tool structure:

    category-name {
      tool-name {
        replaces    = "..."
        description = "..."
        install { method = cargo|dnf|pip|go, package = "..." }
        priority    = 1|2|3
        enabled     = true
        tags        = ["cli", "rust", ...]
        grade       = "A+"
        help { ... }
      }
    }

Produced provisions
-------------------
All entries map to PackageProvision.  The loader normalises the nested structure:

    name     = tool key (e.g. "fd", "ripgrep")
    provider = install.method (e.g. "cargo", "dnf")
    tags     = from the tags list
    metadata = everything else:
                 category   — parent category key
                 package    — install.package (may differ from name, e.g. "fd-find")
                 description, replaces, priority, grade, enabled, help, note, ...

Entries skipped
---------------
- Cross-references (entry contains only a "see" key)   → silently skipped
- Disabled entries (enabled = false)                   → skipped (configurable)

Errors
------
Raises ManifestError (a ValueError subclass) for malformed entries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from proviso.markup.hocon import HoconAdapter
from proviso.provisions.models import PackageProvision

_hocon = HoconAdapter()

_KNOWN_METHODS = {"cargo", "dnf", "apt", "brew", "pip", "go", "npm", "gem", "maven"}


class ManifestError(ValueError):
    """Raised when a manifest entry is structurally invalid."""


class ManifestLoader:
    """Loads a modern-linux-utils.conf catalog into PackageProvision objects."""

    def load(self, path: Path, *, include_disabled: bool = False) -> list[PackageProvision]:
        """Load from a .conf file on disk."""
        data = _hocon.read_file(path)
        return self._parse(data, include_disabled=include_disabled)

    def load_string(self, content: str, *, include_disabled: bool = False) -> list[PackageProvision]:
        """Load from a HOCON string (useful for tests)."""
        data = _hocon.read_string(content)
        return self._parse(data, include_disabled=include_disabled)

    # ── internals ────────────────────────────────────────────────────────────

    def _parse(self, data: dict[str, Any], *, include_disabled: bool) -> list[PackageProvision]:
        provisions: list[PackageProvision] = []
        for category, tools in data.items():
            if not isinstance(tools, dict):
                continue
            for tool_name, tool_data in tools.items():
                if not isinstance(tool_data, dict):
                    continue
                provision = self._parse_tool(tool_name, category, tool_data, include_disabled)
                if provision is not None:
                    provisions.append(provision)
        return provisions

    def _parse_tool(
        self,
        tool_name: str,
        category: str,
        data: dict[str, Any],
        include_disabled: bool,
    ) -> PackageProvision | None:
        # Cross-reference entries (e.g. delta { see = "text-processing.delta" })
        if "see" in data and len(data) == 1:
            return None

        # Disabled entries
        if not include_disabled and not data.get("enabled", True):
            return None

        install = data.get("install")
        if not isinstance(install, dict):
            raise ManifestError(
                f"Tool '{tool_name}' in category '{category}' is missing an 'install' block"
            )

        method = install.get("method")
        if not method:
            raise ManifestError(
                f"Tool '{tool_name}': install block is missing 'method'"
            )
        if method not in _KNOWN_METHODS:
            raise ManifestError(
                f"Tool '{tool_name}': unknown install method '{method}'. "
                f"Known: {sorted(_KNOWN_METHODS)}"
            )

        package = install.get("package")
        if not package:
            raise ManifestError(
                f"Tool '{tool_name}': install block is missing 'package'"
            )

        raw_tags: list[str] = data.get("tags") or []

        metadata: dict[str, Any] = {"category": category}
        for key in ("description", "replaces", "priority", "grade", "enabled", "help", "note"):
            if key in data:
                metadata[key] = data[key]

        install_package = str(package)
        return PackageProvision(
            name=tool_name,
            provider=str(method),
            package=install_package if install_package != tool_name else None,
            tags=tuple(raw_tags),
            metadata=metadata,
        )
