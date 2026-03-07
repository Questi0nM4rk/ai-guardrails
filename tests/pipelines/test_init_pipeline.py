"""Tests for InitPipeline — full project setup."""

from __future__ import annotations

from typing import TYPE_CHECKING

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


def _make_pipeline(**kwargs) -> InitPipeline:  # type: ignore[no-untyped-def]
    defaults = {
        "data_dir": DATA_DIR,
        "configs_dir": CONFIGS_DIR,
        "registry_template": REGISTRY_TEMPLATE,
        "ci_template": CI_TEMPLATE,
        "agent_template": AGENT_TEMPLATE,
    }
    defaults.update(kwargs)
    return InitPipeline(
        options=InitOptions(),
        **defaults,
    )


def test_init_options_defaults() -> None:
    opts = InitOptions()
    assert opts.force is False
    assert opts.no_hooks is False
    assert opts.no_ci is False
    assert opts.no_agent_instructions is False
    assert opts.dry_run is False


def test_init_pipeline_can_be_constructed() -> None:
    pipeline = _make_pipeline()
    assert pipeline is not None


def test_init_pipeline_run_returns_results(tmp_path: Path) -> None:
    """Smoke: run init on empty dir — should scaffold registry, write configs."""
    fm = FakeFileManager()
    pipeline = _make_pipeline()
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    assert isinstance(results, list)
    assert len(results) > 0


def test_init_pipeline_scaffolds_registry(tmp_path: Path) -> None:
    fm = FakeFileManager()
    pipeline = _make_pipeline()
    pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / ".guardrails-exceptions.toml") in written_paths


def test_init_pipeline_generates_editorconfig(tmp_path: Path) -> None:
    fm = FakeFileManager()
    pipeline = _make_pipeline()
    pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / ".editorconfig") in written_paths


def test_init_pipeline_setup_ci_by_default(tmp_path: Path) -> None:
    fm = FakeFileManager()
    pipeline = _make_pipeline()
    pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / ".github/workflows/check.yml") in written_paths


def test_init_pipeline_no_ci_skips_workflow(tmp_path: Path) -> None:
    fm = FakeFileManager()
    pipeline = InitPipeline(
        options=InitOptions(no_ci=True),
        data_dir=DATA_DIR,
        configs_dir=CONFIGS_DIR,
        registry_template=REGISTRY_TEMPLATE,
        ci_template=CI_TEMPLATE,
        agent_template=AGENT_TEMPLATE,
    )
    pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / ".github/workflows/check.yml") not in written_paths


def test_init_pipeline_no_agent_instructions_skips_claude_md(tmp_path: Path) -> None:
    fm = FakeFileManager()
    pipeline = InitPipeline(
        options=InitOptions(no_agent_instructions=True),
        data_dir=DATA_DIR,
        configs_dir=CONFIGS_DIR,
        registry_template=REGISTRY_TEMPLATE,
        ci_template=CI_TEMPLATE,
        agent_template=AGENT_TEMPLATE,
    )
    pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / "CLAUDE.md") not in written_paths


_MINIMAL_REGISTRY = "schema_version = 1\n"


def test_init_pipeline_upgrade_skips_scaffold_registry(tmp_path: Path) -> None:
    """--upgrade skips ScaffoldRegistryStep to preserve existing exception registry."""
    # Pre-populate a fake registry file so we can check it isn't overwritten.
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.write_text(_MINIMAL_REGISTRY)

    fm = FakeFileManager()
    # Seed the existing registry into the fake fs so LoadRegistryStep can read it.
    fm.seed(registry, _MINIMAL_REGISTRY)

    pipeline = InitPipeline(
        options=InitOptions(
            upgrade=True, no_hooks=True, no_ci=True, no_agent_instructions=True
        ),
        data_dir=DATA_DIR,
        configs_dir=CONFIGS_DIR,
        registry_template=REGISTRY_TEMPLATE,
        ci_template=CI_TEMPLATE,
        agent_template=AGENT_TEMPLATE,
    )
    pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )

    written_paths = {p for p, _ in fm.written}
    # ScaffoldRegistryStep must NOT have run — registry must not be in written set.
    assert (tmp_path / ".guardrails-exceptions.toml") not in written_paths
    # No error results (pipeline ran to completion).
    # We verify by checking no error was raised (pipeline returned).


def test_init_pipeline_upgrade_runs_generate_configs(tmp_path: Path) -> None:
    """--upgrade still regenerates tool configs from the existing registry."""
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.write_text(_MINIMAL_REGISTRY)

    fm = FakeFileManager()
    fm.seed(registry, _MINIMAL_REGISTRY)

    pipeline = InitPipeline(
        options=InitOptions(
            upgrade=True, no_hooks=True, no_ci=True, no_agent_instructions=True
        ),
        data_dir=DATA_DIR,
        configs_dir=CONFIGS_DIR,
        registry_template=REGISTRY_TEMPLATE,
        ci_template=CI_TEMPLATE,
        agent_template=AGENT_TEMPLATE,
    )
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )

    # Pipeline ran and produced results.
    assert len(results) > 0
    # At least one non-skip result (GenerateConfigsStep or DetectLanguagesStep ran).
    assert any(r.status != "skip" for r in results)
    # .editorconfig is generated by GenerateConfigsStep — confirms it ran.
    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / ".editorconfig") in written_paths
