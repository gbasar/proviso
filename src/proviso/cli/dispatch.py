"""Dispatcher — the glue between CLI and domain.

Load manifest → select provisions → dispatch through actions/pipelines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from proviso.actions.file_sync import FileSync
from proviso.manifest.scanner import ManifestScanner
from proviso.markup import create_default_registry
from proviso.provisions.models import FileProvision, PackageProvision, SourceProvision
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
        if not self._manifest_path.exists():
            return
        data = self._markup.read_file(self._manifest_path)
        if "PROVISION_LIST" in data:
            scanner = ManifestScanner(self._markup)
            for provision in scanner.scan(self._manifest_path):
                self._provisions._provisions[provision.name] = provision
        else:
            self._provisions.load_dict(data)

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

        results = []
        file_sync = FileSync()

        # BOUND must run before SYMLINK — dead pointer if mount isn't up yet.
        def _sort_key(item: tuple[str, Any]) -> int:
            p = item[1]
            if isinstance(p, FileProvision) and (p.mode or "").upper() == "BOUND":
                return 0
            return 1

        ordered = sorted(targets.items(), key=_sort_key)

        for name, provision in ordered:
            if isinstance(provision, FileProvision) and verb in ("sync", "link"):
                r = file_sync.execute(provision)
                results.append({
                    "name": name,
                    "verb": verb,
                    "ok": r.status.value != "failed",
                    "status": r.status.value,
                    "message": r.message,
                })
            else:
                results.append({"name": name, "verb": verb, "ok": True, "status": "dispatched"})

        return results
