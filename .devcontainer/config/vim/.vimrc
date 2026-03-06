" ═══════════════════════════════════════════════════════════════════════════
" Vim config — ~/.vimrc
"
" Plugin manager: vim-plug (installed by setup.sh)
"
" Plugins:
"   tpope/vim-fugitive         — :Git status/blame/diff/push/pull
"   tpope/vim-commentary       — gcc: comment line, gc: comment in visual
"   tpope/vim-surround         — cs"' change surround, ds" delete, ys motion
"   tpope/vim-repeat           — makes vim-surround/commentary repeatable with .
"   airblade/vim-gitgutter     — git diff signs in gutter, ]c/[c to jump hunks
"   junegunn/fzf               — fuzzy finder core (already installed as binary)
"   junegunn/fzf.vim           — :Files :Rg :Buffers :History :GFiles
"   preservim/nerdtree         — file tree, <leader>e to toggle
"   vim-airline/vim-airline    — statusline with git/lint/mode info
"   dense-analysis/ale         — async linting (ruff) + fixing on save
"   jiangmiao/auto-pairs       — auto-close brackets, quotes, parens
"   catppuccin/vim             — Catppuccin Mocha colorscheme
" ═══════════════════════════════════════════════════════════════════════════

" ── vim-plug ──────────────────────────────────────────────────────────────────
call plug#begin('~/.vim/plugged')

Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-commentary'
Plug 'tpope/vim-surround'
Plug 'tpope/vim-repeat'
Plug 'airblade/vim-gitgutter'
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'
Plug 'preservim/nerdtree'
Plug 'vim-airline/vim-airline'
Plug 'vim-airline/vim-airline-themes'
Plug 'dense-analysis/ale'
Plug 'jiangmiao/auto-pairs'
Plug 'catppuccin/vim', { 'as': 'catppuccin' }

call plug#end()

" ── Core settings ─────────────────────────────────────────────────────────────
set nocompatible
filetype plugin indent on
syntax on

set encoding=utf-8
set fileencoding=utf-8
set number
set relativenumber
set tabstop=4
set shiftwidth=4
set expandtab
set smartindent
set autoindent
set nowrap
set ignorecase
set smartcase
set hlsearch
set incsearch
set scrolloff=8
set sidescrolloff=8
set signcolumn=yes
set cursorline
set mouse=a
set splitbelow
set splitright
set hidden                  " allow switching buffers without saving
set noswapfile
set nobackup
set undofile
set undodir=~/.vim/undo
set updatetime=250
set timeoutlen=300
set wildmenu
set wildmode=longest:full,full
set pumheight=10
set laststatus=2            " always show statusline
set showcmd
set showmatch
set backspace=indent,eol,start

" True colour (enable if terminal supports it)
if has('termguicolors')
    set termguicolors
endif

" ── Colorscheme ───────────────────────────────────────────────────────────────
silent! colorscheme catppuccin_mocha

" ── Leader ────────────────────────────────────────────────────────────────────
let mapleader = " "
let maplocalleader = " "

" ── ALE: linting + fixing ─────────────────────────────────────────────────────
let g:ale_linters = {
\   'python': ['ruff'],
\   'sh':     ['shellcheck'],
\   'json':   ['jq'],
\}

let g:ale_fixers = {
\   '*':      ['remove_trailing_lines', 'trim_whitespace'],
\   'python': ['ruff', 'ruff_format'],
\   'sh':     ['shfmt'],
\   'json':   ['jq'],
\}

let g:ale_fix_on_save          = 1
let g:ale_lint_on_save         = 1
let g:ale_lint_on_text_changed = 'never'
let g:ale_lint_on_insert_leave = 0
let g:ale_sign_error           = '✘'
let g:ale_sign_warning         = '▲'
let g:ale_virtualtext_cursor   = 'current'

" ── Airline statusline ────────────────────────────────────────────────────────
let g:airline_theme               = 'catppuccin_mocha'
let g:airline_powerline_fonts     = 1
let g:airline#extensions#ale#enabled    = 1
let g:airline#extensions#branch#enabled = 1
let g:airline#extensions#hunks#enabled  = 1

" ── NERDTree ──────────────────────────────────────────────────────────────────
let g:NERDTreeShowHidden    = 1
let g:NERDTreeIgnore        = ['^\.git$', '\.pyc$', '__pycache__', '\.venv', '\.DS_Store']
let g:NERDTreeMinimalUI     = 1
let g:NERDTreeStatusline    = ''

