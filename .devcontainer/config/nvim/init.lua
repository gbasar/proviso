-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
    local out = vim.fn.system({
        "git", "clone", "--filter=blob:none", "--branch=stable",
        "https://github.com/folke/lazy.nvim.git", lazypath,
    })
    if vim.v.shell_error ~= 0 then
        vim.api.nvim_echo({
            { "Failed to clone lazy.nvim:\n", "ErrorMsg" },
            { out,                             "WarningMsg" },
            { "\nPress any key to continue...", "" },
        }, true, {})
        vim.fn.getchar()
        os.exit(1)
    end
end
vim.opt.rtp:prepend(lazypath)

vim.g.mapleader      = " "
vim.g.maplocalleader = "\\"

require("lazy").setup({
    spec = {
        { "LazyVim/LazyVim", import = "lazyvim.plugins" },

        -- Optional extras — uncomment to enable:
        -- { import = "lazyvim.plugins.extras.lang.python" },
        -- { import = "lazyvim.plugins.extras.lang.rust" },
        -- { import = "lazyvim.plugins.extras.lang.go" },
        -- { import = "lazyvim.plugins.extras.lang.typescript" },
        -- { import = "lazyvim.plugins.extras.editor.telescope" },
        -- { import = "lazyvim.plugins.extras.ui.mini-animate" },
    },
    defaults  = { lazy = false, version = false },
    install   = { colorscheme = { "tokyonight", "habamax" } },
    checker   = { enabled = true },
    performance = {
        rtp = {
            disabled_plugins = { "gzip", "tarPlugin", "tohtml", "tutor", "zipPlugin" },
        },
    },
})
