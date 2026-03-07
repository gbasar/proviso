"""Provision models — typed, self-describing, immutable records.

Three provision types:
    PackageProvision — any installable package (dnf, apt, brew, pip, cargo, maven, npm, gem)
    SourceProvision  — git repos (third-party or own code)
    FileProvision    — everything else (host lists, SSH keys, configs, symlinks, notes)

All satisfy the Provisionlike Protocol, which is the wide shape
that actions like Logger can accept.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

# --- Common Protocol (wide shape) ---


@runtime_checkable
class Provisionlike(Protocol):
    """Structural type satisfied by all provisions.

    Wide shape — actions like Logger accept anything matching this.
    """

    @property
    def name(self) -> str: ...

    @property
    def provision_type(self) -> str: ...

    @property
    def schedule(self) -> str | None: ...


# --- Provision kind discriminator ---


class ProvisionKind(StrEnum):
    PACKAGE = "package"
    SOURCE = "source"
    FILE = "file"


# --- Frozen base config ---


class _ProvisionBase(BaseModel):
    """Shared config. Not a base class for inheritance — just DRY for field defs."""

    model_config = {"frozen": True, "extra": "forbid"}

    name: str
    schedule: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Concrete provision models ---


class PackageProvision(_ProvisionBase):
    """Any installable package — system or language-level.

    ``package`` is the identifier passed to the installer (e.g. "fd-find" for
    the ``fd`` tool). Defaults to ``name`` when the two are the same.
    """

    provision_type: Literal[ProvisionKind.PACKAGE] = ProvisionKind.PACKAGE
    provider: str  # "dnf", "apt", "brew", "pip", "cargo", "maven", "npm", "gem"
    package: str | None = None  # install arg; falls back to name when None
    version: str | None = None
    destination: Path | None = None
    links: tuple[Path, ...] = ()
    get_latest: bool = False


class SourceProvision(_ProvisionBase):
    """A git repository — third-party dependency or own code."""

    provision_type: Literal[ProvisionKind.SOURCE] = ProvisionKind.SOURCE
    repo: str  # git URL
    target: Path  # clone destination
    branch: str = "main"
    compile_cmd: str | None = None
    get_latest: bool = False


class FileProvision(_ProvisionBase):
    """A file — host list, SSH key, config, symlink, notes, anything."""

    provision_type: Literal[ProvisionKind.FILE] = ProvisionKind.FILE
    path: Path
    origin: Path | str | None = None  # where it comes from
    mode: str | None = None  # SYMLINK, COPY, BOUND


# --- Discriminated union for deserialization ---

AnyProvision = Annotated[
    PackageProvision | SourceProvision | FileProvision,
    Field(discriminator="provision_type"),
]


# --- Backwards compatibility aliases ---
BinaryProvision = PackageProvision
LibraryProvision = PackageProvision
