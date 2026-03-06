"""Resource registry — loads manifests and deserializes into typed resources.

Reads a manifest (any format via markup subsystem), produces a dict of
named, typed, immutable resource objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from proviso.markup import MarkupRegistry
from proviso.resources.models import AnyResource

_resource_adapter = TypeAdapter(AnyResource)


class ResourceRegistry:
    """Holds all known resources. Loaded from manifest files."""

    def __init__(self) -> None:
        self._resources: dict[str, AnyResource] = {}

    @property
    def resources(self) -> dict[str, AnyResource]:
        return dict(self._resources)

    def get(self, name: str) -> AnyResource:
        try:
            return self._resources[name]
        except KeyError:
            msg = f"Unknown resource: '{name}'. Available: {list(self._resources.keys())}"
            raise ValueError(msg) from None

    def load_dict(self, data: dict[str, Any]) -> None:
        """Load resources from a raw dict (already parsed from markup).

        Expects: {"resources": {"name": {resource fields...}, ...}}
        """
        resources_section = data.get("resources", {})
        for name, fields in resources_section.items():
            fields_with_name = {**fields, "name": name}
            resource = _resource_adapter.validate_python(fields_with_name)
            self._resources[name] = resource

    def load_file(self, path: Path, markup: MarkupRegistry) -> None:
        """Load resources from a manifest file (any supported format)."""
        data = markup.read_file(path)
        self.load_dict(data)

    def filter_by_type(self, resource_type: str) -> dict[str, AnyResource]:
        return {k: v for k, v in self._resources.items() if v.resource_type == resource_type}

    def filter_by_tag(self, tag: str) -> dict[str, AnyResource]:
        return {k: v for k, v in self._resources.items() if tag in v.tags}

    def scheduled(self) -> dict[str, AnyResource]:
        return {k: v for k, v in self._resources.items() if v.schedule is not None}
