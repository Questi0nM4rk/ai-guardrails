"""Tests for --profile flag on the init command."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from ai_guardrails.pipelines.base import StepResult
from ai_guardrails.pipelines.init_pipeline import InitOptions, InitPipeline
from tests.conftest import (
    AGENT_TEMPLATE,
    CI_TEMPLATE,
    CONFIGS_DIR,
    DATA_DIR,
    REGISTRY_TEMPLATE,
)

if TYPE_CHECKING:
    from pathlib import Path

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
        data_dir=DATA_DIR,
        configs_dir=CONFIGS_DIR,
        registry_template=REGISTRY_TEMPLATE,
        ci_template=CI_TEMPLATE,
        agent_template=AGENT_TEMPLATE,
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
        data_dir=DATA_DIR,
        configs_dir=CONFIGS_DIR,
        registry_template=REGISTRY_TEMPLATE,
        ci_template=CI_TEMPLATE,
        agent_template=AGENT_TEMPLATE,
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
        data_dir=DATA_DIR,
        configs_dir=CONFIGS_DIR,
        registry_template=REGISTRY_TEMPLATE,
        ci_template=CI_TEMPLATE,
        agent_template=AGENT_TEMPLATE,
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
