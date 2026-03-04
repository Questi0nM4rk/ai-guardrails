"""Tests for StatusStep — shows project health: languages, configs, hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.languages._base import BaseLanguagePlugin
from ai_guardrails.models.registry import ExceptionRegistry
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.status_step import StatusStep
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


def _registry_with_exceptions(count: int) -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {},
            "exceptions": [
                {"tool": "ruff", "rule": f"E{i}", "reason": "test"}
                for i in range(count)
            ],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


class _FreshPlugin(BaseLanguagePlugin):
    """Plugin whose check() returns empty list (configs fresh)."""

    key: ClassVar[str] = "python"
    name: ClassVar[str] = "Python"
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = ["ruff.toml"]

    def detect(self, _project_dir: Path) -> bool:
        return True

    def check(
        self,
        _registry: ExceptionRegistry,
        _project_dir: Path,
    ) -> list[str]:
        return []


class _StalePlugin(BaseLanguagePlugin):
    """Plugin whose check() returns one stale config."""

    key: ClassVar[str] = "shell"
    name: ClassVar[str] = "Shell"
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = ["lefthook.yml"]

    def detect(self, _project_dir: Path) -> bool:
        return True

    def check(
        self,
        _registry: ExceptionRegistry,
        _project_dir: Path,
    ) -> list[str]:
        return ["lefthook.yml is stale"]


def _make_context(
    tmp_path: Path,
    *,
    languages: list | None = None,
    registry: ExceptionRegistry | None = None,
    runner: FakeCommandRunner | None = None,
) -> tuple[PipelineContext, FakeConsole]:
    console = FakeConsole()
    ctx = PipelineContext(
        project_dir=tmp_path,
        file_manager=FakeFileManager(),
        command_runner=runner or FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=console,
        languages=languages or [],
        registry=registry,
        dry_run=False,
        force=False,
    )
    return ctx, console


def test_status_step_name() -> None:
    step = StatusStep()
    assert step.name == "status"


def test_status_step_validate_always_passes(tmp_path: Path) -> None:
    step = StatusStep()
    ctx, _ = _make_context(tmp_path)
    assert step.validate(ctx) == []


def test_status_step_always_returns_ok(tmp_path: Path) -> None:
    """StatusStep is informational — always returns ok regardless of staleness."""
    step = StatusStep()
    runner = FakeCommandRunner()
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.13.6")
    ctx, _ = _make_context(
        tmp_path,
        languages=[_StalePlugin()],
        registry=_empty_registry(),
        runner=runner,
    )
    result = step.execute(ctx)
    assert result.status == "ok"


def test_status_step_shows_fresh_configs(tmp_path: Path) -> None:
    """Fresh plugin generates no issues — output says 'fresh'."""
    step = StatusStep()
    runner = FakeCommandRunner()
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.13.6")
    ctx, console = _make_context(
        tmp_path,
        languages=[_FreshPlugin()],
        registry=_empty_registry(),
        runner=runner,
    )
    step.execute(ctx)
    all_output = " ".join(console.all_text())
    assert "fresh" in all_output.lower()


def test_status_step_shows_stale_config(tmp_path: Path) -> None:
    """Stale plugin check() result appears in status output."""
    step = StatusStep()
    runner = FakeCommandRunner()
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.13.6")
    ctx, console = _make_context(
        tmp_path,
        languages=[_StalePlugin()],
        registry=_empty_registry(),
        runner=runner,
    )
    step.execute(ctx)
    all_output = " ".join(console.all_text())
    assert "stale" in all_output.lower()


def test_status_step_shows_hook_status(tmp_path: Path) -> None:
    """Lefthook installed → output includes version string."""
    step = StatusStep()
    runner = FakeCommandRunner()
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.13.6")
    ctx, console = _make_context(
        tmp_path,
        languages=[],
        registry=_empty_registry(),
        runner=runner,
    )
    step.execute(ctx)
    all_output = " ".join(console.all_text())
    assert "lefthook" in all_output.lower()


def test_status_step_shows_hook_warning_when_not_installed(tmp_path: Path) -> None:
    """Missing lefthook → output warns."""
    step = StatusStep()
    runner = FakeCommandRunner()
    runner.register(
        ["lefthook", "version"],
        returncode=1,
        stderr="not found",
    )
    ctx, console = _make_context(
        tmp_path,
        languages=[],
        registry=_empty_registry(),
        runner=runner,
    )
    step.execute(ctx)
    # Should still return ok but warn about hooks
    result = step.execute(ctx)
    assert result.status == "ok"
    assert any(
        "lefthook" in txt.lower() or "hook" in txt.lower()
        for _, txt in console.messages
    )


def test_status_step_shows_exception_count(tmp_path: Path) -> None:
    """Registry with exceptions shows count in output."""
    step = StatusStep()
    runner = FakeCommandRunner()
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.13.6")
    registry = _registry_with_exceptions(3)
    ctx, console = _make_context(
        tmp_path,
        languages=[],
        registry=registry,
        runner=runner,
    )
    step.execute(ctx)
    all_output = " ".join(console.all_text())
    assert "3" in all_output


def test_status_step_shows_detected_languages(tmp_path: Path) -> None:
    """Detected languages appear in status output."""
    step = StatusStep()
    runner = FakeCommandRunner()
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.13.6")
    ctx, console = _make_context(
        tmp_path,
        languages=[_FreshPlugin()],
        registry=_empty_registry(),
        runner=runner,
    )
    step.execute(ctx)
    all_output = " ".join(console.all_text())
    assert "python" in all_output.lower()
