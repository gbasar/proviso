"""Shared utilities used across proviso modules."""

from __future__ import annotations

_COMPRESSED_SUFFIXES = {".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".zip"}


def is_compressed_suffix(filename: str) -> bool:
    """Return True if filename ends with a recognised archive extension."""
    name = filename.lower()
    return any(name.endswith(s) for s in _COMPRESSED_SUFFIXES)
