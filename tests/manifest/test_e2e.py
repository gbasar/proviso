"""End-to-end test — one conf file with all three provision types.

Exercises the full stack: HOCON conf → ProvisionRegistry → typed objects → FileSync action.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proviso.markup.hocon import HoconAdapter
from proviso.provisions.models import FileProvision, PackageProvision, SourceProvision
from proviso.provisions.registry import ProvisionRegistry, ProvisionError
from proviso.actions.file_sync import FileSync
from proviso.actions.protocol import ActionStatus

_hocon = HoconAdapter()

ALL_TYPES_CONF = """
# Package provisions — type inferred from install {}
tools {
  ripgrep {
    description = "Fast recursive grep"
    install { method = cargo, package = ripgrep }
  }
  fd {
    install { method = cargo, package = fd-find }
  }
  jq {
    description = "JSON processor"
    install { method = dnf, package = jq }
  }
}

# Source provisions — type inferred from src (validated as git URI)
repos {
  my-app {
    description = "Main application"
    repo        = "git@github.com:acme/my-app.git"
    destination = "/opt/my-app"
    branch      = "develop"
  }
  lib {
    repo        = "https://github.com/acme/lib.git"
    destination = "/opt/lib"
  }
}

# File provisions — type inferred from src/destination/mode
dotfiles {
  bashrc {
    description = "Bash config"
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
"""


@pytest.fixture()
def registry() -> ProvisionRegistry:
    reg = ProvisionRegistry()
    reg.load_dict(_hocon.read_string(ALL_TYPES_CONF))
    return reg


class TestAllTypesLoaded:
    def test_total_count(self, registry: ProvisionRegistry) -> None:
        assert len(registry.provisions) == 7

    def test_packages(self, registry: ProvisionRegistry) -> None:
        pkgs = registry.filter_by_type("package")
        assert set(pkgs) == {"ripgrep", "fd", "jq"}

    def test_sources(self, registry: ProvisionRegistry) -> None:
        srcs = registry.filter_by_type("source")
        assert set(srcs) == {"my-app", "lib"}

    def test_files(self, registry: ProvisionRegistry) -> None:
        files = registry.filter_by_type("file")
        assert set(files) == {"bashrc", "nvim"}


class TestPackageShape:
    def test_types(self, registry: ProvisionRegistry) -> None:
        assert isinstance(registry.get("ripgrep"), PackageProvision)
        assert isinstance(registry.get("jq"), PackageProvision)

    def test_provider(self, registry: ProvisionRegistry) -> None:
        assert registry.get("ripgrep").provider == "cargo"
        assert registry.get("jq").provider == "dnf"

    def test_package_differs_from_name(self, registry: ProvisionRegistry) -> None:
        assert registry.get("fd").package == "fd-find"

    def test_package_none_when_same(self, registry: ProvisionRegistry) -> None:
        assert registry.get("ripgrep").package is None

    def test_description(self, registry: ProvisionRegistry) -> None:
        assert registry.get("ripgrep").description == "Fast recursive grep"
        assert registry.get("fd").description is None

    def test_category_tag(self, registry: ProvisionRegistry) -> None:
        assert "tools" in registry.get("ripgrep").tags


class TestSourceShape:
    def test_types(self, registry: ProvisionRegistry) -> None:
        assert isinstance(registry.get("my-app"), SourceProvision)
        assert isinstance(registry.get("lib"), SourceProvision)

    def test_src_ssh(self, registry: ProvisionRegistry) -> None:
        assert registry.get("my-app").repo == "git@github.com:acme/my-app.git"

    def test_src_https(self, registry: ProvisionRegistry) -> None:
        assert registry.get("lib").repo == "https://github.com/acme/lib.git"

    def test_destination(self, registry: ProvisionRegistry) -> None:
        assert registry.get("my-app").destination == Path("/opt/my-app")

    def test_branch_explicit(self, registry: ProvisionRegistry) -> None:
        assert registry.get("my-app").branch == "develop"

    def test_branch_default(self, registry: ProvisionRegistry) -> None:
        assert registry.get("lib").branch == "main"

    def test_category_tag(self, registry: ProvisionRegistry) -> None:
        assert "repos" in registry.get("my-app").tags


class TestFileShape:
    def test_types(self, registry: ProvisionRegistry) -> None:
        assert isinstance(registry.get("bashrc"), FileProvision)
        assert isinstance(registry.get("nvim"), FileProvision)

    def test_src(self, registry: ProvisionRegistry) -> None:
        assert str(registry.get("bashrc").src) == "/proviso/dotfiles/.bashrc"

    def test_destination(self, registry: ProvisionRegistry) -> None:
        assert registry.get("bashrc").destination == Path("~/.bashrc")

    def test_mode(self, registry: ProvisionRegistry) -> None:
        assert registry.get("bashrc").mode == "SYMLINK"

    def test_description(self, registry: ProvisionRegistry) -> None:
        assert registry.get("bashrc").description == "Bash config"

    def test_category_tag(self, registry: ProvisionRegistry) -> None:
        assert "dotfiles" in registry.get("bashrc").tags


class TestSourceValidation:
    def test_invalid_src_rejected(self) -> None:
        bad = """
        provisions {
          my-app {
            provision_type = source
            repo           = "not-a-git-url"
            destination    = "/opt/x"
          }
        }
        """
        reg = ProvisionRegistry()
        with pytest.raises(Exception, match="repo must be"):
            reg.load_dict(_hocon.read_string(bad))


class TestFileSyncAction:
    def test_symlink_created(self, tmp_path: Path) -> None:
        src = tmp_path / "bashrc"
        src.write_text("# bashrc")
        dest = tmp_path / "link_bashrc"

        provision = FileProvision(
            name="bashrc",
            src=src,
            destination=dest,
            mode="SYMLINK",
        )
        result = FileSync().execute(provision)

        assert result.status == ActionStatus.SUCCESS
        assert dest.is_symlink()
        assert dest.resolve() == src.resolve()
