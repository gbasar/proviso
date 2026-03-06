"""Output formatting — structured text for pipes, markup for --format."""

from __future__ import annotations

from typing import Any

from proviso.markup import create_default_registry


def format_output(results: list[dict[str, Any]], fmt: str = "text") -> str:
    """Format results for output."""
    if not results:
        return ""

    if fmt == "text":
        return _format_text(results)

    # Use markup subsystem for structured formats
    markup = create_default_registry()
    adapter = markup.get_by_name(fmt)
    return adapter.write_string({"results": results})


def _format_text(results: list[dict[str, Any]]) -> str:
    """One resource per line, pipe-friendly."""
    lines = []
    for r in results:
        name = r.get("name", "")
        rtype = r.get("type", "")
        verb = r.get("verb", "")
        status = r.get("status", "")
        schedule = r.get("schedule", "")

        parts = [name]
        if rtype:
            parts.append(rtype)
        if verb:
            parts.append(verb)
        if status:
            parts.append(status)
        if schedule:
            parts.append(f"[{schedule}]")

        lines.append("\t".join(parts))
    return "\n".join(lines)
