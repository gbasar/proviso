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

## Examples

### Packages

```hocon
dev-tools {
  ripgrep { install { method = cargo, package = ripgrep } }
  fd      { install { method = cargo, package = fd-find } }
  jq      { install { method = dnf,   package = jq      } }
}
```

### Source repos

```hocon
repos {
  custom-search {
    repo        = "git@github.com:acme/search.git"
    destination = "/opt/custom-search"
  }
}
```

### Dotfiles (bind + symlink)

```hocon
dotfiles {

  # BOUND first — grafts your host dotfiles folder into the container.
  # Everything below depends on this path existing.
  dot_files_folder {
    src         = "~/.proviso/dotfiles"  # on your host (Windows, Mac, Linux)
    destination = "/proviso/dotfiles"    # where it appears inside the container
    mode        = BOUND
  }

  # SYMLINK — places configs where apps expect them.
  # src must use the container path, not the host path.
  bashrc {
    src         = "/proviso/dotfiles/.bashrc"
    destination = "~/.bashrc"
    mode        = SYMLINK
  }
  nvim {
    src         = "/proviso/dotfiles/config/nvim"
    destination = "~/.config/nvim"
    mode        = SYMLINK
  }

}
```

---

## Under the hood

| Provision | Mode | What proviso runs |
|---|---|---|
| `PackageProvision` | — | `dnf install`, `cargo install`, `pip install`, `go install` |
| `SourceProvision` | — | `git clone` / `git pull` |
| `FileProvision` | `BOUND` | `docker run --mount type=bind,...` |
| `FileProvision` | `SYMLINK` | `ln -s src destination` |
| `FileProvision` | `COPY` | `cp src destination` |

> `BOUND` must run before any `SYMLINK` that references its path — a symlink to a missing path is a dead pointer.

Provisions are immutable Pydantic models. Each type shares a common base (`name`, `description`, `tags`, `schedule`, `metadata`) and defines its own `src`/`destination` with the appropriate Python type — `Path` for files, a validated git URI for source repos. No shared base field is typed as `Any`. Actions are composable pipelines. Providers are injected — swap `DnfProvider` for `AptProvider` and the same manifest works on Ubuntu.

---

## Dev container

```bash
./build.sh   # build once (30-60 min first time, cached after)

docker run -it --rm \
  --mount type=bind,source=$(pwd),target=/workspace \
  proviso-dev:latest
```

---

## Why not devcontainers (and what we do instead)

Dev containers are a reasonable idea that accumulates the wrong tradeoffs over time:

- **Slow startup.** Every session involves spinning up a container, waiting for the IDE backend to attach, and negotiating mounts. On a fast machine this is annoying. On a slow one it's a tax on every context switch.
- **IDE runs remote, not native.** JetBrains Remote Development and VS Code Server both run the IDE backend inside the container. You get latency, reduced plugin compatibility, and a second-class experience compared to running the IDE natively.
- **Docker Desktop is spyware-adjacent.** Telemetry on by default, background services, a dashboard that phones home. On Windows it also fights with WSL2 for kernel resources.
- **JetBrains Toolbox is the same problem.** Auto-updates, telemetry, a background agent running at all times. Not acceptable on a dev machine you care about.
- **`BOUND` mounts are a workaround for a problem baremetal doesn't have.** Grafting host dotfiles into a container via bind mount is solving a problem you created by using a container in the first place.
- **Reproducibility is a myth in practice.** The container is reproducible. Your dotfiles, your SSH keys, your personal tools, your muscle memory — none of that travels with it. You end up with a reproducible shell and an irreproducible human.

### What proviso does instead

**Target: WSL2 as baremetal Linux.**

- WSL2 Ubuntu is the machine. Proviso runs directly on it — no container wrapper.
- Packages, dotfiles, tools are installed onto the real filesystem via `dnf`/`apt`/`cargo`/`pip`.
- GUI apps (IntelliJ, Neovide, anything GTK/Qt) run natively in WSL2.
- WSLg (built into Windows 11) forwards Wayland/X11 windows to the Windows display automatically — no config, no Remote Development, no Gateway. A shortcut launches the app; Windows shows the window.
- IntelliJ is installed directly from a tar.gz. No Toolbox.
- `BOUND` mode becomes a no-op on baremetal — the path just exists.
- The same manifest that provisions the Docker dev container provisions WSL2. Swap the target, keep the manifest.

The Docker dev container (`./build.sh`) still exists for CI, onboarding, and environments where you can't or won't touch the host. But it is not the primary target.
