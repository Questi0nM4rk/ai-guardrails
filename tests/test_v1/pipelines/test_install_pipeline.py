"""Tests for InstallPipeline — checks prerequisites, installs global config."""

from __future__ import annotations

import json
from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.install_pipeline import InstallOptions, InstallPipeline
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_DANGEROUS_CMD = "python -m ai_guardrails.hooks.dangerous_cmd"
_PROTECT_CONFIGS_CMD = "python -m ai_guardrails.hooks.protect_configs"


def _make_pipeline(
    global_config_dir: Path | None = None,
    claude_settings_path: Path | None = None,
) -> InstallPipeline:
    return InstallPipeline(
        options=InstallOptions(),
        global_config_dir=global_config_dir or Path("/home/test/.ai-guardrails"),
        claude_settings_path=claude_settings_path
        or Path("/home/test/.claude/settings.json"),
    )


def _run_pipeline(
    tmp_path: Path,
    *,
    claude_settings_path: Path | None = None,
    existing_settings: dict | None = None,
) -> tuple[InstallPipeline, FakeFileManager, list]:
    fm = FakeFileManager()
    runner = FakeCommandRunner()
    runner.register(["git", "--version"], returncode=0, stdout="git version 2.40.0")
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.11.0")

    settings_path = claude_settings_path or (tmp_path / ".claude" / "settings.json")
    if existing_settings is not None:
        fm.seed(settings_path, json.dumps(existing_settings))

    pipeline = _make_pipeline(
        global_config_dir=tmp_path / "config",
        claude_settings_path=settings_path,
    )
    results = pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    return pipeline, fm, results


def test_install_options_defaults() -> None:
    opts = InstallOptions()
    assert opts.upgrade is False


def test_install_pipeline_can_be_constructed() -> None:
    pipeline = _make_pipeline()
    assert pipeline is not None


def test_install_pipeline_checks_git(tmp_path: Path) -> None:
    fm = FakeFileManager()
    runner = FakeCommandRunner()
    runner.register(["git", "--version"], returncode=0, stdout="git version 2.40.0")

    pipeline = _make_pipeline(global_config_dir=tmp_path / "config")
    results = pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    assert isinstance(results, list)
    called_cmds = [tuple(c) for c in runner.calls]
    assert ("git", "--version") in called_cmds


def test_install_pipeline_checks_lefthook(tmp_path: Path) -> None:
    fm = FakeFileManager()
    runner = FakeCommandRunner()
    runner.register(["git", "--version"], returncode=0, stdout="git version 2.40.0")
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.11.0")

    pipeline = _make_pipeline(global_config_dir=tmp_path / "config")
    pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    called_cmds = [tuple(c) for c in runner.calls]
    assert ("lefthook", "version") in called_cmds


def test_install_pipeline_creates_global_config(tmp_path: Path) -> None:
    _, fm, _ = _run_pipeline(tmp_path)
    written_paths = {p for p, _ in fm.written}
    assert any("config.toml" in str(p) for p in written_paths)


def test_install_pipeline_errors_on_missing_required_tool(tmp_path: Path) -> None:
    fm = FakeFileManager()
    runner = FakeCommandRunner()
    runner.register(["git", "--version"], returncode=1, stderr="not found")

    pipeline = _make_pipeline(global_config_dir=tmp_path / "config")
    results = pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    assert any(r.status == "error" for r in results)
    assert any("git" in r.message for r in results)


# ---------------------------------------------------------------------------
# Task 3: global ~/.claude/settings.json tests
# ---------------------------------------------------------------------------


def test_install_creates_global_claude_hooks_when_settings_missing(
    tmp_path: Path,
) -> None:
    """When settings.json is missing, install creates it with both hooks."""
    _, fm, results = _run_pipeline(tmp_path)
    assert all(r.status in ("ok", "skip") for r in results)

    settings_path = tmp_path / ".claude" / "settings.json"
    written = dict(fm.written)
    assert settings_path in written

    data = json.loads(written[settings_path])
    bash_hooks = data["hooks"]["PreToolUse"][0]["hooks"]
    cmds = [h["command"] for h in bash_hooks]
    assert _DANGEROUS_CMD in cmds
    assert _PROTECT_CONFIGS_CMD in cmds


def test_install_merges_into_existing_claude_settings(tmp_path: Path) -> None:
    """When settings.json exists with other content, hooks are merged in."""
    existing = {"someOtherSetting": True, "hooks": {"PreToolUse": []}}
    _, fm, results = _run_pipeline(tmp_path, existing_settings=existing)
    assert all(r.status in ("ok", "skip") for r in results)

    settings_path = tmp_path / ".claude" / "settings.json"
    written = dict(fm.written)
    assert settings_path in written

    data = json.loads(written[settings_path])
    assert data["someOtherSetting"] is True
    bash_entry = next(
        e for e in data["hooks"]["PreToolUse"] if e.get("matcher") == "Bash"
    )
    cmds = [h["command"] for h in bash_entry["hooks"]]
    assert _DANGEROUS_CMD in cmds
    assert _PROTECT_CONFIGS_CMD in cmds


def test_install_is_idempotent_for_claude_settings(tmp_path: Path) -> None:
    """Running install twice does not duplicate hooks."""
    # Pre-populate with hooks already installed
    already_installed = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": _DANGEROUS_CMD},
                        {"type": "command", "command": _PROTECT_CONFIGS_CMD},
                    ],
                }
            ]
        }
    }
    _, fm, results = _run_pipeline(tmp_path, existing_settings=already_installed)

    # Step should skip (already installed)
    settings_path = tmp_path / ".claude" / "settings.json"
    written = dict(fm.written)
    # Either skipped (not written) or written with no duplication
    if settings_path in written:
        data = json.loads(written[settings_path])
        bash_entry = next(
            e for e in data["hooks"]["PreToolUse"] if e.get("matcher") == "Bash"
        )
        cmds = [h["command"] for h in bash_entry["hooks"]]
        assert cmds.count(_DANGEROUS_CMD) == 1
        assert cmds.count(_PROTECT_CONFIGS_CMD) == 1
    else:
        # Skipped — original not modified, check skip result
        assert any(r.status == "skip" for r in results)
