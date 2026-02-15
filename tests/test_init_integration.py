"""Integration tests for guardrails.init — run_init() against temp directories."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Generator
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


@contextlib.contextmanager
def _chdir(path: Path) -> Generator[None]:
    """Context manager to temporarily change directory."""
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


class TestRunInitIntegration:
    """Integration tests that run run_init() against a temp directory."""

    @patch("guardrails.init._install_precommit_hooks")
    @patch("guardrails.init._install_claude_hook")
    @patch("guardrails.init._install_dangerous_cmd_hook")
    def test_creates_precommit_config(
        self, mock_dangerous: object, mock_claude: object, mock_precommit: object, project_dir: Path
    ) -> None:
        """Test that .pre-commit-config.yaml is created."""
        with _chdir(project_dir):
            run_init(project_type="python", force=True, skip_precommit=False)
        assert (project_dir / ".pre-commit-config.yaml").exists()

    @patch("guardrails.init._install_precommit_hooks")
    @patch("guardrails.init._install_claude_hook")
    @patch("guardrails.init._install_dangerous_cmd_hook")
    def test_hooks_dir_populated(
        self, mock_dangerous: object, mock_claude: object, mock_precommit: object, project_dir: Path
    ) -> None:
        """Test that .ai-guardrails/hooks/ is populated."""
        with _chdir(project_dir):
            run_init(project_type="python", force=True)
        hooks_dir = project_dir / ".ai-guardrails" / "hooks"
        assert hooks_dir.is_dir()
        hook_files = list(hooks_dir.glob("*.sh"))
        assert len(hook_files) >= 5, f"Expected at least 5 hook scripts, got {len(hook_files)}"

    @patch("guardrails.init._install_precommit_hooks")
    @patch("guardrails.init._install_claude_hook")
    @patch("guardrails.init._install_dangerous_cmd_hook")
    def test_dangerous_command_check_in_hooks(
        self, mock_dangerous: object, mock_claude: object, mock_precommit: object, project_dir: Path
    ) -> None:
        """Test that dangerous-command-check.sh is deployed to hooks dir."""
        with _chdir(project_dir):
            run_init(project_type="python", force=True)
        hooks_dir = project_dir / ".ai-guardrails" / "hooks"
        assert (hooks_dir / "dangerous-command-check.sh").exists()

    @patch("guardrails.init._install_precommit_hooks")
    @patch("guardrails.init._install_claude_hook")
    @patch("guardrails.init._install_dangerous_cmd_hook")
    def test_editorconfig_copied(
        self, mock_dangerous: object, mock_claude: object, mock_precommit: object, project_dir: Path
    ) -> None:
        """Test that .editorconfig is copied."""
        with _chdir(project_dir):
            run_init(project_type="python", force=True)
        assert (project_dir / ".editorconfig").exists()

    @patch("guardrails.init._install_precommit_hooks")
    @patch("guardrails.init._install_claude_hook")
    @patch("guardrails.init._install_dangerous_cmd_hook")
    def test_gitignore_updated(
        self, mock_dangerous: object, mock_claude: object, mock_precommit: object, project_dir: Path
    ) -> None:
        """Test that .gitignore includes .ai-guardrails/."""
        with _chdir(project_dir):
            run_init(project_type="python", force=True)
        gitignore = project_dir / ".gitignore"
        assert gitignore.exists()
        assert ".ai-guardrails/" in gitignore.read_text()

    @patch("guardrails.init._install_precommit_hooks")
    @patch("guardrails.init._install_claude_hook")
    @patch("guardrails.init._install_dangerous_cmd_hook")
    def test_ci_workflow_installed(
        self, mock_dangerous: object, mock_claude: object, mock_precommit: object, project_dir: Path
    ) -> None:
        """Test CI workflow is installed when install_ci='yes'."""
        (project_dir / ".github").mkdir()
        with _chdir(project_dir):
            run_init(project_type="python", force=True, install_ci="yes")
        assert (project_dir / ".github" / "workflows" / "check.yml").exists()

    @patch("guardrails.init._install_precommit_hooks")
    @patch("guardrails.init._install_claude_hook")
    @patch("guardrails.init._install_dangerous_cmd_hook")
    def test_python_configs_copied(
        self, mock_dangerous: object, mock_claude: object, mock_precommit: object, project_dir: Path
    ) -> None:
        """Test Python-specific configs are copied."""
        with _chdir(project_dir):
            run_init(project_type="python", force=True)
        assert (project_dir / "ruff.toml").exists()

    @patch("guardrails.init._install_precommit_hooks")
    @patch("guardrails.init._install_claude_hook")
    @patch("guardrails.init._install_dangerous_cmd_hook")
    def test_backup_created_on_force(
        self, mock_dangerous: object, mock_claude: object, mock_precommit: object, project_dir: Path
    ) -> None:
        """Test that .bak files are created when --force overwrites."""
        # Create an existing config
        (project_dir / ".editorconfig").write_text("# original\n")
        with _chdir(project_dir):
            run_init(project_type="python", force=True)
        assert (project_dir / ".editorconfig.bak").exists()
        assert (project_dir / ".editorconfig.bak").read_text() == "# original\n"
