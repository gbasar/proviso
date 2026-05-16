#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# build.sh — Build the dev container image with universal host-side cache.
#
# Cache location (universal — NOT project-local):
#   ~/.cache/devcontainer/buildx/
#  XDG Base Directory Specification — a Linux standard that says user cache/config/data should live in ~/.cache, ~/.config, ~/.local/share instead of random dotfiles everywhere. XDG_CACHE_HOME lets you override where ~/.cache points.
#   Follows XDG: override with XDG_CACHE_HOME or DEV_CACHE_DIR env var.
#   Shared across ALL devcontainer projects on this machine.
#   cargo registry, go modules, pip wheels — all reused regardless of project.
#   Survives docker system prune. Shareable via rsync/NFS.
#
# Two modes:
#   ./build.sh                  → build from local source, cache universally
#   ./build.sh --push-tools     → also push tools base image to registry
#   TOOLS_IMAGE=... ./build.sh  → pull pre-built tools image instead of building
#
# Registry workflow (CI / team share):
#   First time / when tools change:
#     ./build.sh --push-tools
#   Every other time (fast, ~30 sec):
#     TOOLS_IMAGE=registry.corp.com/dev-tools:latest ./build.sh
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Universal cache — respects XDG, override with DEV_CACHE_DIR=...
_xdg_cache="${XDG_CACHE_HOME:-$HOME/.cache}"
_cache_base="${DEV_CACHE_DIR:-${_xdg_cache}/devcontainer}"
CACHE_DIR="${_cache_base}/buildx"
BIN_CACHE="${_cache_base}/bins"
TOOLS_TAG="${TOOLS_TAG:-proviso-dev-tools:latest}"
DEV_TAG="${DEV_TAG:-proviso-dev:latest}"
BASE_IMAGE="${BASE_IMAGE:-registry.access.redhat.com/ubi9/ubi}"
PUSH_TOOLS=false
TRACE=false
TEST=false
RUN_ONLY=false
VERBOSE=0
RUNTIME=orbstack   # orbstack (default, GUI native) | docker (Docker Desktop / work)

for arg in "$@"; do
    case "$arg" in
        --push-tools) PUSH_TOOLS=true ;;
        --trace)      TRACE=true ;;
        --test)       TEST=true ;;
        --run)        RUN_ONLY=true ;;
        --docker)     RUNTIME=docker ;;
        -v*)          VERBOSE=${#arg}; VERBOSE=$(( VERBOSE - 1 )) ;;  # -v=1, -vv=2, -vvv=3
        --help|-h)
            echo "Usage: ./build.sh [--push-tools] [--run] [--trace] [--test] [--docker] [-v|-vv|-vvv]"
            echo "  --push-tools       push tools image to registry after build"
            echo "  --run              skip build, just launch the container"
            echo "  --trace            run parcel under viztracer (saves trace.json)"
            echo "  --test             launch display tests (xeyes + gtk3-demo) simultaneously"
            echo "  --docker           use plain Docker (Docker Desktop / work); default is OrbStack"
            echo "  -v/-vv/-vvv        verbosity: plain build output / +docker args / +set -x"
            echo "  TOOLS_IMAGE=<img>  use pre-built tools image instead of building"
            echo "  BASE_IMAGE=<img>   override UBI9 base image"
            exit 0 ;;
    esac
done

[[ $VERBOSE -ge 3 ]] && set -x

mkdir -p "$CACHE_DIR" "$BIN_CACHE"

# ── Helpers ───────────────────────────────────────────────────────────────────
banner() { echo ""; echo "━━━ $* ━━━"; }
log()    { if [[ $VERBOSE -ge $1 ]]; then echo "  [v$1] ${*:2}"; fi; }
# log 1 "msg" → printed at -v; log 2 "msg" → -vv; log 3 "msg" → -vvv

# Populates display_args array and prints which display is active
detect_display() {
    display_args=()
    if [[ -n "${WAYLAND_DISPLAY:-}" && -S "${XDG_RUNTIME_DIR:-}/${WAYLAND_DISPLAY:-}" ]]; then
        display_args+=(
            -e WAYLAND_DISPLAY="$WAYLAND_DISPLAY"
            -e XDG_RUNTIME_DIR=/run/user/host
            --mount "type=bind,source=${XDG_RUNTIME_DIR},target=/run/user/host"
        )
        echo "  Display: Wayland ($WAYLAND_DISPLAY)"
    elif [[ -n "${DISPLAY:-}" && -d /tmp/.X11-unix ]]; then
        display_args+=(
            -e DISPLAY="$DISPLAY"
            --mount "type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix"
        )
        echo "  Display: X11 ($DISPLAY)"
    elif [[ "$RUNTIME" == "orbstack" ]]; then
        echo "  Display: none (headless — OrbStack handles GUI natively)"
    else
        echo "  Display: none (headless)"
    fi
}

cache_flags=(
    --cache-from "type=local,src=$CACHE_DIR"
    --cache-to   "type=local,dest=$CACHE_DIR,mode=max"
)
# progress=plain at -v or above; default (tty spinner) otherwise
[[ $VERBOSE -ge 1 ]] && progress_flag="--progress=plain" || progress_flag="--progress=auto"

