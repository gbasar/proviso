"""Real shell adapter — delegates to subprocess."""

from __future__ import annotations

import subprocess

from proviso.shell.protocol import ShellResult


class SubprocessShell:
    """Production shell that runs real commands."""

    def run(self, command: str) -> ShellResult:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )
        return ShellResult(
            returncode=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
        )
