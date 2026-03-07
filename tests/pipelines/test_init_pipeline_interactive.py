"""Tests for InitPipeline interactive mode.

Interactive mode prompts before skippable steps (hooks, CI, agent instructions).
Non-interactive mode (default) runs all steps without prompting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.init_pipeline import InitOptions, InitPipeline
from tests.conftest import (
    AGENT_TEMPLATE,
    CI_TEMPLATE,
    CONFIGS_DIR,
    DATA_DIR,
    REGISTRY_TEMPLATE,
    FakeCommandRunner,
    FakeConsole,
    FakeFileManager,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_pipeline(options: InitOptions) -> InitPipeline:
    return InitPipeline(
        options=options,
        data_dir=DATA_DIR,
        configs_dir=CONFIGS_DIR,
        registry_template=REGISTRY_TEMPLATE,
        ci_template=CI_TEMPLATE,
        agent_template=AGENT_TEMPLATE,
    )


def _run(pipeline: InitPipeline, tmp_path: Path) -> list:
    return pipeline.run(
        project_dir=tmp_path,
        file_manager=FakeFileManager(),
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )


# ---------------------------------------------------------------------------
# InitOptions interactive field
# ---------------------------------------------------------------------------


def test_init_options_interactive_defaults_to_false() -> None:
    opts = InitOptions()
    assert opts.interactive is False


def test_init_options_interactive_can_be_set() -> None:
    opts = InitOptions(interactive=True)
    assert opts.interactive is True


# ---------------------------------------------------------------------------
# Non-interactive: prompts never called
# ---------------------------------------------------------------------------


def test_init_pipeline_non_interactive_runs_all_steps(tmp_path: Path) -> None:
    """Non-interactive mode runs all steps, ask_yes_no is never called."""
    options = InitOptions(interactive=False)
    pipeline = _make_pipeline(options)

    with patch("ai_guardrails.pipelines.init_pipeline.ask_yes_no") as mock_ask:
        results = _run(pipeline, tmp_path)

    mock_ask.assert_not_called()
    assert len(results) > 0


def test_init_pipeline_non_interactive_includes_ci(tmp_path: Path) -> None:
    """Non-interactive mode writes CI workflow without asking."""
    options = InitOptions(interactive=False)
    fm = FakeFileManager()
    pipeline = _make_pipeline(options)

    with patch("ai_guardrails.pipelines.init_pipeline.ask_yes_no"):
        pipeline.run(
            project_dir=tmp_path,
            file_manager=fm,
            command_runner=FakeCommandRunner(),
            config_loader=ConfigLoader(),
            console=FakeConsole(),
        )

    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / ".github/workflows/check.yml") in written_paths


# ---------------------------------------------------------------------------
# Interactive: declined steps are skipped
# ---------------------------------------------------------------------------


def test_init_pipeline_interactive_skips_declined_hooks(tmp_path: Path) -> None:
    """When user declines hooks prompt, SetupHooksStep is not executed."""
    options = InitOptions(interactive=True, no_ci=True, no_agent_instructions=True)
    pipeline = _make_pipeline(options)

    # The hooks prompt is the first interactive prompt — decline it
    with patch(
        "ai_guardrails.pipelines.init_pipeline.ask_yes_no", return_value=False
    ) as mock_ask:
        results = _run(pipeline, tmp_path)

    mock_ask.assert_called_once()
    # No error/success from SetupHooksStep means it was skipped
    # (SetupHooksStep runs `lefthook install`; FakeCommandRunner records 0 calls)
    step_messages = [r.message for r in results]
    assert not any(
        "hooks" in m.lower() and "install" in m.lower() for m in step_messages
    )


def test_init_pipeline_interactive_skips_declined_ci(tmp_path: Path) -> None:
    """When user declines CI prompt, SetupCIStep is not executed."""
    options = InitOptions(interactive=True, no_hooks=True, no_agent_instructions=True)
    fm = FakeFileManager()
    pipeline = _make_pipeline(options)

    with patch("ai_guardrails.pipelines.init_pipeline.ask_yes_no", return_value=False):
        pipeline.run(
            project_dir=tmp_path,
            file_manager=fm,
            command_runner=FakeCommandRunner(),
            config_loader=ConfigLoader(),
            console=FakeConsole(),
        )

    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / ".github/workflows/check.yml") not in written_paths


def test_init_pipeline_interactive_skips_declined_agent_instructions(
    tmp_path: Path,
) -> None:
    """When user declines agent instructions, SetupAgentInstructionsStep is skipped."""
    options = InitOptions(interactive=True, no_hooks=True, no_ci=True)
    fm = FakeFileManager()
    pipeline = _make_pipeline(options)

    with patch("ai_guardrails.pipelines.init_pipeline.ask_yes_no", return_value=False):
        pipeline.run(
            project_dir=tmp_path,
            file_manager=fm,
            command_runner=FakeCommandRunner(),
            config_loader=ConfigLoader(),
            console=FakeConsole(),
        )

    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / "CLAUDE.md") not in written_paths


# ---------------------------------------------------------------------------
# Interactive: accepted steps run normally
# ---------------------------------------------------------------------------


def test_init_pipeline_interactive_runs_accepted_ci(tmp_path: Path) -> None:
    """When user accepts CI prompt, CI workflow is written."""
    options = InitOptions(interactive=True, no_hooks=True, no_agent_instructions=True)
    fm = FakeFileManager()
    pipeline = _make_pipeline(options)

    with patch("ai_guardrails.pipelines.init_pipeline.ask_yes_no", return_value=True):
        pipeline.run(
            project_dir=tmp_path,
            file_manager=fm,
            command_runner=FakeCommandRunner(),
            config_loader=ConfigLoader(),
            console=FakeConsole(),
        )

    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / ".github/workflows/check.yml") in written_paths


def test_init_pipeline_interactive_runs_accepted_agent_instructions(
    tmp_path: Path,
) -> None:
    """When user accepts agent instructions prompt, CLAUDE.md is written."""
    options = InitOptions(interactive=True, no_hooks=True, no_ci=True)
    fm = FakeFileManager()
    pipeline = _make_pipeline(options)

    with patch("ai_guardrails.pipelines.init_pipeline.ask_yes_no", return_value=True):
        pipeline.run(
            project_dir=tmp_path,
            file_manager=fm,
            command_runner=FakeCommandRunner(),
            config_loader=ConfigLoader(),
            console=FakeConsole(),
        )

    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / "CLAUDE.md") in written_paths


# ---------------------------------------------------------------------------
# Interactive: --no-X flags suppress the corresponding prompt
# ---------------------------------------------------------------------------


def test_init_pipeline_interactive_no_ci_flag_suppresses_ci_prompt(
    tmp_path: Path,
) -> None:
    """With --no-ci, no CI prompt is shown even in interactive mode."""
    options = InitOptions(
        interactive=True, no_ci=True, no_hooks=True, no_agent_instructions=True
    )
    pipeline = _make_pipeline(options)

    with patch("ai_guardrails.pipelines.init_pipeline.ask_yes_no") as mock_ask:
        _run(pipeline, tmp_path)

    # No prompts at all because all optional steps were suppressed via flags
    mock_ask.assert_not_called()


def test_init_pipeline_interactive_no_hooks_flag_suppresses_hooks_prompt(
    tmp_path: Path,
) -> None:
    """With --no-hooks, no hooks prompt is shown even in interactive mode."""
    options = InitOptions(
        interactive=True, no_hooks=True, no_ci=True, no_agent_instructions=True
    )
    pipeline = _make_pipeline(options)

    with patch("ai_guardrails.pipelines.init_pipeline.ask_yes_no") as mock_ask:
        _run(pipeline, tmp_path)

    mock_ask.assert_not_called()


# ---------------------------------------------------------------------------
# Interactive: prompt count matches number of active optional steps
# ---------------------------------------------------------------------------


def test_init_pipeline_interactive_prompts_for_each_optional_step(
    tmp_path: Path,
) -> None:
    """Interactive mode prompts once per optional step: hooks, CI, agent instrs."""
    options = InitOptions(interactive=True)
    pipeline = _make_pipeline(options)

    with patch(
        "ai_guardrails.pipelines.init_pipeline.ask_yes_no", return_value=True
    ) as mock_ask:
        _run(pipeline, tmp_path)

    # Three optional steps: hooks, CI, agent instructions
    assert mock_ask.call_count == 3


def test_init_pipeline_interactive_prompt_questions_are_descriptive(
    tmp_path: Path,
) -> None:
    """Each prompt question mentions the component being installed."""
    options = InitOptions(interactive=True)
    pipeline = _make_pipeline(options)

    with patch(
        "ai_guardrails.pipelines.init_pipeline.ask_yes_no", return_value=True
    ) as mock_ask:
        _run(pipeline, tmp_path)

    questions = [c.args[0].lower() for c in mock_ask.call_args_list]
    # hooks question
    assert any("hook" in q for q in questions)
    # CI question
    assert any("ci" in q or "workflow" in q for q in questions)
    # agent instructions question
    assert any("agent" in q or "claude" in q or "instruction" in q for q in questions)


def test_init_pipeline_interactive_eof_falls_back_to_defaults(tmp_path: Path) -> None:
    """If stdin closes (EOFError) during interactive prompts, fall back to defaults."""
    options = InitOptions(interactive=True)
    pipeline = _make_pipeline(options)

    with patch(
        "ai_guardrails.pipelines.init_pipeline.ask_yes_no", side_effect=EOFError
    ):
        results = _run(pipeline, tmp_path)

    # Should not crash — falls back to running all steps
    assert len(results) > 0
    assert not any(
        r.status == "error" and "EOFError" in (r.message or "") for r in results
    )
