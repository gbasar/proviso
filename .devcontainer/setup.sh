#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# postCreateCommand — runs ONCE when the container is first created.
# Symlinks all configs from the repo into $HOME so they're version-controlled.
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"

step() { echo ""; echo "━━━ $* ━━━"; }

# ── 1. Symlink all configs from the repo into $HOME ──────────────────────────
step "Linking configs"

mkdir -p \
    ~/.config/fish/functions \
    ~/.config/nushell \
    ~/.config/nvim \
    ~/.vim/autoload

ln -sf "$CONFIG_DIR/starship.toml"          ~/.config/starship.toml
ln -sf "$CONFIG_DIR/fish/config.fish"       ~/.config/fish/config.fish
ln -sf "$CONFIG_DIR/nushell/config.nu"      ~/.config/nushell/config.nu
ln -sf "$CONFIG_DIR/nushell/env.nu"         ~/.config/nushell/env.nu
ln -sf "$CONFIG_DIR/nvim/init.lua"          ~/.config/nvim/init.lua
ln -sf "$CONFIG_DIR/vim/.vimrc"             ~/.vimrc

echo "  configs linked"

# ── 2. Fisher + fish plugins ──────────────────────────────────────────────────
step "Installing fish plugins (fisher)"

fish -c "
  curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish \
    | source \
  && fisher install jorgebucaran/fisher \
  && fisher install jethrokuan/z \
  && fisher install PatrickF1/fzf.fish \
  && fisher install jorgebucaran/autopair.fish \
  && fisher install nickeb96/puffer-fish \
  && fisher install franciscolourenco/done \
  && fisher install gazorby/fish-abbreviation-tips
" && echo "  fish plugins installed"

# ── 3. vim-plug + plugins ─────────────────────────────────────────────────────
step "Installing vim-plug and plugins"

curl -fsSLo ~/.vim/autoload/plug.vim \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

# -E = ex mode (non-interactive), -s = silent, || true because vim exits non-zero
vim -E -s -u ~/.vimrc +PlugInstall +qall 2>/dev/null || true
echo "  vim plugins installed"

# ── 4. Neovim lazy.nvim pre-sync ─────────────────────────────────────────────
step "Pre-installing neovim plugins (lazy.nvim)"

# lazy.nvim bootstraps itself on first run; this pre-installs all plugins
nvim --headless "+Lazy! sync" +qa 2>/dev/null || true
echo "  nvim plugins installed"

# ── 5. Python project dependencies ───────────────────────────────────────────
step "Installing Python dependencies (uv sync)"

cd /workspace
uv sync --all-extras

echo "  Python deps ready at /workspace/.venv"

# ── 6. ~/.devbox/bin/<category>/ symlinks ────────────────────────────────────
# Each category dir mirrors the keys in modern-linux-utils.conf.
# Uses `command -v` so it works regardless of whether dnf put it in /usr/bin
# or cargo put it in /usr/local/bin. Missing tools are skipped, not fatal.
step "Creating ~/.devbox/bin/<category>/ symlinks"

DEVBOX="$HOME/.devbox/bin"

_link() {
    local category="$1"; shift
    local dir="$DEVBOX/$category"
    mkdir -p "$dir"
    for bin in "$@"; do
        local path
        path=$(command -v "$bin" 2>/dev/null) || { echo "  SKIP  $category/$bin (not found)"; continue; }
        ln -sf "$path" "$dir/$bin"
        echo "  LINK  $category/$bin -> $path"
    done
}

# Categories match the keys in modern-linux-utils.conf
_link file-navigation  eza bat zoxide broot
_link search           rg fd fzf
_link text-processing  jq yq sd delta
_link monitoring       btop procs duf dust bandwhich
_link git-tools        lazygit gitui delta
_link networking       http xh dog
_link shell            starship tmux zellij atuin tldr nu fish
_link file-transfer    rclone aria2c
_link dev-productivity tokei hyperfine just direnv

echo "  done → $DEVBOX"

# ── 7. Print welcome ─────────────────────────────────────────────────────────
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
