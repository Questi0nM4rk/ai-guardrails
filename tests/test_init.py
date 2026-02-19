"""Unit tests for guardrails.init -- covers error paths, flags, and branches.

Standalone test functions (not classes) per project convention.
Every test function has a docstring.  Filesystem and subprocess calls are
mocked so tests never touch the real system.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from contextlib import chdir
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from guardrails.init import (
    _add_to_gitignore,
    _configure_pip_audit,
    _copy_config,
    _detect_python_deps,
    _dry_run_report,
    _generate_from_registry,
    _has_python,
    _install_ci_workflow,
    _install_claude_review,
    _install_coderabbit,
    _install_dangerous_cmd_hook,
    _install_deepsource,
    _install_gemini,
    _install_precommit_hooks,
    _install_pretooluse_hook,
    _is_github_project,
    _print_fail,
    _print_ok,
    _print_skip,
    _print_warn,
    _resolve_languages,
    _scaffold_registry,
    _setup_agent_instructions,
    run_init,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Create a minimal project directory with .git."""
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture
def configs(tmp_path: Path) -> Path:
    """Create a configs directory with common config files."""
    d = tmp_path / "configs"
    d.mkdir()
    (d / ".editorconfig").write_text("root = true\n")
    (d / ".markdownlint.jsonc").write_text("{}\n")
    (d / "ruff.toml").write_text("[lint]\n")
    (d / "rustfmt.toml").write_text('edition = "2021"\n')
    (d / "Directory.Build.props").write_text("<Project />\n")
    (d / ".globalconfig").write_text("# global\n")
    (d / ".clang-format").write_text("BasedOnStyle: LLVM\n")
    (d / "stylua.toml").write_text("[formatting]\n")
    (d / "biome.json").write_text("{}\n")
    return d


@pytest.fixture
def templates(tmp_path: Path) -> Path:
    """Create a templates directory with common template files."""
    d = tmp_path / "templates"
    d.mkdir()
    (d / "guardrails-exceptions.toml").write_text("# registry\n")
    wf = d / "workflows"
    wf.mkdir()
    (wf / "check.yml").write_text("name: check\n")
    (wf / "claude-review.yml").write_text("name: claude\n")
    (d / ".coderabbit.yaml").write_text("reviews:\n")
    gem = d / ".gemini"
    gem.mkdir()
    (gem / "settings.yaml").write_text("model: gemini\n")
    (d / ".deepsource.toml").write_text("[analyzers]\n")
    (d / "CLAUDE.md.guardrails").write_text("## AI Guardrails - Code Standards\nRules here.\n")
    return d


# ---------------------------------------------------------------------------
# _print_* helpers
# ---------------------------------------------------------------------------


def test_print_ok_outputs_green_checkmark(capsys: pytest.CaptureFixture[str]) -> None:
    """_print_ok prints a green checkmark followed by the message."""
    _print_ok("installed")
    out = capsys.readouterr().out
    assert "installed" in out
    assert "\u2713" in out


def test_print_skip_outputs_yellow(capsys: pytest.CaptureFixture[str]) -> None:
    """_print_skip prints a yellow symbol followed by the message."""
    _print_skip("already exists")
    out = capsys.readouterr().out
    assert "already exists" in out


def test_print_warn_outputs_warning(capsys: pytest.CaptureFixture[str]) -> None:
    """_print_warn prints a yellow warning followed by the message."""
    _print_warn("heads up")
    out = capsys.readouterr().out
    assert "heads up" in out


def test_print_fail_outputs_red_cross(capsys: pytest.CaptureFixture[str]) -> None:
    """_print_fail prints a red cross followed by the message."""
    _print_fail("not found")
    out = capsys.readouterr().out
    assert "not found" in out
    assert "\u2717" in out


# ---------------------------------------------------------------------------
# _copy_config
# ---------------------------------------------------------------------------


