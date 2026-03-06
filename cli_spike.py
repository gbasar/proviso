"""
CLI Framework Spike — proviso package install jq
Same command implemented four ways. Compare and pick.

Run: uv run python cli_spike.py
"""

# ============================================================
# 1. CLICK — the standard
# ============================================================

CLICK_EXAMPLE = '''
import click
import json as json_lib

@click.group()
def cli():
    """Proviso — universal resource lifecycle manager."""
    pass

@cli.group()
def package():
    """Package resource operations."""
    pass

@package.command()
@click.argument("name")
@click.option("--json", "json_override", default=None, help="JSON override for resource fields")
@click.option("--dry-run", is_flag=True, help="Show what would happen without doing it")
@click.option("--tag", multiple=True, help="Filter by tag")
def install(name: str, json_override: str | None, dry_run: bool, tag: tuple[str, ...]):
    """Install a package resource."""
    overrides = json_lib.loads(json_override) if json_override else {}
    if dry_run:
        click.echo(f"[dry-run] Would install {name} with overrides={overrides}")
        return
    click.echo(f"Installing {name}...")

# Usage:
#   proviso package install jq
#   proviso package install jq --json '{"provider": "apt"}' --dry-run
'''

# ============================================================
# 2. TYPER — type-hint driven, built on click
# ============================================================

TYPER_EXAMPLE = '''
import typer
import json as json_lib
from typing import Annotated, Optional

app = typer.Typer(help="Proviso — universal resource lifecycle manager.")
package_app = typer.Typer(help="Package resource operations.")
app.add_typer(package_app, name="package")

@package_app.command()
def install(
    name: str,
    json: Annotated[Optional[str], typer.Option(help="JSON override")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would happen")] = False,
    tag: Annotated[Optional[list[str]], typer.Option(help="Filter by tag")] = None,
):
    """Install a package resource."""
    overrides = json_lib.loads(json) if json else {}
    if dry_run:
        typer.echo(f"[dry-run] Would install {name} with overrides={overrides}")
        return
    typer.echo(f"Installing {name}...")

# Usage: same as click
# Pros: less boilerplate, type hints ARE the schema
# Cons: sub-typer wiring is slightly awkward, Optional handling has quirks
'''

# ============================================================
# 3. CYCLOPTS — bleeding edge, Pydantic-native
# ============================================================

CYCLOPTS_EXAMPLE = '''
import cyclopts
import json as json_lib
from typing import Annotated

app = cyclopts.App(name="proviso", help="Universal resource lifecycle manager.")
package_app = cyclopts.App(name="package", help="Package resource operations.")
app.command(package_app)

@package_app.command()
def install(
    name: str,
    *,
    json: Annotated[str | None, cyclopts.Parameter(help="JSON override")] = None,
    dry_run: Annotated[bool, cyclopts.Parameter(name="--dry-run", help="Show what would happen")] = False,
    tag: Annotated[list[str] | None, cyclopts.Parameter(help="Filter by tag")] = None,
):
    """Install a package resource."""
    overrides = json_lib.loads(json) if json else {}
    if dry_run:
        print(f"[dry-run] Would install {name} with overrides={overrides}")
        return
    print(f"Installing {name}...")

# Usage: same as click
# Pros: cleanest type hints, Pydantic model validation built-in,
#        can accept a Pydantic model directly as CLI input
# Cons: smallest community, youngest project
'''

# ============================================================
# 4. CAPPA — declarative CLI via dataclasses
# ============================================================

CAPPA_EXAMPLE = '''
from __future__ import annotations
import cappa
import json as json_lib
from dataclasses import dataclass

@dataclass
@cappa.command(name="install", help="Install a package resource.")
class Install:
    name: str
    json: str | None = cappa.Arg(default=None, long="--json", help="JSON override")
    dry_run: bool = cappa.Arg(default=False, long="--dry-run", help="Show what would happen")
    tag: list[str] = cappa.Arg(default_factory=list, long="--tag", help="Filter by tag")

    def __call__(self):
        overrides = json_lib.loads(self.json) if self.json else {}
        if self.dry_run:
            print(f"[dry-run] Would install {self.name} with overrides={overrides}")
            return
        print(f"Installing {self.name}...")

@dataclass
@cappa.command(name="package", help="Package resource operations.")
class Package:
    subcommand: cappa.Subcommands[Install]

@dataclass
@cappa.command(name="proviso", help="Universal resource lifecycle manager.")
class Proviso:
    subcommand: cappa.Subcommands[Package]

# Entry: cappa.invoke(Proviso)
# Usage: same as click
# Pros: CLI IS a data structure, very declarative, composable,
#        each command is a callable dataclass — testable without CLI
# Cons: unfamiliar pattern, nesting gets verbose, smallest ecosystem
'''

# ============================================================
# COMPARISON
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CLI FRAMEWORK COMPARISON — proviso package install jq")
    print("=" * 70)

    frameworks = {
        "click": {
            "code": CLICK_EXAMPLE,
            "boilerplate": "medium",
            "type_driven": False,
            "pydantic_native": False,
            "community": "massive",
            "maturity": "battle-tested (10+ years)",
            "sub_commands": "clean nested groups",
            "testing": "CliRunner built-in",
            "bleeding_edge": False,
        },
        "typer": {
            "code": TYPER_EXAMPLE,
            "boilerplate": "low",
            "type_driven": True,
            "pydantic_native": False,
            "community": "large",
            "maturity": "stable (4+ years)",
            "sub_commands": "add_typer — slightly awkward",
            "testing": "CliRunner inherited from click",
            "bleeding_edge": False,
        },
        "cyclopts": {
            "code": CYCLOPTS_EXAMPLE,
            "boilerplate": "lowest",
            "type_driven": True,
            "pydantic_native": True,
            "community": "small",
            "maturity": "young (2+ years)",
            "sub_commands": "app.command(sub_app) — clean",
            "testing": "invoke built-in",
            "bleeding_edge": True,
        },
        "cappa": {
            "code": CAPPA_EXAMPLE,
            "boilerplate": "low (but verbose nesting)",
            "type_driven": True,
            "pydantic_native": False,
            "community": "tiny",
            "maturity": "young (1+ year)",
            "sub_commands": "Subcommands[] — declarative but nested",
            "testing": "commands are callable dataclasses — best testability",
            "bleeding_edge": True,
        },
    }

    for name, info in frameworks.items():
        print(f"\n{'—' * 70}")
        print(f"  {name.upper()}")
        print(f"{'—' * 70}")
        for key, val in info.items():
            if key != "code":
                print(f"  {key:20s}: {val}")
        print(f"\n  CODE:")
        print(info["code"])

    print("=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    print("""
  For proviso specifically:

  cyclopts — if you want bleeding edge + Pydantic native.
             Our models are already Pydantic. Cyclopts can validate
             CLI input directly against them. Lowest boilerplate.
             Risk: small community, your team may not know it.

  typer    — if you want modern + safe. Team will pick it up fast.
             Good docs, large community, type-hint driven.
             Risk: none. It's the safe modern choice.

  cappa    — if you love the declarative philosophy hardest.
             CLI-as-data-structure is beautiful and very testable.
             Risk: smallest ecosystem, nesting gets verbose.

  click    — if your team already knows it. No learning curve.
             Risk: more boilerplate, not type-driven.
""")