" Close vim if NERDTree is the only window left
autocmd BufEnter * if tabpagenr('$') == 1
    \ && winnr('$') == 1
    \ && exists('b:NERDTree')
    \ && b:NERDTree.isTabTree()
    \ | quit | endif

" ── fzf.vim settings ──────────────────────────────────────────────────────────
let g:fzf_layout = { 'down': '40%' }
let g:fzf_preview_window = ['right:55%', 'ctrl-/']

" ── GitGutter ─────────────────────────────────────────────────────────────────
let g:gitgutter_sign_added    = '▎'
let g:gitgutter_sign_modified = '▎'
let g:gitgutter_sign_removed  = ''

" ── Keymaps ───────────────────────────────────────────────────────────────────
" File ops
nnoremap <leader>w  :w<CR>
nnoremap <leader>q  :q<CR>
nnoremap <leader>x  :x<CR>

" fzf file/search navigation
nnoremap <leader>ff :Files<CR>
nnoremap <leader>fg :Rg<CR>
nnoremap <leader>fb :Buffers<CR>
nnoremap <leader>fr :History<CR>
nnoremap <leader>fs :Rg <C-R><C-W><CR>
nnoremap <leader>fh :Helptags<CR>
nnoremap <leader>gc :GFiles?<CR>

" NERDTree
nnoremap <leader>t  :NERDTreeToggle<CR>
nnoremap <leader>tf :NERDTreeFind<CR>

" Window navigation
nnoremap <C-h>  <C-w>h
nnoremap <C-j>  <C-w>j
nnoremap <C-k>  <C-w>k
nnoremap <C-l>  <C-w>l
nnoremap <leader>sv :vsplit<CR>
nnoremap <leader>sh :split<CR>

" Buffer navigation
nnoremap <S-h>  :bprev<CR>
nnoremap <S-l>  :bnext<CR>
nnoremap <leader>bd :bdelete<CR>

" Move lines in visual mode
vnoremap J :m '>+1<CR>gv=gv
vnoremap K :m '<-2<CR>gv=gv

" Clear search highlight
nnoremap <Esc> :nohlsearch<CR>

" Keep cursor centred when jumping
nnoremap n nzzzv
nnoremap N Nzzzv
nnoremap <C-d> <C-d>zz
nnoremap <C-u> <C-u>zz

" Paste without overwriting register
vnoremap p "_dP

" ALE navigation
nnoremap ]e :ALENextWrap<CR>
nnoremap [e :ALEPreviousWrap<CR>
nnoremap <leader>ca :ALECodeAction<CR>
nnoremap <leader>cf :ALEFix<CR>

" Git (fugitive)
nnoremap <leader>gs :Git status<CR>
nnoremap <leader>gb :Git blame<CR>
nnoremap <leader>gd :Git diff<CR>
nnoremap <leader>gp :Git push<CR>

" GitGutter hunk navigation
nnoremap ]h :GitGutterNextHunk<CR>
nnoremap [h :GitGutterPrevHunk<CR>
nnoremap <leader>hs :GitGutterStageHunk<CR>
nnoremap <leader>hu :GitGutterUndoHunk<CR>

" Select all
nnoremap <C-a> ggVG

" Open terminal
nnoremap <leader>tt :split \| terminal<CR>
tnoremap <Esc>      <C-\><C-n>

" ── Autocmds ──────────────────────────────────────────────────────────────────
augroup FileTypeSettings
    autocmd!
    " Python
    autocmd FileType python setlocal tabstop=4 shiftwidth=4 expandtab
    " YAML
    autocmd FileType yaml   setlocal tabstop=2 shiftwidth=2 expandtab
    " JSON
    autocmd FileType json   setlocal tabstop=2 shiftwidth=2 expandtab
    " TOML
    autocmd FileType toml   setlocal tabstop=4 shiftwidth=4 expandtab
    " Markdown
    autocmd FileType markdown setlocal wrap linebreak
augroup END

" Highlight trailing whitespace (red)
highlight TrailingWhitespace ctermbg=red guibg=#f38ba8
autocmd BufWinEnter * match TrailingWhitespace /\s\+$/

" Return to last cursor position when reopening a file
autocmd BufReadPost * if line("'\"") > 1 && line("'\"") <= line("$") | exe "normal! g'\"" | endif
