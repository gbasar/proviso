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
- [x] 196 tests passing

## Up next (in order)
- [ ] FileSync action (ln -s, cp, bind mount — SYMLINK/COPY/BOUND)
- [ ] ManifestLoader: produce SourceProvision + FileProvision (not just PackageProvision)
- [ ] appendToPath field on SourceProvision  # deferred: implies runtime PATH mutation,
      # which opens the build-time vs runtime env question (proxy vars, etc) — scope later
- [ ] Strip setup.sh steps 1+6 once FileProvision SYMLINK works
- [ ] CLI: proviso sync, proviso status
