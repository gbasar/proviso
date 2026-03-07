"""Manifest subsystem — loads catalog files into typed resource objects."""

from proviso.manifest.loader import ManifestError, ManifestLoader

__all__ = ["ManifestLoader", "ManifestError"]
