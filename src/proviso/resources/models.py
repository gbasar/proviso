"""Resource models — typed, self-describing, immutable records.

Four resource types:
    BinaryResource  — system packages (dnf, apt, brew)
    LibraryResource — language packages (pip, cargo, maven, npm, gem)
    SourceResource  — git repos (third-party or own code)
    FileResource    — everything else (host lists, SSH keys, configs, symlinks, notes)

All satisfy the Resourcelike Protocol, which is the wide shape
that actions like Logger can accept.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

# --- Common Protocol (wide shape) ---


@runtime_checkable
class Resourcelike(Protocol):
    """Structural type satisfied by all resources.

    Wide shape — actions like Logger accept anything matching this.
    """

    @property
    def name(self) -> str: ...

    @property
    def resource_type(self) -> str: ...

    @property
    def schedule(self) -> str | None: ...


# --- Resource kind discriminator ---


class ResourceKind(StrEnum):
    BINARY = "binary"
    LIBRARY = "library"
    SOURCE = "source"
    FILE = "file"


# --- Frozen base config ---


class _ResourceBase(BaseModel):
    """Shared config. Not a base class for inheritance — just DRY for field defs.

    Each concrete model composes these fields. Actions never reference this type,
    they reference concrete models or the Resourcelike Protocol.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    name: str
    schedule: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Concrete resource models ---


class BinaryResource(_ResourceBase):
    """A binary installed via system package manager (dnf, apt, brew)."""

    resource_type: Literal[ResourceKind.BINARY] = ResourceKind.BINARY
    provider: str  # "dnf", "apt", "brew"
    destination: Path
    links: tuple[Path, ...] = ()
    get_latest: bool = False


class LibraryResource(_ResourceBase):
    """A language-level package (pip, cargo, maven, npm, gem, go)."""

    resource_type: Literal[ResourceKind.LIBRARY] = ResourceKind.LIBRARY
    provider: str  # "pip", "cargo", "maven", "npm", "gem", "go"
    version: str | None = None
    get_latest: bool = False


class SourceResource(_ResourceBase):
    """A git repository — third-party dependency or own code."""

    resource_type: Literal[ResourceKind.SOURCE] = ResourceKind.SOURCE
    repo: str  # git URL
    target: Path  # clone destination
    branch: str = "main"
    compile_cmd: str | None = None
    get_latest: bool = False


class FileResource(_ResourceBase):
    """A file — host list, SSH key, config, symlink, notes, anything."""

    resource_type: Literal[ResourceKind.FILE] = ResourceKind.FILE
    path: Path
    source: Path | str | None = None  # where it comes from (template, URL, etc.)
    symlink: bool = False  # if True, path is a symlink to source


# --- Discriminated union for deserialization ---

AnyResource = Annotated[
    BinaryResource | LibraryResource | SourceResource | FileResource,
    Field(discriminator="resource_type"),
]