if [[ "$RUN_ONLY" == "true" ]]; then
    banner "Skipping build — launching $DEV_TAG"
else

# ── Step 1: Build (or pull) the tools base image ─────────────────────────────
if [[ -n "${TOOLS_IMAGE:-}" ]]; then
    banner "Pulling pre-built tools image: $TOOLS_IMAGE"
    docker pull "$TOOLS_IMAGE"
    docker tag  "$TOOLS_IMAGE" "$TOOLS_TAG"
else
    if docker image inspect "$TOOLS_TAG" >/dev/null 2>&1; then
        banner "Tools image '$TOOLS_TAG' already exists — skipping heavy build"
        echo "  To force a rebuild: docker rmi $TOOLS_TAG && ./build.sh"
    else
    banner "Building tools base image (cargo/go/pip — heavy, cached)"
    echo "  Cache: $CACHE_DIR  (shared across all devcontainer projects)"
    docker buildx build \
        "${cache_flags[@]}" \
        --build-arg BASE_IMAGE="$BASE_IMAGE" \
        --progress=plain \
        --load \
        -f "$REPO_ROOT/Dockerfile.tools" \
        -t "$TOOLS_TAG" \
        "$REPO_ROOT"

    # Extract compiled binaries to host cache
    banner "Caching compiled binaries → $BIN_CACHE"
    docker run --rm \
        --mount "type=bind,source=$BIN_CACHE,target=/bin-cache" \
        "$TOOLS_TAG" \
        bash -c 'find /usr/local/bin -maxdepth 1 -type f -executable -exec cp {} /bin-cache/ \;'
    echo "  $(ls "$BIN_CACHE" | wc -l | tr -d ' ') binaries cached"

    if [[ "$PUSH_TOOLS" == "true" ]]; then
        banner "Pushing tools image to registry"
        docker push "$TOOLS_TAG"
        echo "  Pushed: $TOOLS_TAG"
        echo "  Others can now run: TOOLS_IMAGE=$TOOLS_TAG ./build.sh"
    fi
    fi  # end: image not found
fi

# ── Step 2: Build the dev container (fast — no cargo/go compiles here) ───────

banner "Building dev container image (fast)"
docker build \
    "$progress_flag" \
    --build-arg TOOLS_IMAGE="$TOOLS_TAG" \
    --build-arg USERNAME="$(whoami)" \
    --build-arg USER_UID="$(id -u)" \
    -f "$REPO_ROOT/Dockerfile.devcontainer" \
    -t "$DEV_TAG" \
    "$REPO_ROOT"

banner "Done"
echo "  Image:  $DEV_TAG"
echo "  Cache:  $CACHE_DIR  ($(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1) on disk)"
echo "  Bins:   $BIN_CACHE  ($(ls "$BIN_CACHE" 2>/dev/null | wc -l | tr -d ' ') files)"
echo ""

fi  # end RUN_ONLY skip

if [[ "$TRACE" == "true" ]]; then
    TOOLS_TAG="$TOOLS_TAG" bash "$REPO_ROOT/scripts/trace.sh"
elif [[ "$TEST" == "true" ]]; then
    detect_display
    banner "Display test — xeyes (X11) + gtk3-demo (Wayland/X11) — close both windows to exit"
    docker run --rm \
        "${display_args[@]}" \
        "$DEV_TAG" \
        bash -c 'xeyes & gtk3-demo; wait'
else
    detect_display

    # Resolve docker socket — check canonical locations in priority order.
    sock_args=()
    for _candidate in \
        "$HOME/.docker/run/docker.sock" \
        "/var/run/docker.sock" \
        "$HOME/.orbstack/run/docker.sock"; do
        _sock_src="$(readlink -f "$_candidate" 2>/dev/null || echo "")"
        if [[ -S "${_sock_src:-}" ]]; then
            sock_args+=(--mount "type=bind,source=${_sock_src},target=/var/run/docker.sock")
            log 2 "docker socket: ${_sock_src}"
            break
        fi
    done
    if [[ ${#sock_args[@]} -eq 0 ]]; then
        echo "  Warning: docker socket not found — docker-in-docker unavailable"
    fi

    # ~/.proviso/ — mount whole dir so dotfiles, packages, etc. are all accessible at /proviso/
    proviso_args=()
    if [[ -d "$HOME/.proviso" ]]; then
        proviso_args+=(--mount "type=bind,source=$HOME/.proviso,target=/proviso")
        log 1 "proviso dir: $HOME/.proviso → /proviso"
    fi

    log 2 "docker run args: display=${display_args[*]:-} sock=${sock_args[*]:-} proviso=${proviso_args[*]:-}"

    docker run -it --rm \
        --mount type=bind,source="$REPO_ROOT",target=/workspace \
        "${sock_args[@]+"${sock_args[@]}"}" \
        "${display_args[@]+"${display_args[@]}"}" \
        "${proviso_args[@]+"${proviso_args[@]}"}" \
        -p 9001:9001 \
        "$DEV_TAG" \
        bash -c '
            if [[ "${SKIP_SETUP:-}" != "1" ]]; then
                bash /workspace/.devcontainer/setup.sh
            fi
            exec "$(command -v fish || echo /bin/bash)"
        '
fi
