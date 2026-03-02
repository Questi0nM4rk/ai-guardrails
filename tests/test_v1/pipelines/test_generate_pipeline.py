"""Tests for GeneratePipeline — re-generates configs from exception registry."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.models.registry import ExceptionRegistry
from ai_guardrails.pipelines.generate_pipeline import GenerateOptions, GeneratePipeline
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_LANGUAGES_YAML = Path(__file__).parents[3] / "configs" / "languages.yaml"
_REGISTRY_TEMPLATE = Path(__file__).parents[3] / "templates" / "guardrails-exceptions.toml"
_LEFTHOOK_TEMPLATES = Path(__file__).parents[3] / "templates" / "lefthook"
_CONFIGS_DIR = Path(__file__).parents[3] / "configs"


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


def _make_pipeline(*, check: bool = False, languages: list[str] | None = None) -> GeneratePipeline:
    return GeneratePipeline(
        options=GenerateOptions(check=check, languages=languages, dry_run=False),
        languages_yaml=_LANGUAGES_YAML,
        configs_dir=_CONFIGS_DIR,
        lefthook_templates_dir=_LEFTHOOK_TEMPLATES,
    )


def test_generate_options_defaults() -> None:
    opts = GenerateOptions()
    assert opts.check is False
    assert opts.languages is None
    assert opts.dry_run is False


def test_generate_pipeline_can_be_constructed() -> None:
    pipeline = _make_pipeline()
    assert pipeline is not None


def test_generate_pipeline_run_returns_results(tmp_path: Path) -> None:
    """Smoke test: pipeline runs without crashing on empty dir with registry."""
    fm = FakeFileManager()
    # Seed a minimal registry
    registry_content = _REGISTRY_TEMPLATE.read_text()
    fm.seed(tmp_path / ".guardrails-exceptions.toml", registry_content)

    console = FakeConsole()
    pipeline = _make_pipeline()
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=console,
    )
    assert isinstance(results, list)


def test_generate_pipeline_with_explicit_languages(tmp_path: Path) -> None:
    fm = FakeFileManager()
    registry_content = _REGISTRY_TEMPLATE.read_text()
    fm.seed(tmp_path / ".guardrails-exceptions.toml", registry_content)

    pipeline = _make_pipeline(languages=["python"])
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    assert isinstance(results, list)
    # Should not fail even when forcing language override
    assert not any(r.status == "error" for r in results)
