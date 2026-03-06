# ══════════════════════════════════════════════════════════════════════════════
# Fish config — ~/.config/fish/config.fish
#
# Plugins (installed by setup.sh via fisher):
#   jorgebucaran/fisher           — plugin manager
#   jethrokuan/z                  — smart directory jumping (frecency)
#   PatrickF1/fzf.fish            — fzf integration: Ctrl-R history, Ctrl-F files,
#                                   Ctrl-Alt-F git log, Alt-S git status
#   jorgebucaran/autopair.fish    — auto-close brackets/quotes in shell
#   nickeb96/puffer-fish          — !! and !$ expansion like bash
#   franciscolourenco/done        — desktop notification when long cmd finishes
#   gazorby/fish-abbreviation-tips— hints when you type a full command that has
#                                   a shorter abbreviation
# ══════════════════════════════════════════════════════════════════════════════

# ── Starship prompt ───────────────────────────────────────────────────────────
if command -q starship
    starship init fish | source
end

# ── Environment ──────────────────────────────────────────────────────────────
set -gx EDITOR nvim
set -gx VISUAL nvim
set -gx PAGER less
set -gx LESS "-R --quit-if-one-screen"
set -gx LANG en_US.UTF-8
set -gx LC_ALL en_US.UTF-8

# uv — avoid symlinking into read-only locations
set -gx UV_LINK_MODE copy

# PATH additions (idempotent via fish_add_path)
fish_add_path ~/.local/bin
fish_add_path /usr/local/bin

# fzf.fish — configure colours and behaviour
set -gx FZF_DEFAULT_OPTS "\
  --height 40% \
  --layout=reverse \
  --border \
  --color=bg+:#313244,bg:#1e1e2e,spinner:#f5e0dc,hl:#f38ba8 \
  --color=fg:#cdd6f4,header:#f38ba8,info:#cba6f7,pointer:#f5e0dc \
  --color=marker:#f5e0dc,fg+:#cdd6f4,prompt:#cba6f7,hl+:#f38ba8"

set -gx FZF_DEFAULT_COMMAND "fd --type f --hidden --follow --exclude .git"

# ── Abbreviations ─────────────────────────────────────────────────────────────
# Abbreviations expand in-place as you type — smarter than aliases because
# you can see and edit what will run before pressing Enter.

# Git
abbr -a g    git
abbr -a gs   git status
abbr -a ga   git add
abbr -a gaa  'git add -A'
abbr -a gc   git commit
abbr -a gcm  'git commit -m'
abbr -a gca  'git commit --amend'
abbr -a gp   git push
abbr -a gpl  git pull
abbr -a gl   'git log --oneline --graph --decorate -20'
abbr -a gd   git diff
abbr -a gds  'git diff --staged'
abbr -a gb   git branch
abbr -a gco  git checkout
abbr -a gsw  git switch
abbr -a gst  git stash

# Editors
abbr -a v    nvim
abbr -a vi   nvim
abbr -a vim  nvim

# Navigation
abbr -a ll   'ls -la'
abbr -a la   'ls -A'
abbr -a ..   'cd ..'
abbr -a ...  'cd ../..'
abbr -a .... 'cd ../../..'

# uv / Python project shortcuts (tailored to this repo)
abbr -a uvs  'uv sync --all-extras'
abbr -a uvr  'uv run'
abbr -a uvt  'uv run pytest'
abbr -a uvtv 'uv run pytest -v'
abbr -a uvtc 'uv run pytest --cov=src --cov-report=term-missing'
abbr -a uvc  'uv run ruff check .'
abbr -a uvf  'uv run ruff format .'
abbr -a uvm  'uv run mypy src'
abbr -a uvb  'uv build'

# ── Key bindings ──────────────────────────────────────────────────────────────
# fzf.fish handles Ctrl-R (history) and Ctrl-F (files) automatically.
# Add extra bindings here if needed:
# bind \ce 'nvim .'     # Ctrl-E → open nvim in current dir

# ── Functions ─────────────────────────────────────────────────────────────────
# mkcd: create directory and cd into it
function mkcd --description "mkdir + cd"
    mkdir -p $argv[1] && cd $argv[1]
end

# up N: go up N directories
function up --description "cd up N directories"
    set n (math (count $argv) == 0 ? 1 : $argv[1])
    set path ""
    for i in (seq 1 $n)
        set path "$path../"
    end
    cd $path
end

# extract: decompress anything
function extract --description "Extract any archive"
    switch $argv[1]
        case '*.tar.gz' '*.tgz'
            tar -xzf $argv[1]
        case '*.tar.bz2'
            tar -xjf $argv[1]
        case '*.tar.xz'
            tar -xJf $argv[1]
        case '*.zip'
            unzip $argv[1]
        case '*.gz'
            gunzip $argv[1]
        case '*'
            echo "Unknown archive: $argv[1]"
    end
end

# test: run pytest with nice output (project-specific)
function t --description "Run pytest"
    uv run pytest $argv
end

# ── Completions ──────────────────────────────────────────────────────────────
# Fish has built-in completions for git, curl, etc.
# Generate completions for uv on first run if not present:
if not test -f ~/.config/fish/completions/uv.fish
    uv generate-shell-completion fish > ~/.config/fish/completions/uv.fish 2>/dev/null
end
