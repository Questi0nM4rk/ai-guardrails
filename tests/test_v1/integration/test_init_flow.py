"""End-to-end integration tests for ai-guardrails init + generate flow.

These tests create a real temporary project directory, run the full pipeline
with a real FileManager (disk I/O), and assert that all expected artifacts
exist with correct content — matching the SPEC-v1 requirements.

FakeCommandRunner is used for external tools (lefthook, git) so the tests
are hermetic and don't depend on installed tools.
"""

from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from ai_guardrails.generators.base import compute_hash
from ai_guardrails.hooks.protect_configs import check_tool_input
from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.infra.file_manager import FileManager
from ai_guardrails.pipelines.generate_pipeline import GenerateOptions, GeneratePipeline
from ai_guardrails.pipelines.init_pipeline import InitOptions, InitPipeline
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole

_REPO_ROOT = Path(__file__).parents[3]
_DATA_DIR = _REPO_ROOT / "src" / "ai_guardrails" / "_data"
_CONFIGS_DIR = _DATA_DIR / "configs"
_TEMPLATES_DIR = _DATA_DIR / "templates"
_REGISTRY_TEMPLATE = _TEMPLATES_DIR / "guardrails-exceptions.toml"
_CI_TEMPLATE = _TEMPLATES_DIR / "workflows" / "check.yml"
_AGENT_TEMPLATE = _TEMPLATES_DIR / "CLAUDE.md.guardrails"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_runner() -> FakeCommandRunner:
    """FakeCommandRunner with lefthook registered as available."""
    runner = FakeCommandRunner()
    runner.register(["lefthook", "install"], returncode=0, stdout="")
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.13.6")
    return runner


def _make_init_pipeline(
    *,
    no_hooks: bool = False,
    no_ci: bool = False,
    no_agent_instructions: bool = False,
) -> InitPipeline:
    return InitPipeline(
        options=InitOptions(
            no_hooks=no_hooks,
            no_ci=no_ci,
            no_agent_instructions=no_agent_instructions,
        ),
        data_dir=_DATA_DIR,
        configs_dir=_CONFIGS_DIR,
        registry_template=_REGISTRY_TEMPLATE,
        ci_template=_CI_TEMPLATE,
        agent_template=_AGENT_TEMPLATE,
    )


def _run_init(project_dir: Path, **kwargs: bool) -> list:
    pipeline = _make_init_pipeline(**kwargs)
    return pipeline.run(
        project_dir=project_dir,
        file_manager=FileManager(),
        command_runner=_make_runner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )


def _seed_python_project(project_dir: Path) -> None:
    """Create a minimal Python project structure."""
    (project_dir / ".git").mkdir()
    (project_dir / "main.py").write_text("print('hello')\n")


# ---------------------------------------------------------------------------
# I-1: Full init flow — all artifacts present
# ---------------------------------------------------------------------------


def test_init_python_project_creates_all_artifacts(tmp_path: Path) -> None:
    """init on a Python project creates all expected files without errors."""
    _seed_python_project(tmp_path)
    results = _run_init(tmp_path)

    errors = [r for r in results if r.status == "error"]
    assert not errors, f"Init returned errors: {[r.message for r in errors]}"

    # Universal artifacts (always present)
    assert (tmp_path / ".guardrails-exceptions.toml").exists()
    assert (tmp_path / ".editorconfig").exists()
    assert (tmp_path / ".markdownlint.jsonc").exists()
    assert (tmp_path / ".codespellrc").exists()

    # Python-specific
    assert (tmp_path / "ruff.toml").exists(), "ruff.toml must be created for Python"

    # Hooks and CI
    assert (tmp_path / "lefthook.yml").exists(), "lefthook.yml must be created"
    ci_workflow = tmp_path / ".github" / "workflows" / "check.yml"
    assert ci_workflow.exists(), "CI workflow must be created"

    # Agent instructions
    assert (tmp_path / "CLAUDE.md").exists(), "CLAUDE.md must be created"
    assert (tmp_path / "AGENTS.md").exists(), "AGENTS.md must be created"


# ---------------------------------------------------------------------------
# I-2: Exception registry is valid TOML with correct schema
# ---------------------------------------------------------------------------


