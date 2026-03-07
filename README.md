# proviso

> **provision** — the action of providing or supplying something for use.
> **proviso** — a condition attached to an agreement or contract.

> *Before a voyage, you prepare a list of provisions — everything the journey requires. **proviso** is that list. Declare what your system needs, and it makes it so.*

proviso is both a manifest of the provisions required, and a contract binding them into your development system. It is designed to be system-agnostic — not tied to Docker or devcontainers.

---

## Manifest structure

Provisions live under root-level categories. Categories are cosmetic — they let you organize freely. proviso infers the type of each provision from its shape at runtime, not from where it sits in the file.

```hocon
# Load additional manifest files, folders, or globs
PROVISION_LIST = [
  "~/.proviso/dotfiles.conf"
  "~/.proviso/configs/"
  "~/.proviso/extras/*.conf"
]
```

`PROVISION_LIST` merges external manifests into the registry. Entries can be a single file (any supported format), a folder (all supported files loaded), or a glob.

---

## What it does

Declare your provisions in a HOCON manifest. Run `proviso sync`. Done.

```hocon
dev-tools {

  # PackageProvision — installed via dnf / cargo / pip / go
  ripgrep { install { method = cargo, package = ripgrep  } }
  fd      { install { method = cargo, package = fd-find  } }
  jq      { install { method = dnf,   package = jq       } }

  # SourceProvision — git repo, kept in sync
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

| Provision | Mode | What proviso runs |
|---|---|---|
| `PackageProvision` | — | `dnf install`, `cargo install`, `pip install`, `go install` |
| `SourceProvision` | — | `git clone` / `git pull` |
| `FileProvision` | `BOUND` | `docker run --mount type=bind,...` |
| `FileProvision` | `SYMLINK` | `ln -s origin path` |
| `FileProvision` | `COPY` | `cp origin path` |

> `BOUND` must run before any `SYMLINK` that references its path — a symlink to a missing path is a dead pointer.

Provisions are immutable Pydantic models. Actions are composable pipelines. Providers are injected — swap `DnfProvider` for `AptProvider` and the same manifest works on Ubuntu.

## Dev container

```bash
./build.sh   # build once (30-60 min first time, cached after)

docker run -it --rm \
  --mount type=bind,source=$(pwd),target=/workspace \
  proviso-dev:latest
```
