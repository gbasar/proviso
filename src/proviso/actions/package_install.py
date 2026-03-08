"""PackageInstall action — installs or updates any package provision.

Accepts PackageProvision. Resolves provider by name,
delegates the actual work. Idempotent — checks status first.

method=file is handled directly here (not via a provider) because it
needs access to loc and symlinks from the full provision.
"""

from __future__ import annotations

import shutil
import tarfile
import zipfile
from pathlib import Path

from proviso.actions.protocol import ActionResult, ActionStatus, ShapeMismatchError
from proviso.providers.protocol import PackageStatus
from proviso.providers.registry import ProviderRegistry
from proviso.provisions.models import PackageProvision
from proviso.shell.protocol import Shell


class PackageInstall:
    """Install or update a package via its declared provider."""

    def __init__(self, providers: ProviderRegistry, shell: Shell) -> None:
        self._providers = providers
        self._shell = shell

    @property
    def action_name(self) -> str:
        return "package-install"

    def execute(self, provision: PackageProvision) -> ActionResult:
        if not isinstance(provision, PackageProvision):
            raise ShapeMismatchError(
                f"{self.action_name} accepts PackageProvision, got {type(provision).__name__}"
            )

        if provision.provider == "file":
            return self._install_file(provision)

        provider = self._providers.get(provision.provider)
        name = provision.name
        package = provision.package or name

        if provision.get_latest:
            result = provider.update(package)
        else:
            current = provider.status(package)
            if current.status == PackageStatus.INSTALLED:
                return ActionResult(
                    status=ActionStatus.SKIPPED,
                    action_name=self.action_name,
                    resource_name=name,
                    message="already installed",
                )
            result = provider.install(package)

        if result.status == PackageStatus.INSTALLED:
            if provision.post_install:
                post = self._shell.run(provision.post_install)
                if not post.success:
                    return ActionResult(
                        status=ActionStatus.FAILED,
                        action_name=self.action_name,
                        resource_name=name,
                        message=f"post_install failed: {post.stderr}",
                    )
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action_name=self.action_name,
                resource_name=name,
                message=result.message,
            )

        return ActionResult(
            status=ActionStatus.FAILED,
            action_name=self.action_name,
            resource_name=name,
            message=result.message,
        )

    def _install_file(self, provision: PackageProvision) -> ActionResult:
        name = provision.name

        if not provision.loc:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.action_name,
                resource_name=name,
                message="method=file requires loc",
            )

        src = Path(provision.loc).expanduser()
        if not src.exists():
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.action_name,
                resource_name=name,
                message=f"file not found: {src}",
            )

        # Idempotent: if all symlink targets already exist, skip
        if provision.symlinks and all(
            Path(s.dest).expanduser().exists() for s in provision.symlinks
        ):
            return ActionResult(
                status=ActionStatus.SKIPPED,
                action_name=self.action_name,
                resource_name=name,
                message="already installed",
            )

        # Extract archive to temp dir, then apply symlinks
        extract_dir = Path(f"/tmp/proviso-{name}")
        extract_dir.mkdir(parents=True, exist_ok=True)

        suffix = "".join(src.suffixes)
        if suffix in (".tar.gz", ".tgz") or src.name.endswith(".tar.gz"):
            with tarfile.open(src, "r:gz") as tf:
                tf.extractall(extract_dir)
        elif suffix == ".tar.bz2":
            with tarfile.open(src, "r:bz2") as tf:
                tf.extractall(extract_dir)
        elif suffix == ".zip":
            with zipfile.ZipFile(src) as zf:
                zf.extractall(extract_dir)
        else:
            # Single binary — copy directly
            dest = extract_dir / src.name
            shutil.copy2(src, dest)
            dest.chmod(0o755)

        # Apply symlinks
        for link in provision.symlinks:
            link_src = self._find_file(extract_dir, Path(link.src).name)
            link_dest = Path(link.dest).expanduser()
            if link_src is None:
                shutil.rmtree(extract_dir, ignore_errors=True)
                return ActionResult(
                    status=ActionStatus.FAILED,
                    action_name=self.action_name,
                    resource_name=name,
                    message=f"binary not found in archive: {link.src}",
                )
            link_dest.parent.mkdir(parents=True, exist_ok=True)
            if link_dest.exists() or link_dest.is_symlink():
                link_dest.unlink()
            link_dest.symlink_to(link_src)

        shutil.rmtree(extract_dir, ignore_errors=True)

        if provision.post_install:
            post = self._shell.run(provision.post_install)
            if not post.success:
                return ActionResult(
                    status=ActionStatus.FAILED,
                    action_name=self.action_name,
                    resource_name=name,
                    message=f"post_install failed: {post.stderr}",
                )

        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.action_name,
            resource_name=name,
            message=f"installed from {src.name}",
        )

    def _find_file(self, root: Path, name: str) -> Path | None:
        """Recursively find a file by name under root."""
        for match in root.rglob(name):
            if match.is_file():
                return match
        return None
