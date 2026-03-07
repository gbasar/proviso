"""Provision registry — loads manifests and deserializes into typed provisions.

Reads a manifest (any format via markup subsystem), produces a dict of
named, typed, immutable provision objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from proviso.markup import MarkupRegistry
from proviso.provisions.models import AnyProvision

_provision_adapter = TypeAdapter(AnyProvision)


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

        Expects: {"provisions": {"name": {provision fields...}, ...}}
        """
        provisions_section = data.get("provisions", {})
        for name, fields in provisions_section.items():
            fields_with_name = {**fields, "name": name}
            provision = _provision_adapter.validate_python(fields_with_name)
            self._provisions[name] = provision

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
