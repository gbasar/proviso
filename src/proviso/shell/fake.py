"""In-memory shell for tests.

Scripted responses, records all commands run.
Percival & Gregory style — real Protocol implementation, fake I/O.
"""

from __future__ import annotations

from proviso.shell.protocol import ShellResult


class FakeShell:
    """Test double: returns scripted responses, records commands."""

    def __init__(self, responses: dict[str, ShellResult] | None = None) -> None:
        self._responses = responses or {}
        self._default = ShellResult(returncode=0)
        self.commands_run: list[str] = []

    def run(self, command: str) -> ShellResult:
        self.commands_run.append(command)
        return self._responses.get(command, self._default)
