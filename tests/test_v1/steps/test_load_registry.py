"""Tests for LoadRegistryStep."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ai_guardrails.constants import REGISTRY_FILENAME
from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.load_registry import LoadRegistryStep
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_MINIMAL_REGISTRY_TOML = """\
schema_version = 1

[global_rules]

[custom]
"""


def _make_context(
    tmp_path: Path,
    *,
    dry_run: bool = False,
) -> tuple[PipelineContext, FakeFileManager]:
    fm = FakeFileManager()
    ctx = PipelineContext(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
        languages=[],
        registry=None,
        dry_run=dry_run,
        force=False,
    )
    return ctx, fm


def test_load_registry_step_name() -> None:
    step = LoadRegistryStep()
    assert step.name == "load-registry"


def test_load_registry_validate_fails_when_file_absent(tmp_path: Path) -> None:
    ctx, _ = _make_context(tmp_path)
    step = LoadRegistryStep()
    errors = step.validate(ctx)
    assert len(errors) == 1
    assert REGISTRY_FILENAME in errors[0]


def test_load_registry_validate_passes_when_file_present(tmp_path: Path) -> None:
    ctx, fm = _make_context(tmp_path)
    fm.seed(tmp_path / REGISTRY_FILENAME, _MINIMAL_REGISTRY_TOML)
    step = LoadRegistryStep()
    assert step.validate(ctx) == []


def test_load_registry_execute_loads_registry(tmp_path: Path) -> None:
    ctx, fm = _make_context(tmp_path)
    fm.seed(tmp_path / REGISTRY_FILENAME, _MINIMAL_REGISTRY_TOML)
    step = LoadRegistryStep()
    result = step.execute(ctx)
    assert result.status == "ok"
    assert ctx.registry is not None


def test_load_registry_dry_run_validate_passes_when_file_absent(tmp_path: Path) -> None:
    """In dry-run mode, validate() must not error when the registry is absent."""
    ctx, _ = _make_context(tmp_path, dry_run=True)
    step = LoadRegistryStep()
    errors = step.validate(ctx)
    assert errors == []


def test_load_registry_dry_run_skips_when_file_absent(tmp_path: Path) -> None:
    """In dry-run mode, LoadRegistryStep must skip gracefully when the registry
    file has not been written yet (ScaffoldRegistryStep also skipped it)."""
    ctx, _ = _make_context(tmp_path, dry_run=True)
    step = LoadRegistryStep()
    result = step.execute(ctx)
    assert result.status == "skip"
    assert "dry" in result.message.lower()
