## hey buddy isd this stilll relvantg?

# proviso — Dev Container Context

> Written for AI assistants and human developers picking up this project.
> Covers architecture, every key decision made, and the reasoning behind each.

---

## What this project is

**proviso** — a Python package (`uv`-managed, Python 3.12+) that is a universal declarative resource lifecycle manager. CLI entry point: `parcel` via `proviso.cli.main:main`. Source in `src/`, tests in `tests/`.

---

## Dev Container Architecture

### File layout

```
proviso/
├── Dockerfile.tools          ← slow build: all OS + cargo/go/pip tool compilation
├── Dockerfile.devcontainer   ← fast build: FROM tools image, adds non-root user
├── build.sh                  ← orchestrates both builds, manages cache
├── .devcontainer/
│   ├── devcontainer.json     ← VS Code dev container spec
│   ├── setup.sh              ← postCreateCommand: symlinks, plugins, uv sync
│   └── config/               ← ALL shell/editor configs live here (version-controlled)
│       ├── starship.toml
│       ├── fish/config.fish
│       ├── nushell/config.nu
│       ├── nushell/env.nu
│       ├── nvim/init.lua
│       ├── vim/.vimrc
│       └── modern-linux-utils.conf
└── .ai/
    └── CONTEXT.md            ← this file
```

### Two-image split (the most important architectural decision)

```
Dockerfile.tools          ~30-60 min cold build
  └── pushed to registry  registry.corp.com/dev-tools:latest

Dockerfile.devcontainer   ~5 seconds
  └── FROM tools image
  └── adds non-root user only
```

**Why:** cargo compilation is slow. Separating the heavy work means:
- Developers never wait for compilation — they pull the tools image
- CI rebuilds the devcontainer in seconds
- Only one person (or CI) ever recompiles tools, when the tool list changes

---

## Key Decisions and Their Reasoning

### 1. Base image: UBI9, flexible via `ARG BASE_IMAGE`

```dockerfile
ARG BASE_IMAGE=registry.access.redhat.com/ubi9/ubi
FROM ${BASE_IMAGE}
```

**Why:** Company requires Red Hat UBI9. The `ARG` allows swapping in a hardened corporate base image without changing the Dockerfile. The devcontainer layers on top of whatever the company provides.

In `build.sh`: `BASE_IMAGE=registry.corp.com/ubi9-hardened:latest ./build.sh`

---

### 2. No binary downloads — company policy

**Rule:** Nothing installed via `curl | sh`, GitHub tarball, or direct binary URL.
**Allowed:** `dnf`, `cargo`, `pip`, `go install`.

| What changed | Before | After |
|---|---|---|
| `uv` | `curl astral.sh/uv/install.sh \| sh` | `pip install uv` |
| `starship` | `curl starship.rs/install.sh \| sh` | `cargo install starship` |
| `neovim` | GitHub tarball download | `dnf install neovim` (EPEL) |
| `nushell` | GitHub tarball download | `cargo install nu` |
| `fzf` | GitHub tarball download | `dnf install fzf` (EPEL) |
| `fd` | GitHub tarball download | `cargo install fd-find` |

---

### 3. EPEL vs cargo: always prefer EPEL

Every package in EPEL 9 that we use was moved OUT of cargo. This reduces build time and avoids compilation failures.

| Package | Source | Reason not cargo |
|---|---|---|
| `neovim` | dnf (EPEL) | Available, saves ~5 min |
| `fzf` | dnf (EPEL) | Available, saves ~3 min |
| `ripgrep` | dnf (EPEL) | Available, saves ~3 min |
| `zoxide` | dnf (EPEL) | Available, saves ~2 min |
| `hyperfine` | dnf (EPEL) | Available, saves ~2 min |
| `btop` | dnf (EPEL) | Available |
| `direnv` | dnf (EPEL) | Available |
| `rclone` | dnf (EPEL) | Available |
| `aria2` | dnf (EPEL) | Available |

