"""ManifestScanner tests — PROVISION_LIST resolution: files, folders, globs."""

from __future__ import annotations

from pathlib import Path

import pytest

from proviso.manifest.scanner import ManifestScanner
from proviso.markup import create_default_registry
from proviso.provisions.models import PackageProvision, SourceProvision

# ── Helpers ──────────────────────────────────────────────────────────────────

PKG_A = {
    "provisions": {
        "jq": {"provision_type": "package", "provider": "dnf"},
        "ripgrep": {"provision_type": "package", "provider": "cargo"},
    }
}

PKG_B = {
    "provisions": {
        "fd": {"provision_type": "package", "provider": "cargo"},
    }
}

SOURCE_C = {
    "provisions": {
        "my-app": {
            "provision_type": "source",
            "repo": "git@github.com:org/app.git",
            "destination": "/opt/app",
        }
    }
}


def _write(tmp_path: Path, name: str, data: dict) -> Path:
    markup = create_default_registry()
    path = tmp_path / name
    markup.write_file(data, path)
    return path


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestSingleFile:
    def test_loads_json(self, tmp_path: Path) -> None:
        f = _write(tmp_path, "a.json", PKG_A)
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(f)])
        assert len(provisions) == 2

    def test_loads_yaml(self, tmp_path: Path) -> None:
        f = _write(tmp_path, "a.yaml", PKG_A)
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(f)])
        assert len(provisions) == 2

    def test_loads_hocon(self, tmp_path: Path) -> None:
        f = _write(tmp_path, "a.conf", PKG_A)
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(f)])
        assert len(provisions) == 2

    def test_loads_toml(self, tmp_path: Path) -> None:
        f = _write(tmp_path, "a.toml", PKG_A)
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(f)])
        assert len(provisions) == 2

    def test_unsupported_extension_skipped(self, tmp_path: Path) -> None:
        bad = tmp_path / "a.txt"
        bad.write_text("irrelevant")
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(bad)])
        assert len(provisions) == 0


class TestFolder:
    def test_loads_all_files_in_folder(self, tmp_path: Path) -> None:
        _write(tmp_path, "a.json", PKG_A)
        _write(tmp_path, "b.json", PKG_B)
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(tmp_path)])
        assert len(provisions) == 3
        names = {p.name for p in provisions}
        assert names == {"jq", "ripgrep", "fd"}

    def test_ignores_unsupported_in_folder(self, tmp_path: Path) -> None:
        _write(tmp_path, "a.json", PKG_A)
        (tmp_path / "notes.txt").write_text("ignore me")
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(tmp_path)])
        assert len(provisions) == 2

    def test_mixed_formats_in_folder(self, tmp_path: Path) -> None:
        _write(tmp_path, "a.json", PKG_A)
        _write(tmp_path, "c.yaml", SOURCE_C)
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(tmp_path)])
        assert len(provisions) == 3
        types = {type(p) for p in provisions}
        assert PackageProvision in types
        assert SourceProvision in types


class TestGlob:
    def test_glob_matches_files(self, tmp_path: Path) -> None:
        _write(tmp_path, "tools-a.json", PKG_A)
        _write(tmp_path, "tools-b.json", PKG_B)
        _write(tmp_path, "other.yaml", SOURCE_C)
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(tmp_path / "tools-*.json")])
        assert len(provisions) == 3
        names = {p.name for p in provisions}
        assert "jq" in names
        assert "fd" in names
        assert "my-app" not in names

    def test_no_glob_matches_returns_empty(self, tmp_path: Path) -> None:
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(tmp_path / "*.conf")])
        assert provisions == []


class TestMixedList:
    def test_file_and_folder(self, tmp_path: Path) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        _write(tmp_path, "root.json", PKG_A)
        _write(subdir, "extra.json", PKG_B)
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(tmp_path / "root.json"), str(subdir)])
        assert len(provisions) == 3

    def test_last_write_wins_on_duplicate_name(self, tmp_path: Path) -> None:
        """Same provision name in two files — last loaded wins."""
        f1 = _write(tmp_path, "a.json", {"provisions": {"jq": {"provision_type": "package", "provider": "dnf"}}})
        f2 = _write(tmp_path, "b.json", {"provisions": {"jq": {"provision_type": "package", "provider": "brew"}}})
        scanner = ManifestScanner()
        provisions = scanner.scan_list([str(f1), str(f2)])
        jq = next(p for p in provisions if p.name == "jq")
        assert isinstance(jq, PackageProvision)
        assert jq.provider == "brew"


class TestScanFromRootManifest:
    def test_scan_reads_provision_list(self, tmp_path: Path) -> None:
        subdir = tmp_path / "tools"
        subdir.mkdir()
        _write(subdir, "pkgs.json", PKG_A)

        root = tmp_path / "proviso.conf"
        markup = create_default_registry()
        markup.write_file({"PROVISION_LIST": [str(subdir)]}, root)

        scanner = ManifestScanner()
        provisions = scanner.scan(root)
        assert len(provisions) == 2

    def test_scan_empty_list(self, tmp_path: Path) -> None:
        root = tmp_path / "proviso.conf"
        markup = create_default_registry()
        markup.write_file({"PROVISION_LIST": []}, root)

        scanner = ManifestScanner()
        provisions = scanner.scan(root)
        assert provisions == []
