-- ═══════════════════════════════════════════════════════════════════════════
-- Neovim config — init.lua
--
-- Plugin manager: lazy.nvim (auto-bootstraps on first launch)
--
-- Plugins:
--   catppuccin/nvim              — Catppuccin Mocha colorscheme
--   nvim-treesitter              — Semantic syntax highlighting + indenting
--   neovim/nvim-lspconfig        — LSP client (language servers)
--   williamboman/mason.nvim      — Install LSP servers / formatters from :Mason
--   williamboman/mason-lspconfig — Bridge: mason ↔ lspconfig
--   hrsh7th/nvim-cmp             — Completion engine
--   L3MON4D3/LuaSnip             — Snippet engine
--   rafamadriz/friendly-snippets — VSCode-style snippet collection
--   nvim-telescope/telescope.nvim— Fuzzy finder: files, grep, buffers, help
--   nvim-lualine/lualine.nvim    — Statusline
--   lewis6991/gitsigns.nvim      — Git diff signs in gutter + hunk actions
--   tpope/vim-fugitive           — Git commands (:Git status/blame/diff/push)
--   nvim-tree/nvim-tree.lua      — File explorer (<leader>e)
--   folke/which-key.nvim         — Pop-up hints for pending keybindings
--   windwp/nvim-autopairs        — Auto-close brackets and quotes
--   numToStr/Comment.nvim        — gcc to toggle comment, gc in visual
--   stevearc/conform.nvim        — Format on save (ruff for Python)
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Bootstrap lazy.nvim ──────────────────────────────────────────────────────
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
    vim.fn.system({
        "git", "clone", "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable",
        lazypath,
    })
end
vim.opt.rtp:prepend(lazypath)

-- ── Options ───────────────────────────────────────────────────────────────────
vim.g.mapleader       = " "
vim.g.maplocalleader  = " "

local opt = vim.opt
opt.number            = true
opt.relativenumber    = true
opt.tabstop           = 4
opt.shiftwidth        = 4
opt.expandtab         = true
opt.smartindent       = true
opt.wrap              = false
opt.ignorecase        = true
opt.smartcase         = true
opt.hlsearch          = false
opt.incsearch         = true
opt.termguicolors     = true
opt.scrolloff         = 8
opt.sidescrolloff     = 8
opt.signcolumn        = "yes"
opt.updatetime        = 250
opt.timeoutlen        = 300
opt.splitbelow        = true
opt.splitright        = true
opt.undofile          = true
opt.cursorline        = true
opt.mouse             = "a"
opt.clipboard         = "unnamedplus"   -- system clipboard
opt.completeopt       = "menu,menuone,noselect"
opt.pumheight         = 10             -- max items in completion menu
opt.fileencoding      = "utf-8"
opt.swapfile          = false
opt.backup            = false

