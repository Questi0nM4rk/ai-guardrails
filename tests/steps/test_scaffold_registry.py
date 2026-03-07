"""Tests for ScaffoldRegistryStep."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.scaffold_registry import ScaffoldRegistryStep
from tests.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_TEMPLATE = (
    Path(__file__).parents[2]
    / "src"
    / "ai_guardrails"
    / "_data"
    / "templates"
    / "guardrails-exceptions.toml"
)


def _make_context(
    tmp_path: Path,
    *,
    force: bool = False,
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
        dry_run=False,
        force=force,
    )
    return ctx, fm


def test_scaffold_registry_step_name() -> None:
    step = ScaffoldRegistryStep(template_path=_TEMPLATE)
    assert step.name == "scaffold-registry"


def test_scaffold_validate_fails_if_template_missing(tmp_path: Path) -> None:
    step = ScaffoldRegistryStep(template_path=tmp_path / "missing.toml")
    ctx, _ = _make_context(tmp_path)
    errors = step.validate(ctx)
    assert len(errors) == 1
    assert "template" in errors[0].lower()


def test_scaffold_validate_passes_when_template_exists() -> None:
    step = ScaffoldRegistryStep(template_path=_TEMPLATE)
    ctx, _ = _make_context(Path("/project"))
    assert step.validate(ctx) == []


def test_scaffold_creates_registry_when_missing(tmp_path: Path) -> None:
    step = ScaffoldRegistryStep(template_path=_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    target = tmp_path / ".guardrails-exceptions.toml"
    assert target in [p for p, _ in fm.written]


def test_scaffold_skips_if_registry_exists(tmp_path: Path) -> None:
    # Pre-create the registry
    target = tmp_path / ".guardrails-exceptions.toml"
    target.write_text("schema_version = 1\n")

    step = ScaffoldRegistryStep(template_path=_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "skip"
    # Should not have written anything
    assert not any(p == target for p, _ in fm.written)


def test_scaffold_never_overwrites_even_with_force(tmp_path: Path) -> None:
    """Registry is user data — force flag must not affect it."""
    target = tmp_path / ".guardrails-exceptions.toml"
    target.write_text("schema_version = 1\n")

    step = ScaffoldRegistryStep(template_path=_TEMPLATE)
    ctx, fm = _make_context(tmp_path, force=True)
    result = step.execute(ctx)
    assert result.status == "skip"
    assert not any(p == target for p, _ in fm.written)


def test_scaffold_copies_template_content(tmp_path: Path) -> None:
    step = ScaffoldRegistryStep(template_path=_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    step.execute(ctx)

    target = tmp_path / ".guardrails-exceptions.toml"
    written_content = dict(fm.written).get(target, "")
    assert "schema_version" in written_content
