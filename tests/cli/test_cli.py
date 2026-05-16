"""CLI tests — command parsing, dispatch, output formatting."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from proviso.cli.dispatch import Dispatcher
from proviso.cli.main import main, parse_command
from proviso.cli.output import format_output
from proviso.markup import create_default_registry

SAMPLE_MANIFEST: dict[str, Any] = {
    "provisions": {
        "jq": {
            "provision_type": "package",
            "provider": "dnf",
            "destination": "/usr/bin",
            "get_latest": True,
            "schedule": "0 1 * * *",
        },
        "requests": {
            "provision_type": "package",
            "provider": "pip",
            "version": "2.31.0",
        },
        "my-app": {
            "provision_type": "source",
            "repo": "git@github.com:org/app.git",
            "destination": "/opt/app",
            "schedule": "0 */12 * * *",
        },
        "trading-hosts": {
            "provision_type": "file",
            "destination": "/etc/proviso/hosts.conf",
            "tags": ["trading"],
        },
    },
}


@pytest.fixture()
def manifest_file(tmp_path: Path) -> Path:
    markup = create_default_registry()
    path = tmp_path / "manifest.conf"
    markup.write_file(SAMPLE_MANIFEST, path)
    return path


class TestParseCommand:
    def test_full_command(self) -> None:
        result = parse_command(["cat", "package", "jq", "install"])
        assert result["catalog"] == "cat"
        assert result["provision_type"] == "package"
        assert result["name"] == "jq"
        assert result["verb"] == "install"

    def test_list_by_type(self) -> None:
        result = parse_command(["cat", "package", "list"])
        assert result["provision_type"] == "package"
        assert result["verb"] == "list"
        assert result["name"] is None

    def test_list_all(self) -> None:
        result = parse_command(["cat", "list"])
        assert result["verb"] == "list"
        assert result["provision_type"] is None

    def test_source_sync(self) -> None:
        result = parse_command(["cat", "source", "my-app", "sync"])
        assert result["provision_type"] == "source"
        assert result["name"] == "my-app"
        assert result["verb"] == "sync"

    def test_empty(self) -> None:
        result = parse_command([])
        assert result["catalog"] is None

    def test_status_by_name(self) -> None:
        result = parse_command(["cat", "file", "trading-hosts", "status"])
        assert result["provision_type"] == "file"
        assert result["name"] == "trading-hosts"
        assert result["verb"] == "status"


class TestDispatcher:
    def test_list_all(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file)
        results = d.run(provision_type=None, name=None, verb="list")
        assert len(results) == 4
        names = {r["name"] for r in results}
        assert "jq" in names
        assert "trading-hosts" in names

    def test_list_by_type(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file)
        results = d.run(provision_type="package", name=None, verb="list")
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert names == {"jq", "requests"}

    def test_info_single(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file)
        results = d.run(provision_type=None, name="jq", verb="info")
        assert len(results) == 1
        assert results[0]["provider"] == "dnf"

    def test_status(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file)
        results = d.run(provision_type=None, name="trading-hosts", verb="status")
        assert results[0]["tags"] == ["trading"]

    def test_dry_run(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file, dry_run=True)
        results = d.run(provision_type=None, name="jq", verb="install")
        assert results[0]["dry_run"] is True
        assert results[0]["ok"] is True

    def test_action_dispatched(self, manifest_file: Path) -> None:
        # SourceProvision has no install handler → falls through to "dispatched"
        d = Dispatcher(manifest_path=manifest_file)
        results = d.run(provision_type=None, name="my-app", verb="install")
        assert results[0]["status"] == "dispatched"

    def test_unknown_verb(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file)
        results = d.run(provision_type=None, name=None, verb="explode")
        assert results[0]["ok"] is False

    def test_stdin_names(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file)
        results = d.run(
            provision_type=None,
            name=None,
            verb="list",
            stdin_names=["jq", "my-app"],
        )
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert names == {"jq", "my-app"}

    def test_missing_manifest(self, tmp_path: Path) -> None:
        d = Dispatcher(manifest_path=tmp_path / "nope.conf")
        results = d.run(provision_type=None, name=None, verb="list")
        assert len(results) == 0


class TestMethodFilter:
    def test_cli_filter_skips_excluded_methods(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file, dry_run=True, method_filter=frozenset({"dnf"}))
        results = d.run(provision_type="package", name=None, verb="install")
        skipped = [r for r in results if r.get("status") == "skipped"]
        installed = [r for r in results if r.get("dry_run")]
        assert any(r["name"] == "requests" for r in skipped), "pip provision should be skipped"
        assert any(r["name"] == "jq" for r in installed), "dnf provision should run"

    def test_cli_filter_allows_multiple_methods(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file, dry_run=True, method_filter=frozenset({"dnf", "pip"}))
        results = d.run(provision_type="package", name=None, verb="install")
        skipped = [r for r in results if r.get("status") == "skipped"]
        assert len(skipped) == 0

    def test_no_filter_runs_all(self, manifest_file: Path) -> None:
        d = Dispatcher(manifest_path=manifest_file, dry_run=True)
        results = d.run(provision_type="package", name=None, verb="install")
        skipped = [r for r in results if r.get("status") == "skipped"]
        assert len(skipped) == 0

    def test_env_var_filter(self, manifest_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROVISO_METHODS", "dnf")
        d = Dispatcher(manifest_path=manifest_file, dry_run=True)
        results = d.run(provision_type="package", name=None, verb="install")
        skipped = [r for r in results if r.get("status") == "skipped"]
        assert any(r["name"] == "requests" for r in skipped)

    def test_cli_overrides_env_var(self, manifest_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROVISO_METHODS", "dnf")
        d = Dispatcher(manifest_path=manifest_file, dry_run=True, method_filter=frozenset({"dnf", "pip"}))
        results = d.run(provision_type="package", name=None, verb="install")
        skipped = [r for r in results if r.get("status") == "skipped"]
        assert len(skipped) == 0, "CLI filter should override env var, allowing pip"

    def test_manifest_allowed_methods(self, tmp_path: Path) -> None:
        markup = create_default_registry()
        manifest: dict[str, Any] = {
            "allowed_methods": ["dnf"],
            "provisions": {
                "jq":       {"provision_type": "package", "provider": "dnf"},
                "requests": {"provision_type": "package", "provider": "pip"},
            },
        }
        path = tmp_path / "manifest.conf"
        markup.write_file(manifest, path)
        d = Dispatcher(manifest_path=path, dry_run=True)
        results = d.run(provision_type="package", name=None, verb="install")
        skipped = [r for r in results if r.get("status") == "skipped"]
        assert any(r["name"] == "requests" for r in skipped)
        assert not any(r["name"] == "jq" and r.get("status") == "skipped" for r in results)

    def test_main_method_flag(self, manifest_file: Path) -> None:
        exit_code = main([
            "--manifest", str(manifest_file),
            "--method", "dnf",
            "--dry-run",
            "cat", "package", "install",
        ])
        assert exit_code == 0


class TestFormatOutput:
    def test_text_format(self) -> None:
        results = [{"name": "jq", "type": "package", "schedule": "0 1 * * *"}]
        output = format_output(results, fmt="text")
        assert "jq" in output
        assert "package" in output

    def test_json_format(self) -> None:
        results = [{"name": "jq", "type": "package"}]
        output = format_output(results, fmt="json")
        assert '"jq"' in output

    def test_yaml_format(self) -> None:
        results = [{"name": "jq", "type": "package"}]
        output = format_output(results, fmt="yaml")
        assert "name: jq" in output

    def test_empty_results(self) -> None:
        assert format_output([], fmt="text") == ""

    def test_text_pipe_friendly(self) -> None:
        results = [
            {"name": "jq", "type": "package"},
            {"name": "rg", "type": "package"},
        ]
        output = format_output(results, fmt="text")
        lines = output.strip().split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("jq")
        assert lines[1].startswith("rg")


class TestAudit:
    def test_audit_writes_yaml(self, tmp_path: Path) -> None:
        markup = create_default_registry()
        manifest: dict[str, Any] = {
            "provisions": {
                "jq":       {"provision_type": "package", "provider": "dnf"},
                "requests": {"provision_type": "package", "provider": "pip"},
                "eza":      {"provision_type": "package", "provider": "cargo"},
            },
        }
        path = tmp_path / "manifest.conf"
        markup.write_file(manifest, path)
        out = tmp_path / "audit.yaml"

        d = Dispatcher(manifest_path=path, audit_out=out)
        results = d.run(provision_type="package", name=None, verb="audit")

        assert out.exists()
        import yaml
        doc = yaml.safe_load(out.read_text())
        assert doc["total_packages"] == 3
        names = {p["name"] for p in doc["packages"]}
        assert names == {"jq", "requests", "eza"}
        assert "by_method" in doc["summary"]
        assert len(results) == 3

    def test_audit_dnf_candidate_flagged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        markup = create_default_registry()
        manifest: dict[str, Any] = {
            "provisions": {
                "ripgrep": {"provision_type": "package", "provider": "cargo", "package": "ripgrep"},
            },
        }
        path = tmp_path / "manifest.conf"
        markup.write_file(manifest, path)
        out = tmp_path / "audit.yaml"

        from proviso.providers.dnf import DnfProvider
        monkeypatch.setattr(DnfProvider, "is_in_repo", lambda self, pkg: True)

        d = Dispatcher(manifest_path=path, audit_out=out)
        d.run(provision_type="package", name=None, verb="audit")

        import yaml
        doc = yaml.safe_load(out.read_text())
        pkg = doc["packages"][0]
        assert pkg["dnf_available"] is True
        assert "dnf_candidates" in doc["summary"]
        assert "ripgrep" in doc["summary"]["dnf_candidates"]

    def test_audit_via_cli(self, manifest_file: Path, tmp_path: Path) -> None:
        out = tmp_path / "audit.yaml"
        exit_code = main([
            "--manifest", str(manifest_file),
            "--audit-out", str(out),
            "cat", "package", "audit",
        ])
        assert exit_code == 0
        assert out.exists()


class TestMainEntryPoint:
    def test_list_all(self, manifest_file: Path) -> None:
        exit_code = main(["--manifest", str(manifest_file), "cat", "list"])
        assert exit_code == 0

    def test_list_packages(self, manifest_file: Path) -> None:
        exit_code = main(["--manifest", str(manifest_file), "cat", "package", "list"])
        assert exit_code == 0

    def test_info(self, manifest_file: Path) -> None:
        exit_code = main(["--manifest", str(manifest_file), "cat", "package", "jq", "info"])
        assert exit_code == 0

    def test_dry_run(self, manifest_file: Path) -> None:
        exit_code = main(
            [
                "--manifest",
                str(manifest_file),
                "--dry-run",
                "cat",
                "package",
                "jq",
                "install",
            ]
        )
        assert exit_code == 0

    def test_json_output(self, manifest_file: Path) -> None:
        exit_code = main(
            [
                "--manifest",
                str(manifest_file),
                "--format",
                "json",
                "cat",
                "list",
            ]
        )
        assert exit_code == 0

    def test_missing_manifest(self, tmp_path: Path) -> None:
        exit_code = main(["--manifest", str(tmp_path / "nope.conf"), "cat", "list"])
        assert exit_code == 0  # empty list, not an error
