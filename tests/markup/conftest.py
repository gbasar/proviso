"""Shared fixtures for markup tests."""

from __future__ import annotations

import pytest

from proviso.markup import MarkupRegistry, create_default_registry
from proviso.markup.hocon import HoconAdapter
from proviso.markup.json import JsonAdapter
from proviso.markup.toml import TomlAdapter
from proviso.markup.yaml import YamlAdapter


@pytest.fixture
def registry() -> MarkupRegistry:
    """Fully wired default registry."""
    return create_default_registry()


@pytest.fixture
def json_adapter() -> JsonAdapter:
    return JsonAdapter()


@pytest.fixture
def hocon_adapter() -> HoconAdapter:
    return HoconAdapter()


@pytest.fixture
def yaml_adapter() -> YamlAdapter:
    return YamlAdapter()


@pytest.fixture
def toml_adapter() -> TomlAdapter:
    return TomlAdapter()


# Representative resource data used across all format tests
SAMPLE_RESOURCE: dict = {
    "name": "jq",
    "type": "binary",
    "provider": "dnf",
    "destination": "/usr/bin",
    "getLatest": True,
    "schedule": "0 1 * * *",
    "links": ["/usr/local/bin/jq"],
}

SAMPLE_MANIFEST: dict = {
    "resources": {
        "jq": {
            "type": "binary",
            "provider": "dnf",
            "destination": "/usr/bin",
            "getLatest": True,
        },
        "trading-hosts": {
            "type": "host",
            "entries": [
                {"name": "prod-1", "addr": "10.0.1.1"},
                {"name": "prod-2", "addr": "10.0.1.2"},
            ],
        },
    }
}
