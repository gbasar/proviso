"""Provider registry — resolves the right provider for a resource."""

from __future__ import annotations

from proviso.providers.protocol import PackageProvider


class ProviderRegistry:
    """Holds all known providers. Resolves by name."""

    def __init__(self) -> None:
        self._providers: dict[str, PackageProvider] = {}

    def register(self, provider: PackageProvider) -> None:
        name = provider.provider_name
        if name in self._providers:
            msg = f"Provider '{name}' already registered"
            raise ValueError(msg)
        self._providers[name] = provider

    def get(self, name: str) -> PackageProvider:
        try:
            return self._providers[name]
        except KeyError:
            msg = f"Unknown provider: '{name}'. Available: {list(self._providers.keys())}"
            raise ValueError(msg) from None

    def available(self) -> dict[str, PackageProvider]:
        """Return only providers that are available on this system."""
        return {k: v for k, v in self._providers.items() if v.is_available()}

    @property
    def all_providers(self) -> list[str]:
        return list(self._providers.keys())
