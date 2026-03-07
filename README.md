# proviso

> *Before a voyage, you prepare a list of provisions — everything the journey requires. **proviso** is that list. Declare what your system needs, and it makes it so.*

---

## What it does

Declare your resources in a HOCON manifest. Run `proviso sync`. Done.

```hocon
dev-tools {

  # PackageResource — installed via dnf / cargo / pip / go
  ripgrep { install { method = cargo, package = ripgrep  } }
  fd      { install { method = cargo, package = fd-find  } }
  jq      { install { method = dnf,   package = jq       } }

  # SourceResource — git repo, kept in sync
  gregs-search {
    repo   = "git@github.com:greg/search.git"
    target = "/opt/gregs-search"
  }

}

dotfiles {

  # BOUND first — grafts your host dotfiles folder into the container.
  # Everything below depends on this path existing.
  dot_files_folder {
    origin = "~/.proviso/dotfiles"   # on your host (Windows, Mac, Linux)
    path   = "/proviso/dotfiles"     # where it appears inside the container
    mode   = BOUND
  }

  # SYMLINK — places configs where apps expect them.
  # origin must use the container path (/proviso/dotfiles), not the host path.
  bashrc {
    origin = "/proviso/dotfiles/.bashrc"
    path   = "~/.bashrc"
    mode   = SYMLINK
  }
  nvim {
    origin = "/proviso/dotfiles/config/nvim"
    path   = "~/.config/nvim"
    mode   = SYMLINK
  }

}
```

## Under the hood

| Resource | Mode | What proviso runs |
|---|---|---|
| `PackageResource` | — | `dnf install`, `cargo install`, `pip install`, `go install` |
| `SourceResource` | — | `git clone` / `git pull` |
| `FileResource` | `BOUND` | `docker run --mount type=bind,...` |
| `FileResource` | `SYMLINK` | `ln -s origin path` |
| `FileResource` | `COPY` | `cp origin path` |
| `FileResource` | `HARDLINK` | `ln origin path` |

> `BOUND` must run before any `SYMLINK` that references its path — a symlink to a missing path is a dead pointer.

Resources are immutable Pydantic models. Actions are composable pipelines. Providers are injected — swap `DnfProvider` for `AptProvider` and the same manifest works on Ubuntu.

## Dev container

```bash
./build.sh   # build once (30-60 min first time, cached after)

docker run -it --rm \
  --mount type=bind,source=$(pwd),target=/workspace \
  proviso-dev:latest
```
