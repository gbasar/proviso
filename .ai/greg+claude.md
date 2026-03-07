# proviso — working todo

## Done
- [x] Manifest loader (ManifestLoader → list[PackageResource] from modern-linux-utils.conf)
- [x] PackageResource.package field (name=fd, package=fd-find)
- [x] PackageInstall uses resource.package or resource.name
- [x] build.sh step 2 → plain docker build (sees local images)
- [x] README with tagline, working example, under-the-hood table

## In progress / decidee
awesopme thanks pal agreed
- [ ] FileResource modes: SYMLINK, COPY, HARDLINK, BOUND
- [ ] FileResource.origin field (replaces ambiguous "source")
- [ ] FileResource.path stays as-is
- [ ] BOUND mode = bind mount (must run before any SYMLINK referencing its path)
- [ ] Loader infers resource type from shape (install→package, repo→source, path→file)

## Up next
- [ ] FileSync action (ln -s, cp, ln, bind mount)
- [ ] Update ManifestLoader to produce SourceResource and FileResource (not just PackageResource)
- [ ] Strip setup.sh steps 1 + 6 once FileResource SYMLINK is working
- [ ] .gitignore (.DS_Store, etc.)
- [ ] CLI: proviso sync, proviso status
