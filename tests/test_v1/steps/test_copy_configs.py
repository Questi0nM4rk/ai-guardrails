"""Tests for CopyConfigsStep — copies language-specific base configs."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.models.language import DetectionRules, LanguageConfig
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.copy_configs import CopyConfigsStep
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager


def _make_lang(key: str, configs: list[str]) -> LanguageConfig:
    return LanguageConfig(
        key=key,
        name=key.capitalize(),
        detect=DetectionRules(files=[], patterns=[], directories=[]),
        configs=configs,
        hook_template="",
    )


def _make_context(
    tmp_path: Path,
    languages: list[LanguageConfig],
    *,
    force: bool = False,
) -> tuple[PipelineContext, FakeFileManager]:
    fm = FakeFileManager()
    ctx = PipelineContext(
        project_dir=tmp_path / "project",
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
        languages=languages,
        registry=None,
        dry_run=False,
        force=force,
    )
    return ctx, fm


def test_copy_configs_step_name(tmp_path: Path) -> None:
    step = CopyConfigsStep(configs_dir=tmp_path)
    assert step.name == "copy-configs"


def test_copy_configs_validate_passes(tmp_path: Path) -> None:
    step = CopyConfigsStep(configs_dir=tmp_path)
    ctx, _ = _make_context(tmp_path, [])
    assert step.validate(ctx) == []


def test_copy_copies_language_config_files(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    rust = _make_lang("rust", ["rustfmt.toml"])
    ctx, fm = _make_context(tmp_path, [rust])
    ctx.project_dir = project_dir
    # Seed FakeFileManager with the source config
    fm.seed(configs_dir / "rustfmt.toml", "[rustfmt]\n")

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    assert result.status == "ok"
    assert (project_dir / "rustfmt.toml") in [dst for _, dst in fm.copied]


def test_copy_skips_existing_file_without_force(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    rust = _make_lang("rust", ["rustfmt.toml"])
    ctx, fm = _make_context(tmp_path, [rust])
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "rustfmt.toml", "[rustfmt]\n")
    # Pre-seed existing project file
    fm.seed(project_dir / "rustfmt.toml", "# existing\n")

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    assert result.status == "skip"
    assert not fm.copied


def test_copy_overwrites_with_force(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    rust = _make_lang("rust", ["rustfmt.toml"])
    ctx, fm = _make_context(tmp_path, [rust], force=True)
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "rustfmt.toml", "[rustfmt]\n")
    fm.seed(project_dir / "rustfmt.toml", "# old\n")

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    assert result.status == "ok"
    assert (project_dir / "rustfmt.toml") in [dst for _, dst in fm.copied]


def test_copy_skips_config_not_in_configs_dir(tmp_path: Path) -> None:
    """Config listed in language but not in configs_dir — should warn, not error."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    # rustfmt.toml NOT seeded in FakeFileManager

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    rust = _make_lang("rust", ["rustfmt.toml"])
    ctx, _fm = _make_context(tmp_path, [rust])
    ctx.project_dir = project_dir

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    # Should not crash — missing base configs are silently skipped
    assert result.status in ("ok", "skip", "warn")


def test_copy_no_languages_returns_skip(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    ctx, _fm = _make_context(tmp_path, [])
    ctx.project_dir = project_dir

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    assert result.status == "skip"


def test_copy_multiple_languages_multiple_configs(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    rust = _make_lang("rust", ["rustfmt.toml"])
    cpp = _make_lang("cpp", [".clang-format"])
    ctx, fm = _make_context(tmp_path, [rust, cpp])
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "rustfmt.toml", "[rustfmt]\n")
    fm.seed(configs_dir / ".clang-format", "BasedOnStyle: LLVM\n")

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    assert result.status == "ok"
    copied_dsts = [dst for _, dst in fm.copied]
    assert (project_dir / "rustfmt.toml") in copied_dsts
    assert (project_dir / ".clang-format") in copied_dsts
