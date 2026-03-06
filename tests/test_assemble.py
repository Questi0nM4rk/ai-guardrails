"""Tests for guardrails.assemble module."""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from guardrails.assemble import (
    assemble_config,
    detect_languages,
    find_installation_paths,
    load_registry,
    load_template,
    write_config,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_registry() -> dict[str, Any]:
    """Sample language registry for testing."""
    return {
        "python": {
            "name": "Python",
            "emoji": "🐍",
            "detect": {
                "files": ["pyproject.toml", "setup.py", "requirements.txt"],
                "patterns": ["*.py"],
                "directories": [],
            },
            "configs": ["ruff.toml"],
            "pre_commit_template": "python.yaml",
        },
        "go": {
            "name": "Go",
            "emoji": "🐹",
            "detect": {
                "files": ["go.mod", "go.sum"],
                "patterns": ["*.go"],
                "directories": [],
            },
            "configs": [],
            "pre_commit_template": "go.yaml",
        },
        "lua": {
            "name": "Lua",
            "emoji": "🌙",
            "detect": {
                "files": [],
                "patterns": ["*.lua", "*.rockspec"],
                "directories": ["lua"],
            },
            "configs": ["stylua.toml"],
            "pre_commit_template": "lua.yaml",
        },
    }


@pytest.fixture
def templates_dir(temp_dir: Path) -> Path:
    """Create a templates directory with sample templates."""
    tpl_dir = temp_dir / "templates"
    tpl_dir.mkdir()

    # Base template
    base_config = {
        "repos": [
            {
                "repo": "https://github.com/pre-commit/pre-commit-hooks",
                "rev": "v5.0.0",
                "hooks": [{"id": "trailing-whitespace"}],
            }
        ]
    }
    (tpl_dir / "base.yaml").write_text(yaml.dump(base_config))

    # Python template
    python_config = {
        "repos": [
            {
                "repo": "https://github.com/astral-sh/ruff-pre-commit",
                "rev": "v0.8.0",
                "hooks": [{"id": "ruff"}],
            }
        ]
    }
    (tpl_dir / "python.yaml").write_text(yaml.dump(python_config))

    # Go template
    go_config = {
        "repos": [
            {
                "repo": "local",
                "hooks": [{"id": "go-fmt"}],
            }
        ]
    }
    (tpl_dir / "go.yaml").write_text(yaml.dump(go_config))

    return tpl_dir


# =============================================================================
# Test load_registry
# =============================================================================


class TestLoadRegistry:
    """Tests for load_registry function."""

    def test_load_valid_registry(self, temp_dir: Path) -> None:
        """Test loading a valid registry file."""
        registry_data = {"python": {"name": "Python"}}
        registry_path = temp_dir / "languages.yaml"
        registry_path.write_text(yaml.dump(registry_data))

        result = load_registry(registry_path)
        assert result == registry_data

    def test_load_missing_registry(self, temp_dir: Path) -> None:
        """Test loading a missing registry file raises error."""
        registry_path = temp_dir / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            load_registry(registry_path)

    def test_load_invalid_yaml(self, temp_dir: Path) -> None:
        """Test loading invalid YAML raises error."""
        registry_path = temp_dir / "invalid.yaml"
        registry_path.write_text("invalid: yaml: content: [")
        with pytest.raises(yaml.YAMLError):
            load_registry(registry_path)

    def test_load_empty_registry(self, temp_dir: Path) -> None:
        """Test loading empty registry raises TypeError."""
        registry_path = temp_dir / "empty.yaml"
        registry_path.write_text("")
        with pytest.raises(TypeError, match="must be a dict"):
            load_registry(registry_path)

    def test_load_list_registry(self, temp_dir: Path) -> None:
        """Test loading list registry raises TypeError."""
        registry_path = temp_dir / "list.yaml"
        registry_path.write_text("- item1\n- item2")
        with pytest.raises(TypeError, match="must be a dict"):
            load_registry(registry_path)


# =============================================================================
# Test detect_languages
# =============================================================================


class TestDetectLanguages:
    """Tests for detect_languages function."""

    def test_detect_python_from_pyproject(
        self, temp_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test detecting Python from pyproject.toml."""
        (temp_dir / "pyproject.toml").touch()
        result = detect_languages(temp_dir, sample_registry)
        assert "python" in result

    def test_detect_python_from_setup_py(
        self, temp_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test detecting Python from setup.py."""
        (temp_dir / "setup.py").touch()
        result = detect_languages(temp_dir, sample_registry)
        assert "python" in result

    def test_detect_python_from_requirements(
        self, temp_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test detecting Python from requirements.txt."""
        (temp_dir / "requirements.txt").touch()
        result = detect_languages(temp_dir, sample_registry)
        assert "python" in result

    def test_detect_python_from_pattern(
        self, temp_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test detecting Python from .py file pattern."""
        (temp_dir / "main.py").touch()
        result = detect_languages(temp_dir, sample_registry)
        assert "python" in result

    def test_detect_go_from_go_mod(self, temp_dir: Path, sample_registry: dict[str, Any]) -> None:
        """Test detecting Go from go.mod."""
        (temp_dir / "go.mod").touch()
        result = detect_languages(temp_dir, sample_registry)
        assert "go" in result

    def test_detect_go_from_go_sum(self, temp_dir: Path, sample_registry: dict[str, Any]) -> None:
        """Test detecting Go from go.sum."""
        (temp_dir / "go.sum").touch()
        result = detect_languages(temp_dir, sample_registry)
        assert "go" in result

    def test_detect_go_from_pattern(self, temp_dir: Path, sample_registry: dict[str, Any]) -> None:
        """Test detecting Go from .go file pattern."""
        (temp_dir / "main.go").touch()
        result = detect_languages(temp_dir, sample_registry)
        assert "go" in result

    def test_detect_lua_from_directory(
        self, temp_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test detecting Lua from lua/ directory."""
        (temp_dir / "lua").mkdir()
        result = detect_languages(temp_dir, sample_registry)
        assert "lua" in result

    def test_detect_lua_from_pattern(self, temp_dir: Path, sample_registry: dict[str, Any]) -> None:
        """Test detecting Lua from .lua file pattern."""
        (temp_dir / "init.lua").touch()
        result = detect_languages(temp_dir, sample_registry)
        assert "lua" in result

    def test_detect_multiple_languages(
        self, temp_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test detecting multiple languages."""
        (temp_dir / "pyproject.toml").touch()
        (temp_dir / "go.mod").touch()
        result = detect_languages(temp_dir, sample_registry)
        assert "python" in result
        assert "go" in result

    def test_detect_empty_directory(self, temp_dir: Path, sample_registry: dict[str, Any]) -> None:
        """Test detecting nothing in empty directory."""
        result = detect_languages(temp_dir, sample_registry)
        assert result == []


# =============================================================================
# Test load_template
# =============================================================================


class TestLoadTemplate:
    """Tests for load_template function."""

    def test_load_valid_template(self, templates_dir: Path) -> None:
        """Test loading a valid template."""
        result = load_template(templates_dir / "base.yaml")
        assert "repos" in result
        assert len(result["repos"]) > 0

    def test_load_missing_template(self, temp_dir: Path) -> None:
        """Test loading missing template raises error."""
        with pytest.raises(FileNotFoundError):
            load_template(temp_dir / "missing.yaml")

    def test_load_empty_template(self, temp_dir: Path) -> None:
        """Test loading empty template raises TypeError."""
        template_path = temp_dir / "empty.yaml"
        template_path.write_text("")
        with pytest.raises(TypeError, match="must be a dict"):
            load_template(template_path)

    def test_load_list_template(self, temp_dir: Path) -> None:
        """Test loading list template raises TypeError."""
        template_path = temp_dir / "list.yaml"
        template_path.write_text("- repo: local")
        with pytest.raises(TypeError, match="must be a dict"):
            load_template(template_path)


# =============================================================================
# Test assemble_config
# =============================================================================


class TestAssembleConfig:
    """Tests for assemble_config function."""

    def test_base_only(self, templates_dir: Path, sample_registry: dict[str, Any]) -> None:
        """Test assembling base-only config."""
        result = assemble_config([], sample_registry, templates_dir)
        assert "repos" in result
        assert len(result["repos"]) == 1
        assert result["repos"][0]["repo"] == "https://github.com/pre-commit/pre-commit-hooks"

    def test_with_python(self, templates_dir: Path, sample_registry: dict[str, Any]) -> None:
        """Test assembling config with Python."""
        result = assemble_config(["python"], sample_registry, templates_dir)
        assert len(result["repos"]) == 2
        repos = [r["repo"] for r in result["repos"]]
        assert "https://github.com/astral-sh/ruff-pre-commit" in repos

    def test_with_go(self, templates_dir: Path, sample_registry: dict[str, Any]) -> None:
        """Test assembling config with Go."""
        result = assemble_config(["go"], sample_registry, templates_dir)
        assert len(result["repos"]) == 2
        hook_ids = [h["id"] for r in result["repos"] for h in r.get("hooks", [])]
        assert "go-fmt" in hook_ids

    def test_with_multiple_languages(
        self, templates_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test assembling config with multiple languages."""
        result = assemble_config(["python", "go"], sample_registry, templates_dir)
        assert len(result["repos"]) == 3

    def test_missing_template_warns(
        self,
        templates_dir: Path,
        sample_registry: dict[str, Any],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test warning when template is missing."""
        result = assemble_config(["lua"], sample_registry, templates_dir)
        captured = capsys.readouterr()
        assert "Warning: Template lua.yaml not found" in captured.err
        # Should still have base repos
        assert len(result["repos"]) >= 1

    def test_base_template_missing_repos_key(
        self, temp_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test assembling config when base template has no repos key."""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()

        # Base template without "repos" key
        base_config = {"exclude": "^vendor/"}
        (templates_dir / "base.yaml").write_text(yaml.dump(base_config))

        # Python template with repos
        python_config = {
            "repos": [
                {
                    "repo": "https://github.com/astral-sh/ruff-pre-commit",
                    "rev": "v0.8.0",
                }
            ]
        }
        (templates_dir / "python.yaml").write_text(yaml.dump(python_config))

        result = assemble_config(["python"], sample_registry, templates_dir)
        assert "repos" in result
        assert len(result["repos"]) == 1
        assert result["repos"][0]["repo"] == "https://github.com/astral-sh/ruff-pre-commit"

    def test_lang_template_missing_repos_key(
        self, temp_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test assembling config when language template has no repos key."""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()

        # Base template
        base_config = {"repos": [{"repo": "base-repo"}]}
        (templates_dir / "base.yaml").write_text(yaml.dump(base_config))

        # Python template without repos key
        python_config = {"exclude": "^venv/"}
        (templates_dir / "python.yaml").write_text(yaml.dump(python_config))

        result = assemble_config(["python"], sample_registry, templates_dir)
        assert "repos" in result
        assert len(result["repos"]) == 1  # Only base repo

    def test_lang_template_repos_is_none(
        self, temp_dir: Path, sample_registry: dict[str, Any]
    ) -> None:
        """Test assembling config when language template repos is None."""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()

        # Base template
        base_config = {"repos": [{"repo": "base-repo"}]}
        (templates_dir / "base.yaml").write_text(yaml.dump(base_config))

        # Python template with repos: null
        python_config = {"repos": None}
        (templates_dir / "python.yaml").write_text(yaml.dump(python_config))

        result = assemble_config(["python"], sample_registry, templates_dir)
        assert "repos" in result
        assert len(result["repos"]) == 1  # Only base repo


# =============================================================================
# Test write_config
# =============================================================================


class TestWriteConfig:
    """Tests for write_config function."""

    def test_write_config(self, temp_dir: Path) -> None:
        """Test writing config to file."""
        config = {"repos": [{"repo": "local", "hooks": [{"id": "test"}]}]}
        output_path = temp_dir / ".pre-commit-config.yaml"
        write_config(config, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "AI Guardrails" in content
        assert "repos:" in content

    def test_write_config_with_multiline(self, temp_dir: Path) -> None:
        """Test writing config with multiline strings uses block style."""
        config = {"repos": [{"description": "line1\nline2\nline3"}]}
        output_path = temp_dir / "test.yaml"
        write_config(config, output_path)

        content = output_path.read_text()
        assert "|-" in content or "|" in content


# =============================================================================
# Test find_installation_paths
# =============================================================================


class TestFindInstallationPaths:
    """Tests for find_installation_paths function."""

    def test_finds_local_paths(self, temp_dir: Path) -> None:
        """Test finding local development paths when no global install exists."""
        # Patch Path.home() to temp_dir so we don't pick up real ~/.ai-guardrails
        with patch.object(Path, "home", return_value=temp_dir):
            configs_dir, templates_dir = find_installation_paths()
            assert configs_dir.exists()
            assert templates_dir.exists()


def test_local_preferred_over_global(temp_dir: Path) -> None:
    """Test that local dev paths are preferred when they exist (even with global)."""
    # Create global install
    global_dir = temp_dir / ".ai-guardrails"
    configs = global_dir / "configs"
    templates = global_dir / "templates" / "pre-commit"
    configs.mkdir(parents=True)
    templates.mkdir(parents=True)
    (configs / "languages.yaml").write_text("python: {}")

    with patch("guardrails._paths._GLOBAL_INSTALL", global_dir):
        result_configs, _result_templates = find_installation_paths()
        # Local dev paths should win over global
        assert result_configs != configs


def test_global_fallback_when_no_local(temp_dir: Path) -> None:
    """Test global install is used when local dev paths don't exist."""
    global_dir = temp_dir / ".ai-guardrails"
    configs = global_dir / "configs"
    templates = global_dir / "templates"
    pre_commit = templates / "pre-commit"
    configs.mkdir(parents=True)
    pre_commit.mkdir(parents=True)
    (configs / "languages.yaml").write_text("python: {}")

    # Patch _paths.__file__ so _repo_root() resolves to a non-existent local tree,
    # and _GLOBAL_INSTALL so the global fallback points to our temp dir.
    fake_script = str(temp_dir / "fake" / "lib" / "python" / "guardrails" / "_paths.py")

    with (
        patch("guardrails._paths.__file__", fake_script),
        patch("guardrails._paths._GLOBAL_INSTALL", global_dir),
    ):
        result_configs, result_templates = find_installation_paths()
        assert result_configs == configs
        assert result_templates == pre_commit
