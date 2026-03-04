"""Tests for GenerateConfigsStep — runs active plugins and assembles lefthook.yml."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from ai_guardrails.generators.base import HASH_HEADER_PREFIX
from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.languages._base import BaseLanguagePlugin
from ai_guardrails.models.registry import ExceptionRegistry
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.generate_configs import GenerateConfigsStep
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

if TYPE_CHECKING:
    from pathlib import Path


def _empty_registry() -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


# ---------------------------------------------------------------------------
# Fake plugins for testing
# ---------------------------------------------------------------------------


class _FakePlugin(BaseLanguagePlugin):
    """Minimal plugin: generates one file, no hooks."""

    def __init__(
        self,
        key: str,
        filenames: list[str],
        hooks: dict | None = None,  # type: ignore[type-arg]
    ) -> None:
        self.key = key
        self.name = key.capitalize()
        self.copy_files: list[str] = []
        self.generated_configs = filenames
        self._filenames = filenames
        self._hooks = hooks or {}

    def detect(self, _project_dir: Path) -> bool:
        return True

    def generate(
        self, registry: ExceptionRegistry, project_dir: Path
    ) -> dict[Path, str]:
        return {project_dir / fname: f"# {self.key}\n" for fname in self._filenames}

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        return self._hooks


def _make_context(
    tmp_path: Path,
    languages: list[BaseLanguagePlugin] | None = None,
    registry: ExceptionRegistry | None = None,
) -> tuple[PipelineContext, FakeFileManager]:
    fm = FakeFileManager()
    ctx = PipelineContext(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
        languages=languages or [],
        registry=registry or _empty_registry(),
        dry_run=False,
        force=False,
    )
    return ctx, fm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_generate_configs_step_name(tmp_path: Path) -> None:
    step = GenerateConfigsStep()
    assert step.name == "generate-configs"


def test_generate_configs_validate_fails_without_registry(tmp_path: Path) -> None:
    step = GenerateConfigsStep()
    ctx, _ = _make_context(tmp_path)
    ctx.registry = None
    errors = step.validate(ctx)
    assert len(errors) == 1
    assert "registry" in errors[0].lower()


def test_generate_configs_validate_passes_with_registry(tmp_path: Path) -> None:
    step = GenerateConfigsStep()
    ctx, _ = _make_context(tmp_path)
    assert step.validate(ctx) == []


def test_generate_configs_writes_output_files(tmp_path: Path) -> None:
    plugin = _FakePlugin("ruff", ["ruff.toml"])
    step = GenerateConfigsStep()
    ctx, fm = _make_context(tmp_path, languages=[plugin])
    result = step.execute(ctx)
    assert result.status == "ok"
    assert any(p == tmp_path / "ruff.toml" for p, _ in fm.written)


def test_generate_configs_runs_all_plugins(tmp_path: Path) -> None:
    p1 = _FakePlugin("python", ["ruff.toml"])
    p2 = _FakePlugin("universal", [".editorconfig"])
    step = GenerateConfigsStep()
    ctx, fm = _make_context(tmp_path, languages=[p1, p2])
    result = step.execute(ctx)
    assert result.status == "ok"
    written_paths = {p for p, _ in fm.written}
    assert tmp_path / "ruff.toml" in written_paths
    assert tmp_path / ".editorconfig" in written_paths


def test_generate_configs_no_plugins_returns_ok(tmp_path: Path) -> None:
    step = GenerateConfigsStep()
    ctx, _fm = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"


def test_generate_configs_assembles_lefthook_yml(tmp_path: Path) -> None:
    hooks = {
        "pre-commit": {
            "commands": {
                "codespell": {"run": "codespell {staged_files}", "priority": 2}
            }
        }
    }
    plugin = _FakePlugin("universal", [], hooks=hooks)
    step = GenerateConfigsStep()
    ctx, fm = _make_context(tmp_path, languages=[plugin])
    result = step.execute(ctx)
    assert result.status == "ok"
    written_paths = {p for p, _ in fm.written}
    assert tmp_path / "lefthook.yml" in written_paths


def test_generate_configs_lefthook_has_hash_header(tmp_path: Path) -> None:
    hooks = {
        "pre-commit": {"commands": {"codespell": {"run": "codespell {staged_files}"}}}
    }
    plugin = _FakePlugin("universal", [], hooks=hooks)
    step = GenerateConfigsStep()
    ctx, fm = _make_context(tmp_path, languages=[plugin])
    step.execute(ctx)
    lefthook_content = next(
        content for path, content in fm.written if path.name == "lefthook.yml"
    )
    assert lefthook_content.startswith(HASH_HEADER_PREFIX)


def test_generate_configs_merges_multiple_plugin_hooks(tmp_path: Path) -> None:
    universal_hooks = {
        "pre-commit": {
            "commands": {
                "codespell": {"run": "codespell {staged_files}", "priority": 2}
            }
        }
    }
    python_hooks = {
        "pre-commit": {
            "commands": {
                "ruff-check": {"run": "ruff check {staged_files}", "priority": 2}
            }
        }
    }
    p1 = _FakePlugin("universal", [], hooks=universal_hooks)
    p2 = _FakePlugin("python", ["ruff.toml"], hooks=python_hooks)
    step = GenerateConfigsStep()
    ctx, fm = _make_context(tmp_path, languages=[p1, p2])
    step.execute(ctx)
    lefthook_content = next(
        content for path, content in fm.written if path.name == "lefthook.yml"
    )
    body = lefthook_content.split("\n", 1)[1]
    parsed = yaml.safe_load(body)
    commands = parsed["pre-commit"]["commands"]
    assert "codespell" in commands
    assert "ruff-check" in commands


def test_generate_configs_creates_parent_directories(tmp_path: Path) -> None:
    plugin = _FakePlugin("settings", [".claude/settings.json"])
    step = GenerateConfigsStep()
    ctx, _fm = _make_context(tmp_path, languages=[plugin])
    result = step.execute(ctx)
    assert result.status == "ok"


def test_generate_configs_no_hooks_no_lefthook(tmp_path: Path) -> None:
    """If no plugin returns hook_config, lefthook.yml is not written."""
    plugin = _FakePlugin("python", ["ruff.toml"], hooks={})
    step = GenerateConfigsStep()
    ctx, fm = _make_context(tmp_path, languages=[plugin])
    step.execute(ctx)
    written_paths = {p.name for p, _ in fm.written}
    assert "lefthook.yml" not in written_paths


# ---------------------------------------------------------------------------
# check mode
# ---------------------------------------------------------------------------


class _CheckPlugin(_FakePlugin):
    """Plugin whose check() returns configurable issues."""

    def __init__(self, key: str, issues: list[str]) -> None:
        super().__init__(key, [])
        self._issues = issues

    def check(self, registry: ExceptionRegistry, project_dir: Path) -> list[str]:
        return list(self._issues)


def _make_check_context(
    tmp_path: Path,
    languages: list[_FakePlugin] | None = None,
) -> tuple[PipelineContext, FakeFileManager]:
    fm = FakeFileManager()
    ctx = PipelineContext(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
        languages=languages or [],
        registry=_empty_registry(),
        dry_run=False,
        force=False,
        check=True,
    )
    return ctx, fm


def test_generate_configs_check_mode_returns_ok_when_all_fresh(tmp_path: Path) -> None:
    """check=True with no issues returns ok and message 'All configs are fresh'."""
    plugin = _CheckPlugin("python", issues=[])
    step = GenerateConfigsStep()
    ctx, _ = _make_check_context(tmp_path, languages=[plugin])
    result = step.execute(ctx)
    assert result.status == "ok"
    assert "fresh" in result.message.lower()


def test_generate_configs_check_mode_returns_error_when_stale(tmp_path: Path) -> None:
    """check=True with issues returns error status."""
    plugin = _CheckPlugin("python", issues=["ruff.toml is stale"])
    step = GenerateConfigsStep()
    ctx, _ = _make_check_context(tmp_path, languages=[plugin])
    result = step.execute(ctx)
    assert result.status == "error"
    assert "stale" in result.message.lower() or "1" in result.message


def test_generate_configs_check_mode_does_not_write_files(tmp_path: Path) -> None:
    """check=True must never write any files, even if plugin.generate() would."""

    class _GeneratingCheckPlugin(_FakePlugin):
        """Plugin that both generates files AND reports no issues."""

        def __init__(self) -> None:
            super().__init__("python", ["ruff.toml"])

        def check(self, registry: ExceptionRegistry, project_dir: Path) -> list[str]:
            return []

    plugin = _GeneratingCheckPlugin()
    step = GenerateConfigsStep()
    ctx, fm = _make_check_context(tmp_path, languages=[plugin])
    step.execute(ctx)
    assert fm.written == []
