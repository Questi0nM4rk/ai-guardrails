"""Tests for GenerateConfigsStep — runs generators based on detected languages."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.models.language import DetectionRules, LanguageConfig
from ai_guardrails.models.registry import ExceptionRegistry
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.generate_configs import GenerateConfigsStep
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager


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


def _make_lang(key: str) -> LanguageConfig:
    return LanguageConfig(
        key=key,
        name=key.capitalize(),
        detect=DetectionRules(files=[], patterns=[], directories=[]),
        configs=[],
        hook_template="",
    )


def _make_context(
    tmp_path: Path,
    languages: list[LanguageConfig] | None = None,
    registry: ExceptionRegistry | None = None,
) -> tuple[PipelineContext, FakeFileManager]:
    fm = FakeFileManager()
    ctx = PipelineContext(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
        languages=languages or [],
        registry=registry or _empty_registry(),
        dry_run=False,
        force=False,
    )
    return ctx, fm


# ---------------------------------------------------------------------------
# Fake generator for testing
# ---------------------------------------------------------------------------


class _FakeGenerator:
    def __init__(
        self, name: str, output_files: list[str], languages: list[str] | None = None
    ) -> None:
        self.name = name
        self.output_files = output_files
        self._required_langs = languages  # None = always run

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]:
        if self._required_langs is not None and not any(
            lang in languages for lang in self._required_langs
        ):
            return {}
        return {project_dir / fname: f"# {self.name}\n" for fname in self.output_files}

    def check(self, registry: ExceptionRegistry, project_dir: Path) -> list[str]:
        return []


def test_generate_configs_step_name(tmp_path: Path) -> None:
    step = GenerateConfigsStep(generators=[])
    assert step.name == "generate-configs"


def test_generate_configs_validate_fails_without_registry(tmp_path: Path) -> None:
    step = GenerateConfigsStep(generators=[])
    ctx, _ = _make_context(tmp_path)
    ctx.registry = None
    errors = step.validate(ctx)
    assert len(errors) == 1
    assert "registry" in errors[0].lower()


def test_generate_configs_validate_passes_with_registry(tmp_path: Path) -> None:
    step = GenerateConfigsStep(generators=[])
    ctx, _ = _make_context(tmp_path)
    assert step.validate(ctx) == []


def test_generate_configs_writes_output_files(tmp_path: Path) -> None:
    gen = _FakeGenerator("ruff", ["ruff.toml"])
    step = GenerateConfigsStep(generators=[gen])
    ctx, fm = _make_context(tmp_path, languages=[_make_lang("python")])
    result = step.execute(ctx)
    assert result.status == "ok"
    assert any(p == tmp_path / "ruff.toml" for p, _ in fm.written)


def test_generate_configs_runs_all_generators(tmp_path: Path) -> None:
    gen1 = _FakeGenerator("ruff", ["ruff.toml"])
    gen2 = _FakeGenerator("editorconfig", [".editorconfig"])
    step = GenerateConfigsStep(generators=[gen1, gen2])
    ctx, fm = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    written_paths = {p for p, _ in fm.written}
    assert tmp_path / "ruff.toml" in written_paths
    assert tmp_path / ".editorconfig" in written_paths


def test_generate_configs_no_generators_returns_ok(tmp_path: Path) -> None:
    step = GenerateConfigsStep(generators=[])
    ctx, _fm = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"


def test_generate_configs_passes_language_keys_to_generators(tmp_path: Path) -> None:
    """Generator only runs if its required language is present."""
    python_only = _FakeGenerator("ruff", ["ruff.toml"], languages=["python"])
    step = GenerateConfigsStep(generators=[python_only])

    # No python detected — generator should produce nothing
    ctx, fm = _make_context(tmp_path, languages=[_make_lang("rust")])
    step.execute(ctx)
    assert not any(p == tmp_path / "ruff.toml" for p, _ in fm.written)


def test_generate_configs_creates_parent_directories(tmp_path: Path) -> None:
    """Generator output in subdirectory — parent must be created."""
    gen = _FakeGenerator("claude_settings", [".claude/settings.json"])
    step = GenerateConfigsStep(generators=[gen])
    ctx, _fm = _make_context(tmp_path)

    # Should not raise even if .claude/ doesn't exist in FakeFileManager
    result = step.execute(ctx)
    assert result.status == "ok"
