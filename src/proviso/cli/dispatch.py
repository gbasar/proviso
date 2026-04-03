"""Dispatcher — the glue between CLI and domain.

Load manifest → select provisions → dispatch through actions/pipelines.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import IO, Any

from proviso.actions.file_sync import FileSync
from proviso.actions.package_install import PackageInstall
from proviso.manifest.scanner import ManifestScanner
from proviso.markup import create_default_registry
from proviso.providers.cargo import CargoProvider
from proviso.providers.dnf import DnfProvider
from proviso.providers.go import GoProvider
from proviso.providers.pip import PipProvider
from proviso.providers.registry import ProviderRegistry
from proviso.provisions.models import FileProvision, PackageProvision, SourceProvision
from proviso.provisions.registry import ProvisionRegistry
from proviso.shell.subprocess import SubprocessShell

# Verbosity levels
_V1 = 1   # action results (success / failed)
_V2 = 2   # skipped results too
_V3 = 3   # manifest loading details


class Dispatcher:
    """Load, select, dispatch."""

    def __init__(
        self,
        manifest_path: Path,
        verbosity: int = 0,
        output_format: str = "text",
        dry_run: bool = False,
        log_file: Path | None = None,
    ) -> None:
        self._manifest_path = manifest_path
        self._verbosity = verbosity
        self._format = output_format
        self._dry_run = dry_run
        self._log_fh: IO[str] | None = None
        if log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            self._log_fh = log_file.open("a")
        self._markup = create_default_registry()
        self._provisions = ProvisionRegistry()
        _shell = SubprocessShell()
        _providers = ProviderRegistry()
        for p in [DnfProvider(_shell), PipProvider(_shell), CargoProvider(_shell), GoProvider(_shell)]:
            _providers.register(p)
        self._package_install = PackageInstall(_providers, _shell)

    def _log(self, level: int, msg: str) -> None:
        line = f"[proviso] {msg}"
        if self._verbosity >= level:
            print(line, file=sys.stderr)
        if self._log_fh is not None:
            print(line, file=self._log_fh, flush=True)

    def _load(self) -> None:
        if not self._manifest_path.exists():
            return
        if self._manifest_path.is_dir():
            for conf in sorted(self._manifest_path.glob("*.conf")):
                self._provisions.load_file(conf, self._markup)
                self._log(_V3, f"  loaded manifest: {conf}")
            return
        data = self._markup.read_file(self._manifest_path)
        if "PROVISION_LIST" in data or "PROVISO_REQUIRED_PROVISIONS" in data:
            scanner = ManifestScanner(self._markup)
            provisions = scanner.scan(self._manifest_path)
            self._log(_V3, f"  loaded {len(provisions)} provisions via PROVISION_LIST")
            for provision in provisions:
                self._provisions._provisions[provision.name] = provision
                self._log(_V3, f"    {provision.provision_type}  {provision.name}")
        else:
            self._provisions.load_dict(data)
            self._log(_V3, f"  loaded manifest: {self._manifest_path}")

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
                entry["destination"] = str(r.destination)
                entry["branch"] = r.branch
            results.append(entry)
        return results

    def _action(self, verb: str, targets: dict[str, Any]) -> list[dict[str, Any]]:
        if self._dry_run:
            for name in targets:
                self._log(_V1, f"  DRY-RUN  {verb}  {name}")
            return [{"name": name, "verb": verb, "dry_run": True, "ok": True} for name in targets]

        results = []
        file_sync = FileSync()

        # Execution order: BOUND (0) → default SYMLINK/COPY (1) → override SYMLINK/COPY (2)
        # override = true => personal dotfiles that replace devcontainer defaults
        def _sort_key(item: tuple[str, Any]) -> int:
            p = item[1]
            if isinstance(p, FileProvision) and (p.mode or "").upper() == "BOUND":
                return 0
            if isinstance(p, FileProvision) and p.override:
                return 2
            return 1

        ordered = sorted(targets.items(), key=_sort_key)
        total = len(ordered)

        for i, (name, provision) in enumerate(ordered, 1):
            n = f"[{i}/{total}]"
            if isinstance(provision, PackageProvision):
                self._log(_V1, f"{n} {name}  [{provision.provider}: {provision.package or name}]")
            else:
                self._log(_V1, f"{n} {name}")
            t0 = time.monotonic()
            if isinstance(provision, FileProvision) and verb in ("sync", "link"):
                r = file_sync.execute(provision)
            elif isinstance(provision, PackageProvision) and verb == "install":
                r = self._package_install.execute(provision)
            else:
                results.append({"name": name, "verb": verb, "ok": True, "status": "dispatched"})
                self._log(_V2, f"  DISPATCH {name}")
                continue

            elapsed = time.monotonic() - t0
            ok = r.status.value != "failed"
            results.append({
                "name": name,
                "verb": verb,
                "ok": ok,
                "status": r.status.value,
                "message": r.message,
            })
            if r.status.value == "failed":
                msg = f"[proviso]   FAILED   {n} {name}: {r.message} ({elapsed:.1f}s)"
                print(msg, file=sys.stderr)
                if self._log_fh is not None:
                    print(msg, file=self._log_fh, flush=True)
            elif r.status.value == "skipped":
                self._log(_V2, f"  SKIP     {n} {name}: {r.message} ({elapsed:.1f}s)")
            else:
                self._log(_V1, f"  OK       {n} {name}: {r.message} ({elapsed:.1f}s)")

        return results
