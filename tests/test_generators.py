"""Tests for all config generators."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from textwrap import dedent

import pytest
from guardrails.registry import ExceptionRegistry


@pytest.fixture
def registry(tmp_path: Path) -> ExceptionRegistry:
    """Full registry for generator tests."""
    p = tmp_path / ".guardrails-exceptions.toml"
    p.write_text(
        dedent("""\
        schema_version = 1

        [global.ruff]
        "W191" = "formatter-conflict: tab-indentation"
        "E111" = "formatter-conflict: indentation"
        "D" = "docstrings not enforced yet"
        "ANN" = "using mypy --strict instead"

        [global.markdownlint]
        "MD013" = "line-length handled by editors"
        "MD033" = "inline HTML needed in docs"

        [global.codespell]
        skip = [".git", "*.lock", "node_modules"]
        ignore_words = ["brin", "crate"]

        [global.pyright]
        reportMissingTypeStubs = false

        [[file_exceptions]]
        glob = "tests/**/*.py"
        tool = "ruff"
        rules = ["S101", "ARG001", "PLR2004", "D103"]
        reason = "Test files: asserts, fixtures, magic values"

        [[file_exceptions]]
        glob = "__init__.py"
        tool = "ruff"
        rules = ["D104", "F401"]
        reason = "Package init re-exports"

        [[file_exceptions]]
        glob = ["*.config.ts", "*.config.js"]
        tool = "biome"
        rules = ["style/noDefaultExport"]
        reason = "Config files require default exports"

        [[inline_suppressions]]
        pattern = "noqa: BLE001"
        glob = "**/tools/*.py"
        reason = "MCP tool boundaries"

        [[inline_suppressions]]
        pattern = "noqa: PLR0913"
        glob = ["**/tools/*.py", "**/services/*.py"]
        reason = "MCP functions have many params"

        [[inline_suppressions]]
        pattern = "shellcheck disable=SC2317"
        glob = "**/*.sh"
        reason = "Indirect function calls"

        [skip]
        semgrep = ["tests/"]
    """)
    )
    return ExceptionRegistry.load(p)


@pytest.fixture
def base_ruff_toml(tmp_path: Path) -> Path:
    """Minimal base ruff.toml template."""
    p = tmp_path / "ruff.toml"
    p.write_text(
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
    return p


@pytest.fixture
def base_biome_json(tmp_path: Path) -> Path:
    """Minimal base biome.json template."""
    p = tmp_path / "biome.json"
    p.write_text(
        json.dumps(
            {
                "$schema": "https://biomejs.dev/schemas/2.0.0/schema.json",
                "linter": {
                    "enabled": True,
                    "rules": {
                        "recommended": True,
                        "correctness": {"noUndeclaredVariables": "error"},
                        "style": {"noDefaultExport": "error"},
                    },
                },
                "overrides": [],
            },
            indent=2,
        )
    )
    return p


@pytest.fixture
def base_markdownlint(tmp_path: Path) -> Path:
    """Minimal base .markdownlint.jsonc."""
    p = tmp_path / ".markdownlint.jsonc"
    p.write_text(
        dedent("""\
        {
          "default": true,
          "MD013": true,
          "MD033": true,
          "MD041": true
        }
    """)
    )
    return p


# -- Ruff Generator ------------------------------------------------------------


class TestRuffGenerator:
    """Test ruff.toml generation."""

    def test_merge_global_ignores(
        self,
        registry: ExceptionRegistry,
        base_ruff_toml: Path,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.ruff import generate_ruff

        output = tmp_path / "output" / "ruff.toml"
        generate_ruff(registry, base_ruff_toml, output)

        with output.open("rb") as f:
            result = tomllib.load(f)

        ignores = result["lint"]["ignore"]
        assert "W191" in ignores
        assert "E111" in ignores
        assert "D" in ignores
        assert "ANN" in ignores

    def test_merge_per_file_ignores(
        self,
        registry: ExceptionRegistry,
        base_ruff_toml: Path,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.ruff import generate_ruff

        output = tmp_path / "output" / "ruff.toml"
        generate_ruff(registry, base_ruff_toml, output)

        with output.open("rb") as f:
            result = tomllib.load(f)

        pfi = result["lint"]["per-file-ignores"]
        assert "tests/**/*.py" in pfi
        assert "S101" in pfi["tests/**/*.py"]
        assert "__init__.py" in pfi
        assert "F401" in pfi["__init__.py"]

    def test_preserves_base_settings(
        self,
        registry: ExceptionRegistry,
        base_ruff_toml: Path,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.ruff import generate_ruff

        output = tmp_path / "output" / "ruff.toml"
        generate_ruff(registry, base_ruff_toml, output)

        with output.open("rb") as f:
            result = tomllib.load(f)

        assert result["target-version"] == "py311"
        assert result["line-length"] == 88
        assert result["lint"]["select"] == ["ALL"]
        assert result["format"]["quote-style"] == "double"

    def test_has_auto_generated_header(
        self,
        registry: ExceptionRegistry,
        base_ruff_toml: Path,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.ruff import generate_ruff

        output = tmp_path / "output" / "ruff.toml"
        generate_ruff(registry, base_ruff_toml, output)

        content = output.read_text()
        assert "AUTO-GENERATED" in content


# -- Biome Generator -----------------------------------------------------------


class TestBiomeGenerator:
    """Test biome.json generation."""

    def test_generates_overrides(
        self,
        registry: ExceptionRegistry,
        base_biome_json: Path,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.biome import generate_biome

        output = tmp_path / "output" / "biome.json"
        generate_biome(registry, base_biome_json, output)

        result = json.loads(output.read_text())
        overrides = result.get("overrides", [])
        assert len(overrides) >= 1

        # Find the config files override
        config_override = next(
            (o for o in overrides if "*.config.ts" in o.get("includes", [])),
            None,
        )
        assert config_override is not None

    def test_preserves_base_settings(
        self,
        registry: ExceptionRegistry,
        base_biome_json: Path,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.biome import generate_biome

        output = tmp_path / "output" / "biome.json"
        generate_biome(registry, base_biome_json, output)

        result = json.loads(output.read_text())
        assert result["linter"]["enabled"] is True


# -- Markdownlint Generator ----------------------------------------------------


class TestMarkdownlintGenerator:
    """Test .markdownlint.jsonc generation."""

    def test_disables_excepted_rules(
        self,
        registry: ExceptionRegistry,
        base_markdownlint: Path,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.markdownlint import generate_markdownlint

        output = tmp_path / "output" / ".markdownlint.jsonc"
        generate_markdownlint(registry, base_markdownlint, output)

        # Strip comments for JSON parsing
        content = output.read_text()
        lines = [line for line in content.splitlines() if not line.strip().startswith("//")]
        result = json.loads("\n".join(lines))

        assert result["MD013"] is False
        assert result["MD033"] is False
        # MD041 is not in exceptions, should stay true
        assert result["MD041"] is True


# -- Codespell Generator -------------------------------------------------------


class TestCodespellGenerator:
    """Test .codespellrc generation."""

    def test_generates_codespellrc(
        self,
        registry: ExceptionRegistry,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.codespell import generate_codespell

        output = tmp_path / ".codespellrc"
        generate_codespell(registry, output)

        content = output.read_text()
        assert "skip" in content
        assert ".git" in content
        assert "*.lock" in content
        assert "ignore-words-list" in content
        assert "brin" in content
        assert "crate" in content


# -- Allowlist Generator -------------------------------------------------------


class TestAllowlistGenerator:
    """Test .suppression-allowlist generation."""

    def test_generates_allowlist(
        self,
        registry: ExceptionRegistry,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.allowlist import generate_allowlist

        output = tmp_path / ".suppression-allowlist"
        generate_allowlist(registry, output)

        content = output.read_text()
        assert "noqa: BLE001" in content
        assert "noqa: PLR0913" in content
        assert "shellcheck disable=SC2317" in content

    def test_includes_reasons_as_comments(
        self,
        registry: ExceptionRegistry,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.allowlist import generate_allowlist

        output = tmp_path / ".suppression-allowlist"
        generate_allowlist(registry, output)

        content = output.read_text()
        assert "MCP tool boundaries" in content

    def test_has_header(
        self,
        registry: ExceptionRegistry,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.allowlist import generate_allowlist

        output = tmp_path / ".suppression-allowlist"
        generate_allowlist(registry, output)

        content = output.read_text()
        assert "AUTO-GENERATED" in content


# -- Pyright Generator ---------------------------------------------------------


class TestPyrightGenerator:
    """Test pyright config merging into pyproject.toml."""

    def test_merges_pyright_settings(
        self,
        registry: ExceptionRegistry,
        tmp_path: Path,
    ) -> None:
        from guardrails.generators.pyright import generate_pyright

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            dedent("""\
            [project]
            name = "test"

            [tool.pyright]
            pythonVersion = "3.11"
            typeCheckingMode = "standard"
        """)
        )

        generate_pyright(registry, pyproject)

        with pyproject.open("rb") as f:
            result = tomllib.load(f)

        assert result["tool"]["pyright"]["reportMissingTypeStubs"] is False
        # Original settings preserved
        assert result["tool"]["pyright"]["pythonVersion"] == "3.11"
        assert result["tool"]["pyright"]["typeCheckingMode"] == "standard"


# -- Freshness Check -----------------------------------------------------------


class TestFreshnessCheck:
    """Test config freshness validation (--check mode)."""

    def _setup_project(self, tmp_path: Path) -> Path:
        """Set up a minimal project with registry and base templates."""
        project = tmp_path / "project"
        project.mkdir()

        # Registry
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

            [[inline_suppressions]]
            pattern = "noqa: BLE001"
            glob = "**/tools/*.py"
            reason = "MCP tool boundaries"
        """)
        )

        # Base templates
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
        (configs / ".markdownlint.jsonc").write_text(
            dedent("""\
            {
              "default": true,
              "MD013": true,
              "MD041": true
            }
        """)
        )
        return project

    def test_check_passes_when_fresh(self, tmp_path: Path) -> None:
        from guardrails.generate import run_generate_configs

        project = self._setup_project(tmp_path)

        # Generate configs first
        assert run_generate_configs(str(project)) is True

        # Check should pass
        assert run_generate_configs(str(project), check=True) is True

    def test_check_fails_when_stale(self, tmp_path: Path) -> None:
        from guardrails.generate import run_generate_configs

        project = self._setup_project(tmp_path)

        # Generate configs
        assert run_generate_configs(str(project)) is True

        # Tamper with a generated file
        ruff = project / "ruff.toml"
        ruff.write_text(ruff.read_text() + "\n# manual edit\n")

        # Check should fail
        assert run_generate_configs(str(project), check=True) is False

    def test_check_fails_when_missing(self, tmp_path: Path) -> None:
        from guardrails.generate import run_generate_configs

        project = self._setup_project(tmp_path)

        # Don't generate - files are missing
        assert run_generate_configs(str(project), check=True) is False