-- ── Plugins ───────────────────────────────────────────────────────────────────
require("lazy").setup({

    -- ── Colorscheme ────────────────────────────────────────────────────────
    {
        "catppuccin/nvim",
        name     = "catppuccin",
        priority = 1000,
        config   = function()
            require("catppuccin").setup({
                flavour         = "mocha",
                transparent_background = false,
                integrations    = {
                    treesitter   = true,
                    telescope    = true,
                    gitsigns     = true,
                    nvimtree     = true,
                    cmp          = true,
                    mason        = true,
                    which_key    = true,
                    lualine      = true,
                },
            })
            vim.cmd.colorscheme("catppuccin-mocha")
        end,
    },

    -- ── Treesitter: semantic highlighting + indenting ──────────────────────
    {
        "nvim-treesitter/nvim-treesitter",
        build  = ":TSUpdate",
        config = function()
            require("nvim-treesitter.configs").setup({
                ensure_installed = {
                    "python", "lua", "bash", "json", "jsonc",
                    "toml", "yaml", "markdown", "markdown_inline",
                    "regex", "vim", "vimdoc",
                },
                highlight = { enable = true },
                indent    = { enable = true },
                incremental_selection = {
                    enable = true,
                    keymaps = {
                        init_selection    = "<C-space>",
                        node_incremental  = "<C-space>",
                        scope_incremental = "<C-s>",
                        node_decremental  = "<bs>",
                    },
                },
            })
        end,
    },

    -- ── Mason: install LSP servers / tools from inside nvim ───────────────
    {
        "williamboman/mason.nvim",
        config = function()
            require("mason").setup({ ui = { border = "rounded" } })
        end,
    },
    {
        "williamboman/mason-lspconfig.nvim",
        dependencies = { "williamboman/mason.nvim" },
        config = function()
            require("mason-lspconfig").setup({
                ensure_installed = {
                    "pyright",   -- Python type checking
                    "ruff",      -- Python linting + fast fixes (replaces ruff_lsp)
                    "lua_ls",    -- Lua (for editing this config)
                    "bashls",    -- bash/sh
                    "jsonls",    -- JSON with schema support
                    "yamlls",    -- YAML
                },
                automatic_installation = true,
            })
        end,
    },

    -- ── LSP: language server protocol client ──────────────────────────────
    {
        "neovim/nvim-lspconfig",
        dependencies = {
            "williamboman/mason-lspconfig.nvim",
            "hrsh7th/cmp-nvim-lsp",
        },
        config = function()
            local lspconfig    = require("lspconfig")
            local capabilities = require("cmp_nvim_lsp").default_capabilities()

            -- Shared on_attach: set keymaps when LSP attaches to a buffer
            local on_attach = function(_, bufnr)
                local map = function(keys, func, desc)
                    vim.keymap.set("n", keys, func, { buffer = bufnr, desc = desc })
                end
                local tb = require("telescope.builtin")
                map("gd",        tb.lsp_definitions,      "Go to definition")
                map("gr",        tb.lsp_references,        "Go to references")
                map("gI",        tb.lsp_implementations,   "Go to implementation")
                map("<leader>D", tb.lsp_type_definitions,  "Type definition")
                map("<leader>ds",tb.lsp_document_symbols,  "Document symbols")
                map("<leader>ws",tb.lsp_workspace_symbols, "Workspace symbols")
                map("<leader>rn",vim.lsp.buf.rename,       "Rename symbol")
                map("<leader>ca",vim.lsp.buf.code_action,  "Code action")
                map("K",         vim.lsp.buf.hover,        "Hover docs")
                map("[d",        vim.diagnostic.goto_prev, "Prev diagnostic")
                map("]d",        vim.diagnostic.goto_next, "Next diagnostic")
                map("<leader>e", vim.diagnostic.open_float,"Show diagnostic")
            end

            local servers = {
                pyright  = {},
                ruff     = {},
                bashls   = {},
                jsonls   = {},
                yamlls   = {
                    settings = { yaml = { keyOrdering = false } }
                },
                lua_ls   = {
                    settings = {
                        Lua = {
                            workspace = { checkThirdParty = false },
                            telemetry = { enable = false },
                            diagnostics = { globals = { "vim" } },
                        },
                    },
                },
            }

            for server, config in pairs(servers) do
                config.capabilities = capabilities
                config.on_attach    = on_attach
                lspconfig[server].setup(config)
            end

            -- Diagnostic display
            vim.diagnostic.config({
                virtual_text  = true,
                signs         = true,
                underline     = true,
                update_in_insert = false,
                severity_sort = true,
                float         = { border = "rounded", source = true },
            })
        end,
    },

    -- ── Completion ────────────────────────────────────────────────────────
    {
        "hrsh7th/nvim-cmp",
        event = "InsertEnter",
        dependencies = {
            "hrsh7th/cmp-nvim-lsp",
            "hrsh7th/cmp-buffer",
            "hrsh7th/cmp-path",
            "hrsh7th/cmp-cmdline",
            "L3MON4D3/LuaSnip",
            "saadparwaiz1/cmp_luasnip",
            "rafamadriz/friendly-snippets",
        },
        config = function()
            local cmp     = require("cmp")
            local luasnip = require("luasnip")
            require("luasnip.loaders.from_vscode").lazy_load()

            cmp.setup({
                snippet = {
                    expand = function(args) luasnip.lsp_expand(args.body) end,
                },
                window = {
                    completion    = cmp.config.window.bordered(),
                    documentation = cmp.config.window.bordered(),
                },
                mapping = cmp.mapping.preset.insert({
                    ["<C-n>"]     = cmp.mapping.select_next_item(),
                    ["<C-p>"]     = cmp.mapping.select_prev_item(),
                    ["<C-b>"]     = cmp.mapping.scroll_docs(-4),
                    ["<C-f>"]     = cmp.mapping.scroll_docs(4),
                    ["<C-Space>"] = cmp.mapping.complete(),
                    ["<C-e>"]     = cmp.mapping.abort(),
                    ["<CR>"]      = cmp.mapping.confirm({ select = true }),
                    ["<Tab>"]     = cmp.mapping(function(fallback)
                        if cmp.visible() then
                            cmp.select_next_item()
                        elseif luasnip.expand_or_jumpable() then
                            luasnip.expand_or_jump()
                        else
                            fallback()
                        end
                    end, { "i", "s" }),
                    ["<S-Tab>"]   = cmp.mapping(function(fallback)
                        if cmp.visible() then
                            cmp.select_prev_item()
                        elseif luasnip.jumpable(-1) then
                            luasnip.jump(-1)
                        else
                            fallback()
                        end
                    end, { "i", "s" }),
                }),
                sources = cmp.config.sources({
                    { name = "nvim_lsp", priority = 1000 },
                    { name = "luasnip",  priority = 750 },
                    { name = "buffer",   priority = 500 },
                    { name = "path",     priority = 250 },
                }),
            })

            -- Command-line completion
            cmp.setup.cmdline({ "/", "?" }, {
                mapping = cmp.mapping.preset.cmdline(),
                sources = { { name = "buffer" } },
            })
            cmp.setup.cmdline(":", {
                mapping = cmp.mapping.preset.cmdline(),
                sources = cmp.config.sources(
                    { { name = "path" } },
                    { { name = "cmdline" } }
                ),
            })
        end,
    },

    -- ── Telescope: fuzzy finder ───────────────────────────────────────────
    {
        "nvim-telescope/telescope.nvim",
        tag          = "0.1.x",
        dependencies = {
            "nvim-lua/plenary.nvim",
            {
                "nvim-telescope/telescope-fzf-native.nvim",
                build = "make",
                cond  = function() return vim.fn.executable("make") == 1 end,
            },
        },
        config = function()
            local telescope = require("telescope")
            local builtin   = require("telescope.builtin")

            telescope.setup({
                defaults = {
                    mappings = {
                        i = { ["<C-u>"] = false, ["<C-d>"] = false },
                    },
                    layout_config = { horizontal = { preview_width = 0.55 } },
                    file_ignore_patterns = { "%.git/", "%.venv/", "__pycache__" },
                },
            })

            pcall(telescope.load_extension, "fzf")

            local map = vim.keymap.set
            map("n", "<leader>ff", builtin.find_files,        { desc = "Find files" })
            map("n", "<leader>fg", builtin.live_grep,         { desc = "Live grep" })
            map("n", "<leader>fb", builtin.buffers,           { desc = "Buffers" })
            map("n", "<leader>fh", builtin.help_tags,         { desc = "Help tags" })
            map("n", "<leader>fr", builtin.oldfiles,          { desc = "Recent files" })
            map("n", "<leader>fs", builtin.grep_string,       { desc = "Grep word under cursor" })
            map("n", "<leader>fd", builtin.diagnostics,       { desc = "Diagnostics" })
            map("n", "<leader><leader>", builtin.buffers,     { desc = "Buffer switcher" })
            map("n", "<leader>/",  function()
                builtin.current_buffer_fuzzy_find(
                    require("telescope.themes").get_dropdown({ previewer = false })
                )
            end, { desc = "Fuzzy search buffer" })
        end,
    },

    -- ── Statusline ───────────────────────────────────────────────────────
    {
        "nvim-lualine/lualine.nvim",
        config = function()
            require("lualine").setup({
                options = {
                    theme             = "catppuccin",
                    component_separators = { left = "", right = "" },
                    section_separators  = { left = "", right = "" },
                    globalstatus      = true,
                },
                sections = {
                    lualine_a = { "mode" },
                    lualine_b = { "branch", "diff", "diagnostics" },
                    lualine_c = { { "filename", path = 1 } },
                    lualine_x = { "encoding", "fileformat", "filetype" },
                    lualine_y = { "progress" },
                    lualine_z = { "location" },
                },
            })
        end,
    },

    -- ── Git ───────────────────────────────────────────────────────────────
    {
        "lewis6991/gitsigns.nvim",
        config = function()
            require("gitsigns").setup({
                signs = {
                    add          = { text = "▎" },
                    change       = { text = "▎" },
                    delete       = { text = "" },
                    topdelete    = { text = "" },
                    changedelete = { text = "▎" },
                },
                on_attach = function(bufnr)
                    local gs  = package.loaded.gitsigns
                    local map = function(mode, l, r, desc)
                        vim.keymap.set(mode, l, r, { buffer = bufnr, desc = desc })
                    end
                    map("n", "]h", gs.next_hunk,             "Next hunk")
                    map("n", "[h", gs.prev_hunk,             "Prev hunk")
                    map("n", "<leader>hs", gs.stage_hunk,    "Stage hunk")
                    map("n", "<leader>hr", gs.reset_hunk,    "Reset hunk")
                    map("n", "<leader>hb", gs.blame_line,    "Blame line")
                    map("n", "<leader>hp", gs.preview_hunk,  "Preview hunk")
                    map("n", "<leader>hd", gs.diffthis,      "Diff this")
                end,
            })
        end,
    },
    { "tpope/vim-fugitive" },

    -- ── File tree ────────────────────────────────────────────────────────
    {
        "nvim-tree/nvim-tree.lua",
        config = function()
            vim.g.loaded_netrw       = 1
            vim.g.loaded_netrwPlugin = 1
            require("nvim-tree").setup({
                view          = { width = 35 },
                renderer      = {
                    group_empty = true,
                    icons       = { show = { git = true, folder = true, file = true } },
                },
                filters       = { dotfiles = false },
                git           = { enable = true },
                diagnostics   = { enable = true },
                actions       = { open_file = { quit_on_open = false } },
            })
            vim.keymap.set("n", "<leader>t", ":NvimTreeToggle<CR>", { desc = "Toggle file tree" })
            vim.keymap.set("n", "<leader>tf",":NvimTreeFindFile<CR>",{ desc = "Find current file in tree" })
        end,
    },

    -- ── Which-key: keybinding hints ───────────────────────────────────────
    {
        "folke/which-key.nvim",
        event  = "VeryLazy",
        config = function()
            require("which-key").setup({ window = { border = "rounded" } })
            -- Register group names for <leader> prefixes
            require("which-key").register({
                ["<leader>f"] = { name = "+find/files" },
                ["<leader>h"] = { name = "+git hunks" },
                ["<leader>t"] = { name = "+tree" },
                ["<leader>d"] = { name = "+diagnostics/defs" },
                ["<leader>w"] = { name = "+workspace" },
            })
        end,
    },

    -- ── Auto pairs ───────────────────────────────────────────────────────
    {
        "windwp/nvim-autopairs",
        event  = "InsertEnter",
        config = function()
            local autopairs = require("nvim-autopairs")
            autopairs.setup({ check_ts = true })
            -- Hook into cmp so <CR> selects completion AND inserts pair
            local cmp_autopairs = require("nvim-autopairs.completion.cmp")
            require("cmp").event:on("confirm_done", cmp_autopairs.on_confirm_done())
        end,
    },

    -- ── Comments ─────────────────────────────────────────────────────────
    -- gcc: toggle line comment, gc: toggle in visual, gcA: end-of-line comment
    { "numToStr/Comment.nvim", config = true, lazy = false },

    -- ── Formatting ───────────────────────────────────────────────────────
    {
        "stevearc/conform.nvim",
        event = "BufWritePre",
        config = function()
            require("conform").setup({
                formatters_by_ft = {
                    python = { "ruff_format", "ruff_fix" },
                    lua    = { "stylua" },
                    sh     = { "shfmt" },
                    json   = { "jq" },
                    yaml   = { "prettier" },
                    toml   = { "taplo" },
                },
                format_on_save = {
                    timeout_ms   = 500,
                    lsp_fallback = true,
                },
            })
            vim.keymap.set({ "n", "v" }, "<leader>cf",
                function() require("conform").format({ async = true, lsp_fallback = true }) end,
                { desc = "Format buffer" }
            )
        end,
    },

}, {
    -- lazy.nvim UI settings
    ui = { border = "rounded" },
    checker = { enabled = false },  -- disable auto update checks
})

