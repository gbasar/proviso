"""FileSync action — materialises a FileProvision on disk.

Modes:
    SYMLINK  ln -s src destination   idempotent: skip if link already correct
    COPY     cp -r src destination   idempotent: skip if dest exists
    BOUND    mount --bind src destination  requires root; skip if already mounted
"""

from __future__ import annotations

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

        if provision.src is None:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.action_name,
                resource_name=provision.name,
                message="src is required for file-sync",
            )

        src = Path(provision.src).expanduser()
        dest = Path(provision.destination).expanduser()

        match mode:
            case "SYMLINK":
                return self._symlink(provision.name, src, dest)
            case "COPY":
                return self._copy(provision.name, src, dest)
            case "BOUND":
                return self._bound(provision.name, src, dest)

    # ------------------------------------------------------------------

    def _symlink(self, name: str, src: Path, dest: Path) -> ActionResult:
        if dest.is_symlink():
            if dest.resolve() == src.resolve():
                return ActionResult(
                    status=ActionStatus.SKIPPED,
                    action_name=self.action_name,
                    resource_name=name,
                    message="symlink already correct",
                )
            dest.unlink()

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(src)
        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.action_name,
            resource_name=name,
            message=f"symlinked {dest} → {src}",
        )

    def _copy(self, name: str, src: Path, dest: Path) -> ActionResult:
        if dest.exists():
            return ActionResult(
                status=ActionStatus.SKIPPED,
                action_name=self.action_name,
                resource_name=name,
                message="destination already exists",
            )

        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.action_name,
            resource_name=name,
            message=f"copied {src} → {dest}",
        )

    def _bound(self, name: str, src: Path, dest: Path) -> ActionResult:
        if not src.exists():
            return ActionResult(
                status=ActionStatus.SKIPPED,
                action_name=self.action_name,
                resource_name=name,
                message=f"source absent, skipping ({src})",
            )

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
            ["mount", "--bind", str(src), str(dest)],
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
            message=f"bind-mounted {src} → {dest}",
        )
