"""Shell port — the I/O boundary for subprocess calls.

Actions and providers never call subprocess directly.
They depend on this Protocol, which is injected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ShellResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def success(self) -> bool:
        return self.returncode == 0


@runtime_checkable
class Shell(Protocol):
    def run(self, command: str) -> ShellResult: ...