Everything else is cargo-only (no EPEL package on RHEL9):
`starship, nu, fd-find, eza, bat, broot, sd, git-delta, procs, du-dust, bandwhich, gitui, xh, dog, zellij, atuin, tealdeer, tokei, just`

Go-only (no cargo, no EPEL):
`lazygit, duf`

---

### 4. Parallel cargo installs (xargs -P)

**Problem:** 17 cargo crates × ~3-5 min each = 60-90 min sequential.

**Solution:** `xargs -P 6` with `--jobs 2` per crate.

```bash
_install() {
    CARGO_TARGET_DIR="/cargo-targets/${1}" \
        cargo install --locked --root /usr/local --jobs 2 "${1}"
}
export -f _install
printf "%s\n" "${CRATES[@]}" | xargs -P 6 -I{} bash -c "_install {}"
```

**Why per-crate target dirs:** A shared `CARGO_TARGET_DIR` causes cargo file-lock contention between parallel processes, effectively serializing them again. Separate dirs per crate = true parallelism. Shared dependencies (tokio, serde) get recompiled per crate, but this is acceptable given the parallelism gain.

**Why `export -f`:** `xargs` spawns subshells. Functions must be exported to be visible in those subshells. Requires bash (not sh).

**Why nushell stays separate:** It's the heaviest build (~15 min). Its own Docker layer means its cache isn't busted when other crates change.

**Result:** ~30-35 min total vs ~90 min sequential.

---

### 5. BuildKit cache mounts — keep cargo registry between builds

```dockerfile
RUN --mount=type=cache,target=/root/.cargo/registry \
    --mount=type=cache,target=/root/.cargo/git \
    --mount=type=cache,id=cargo-tools,target=/cargo-targets \
    bash -c '...'
```

**What this does:** When a Docker layer is invalidated and must be re-run, the cargo registry (downloaded crate tarballs) and compiled artifacts are still there from last time. Incremental recompilation kicks in instead of a full rebuild.

**Requires:** `# syntax=docker/dockerfile:1` at the top of the Dockerfile (enables BuildKit syntax). Set `DOCKER_BUILDKIT=1` in CI if not default.

**Important:** Cache mount IDs (`cargo-registry`, `cargo-tools`) are **global** — shared across ALL projects on the same Docker daemon. `tokio` compiled for one project is reused by another.

---

### 6. Universal cache at `~/.cache/devcontainer/`

```bash
_xdg_cache="${XDG_CACHE_HOME:-$HOME/.cache}"
CACHE_DIR="${DEV_CACHE_DIR:-${_xdg_cache}/devcontainer}/buildx"
```

**Why not `.cache/` in the project:** cargo registry, Go modules, pip wheels are not project-specific. They should be shared across all devcontainer projects on a machine.

**Override:** `DEV_CACHE_DIR=/mnt/shared/cache ./build.sh` for NFS or shared build servers.

The `--cache-from/--cache-to type=local` in `build.sh` saves the full Docker layer cache (including compiled binaries) at this path. It survives `docker system prune` because it's on the host filesystem.

---

### 7. Dockerfile multi-line bash strings: the parser gotcha

The Docker parser scans **every line that isn't a continuation (`\`)** for instruction keywords — including lines inside a `bash -c '...'` string. Any bare word at the start of a line triggers it.

Affected keywords seen so far: `name=` (fish repo file), `set` (`set -e` in cargo scripts).

```dockerfile
# WRONG — "set -e" on its own line → Docker sees SET instruction
RUN bash -c '
    set -e
    cargo install ...
'

# WRONG — "name=..." on its own line → Docker sees NAME instruction
RUN echo '[section]
name=value' > file.conf

# CORRECT for bash scripts — heredoc content is never scanned
RUN bash <<'EOF'
set -e
cargo install ...
EOF

# CORRECT for writing config files — each line preceded by "echo"
RUN { \
    echo '[section]'; \
    echo 'name=value'; \
    } > file.conf
```

