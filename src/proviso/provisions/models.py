"""Provision models — typed, self-describing, immutable records.

Three provision types:
    PackageProvision — any installable package (dnf, apt, brew, pip, cargo, maven, npm, gem)
    SourceProvision  — git repos (http/https or ssh)
    FileProvision    — files, symlinks, bind mounts

All share a common base (name, description, tags, schedule, metadata).
Each defines its own src/destination with the appropriate Python type —
Path for files, a validated git URI string for source repos.
No shared base field is typed as Any.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator


# --- Common Protocol (wide shape) ---

@runtime_checkable
class Provisionlike(Protocol):
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


# --- Frozen base ---

class _ProvisionBase(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    name: str
    description: str | None = None
    schedule: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Concrete provision models ---

class PackageProvision(_ProvisionBase):
    """Any installable package — system or language-level."""

    provision_type: Literal[ProvisionKind.PACKAGE] = ProvisionKind.PACKAGE
    provider: str                  # "dnf", "apt", "brew", "pip", "cargo", "maven", "npm", "gem"
    package: str | None = None     # install identifier when it differs from name
    version: str | None = None
    destination: Path | None = None
    links: tuple[Path, ...] = ()
    get_latest: bool = False
    post_install: str | None = None  # shell command run after a successful install


class SourceProvision(_ProvisionBase):
    """A git repository — third-party dependency or own code."""

    provision_type: Literal[ProvisionKind.SOURCE] = ProvisionKind.SOURCE
    repo: str                      # git URL — http(s):// or git@host:path or ssh://
    destination: Path              # clone target
    branch: str = "main"
    compile_cmd: str | None = None
    get_latest: bool = False

    @field_validator("repo")
    @classmethod
    def _repo_is_git_uri(cls, v: str) -> str:
        if not (
            v.startswith("https://")
            or v.startswith("http://")
            or v.startswith("ssh://")
            or v.startswith("git@")
        ):
            raise ValueError(
                f"repo must be an http(s):// URL or git@host:path SSH URI, got: {v!r}"
            )
        return v


class FileProvision(_ProvisionBase):
    """A file, symlink, or bind mount."""

    provision_type: Literal[ProvisionKind.FILE] = ProvisionKind.FILE
    destination: Path              # where it lands on disk
    src: Path | str | None = None  # where it comes from (not required for bare file refs)
    mode: str | None = None        # SYMLINK | COPY | BOUND


# --- Discriminated union ---

AnyProvision = Annotated[
    PackageProvision | SourceProvision | FileProvision,
    Field(discriminator="provision_type"),
]


# --- Backwards compatibility aliases ---
BinaryProvision = PackageProvision
LibraryProvision = PackageProvision
