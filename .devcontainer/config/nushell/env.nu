# ══════════════════════════════════════════════════════════════════════════════
# Nushell env.nu — loaded before config.nu, sets environment variables
# ══════════════════════════════════════════════════════════════════════════════

# ── PATH ─────────────────────────────────────────────────────────────────────
$env.PATH = (
    $env.PATH
    | split row (char esep)
    | prepend [
        ($env.HOME | path join ".local" "bin")
        "/usr/local/bin"
    ]
    | uniq
)

# ── Editor / pager ────────────────────────────────────────────────────────────
$env.EDITOR  = "nvim"
$env.VISUAL  = "nvim"
$env.PAGER   = "less"
$env.LESS    = "-R --quit-if-one-screen"

# ── Locale ────────────────────────────────────────────────────────────────────
$env.LANG   = "en_US.UTF-8"
$env.LC_ALL = "en_US.UTF-8"

# ── uv ────────────────────────────────────────────────────────────────────────
$env.UV_LINK_MODE = "copy"

# ── fzf ───────────────────────────────────────────────────────────────────────
$env.FZF_DEFAULT_COMMAND = "fd --type f --hidden --follow --exclude .git"
$env.FZF_DEFAULT_OPTS = "--height 40% --layout=reverse --border"

# ── Starship ──────────────────────────────────────────────────────────────────
# starship init is handled in config.nu via hooks
$env.STARSHIP_SHELL = "nu"

# ── Prompt config for starship (required by starship init nu) ─────────────────
$env.STARSHIP_SESSION_KEY = (random chars --length 16)
