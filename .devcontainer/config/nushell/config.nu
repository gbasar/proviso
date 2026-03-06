# ══════════════════════════════════════════════════════════════════════════════
# Nushell config.nu
#
# Nushell is a structured-data shell — commands return typed tables, not text.
# Think of it as a shell where everything is a spreadsheet.
#
# There is no plugin manager; nushell plugins are compiled Rust binaries.
# The community script library (nu_scripts) provides completions + utilities.
# ══════════════════════════════════════════════════════════════════════════════

# ── Core settings ─────────────────────────────────────────────────────────────
$env.config = {
    show_banner: false

    history: {
        max_size:     100_000
        sync_on_enter: true
        file_format:  "sqlite"   # sqlite history enables dedup + search
        isolation:    false
    }

    completions: {
        case_sensitive: false
        quick:          true
        partial:        true
        algorithm:      "fuzzy"  # fuzzy > prefix matching
        external: {
            enable:   true
            max_results: 100
        }
    }

    cursor_shape: {
        emacs:     line
        vi_insert: line
        vi_normal: block
    }

    table: {
        mode:        rounded
        index_mode:  always
        show_empty:  true
        trim: {
            methodology: wrapping
            wrapping_try_keep_words: true
        }
    }

    ls: {
        use_ls_colors:  true
        clickable_links: true
    }

    rm: {
        always_trash: false
    }

    filesize: {
        metric:    false
        format:    "auto"
    }

    color_config: {
        separator:            white
        leading_trailing_space_bg: { attr: n }
        header:               { fg: green  attr: b }
        empty:                blue
        bool:                 { |b| if $b { "light_cyan" } else { "light_red" } }
        int:                  white
        filesize:             cyan
        duration:             white
        date:                 purple
        range:                white
        float:                white
        string:               white
        nothing:              white
        binary:               white
        cell-path:            white
        row_index:            { fg: green attr: b }
        record:               white
        list:                 white
        block:                white
        hints:                dark_gray
        search_result:        { fg: white bg: red }
        shape_and:            { fg: purple attr: b }
        shape_or:             { fg: purple attr: b }
        shape_pipe:           { fg: purple attr: b }
        shape_internalcall:   { fg: cyan   attr: b }
        shape_external:       cyan
        shape_externalarg:    green
        shape_literal:        blue
        shape_operator:       yellow
        shape_signature:      { fg: green  attr: b }
        shape_string:         green
        shape_string_interpolation: { fg: cyan attr: b }
        shape_variable:       purple
        shape_flag:           { fg: blue   attr: b }
        shape_custom:         green
        shape_keyword:        { fg: cyan   attr: b }
        shape_int:            { fg: purple attr: b }
        shape_float:          { fg: purple attr: b }
    }

    # Ctrl-R: fuzzy history search via fzf
    keybindings: [
        {
            name:     fuzzy_history
            modifier: control
            keycode:  char_r
            mode:     [emacs, vi_normal, vi_insert]
            event: {
                send: ExecuteHostCommand
                cmd: "commandline edit --replace (
                    history
                    | get command
                    | reverse
                    | uniq
                    | str join (char newline)
                    | fzf --scheme history --no-sort --height 40% --layout reverse
                    | str trim
                )"
            }
        }
        {
            name:     fuzzy_files
            modifier: control
            keycode:  char_f
            mode:     [emacs, vi_normal, vi_insert]
            event: {
                send: ExecuteHostCommand
                cmd: "commandline edit --insert (
                    fd --type f --hidden --exclude .git
                    | fzf --height 40% --layout reverse
                    | str trim
                )"
            }
        }
    ]

    hooks: {
        # Starship prompt (pre-prompt hook updates the prompt string)
        pre_prompt: [{ ||
            null  # starship is set via prompt commands below
        }]

        env_change: {
            PWD: [{ |before, after|
                null  # could add direnv hook here
            }]
        }
    }
}

# ── Starship prompt ───────────────────────────────────────────────────────────
# Starship integrates with nushell via prompt commands, not hooks
def create_left_prompt [] {
    starship prompt --cmd-duration $env.CMD_DURATION_MS $"--status=($env.LAST_EXIT_CODE)"
}

def create_right_prompt [] {
    ""
}

$env.PROMPT_COMMAND       = { create_left_prompt }
$env.PROMPT_COMMAND_RIGHT = { create_right_prompt }
$env.PROMPT_INDICATOR     = ""
$env.PROMPT_INDICATOR_VI_INSERT  = ": "
$env.PROMPT_INDICATOR_VI_NORMAL  = "> "
$env.PROMPT_MULTILINE_INDICATOR  = "::: "

# ── Aliases ───────────────────────────────────────────────────────────────────
# In nushell, aliases don't expand in-place (unlike fish abbreviations).
# Use them for short names for long commands.

alias ll   = ls -la
alias la   = ls -a
alias v    = nvim
alias vi   = nvim

alias g    = git
alias gs   = git status
alias ga   = git add
alias gp   = git push
alias gpl  = git pull
alias gd   = git diff
alias gds  = git diff --staged

# uv shortcuts
alias uvs  = uv sync --all-extras
alias uvr  = uv run
alias uvt  = uv run pytest
alias uvtv = uv run pytest -v
alias uvtc = uv run pytest --cov=src --cov-report=term-missing
alias uvc  = uv run ruff check .
alias uvf  = uv run ruff format .
alias uvm  = uv run mypy src

# ── Custom commands ───────────────────────────────────────────────────────────
# Nushell's strength: commands return structured data, not text.

# Show PATH as a clean table
def "show path" [] {
    $env.PATH | each { |p| {path: $p} } | table
}

# Git log as a structured table (not just text)
def glog [n: int = 20] {
    ^git log --pretty=format:"%h|%an|%ar|%s" -$n
    | lines
    | each { |line|
        let parts = ($line | split column "|" hash author time subject)
        $parts | get 0
    }
    | table
}

# Navigate up N directories
def up [n: int = 1] {
    let path = (1..$n | each { ".." } | str join "/")
    cd $path
}

# mkcd: make directory and enter it
def mkcd [dir: string] {
    mkdir $dir
    cd $dir
}

# Run pytest and show summary
def t [...args: string] {
    uv run pytest ...$args
}

# Quick project status
def status [] {
    print $"Branch: (^git branch --show-current)"
    print $"Python: (^uv run python --version)"
    print ""
    ^git status --short
}
