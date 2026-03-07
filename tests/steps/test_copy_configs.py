"""Tests for CopyConfigsStep — copies language-specific base configs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.generators.base import HASH_HEADER_PREFIX, compute_hash
from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.languages._base import BaseLanguagePlugin
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.copy_configs import CopyConfigsStep
from tests.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

if TYPE_CHECKING:
    from pathlib import Path


class _LangPlugin(BaseLanguagePlugin):
    """Minimal plugin for testing CopyConfigsStep."""

    def __init__(self, key: str, copy_files: list[str]) -> None:
        self.key = key
        self.name = key.capitalize()
        self.copy_files = copy_files
        self.generated_configs: list[str] = []

    def detect(self, project_dir: Path) -> bool:
        return True


def _make_context(
    tmp_path: Path,
    languages: list[BaseLanguagePlugin],
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

    rust = _LangPlugin("rust", ["rustfmt.toml"])
    ctx, fm = _make_context(tmp_path, [rust])
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "rustfmt.toml", "[rustfmt]\n")

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    assert result.status == "ok"
    assert (project_dir / "rustfmt.toml") in [dst for dst, _ in fm.written]


def test_copy_skips_existing_file_without_force(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    rust = _LangPlugin("rust", ["rustfmt.toml"])
    ctx, fm = _make_context(tmp_path, [rust])
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "rustfmt.toml", "[rustfmt]\n")
    fm.seed(project_dir / "rustfmt.toml", "# existing\n")

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    assert result.status == "skip"
    assert not fm.written


def test_copy_overwrites_with_force(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    rust = _LangPlugin("rust", ["rustfmt.toml"])
    ctx, fm = _make_context(tmp_path, [rust], force=True)
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "rustfmt.toml", "[rustfmt]\n")
    fm.seed(project_dir / "rustfmt.toml", "# old\n")

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    assert result.status == "ok"
    assert (project_dir / "rustfmt.toml") in [dst for dst, _ in fm.written]


def test_copy_skips_config_not_in_configs_dir(tmp_path: Path) -> None:
    """Config listed in plugin but not in configs_dir — silently skip."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    rust = _LangPlugin("rust", ["rustfmt.toml"])
    ctx, _fm = _make_context(tmp_path, [rust])
    ctx.project_dir = project_dir

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
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

    rust = _LangPlugin("rust", ["rustfmt.toml"])
    cpp = _LangPlugin("cpp", [".clang-format"])
    ctx, fm = _make_context(tmp_path, [rust, cpp])
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "rustfmt.toml", "[rustfmt]\n")
    fm.seed(configs_dir / ".clang-format", "BasedOnStyle: LLVM\n")

    step = CopyConfigsStep(configs_dir=configs_dir)
    result = step.execute(ctx)
    assert result.status == "ok"
    written_dsts = [dst for dst, _ in fm.written]
    assert (project_dir / "rustfmt.toml") in written_dsts
    assert (project_dir / ".clang-format") in written_dsts


# ---------------------------------------------------------------------------
# Hash header protection (M-8)
# ---------------------------------------------------------------------------


def test_copied_configs_have_hash_headers(tmp_path: Path) -> None:
    """Copied configs must have ai-guardrails hash headers prepended."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    body = "max_width = 100\n"
    rust = _LangPlugin("rust", ["rustfmt.toml"])
    ctx, fm = _make_context(tmp_path, [rust])
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "rustfmt.toml", body)

    step = CopyConfigsStep(configs_dir=configs_dir)
    step.execute(ctx)

    # Find what was written to project_dir/rustfmt.toml
    written_content = fm.read_text(project_dir / "rustfmt.toml")
    assert written_content.startswith(HASH_HEADER_PREFIX)
    # Verify the hash matches the original body
    expected_hash = compute_hash(body)
    first_line = written_content.split("\n", 1)[0]
    assert first_line == f"{HASH_HEADER_PREFIX}{expected_hash}"


def test_copied_json_config_uses_jsonc_comment_prefix(tmp_path: Path) -> None:
    """JSON configs (biome.json) must use // prefix, not # prefix."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    body = '{"linter": {"enabled": true}}\n'
    node = _LangPlugin("node", ["biome.json"])
    ctx, fm = _make_context(tmp_path, [node])
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "biome.json", body)

    step = CopyConfigsStep(configs_dir=configs_dir)
    step.execute(ctx)

    written_content = fm.read_text(project_dir / "biome.json")
    expected_hash = compute_hash(body)
    first_line = written_content.split("\n", 1)[0]
    assert first_line == f"// ai-guardrails:hash:sha256:{expected_hash}"


def test_copied_xml_config_skips_hash_header(tmp_path: Path) -> None:
    """XML configs (Directory.Build.props) skip hash protection."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    body = "<Project>\n</Project>\n"
    dotnet = _LangPlugin("dotnet", ["Directory.Build.props"])
    ctx, fm = _make_context(tmp_path, [dotnet])
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "Directory.Build.props", body)

    step = CopyConfigsStep(configs_dir=configs_dir)
    step.execute(ctx)

    written_content = fm.read_text(project_dir / "Directory.Build.props")
    # XML files should NOT have a hash header
    assert "ai-guardrails:hash" not in written_content
    # Content should be copied as-is
    assert written_content == body


def test_copied_config_detected_as_tampered_after_modification(
    tmp_path: Path,
) -> None:
    """After copying, modifying the file body should invalidate the hash."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    body = "max_width = 100\n"
    rust = _LangPlugin("rust", ["rustfmt.toml"])
    ctx, fm = _make_context(tmp_path, [rust])
    ctx.project_dir = project_dir
    fm.seed(configs_dir / "rustfmt.toml", body)

    step = CopyConfigsStep(configs_dir=configs_dir)
    step.execute(ctx)

    # Read the written content and tamper with it
    written = fm.read_text(project_dir / "rustfmt.toml")
    header_line, _original_body = written.split("\n", 1)
    tampered = header_line + "\n" + "max_width = 120\n"

    # The hash from header should NOT match the tampered body
    stored_hash = header_line[len(HASH_HEADER_PREFIX) :]
    tampered_body = tampered.split("\n", 1)[1]
    assert stored_hash != compute_hash(tampered_body)