def test_init_registry_is_valid_toml(tmp_path: Path) -> None:
    """Registry created by init is valid TOML with schema_version = 1."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    registry_path = tmp_path / ".guardrails-exceptions.toml"
    content = registry_path.read_text()
    data = tomllib.loads(content)

    assert data.get("schema_version") == 1, "schema_version must be 1"


# ---------------------------------------------------------------------------
# I-3: Generated configs have tamper-detection hash headers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    ["ruff.toml", ".editorconfig", ".markdownlint.jsonc", ".codespellrc"],
)
def test_init_generated_configs_have_hash_headers(
    tmp_path: Path, filename: str
) -> None:
    """Each generated config file starts with the ai-guardrails hash header."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    config_path = tmp_path / filename
    if not config_path.exists():
        pytest.skip(f"{filename} not generated for this project")

    first_line = config_path.read_text().splitlines()[0]
    assert "ai-guardrails:hash:sha256:" in first_line, (
        f"{filename} must start with a hash header for tamper protection"
    )


def test_init_hash_headers_are_valid(tmp_path: Path) -> None:
    """Hash headers in generated configs match the file body content."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    for filename in (".editorconfig", ".codespellrc", "ruff.toml"):
        path = tmp_path / filename
        if not path.exists():
            continue
        content = path.read_text()
        first_line, _, body = content.partition("\n")
        stored_hash = first_line.rsplit(":", 1)[-1].strip()
        assert stored_hash == compute_hash(body), (
            f"{filename}: stored hash does not match body — tamper detection would fail"
        )


# ---------------------------------------------------------------------------
# I-4: AGENTS.md is a symlink to CLAUDE.md
# ---------------------------------------------------------------------------


def test_init_agents_md_is_symlink_to_claude_md(tmp_path: Path) -> None:
    """AGENTS.md must be a symlink pointing to CLAUDE.md."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    agents_md = tmp_path / "AGENTS.md"
    assert agents_md.is_symlink(), "AGENTS.md must be a symlink"
    assert agents_md.readlink() == Path("CLAUDE.md"), (
        "AGENTS.md must point to CLAUDE.md"
    )
    # Resolving the symlink must reach CLAUDE.md content
    assert agents_md.resolve().name == "CLAUDE.md"


def test_init_claude_md_has_guardrails_section(tmp_path: Path) -> None:
    """CLAUDE.md must contain the '## AI Guardrails' section."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    claude_md = (tmp_path / "CLAUDE.md").read_text()
    assert "## AI Guardrails" in claude_md, "CLAUDE.md must contain guardrails section"


# ---------------------------------------------------------------------------
# I-5: generate --check passes immediately after init (configs are fresh)
# ---------------------------------------------------------------------------


def test_generate_check_passes_after_init(tmp_path: Path) -> None:
    """Running generate --check right after init must return no errors."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    pipeline = GeneratePipeline(
        options=GenerateOptions(check=True),
        data_dir=_DATA_DIR,
    )
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=FileManager(),
        command_runner=_make_runner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    errors = [r for r in results if r.status == "error"]
    assert not errors, (
        f"generate --check should pass right after init, but got errors: "
        f"{[r.message for r in errors]}"
    )


# ---------------------------------------------------------------------------
# I-6: --no-hooks flag skips hook setup
# ---------------------------------------------------------------------------


def test_init_no_hooks_flag_skips_hook_setup(tmp_path: Path) -> None:
    """--no-hooks must produce no errors and skip lefthook install."""
    _seed_python_project(tmp_path)
    runner = _make_runner()
    pipeline = _make_init_pipeline(no_hooks=True)
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=FileManager(),
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    errors = [r for r in results if r.status == "error"]
    assert not errors

    called_cmds = [tuple(c) for c in runner.calls]
    assert ("lefthook", "install") not in called_cmds, (
        "lefthook install must NOT be called when --no-hooks is set"
    )


# ---------------------------------------------------------------------------
# I-7: --no-ci flag skips CI workflow creation
# ---------------------------------------------------------------------------


def test_init_no_ci_flag_skips_ci_workflow(tmp_path: Path) -> None:
    """--no-ci must not create the GitHub Actions workflow."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path, no_ci=True)

    assert not (tmp_path / ".github" / "workflows" / "check.yml").exists(), (
        "CI workflow must NOT be created when --no-ci is set"
    )


# ---------------------------------------------------------------------------
# I-8: --no-agent-instructions flag skips CLAUDE.md / AGENTS.md
# ---------------------------------------------------------------------------


def test_init_no_agent_instructions_skips_claude_md(tmp_path: Path) -> None:
    """--no-agent-instructions must not create CLAUDE.md or AGENTS.md."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path, no_agent_instructions=True)

    assert not (tmp_path / "CLAUDE.md").exists(), (
        "CLAUDE.md must NOT be created when --no-agent-instructions is set"
    )
    assert not (tmp_path / "AGENTS.md").exists(), (
        "AGENTS.md must NOT be created when --no-agent-instructions is set"
    )


