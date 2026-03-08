"""Parcel CLI — load manifest, select provisions, dispatch through pipelines.

Usage:
    proviso cat package list
    proviso cat package jq install -vvv
    proviso cat package list --tag=dev
    proviso cat source list --scheduled
    proviso cat file trading-hosts status
    proviso cat list
    echo "jq" | proviso cat package install --stdin
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from proviso.cli.dispatch import Dispatcher
from proviso.cli.output import format_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proviso",
        description="Universal declarative provision lifecycle manager.",
    )
    parser.add_argument(
        "-m",
        "--manifest",
        default="manifest.conf",
        help="Path to manifest file (default: manifest.conf)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity: -v, -vv, -vvv",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "yaml", "hocon", "toml"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read provision names from stdin",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without doing it",
    )
    parser.add_argument(
        "--log-file",
        metavar="PATH",
        help="Write OK/FAIL/SKIP lines to this file (in addition to stderr)",
    )

    parser.add_argument(
        "--devcontainer",
        metavar="PATH",
        default=".devcontainer/devcontainer.json",
        help="Path to devcontainer.json (used by gen-devcontainer)",
    )
    parser.add_argument("command", nargs="*", help="cat <type> [name] [verb]  |  gen-devcontainer")

    return parser


def parse_command(args: list[str]) -> dict[str, str | None]:
    """Parse positional args into catalog, type, name, verb."""
    result: dict[str, str | None] = {
        "catalog": None,
        "provision_type": None,
        "name": None,
        "verb": None,
    }

    if not args:
        return result

    if args[0] == "cat":
        result["catalog"] = "cat"
        args = args[1:]

    if not args:
        return result

    types = {"package", "source", "file", "host"}
    verbs = {"list", "install", "uninstall", "sync", "status", "info", "connect", "link"}

    if args[0] in types:
        result["provision_type"] = args[0]
        args = args[1:]
    elif args[0] in verbs:
        result["verb"] = args[0]
        return result

    if not args:
        return result

    if args[0] in verbs:
        result["verb"] = args[0]
        args = args[1:]
    else:
        result["name"] = args[0]
        args = args[1:]

    if not args:
        return result

    if args[0] in verbs:
        result["verb"] = args[0]

    return result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)

    if args.command and args.command[0] == "gen-devcontainer":
        from proviso.devcontainer.gen import gen_devcontainer
        devcontainer_path = Path(args.devcontainer)
        try:
            patched = gen_devcontainer(manifest_path, devcontainer_path)
            print(f"Updated {devcontainer_path} with {len(patched)} BOUND mount(s): {', '.join(patched)}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0

    cmd = parse_command(args.command)

    stdin_names: list[str] = []
    if args.stdin and not sys.stdin.isatty():
        stdin_names = [line.strip() for line in sys.stdin if line.strip()]

    dispatcher = Dispatcher(
        manifest_path=manifest_path,
        verbosity=args.verbose,
        output_format=args.format,
        dry_run=args.dry_run,
        log_file=Path(args.log_file) if args.log_file else None,
    )

    try:
        results = dispatcher.run(
            provision_type=cmd["provision_type"],
            name=cmd["name"],
            verb=cmd["verb"] or "list",
            stdin_names=stdin_names,
        )
    except FileNotFoundError:
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = format_output(results, fmt=args.format)
    if output:
        print(output)

    return 0 if all(r.get("ok", True) for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
