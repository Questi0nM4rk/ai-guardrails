"""Tests for SetupAgentInstructionsStep — appends guardrails section to CLAUDE.md."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.setup_agent_instructions import SetupAgentInstructionsStep
from tests.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_GUARDRAILS_TEMPLATE = (
    Path(__file__).parents[2]
    / "src"
    / "ai_guardrails"
    / "_data"
    / "templates"
    / "CLAUDE.md.guardrails"
)

_SECTION_MARKER = "## AI Guardrails"


def _make_context(
    tmp_path: Path,
    *,
    existing_claude_md: str | None = None,
    dry_run: bool = False,
) -> tuple[PipelineContext, FakeFileManager]:
    fm = FakeFileManager(dry_run=dry_run)
    if existing_claude_md is not None:
        fm.seed(tmp_path / "CLAUDE.md", existing_claude_md)
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


def test_setup_agent_instructions_step_name() -> None:
    step = SetupAgentInstructionsStep(template_path=_GUARDRAILS_TEMPLATE)
    assert step.name == "setup-agent-instructions"


def test_validate_fails_if_template_missing(tmp_path: Path) -> None:
    step = SetupAgentInstructionsStep(template_path=tmp_path / "missing.md")
    ctx, _ = _make_context(tmp_path)
    errors = step.validate(ctx)
    assert len(errors) == 1
    assert "template" in errors[0].lower()


def test_validate_passes_with_existing_template() -> None:
    step = SetupAgentInstructionsStep(template_path=_GUARDRAILS_TEMPLATE)
    ctx, _ = _make_context(Path("/project"))
    assert step.validate(ctx) == []


def test_creates_claude_md_if_missing(tmp_path: Path) -> None:
    step = SetupAgentInstructionsStep(template_path=_GUARDRAILS_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / "CLAUDE.md") in written_paths


def test_appends_guardrails_section_to_existing_claude_md(tmp_path: Path) -> None:
    step = SetupAgentInstructionsStep(template_path=_GUARDRAILS_TEMPLATE)
    ctx, fm = _make_context(
        tmp_path, existing_claude_md="# My Project\n\nProject docs.\n"
    )
    result = step.execute(ctx)
    assert result.status == "ok"
    written = dict(fm.written)
    content = written[tmp_path / "CLAUDE.md"]
    assert "# My Project" in content
    assert _SECTION_MARKER in content


def test_skips_if_guardrails_section_already_present(tmp_path: Path) -> None:
    existing = f"# Project\n\n{_SECTION_MARKER}\n\nAlready here.\n"
    step = SetupAgentInstructionsStep(template_path=_GUARDRAILS_TEMPLATE)
    ctx, fm = _make_context(tmp_path, existing_claude_md=existing)
    result = step.execute(ctx)
    assert result.status == "skip"
    assert not fm.written


def test_appended_content_comes_from_template(tmp_path: Path) -> None:
    step = SetupAgentInstructionsStep(template_path=_GUARDRAILS_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    step.execute(ctx)
    written = dict(fm.written)
    content = written.get(tmp_path / "CLAUDE.md", "")
    # Template contains AI Guardrails content
    assert "ai-guardrails" in content.lower() or "guardrails" in content.lower()


def test_setup_agent_instructions_creates_agents_md_symlink(tmp_path: Path) -> None:
    """After writing CLAUDE.md, step creates AGENTS.md -> CLAUDE.md symlink."""
    step = SetupAgentInstructionsStep(template_path=_GUARDRAILS_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    assert (tmp_path / "AGENTS.md", "CLAUDE.md") in fm.symlinked


def test_setup_agent_instructions_skips_agents_md_if_exists(tmp_path: Path) -> None:
    """If AGENTS.md already exists, step does not create symlink."""
    step = SetupAgentInstructionsStep(template_path=_GUARDRAILS_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    fm.seed(tmp_path / "AGENTS.md", "custom agents instructions\n")
    step.execute(ctx)
    assert not fm.symlinked


def test_setup_agent_instructions_dry_run_does_not_create_symlink(
    tmp_path: Path,
) -> None:
    """In dry-run mode, AGENTS.md symlink is not created on disk."""
    step = SetupAgentInstructionsStep(template_path=_GUARDRAILS_TEMPLATE)
    ctx, fm = _make_context(tmp_path, dry_run=True)
    step.execute(ctx)
    agents_md = tmp_path / "AGENTS.md"
    assert not agents_md.exists()
    assert not fm.symlinked
