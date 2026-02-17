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
    main,
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
            assert (configs_dir / "languages.yaml").exists()
            assert templates_dir.exists()

    def test_local_preferred_over_global(self, temp_dir: Path) -> None:
        """Test that local dev paths are preferred when they exist (even with global)."""
        # Create global install
        global_dir = temp_dir / ".ai-guardrails"
        configs = global_dir / "configs"
        templates = global_dir / "templates" / "pre-commit"
        configs.mkdir(parents=True)
        templates.mkdir(parents=True)
        (configs / "languages.yaml").write_text("python: {}")

        with patch.object(Path, "home", return_value=temp_dir):
            result_configs, _result_templates = find_installation_paths()
            # Local dev paths should win over global
            assert result_configs != configs

    def test_global_fallback_when_no_local(self, temp_dir: Path) -> None:
        """Test global install is used when local dev paths don't exist."""
        global_dir = temp_dir / ".ai-guardrails"
        configs = global_dir / "configs"
        templates = global_dir / "templates" / "pre-commit"
        configs.mkdir(parents=True)
        templates.mkdir(parents=True)
        (configs / "languages.yaml").write_text("python: {}")

        # Patch __file__ to a location where local dev paths won't resolve
        fake_script = temp_dir / "fake" / "lib" / "python" / "guardrails" / "assemble.py"
        fake_script.parent.mkdir(parents=True)
        fake_script.touch()

        with (
            patch.object(Path, "home", return_value=temp_dir),
            patch("guardrails.assemble.Path.__file__", fake_script, create=True),
            patch("guardrails.assemble.__file__", str(fake_script)),
        ):
            result_configs, result_templates = find_installation_paths()
            assert result_configs == configs
            assert result_templates == templates


# =============================================================================
# Test main CLI
# =============================================================================


