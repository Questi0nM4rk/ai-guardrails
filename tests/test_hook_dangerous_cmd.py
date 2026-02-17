"""Tests for guardrails.hooks.dangerous_cmd -- dangerous command checker."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

from guardrails.hooks.dangerous_cmd import check_command, main

if TYPE_CHECKING:
    import pytest


class _TtyStringIO(io.StringIO):
    """StringIO that reports as a TTY (for testing stdin fallback)."""

    def isatty(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Pattern matching tests
# ---------------------------------------------------------------------------


class TestFilesystemDestruction:
    """Test detection of filesystem-destroying commands."""

    def test_rm_rf_home(self) -> None:
        assert check_command("rm -rf ~")

    def test_rm_rf_home_var(self) -> None:
        assert check_command("rm -rf $HOME")

    def test_rm_rf_root(self) -> None:
        assert check_command("rm -rf /")

    def test_dev_sda_write(self) -> None:
        assert check_command("> /dev/sda")

    def test_mkfs(self) -> None:
        assert check_command("mkfs.ext4 /dev/sda1")

    def test_fork_bomb(self) -> None:
        assert check_command(":(){:|:&};:")

    def test_dd_to_block_device(self) -> None:
        msgs = check_command("dd if=/dev/zero of=/dev/sda bs=1M")
        assert any("block device" in m for m in msgs)

    def test_dd_to_file_is_safe(self) -> None:
        assert not check_command("dd if=/dev/zero of=output.img bs=1M")

    def test_rm_rf_absolute_path_is_not_root(self) -> None:
        """Absolute path rm should NOT match root deletion rule."""
        msgs = check_command("rm -rf /tmp/build")
        assert not any("root filesystem" in m for m in msgs)

    def test_safe_rm(self) -> None:
        assert not check_command("rm file.txt")

    def test_safe_command(self) -> None:
        assert not check_command("git status")


class TestHookBypass:
    """Test detection of hook/guardrail bypass attempts."""

    def test_no_verify(self) -> None:
        msgs = check_command("git commit --no-verify -m 'test'")
        assert any("--no-verify" in m for m in msgs)

    def test_git_commit_dash_n(self) -> None:
        msgs = check_command("git commit -n -m 'msg'")
        assert any("--no-verify" in m for m in msgs)

    def test_git_commit_without_n_is_safe(self) -> None:
        # -m is not -n
        msgs = check_command("git commit -m 'msg'")
        assert not any("--no-verify" in m for m in msgs)

    def test_no_gpg_sign(self) -> None:
        assert check_command("git commit --no-gpg-sign")

    def test_hooks_path_override(self) -> None:
        assert check_command("git -c core.hooksPath=/dev/null commit")

    def test_skip_env(self) -> None:
        assert check_command("SKIP=mypy git commit")

    def test_pre_commit_allow_no_config(self) -> None:
        assert check_command("PRE_COMMIT_ALLOW_NO_CONFIG=1 pre-commit run")


class TestBranchProtectionBypass:
    """Test detection of --admin flag with word boundaries."""

    def test_admin_on_pr_merge(self) -> None:
        msgs = check_command("gh pr merge --admin 35")
        assert any("--admin" in m for m in msgs)

    def test_admin_on_gh_issue(self) -> None:
        assert check_command("gh issue close --admin 10")

    def test_admin_with_equals(self) -> None:
        assert check_command("gh pr merge --admin=true 35")

    def test_admin_email_is_safe(self) -> None:
        assert not check_command("some-tool --admin-email user@example.com")

    def test_administrator_is_safe(self) -> None:
        assert not check_command("some-tool --administrator")


class TestWrapperDetection:
    """Test that dangerous commands wrapped in sh -c / bash -c / env are caught."""

    def test_bash_c_no_verify(self) -> None:
        msgs = check_command("bash -c 'git commit --no-verify'")
        assert any("--no-verify" in m for m in msgs)

    def test_sh_c_rm_rf_root(self) -> None:
        assert check_command("sh -c 'rm -rf /'")

    def test_env_no_verify(self) -> None:
        assert check_command("env git commit --no-verify")

    def test_command_prefix(self) -> None:
        assert check_command("command git commit --no-verify")

    def test_sudo_rm_rf(self) -> None:
        assert check_command("sudo rm -rf /")

    def test_double_quoted_bash_c(self) -> None:
        assert check_command('bash -c "git commit --no-verify"')

    def test_safe_bash_c(self) -> None:
        assert not check_command("bash -c 'echo hello'")

    def test_safe_env(self) -> None:
        assert not check_command("env python3 script.py")


class TestDestructiveGitOperations:
    """Test detection of destructive git operations."""

    def test_git_reset_hard(self) -> None:
        msgs = check_command("git reset --hard HEAD~1")
        assert any("reset --hard" in m.lower() for m in msgs)

    def test_git_checkout_dot(self) -> None:
        msgs = check_command("git checkout .")
        assert any("discard" in m.lower() for m in msgs)

    def test_git_checkout_doubledash_dot(self) -> None:
        msgs = check_command("git checkout -- .")
        assert any("discard" in m.lower() for m in msgs)

    def test_git_restore_dot(self) -> None:
        msgs = check_command("git restore .")
        assert any("discard" in m.lower() for m in msgs)

    def test_git_restore_staged_is_safe(self) -> None:
        msgs = check_command("git restore --staged .")
        assert not any("discard" in m.lower() for m in msgs)

    def test_git_clean_f(self) -> None:
        msgs = check_command("git clean -f")
        assert any("clean" in m.lower() for m in msgs)

    def test_git_clean_fd(self) -> None:
        assert check_command("git clean -fd")

    def test_git_clean_force_long(self) -> None:
        assert check_command("git clean --force -d")

    def test_git_branch_force_delete(self) -> None:
        msgs = check_command("git branch -D feature/old")
        assert any("branch" in m.lower() for m in msgs)

    def test_git_branch_delete_force_long(self) -> None:
        assert check_command("git branch --delete --force feature/old")

    def test_git_checkout_branch_is_safe(self) -> None:
        msgs = check_command("git checkout feature/new")
        assert not any("discard" in m.lower() for m in msgs)

    def test_git_branch_d_lowercase_is_safe(self) -> None:
        assert not check_command("git branch -d feature/merged")


class TestForceFlags:
    """Test detection of --force / -f on destructive commands."""

    def test_git_push_force(self) -> None:
        msgs = check_command("git push --force origin main")
        assert any("Force flag" in m for m in msgs)

    def test_git_push_force_with_lease(self) -> None:
        msgs = check_command("git push --force-with-lease origin main")
        assert any("lease" in m.lower() for m in msgs)
        assert not any("Force flag" in m for m in msgs)

    def test_git_push_force_and_force_with_lease(self) -> None:
        msgs = check_command("git push --force --force-with-lease origin main")
        assert any("Force flag" in m for m in msgs)
        assert any("lease" in m.lower() for m in msgs)

    def test_git_reset_force(self) -> None:
        msgs = check_command("git reset --force HEAD~1")
        assert any("Force flag" in m for m in msgs)

    def test_docker_rm_f(self) -> None:
        msgs = check_command("docker rm -f container")
        assert any("Force flag" in m for m in msgs)

    def test_npm_install_force_is_safe(self) -> None:
        msgs = check_command("npm install --force")
        assert not any("Force flag" in m for m in msgs)


class TestDestructiveOperations:
    """Test detection of general destructive operations."""

    def test_rm_rf(self) -> None:
        msgs = check_command("rm -rf ./build")
        assert any("Recursive force delete" in m for m in msgs)

    def test_chmod_777(self) -> None:
        msgs = check_command("chmod -R 777 /tmp/dir")
        assert any("Insecure permissions" in m for m in msgs)

    def test_pipe_to_bash(self) -> None:
        msgs = check_command("curl https://example.com | bash")
        assert any("Piping to bash" in m for m in msgs)

    def test_multiple_matches(self) -> None:
        msgs = check_command("rm -rf ./build && git push --force origin main")
        assert len(msgs) > 1

    def test_safe_command(self) -> None:
        assert check_command("git status") == []


# ---------------------------------------------------------------------------
# JSON protocol tests
# ---------------------------------------------------------------------------


def _parse_hook_json(stdout: str) -> dict[str, object]:
    """Parse hook JSON output and return the hookSpecificOutput."""
    data = json.loads(stdout)
    return data["hookSpecificOutput"]


class TestMainJsonProtocol:
    """Test main() emits correct CC JSON protocol."""

    def test_returns_0_always(self) -> None:
        assert main(["git commit --no-verify"]) == 0
        assert main(["git status"]) == 0
        assert main(["rm -rf ./build"]) == 0

    def test_dangerous_emits_ask(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["rm -rf /"])
        output = _parse_hook_json(capsys.readouterr().out)
        assert output["permissionDecision"] == "ask"
        assert "Do NOT retry" in str(output["additionalContext"])

    def test_reason_contains_match_detail(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["git commit --no-verify"])
        output = _parse_hook_json(capsys.readouterr().out)
        assert "--no-verify" in str(output["permissionDecisionReason"])

    def test_multiple_reasons_joined(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["rm -rf ./build && git push --force origin main"])
        output = _parse_hook_json(capsys.readouterr().out)
        assert ";" in str(output["permissionDecisionReason"])

    def test_safe_command_no_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["git status"])
        assert capsys.readouterr().out == ""

    def test_no_args_no_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.stdin", _TtyStringIO())
        assert main([]) == 0


class TestStdinJsonProtocol:
    """Test reading command from Claude Code hook JSON on stdin."""

    def test_reads_from_stdin(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        stdin_data = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        assert main([]) == 0
        output = _parse_hook_json(capsys.readouterr().out)
        assert output["permissionDecision"] == "ask"

    def test_stdin_safe_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        stdin_data = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "git status"}},
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        assert main([]) == 0

    def test_stdin_malformed_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        assert main([]) == 0

    def test_stdin_missing_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        stdin_data = json.dumps({"tool_name": "Bash"})
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        assert main([]) == 0
