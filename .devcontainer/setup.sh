#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# postCreateCommand — runs ONCE when the container is first created.
# Symlinks all configs from the repo into $HOME so they're version-controlled.
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"

step() { echo ""; echo "━━━ $* ━━━"; }

# ── 1. Dotfile symlinks (managed by proviso) ─────────────────────────────────
step "Linking configs"
export PROVISION_LIST=/workspace/.devcontainer/config/manifest.conf
uv run proviso -vvv -m "$PROVISION_LIST" file sync
echo "  configs linked"

# ── 2. Python project dependencies ───────────────────────────────────────────
step "Installing Python dependencies (uv sync)"

cd /workspace
uv sync --all-extras

echo "  Python deps ready at /workspace/.venv"

# ── 6. Print welcome ─────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Dev container ready                                 ║"
echo "║                                                      ║"
echo "║  Shells:   fish (default)  nu  zsh  bash             ║"
echo "║  Editors:  nvim  vim                                 ║"
echo "║  Prompt:   starship (all shells)                     ║"
echo "║                                                      ║"
echo "║  Quick commands:                                     ║"
echo "║    uvt          → uv run pytest                      ║"
echo "║    uvc          → uv run ruff check .                ║"
echo "║    uvf          → uv run ruff format .               ║"
echo "║    lg           → lazygit                            ║"
echo "║    j --list     → list justfile recipes              ║"
echo "║                                                      ║"
echo "║  Browse tools by category:                           ║"
echo "║    ls ~/.devbox/bin/                                 ║"
echo "║    ls ~/.devbox/bin/dev-productivity                 ║"
echo "╚══════════════════════════════════════════════════════╝"
