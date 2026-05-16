"""PackageInstall action — installs or updates any package provision.

Accepts PackageProvision. Resolves provider by name, delegates the actual work.
Idempotent — checks status first.

Fallback chain:
  1. If method_filter excludes the provider and fallback_urls exist → try fallbacks.
  2. If primary install fails and fallback_urls exist → try fallbacks in order.
  3. First successful fallback wins; all fail → FAILED.
"""

from __future__ import annotations

import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from proviso.actions.protocol import ActionResult, ActionStatus, ShapeMismatchError
from proviso.commons import is_compressed_suffix
from proviso.providers.protocol import PackageStatus
from proviso.providers.registry import ProviderRegistry
from proviso.provisions.models import PackageProvision
from proviso.shell.protocol import Shell

_INSTALL_BASE = Path.home() / ".local" / "share" / "proviso"


class PackageInstall:
    """Install or update a package via its declared provider."""

    def __init__(self, providers: ProviderRegistry, shell: Shell) -> None:
        self._providers = providers
        self._shell = shell

    @property
    def action_name(self) -> str:
        return "package-install"

    def execute(
        self,
        provision: PackageProvision,
        method_filter: frozenset[str] | None = None,
    ) -> ActionResult:
        if not isinstance(provision, PackageProvision):
            raise ShapeMismatchError(
                f"{self.action_name} accepts PackageProvision, got {type(provision).__name__}"
            )

        if method_filter is not None and provision.provider not in method_filter:
            if provision.fallback_urls:
                return self._try_fallbacks(
                    provision, f"method '{provision.provider}' not in allowed_methods"
                )
            return ActionResult(
                status=ActionStatus.SKIPPED,
                action_name=self.action_name,
                resource_name=provision.name,
                message=f"method '{provision.provider}' not in allowed_methods",
            )

        result = self._run_primary(provision)

        if result.status == ActionStatus.FAILED and provision.fallback_urls:
            return self._try_fallbacks(provision, "primary install failed")

        return result

    def _run_primary(self, provision: PackageProvision) -> ActionResult:
        if provision.provider == "file":
            return self._install_file(provision)
        if provision.provider == "cargo" and provision.repo:
            return self._install_cargo_git(provision)
        return self._install_via_provider(provision)

    def _try_fallbacks(self, provision: PackageProvision, reason: str) -> ActionResult:
        for url in provision.fallback_urls:
            result = self._install_from_url(url, provision)
            if result.status != ActionStatus.FAILED:
                return result
        return ActionResult(
            status=ActionStatus.FAILED,
            action_name=self.action_name,
            resource_name=provision.name,
            message=f"all fallbacks failed ({reason})",
        )

    def _install_via_provider(self, provision: PackageProvision) -> ActionResult:
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

    def _install_cargo_git(self, provision: PackageProvision) -> ActionResult:
        name = provision.name
        binary = provision.package or name

        check = self._shell.run("cargo install --list --root /usr/local")
        if check.success and f"\n{binary} v" in f"\n{check.stdout}":
            return ActionResult(
                status=ActionStatus.SKIPPED,
                action_name=self.action_name,
                resource_name=name,
                message="already installed",
            )

        result = self._shell.run(
            f"cargo install --git {provision.repo} {binary} --root /usr/local"
        )
        if not result.success:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.action_name,
                resource_name=name,
                message=result.stderr,
            )

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
            message="installed from git",
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
        return self._install_from_path(src, provision)

    def _install_from_url(self, url: str, provision: PackageProvision) -> ActionResult:
        name = provision.name
        raw = url.split("?")[0]
        suffixes = "".join(Path(raw).suffixes[-2:]) or ".tar.gz"
        tmp = Path(tempfile.mktemp(suffix=suffixes))
        try:
            urllib.request.urlretrieve(url, tmp)  # noqa: S310
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.action_name,
                resource_name=name,
                message=f"download failed ({url}): {exc}",
            )
        try:
            return self._install_from_path(tmp, provision, label=url)
        finally:
            tmp.unlink(missing_ok=True)

    def _install_from_path(
        self, src: Path, provision: PackageProvision, label: str | None = None
    ) -> ActionResult:
        name = provision.name

        if provision.symlinks and all(
            Path(s.dest).expanduser().exists() for s in provision.symlinks
        ):
            return ActionResult(
                status=ActionStatus.SKIPPED,
                action_name=self.action_name,
                resource_name=name,
                message="already installed",
            )

        extract_dir = provision.destination or (_INSTALL_BASE / name)
        extract_dir = Path(extract_dir).expanduser()
        extract_dir.mkdir(parents=True, exist_ok=True)

        if is_compressed_suffix(src.name):
            if src.name.endswith(".zip"):
                with zipfile.ZipFile(src) as zf:
                    zf.extractall(extract_dir)
            else:
                with tarfile.open(src) as tf:
                    tf.extractall(extract_dir)
        else:
            dest = extract_dir / src.name
            shutil.copy2(src, dest)
            dest.chmod(0o755)

        for link in provision.symlinks:
            link_src = self._find_file(extract_dir, Path(link.src).name)
            link_dest = Path(link.dest).expanduser()
            if link_src is None:
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

        if provision.post_install:
            post = self._shell.run(provision.post_install)
            if not post.success:
                return ActionResult(
                    status=ActionStatus.FAILED,
                    action_name=self.action_name,
                    resource_name=name,
                    message=f"post_install failed: {post.stderr}",
                )

        source_label = label or src.name
        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.action_name,
            resource_name=name,
            message=f"installed from {source_label}",
        )

    def _find_file(self, root: Path, name: str) -> Path | None:
        for match in root.rglob(name):
            if match.is_file():
                return match
        return None
