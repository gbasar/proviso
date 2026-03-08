# proviso — working todo

## Done
- [x] ManifestLoader (modern-linux-utils.conf → list[PackageProvision])
- [x] PackageProvision.package field (name=fd, package=fd-find)
- [x] PackageInstall uses provision.package or name
- [x] build.sh step 2 → plain docker build (sees local images)
- [x] README with tagline, examples, under-the-hood table
- [x] Resource → Provision rename (all files, tests, CLI)
- [x] ManifestScanner (PROVISION_LIST support)
- [x] .gitignore (.DS_Store, .idea/)
- [x] FileProvision model: path, origin, mode (SYMLINK/COPY/BOUND)
- [x] FileSync action (SYMLINK/COPY/BOUND, 210 tests passing)
- [x] dotfiles.conf (BOUND + SYMLINK pattern, host ~/.proviso/dotfiles)
- [x] root manifest.conf with PROVISION_LIST → provisions/ folder
- [x] Dispatcher wired to ManifestScanner + FileSync + BOUND-before-SYMLINK ordering
- [x] Logging: FAILED always, OK at -v****, SKIP at -vv, manifest detail at -vvv
- [x] setup.sh step 1 replaced by parcel -v file sync

## Package issues (not proviso bugs — revisit individually)
- [ ] gitui — openssl-sys build; OPENSSL_NO_VENDOR=1 added, verify on next build
- [ ] zellij — same openssl-sys issue + yanked packages in lock; verify on next build
- [ ] tmux — not in EPEL 9; find source or alternative (e.g. compile, different repo)
- [ ] aria2 — missing libcares.so.2 in EPEL 9; needs c-ares or alternative
- [ ] dog (DNS client) — crate `dog` on crates.io is a library, not the ogham/dog binary; find correct install path

## Up next (in order)
- [x] setup.sh step 6 (devbox bin symlinks) → trashed for now
- [x] setup.sh steps 2-4 (fisher/vim-plug/lazy.nvim installs) → trashed for now
- [ ] fisher self-bootstrap: add fisher install to fish config so plugins install on first shell open
- [ ] vim-plug self-bootstrap: add plug.vim download + PlugInstall to .vimrc on first vim open
- [ ] lazy.nvim self-bootstrap: already works if bootstrap snippet is in init.lua (verify)
- [ ] ManifestLoader: produce SourceProvision + FileProvision (not just PackageProvision)
- [ ] CLI: proviso sync, proviso status
- [ ] e2e test: real runtime, all provision types, npm provider + local Python HTTP server as fake registry, session-scoped Docker fixture (started once), explicit pass/fail per feature
- [ ] appendToPath on SourceProvision  # deferred: runtime PATH mutation → env var scope

## nice to have
-pre and post install hooks for every provisonu type, also at file level,

## While u were away claude.. i decided to

### Ådd commands
tree, 

### aadd features
docker in docker
