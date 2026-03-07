"""CLI tests — command parsing, dispatch, output formatting."""

from __future__ import annotations

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
            "target": "/opt/app",
            "schedule": "0 */12 * * *",
        },
        "trading-hosts": {
            "provision_type": "file",
            "path": "/etc/proviso/hosts.conf",
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
        d = Dispatcher(manifest_path=manifest_file)
        results = d.run(provision_type=None, name="jq", verb="install")
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