class TestMainCLI:
    """Tests for main CLI function."""

    def test_list_detected_empty(self, temp_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --list-detected with no languages."""
        result = main(["--project-dir", str(temp_dir), "--list-detected"])
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_list_detected_python(self, temp_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --list-detected with Python project."""
        (temp_dir / "pyproject.toml").touch()
        result = main(["--project-dir", str(temp_dir), "--list-detected"])
        assert result == 0
        captured = capsys.readouterr()
        assert "python:" in captured.out

    def test_explicit_languages(self, temp_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test explicit --languages flag."""
        result = main(["--project-dir", str(temp_dir), "--languages", "python", "go", "--dry-run"])
        assert result == 0
        captured = capsys.readouterr()
        assert "ruff" in captured.out
        assert "go" in captured.out.lower()

    def test_invalid_language(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error on invalid language."""
        result = main(["--languages", "invalid-lang"])
        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown languages: invalid-lang" in captured.err

    def test_dry_run_output(self, temp_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --dry-run outputs to stdout."""
        result = main(["--project-dir", str(temp_dir), "--dry-run"])
        assert result == 0
        captured = capsys.readouterr()
        assert "repos:" in captured.out

    def test_dry_run_uses_multiline_dumper(
        self, temp_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --dry-run uses MultilineDumper for consistent formatting."""
        # Create a project that will generate config with multiline strings
        global_dir = temp_dir / ".ai-guardrails"
        configs = global_dir / "configs"
        templates = global_dir / "templates" / "pre-commit"
        configs.mkdir(parents=True)
        templates.mkdir(parents=True)

        # Create registry
        registry_data = {
            "python": {
                "name": "Python",
                "pre_commit_template": "python.yaml",
            }
        }
        (configs / "languages.yaml").write_text(yaml.dump(registry_data))

        # Base template
        base_config = {"repos": [{"repo": "base"}]}
        (templates / "base.yaml").write_text(yaml.dump(base_config))

        # Python template with multiline description
        python_config = {
            "repos": [
                {
                    "repo": "https://github.com/astral-sh/ruff-pre-commit",
                    "hooks": [
                        {
                            "id": "ruff",
                            "description": "Line 1\nLine 2\nLine 3",
                        }
                    ],
                }
            ]
        }
        (templates / "python.yaml").write_text(yaml.dump(python_config))

        # Create Python project
        (temp_dir / "pyproject.toml").write_text("")

        # Patch __file__ so local-first resolution falls through to global
        fake_script = str(temp_dir / "fake" / "guardrails" / "assemble.py")
        with (
            patch.object(Path, "home", return_value=temp_dir),
            patch("guardrails.assemble.__file__", fake_script),
        ):
            result = main(["--project-dir", str(temp_dir), "--languages", "python", "--dry-run"])
            assert result == 0
            captured = capsys.readouterr()
            # MultilineDumper should use block style (| or |-) for multiline strings
            # instead of quoted flow style
            assert "description: |" in captured.out or "description: |-" in captured.out

    def test_output_file(self, temp_dir: Path) -> None:
        """Test --output writes to specified file."""
        output_path = temp_dir / "custom.yaml"
        result = main(["--project-dir", str(temp_dir), "--output", str(output_path)])
        assert result == 0
        assert output_path.exists()

    def test_auto_detect_and_generate(
        self, temp_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test auto-detection generates correct config."""
        (temp_dir / "pyproject.toml").touch()
        output_path = temp_dir / ".pre-commit-config.yaml"
        result = main(["--project-dir", str(temp_dir), "--output", str(output_path)])
        assert result == 0
        captured = capsys.readouterr()
        assert "Python" in captured.out
        assert output_path.exists()

    def test_no_languages_warning(self, temp_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test warning when no languages detected."""
        output_path = temp_dir / ".pre-commit-config.yaml"
        result = main(["--project-dir", str(temp_dir), "--output", str(output_path)])
        assert result == 0
        captured = capsys.readouterr()
        assert "No languages detected" in captured.err or "base config only" in captured.out

    def test_handles_missing_base_template(
        self, temp_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test error handling when base.yaml is missing."""
        # Create fake installation directory without base.yaml
        global_dir = temp_dir / ".ai-guardrails"
        configs = global_dir / "configs"
        templates = global_dir / "templates" / "pre-commit"
        configs.mkdir(parents=True)
        templates.mkdir(parents=True)

        # Create languages.yaml but no base.yaml
        (configs / "languages.yaml").write_text("python: {}")

        # Patch __file__ so local-first resolution falls through to global
        fake_script = str(temp_dir / "fake" / "guardrails" / "assemble.py")
        with (
            patch.object(Path, "home", return_value=temp_dir),
            patch("guardrails.assemble.__file__", fake_script),
        ):
            result = main(["--project-dir", str(temp_dir), "--dry-run"])
            assert result == 1
            captured = capsys.readouterr()
            assert "Error:" in captured.err

    def test_handles_invalid_yaml_in_template(
        self, temp_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test error handling when template contains invalid YAML."""
        global_dir = temp_dir / ".ai-guardrails"
        configs = global_dir / "configs"
        templates = global_dir / "templates" / "pre-commit"
        configs.mkdir(parents=True)
        templates.mkdir(parents=True)

        # Create languages.yaml
        (configs / "languages.yaml").write_text("python: {}")

        # Create base.yaml with invalid YAML
        (templates / "base.yaml").write_text("invalid: yaml: [[[")

        # Patch __file__ so local-first resolution falls through to global
        fake_script = str(temp_dir / "fake" / "guardrails" / "assemble.py")
        with (
            patch.object(Path, "home", return_value=temp_dir),
            patch("guardrails.assemble.__file__", fake_script),
        ):
            result = main(["--project-dir", str(temp_dir), "--dry-run"])
            assert result == 1
            captured = capsys.readouterr()
            assert "Error:" in captured.err

    def test_handles_type_error_in_assemble(
        self, temp_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test error handling when template is not a dict (TypeError)."""
        global_dir = temp_dir / ".ai-guardrails"
        configs = global_dir / "configs"
        templates = global_dir / "templates" / "pre-commit"
        configs.mkdir(parents=True)
        templates.mkdir(parents=True)

        # Create languages.yaml
        (configs / "languages.yaml").write_text("python: {}")

        # Create base.yaml with list instead of dict
        (templates / "base.yaml").write_text("- item1\n- item2")

        # Patch __file__ so local-first resolution falls through to global
        fake_script = str(temp_dir / "fake" / "guardrails" / "assemble.py")
        with (
            patch.object(Path, "home", return_value=temp_dir),
            patch("guardrails.assemble.__file__", fake_script),
        ):
            result = main(["--project-dir", str(temp_dir), "--dry-run"])
            assert result == 1
            captured = capsys.readouterr()
            assert "Error:" in captured.err


# =============================================================================
# Integration tests using real registry and templates
# =============================================================================
# Migrated from tests/bats/test_assembly.bats. These tests use the actual
# languages.yaml and pre-commit templates to verify end-to-end assembly.
# =============================================================================


_REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def real_registry() -> dict[str, Any]:
    """Load the real language registry from configs/languages.yaml."""
    registry_path = _REPO_ROOT / "configs" / "languages.yaml"
    return load_registry(registry_path)


@pytest.fixture
def real_templates_dir() -> Path:
    """Return path to the real pre-commit templates directory."""
    return _REPO_ROOT / "templates" / "pre-commit"


def _get_all_hook_ids(config: dict[str, Any]) -> list[str]:
    """Extract all hook IDs from an assembled config."""
    return [hook["id"] for repo in config.get("repos", []) for hook in repo.get("hooks", [])]


class TestAssemblyIntegration:
    """Integration tests using real registry and templates (migrated from bats)."""

    def test_base_hooks_always_present(
        self, real_registry: dict[str, Any], real_templates_dir: Path
    ) -> None:
        """Base hooks (security, spelling, formatting) should always be included."""
        config = assemble_config([], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "gitleaks" in hook_ids
        assert "detect-secrets" in hook_ids
        assert "codespell" in hook_ids
        assert "trailing-whitespace" in hook_ids
        assert "check-yaml" in hook_ids

    def test_python_hooks(self, real_registry: dict[str, Any], real_templates_dir: Path) -> None:
        """Python assembly should include ruff, mypy, bandit, vulture."""
        config = assemble_config(["python"], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "ruff" in hook_ids
        assert "mypy" in hook_ids
        assert "bandit" in hook_ids
        assert "vulture" in hook_ids

        # Should NOT contain other language hooks
        assert "cargo-fmt" not in hook_ids
        assert "golangci-lint" not in hook_ids

    def test_go_hooks(self, real_registry: dict[str, Any], real_templates_dir: Path) -> None:
        """Go assembly should include go-fmt, go-vet, golangci-lint, go-vulncheck."""
        config = assemble_config(["go"], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "go-fmt" in hook_ids
        assert "go-vet" in hook_ids
        assert "golangci-lint" in hook_ids
        assert "go-vulncheck" in hook_ids

        assert "ruff" not in hook_ids
        assert "cargo-fmt" not in hook_ids

    def test_rust_hooks(self, real_registry: dict[str, Any], real_templates_dir: Path) -> None:
        """Rust assembly should include cargo-fmt, cargo-clippy, cargo-doc, cargo-audit."""
        config = assemble_config(["rust"], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "cargo-fmt" in hook_ids
        assert "cargo-clippy" in hook_ids
        assert "cargo-doc" in hook_ids
        assert "cargo-audit" in hook_ids

        assert "ruff" not in hook_ids
        assert "golangci-lint" not in hook_ids

    def test_node_hooks(self, real_registry: dict[str, Any], real_templates_dir: Path) -> None:
        """Node assembly should include biome-check, tsc, npm-audit."""
        config = assemble_config(["node"], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "biome-check" in hook_ids
        assert "tsc" in hook_ids
        assert "npm-audit" in hook_ids

        assert "ruff" not in hook_ids
        assert "cargo-fmt" not in hook_ids

    def test_dotnet_hooks(self, real_registry: dict[str, Any], real_templates_dir: Path) -> None:
        """Dotnet assembly should include dotnet-format, dotnet-build."""
        config = assemble_config(["dotnet"], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "dotnet-format" in hook_ids
        assert "dotnet-build" in hook_ids

        assert "ruff" not in hook_ids
        assert "cargo-fmt" not in hook_ids

    def test_cpp_hooks(self, real_registry: dict[str, Any], real_templates_dir: Path) -> None:
        """C++ assembly should include clang-format, clang-tidy."""
        config = assemble_config(["cpp"], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "clang-format" in hook_ids
        assert "clang-tidy" in hook_ids

        assert "ruff" not in hook_ids
        assert "cargo-fmt" not in hook_ids

    def test_lua_hooks(self, real_registry: dict[str, Any], real_templates_dir: Path) -> None:
        """Lua assembly should include stylua, luacheck."""
        config = assemble_config(["lua"], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "stylua" in hook_ids
        assert "luacheck" in hook_ids

        assert "ruff" not in hook_ids
        assert "cargo-fmt" not in hook_ids

    def test_shell_hooks(self, real_registry: dict[str, Any], real_templates_dir: Path) -> None:
        """Shell assembly should include shellcheck, shfmt."""
        config = assemble_config(["shell"], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "shellcheck" in hook_ids
        assert "shfmt" in hook_ids

        assert "ruff" not in hook_ids
        assert "cargo-fmt" not in hook_ids

    def test_multiple_languages(
        self, real_registry: dict[str, Any], real_templates_dir: Path
    ) -> None:
        """Assembly with multiple languages should include hooks for all."""
        config = assemble_config(["python", "go"], real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "ruff" in hook_ids
        assert "mypy" in hook_ids
        assert "go-fmt" in hook_ids
        assert "golangci-lint" in hook_ids

    def test_all_languages(self, real_registry: dict[str, Any], real_templates_dir: Path) -> None:
        """Assembly with all languages includes hooks for every language."""
        all_langs = list(real_registry.keys())
        config = assemble_config(all_langs, real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "ruff" in hook_ids  # Python
        assert "cargo-fmt" in hook_ids  # Rust
        assert "dotnet-format" in hook_ids  # .NET
        assert "clang-format" in hook_ids  # C++
        assert "stylua" in hook_ids  # Lua
        assert "biome-check" in hook_ids  # Node
        assert "go-fmt" in hook_ids  # Go
        assert "shellcheck" in hook_ids  # Shell


class TestAssemblyOutputIntegration:
    """Integration tests for file output (migrated from bats)."""

    def test_writes_config_to_output_file(
        self,
        tmp_path: Path,
        real_registry: dict[str, Any],
        real_templates_dir: Path,
    ) -> None:
        """Assembled config is written to the output file with correct content."""
        config = assemble_config(["python"], real_registry, real_templates_dir)
        output_path = tmp_path / ".pre-commit-config.yaml"
        write_config(config, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "ruff" in content
        assert "mypy" in content

    def test_output_file_has_header_comment(
        self,
        tmp_path: Path,
        real_registry: dict[str, Any],
        real_templates_dir: Path,
    ) -> None:
        """Output file should contain the AI Guardrails header."""
        config = assemble_config(["python"], real_registry, real_templates_dir)
        output_path = tmp_path / ".pre-commit-config.yaml"
        write_config(config, output_path)

        content = output_path.read_text()
        assert "AI Guardrails" in content
        assert "Auto-Generated" in content

    def test_output_is_valid_yaml(
        self,
        tmp_path: Path,
        real_registry: dict[str, Any],
        real_templates_dir: Path,
    ) -> None:
        """Output file must be valid YAML that round-trips."""
        config = assemble_config(["python", "go"], real_registry, real_templates_dir)
        output_path = tmp_path / ".pre-commit-config.yaml"
        write_config(config, output_path)

        # yaml.safe_load should not raise
        with output_path.open() as f:
            loaded = yaml.safe_load(f)
        assert isinstance(loaded, dict)
        assert "repos" in loaded


class TestAssemblyAutoDetectIntegration:
    """Integration tests for auto-detection + assembly (migrated from bats)."""

    def test_auto_detects_python_and_generates(
        self,
        tmp_path: Path,
        real_registry: dict[str, Any],
        real_templates_dir: Path,
    ) -> None:
        """Auto-detecting Python project generates config with Python hooks."""
        (tmp_path / "pyproject.toml").touch()
        languages = detect_languages(tmp_path, real_registry)
        config = assemble_config(languages, real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "ruff" in hook_ids
        assert "mypy" in hook_ids

    def test_auto_detects_go_and_generates(
        self,
        tmp_path: Path,
        real_registry: dict[str, Any],
        real_templates_dir: Path,
    ) -> None:
        """Auto-detecting Go project generates config with Go hooks."""
        (tmp_path / "go.mod").touch()
        languages = detect_languages(tmp_path, real_registry)
        config = assemble_config(languages, real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "go-fmt" in hook_ids
        assert "golangci-lint" in hook_ids

    def test_auto_detects_multi_language_and_generates(
        self,
        tmp_path: Path,
        real_registry: dict[str, Any],
        real_templates_dir: Path,
    ) -> None:
        """Auto-detecting multi-language project generates hooks for all."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "go.mod").touch()
        (tmp_path / "script.sh").touch()
        languages = detect_languages(tmp_path, real_registry)
        config = assemble_config(languages, real_registry, real_templates_dir)
        hook_ids = _get_all_hook_ids(config)

        assert "ruff" in hook_ids
        assert "go-fmt" in hook_ids
        assert "shellcheck" in hook_ids