**Rule of thumb:** Use `bash <<'EOF' ... EOF` for any multi-line shell script in a RUN instruction. Use grouped `echo` only when writing config file content.

---

### 8. Shell and editor configs are version-controlled

All configs live in `.devcontainer/config/` and are **symlinked** (not copied) into `$HOME` by `setup.sh`. Changes to configs are immediately reflected in running containers without rebuild.

```
~/.config/fish/config.fish  →  /workspace/.devcontainer/config/fish/config.fish
~/.config/nvim/init.lua     →  /workspace/.devcontainer/config/nvim/init.lua
~/.config/starship.toml     →  /workspace/.devcontainer/config/starship.toml
...
```

---

### 9. `~/.devbox/bin/<category>/` symlinks

Tools are symlinked by category matching the keys in `modern-linux-utils.conf`:

```
~/.devbox/bin/
├── file-navigation/   eza bat zoxide broot
├── search/            rg fd fzf
├── text-processing/   jq yq sd delta
├── monitoring/        btop procs duf dust bandwhich
├── git-tools/         lazygit gitui delta
├── networking/        http xh dog
├── shell/             starship tmux zellij atuin tldr nu fish
├── file-transfer/     rclone aria2c
└── dev-productivity/  tokei hyperfine just direnv
```

Created by `_link()` in `setup.sh` using `command -v` to find the binary regardless of whether it landed in `/usr/bin` (dnf) or `/usr/local/bin` (cargo). Missing tools are skipped with a warning, not a fatal error.

---

### 10. Bind mount — what it actually means

```
devcontainer.json:
"workspaceMount": "source=${localWorkspaceFolder},target=/workspace,type=bind"
```

No copying. The kernel presents the same directory tree to both the host and the container. A file save in VS Code on the Mac IS the file the container reads. Zero latency, one copy of data. The container provides the runtime; the host provides the source.

---

## Shells and tools installed

| Shell | Default | Config |
|---|---|---|
| fish | yes (default) | `.devcontainer/config/fish/config.fish` + fisher plugins |
| nushell | no | `.devcontainer/config/nushell/config.nu` + `env.nu` |
| zsh | no | system default |
| bash | no | system default |

| Editor | Config |
|---|---|
| nvim | `.devcontainer/config/nvim/init.lua` (lazy.nvim, pyright LSP, telescope) |
| vim | `.devcontainer/config/vim/.vimrc` (vim-plug, ALE+ruff) |

**Prompt:** starship — configured at `.devcontainer/config/starship.toml`, active in all four shells.

---

## Modern Linux Utils catalog

`.devcontainer/config/modern-linux-utils.conf` — HOCON format, 32 tools across 9 categories. Schema per entry:

```hocon
tool-name {
  replaces = "legacy-tool"
  description = "..."
  install { method = cargo|dnf|pip|go, package = "..." }
  priority = 1|2|3          # 3 = essential
  enabled = true
  tags = ["cli", "rust", ...]
  grade = "A+"               # letter grade
  help {
    tldr = "tldr tool-name"
    aliases = ["ll = eza -l"]
    try = ["eza -la --tree"]
  }
}
```

---

## How to build

```bash
# First time or when tool list changes:
./build.sh --push-tools

# Fast rebuild (tools image already built):
./build.sh

# Use a pre-built tools image from registry:
TOOLS_IMAGE=registry.corp.com/dev-tools:latest ./build.sh

# Override base image:
BASE_IMAGE=registry.corp.com/ubi9-hardened:latest ./build.sh

# Run the container manually:
docker run -it --rm \
  --mount type=bind,source=$(pwd),target=/workspace \
  proviso-dev:latest
```

---

## What `setup.sh` does (postCreateCommand, runs once)

1. Symlinks all configs from repo into `$HOME`
2. Installs fisher + fish plugins
3. Installs vim-plug + vim plugins
4. Pre-installs neovim plugins via `nvim --headless "+Lazy! sync" +qa`
5. Runs `uv sync --all-extras`
6. Creates `~/.devbox/bin/<category>/` symlinks
