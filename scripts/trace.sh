#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# scripts/trace.sh — Run proviso under viztracer inside the tools image.
#
# Traces all three provision types in one container run:
p
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
MANIFEST=".devcontainer/config/manifest.conf"

echo ""
echo "━━━ Tracing proviso under viztracer ━━━"
echo "  Image:    $TOOLS_TAG"
echo "  Manifest: $MANIFEST"
echo ""

echo "  [1/2] package install"
docker run --rm \
    --mount type=bind,source="$REPO_ROOT",target=/workspace \
    "$TOOLS_TAG" \
    viztracer --output_file /workspace/trace-packages.json -- \
        proviso -vv \
            -m "/workspace/$MANIFEST" \
            package install

echo ""
echo "  [2/2] file sync"
docker run --rm \
    --mount type=bind,source="$REPO_ROOT",target=/workspace \
    "$TOOLS_TAG" \
    viztracer --output_file /workspace/trace-dotfiles.json -- \
        proviso -vv \
            -m "/workspace/$MANIFEST" \
            file sync

echo ""
echo "━━━ Done ━━━"
echo "  trace-packages.json  →  vizviewer $REPO_ROOT/trace-packages.json"
echo "  trace-dotfiles.json  →  vizviewer $REPO_ROOT/trace-dotfiles.json"
