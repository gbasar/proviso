
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from proviso.actions.file_sync import FileSync
from proviso.actions.protocol import ActionStatus, ShapeMismatchError
from proviso.provisions.models import FileProvision, PackageProvision


def make_provision(**kwargs) -> FileProvision:
    defaults = dict(name="test-file", path="/tmp/proviso-test-dest", mode="SYMLINK", origin="/tmp/proviso-test-origin")
    return FileProvision(**{**defaults, **kwargs})


# --- shape guard ---

def test_rejects_wrong_provision_type():
    pkg = PackageProvision(name="x", provider="dnf")
    with pytest.raises(ShapeMismatchError):
        FileSync().execute(pkg)


# --- missing fields ---

def test_missing_origin_fails():
    p = make_provision(origin=None)
    result = FileSync().execute(p)
    assert result.status == ActionStatus.FAILED
    assert "origin" in result.message


def test_unknown_mode_fails():
    p = make_provision(mode="HARDLINK")
    result = FileSync().execute(p)
    assert result.status == ActionStatus.FAILED
    assert "unknown mode" in result.message


def test_none_mode_fails():
    p = make_provision(mode=None)
    result = FileSync().execute(p)
    assert result.status == ActionStatus.FAILED


# --- SYMLINK ---

def test_symlink_creates_link(tmp_path):
    origin = tmp_path / "origin.txt"
    origin.write_text("hello")
    dest = tmp_path / "link.txt"

    p = make_provision(path=str(dest), origin=str(origin), mode="SYMLINK")
    result = FileSync().execute(p)

    assert result.status == ActionStatus.SUCCESS
    assert dest.is_symlink()
    assert dest.resolve() == origin.resolve()


def test_symlink_skips_if_already_correct(tmp_path):
    origin = tmp_path / "origin.txt"
    origin.write_text("hello")
    dest = tmp_path / "link.txt"
    dest.symlink_to(origin)

    p = make_provision(path=str(dest), origin=str(origin), mode="SYMLINK")
    result = FileSync().execute(p)

    assert result.status == ActionStatus.SKIPPED


def test_symlink_replaces_stale_link(tmp_path):
    old_target = tmp_path / "old.txt"
    old_target.write_text("old")
    new_origin = tmp_path / "new.txt"
    new_origin.write_text("new")
    dest = tmp_path / "link.txt"
    dest.symlink_to(old_target)

    p = make_provision(path=str(dest), origin=str(new_origin), mode="SYMLINK")
    result = FileSync().execute(p)

    assert result.status == ActionStatus.SUCCESS
    assert dest.resolve() == new_origin.resolve()


def test_symlink_creates_parent_dirs(tmp_path):
    origin = tmp_path / "origin.txt"
    origin.write_text("x")
    dest = tmp_path / "a" / "b" / "c" / "link.txt"

    p = make_provision(path=str(dest), origin=str(origin), mode="SYMLINK")
    FileSync().execute(p)

    assert dest.is_symlink()


# --- COPY ---

def test_copy_copies_file(tmp_path):
    origin = tmp_path / "file.txt"
    origin.write_text("content")
    dest = tmp_path / "copy.txt"

    p = make_provision(path=str(dest), origin=str(origin), mode="COPY")
    result = FileSync().execute(p)

    assert result.status == ActionStatus.SUCCESS
    assert dest.read_text() == "content"


def test_copy_skips_if_dest_exists(tmp_path):
    origin = tmp_path / "file.txt"
    origin.write_text("new")
    dest = tmp_path / "copy.txt"
    dest.write_text("old")

    p = make_provision(path=str(dest), origin=str(origin), mode="COPY")
    result = FileSync().execute(p)

    assert result.status == ActionStatus.SKIPPED
    assert dest.read_text() == "old"  # untouched


def test_copy_copies_directory(tmp_path):
    origin = tmp_path / "src_dir"
    origin.mkdir()
    (origin / "a.txt").write_text("a")
    dest = tmp_path / "dst_dir"

    p = make_provision(path=str(dest), origin=str(origin), mode="COPY")
    result = FileSync().execute(p)

    assert result.status == ActionStatus.SUCCESS
    assert (dest / "a.txt").read_text() == "a"


# --- BOUND ---

def test_bound_skips_if_already_mounted(tmp_path):
    origin = tmp_path / "src"
    origin.mkdir()
    dest = tmp_path / "dst"
    dest.mkdir()

    mock_mounts = f"none {dest} tmpfs rw 0 0\n"
    with patch("proviso.actions.file_sync.Path.read_text", return_value=mock_mounts):
        p = make_provision(path=str(dest), origin=str(origin), mode="BOUND")
        result = FileSync().execute(p)

    assert result.status == ActionStatus.SKIPPED


def test_bound_calls_mount(tmp_path):
    origin = tmp_path / "src"
    origin.mkdir()
    dest = tmp_path / "dst"

    mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with patch("proviso.actions.file_sync.Path.read_text", side_effect=FileNotFoundError):
        with patch("proviso.actions.file_sync.subprocess.run", return_value=mock_result) as mock_run:
            p = make_provision(path=str(dest), origin=str(origin), mode="BOUND")
            result = FileSync().execute(p)

    assert result.status == ActionStatus.SUCCESS
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "mount" in args and "--bind" in args


def test_bound_fails_on_mount_error(tmp_path):
    origin = tmp_path / "src"
    origin.mkdir()
    dest = tmp_path / "dst"

    mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="permission denied")
    with patch("proviso.actions.file_sync.Path.read_text", side_effect=FileNotFoundError):
        with patch("proviso.actions.file_sync.subprocess.run", return_value=mock_result):
            p = make_provision(path=str(dest), origin=str(origin), mode="BOUND")
            result = FileSync().execute(p)

    assert result.status == ActionStatus.FAILED
    assert "permission denied" in result.message
