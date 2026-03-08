#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# scripts/trace.sh — Run proviso under viztracer inside the tools image.
#
# Traces all three provision types in one container run:
#   1. package install  (modern-linux-utils.conf)
#   2. file sync        (dotfiles.conf)
#
# Usage:
#   ./scripts/trace.sh                         # uses proviso-dev-tools:latest
#   TOOLS_TAG=my-image:tag ./scripts/trace.sh  # override image
#
# Output:
#   trace-packages.json  — package install pass
#   trace-dotfiles.json  — file sync pass
# View:
#   viztracer trace-packages.json
#   viztracer trace-dotfiles.json
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_TAG="${TOOLS_TAG:-proviso-dev-tools:latest}"
PACKAGES_CONF=".devcontainer/config/provisions/modern-linux-utils.conf"
DOTFILES_CONF=".devcontainer/config/provisions/dotfiles.conf"

echo ""
echo "━━━ Tracing proviso under viztracer ━━━"
echo "  Image: $TOOLS_TAG"
echo ""

echo "  [1/2] package install ($PACKAGES_CONF)"
docker run --rm \
    --mount type=bind,source="$REPO_ROOT",target=/workspace \
    "$TOOLS_TAG" \
    viztracer --output_file /workspace/trace-packages.json -- \
        proviso -vv \
            -m "/workspace/$PACKAGES_CONF" \
            package install

echo ""
echo "  [2/2] file sync ($DOTFILES_CONF)"
docker run --rm \
    --mount type=bind,source="$REPO_ROOT",target=/workspace \
    "$TOOLS_TAG" \
    viztracer --output_file /workspace/trace-dotfiles.json -- \
        proviso -vv \
            -m "/workspace/$DOTFILES_CONF" \
            file sync

echo ""
echo "━━━ Done ━━━"
echo "  trace-packages.json  →  viztracer $REPO_ROOT/trace-packages.json"
echo "  trace-dotfiles.json  →  viztracer $REPO_ROOT/trace-dotfiles.json"
