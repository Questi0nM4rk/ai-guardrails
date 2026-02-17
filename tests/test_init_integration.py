"""Integration tests for guardrails.init -- run_init() against temp directories."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import chdir
from pathlib import Path
from unittest.mock import patch

import pytest
from guardrails.init import run_init

_PATCHES = (
    "guardrails.init._install_precommit_hooks",
    "guardrails.init._install_claude_hook",
    "guardrails.init._install_dangerous_cmd_hook",
)


@pytest.fixture
def _mock_hooks() -> Iterator[None]:
    """Patch out hook installation side effects."""
    with patch(_PATCHES[0]), patch(_PATCHES[1]), patch(_PATCHES[2]):
        yield


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal git project directory."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    (tmp_path / "main.py").write_text("print('hello')\n")
    return tmp_path


@pytest.mark.usefixtures("_mock_hooks")
def test_creates_precommit_config(project_dir: Path) -> None:
    """Test that .pre-commit-config.yaml is created."""
    with chdir(project_dir):
        run_init(project_type="python", force=True, skip_precommit=False)
    assert (project_dir / ".pre-commit-config.yaml").exists()


@pytest.mark.usefixtures("_mock_hooks")
def test_hooks_dir_populated(project_dir: Path) -> None:
    """Test that .ai-guardrails/hooks/ is populated."""
    with chdir(project_dir):
        run_init(project_type="python", force=True)
    hooks_dir = project_dir / ".ai-guardrails" / "hooks"
    assert hooks_dir.is_dir()
    hook_files = list(hooks_dir.glob("*.sh"))
    assert len(hook_files) >= 5, f"Expected >= 5 hooks, got {len(hook_files)}"


@pytest.mark.usefixtures("_mock_hooks")
def test_dangerous_command_check_in_hooks(project_dir: Path) -> None:
    """Test that dangerous-command-check.sh is deployed."""
    with chdir(project_dir):
        run_init(project_type="python", force=True)
    hooks_dir = project_dir / ".ai-guardrails" / "hooks"
    assert (hooks_dir / "dangerous-command-check.sh").exists()


@pytest.mark.usefixtures("_mock_hooks")
def test_editorconfig_copied(project_dir: Path) -> None:
    """Test that .editorconfig is copied."""
    with chdir(project_dir):
        run_init(project_type="python", force=True)
    assert (project_dir / ".editorconfig").exists()


@pytest.mark.usefixtures("_mock_hooks")
def test_gitignore_updated(project_dir: Path) -> None:
    """Test that .gitignore includes .ai-guardrails/."""
    with chdir(project_dir):
        run_init(project_type="python", force=True)
    gitignore = project_dir / ".gitignore"
    assert gitignore.exists()
    assert ".ai-guardrails/" in gitignore.read_text()


@pytest.mark.usefixtures("_mock_hooks")
def test_ci_workflow_installed(project_dir: Path) -> None:
    """Test CI workflow is installed when install_ci='yes'."""
    (project_dir / ".github").mkdir()
    with chdir(project_dir):
        run_init(project_type="python", force=True, install_ci="yes")
    assert (project_dir / ".github" / "workflows" / "check.yml").exists()


@pytest.mark.usefixtures("_mock_hooks")
def test_python_configs_copied(project_dir: Path) -> None:
    """Test Python-specific configs are copied."""
    with chdir(project_dir):
        run_init(project_type="python", force=True)
    assert (project_dir / "ruff.toml").exists()


@pytest.mark.usefixtures("_mock_hooks")
def test_backup_created_on_force(project_dir: Path) -> None:
    """Test that .bak files are created when --force overwrites."""
    (project_dir / ".editorconfig").write_text("# original\n")
    with chdir(project_dir):
        run_init(project_type="python", force=True)
    assert (project_dir / ".editorconfig.bak").exists()
    assert (project_dir / ".editorconfig.bak").read_text() == "# original\n"


@pytest.mark.usefixtures("_mock_hooks")
def test_dry_run_reports_actions(project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test that dry_run=True reports actions without modifying files."""
    with chdir(project_dir):
        rc = run_init(project_type="python", force=True, dry_run=True)
    assert rc == 0
    # No files should be created
    assert not (project_dir / ".pre-commit-config.yaml").exists()
    assert not (project_dir / ".editorconfig").exists()
    assert not (project_dir / "ruff.toml").exists()
    # But the report should list planned actions
    captured = capsys.readouterr()
    assert "would" in captured.out
    assert ".editorconfig" in captured.out
    assert "ruff.toml" in captured.out
