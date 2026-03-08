"""Generate / sync the proviso-managed mounts block in devcontainer.json.

Reads BOUND FileProvisions from the manifest and rewrites the section between:

    // [proviso:mounts:begin]
    ...
    // [proviso:mounts:end]

Run on the host before committing devcontainer.json changes:

    parcel gen-devcontainer -m .devcontainer/config/manifest.conf \\
                            --devcontainer .devcontainer/devcontainer.json
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from proviso.provisions.models import FileProvision

_BEGIN = "// [proviso:mounts:begin]"
_END   = "// [proviso:mounts:end]"

_PATTERN = re.compile(
    r"(\s*// \[proviso:mounts:begin\]).*?(// \[proviso:mounts:end\])",
    re.DOTALL,
)


def _to_devcontainer_path(raw: str) -> str:
    """Translate ~/… or $HOME/… to devcontainer ${localEnv:HOME}/… syntax."""
    if raw.startswith("~/"):
        return "${localEnv:HOME}/" + raw[2:]
    if raw.startswith("$HOME/"):
        return "${localEnv:HOME}/" + raw[6:]
    return raw


def _mount_string(provision: FileProvision) -> str:
    src  = _to_devcontainer_path(str(provision.src))
    dest = str(provision.destination)
    return f'source={src},target={dest},type=bind,consistency=cached,optional=true'


def gen_devcontainer(manifest_path: Path, devcontainer_path: Path) -> list[str]:
    """Patch devcontainer.json mounts from BOUND provisions. Returns names of patched provisions."""
    from proviso.manifest.scanner import ManifestScanner
    from proviso.markup import create_default_registry
    from proviso.provisions.models import FileProvision

    markup    = create_default_registry()
    scanner   = ManifestScanner(markup)
    provisions = scanner.scan(manifest_path)

    bound = [
        p for p in provisions
        if isinstance(p, FileProvision) and (p.mode or "").upper() == "BOUND"
    ]

    indent = "    "
    lines = [f"{indent}{_BEGIN} — managed by `parcel gen-devcontainer`, do not edit"]
    for p in bound:
        lines.append(f'{indent}"{_mount_string(p)}",')
    lines.append(f"{indent}{_END}")
    block = "\n".join(lines)

    content = devcontainer_path.read_text()
    if _BEGIN not in content:
        raise ValueError(
            f"Marker '{_BEGIN}' not found in {devcontainer_path}.\n"
            f"Add '{_BEGIN}' and '{_END}' comments inside the mounts array."
        )

    new_content = _PATTERN.sub(lambda _: "\n" + block, content)
    devcontainer_path.write_text(new_content)

    return [p.name for p in bound]
