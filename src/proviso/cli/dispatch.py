"""Dispatcher — the glue between CLI and domain.

Load manifest → select resources → dispatch through actions/pipelines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from proviso.markup import create_default_registry
from proviso.resources.models import PackageResource, SourceResource
from proviso.resources.registry import ResourceRegistry


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
        self._resources = ResourceRegistry()

    def _load(self) -> None:
        if self._manifest_path.exists():
            self._resources.load_file(self._manifest_path, self._markup)

    def run(
        self,
        resource_type: str | None,
        name: str | None,
        verb: str,
        stdin_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        self._load()

        # Resolve target resources
        if stdin_names:
            targets = {n: self._resources.get(n) for n in stdin_names}
        elif name:
            targets = {name: self._resources.get(name)}
        elif resource_type:
            targets = self._resources.filter_by_type(resource_type)
        else:
            targets = self._resources.resources

        # Dispatch verb
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
            {"name": name, "type": r.resource_type, "schedule": r.schedule}
            for name, r in targets.items()
        ]

    def _status(self, targets: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        for name, r in targets.items():
            results.append(
                {
                    "name": name,
                    "type": r.resource_type,
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
                "type": r.resource_type,
                "schedule": r.schedule,
                "tags": list(r.tags),
            }
            if isinstance(r, PackageResource):
                entry["provider"] = r.provider
                entry["version"] = r.version
                entry["get_latest"] = r.get_latest
            elif isinstance(r, SourceResource):
                entry["repo"] = r.repo
                entry["target"] = str(r.target)
                entry["branch"] = r.branch
            results.append(entry)
        return results

    def _action(self, verb: str, targets: dict[str, Any]) -> list[dict[str, Any]]:
        if self._dry_run:
            return [{"name": name, "verb": verb, "dry_run": True, "ok": True} for name in targets]

        # TODO: wire to actual pipelines once composition root is built
        # For now, return pending status
        return [
            {"name": name, "verb": verb, "ok": True, "status": "dispatched"} for name in targets
        ]
