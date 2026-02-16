"""Integration tests for guardrails.init -- run_init() against temp directories."""

from __future__ import annotations

from contextlib import chdir
from pathlib import Path
from unittest.mock import patch

import pytest
from guardrails.init import run_init


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal git project directory."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    (tmp_path / "main.py").write_text("print('hello')\n")
    return tmp_path


@patch("guardrails.init._install_precommit_hooks")
@patch("guardrails.init._install_claude_hook")
@patch("guardrails.init._install_dangerous_cmd_hook")
class TestRunInitIntegration:
    """Integration tests that run run_init() against a temp directory."""

    def test_creates_precommit_config(
        self, _d: object, _c: object, _p: object, project_dir: Path
    ) -> None:
        """Test that .pre-commit-config.yaml is created."""
        with chdir(project_dir):
            run_init(project_type="python", force=True, skip_precommit=False)
        assert (project_dir / ".pre-commit-config.yaml").exists()

    def test_hooks_dir_populated(
        self, _d: object, _c: object, _p: object, project_dir: Path
    ) -> None:
        """Test that .ai-guardrails/hooks/ is populated."""
        with chdir(project_dir):
            run_init(project_type="python", force=True)
        hooks_dir = project_dir / ".ai-guardrails" / "hooks"
        assert hooks_dir.is_dir()
        hook_files = list(hooks_dir.glob("*.sh"))
        assert len(hook_files) >= 5, f"Expected >= 5 hooks, got {len(hook_files)}"

    def test_dangerous_command_check_in_hooks(
        self, _d: object, _c: object, _p: object, project_dir: Path
    ) -> None:
        """Test that dangerous-command-check.sh is deployed."""
        with chdir(project_dir):
            run_init(project_type="python", force=True)
        hooks_dir = project_dir / ".ai-guardrails" / "hooks"
        assert (hooks_dir / "dangerous-command-check.sh").exists()

    def test_editorconfig_copied(
        self, _d: object, _c: object, _p: object, project_dir: Path
    ) -> None:
        """Test that .editorconfig is copied."""
        with chdir(project_dir):
            run_init(project_type="python", force=True)
        assert (project_dir / ".editorconfig").exists()

    def test_gitignore_updated(self, _d: object, _c: object, _p: object, project_dir: Path) -> None:
        """Test that .gitignore includes .ai-guardrails/."""
        with chdir(project_dir):
            run_init(project_type="python", force=True)
        gitignore = project_dir / ".gitignore"
        assert gitignore.exists()
        assert ".ai-guardrails/" in gitignore.read_text()

    def test_ci_workflow_installed(
        self, _d: object, _c: object, _p: object, project_dir: Path
    ) -> None:
        """Test CI workflow is installed when install_ci='yes'."""
        (project_dir / ".github").mkdir()
        with chdir(project_dir):
            run_init(project_type="python", force=True, install_ci="yes")
        assert (project_dir / ".github" / "workflows" / "check.yml").exists()

    def test_python_configs_copied(
        self, _d: object, _c: object, _p: object, project_dir: Path
    ) -> None:
        """Test Python-specific configs are copied."""
        with chdir(project_dir):
            run_init(project_type="python", force=True)
        assert (project_dir / "ruff.toml").exists()

    def test_backup_created_on_force(
        self, _d: object, _c: object, _p: object, project_dir: Path
    ) -> None:
        """Test that .bak files are created when --force overwrites."""
        (project_dir / ".editorconfig").write_text("# original\n")
        with chdir(project_dir):
            run_init(project_type="python", force=True)
        assert (project_dir / ".editorconfig.bak").exists()
        assert (project_dir / ".editorconfig.bak").read_text() == "# original\n"

    def test_dry_run_makes_no_changes(
        self, _d: object, _c: object, _p: object, project_dir: Path
    ) -> None:
        """Test that dry_run=True does not create any files."""
        with chdir(project_dir):
            rc = run_init(project_type="python", force=True, dry_run=True)
        assert rc == 0
        assert not (project_dir / ".pre-commit-config.yaml").exists()
        assert not (project_dir / ".editorconfig").exists()
        assert not (project_dir / "ruff.toml").exists()
