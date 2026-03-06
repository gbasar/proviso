"""Provider port — platform-specific package manager adapters.

Each provider knows how to install, remove, update, and check status
for packages in its ecosystem. Providers never decide *what* to do —
actions decide that. Providers know *how*.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class PackageStatus(StrEnum):
    INSTALLED = "installed"
    MISSING = "missing"
    OUTDATED = "outdated"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderResult:
    status: PackageStatus
    message: str = ""
    version: str = ""


@runtime_checkable
class PackageProvider(Protocol):
    """Structural type for package manager adapters."""

    @property
    def provider_name(self) -> str: ...

    def is_available(self) -> bool:
        """Can this provider run on the current system?"""
        ...

    def status(self, package_name: str) -> ProviderResult: ...

    def install(self, package_name: str) -> ProviderResult: ...

    def update(self, package_name: str) -> ProviderResult: ...

    def remove(self, package_name: str) -> ProviderResult: ...
