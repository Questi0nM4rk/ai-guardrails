"""Tests for InitPipeline — full project setup."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.init_pipeline import InitOptions, InitPipeline
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_LANGUAGES_YAML = Path(__file__).parents[3] / "configs" / "languages.yaml"
_REGISTRY_TEMPLATE = Path(__file__).parents[3] / "templates" / "guardrails-exceptions.toml"
_CI_TEMPLATE = Path(__file__).parents[3] / "templates" / "workflows" / "check.yml"
_AGENT_TEMPLATE = Path(__file__).parents[3] / "templates" / "CLAUDE.md.guardrails"
_LEFTHOOK_TEMPLATES = Path(__file__).parents[3] / "templates" / "lefthook"
_CONFIGS_DIR = Path(__file__).parents[3] / "configs"


def _make_pipeline(**kwargs) -> InitPipeline:  # type: ignore[no-untyped-def]
    defaults = {
        "languages_yaml": _LANGUAGES_YAML,
        "configs_dir": _CONFIGS_DIR,
        "lefthook_templates_dir": _LEFTHOOK_TEMPLATES,
        "registry_template": _REGISTRY_TEMPLATE,
        "ci_template": _CI_TEMPLATE,
        "agent_template": _AGENT_TEMPLATE,
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
        languages_yaml=_LANGUAGES_YAML,
        configs_dir=_CONFIGS_DIR,
        lefthook_templates_dir=_LEFTHOOK_TEMPLATES,
        registry_template=_REGISTRY_TEMPLATE,
        ci_template=_CI_TEMPLATE,
        agent_template=_AGENT_TEMPLATE,
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
        languages_yaml=_LANGUAGES_YAML,
        configs_dir=_CONFIGS_DIR,
        lefthook_templates_dir=_LEFTHOOK_TEMPLATES,
        registry_template=_REGISTRY_TEMPLATE,
        ci_template=_CI_TEMPLATE,
        agent_template=_AGENT_TEMPLATE,
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
