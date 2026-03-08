"""ManifestScanner — resolves PROVISION_LIST into a flat list of provisions.

PROVISION_LIST is an optional top-level key in any proviso manifest:

    PROVISION_LIST = [
      "~/.proviso/dotfiles.conf"       # single file (any supported format)
      "~/.proviso/configs/"            # folder — loads all supported files in it
      "~/.proviso/extras/*.conf"       # glob
    ]

Each entry is expanded to a list of paths, filtered to supported extensions,
then loaded via the markup registry (format detected by extension).
All provisions are merged into a single flat list.

Supported extensions: whatever is registered in the MarkupRegistry
(.conf, .hocon, .json, .yaml, .yml, .toml).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from proviso.markup import MarkupRegistry, create_default_registry
from proviso.provisions.models import AnyProvision
from proviso.provisions.registry import ProvisionRegistry

_REQUIRED_KEY = "PROVISO_REQUIRED_PROVISIONS"
_PROVISION_LIST_KEY = "PROVISION_LIST"


class ManifestScanner:
    """Loads provisions from a PROVISION_LIST — files, folders, or globs.

    PROVISO_REQUIRED_PROVISIONS entries are loaded first (system/config requirements).
    PROVISION_LIST entries are loaded after (user-facing apps and tools).
    """

    def __init__(self, markup: MarkupRegistry | None = None) -> None:
        self._markup = markup or create_default_registry()

    def scan(self, root: Path) -> list[AnyProvision]:
        """Load the root manifest, extract both lists, return all provisions in order."""
        data = self._markup.read_file(root)
        required_entries: list[str] = data.get(_REQUIRED_KEY, [])
        user_entries: list[str] = data.get(_PROVISION_LIST_KEY, [])
        paths = self._resolve(required_entries) + self._resolve(user_entries)
        return self._load_all(paths)

    def scan_list(self, entries: list[str], base: Path | None = None) -> list[AnyProvision]:
        """Resolve and load a PROVISION_LIST directly (useful for testing)."""
        paths = self._resolve(entries, base=base)
        return self._load_all(paths)

    # ── internals ────────────────────────────────────────────────────────────

    def _resolve(self, entries: list[str], base: Path | None = None) -> list[Path]:
        """Expand each entry (file / folder / glob) to concrete paths."""
        supported = set(self._markup._by_ext.keys())
        paths: list[Path] = []

        for entry in entries:
            p = Path(entry).expanduser()
            if not p.is_absolute() and base:
                p = base / p

            if p.is_dir():
                # Folder — load all supported files (non-recursive)
                for child in sorted(p.iterdir()):
                    if child.is_file() and child.suffix in supported:
                        paths.append(child)
            elif p.is_file():
                if p.suffix in supported:
                    paths.append(p)
            else:
                # Treat as glob
                parent = p.parent
                pattern = p.name
                for match in sorted(parent.glob(pattern)):
                    if match.is_file() and match.suffix in supported:
                        paths.append(match)

        return paths

    def _load_all(self, paths: list[Path]) -> list[AnyProvision]:
        """Load each path into a ProvisionRegistry and return merged provisions."""
        registry = ProvisionRegistry()
        for path in paths:
            data = self._markup.read_file(path)
            registry.load_dict(data)
        return list(registry.provisions.values())
