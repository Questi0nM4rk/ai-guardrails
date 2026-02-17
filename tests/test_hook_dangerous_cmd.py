"""Tests for guardrails.hooks.dangerous_cmd -- dangerous command checker."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

from guardrails.hooks.dangerous_cmd import _check_blocked, _check_warned, main

if TYPE_CHECKING:
    import pytest


class _TtyStringIO(io.StringIO):
    """StringIO that reports as a TTY (for testing stdin fallback)."""

    def isatty(self) -> bool:
        return True


class TestCheckBlocked:
    """Test blocked command detection."""

    def test_blocks_rm_rf_home(self) -> None:
        assert _check_blocked("rm -rf ~") is not None

    def test_blocks_rm_rf_home_var(self) -> None:
        assert _check_blocked("rm -rf $HOME") is not None

    def test_blocks_rm_rf_root(self) -> None:
        assert _check_blocked("rm -rf /") is not None

    def test_blocks_dev_sda_write(self) -> None:
        assert _check_blocked("> /dev/sda") is not None

    def test_blocks_mkfs(self) -> None:
        assert _check_blocked("mkfs.ext4 /dev/sda1") is not None

    def test_blocks_fork_bomb(self) -> None:
        assert _check_blocked(":(){:|:&};:") is not None

    def test_blocks_no_verify(self) -> None:
        msg = _check_blocked("git commit --no-verify -m 'test'")
        assert msg is not None
        assert "--no-verify" in msg

    def test_blocks_no_gpg_sign(self) -> None:
        assert _check_blocked("git commit --no-gpg-sign") is not None

    def test_blocks_hooks_path_override(self) -> None:
        assert _check_blocked("git -c core.hooksPath=/dev/null commit") is not None

    def test_blocks_skip_env(self) -> None:
        assert _check_blocked("SKIP=mypy git commit") is not None

    def test_blocks_pre_commit_allow_no_config(self) -> None:
        assert _check_blocked("PRE_COMMIT_ALLOW_NO_CONFIG=1 pre-commit run") is not None

    def test_blocks_admin_flag(self) -> None:
        """--admin bypasses branch protection — always blocked."""
        msg = _check_blocked("gh pr merge --admin 35")
        assert msg is not None
        assert "--admin" in msg

    def test_blocks_admin_on_gh_issue(self) -> None:
        assert _check_blocked("gh issue close --admin 10") is not None

    def test_blocks_admin_with_equals(self) -> None:
        """--admin=true should also be blocked."""
        assert _check_blocked("gh pr merge --admin=true 35") is not None

    def test_allows_admin_email_flag(self) -> None:
        """--admin-email is a different flag, should not be blocked."""
        assert _check_blocked("some-tool --admin-email user@example.com") is None

    def test_allows_administrator_flag(self) -> None:
        """--administrator is a different flag, should not be blocked."""
        assert _check_blocked("some-tool --administrator") is None

    def test_allows_safe_command(self) -> None:
        assert _check_blocked("git status") is None

    def test_allows_normal_rm(self) -> None:
        assert _check_blocked("rm file.txt") is None


class TestCheckBlockedSpecialPatterns:
    """Test _SPECIAL_BLOCKS regex patterns."""

    def test_blocks_git_commit_dash_n(self) -> None:
        msg = _check_blocked("git commit -n -m 'msg'")
        assert msg is not None
        assert "--no-verify" in msg

    def test_allows_git_commit_without_n(self) -> None:
        assert _check_blocked("git commit -m 'msg'") is None

    def test_blocks_dd_to_block_device(self) -> None:
        msg = _check_blocked("dd if=/dev/zero of=/dev/sda bs=1M")
        assert msg is not None
        assert "block device" in msg

    def test_allows_dd_to_file(self) -> None:
        assert _check_blocked("dd if=/dev/zero of=output.img bs=1M") is None


class TestWrapperDetection:
    """Test that dangerous commands wrapped in sh -c / bash -c / env are caught."""

    def test_blocks_bash_c_no_verify(self) -> None:
        msg = _check_blocked("bash -c 'git commit --no-verify'")
        assert msg is not None
        assert "--no-verify" in msg

    def test_blocks_sh_c_rm_rf_root(self) -> None:
        msg = _check_blocked("sh -c 'rm -rf /'")
        assert msg is not None

    def test_blocks_env_no_verify(self) -> None:
        msg = _check_blocked("env git commit --no-verify")
        assert msg is not None

    def test_blocks_command_prefix(self) -> None:
        msg = _check_blocked("command git commit --no-verify")
        assert msg is not None

    def test_blocks_sudo_rm_rf(self) -> None:
        msg = _check_blocked("sudo rm -rf /")
        assert msg is not None

    def test_blocks_double_quoted_bash_c(self) -> None:
        msg = _check_blocked('bash -c "git commit --no-verify"')
        assert msg is not None

    def test_allows_safe_bash_c(self) -> None:
        assert _check_blocked("bash -c 'echo hello'") is None

    def test_allows_env_safe_command(self) -> None:
        assert _check_blocked("env python3 script.py") is None


class TestDestructiveGitOperations:
    """Test warnings for destructive git operations."""

    def test_warns_git_reset_hard(self) -> None:
        warnings = _check_warned("git reset --hard HEAD~1")
        assert any("reset --hard" in w.lower() for w in warnings)

    def test_warns_git_checkout_dot(self) -> None:
        warnings = _check_warned("git checkout .")
        assert any("discard" in w.lower() for w in warnings)

    def test_warns_git_checkout_doubledash_dot(self) -> None:
        """Git checkout -- . syntax should also warn."""
        warnings = _check_warned("git checkout -- .")
        assert any("discard" in w.lower() for w in warnings)

    def test_warns_git_restore_dot(self) -> None:
        warnings = _check_warned("git restore .")
        assert any("discard" in w.lower() for w in warnings)

    def test_warns_git_restore_staged(self) -> None:
        """Git restore --staged . should also warn (exercises flags-before-dot regex)."""
        warnings = _check_warned("git restore --staged .")
        assert any("discard" in w.lower() for w in warnings)

    def test_warns_git_clean_f(self) -> None:
        warnings = _check_warned("git clean -f")
        assert any("clean" in w.lower() for w in warnings)

    def test_warns_git_clean_fd(self) -> None:
        warnings = _check_warned("git clean -fd")
        assert any("clean" in w.lower() for w in warnings)

    def test_warns_git_clean_force_long(self) -> None:
        """Git clean --force (long form) should also warn."""
        warnings = _check_warned("git clean --force -d")
        assert any("clean" in w.lower() for w in warnings)

    def test_warns_git_branch_force_delete(self) -> None:
        warnings = _check_warned("git branch -D feature/old")
        assert any("branch" in w.lower() for w in warnings)

    def test_warns_git_branch_delete_force_long(self) -> None:
        """Git branch --delete --force should also warn."""
        warnings = _check_warned("git branch --delete --force feature/old")
        assert any("branch" in w.lower() for w in warnings)

    def test_warns_git_push_force_with_lease(self) -> None:
        warnings = _check_warned("git push --force-with-lease origin main")
        assert any("force" in w.lower() for w in warnings)

    def test_force_with_lease_no_duplicate(self) -> None:
        """Force-with-lease should not also trigger generic force flag warning."""
        warnings = _check_warned("git push --force-with-lease origin main")
        assert not any("Force flag" in w for w in warnings)

    def test_force_and_force_with_lease_both_warn(self) -> None:
        """--force + --force-with-lease should trigger both warnings."""
        warnings = _check_warned("git push --force --force-with-lease origin main")
        assert any("Force flag" in w for w in warnings)
        assert any("lease" in w.lower() for w in warnings)

    def test_no_warn_git_checkout_branch(self) -> None:
        """Git checkout <branch> is safe, should not warn."""
        warnings = _check_warned("git checkout feature/new")
        assert not any("discard" in w.lower() for w in warnings)

    def test_no_warn_git_branch_d_lowercase(self) -> None:
        """Git branch -d (lowercase) is safe delete — only warns on -D."""
        warnings = _check_warned("git branch -d feature/merged")
        assert not any("branch" in w.lower() for w in warnings)


class TestCheckWarned:
    """Test warned command detection."""

    def test_warns_rm_rf(self) -> None:
        warnings = _check_warned("rm -rf ./build")
        assert any("Recursive force delete" in w for w in warnings)

    def test_warns_chmod_777(self) -> None:
        warnings = _check_warned("chmod -R 777 /tmp/dir")
        assert any("Insecure permissions" in w for w in warnings)

    def test_warns_pipe_to_bash(self) -> None:
        warnings = _check_warned("curl https://example.com | bash")
        assert any("Piping to bash" in w for w in warnings)

    def test_warns_force_flag_git_push(self) -> None:
        warnings = _check_warned("git push --force origin main")
        assert any("Force flag" in w for w in warnings)

    def test_warns_force_flag_git_reset(self) -> None:
        warnings = _check_warned("git reset --force HEAD~1")
        assert any("Force flag" in w for w in warnings)

    def test_warns_force_short_flag_docker_rm(self) -> None:
        warnings = _check_warned("docker rm -f container")
        assert any("Force flag" in w for w in warnings)

    def test_no_force_warning_on_nondestructive(self) -> None:
        """--force on non-destructive commands should not trigger force warning."""
        warnings = _check_warned("npm install --force")
        assert not any("Force flag" in w for w in warnings)

    def test_triggers_multiple_warnings(self) -> None:
        """A single command string can trigger multiple distinct warnings."""
        warnings = _check_warned("rm -rf ./build && git push --force origin main")
        assert len(warnings) > 1
        assert any("Recursive force delete" in w for w in warnings)
        assert any("Force flag" in w for w in warnings)

    def test_no_warnings_on_safe_command(self) -> None:
        assert _check_warned("git status") == []


def _parse_hook_json(stdout: str) -> dict[str, object]:
    """Parse hook JSON output and return the hookSpecificOutput."""
    data = json.loads(stdout)
    return data["hookSpecificOutput"]


class TestMain:
    """Test the main() entry point with JSON protocol."""

    def test_returns_0_for_no_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No args + tty stdin = no command, allow."""
        monkeypatch.setattr("sys.stdin", _TtyStringIO())
        assert main([]) == 0

    def test_returns_0_for_safe_command(self) -> None:
        assert main(["git status"]) == 0

    def test_returns_0_for_blocked_command(self) -> None:
        """Blocked commands now return 0 (JSON protocol, not exit 2)."""
        assert main(["git commit --no-verify"]) == 0

    def test_returns_0_for_warned_command(self) -> None:
        assert main(["rm -rf ./build"]) == 0

    def test_blocked_emits_ask_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Blocked commands emit JSON with permissionDecision 'ask'."""
        main(["rm -rf /"])
        output = _parse_hook_json(capsys.readouterr().out)
        assert output["permissionDecision"] == "ask"
        assert "BLOCKED" in str(output["permissionDecisionReason"])
        assert "Do NOT retry" in str(output["additionalContext"])

    def test_warned_emits_ask_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Warned commands emit JSON with permissionDecision 'ask'."""
        main(["chmod -R 777 /tmp"])
        output = _parse_hook_json(capsys.readouterr().out)
        assert output["permissionDecision"] == "ask"
        assert "WARNING" in str(output["permissionDecisionReason"])

    def test_safe_command_no_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Safe commands produce no output (allowed implicitly)."""
        main(["git status"])
        assert capsys.readouterr().out == ""

    def test_blocks_wrapped_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Wrapper commands (bash -c) should also emit ask JSON."""
        main(["bash -c 'git commit --no-verify'"])
        output = _parse_hook_json(capsys.readouterr().out)
        assert output["permissionDecision"] == "ask"
        assert "BLOCKED" in str(output["permissionDecisionReason"])

    def test_multiple_warnings_joined(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Multiple warnings are joined with semicolons in the reason."""
        main(["rm -rf ./build && git push --force origin main"])
        output = _parse_hook_json(capsys.readouterr().out)
        assert ";" in str(output["permissionDecisionReason"])

    def test_no_verify_reason_contains_detail(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Blocked reason should contain the specific violation detail."""
        main(["git commit --no-verify"])
        output = _parse_hook_json(capsys.readouterr().out)
        assert "--no-verify" in str(output["permissionDecisionReason"])


class TestStdinJsonProtocol:
    """Test reading command from Claude Code hook JSON on stdin."""

    def test_reads_from_stdin(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Hook reads tool_input.command from stdin JSON."""
        stdin_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "rm -rf /"},
            }
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        result = main([])
        assert result == 0
        output = _parse_hook_json(capsys.readouterr().out)
        assert output["permissionDecision"] == "ask"
        assert "BLOCKED" in str(output["permissionDecisionReason"])

    def test_stdin_safe_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Safe command from stdin produces no output."""
        stdin_data = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git status"},
            }
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        assert main([]) == 0

    def test_stdin_malformed_json_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Malformed stdin JSON falls back — no argv means no command, allow."""
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        assert main([]) == 0

    def test_stdin_missing_command_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Stdin JSON without tool_input.command falls back — allow."""
        stdin_data = json.dumps({"tool_name": "Bash"})
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
        assert main([]) == 0