def test_copy_config_skips_existing_without_force(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_copy_config skips if destination exists and force is False."""
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("new")
    dst.write_text("old")
    _copy_config(src, dst, force=False)
    assert dst.read_text() == "old"
    assert "exists" in capsys.readouterr().out


def test_copy_config_overwrites_with_force_and_backup(tmp_path: Path) -> None:
    """_copy_config creates .bak backup when force-overwriting existing file."""
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("new")
    dst.write_text("old")
    _copy_config(src, dst, force=True)
    assert dst.read_text() == "new"
    assert (tmp_path / "dst.txt.bak").read_text() == "old"


def test_copy_config_creates_parent_dirs(tmp_path: Path) -> None:
    """_copy_config creates parent directories if they don't exist."""
    src = tmp_path / "src.txt"
    dst = tmp_path / "sub" / "dir" / "dst.txt"
    src.write_text("content")
    _copy_config(src, dst, force=True)
    assert dst.read_text() == "content"


def test_copy_config_prints_fail_when_source_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_copy_config prints failure when source file does not exist."""
    src = tmp_path / "nonexistent.txt"
    dst = tmp_path / "dst.txt"
    _copy_config(src, dst, force=True)
    assert not dst.exists()
    out = capsys.readouterr().out
    assert "not found" in out


def test_copy_config_copies_new_file(tmp_path: Path) -> None:
    """_copy_config copies file when destination does not exist."""
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("hello")
    _copy_config(src, dst, force=False)
    assert dst.read_text() == "hello"


# ---------------------------------------------------------------------------
# _is_github_project
# ---------------------------------------------------------------------------


def test_is_github_project_with_github_dir(tmp_path: Path) -> None:
    """_is_github_project returns True if .github directory exists."""
    (tmp_path / ".github").mkdir()
    assert _is_github_project(tmp_path) is True


@patch("guardrails.init.subprocess.run")
def test_is_github_project_from_git_remote(mock_run: MagicMock, tmp_path: Path) -> None:
    """_is_github_project returns True if git remote contains github.com."""
    mock_run.return_value = MagicMock(stdout="origin\tgit@github.com:user/repo.git (fetch)\n")
    assert _is_github_project(tmp_path) is True


@patch("guardrails.init.subprocess.run")
def test_is_github_project_no_github_remote(mock_run: MagicMock, tmp_path: Path) -> None:
    """_is_github_project returns False if remote is not github."""
    mock_run.return_value = MagicMock(stdout="origin\tgit@gitlab.com:user/repo.git (fetch)\n")
    assert _is_github_project(tmp_path) is False


@patch("guardrails.init.subprocess.run", side_effect=FileNotFoundError)
def test_is_github_project_git_not_found(mock_run: MagicMock, tmp_path: Path) -> None:
    """_is_github_project returns False when git is not installed."""
    assert _is_github_project(tmp_path) is False


# ---------------------------------------------------------------------------
# _detect_python_deps
# ---------------------------------------------------------------------------


def test_detect_python_deps_uv(tmp_path: Path) -> None:
    """_detect_python_deps returns 'uv' when uv.lock exists."""
    (tmp_path / "uv.lock").write_text("")
    assert _detect_python_deps(tmp_path) == "uv"


def test_detect_python_deps_pip_requirements(tmp_path: Path) -> None:
    """_detect_python_deps returns 'pip' when requirements.txt exists."""
    (tmp_path / "requirements.txt").write_text("")
    assert _detect_python_deps(tmp_path) == "pip"


def test_detect_python_deps_pip_pyproject(tmp_path: Path) -> None:
    """_detect_python_deps returns 'pip' when only pyproject.toml exists."""
    (tmp_path / "pyproject.toml").write_text("")
    assert _detect_python_deps(tmp_path) == "pip"


def test_detect_python_deps_none(tmp_path: Path) -> None:
    """_detect_python_deps returns 'none' when no dependency files exist."""
    assert _detect_python_deps(tmp_path) == "none"


# ---------------------------------------------------------------------------
# _has_python
# ---------------------------------------------------------------------------


def test_has_python_true() -> None:
    """_has_python returns True when 'python' is in the list."""
    assert _has_python(["python", "rust"]) is True


def test_has_python_false() -> None:
    """_has_python returns False when 'python' is not in the list."""
    assert _has_python(["rust", "node"]) is False


# ---------------------------------------------------------------------------
# _configure_pip_audit
# ---------------------------------------------------------------------------


def test_configure_pip_audit_uv_success(tmp_path: Path) -> None:
    """_configure_pip_audit appends pip-audit block for uv mode."""
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos:\n")
    with patch("guardrails.init.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        _configure_pip_audit("uv", tmp_path)
    content = cfg.read_text()
    assert "pip-audit" in content
    assert "requirements-audit.txt" in content


def test_configure_pip_audit_uv_export_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_configure_pip_audit warns and returns when uv export fails."""
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos:\n")
    with patch("guardrails.init.subprocess.run", side_effect=FileNotFoundError):
        _configure_pip_audit("uv", tmp_path)
    content = cfg.read_text()
    assert "pip-audit" not in content
    assert "disabled" in capsys.readouterr().out


def test_configure_pip_audit_uv_called_process_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_configure_pip_audit warns when uv export raises CalledProcessError."""
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos:\n")
    with patch(
        "guardrails.init.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "uv"),
    ):
        _configure_pip_audit("uv", tmp_path)
    assert "pip-audit" not in cfg.read_text()


def test_configure_pip_audit_pip_with_requirements(tmp_path: Path) -> None:
    """_configure_pip_audit uses -r requirements.txt when it exists."""
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos:\n")
    (tmp_path / "requirements.txt").write_text("flask\n")
    _configure_pip_audit("pip", tmp_path)
    content = cfg.read_text()
    assert "pip-audit" in content
    assert "-r requirements.txt" in content


def test_configure_pip_audit_pip_without_requirements(tmp_path: Path) -> None:
    """_configure_pip_audit uses '.' when no requirements.txt."""
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos:\n")
    _configure_pip_audit("pip", tmp_path)
    content = cfg.read_text()
    assert "pip-audit" in content


def test_configure_pip_audit_none_mode(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_configure_pip_audit prints warning and returns for 'none' mode."""
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("repos:\n")
    _configure_pip_audit("none", tmp_path)
    assert cfg.read_text() == "repos:\n"
    assert "disabled" in capsys.readouterr().out


def test_configure_pip_audit_no_config_file(tmp_path: Path) -> None:
    """_configure_pip_audit returns early when config file does not exist."""
    _configure_pip_audit("pip", tmp_path)
    # No exception, no file created


# ---------------------------------------------------------------------------
# _install_pretooluse_hook
# ---------------------------------------------------------------------------


def test_install_pretooluse_hook_creates_settings(tmp_path: Path) -> None:
    """_install_pretooluse_hook creates settings.json when it does not exist."""
    settings = tmp_path / ".claude" / "settings.json"
    with patch("guardrails.init.Path.home", return_value=tmp_path):
        _install_pretooluse_hook(
            hook_cmd="test-hook.sh",
            matcher="Bash",
            check_substring="test-hook",
            label="Test hook",
        )
    assert settings.exists()
    data = json.loads(settings.read_text())
    assert len(data["hooks"]["PreToolUse"]) == 1
    assert data["hooks"]["PreToolUse"][0]["matcher"] == "Bash"


def test_install_pretooluse_hook_skips_duplicate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_pretooluse_hook skips if hook is already installed."""
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    existing = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "test-hook.sh"}],
                }
            ]
        }
    }
    settings.write_text(json.dumps(existing))
    with patch("guardrails.init.Path.home", return_value=tmp_path):
        _install_pretooluse_hook(
            hook_cmd="new-test-hook.sh",
            matcher="Bash",
            check_substring="test-hook",
            label="Test hook",
        )
    assert "already installed" in capsys.readouterr().out


def test_install_pretooluse_hook_backs_up_existing(tmp_path: Path) -> None:
    """_install_pretooluse_hook creates .bak of existing settings.json."""
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}")
    with patch("guardrails.init.Path.home", return_value=tmp_path):
        _install_pretooluse_hook(
            hook_cmd="test-hook.sh",
            matcher="Bash",
            check_substring="test-hook",
            label="Test hook",
        )
    assert (tmp_path / ".claude" / "settings.json.bak").exists()


def test_install_pretooluse_hook_handles_corrupt_json(tmp_path: Path) -> None:
    """_install_pretooluse_hook handles corrupt settings.json gracefully."""
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("not json{{{")
    with patch("guardrails.init.Path.home", return_value=tmp_path):
        _install_pretooluse_hook(
            hook_cmd="test-hook.sh",
            matcher="Bash",
            check_substring="test-hook",
            label="Test hook",
        )
    data = json.loads(settings.read_text())
    assert "hooks" in data


# ---------------------------------------------------------------------------
# _install_claude_hook / _install_dangerous_cmd_hook
# ---------------------------------------------------------------------------


def test_install_claude_hook_delegates() -> None:
    """_install_claude_hook calls _install_pretooluse_hook with correct args."""
    with patch("guardrails.init._install_pretooluse_hook") as mock:
        from guardrails.init import _install_claude_hook

        _install_claude_hook()
        mock.assert_called_once()


def test_install_dangerous_cmd_hook_delegates() -> None:
    """_install_dangerous_cmd_hook calls _install_pretooluse_hook."""
    with patch("guardrails.init._install_pretooluse_hook") as mock:
        _install_dangerous_cmd_hook()
        mock.assert_called_once()


# ---------------------------------------------------------------------------
# _install_precommit_hooks
# ---------------------------------------------------------------------------


def test_install_precommit_hooks_no_git_dir(tmp_path: Path) -> None:
    """_install_precommit_hooks returns early if no .git directory."""
    _install_precommit_hooks(tmp_path)
    # No exception, just returns


@patch("guardrails.init.shutil.which", return_value=None)
def test_install_precommit_hooks_no_precommit(
    mock_which: MagicMock,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_precommit_hooks prints install instructions when pre-commit missing."""
    _install_precommit_hooks(project)
    out = capsys.readouterr().out
    assert "uv tool install pre-commit" in out


@patch("guardrails.init.shutil.which", return_value="/usr/bin/pre-commit")
@patch("guardrails.init.subprocess.run")
def test_install_precommit_hooks_fixes_empty_hookspath(
    mock_run: MagicMock,
    mock_which: MagicMock,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_precommit_hooks unsets empty core.hooksPath."""
    git_config_result = MagicMock(returncode=0, stdout="")
    mock_run.return_value = git_config_result
    (project / ".git" / "hooks").mkdir(parents=True)
    (project / ".git" / "hooks" / "pre-commit").touch()

    _install_precommit_hooks(project)

    calls = mock_run.call_args_list
    unset_calls = [c for c in calls if "--unset" in str(c)]
    assert len(unset_calls) >= 1
    assert "Fixed empty" in capsys.readouterr().out


@patch("guardrails.init.shutil.which", return_value="/usr/bin/pre-commit")
@patch("guardrails.init.subprocess.run")
def test_install_precommit_hooks_git_not_found_during_hookspath(
    mock_run: MagicMock,
    mock_which: MagicMock,
    project: Path,
) -> None:
    """_install_precommit_hooks handles git not found during hooksPath check."""
    mock_run.side_effect = FileNotFoundError
    _install_precommit_hooks(project)
    # Should not raise


@patch("guardrails.init.shutil.which", return_value="/usr/bin/pre-commit")
@patch("guardrails.init.subprocess.run")
def test_install_precommit_hooks_verify_fails(
    mock_run: MagicMock,
    mock_which: MagicMock,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_precommit_hooks warns when pre-commit hook file not found."""
    mock_run.return_value = MagicMock(returncode=1, stdout="")
    _install_precommit_hooks(project)
    out = capsys.readouterr().out
    assert "not found" in out or "Warning" in out


@patch("guardrails.init.shutil.which", return_value="/usr/bin/pre-commit")
@patch("guardrails.init.subprocess.run")
def test_install_precommit_hooks_success(
    mock_run: MagicMock,
    mock_which: MagicMock,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_precommit_hooks installs hooks and verifies."""
    mock_run.return_value = MagicMock(returncode=1, stdout="")
    (project / ".git" / "hooks").mkdir(parents=True)
    (project / ".git" / "hooks" / "pre-commit").touch()
    _install_precommit_hooks(project)
    out = capsys.readouterr().out
    assert "Hooks verified" in out


# ---------------------------------------------------------------------------
# _add_to_gitignore
# ---------------------------------------------------------------------------


def test_add_to_gitignore_no_git(tmp_path: Path) -> None:
    """_add_to_gitignore does nothing without .git directory."""
    _add_to_gitignore(tmp_path)
    assert not (tmp_path / ".gitignore").exists()


def test_add_to_gitignore_creates_entry(project: Path) -> None:
    """_add_to_gitignore adds .ai-guardrails/ to .gitignore."""
    _add_to_gitignore(project)
    content = (project / ".gitignore").read_text()
    assert ".ai-guardrails/" in content


def test_add_to_gitignore_skips_if_present(project: Path) -> None:
    """_add_to_gitignore does not duplicate .ai-guardrails/ entry."""
    (project / ".gitignore").write_text(".ai-guardrails/\n")
    _add_to_gitignore(project)
    content = (project / ".gitignore").read_text()
    assert content.count(".ai-guardrails/") == 1


def test_add_to_gitignore_appends_newline_if_missing(project: Path) -> None:
    """_add_to_gitignore prepends newline if file doesn't end with one."""
    (project / ".gitignore").write_text("node_modules/")
    _add_to_gitignore(project)
    content = (project / ".gitignore").read_text()
    assert content.startswith("node_modules/\n")
    assert ".ai-guardrails/" in content


# ---------------------------------------------------------------------------
# _scaffold_registry
# ---------------------------------------------------------------------------


def test_scaffold_registry_copies_template(templates: Path, project: Path) -> None:
    """_scaffold_registry copies the registry template."""
    _scaffold_registry(templates, project, force=False)
    assert (project / ".guardrails-exceptions.toml").exists()


def test_scaffold_registry_skips_existing_without_force(
    templates: Path,
    project: Path,
) -> None:
    """_scaffold_registry skips when registry exists and force is False."""
    (project / ".guardrails-exceptions.toml").write_text("custom")
    _scaffold_registry(templates, project, force=False)
    assert (project / ".guardrails-exceptions.toml").read_text() == "custom"


def test_scaffold_registry_no_template(project: Path, tmp_path: Path) -> None:
    """_scaffold_registry returns when template does not exist."""
    empty_templates = tmp_path / "empty_templates"
    empty_templates.mkdir()
    _scaffold_registry(empty_templates, project, force=False)
    assert not (project / ".guardrails-exceptions.toml").exists()


# ---------------------------------------------------------------------------
# _generate_from_registry
# ---------------------------------------------------------------------------


def test_generate_from_registry_no_registry(project: Path) -> None:
    """_generate_from_registry returns when no registry exists."""
    _generate_from_registry(project)
    # Should not raise


def test_generate_from_registry_success(
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_generate_from_registry prints success when generation works."""
    (project / ".guardrails-exceptions.toml").write_text("# registry")
    mock_gen_module = MagicMock()
    mock_gen_module.run_generate_configs.return_value = True
    with patch.dict("sys.modules", {"guardrails.generate": mock_gen_module}):
        _generate_from_registry(project)
    out = capsys.readouterr().out
    assert "Generated" in out or "registry" in out.lower()


def test_generate_from_registry_failure(
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_generate_from_registry prints warning on generation failure."""
    (project / ".guardrails-exceptions.toml").write_text("# registry")
    mock_gen_module = MagicMock()
    mock_gen_module.run_generate_configs.return_value = False
    with patch.dict("sys.modules", {"guardrails.generate": mock_gen_module}):
        _generate_from_registry(project)
    out = capsys.readouterr().out
    assert "failed" in out.lower() or "generation" in out.lower()


# ---------------------------------------------------------------------------
# _install_ci_workflow
# ---------------------------------------------------------------------------


def test_install_ci_workflow_copies(templates: Path, project: Path) -> None:
    """_install_ci_workflow creates check.yml in .github/workflows/."""
    _install_ci_workflow(templates, project, force=True)
    assert (project / ".github" / "workflows" / "check.yml").exists()


def test_install_ci_workflow_no_template(
    project: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_ci_workflow warns when template is missing."""
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "workflows").mkdir()
    _install_ci_workflow(empty, project, force=True)
    assert "not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _install_claude_review
# ---------------------------------------------------------------------------


def test_install_claude_review_copies(templates: Path, project: Path) -> None:
    """_install_claude_review creates claude-review.yml."""
    _install_claude_review(templates, project, force=True)
    assert (project / ".github" / "workflows" / "claude-review.yml").exists()


def test_install_claude_review_no_template(
    project: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_claude_review warns when template is missing."""
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "workflows").mkdir()
    _install_claude_review(empty, project, force=True)
    assert "not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _install_coderabbit
# ---------------------------------------------------------------------------


def test_install_coderabbit_copies(templates: Path, project: Path) -> None:
    """_install_coderabbit creates .coderabbit.yaml."""
    _install_coderabbit(templates, project, force=True)
    assert (project / ".coderabbit.yaml").exists()


def test_install_coderabbit_no_template(
    project: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_coderabbit warns when template is missing."""
    empty = tmp_path / "empty"
    empty.mkdir()
    _install_coderabbit(empty, project, force=True)
    assert "not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _install_gemini
# ---------------------------------------------------------------------------


def test_install_gemini_copies(templates: Path, project: Path) -> None:
    """_install_gemini creates .gemini/ directory with config files."""
    _install_gemini(templates, project, force=True)
    assert (project / ".gemini" / "settings.yaml").exists()


def test_install_gemini_no_template(
    project: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_gemini warns when .gemini template dir is missing."""
    empty = tmp_path / "empty"
    empty.mkdir()
    _install_gemini(empty, project, force=True)
    assert "not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _install_deepsource
# ---------------------------------------------------------------------------


def test_install_deepsource_copies(templates: Path, project: Path) -> None:
    """_install_deepsource creates .deepsource.toml."""
    _install_deepsource(templates, project, force=True)
    assert (project / ".deepsource.toml").exists()


def test_install_deepsource_no_template(
    project: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_install_deepsource warns when template is missing."""
    empty = tmp_path / "empty"
    empty.mkdir()
    _install_deepsource(empty, project, force=True)
    assert "not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _setup_agent_instructions
# ---------------------------------------------------------------------------


def test_setup_agent_instructions_creates_claude_md(
    templates: Path,
    project: Path,
) -> None:
    """_setup_agent_instructions creates CLAUDE.md when neither it nor AGENTS.md exist."""
    _setup_agent_instructions(templates, project)
    assert (project / "CLAUDE.md").exists()
    content = (project / "CLAUDE.md").read_text()
    assert "AI Guardrails - Code Standards" in content


def test_setup_agent_instructions_appends_to_existing_claude_md(
    templates: Path,
    project: Path,
) -> None:
    """_setup_agent_instructions appends to existing CLAUDE.md."""
    (project / "CLAUDE.md").write_text("# My Project\n")
    _setup_agent_instructions(templates, project)
    content = (project / "CLAUDE.md").read_text()
    assert "# My Project" in content
    assert "AI Guardrails - Code Standards" in content


def test_setup_agent_instructions_appends_to_agents_md(
    templates: Path,
    project: Path,
) -> None:
    """_setup_agent_instructions appends to existing AGENTS.md."""
    (project / "AGENTS.md").write_text("# Agents\n")
    _setup_agent_instructions(templates, project)
    content = (project / "AGENTS.md").read_text()
    assert "AI Guardrails - Code Standards" in content


def test_setup_agent_instructions_skips_if_marker_present(
    templates: Path,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_setup_agent_instructions skips if guardrails section already exists."""
    (project / "CLAUDE.md").write_text("## AI Guardrails - Code Standards\nExisting.\n")
    _setup_agent_instructions(templates, project)
    assert "already has" in capsys.readouterr().out


def test_setup_agent_instructions_no_template(project: Path, tmp_path: Path) -> None:
    """_setup_agent_instructions returns when template does not exist."""
    empty = tmp_path / "empty"
    empty.mkdir()
    _setup_agent_instructions(empty, project)
    assert not (project / "CLAUDE.md").exists()


def test_setup_agent_instructions_appends_newline_to_existing_without_trailing(
    templates: Path,
    project: Path,
) -> None:
    """_setup_agent_instructions handles files not ending with newline."""
    (project / "CLAUDE.md").write_text("# Project")  # No trailing newline
    _setup_agent_instructions(templates, project)
    content = (project / "CLAUDE.md").read_text()
    assert "# Project\n" in content
    assert "AI Guardrails" in content


# ---------------------------------------------------------------------------
# _resolve_languages
# ---------------------------------------------------------------------------


def test_resolve_languages_all(configs: Path, project: Path) -> None:
    """_resolve_languages returns all languages for 'all' type."""
    result = _resolve_languages("all", configs, project)
    assert "python" in result
    assert "rust" in result
    assert "dotnet" in result


def test_resolve_languages_specific(
    configs: Path,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_resolve_languages returns single language for specific type."""
    result = _resolve_languages("python", configs, project)
    assert result == ["python"]
    assert "python" in capsys.readouterr().out


def test_resolve_languages_autodetect_multiple(
    configs: Path,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_resolve_languages auto-detects multiple languages."""
    mock_assemble = MagicMock()
    mock_assemble.detect_languages.return_value = ["python", "rust"]
    mock_assemble.load_registry.return_value = {}
    (configs / "languages.yaml").write_text("languages:\n")
    with patch.dict("sys.modules", {"guardrails.assemble": mock_assemble}):
        result = _resolve_languages("", configs, project)
    assert result == ["python", "rust"]
    out = capsys.readouterr().out
    assert "multiple" in out.lower()


def test_resolve_languages_autodetect_fails(
    configs: Path,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_resolve_languages returns empty list when auto-detection fails."""
    mock_assemble = MagicMock()
    mock_assemble.detect_languages.side_effect = RuntimeError("broken")
    mock_assemble.load_registry.return_value = {}
    (configs / "languages.yaml").write_text("languages:\n")
    with patch.dict("sys.modules", {"guardrails.assemble": mock_assemble}):
        result = _resolve_languages("", configs, project)
    assert result == []
    out = capsys.readouterr().out
    assert "No language detected" in out


def test_resolve_languages_no_registry_file(
    configs: Path,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_resolve_languages handles missing languages.yaml gracefully."""
    result = _resolve_languages("", configs, project)
    assert result == []


# ---------------------------------------------------------------------------
# _dry_run_report
# ---------------------------------------------------------------------------


def test_dry_run_report_outputs_would_actions(
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_dry_run_report lists planned actions with 'would' prefix."""
    with patch("guardrails.init._is_github_project", return_value=False):
        _dry_run_report(
            project,
            languages=["python"],
            project_type="python",
            force=False,
            skip_precommit=False,
            pip_audit_mode="auto",
            install_ci="no",
            install_claude_review="no",
            install_coderabbit="no",
            install_gemini="no",
            install_deepsource="no",
        )
    out = capsys.readouterr().out
    assert "would" in out
    assert ".editorconfig" in out
    assert "ruff.toml" in out


def test_dry_run_report_all_type(
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_dry_run_report lists all language configs for 'all' type."""
    with patch("guardrails.init._is_github_project", return_value=False):
        _dry_run_report(
            project,
            languages=list({"python": [], "rust": [], "dotnet": []}.keys()),
            project_type="all",
            force=True,
            skip_precommit=True,
            pip_audit_mode="auto",
            install_ci="no",
            install_claude_review="no",
            install_coderabbit="no",
            install_gemini="no",
            install_deepsource="no",
        )
    out = capsys.readouterr().out
    assert "would" in out
    assert "force overwrite" in out


def test_dry_run_report_github_integrations(
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_dry_run_report shows GitHub integrations when auto+github."""
    with patch("guardrails.init._is_github_project", return_value=True):
        _dry_run_report(
            project,
            languages=[],
            project_type="",
            force=False,
            skip_precommit=False,
            pip_audit_mode="auto",
            install_ci="auto",
            install_claude_review="auto",
            install_coderabbit="auto",
            install_gemini="auto",
            install_deepsource="auto",
        )
    out = capsys.readouterr().out
    assert "CI workflow" in out
    assert "CodeRabbit" in out


def test_dry_run_report_skip_precommit(
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_dry_run_report omits pre-commit section when skip_precommit is True."""
    with patch("guardrails.init._is_github_project", return_value=False):
        _dry_run_report(
            project,
            languages=[],
            project_type="",
            force=False,
            skip_precommit=True,
            pip_audit_mode="auto",
            install_ci="no",
            install_claude_review="no",
            install_coderabbit="no",
            install_gemini="no",
            install_deepsource="no",
        )
    out = capsys.readouterr().out
    assert "pre-commit install" not in out


# ---------------------------------------------------------------------------
# run_init -- error paths
# ---------------------------------------------------------------------------


def test_run_init_returns_1_when_configs_dir_not_found() -> None:
    """run_init returns 1 when find_configs_dir raises FileNotFoundError."""
    with patch(
        "guardrails.init.find_configs_dir",
        side_effect=FileNotFoundError("no configs"),
    ):
        rc = run_init()
    assert rc == 1


def test_run_init_returns_1_when_templates_dir_not_found() -> None:
    """run_init returns 1 when find_templates_dir raises FileNotFoundError."""
    with (
        patch("guardrails.init.find_configs_dir", return_value=Path("/fake/configs")),
        patch(
            "guardrails.init.find_templates_dir",
            side_effect=FileNotFoundError("no templates"),
        ),
    ):
        rc = run_init()
    assert rc == 1


def test_run_init_returns_1_when_lib_dir_not_found() -> None:
    """run_init returns 1 when find_lib_dir raises FileNotFoundError."""
    with (
        patch("guardrails.init.find_configs_dir", return_value=Path("/fake/configs")),
        patch("guardrails.init.find_templates_dir", return_value=Path("/fake/templates")),
        patch(
            "guardrails.init.find_lib_dir",
            side_effect=FileNotFoundError("no lib"),
        ),
    ):
        rc = run_init()
    assert rc == 1


_HOOK_PATCHES = (
    "guardrails.init._install_precommit_hooks",
    "guardrails.init._install_claude_hook",
    "guardrails.init._install_dangerous_cmd_hook",
)


@pytest.fixture
def _mock_hooks() -> Iterator[None]:
    """Patch out hook installation side effects."""
    with patch(_HOOK_PATCHES[0]), patch(_HOOK_PATCHES[1]), patch(_HOOK_PATCHES[2]):
        yield


@pytest.mark.usefixtures("_mock_hooks")
def test_run_init_all_type(
    configs: Path,
    templates: Path,
    project: Path,
) -> None:
    """run_init with project_type='all' copies all language configs."""
    lib = configs.parent / "lib"
    lib.mkdir()
    (lib / "hooks").mkdir()
    with (
        chdir(project),
        patch("guardrails.init.find_configs_dir", return_value=configs),
        patch("guardrails.init.find_templates_dir", return_value=templates),
        patch("guardrails.init.find_lib_dir", return_value=lib),
        patch("guardrails.init._is_github_project", return_value=False),
    ):
        rc = run_init(project_type="all", force=True)
    assert rc == 0
    assert (project / "ruff.toml").exists()
    assert (project / "rustfmt.toml").exists()
    assert (project / ".clang-format").exists()
    assert (project / "stylua.toml").exists()
    assert (project / "biome.json").exists()


@pytest.mark.usefixtures("_mock_hooks")
def test_run_init_skip_precommit(
    configs: Path,
    templates: Path,
    project: Path,
) -> None:
    """run_init with skip_precommit=True skips pre-commit setup."""
    lib = configs.parent / "lib"
    lib.mkdir()
    with (
        chdir(project),
        patch("guardrails.init.find_configs_dir", return_value=configs),
        patch("guardrails.init.find_templates_dir", return_value=templates),
        patch("guardrails.init.find_lib_dir", return_value=lib),
        patch("guardrails.init._is_github_project", return_value=False),
        patch("guardrails.init._setup_precommit") as mock_precommit,
    ):
        rc = run_init(project_type="python", force=True, skip_precommit=True)
    assert rc == 0
    mock_precommit.assert_not_called()


@pytest.mark.usefixtures("_mock_hooks")
def test_run_init_ci_yes(
    configs: Path,
    templates: Path,
    project: Path,
) -> None:
    """run_init with install_ci='yes' installs CI workflow."""
    lib = configs.parent / "lib"
    lib.mkdir()
    (lib / "hooks").mkdir()
    with (
        chdir(project),
        patch("guardrails.init.find_configs_dir", return_value=configs),
        patch("guardrails.init.find_templates_dir", return_value=templates),
        patch("guardrails.init.find_lib_dir", return_value=lib),
        patch("guardrails.init._is_github_project", return_value=False),
    ):
        rc = run_init(
            project_type="python",
            force=True,
            install_ci="yes",
            install_claude_review="no",
            install_coderabbit="no",
            install_gemini="no",
            install_deepsource="no",
        )
    assert rc == 0
    assert (project / ".github" / "workflows" / "check.yml").exists()


@pytest.mark.usefixtures("_mock_hooks")
def test_run_init_force_regenerates_registry(
    configs: Path,
    templates: Path,
    project: Path,
) -> None:
    """run_init with force=True calls _generate_from_registry."""
    lib = configs.parent / "lib"
    lib.mkdir()
    (lib / "hooks").mkdir()
    with (
        chdir(project),
        patch("guardrails.init.find_configs_dir", return_value=configs),
        patch("guardrails.init.find_templates_dir", return_value=templates),
        patch("guardrails.init.find_lib_dir", return_value=lib),
        patch("guardrails.init._is_github_project", return_value=False),
        patch("guardrails.init._generate_from_registry") as mock_gen,
    ):
        rc = run_init(project_type="python", force=True)
    assert rc == 0
    mock_gen.assert_called_once()


@pytest.mark.usefixtures("_mock_hooks")
def test_run_init_dry_run(
    configs: Path,
    templates: Path,
    project: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_init with dry_run=True reports actions without changes."""
    with (
        chdir(project),
        patch("guardrails.init.find_configs_dir", return_value=configs),
        patch("guardrails.init.find_templates_dir", return_value=templates),
        patch("guardrails.init.find_lib_dir", return_value=configs.parent / "lib"),
        patch("guardrails.init._is_github_project", return_value=False),
    ):
        rc = run_init(project_type="python", dry_run=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "would" in out
    assert not (project / "ruff.toml").exists()
