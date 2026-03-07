"""Tests for FileManager infrastructure."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_guardrails.infra.file_manager import FileManager


def test_write_text_creates_file(tmp_path: Path) -> None:
    fm = FileManager()
    target = tmp_path / "hello.txt"
    result = fm.write_text(target, "hello world")
    assert result is None
    assert target.read_text() == "hello world"


def test_write_text_dry_run_returns_message(tmp_path: Path) -> None:
    fm = FileManager(dry_run=True)
    target = tmp_path / "hello.txt"
    result = fm.write_text(target, "hello world")
    assert result is not None
    assert "would write" in result
    assert not target.exists()


def test_read_text_returns_file_content(tmp_path: Path) -> None:
    fm = FileManager()
    target = tmp_path / "data.txt"
    target.write_text("content here")
    assert fm.read_text(target) == "content here"


def test_read_text_missing_raises_file_not_found(tmp_path: Path) -> None:
    fm = FileManager()
    with pytest.raises(FileNotFoundError):
        fm.read_text(tmp_path / "missing.txt")


def test_copy_copies_content(tmp_path: Path) -> None:
    fm = FileManager()
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("source content")
    result = fm.copy(src, dst)
    assert result is None
    assert dst.read_text() == "source content"


def test_copy_dry_run_returns_message(tmp_path: Path) -> None:
    fm = FileManager(dry_run=True)
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("content")
    result = fm.copy(src, dst)
    assert result is not None
    assert "would copy" in result
    assert not dst.exists()


def test_exists_returns_true_for_existing_file(tmp_path: Path) -> None:
    fm = FileManager()
    p = tmp_path / "exists.txt"
    p.write_text("x")
    assert fm.exists(p) is True


def test_exists_returns_false_for_missing_file(tmp_path: Path) -> None:
    fm = FileManager()
    assert fm.exists(tmp_path / "nope.txt") is False


def test_glob_returns_matching_paths(tmp_path: Path) -> None:
    fm = FileManager()
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    (tmp_path / "c.txt").write_text("")
    results = fm.glob(tmp_path, "*.py")
    names = {p.name for p in results}
    assert names == {"a.py", "b.py"}


def test_mkdir_creates_directory(tmp_path: Path) -> None:
    fm = FileManager()
    new_dir = tmp_path / "sub" / "dir"
    fm.mkdir(new_dir, parents=True, exist_ok=True)
    assert new_dir.is_dir()


def test_mkdir_exist_ok_false_raises_on_existing(tmp_path: Path) -> None:
    fm = FileManager()
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        fm.mkdir(existing, exist_ok=False)


def test_mkdir_dry_run_returns_description(tmp_path: Path) -> None:
    fm = FileManager(dry_run=True)
    new_dir = tmp_path / "new_dir"
    result = fm.mkdir(new_dir, parents=True, exist_ok=True)
    assert result is not None
    assert "would create directory" in result
    assert not new_dir.exists()


def test_mkdir_returns_none_on_actual_create(tmp_path: Path) -> None:
    fm = FileManager()
    new_dir = tmp_path / "sub" / "dir"
    result = fm.mkdir(new_dir, parents=True, exist_ok=True)
    assert result is None
    assert new_dir.is_dir()


def test_symlink_dry_run_returns_description(tmp_path: Path) -> None:
    fm = FileManager(dry_run=True)
    link = tmp_path / "AGENTS.md"
    result = fm.symlink(link, "CLAUDE.md")
    assert result is not None
    assert "would symlink" in result
    assert not link.exists()


def test_symlink_creates_link(tmp_path: Path) -> None:
    fm = FileManager()
    link = tmp_path / "AGENTS.md"
    result = fm.symlink(link, "CLAUDE.md")
    assert result is None
    assert link.is_symlink()
    assert link.readlink() == Path("CLAUDE.md")


def test_symlink_skips_existing(tmp_path: Path) -> None:
    fm = FileManager()
    link = tmp_path / "AGENTS.md"
    link.write_text("existing content")
    result = fm.symlink(link, "CLAUDE.md")
    assert result is None
    assert not link.is_symlink()
    assert link.read_text() == "existing content"


def test_file_manager_append_text_creates_file(tmp_path: Path) -> None:
    fm = FileManager()
    p = tmp_path / "log.jsonl"
    result = fm.append_text(p, "line1\n")
    assert result is None
    assert p.read_text() == "line1\n"


def test_file_manager_append_text_appends(tmp_path: Path) -> None:
    fm = FileManager()
    p = tmp_path / "log.jsonl"
    fm.append_text(p, "line1\n")
    fm.append_text(p, "line2\n")
    assert p.read_text() == "line1\nline2\n"


def test_file_manager_append_text_dry_run(tmp_path: Path) -> None:
    fm = FileManager(dry_run=True)
    p = tmp_path / "log.jsonl"
    result = fm.append_text(p, "line1\n")
    assert result is not None
    assert not p.exists()
