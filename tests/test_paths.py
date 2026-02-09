"""Tests for guardrails._paths -- installation path resolution."""

from __future__ import annotations

from pathlib import Path

from guardrails._paths import (
    _repo_root,
    find_base_config,
    find_configs_dir,
    find_lib_dir,
    find_templates_dir,
)


class TestRepoRoot:
    """Test _repo_root() resolves to the repository root."""

    def test_returns_parent_of_lib(self) -> None:
        root = _repo_root()
        assert root.is_dir()
        # The repo root should contain lib/python/guardrails
        assert (root / "lib" / "python" / "guardrails").is_dir()

    def test_returns_absolute_path(self) -> None:
        root = _repo_root()
        assert root.is_absolute()


class TestFindConfigsDir:
    """Test find_configs_dir() locates the configs directory."""

    def test_finds_local_configs(self) -> None:
        """In dev mode, local repo configs/ should exist."""
        configs = find_configs_dir()
        assert configs.is_dir()
        assert configs.name == "configs"

    def test_configs_dir_contains_expected_files(self) -> None:
        configs = find_configs_dir()
        # Should have at least one config file
        assert any(configs.iterdir())


class TestFindTemplatesDir:
    """Test find_templates_dir() locates the templates directory."""

    def test_finds_local_templates(self) -> None:
        """In dev mode, local repo templates/ should exist."""
        templates = find_templates_dir()
        assert templates.is_dir()
        assert templates.name == "templates"


class TestFindLibDir:
    """Test find_lib_dir() locates the lib directory."""

    def test_finds_local_lib(self) -> None:
        """In dev mode, local repo lib/ should exist."""
        lib = find_lib_dir()
        assert lib.is_dir()
        assert lib.name == "lib"


class TestFindBaseConfig:
    """Test find_base_config() locates base config templates."""

    def test_finds_from_project_local_configs(self, tmp_path: Path) -> None:
        """Project-local configs/ directory takes precedence."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        config_file = configs_dir / "ruff.toml"
        config_file.write_text("[lint]\nselect = ['E']\n")

        result = find_base_config("ruff.toml", tmp_path)
        assert result is not None
        assert result == config_file

    def test_finds_from_global_configs(self, tmp_path: Path) -> None:
        """Falls back to global ai-guardrails configs."""
        result = find_base_config("ruff.toml", tmp_path)
        # In dev mode, the repo-local configs dir is found via _repo_root()
        assert result is not None
        assert result.name == "ruff.toml"
        assert result.is_file()

    def test_returns_none_for_nonexistent_config(self, tmp_path: Path) -> None:
        result = find_base_config("nonexistent_config.xyz", tmp_path)
        assert result is None

    def test_prefers_local_over_global(self, tmp_path: Path) -> None:
        """Local configs/ should be preferred over global."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        local_config = configs_dir / "test_config.toml"
        local_config.write_text("local = true\n")

        result = find_base_config("test_config.toml", tmp_path)
        assert result == local_config
