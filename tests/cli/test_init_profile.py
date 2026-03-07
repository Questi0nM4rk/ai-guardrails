"""Tests for --profile flag on the init command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_guardrails.pipelines.base import StepResult
from ai_guardrails.pipelines.init_pipeline import InitOptions, InitPipeline

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "ai_guardrails" / "_data"
_CONFIGS_DIR = _DATA_DIR / "configs"
_TEMPLATES_DIR = _DATA_DIR / "templates"
_REGISTRY_TEMPLATE = _TEMPLATES_DIR / "guardrails-exceptions.toml"
_CI_TEMPLATE = _TEMPLATES_DIR / "workflows" / "check.yml"
_AGENT_TEMPLATE = _TEMPLATES_DIR / "CLAUDE.md.guardrails"


_EMPTY_REGISTRY_TOML = "schema_version = 1\n"


def _run_init(tmp_path: Path, profile: str) -> list[StepResult]:
    (tmp_path / ".git").mkdir()
    options = InitOptions(
        profile=profile,
        no_hooks=True,
        no_ci=True,
        no_agent_instructions=True,
    )
    pipeline = InitPipeline(
        options=options,
        data_dir=_DATA_DIR,
        configs_dir=_CONFIGS_DIR,
        registry_template=_REGISTRY_TEMPLATE,
        ci_template=_CI_TEMPLATE,
        agent_template=_AGENT_TEMPLATE,
    )
    fm = MagicMock()
    fm.exists.return_value = True
    fm.read_text.return_value = _EMPTY_REGISTRY_TOML
    runner = MagicMock()
    loader = MagicMock()
    console = MagicMock()
    with (
        patch(
            "ai_guardrails.steps.detect_languages.DetectLanguagesStep.execute",
            return_value=StepResult(status="ok", message="detected"),
        ),
        patch(
            "ai_guardrails.steps.copy_configs.CopyConfigsStep.execute",
            return_value=StepResult(status="ok", message="copied"),
        ),
        patch(
            "ai_guardrails.steps.scaffold_registry.ScaffoldRegistryStep.execute",
            return_value=StepResult(status="ok", message="scaffolded"),
        ),
        patch(
            "ai_guardrails.steps.generate_configs.GenerateConfigsStep.execute",
            return_value=StepResult(status="ok", message="generated"),
        ),
    ):
        return pipeline.run(
            project_dir=tmp_path,
            file_manager=fm,
            command_runner=runner,
            config_loader=loader,
            console=console,
        )


def test_init_with_standard_profile_succeeds(tmp_path: Path):
    results = _run_init(tmp_path, "standard")
    statuses = [r.status for r in results]
    assert "error" not in statuses


def test_init_with_strict_profile_succeeds(tmp_path: Path):
    results = _run_init(tmp_path, "strict")
    statuses = [r.status for r in results]
    assert "error" not in statuses


def test_init_with_minimal_profile_succeeds(tmp_path: Path):
    results = _run_init(tmp_path, "minimal")
    statuses = [r.status for r in results]
    assert "error" not in statuses


def test_init_with_unknown_profile_returns_error(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    options = InitOptions(profile="nonexistent", no_hooks=True, no_ci=True)
    pipeline = InitPipeline(
        options=options,
        data_dir=_DATA_DIR,
        configs_dir=_CONFIGS_DIR,
        registry_template=_REGISTRY_TEMPLATE,
        ci_template=_CI_TEMPLATE,
        agent_template=_AGENT_TEMPLATE,
    )
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=MagicMock(),
        command_runner=MagicMock(),
        config_loader=MagicMock(),
        console=MagicMock(),
    )
    assert len(results) == 1
    assert results[0].status == "error"
    assert "nonexistent" in results[0].message


def test_init_with_unknown_profile_lists_available(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    options = InitOptions(profile="bogus", no_hooks=True, no_ci=True)
    pipeline = InitPipeline(
        options=options,
        data_dir=_DATA_DIR,
        configs_dir=_CONFIGS_DIR,
        registry_template=_REGISTRY_TEMPLATE,
        ci_template=_CI_TEMPLATE,
        agent_template=_AGENT_TEMPLATE,
    )
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=MagicMock(),
        command_runner=MagicMock(),
        config_loader=MagicMock(),
        console=MagicMock(),
    )
    assert results[0].status == "error"
    assert "standard" in results[0].message  # available profiles listed