# ---------------------------------------------------------------------------
# I-9: init is idempotent — running twice returns skip for already-done steps
# ---------------------------------------------------------------------------


def test_init_is_idempotent(tmp_path: Path) -> None:
    """Running init twice must not fail — second run skips already-done steps."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)
    results2 = _run_init(tmp_path)

    errors = [r for r in results2 if r.status == "error"]
    assert not errors, (
        f"Second init run must not error, but got: {[r.message for r in errors]}"
    )
    statuses = {r.status for r in results2}
    assert "skip" in statuses, "Second init run should skip already-done steps"


# ---------------------------------------------------------------------------
# I-10: Tamper detection — modified generated config triggers error on generate --check
# ---------------------------------------------------------------------------


def test_generate_check_fails_on_tampered_config(tmp_path: Path) -> None:
    """Modifying a generated config must cause generate --check to return an error."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    # Tamper: strip the hash header and replace with garbage
    ruff_path = tmp_path / "ruff.toml"
    original = ruff_path.read_text()
    # Corrupt the stored hash in the header line
    lines = original.splitlines()
    lines[0] = lines[0][:-4] + "XXXX"  # flip last 4 chars of hash
    ruff_path.write_text("\n".join(lines) + "\n")

    pipeline = GeneratePipeline(
        options=GenerateOptions(check=True),
        data_dir=_DATA_DIR,
    )
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=FileManager(),
        command_runner=_make_runner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    errors = [r for r in results if r.status == "error"]
    assert errors, "generate --check must detect tampered ruff.toml and return error"


# ---------------------------------------------------------------------------
# I-11: protect_configs hook blocks edits to generated files in ai-guardrails projects
# ---------------------------------------------------------------------------


def test_protect_configs_hook_triggers_on_generated_file(tmp_path: Path) -> None:
    """protect_configs must intercept edits to generated config files."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    # Simulate Claude Code Edit tool input for ruff.toml
    tool_input = {
        "file_path": str(tmp_path / "ruff.toml"),
        "old_string": "old",
        "new_string": "new",
    }
    reason = check_tool_input(tool_input, project_dir=tmp_path)
    assert reason is not None, (
        "protect_configs must return a reason for editing a generated config"
    )
    assert "auto-generated" in reason.lower() or "guardrails" in reason.lower()


def test_protect_configs_hook_allows_normal_files(tmp_path: Path) -> None:
    """protect_configs must NOT block edits to regular (non-generated) files."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    tool_input = {
        "file_path": str(tmp_path / "main.py"),
        "old_string": "print",
        "new_string": "logger.info",
    }
    reason = check_tool_input(tool_input, project_dir=tmp_path)
    assert reason is None, (
        "protect_configs must not block edits to regular Python files"
    )


def test_protect_configs_hook_inactive_without_registry(tmp_path: Path) -> None:
    """protect_configs must be a no-op without a registry."""
    # No init — no .guardrails-exceptions.toml
    (tmp_path / "ruff.toml").write_text("# some ruff config\n")

    tool_input = {
        "file_path": str(tmp_path / "ruff.toml"),
        "old_string": "old",
        "new_string": "new",
    }
    reason = check_tool_input(tool_input, project_dir=tmp_path)
    assert reason is None, (
        "protect_configs must be a no-op in projects without a guardrails registry"
    )


# ---------------------------------------------------------------------------
# I-12: generate with unknown language returns a single error
# ---------------------------------------------------------------------------


def test_generate_unknown_language_returns_error(tmp_path: Path) -> None:
    """generate --languages foobar must return a single error naming 'foobar'."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    pipeline = GeneratePipeline(
        options=GenerateOptions(languages=["foobar"]),
        data_dir=_DATA_DIR,
    )
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=FileManager(),
        command_runner=_make_runner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    assert len(results) == 1
    assert results[0].status == "error"
    assert "foobar" in results[0].message.lower()


# ---------------------------------------------------------------------------
# I-13: Registry editing triggers protect_configs prompt
# ---------------------------------------------------------------------------


def test_protect_configs_hook_triggers_on_registry_edit(tmp_path: Path) -> None:
    """protect_configs must intercept direct edits to .guardrails-exceptions.toml."""
    _seed_python_project(tmp_path)
    _run_init(tmp_path)

    tool_input = {
        "file_path": str(tmp_path / ".guardrails-exceptions.toml"),
        "old_string": "schema_version = 1",
        "new_string": "schema_version = 2",
    }
    reason = check_tool_input(tool_input, project_dir=tmp_path)
    assert reason is not None, (
        "protect_configs must block direct edits to the exception registry"
    )
