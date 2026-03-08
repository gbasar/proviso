"""Provision registry — loads manifests and deserializes into typed provisions.

Supports two manifest shapes:

  Flat (explicit provision_type):
      provisions {
        starship { provision_type = file, path = "~/.config/starship.toml", from = "..." }
        eza      { provision_type = package, provider = cargo }
      }

  Categorized (type inferred from fields, category becomes a tag):
      file-navigation {
        eza { install { method = cargo, package = eza } }
      }
      dotfiles {
        starship { from = "...", path = "~/.config/starship.toml", mode = SYMLINK }
      }

Type inference rules (when provision_type is absent):
  - Has install {}  →  package
  - Has repo        →  source
  - Otherwise       →  file

Unknown fields are collected into metadata rather than rejected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from proviso.markup import MarkupRegistry
from proviso.provisions.models import AnyProvision

_provision_adapter = TypeAdapter(AnyProvision)

_KNOWN_METHODS = {"cargo", "dnf", "apt", "brew", "pip", "go", "npm", "gem", "maven", "file"}

# Known fields per type — anything else goes into metadata
_BASE_KNOWN = {"name", "description", "schedule", "tags", "metadata", "provision_type",
               "symlinks", "pre_install", "post_install"}
_KNOWN: dict[str, set[str]] = {
    "package": _BASE_KNOWN | {"provider", "package", "version", "destination", "loc", "get_latest"},
    "source":  _BASE_KNOWN | {"repo", "destination", "branch", "compile_cmd", "get_latest"},
    "file":    _BASE_KNOWN | {"src", "destination", "mode"},
}


class ProvisionError(ValueError):
    """Raised when a provision entry is structurally invalid."""


class ProvisionRegistry:
    """Holds all known provisions. Loaded from manifest files."""

    def __init__(self) -> None:
        self._provisions: dict[str, AnyProvision] = {}

    @property
    def provisions(self) -> dict[str, AnyProvision]:
        return dict(self._provisions)

    def get(self, name: str) -> AnyProvision:
        try:
            return self._provisions[name]
        except KeyError:
            msg = f"Unknown provision: '{name}'. Available: {list(self._provisions.keys())}"
            raise ValueError(msg) from None

    def load_dict(self, data: dict[str, Any]) -> None:
        """Load provisions from a raw dict (already parsed from markup).

        Accepts either flat style (top-level 'provisions' key) or
        categorized style (top-level keys are category names).
        """
        if "provisions" in data:
            for name, fields in data["provisions"].items():
                if isinstance(fields, dict):
                    self._load_entry(name, fields)
        else:
            for category, tools in data.items():
                if not isinstance(tools, dict):
                    continue
                for name, fields in tools.items():
                    if isinstance(fields, dict):
                        self._load_entry(name, fields, category=category)

    def load_file(self, path: Path, markup: MarkupRegistry) -> None:
        """Load provisions from a manifest file (any supported format)."""
        data = markup.read_file(path)
        self.load_dict(data)

    def filter_by_type(self, provision_type: str) -> dict[str, AnyProvision]:
        return {k: v for k, v in self._provisions.items() if v.provision_type == provision_type}

    def filter_by_tag(self, tag: str) -> dict[str, AnyProvision]:
        return {k: v for k, v in self._provisions.items() if tag in v.tags}

    def scheduled(self) -> dict[str, AnyProvision]:
        return {k: v for k, v in self._provisions.items() if v.schedule is not None}

    # ── internals ─────────────────────────────────────────────────────────────

    def _load_entry(self, name: str, fields: dict[str, Any], category: str | None = None) -> None:
        normalized = self._normalize(name, fields, category)
        if normalized is None:
            return
        provision = _provision_adapter.validate_python(normalized)
        self._provisions[name] = provision

    def _normalize(
        self, name: str, fields: dict[str, Any], category: str | None = None
    ) -> dict[str, Any] | None:
        # Cross-references: { see = "category.name" }
        if "see" in fields and len(fields) == 1:
            return None

        fields = dict(fields)

        # Infer or keep provision_type
        if "provision_type" not in fields:
            if "install" in fields:
                fields["provision_type"] = "package"
            elif "repo" in fields:
                fields["provision_type"] = "source"
            else:
                fields["provision_type"] = "file"

        ptype = fields["provision_type"]

        # Unwrap install block → provider + package
        if ptype == "package" and "install" in fields:
            install = fields.pop("install")
            if not isinstance(install, dict):
                raise ProvisionError(f"'{name}': install must be a block")
            method = install.get("method")
            if not method:
                raise ProvisionError(f"'{name}': install block is missing 'method'")
            if method not in _KNOWN_METHODS:
                raise ProvisionError(
                    f"'{name}': unknown install method '{method}'. Known: {sorted(_KNOWN_METHODS)}"
                )
            fields["provider"] = method
            if method == "file":
                loc = install.get("loc")
                if loc:
                    fields["loc"] = loc
            else:
                pkg = install.get("package")
                if not pkg:
                    raise ProvisionError(f"'{name}': install block is missing 'package'")
                if str(pkg) != name:
                    fields["package"] = str(pkg)

        # Category → prepend to tags
        if category is not None:
            existing = list(fields.get("tags", []))
            if category not in existing:
                fields["tags"] = tuple([category] + existing)

        # Collect unknown fields into metadata
        known = _KNOWN.get(ptype, _BASE_KNOWN)
        metadata = dict(fields.get("metadata") or {})
        clean: dict[str, Any] = {}
        for k, v in fields.items():
            if k in known:
                clean[k] = v
            else:
                metadata[k] = v
        if metadata:
            clean["metadata"] = metadata

        clean["name"] = name
        return clean
