"""FileSync action — materialises a FileProvision on disk.

Modes:
    SYMLINK  ln -s origin path        idempotent: skip if link already correct
    COPY     cp -r origin path        idempotent: skip if dest exists
    BOUND    mount --bind origin path requires root; skip if already mounted
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from proviso.actions.protocol import ActionResult, ActionStatus, ShapeMismatchError
from proviso.provisions.models import FileProvision


class FileSync:
    """Materialise a FileProvision on disk according to its mode."""

    @property
    def action_name(self) -> str:
        return "file-sync"

    def execute(self, provision: FileProvision) -> ActionResult:
        if not isinstance(provision, FileProvision):
            raise ShapeMismatchError(
                f"{self.action_name} accepts FileProvision, got {type(provision).__name__}"
            )

        mode = (provision.mode or "").upper()
        if mode not in ("SYMLINK", "COPY", "BOUND"):
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.action_name,
                resource_name=provision.name,
                message=f"unknown mode {provision.mode!r}; expected SYMLINK, COPY, or BOUND",
            )

        if provision.origin is None:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.action_name,
                resource_name=provision.name,
                message="origin is required for file-sync",
            )

        origin = Path(provision.origin).expanduser()
        dest = Path(provision.path).expanduser()

        match mode:
            case "SYMLINK":
                return self._symlink(provision.name, origin, dest)
            case "COPY":
                return self._copy(provision.name, origin, dest)
            case "BOUND":
                return self._bound(provision.name, origin, dest)

    # ------------------------------------------------------------------

    def _symlink(self, name: str, origin: Path, dest: Path) -> ActionResult:
        if dest.is_symlink():
            if dest.resolve() == origin.resolve():
                return ActionResult(
                    status=ActionStatus.SKIPPED,
                    action_name=self.action_name,
                    resource_name=name,
                    message="symlink already correct",
                )
            dest.unlink()

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(origin)
        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.action_name,
            resource_name=name,
            message=f"symlinked {dest} → {origin}",
        )

    def _copy(self, name: str, origin: Path, dest: Path) -> ActionResult:
        if dest.exists():
            return ActionResult(
                status=ActionStatus.SKIPPED,
                action_name=self.action_name,
                resource_name=name,
                message="destination already exists",
            )

        dest.parent.mkdir(parents=True, exist_ok=True)
        if origin.is_dir():
            shutil.copytree(origin, dest)
        else:
            shutil.copy2(origin, dest)
        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.action_name,
            resource_name=name,
            message=f"copied {origin} → {dest}",
        )

    def _bound(self, name: str, origin: Path, dest: Path) -> ActionResult:
        # Check if already mounted
        try:
            mounts = Path("/proc/mounts").read_text()
            if str(dest) in mounts:
                return ActionResult(
                    status=ActionStatus.SKIPPED,
                    action_name=self.action_name,
                    resource_name=name,
                    message="already bind-mounted",
                )
        except FileNotFoundError:
            pass  # not on Linux — fall through

        dest.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["mount", "--bind", str(origin), str(dest)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.action_name,
                resource_name=name,
                message=result.stderr.strip() or "mount --bind failed",
            )
        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.action_name,
            resource_name=name,
            message=f"bind-mounted {origin} → {dest}",
        )
