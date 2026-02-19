"""Tests for guardrails._paths -- installation path resolution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from guardrails._paths import (
    _GLOBAL_INSTALL,
    _repo_root,
    find_base_config,
    find_configs_dir,
    find_lib_dir,
    find_templates_dir,
)


def test_repo_root_returns_directory() -> None:
    """_repo_root() should return an existing directory."""
    root = _repo_root()
    assert root.is_dir()


def test_repo_root_contains_lib_structure() -> None:
    """_repo_root() should resolve to the repo root containing lib/python/guardrails."""
    root = _repo_root()
    assert (root / "lib" / "python" / "guardrails").is_dir()


def test_repo_root_returns_absolute_path() -> None:
    """_repo_root() should always return an absolute path."""
    root = _repo_root()
    assert root.is_absolute()


def test_find_configs_dir_returns_existing_dir() -> None:
    """In dev mode, find_configs_dir() should find local repo configs/."""
    configs = find_configs_dir()
    assert configs.is_dir()
    assert configs.name == "configs"


def test_find_configs_dir_contains_files() -> None:
    """The configs directory should contain at least one file."""
    configs = find_configs_dir()
    assert any(configs.iterdir())


def test_find_configs_dir_falls_back_to_global(tmp_path: Path) -> None:
    """When local configs/ doesn't exist, fall back to global install."""
    fake_global = tmp_path / ".ai-guardrails" / "configs"
    fake_global.mkdir(parents=True)
    (fake_global / "test.toml").write_text("x = 1\n")

    with (
        patch("guardrails._paths._repo_root", return_value=tmp_path / "nonexistent"),
        patch("guardrails._paths._GLOBAL_INSTALL", tmp_path / ".ai-guardrails"),
    ):
        result = find_configs_dir()
    assert result == fake_global


def test_find_configs_dir_raises_when_no_dir_found(tmp_path: Path) -> None:
    """FileNotFoundError when neither local nor global configs exist."""
    with (
        patch("guardrails._paths._repo_root", return_value=tmp_path / "nonexistent"),
        patch("guardrails._paths._GLOBAL_INSTALL", tmp_path / ".ai-guardrails"),
        pytest.raises(FileNotFoundError, match="configs"),
    ):
        find_configs_dir()


def test_find_templates_dir_returns_existing_dir() -> None:
    """In dev mode, find_templates_dir() should find local repo templates/."""
    templates = find_templates_dir()
    assert templates.is_dir()
    assert templates.name == "templates"


def test_find_templates_dir_falls_back_to_global(tmp_path: Path) -> None:
    """When local templates/ doesn't exist, fall back to global install."""
    fake_global = tmp_path / ".ai-guardrails" / "templates"
    fake_global.mkdir(parents=True)

    with (
        patch("guardrails._paths._repo_root", return_value=tmp_path / "nonexistent"),
        patch("guardrails._paths._GLOBAL_INSTALL", tmp_path / ".ai-guardrails"),
    ):
        result = find_templates_dir()
    assert result == fake_global


def test_find_templates_dir_raises_when_no_dir_found(tmp_path: Path) -> None:
    """FileNotFoundError when neither local nor global templates exist."""
    with (
        patch("guardrails._paths._repo_root", return_value=tmp_path / "nonexistent"),
        patch("guardrails._paths._GLOBAL_INSTALL", tmp_path / ".ai-guardrails"),
        pytest.raises(FileNotFoundError, match="templates"),
    ):
        find_templates_dir()


def test_find_lib_dir_returns_existing_dir() -> None:
    """In dev mode, find_lib_dir() should find local repo lib/."""
    lib = find_lib_dir()
    assert lib.is_dir()
    assert lib.name == "lib"


def test_find_lib_dir_falls_back_to_global(tmp_path: Path) -> None:
    """When local lib/ doesn't exist, fall back to global install."""
    fake_global = tmp_path / ".ai-guardrails" / "lib"
    fake_global.mkdir(parents=True)

    with (
        patch("guardrails._paths._repo_root", return_value=tmp_path / "nonexistent"),
        patch("guardrails._paths._GLOBAL_INSTALL", tmp_path / ".ai-guardrails"),
    ):
        result = find_lib_dir()
    assert result == fake_global


def test_find_lib_dir_raises_when_no_dir_found(tmp_path: Path) -> None:
    """FileNotFoundError when neither local nor global lib exist."""
    with (
        patch("guardrails._paths._repo_root", return_value=tmp_path / "nonexistent"),
        patch("guardrails._paths._GLOBAL_INSTALL", tmp_path / ".ai-guardrails"),
        pytest.raises(FileNotFoundError, match="lib"),
    ):
        find_lib_dir()


def test_find_base_config_prefers_local(tmp_path: Path) -> None:
    """Project-local configs/ directory takes precedence over global."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    config_file = configs_dir / "ruff.toml"
    config_file.write_text("[lint]\nselect = ['E']\n")

    result = find_base_config("ruff.toml", tmp_path)
    assert result is not None
    assert result == config_file


def test_find_base_config_falls_back_to_global(tmp_path: Path) -> None:
    """Falls back to global ai-guardrails configs when local is absent."""
    result = find_base_config("ruff.toml", tmp_path)
    assert result is not None
    assert result.name == "ruff.toml"
    assert result.is_file()


def test_find_base_config_returns_none_for_nonexistent(tmp_path: Path) -> None:
    """Returns None when the config file doesn't exist anywhere."""
    result = find_base_config("nonexistent_config.xyz", tmp_path)
    assert result is None


def test_find_base_config_returns_none_when_configs_dir_missing(tmp_path: Path) -> None:
    """Returns None when find_configs_dir raises FileNotFoundError."""
    with (
        patch("guardrails._paths._repo_root", return_value=tmp_path / "nonexistent"),
        patch("guardrails._paths._GLOBAL_INSTALL", tmp_path / ".ai-guardrails"),
    ):
        result = find_base_config("ruff.toml", tmp_path)
    assert result is None


def test_find_base_config_prefers_local_over_global(tmp_path: Path) -> None:
    """Local configs/ should be preferred over global when both exist."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    local_config = configs_dir / "test_config.toml"
    local_config.write_text("local = true\n")

    result = find_base_config("test_config.toml", tmp_path)
    assert result == local_config


def test_global_install_points_to_home() -> None:
    """_GLOBAL_INSTALL should be under the user home directory."""
    assert Path.home() / ".ai-guardrails" == _GLOBAL_INSTALL