-- ── Keymaps ───────────────────────────────────────────────────────────────────
local map = vim.keymap.set

-- File ops
map("n", "<leader>w",  ":w<CR>",   { desc = "Save" })
map("n", "<leader>q",  ":q<CR>",   { desc = "Quit" })
map("n", "<leader>x",  ":x<CR>",   { desc = "Save and quit" })

-- Window splits
map("n", "<leader>sv", ":vsplit<CR>", { desc = "Vertical split" })
map("n", "<leader>sh", ":split<CR>",  { desc = "Horizontal split" })
map("n", "<C-h>",      "<C-w>h",      { desc = "Window left" })
map("n", "<C-j>",      "<C-w>j",      { desc = "Window down" })
map("n", "<C-k>",      "<C-w>k",      { desc = "Window up" })
map("n", "<C-l>",      "<C-w>l",      { desc = "Window right" })
map("n", "<C-Up>",     ":resize +2<CR>" )
map("n", "<C-Down>",   ":resize -2<CR>" )
map("n", "<C-Left>",   ":vertical resize -2<CR>")
map("n", "<C-Right>",  ":vertical resize +2<CR>")

-- Buffer navigation
map("n", "<S-h>",  ":bprev<CR>",   { desc = "Prev buffer" })
map("n", "<S-l>",  ":bnext<CR>",   { desc = "Next buffer" })
map("n", "<leader>bd", ":bdelete<CR>", { desc = "Delete buffer" })

-- Move selected lines up/down in visual mode
map("v", "J", ":m '>+1<CR>gv=gv", { desc = "Move line down" })
map("v", "K", ":m '<-2<CR>gv=gv",  { desc = "Move line up" })

-- Keep cursor centered when scrolling / searching
map("n", "<C-d>", "<C-d>zz")
map("n", "<C-u>", "<C-u>zz")
map("n", "n",     "nzzzv")
map("n", "N",     "Nzzzv")

-- Paste without overwriting clipboard
map("v", "p", '"_dP', { desc = "Paste without losing clipboard" })

-- Select all
map("n", "<C-a>", "gg<S-v>G", { desc = "Select all" })

-- Clear search highlight
map("n", "<Esc>", ":nohlsearch<CR>")

-- Terminal (open at bottom)
map("n", "<leader>tt", ":split | terminal<CR>", { desc = "Open terminal" })
map("t", "<Esc>",       "<C-\\><C-n>",           { desc = "Exit terminal mode" })
