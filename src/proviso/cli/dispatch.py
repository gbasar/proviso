"""Dispatcher — the glue between CLI and domain.

Load manifest → select provisions → dispatch through actions/pipelines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from proviso.markup import create_default_registry
from proviso.provisions.models import PackageProvision, SourceProvision
from proviso.provisions.registry import ProvisionRegistry


class Dispatcher:
    """Load, select, dispatch."""

    def __init__(
        self,
        manifest_path: Path,
        verbosity: int = 0,
        output_format: str = "text",
        dry_run: bool = False,
    ) -> None:
        self._manifest_path = manifest_path
        self._verbosity = verbosity
        self._format = output_format
        self._dry_run = dry_run
        self._markup = create_default_registry()
        self._provisions = ProvisionRegistry()

    def _load(self) -> None:
        if self._manifest_path.exists():
            self._provisions.load_file(self._manifest_path, self._markup)

    def run(
        self,
        provision_type: str | None,
        name: str | None,
        verb: str,
        stdin_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        self._load()

        if stdin_names:
            targets = {n: self._provisions.get(n) for n in stdin_names}
        elif name:
            targets = {name: self._provisions.get(name)}
        elif provision_type:
            targets = self._provisions.filter_by_type(provision_type)
        else:
            targets = self._provisions.provisions

        if verb == "list":
            return self._list(targets)
        if verb == "status":
            return self._status(targets)
        if verb == "info":
            return self._info(targets)
        if verb in ("install", "sync", "uninstall", "connect", "link"):
            return self._action(verb, targets)

        return [{"ok": False, "error": f"Unknown verb: {verb}"}]

    def _list(self, targets: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {"name": name, "type": r.provision_type, "schedule": r.schedule}
            for name, r in targets.items()
        ]

    def _status(self, targets: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        for name, r in targets.items():
            results.append(
                {
                    "name": name,
                    "type": r.provision_type,
                    "schedule": r.schedule,
                    "tags": list(r.tags),
                }
            )
        return results

    def _info(self, targets: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        for name, r in targets.items():
            entry: dict[str, Any] = {
                "name": name,
                "type": r.provision_type,
                "schedule": r.schedule,
                "tags": list(r.tags),
            }
            if isinstance(r, PackageProvision):
                entry["provider"] = r.provider
                entry["version"] = r.version
                entry["get_latest"] = r.get_latest
            elif isinstance(r, SourceProvision):
                entry["repo"] = r.repo
                entry["target"] = str(r.target)
                entry["branch"] = r.branch
            results.append(entry)
        return results

    def _action(self, verb: str, targets: dict[str, Any]) -> list[dict[str, Any]]:
        if self._dry_run:
            return [{"name": name, "verb": verb, "dry_run": True, "ok": True} for name in targets]

        # TODO: wire to actual pipelines once composition root is built
        return [
            {"name": name, "verb": verb, "ok": True, "status": "dispatched"} for name in targets
        ]
