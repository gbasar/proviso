"""Catalog loading tests — ProvisionRegistry with categorized (modern-linux-utils) style.

Covers: real conf file, type inference, cross-reference skipping,
category-as-tag, install block unwrapping, error cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from proviso.markup.hocon import HoconAdapter
from proviso.provisions.models import PackageProvision
from proviso.provisions.registry import ProvisionError, ProvisionRegistry

CONF_PATH = (
    Path(__file__).parent.parent.parent
    / ".devcontainer" / "config" / "provisions" / "modern-linux-utils.conf"
)

_hocon = HoconAdapter()

MINIMAL_CONF = """
tools {
  ripgrep {
    description = "fast grep"
    install { method = cargo, package = ripgrep }
  }

  fd {
    description = "fast find"
    install { method = cargo, package = fd-find }
  }
}

other {
  delta { see = "tools.ripgrep" }
}
"""


def _load_string(content: str) -> ProvisionRegistry:
    reg = ProvisionRegistry()
    reg.load_dict(_hocon.read_string(content))
    return reg


class TestRealManifest:
    """Load the actual modern-linux-utils.conf from the repo."""

    def _load(self) -> ProvisionRegistry:
        reg = ProvisionRegistry()
        reg.load_dict(_hocon.read_file(CONF_PATH))
        return reg

    def test_loads_without_error(self) -> None:
        reg = self._load()
        assert len(reg.provisions) > 0

    def test_all_package_provisions(self) -> None:
        reg = self._load()
        assert all(isinstance(r, PackageProvision) for r in reg.provisions.values())

    def test_cross_reference_skipped(self) -> None:
        reg = self._load()
        assert list(reg.provisions).count("delta") == 1

    def test_expected_count(self) -> None:
        """31 entries (30 real + 1 cross-ref) → 30 provisions."""
        reg = self._load()
        assert len(reg.provisions) == 30

    def test_known_tools_present(self) -> None:
        reg = self._load()
        names = set(reg.provisions)
        for name in ("eza", "bat", "ripgrep", "fd", "jq", "lazygit", "starship", "just"):
            assert name in names

    def test_providers_mapped(self) -> None:
        reg = self._load()
        p = reg.provisions
        assert p["ripgrep"].provider == "cargo"
        assert p["jq"].provider == "dnf"
        assert p["yq"].provider == "pip"
        assert p["lazygit"].provider == "go"

    def test_package_field_when_differs(self) -> None:
        reg = self._load()
        p = reg.provisions
        assert p["fd"].package == "fd-find"
        assert p["dust"].package == "du-dust"
        assert p["delta"].package == "git-delta"

    def test_package_field_none_when_same(self) -> None:
        reg = self._load()
        p = reg.provisions
        assert p["ripgrep"].package is None
        assert p["jq"].package is None

    def test_category_in_tags(self) -> None:
        reg = self._load()
        p = reg.provisions
        assert "file-navigation" in p["eza"].tags
        assert "text-processing" in p["jq"].tags
        assert "git-tools" in p["lazygit"].tags

    def test_tags_are_tuples(self) -> None:
        reg = self._load()
        for r in reg.provisions.values():
            assert isinstance(r.tags, tuple)


class TestMinimalConf:
    def test_loads_two_entries(self) -> None:
        reg = _load_string(MINIMAL_CONF)
        assert set(reg.provisions) == {"ripgrep", "fd"}

    def test_cross_reference_skipped(self) -> None:
        reg = _load_string(MINIMAL_CONF)
        assert "delta" not in reg.provisions

    def test_description_on_provision(self) -> None:
        reg = _load_string(MINIMAL_CONF)
        assert reg.provisions["ripgrep"].description == "fast grep"

    def test_package_differs_from_name(self) -> None:
        reg = _load_string(MINIMAL_CONF)
        assert reg.provisions["fd"].package == "fd-find"

    def test_category_tag(self) -> None:
        reg = _load_string(MINIMAL_CONF)
        assert "tools" in reg.provisions["ripgrep"].tags


class TestErrors:
    def test_missing_method(self) -> None:
        bad = "cat { jq { install { package = jq } } }"
        with pytest.raises(ProvisionError, match="missing 'method'"):
            _load_string(bad)

    def test_missing_package(self) -> None:
        bad = "cat { jq { install { method = dnf } } }"
        with pytest.raises(ProvisionError, match="missing 'package'"):
            _load_string(bad)

    def test_unknown_method(self) -> None:
        bad = "cat { jq { install { method = chocolatey, package = jq } } }"
        with pytest.raises(ProvisionError, match="unknown install method"):
            _load_string(bad)
