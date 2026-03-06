"""Markup subsystem — format-agnostic serialization layer.

Usage:
    from proviso.markup import create_default_registry

    registry = create_default_registry()
    data = registry.read_file(Path("config.hocon"))
    registry.write_file(data, Path("output.yaml"))
"""

from proviso.markup.protocol import MarkupAdapter
from proviso.markup.registry import MarkupRegistry, create_default_registry

__all__ = ["MarkupAdapter", "MarkupRegistry", "create_default_registry"]
