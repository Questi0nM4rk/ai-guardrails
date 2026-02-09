"""Tests for guardrails.hooks.dangerous_cmd -- dangerous command checker."""

from __future__ import annotations

from typing import TYPE_CHECKING

from guardrails.hooks.dangerous_cmd import _check_blocked, _check_warned, main

if TYPE_CHECKING:
    import pytest


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

    def test_no_warnings_on_safe_command(self) -> None:
        assert _check_warned("git status") == []


class TestMain:
    """Test the main() entry point."""

    def test_returns_0_for_no_args(self) -> None:
        assert main([]) == 0

    def test_returns_0_for_safe_command(self) -> None:
        assert main(["git status"]) == 0

    def test_returns_2_for_blocked_command(self) -> None:
        assert main(["git commit --no-verify"]) == 2

    def test_returns_0_for_warned_command(self) -> None:
        """Warned commands are allowed (exit 0), just print warnings."""
        assert main(["rm -rf ./build"]) == 0

    def test_blocked_message_printed(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["rm -rf /"])
        captured = capsys.readouterr()
        assert "BLOCKED" in captured.out

    def test_warning_message_printed(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["chmod -R 777 /tmp"])
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
