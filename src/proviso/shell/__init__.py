"""Shell abstraction — I/O boundary for subprocess calls."""

from proviso.shell.fake import FakeShell
from proviso.shell.protocol import Shell, ShellResult
from proviso.shell.subprocess import SubprocessShell

__all__ = ["FakeShell", "Shell", "ShellResult", "SubprocessShell"]
