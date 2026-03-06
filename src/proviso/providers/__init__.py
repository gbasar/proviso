"""Package provider adapters."""

from proviso.providers.apt import AptProvider
from proviso.providers.dnf import DnfProvider
from proviso.providers.pip import PipProvider
from proviso.providers.protocol import PackageProvider, PackageStatus, ProviderResult
from proviso.providers.registry import ProviderRegistry

__all__ = [
    "AptProvider",
    "DnfProvider",
    "PackageProvider",
    "PackageStatus",
    "PipProvider",
    "ProviderRegistry",
    "ProviderResult",
]
