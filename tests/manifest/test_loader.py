"""Manifest loader tests.

Covers: the real .conf file, filtering, cross-reference skipping,
metadata mapping, error cases, and load_string convenience method.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proviso.manifest.loader import ManifestError, ManifestLoader
from proviso.provisions.models import PackageProvision

# Path to the real catalog (repo-relative from test runner cwd)
CONF_PATH = Path(__file__).parent.parent.parent / ".devcontainer" / "config" / "modern-linux-utils.conf"

# Minimal HOCON snippet used for unit-level tests — no file I/O needed
MINIMAL_CONF = """
tools {
  ripgrep {
    description = "fast grep"
    replaces    = "grep"
    install { method = cargo, package = ripgrep }
    priority = 3
    enabled  = true
    tags     = ["cli", "rust", "search"]
    grade    = "A+"
  }

  fd {
    description = "fast find"
    replaces    = "find"
    install { method = cargo, package = fd-find }
    priority = 3
    enabled  = true
    tags     = ["cli", "rust", "search"]
    grade    = "A+"
  }

  jq {
    description = "json processor"
    replaces    = "awk"
    install { method = dnf, package = jq }
    priority = 3
    enabled  = false
    tags     = ["cli", "json"]
    grade    = "A+"
  }
}

other {
  delta { see = "tools.ripgrep" }
}
"""


class TestRealManifest:
    """Load the actual modern-linux-utils.conf from the repo."""

    def test_loads_without_error(self) -> None:
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        assert len(resources) > 0

    def test_produces_package_resources(self) -> None:
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        assert all(isinstance(r, PackageProvision) for r in resources)

    def test_cross_references_skipped(self) -> None:
        """The delta cross-reference in git-tools must not appear twice."""
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        names = [r.name for r in resources]
        # delta appears in text-processing; the git-tools entry is a ref
        assert names.count("delta") == 1

    def test_expected_count(self) -> None:
        """33 entries in conf (32 real + 1 cross-reference) → 32 resources."""
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        assert len(resources) == 32

    def test_known_tools_present(self) -> None:
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        names = {r.name for r in resources}
        for expected in ("eza", "bat", "ripgrep", "fd", "jq", "lazygit", "starship", "just"):
            assert expected in names, f"Expected '{expected}' in loaded resources"

    def test_providers_mapped(self) -> None:
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        by_name = {r.name: r for r in resources}

        assert by_name["ripgrep"].provider == "cargo"
        assert by_name["jq"].provider == "dnf"
        assert by_name["yq"].provider == "pip"
        assert by_name["lazygit"].provider == "go"

    def test_tags_are_tuples(self) -> None:
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        for r in resources:
            assert isinstance(r.tags, tuple)

    def test_category_in_metadata(self) -> None:
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        by_name = {r.name: r for r in resources}

        assert by_name["eza"].metadata["category"] == "file-navigation"
        assert by_name["jq"].metadata["category"] == "text-processing"
        assert by_name["lazygit"].metadata["category"] == "git-tools"

    def test_package_field_when_differs(self) -> None:
        """resource.package is set when install package differs from tool name."""
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        by_name = {r.name: r for r in resources}

        assert by_name["fd"].package == "fd-find"
        assert by_name["dust"].package == "du-dust"
        assert by_name["delta"].package == "git-delta"

    def test_package_field_none_when_same(self) -> None:
        """resource.package is None when install package equals tool name."""
        loader = ManifestLoader()
        resources = loader.load(CONF_PATH)
        by_name = {r.name: r for r in resources}

        assert by_name["ripgrep"].package is None
        assert by_name["jq"].package is None


class TestFiltering:
    """Enabled/disabled filtering."""

    def test_disabled_excluded_by_default(self) -> None:
        loader = ManifestLoader()
        resources = loader.load_string(MINIMAL_CONF)
        names = {r.name for r in resources}
        assert "jq" not in names

    def test_disabled_included_when_flag_set(self) -> None:
        loader = ManifestLoader()
        resources = loader.load_string(MINIMAL_CONF, include_disabled=True)
        names = {r.name for r in resources}
        assert "jq" in names

    def test_cross_reference_always_skipped(self) -> None:
        loader = ManifestLoader()
        resources = loader.load_string(MINIMAL_CONF)
        names = {r.name for r in resources}
        assert "delta" not in names


class TestMetadataMapping:
    """Metadata fields populated correctly."""

    def test_description_in_metadata(self) -> None:
        loader = ManifestLoader()
        resources = loader.load_string(MINIMAL_CONF)
        by_name = {r.name: r for r in resources}
        assert by_name["ripgrep"].metadata["description"] == "fast grep"

    def test_grade_in_metadata(self) -> None:
        loader = ManifestLoader()
        resources = loader.load_string(MINIMAL_CONF)
        by_name = {r.name: r for r in resources}
        assert by_name["ripgrep"].metadata["grade"] == "A+"

    def test_priority_in_metadata(self) -> None:
        loader = ManifestLoader()
        resources = loader.load_string(MINIMAL_CONF)
        by_name = {r.name: r for r in resources}
        assert by_name["fd"].metadata["priority"] == 3

    def test_package_differs_from_name(self) -> None:
        loader = ManifestLoader()
        resources = loader.load_string(MINIMAL_CONF)
        by_name = {r.name: r for r in resources}
        assert by_name["fd"].name == "fd"
        assert by_name["fd"].package == "fd-find"

    def test_tags_preserved(self) -> None:
        loader = ManifestLoader()
        resources = loader.load_string(MINIMAL_CONF)
        by_name = {r.name: r for r in resources}
        assert "rust" in by_name["ripgrep"].tags
        assert "search" in by_name["ripgrep"].tags


class TestErrors:
    """ManifestError on malformed entries."""

    def test_missing_install_block(self) -> None:
        bad = "cat { jq { description = x } }"
        loader = ManifestLoader()
        with pytest.raises(ManifestError, match="missing an 'install' block"):
            loader.load_string(bad)

    def test_missing_method(self) -> None:
        bad = "cat { jq { install { package = jq } } }"
        loader = ManifestLoader()
        with pytest.raises(ManifestError, match="missing 'method'"):
            loader.load_string(bad)

    def test_missing_package(self) -> None:
        bad = "cat { jq { install { method = dnf } } }"
        loader = ManifestLoader()
        with pytest.raises(ManifestError, match="missing 'package'"):
            loader.load_string(bad)

    def test_unknown_method(self) -> None:
        bad = "cat { jq { install { method = chocolatey, package = jq } } }"
        loader = ManifestLoader()
        with pytest.raises(ManifestError, match="unknown install method"):
            loader.load_string(bad)
