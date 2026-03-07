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

## Up next (in order)
- [ ] setup.sh step 6 (devbox bin symlinks) → replace with proviso
- [ ] ManifestLoader: produce SourceProvision + FileProvision (not just PackageProvision)
- [ ] CLI: proviso sync, proviso status
- [ ] appendToPath on SourceProvision  # deferred: runtime PATH mutation → env var scope
