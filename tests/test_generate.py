"""Tests for guardrails.generate -- config generation from exception registry."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import yaml
from guardrails.generate import _generate_to_dir, _load_registry, run_generate_configs
from guardrails.registry import ExceptionRegistry

if TYPE_CHECKING:
    import pytest


class TestLoadRegistry:
    """Test registry loading with error handling."""

    def test_load_valid_registry(self, tmp_path: Path) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text(
            dedent("""\
            schema_version = 1

            [global.ruff]
            "E501" = "line length handled by formatter"
        """)
        )
        result = _load_registry(tmp_path)
        assert result is not None
        assert result.schema_version == 1

    def test_load_missing_registry(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        result = _load_registry(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_load_invalid_toml(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("invalid toml [[[")
        result = _load_registry(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_load_missing_schema_version(self, tmp_path: Path) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text('[global.ruff]\n"E501" = "reason"\n')
        result = _load_registry(tmp_path)
        assert result is None

    def test_load_with_validation_errors(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text(
            dedent("""\
            schema_version = 1

            [global.ruff]
            "E501" = ""
        """)
        )
        result = _load_registry(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "Validation" in captured.err


class TestRunGenerateConfigsDryRun:
    """Test dry-run mode (validate only)."""

    def test_dry_run_valid_registry(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("schema_version = 1\n")
        result = run_generate_configs(project_dir=str(tmp_path), dry_run=True)
        assert result is True
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_dry_run_missing_registry(self, tmp_path: Path) -> None:
        result = run_generate_configs(project_dir=str(tmp_path), dry_run=True)
        assert result is False


class TestRunGenerateConfigsCheck:
    """Test check mode (compare against existing)."""

    def test_check_returns_false_when_no_registry(self, tmp_path: Path) -> None:
        result = run_generate_configs(project_dir=str(tmp_path), check=True)
        assert result is False

    @patch("guardrails.generate._generate_to_dir")
    def test_check_passes_when_configs_up_to_date(
        self,
        mock_gen: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Check succeeds when generated configs match existing files."""
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("schema_version = 1\n")
        # Write existing config that matches what _generate_to_dir produces
        (tmp_path / "ruff.toml").write_text("# generated\n")

        def write_matching(registry: object, project_path: Path, output_dir: Path) -> list[str]:
            (output_dir / "ruff.toml").write_text("# generated\n")
            return ["ruff.toml"]

        mock_gen.side_effect = write_matching
        result = run_generate_configs(project_dir=str(tmp_path), check=True)
        assert result is True
        captured = capsys.readouterr()
        assert "up to date" in captured.out.lower()

    @patch("guardrails.generate._generate_to_dir")
    def test_check_detects_stale_configs(
        self,
        mock_gen: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Check fails when generated configs differ from existing files."""
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("schema_version = 1\n")
        # Write existing config that differs semantically from generated
        (tmp_path / "ruff.toml").write_text('key = "old"\n')

        def write_different(registry: object, project_path: Path, output_dir: Path) -> list[str]:
            (output_dir / "ruff.toml").write_text('key = "new"\n')
            return ["ruff.toml"]

        mock_gen.side_effect = write_different
        result = run_generate_configs(project_dir=str(tmp_path), check=True)
        assert result is False
        captured = capsys.readouterr()
        assert "stale" in captured.err.lower()


class TestRunGenerateConfigsGenerate:
    """Test actual generation mode."""

    def test_returns_false_when_no_registry(self, tmp_path: Path) -> None:
        result = run_generate_configs(project_dir=str(tmp_path))
        assert result is False

    @patch("guardrails.generate._generate_to_dir")
    def test_generates_configs(
        self,
        mock_gen: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("schema_version = 1\n")

        def write_fake_config(registry: object, project_path: Path, output_dir: Path) -> list[str]:
            (output_dir / "ruff.toml").write_text("# generated\n")
            return ["ruff.toml"]

        mock_gen.side_effect = write_fake_config

        result = run_generate_configs(project_dir=str(tmp_path))
        assert result is True
        captured = capsys.readouterr()
        assert "ruff.toml" in captured.out

    @patch("guardrails.generate._generate_to_dir", side_effect=RuntimeError("boom"))
    def test_handles_generation_error(
        self,
        _mock_gen: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("schema_version = 1\n")

        result = run_generate_configs(project_dir=str(tmp_path))
        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.err


# -- Language-filtered generation tests ----------------------------------------


def _make_project_with_registry(tmp_path: Path) -> tuple[Path, ExceptionRegistry]:
    """Set up a project with registry, base templates, and languages.yaml."""
    project = tmp_path / "project"
    project.mkdir()

    # Registry with both ruff and biome exceptions
    (project / ".guardrails-exceptions.toml").write_text(
        dedent("""\
        schema_version = 1

        [global.ruff]
        "D" = "docstrings not enforced"

        [global.markdownlint]
        "MD013" = "line-length handled by editors"

        [global.codespell]
        skip = [".git"]
        ignore_words = ["brin"]

        [[file_exceptions]]
        glob = ["*.config.ts"]
        tool = "biome"
        rules = ["style/noDefaultExport"]
        reason = "Config files"

        [[inline_suppressions]]
        pattern = "noqa: BLE001"
        glob = "**/tools/*.py"
        reason = "MCP tool boundaries"
    """)
    )

    # Base config templates (in a configs/ dir within the project)
    configs = project / "configs"
    configs.mkdir()
    (configs / "ruff.toml").write_text(
        dedent("""\
        target-version = "py311"
        line-length = 88
        [lint]
        select = ["ALL"]
        ignore = []
        [lint.per-file-ignores]
        [format]
        quote-style = "double"
    """)
    )
    (configs / "biome.json").write_text(
        json.dumps(
            {
                "$schema": "https://biomejs.dev/schemas/2.0.0/schema.json",
                "linter": {"enabled": True, "rules": {"recommended": True}},
                "overrides": [],
            },
            indent=2,
        )
    )
    (configs / ".markdownlint.jsonc").write_text(
        dedent("""\
        {
          "default": true,
          "MD013": true,
          "MD041": true
        }
    """)
    )

    # languages.yaml (in configs dir)
    (configs / "languages.yaml").write_text(
        yaml.dump(
            {
                "python": {
                    "name": "Python",
                    "detect": {"files": ["pyproject.toml"], "patterns": ["*.py"]},
                    "configs": ["ruff.toml"],
                },
                "node": {
                    "name": "TypeScript/JavaScript",
                    "detect": {"files": ["package.json"], "patterns": ["*.ts"]},
                    "configs": ["biome.json"],
                },
            }
        )
    )

    registry = ExceptionRegistry.load(project / ".guardrails-exceptions.toml")
    return project, registry


def test_python_only_skips_biome(tmp_path: Path) -> None:
    """Python-only project should not generate biome.json."""
    project, registry = _make_project_with_registry(tmp_path)

    output = tmp_path / "output"
    output.mkdir()

    generated = _generate_to_dir(registry, project, output, languages=["python"])

    assert "ruff.toml" in generated
    assert "biome.json" not in generated
    assert (output / "ruff.toml").exists()
    assert not (output / "biome.json").exists()


def test_node_project_generates_biome(tmp_path: Path) -> None:
    """Node project should generate biome.json."""
    project, registry = _make_project_with_registry(tmp_path)

    output = tmp_path / "output"
    output.mkdir()

    generated = _generate_to_dir(registry, project, output, languages=["node"])

    assert "biome.json" in generated
    assert "ruff.toml" not in generated
    assert (output / "biome.json").exists()
    assert not (output / "ruff.toml").exists()


def test_multi_language_generates_all_relevant(tmp_path: Path) -> None:
    """Python+Node project generates both ruff.toml and biome.json."""
    project, registry = _make_project_with_registry(tmp_path)

    output = tmp_path / "output"
    output.mkdir()

    generated = _generate_to_dir(registry, project, output, languages=["python", "node"])

    assert "ruff.toml" in generated
    assert "biome.json" in generated


def test_agnostic_configs_always_generated(tmp_path: Path) -> None:
    """markdownlint, codespell, allowlist generate regardless of language."""
    project, registry = _make_project_with_registry(tmp_path)

    output = tmp_path / "output"
    output.mkdir()

    # Only Python detected, but agnostic configs should still generate
    generated = _generate_to_dir(registry, project, output, languages=["python"])

    assert ".markdownlint.jsonc" in generated
    assert ".codespellrc" in generated
    assert ".suppression-allowlist" in generated


def test_no_languages_param_generates_all(tmp_path: Path) -> None:
    """When languages=None (default), all configs are generated (backward compat)."""
    project, registry = _make_project_with_registry(tmp_path)

    output = tmp_path / "output"
    output.mkdir()

    generated = _generate_to_dir(registry, project, output, languages=None)

    assert "ruff.toml" in generated
    assert "biome.json" in generated
    assert ".markdownlint.jsonc" in generated


def test_run_generate_configs_detects_languages(tmp_path: Path) -> None:
    """run_generate_configs auto-detects languages and filters generation."""
    project, _ = _make_project_with_registry(tmp_path)

    # Create a Python marker file but no Node marker
    (project / "pyproject.toml").write_text('[project]\nname = "test"\n')

    # Generate configs
    result = run_generate_configs(project_dir=str(project))
    assert result is True

    # ruff.toml should exist (Python detected), biome.json should NOT
    assert (project / "ruff.toml").exists()
    assert not (project / "biome.json").exists()


def test_check_freshness_respects_languages(tmp_path: Path) -> None:
    """Check mode should not flag missing biome.json for Python-only project."""
    project, _ = _make_project_with_registry(tmp_path)

    # Create a Python marker file but no Node marker
    (project / "pyproject.toml").write_text('[project]\nname = "test"\n')

    # Generate configs (will be Python-only)
    assert run_generate_configs(project_dir=str(project)) is True

    # Check should pass without biome.json
    assert run_generate_configs(project_dir=str(project), check=True) is True


def test_lang_configs_matches_languages_yaml() -> None:
    """LANG_CONFIGS in constants.py must match languages.yaml."""
    from guardrails._paths import find_configs_dir
    from guardrails.constants import LANG_CONFIGS

    configs_dir = find_configs_dir()
    with (configs_dir / "languages.yaml").open() as f:
        lang_registry = yaml.safe_load(f)

    for lang, config in lang_registry.items():
        yaml_configs = config.get("configs", [])
        constant_configs = LANG_CONFIGS.get(lang, [])
        assert sorted(yaml_configs) == sorted(constant_configs), (
            f"LANG_CONFIGS[{lang!r}] = {constant_configs} "
            f"does not match languages.yaml configs = {yaml_configs}"
        )
