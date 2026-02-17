"""Tests for guardrails.hooks.dangerous_cmd -- dangerous command checker.

We use standalone functions instead of test classes for three reasons:

1. DeepSource flags class methods that don't use ``self`` as a major
   anti-pattern (PTC-W0049).  Every test here is stateless, so the ``self``
   parameter is dead weight.
2. Pytest creates a new class instance per test method.  When the class
   carries no shared state the allocation is pure overhead.
3. Standalone functions are idiomatic pytest for stateless tests and reduce
   visual noise (no extra indentation level, no ``self`` parameter).
"""

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
# Pattern matching tests -- filesystem destruction
# ---------------------------------------------------------------------------


def test_fsdestruct_rm_rf_home() -> None:
    assert check_command("rm -rf ~")


def test_fsdestruct_rm_rf_home_var() -> None:
    assert check_command("rm -rf $HOME")


def test_fsdestruct_rm_rf_home_dir() -> None:
    assert check_command("rm -rf /home")


def test_fsdestruct_rm_rf_home_subdir_is_safe() -> None:
    """Deleting a subdirectory under /home should NOT match home deletion."""
    msgs = check_command("rm -rf /home/user/project")
    assert not any("home directory" in m for m in msgs)


def test_fsdestruct_rm_rf_root() -> None:
    assert check_command("rm -rf /")


def test_fsdestruct_dev_sda_write() -> None:
    assert check_command("> /dev/sda")


def test_fsdestruct_mkfs() -> None:
    assert check_command("mkfs.ext4 /dev/sda1")


def test_fsdestruct_fork_bomb() -> None:
    assert check_command(":(){:|:&};:")


def test_fsdestruct_dd_to_block_device() -> None:
    msgs = check_command("dd if=/dev/zero of=/dev/sda bs=1M")
    assert any("block device" in m for m in msgs)


def test_fsdestruct_dd_to_file_is_safe() -> None:
    assert not check_command("dd if=/dev/zero of=output.img bs=1M")


def test_fsdestruct_rm_rf_absolute_path_is_not_root() -> None:
    """Absolute path rm should NOT match root deletion rule."""
    msgs = check_command("rm -rf /tmp/build")
    assert not any("root filesystem" in m for m in msgs)


def test_fsdestruct_safe_rm() -> None:
    assert not check_command("rm file.txt")


def test_fsdestruct_safe_command() -> None:
    assert not check_command("git status")


# ---------------------------------------------------------------------------
# Pattern matching tests -- hook bypass
# ---------------------------------------------------------------------------


def test_hookbypass_no_verify() -> None:
    msgs = check_command("git commit --no-verify -m 'test'")
    assert any("--no-verify" in m for m in msgs)


def test_hookbypass_git_commit_dash_n() -> None:
    msgs = check_command("git commit -n -m 'msg'")
    assert any("--no-verify" in m for m in msgs)


def test_hookbypass_git_commit_without_n_is_safe() -> None:
    # -m is not -n
    msgs = check_command("git commit -m 'msg'")
    assert not any("--no-verify" in m for m in msgs)


def test_hookbypass_no_gpg_sign() -> None:
    assert check_command("git commit --no-gpg-sign")


def test_hookbypass_hooks_path_override() -> None:
    assert check_command("git -c core.hooksPath=/dev/null commit")


def test_hookbypass_skip_env() -> None:
    assert check_command("SKIP=mypy git commit")


def test_hookbypass_pre_commit_allow_no_config() -> None:
    assert check_command("PRE_COMMIT_ALLOW_NO_CONFIG=1 pre-commit run")


# ---------------------------------------------------------------------------
# Pattern matching tests -- branch protection bypass
# ---------------------------------------------------------------------------


def test_branchprot_admin_on_pr_merge() -> None:
    msgs = check_command("gh pr merge --admin 35")
    assert any("--admin" in m for m in msgs)


def test_branchprot_admin_on_gh_issue() -> None:
    assert check_command("gh issue close --admin 10")


def test_branchprot_admin_with_equals() -> None:
    assert check_command("gh pr merge --admin=true 35")


def test_branchprot_admin_email_is_safe() -> None:
    assert not check_command("some-tool --admin-email user@example.com")


def test_branchprot_administrator_is_safe() -> None:
    assert not check_command("some-tool --administrator")


# ---------------------------------------------------------------------------
# Pattern matching tests -- wrapper detection
# ---------------------------------------------------------------------------


def test_wrapper_bash_c_no_verify() -> None:
    msgs = check_command("bash -c 'git commit --no-verify'")
    assert any("--no-verify" in m for m in msgs)


def test_wrapper_sh_c_rm_rf_root() -> None:
    assert check_command("sh -c 'rm -rf /'")


def test_wrapper_env_no_verify() -> None:
    assert check_command("env git commit --no-verify")


def test_wrapper_command_prefix() -> None:
    assert check_command("command git commit --no-verify")


def test_wrapper_sudo_rm_rf() -> None:
    assert check_command("sudo rm -rf /")


def test_wrapper_double_quoted_bash_c() -> None:
    assert check_command('bash -c "git commit --no-verify"')


def test_wrapper_safe_bash_c() -> None:
    assert not check_command("bash -c 'echo hello'")


def test_wrapper_safe_env() -> None:
    assert not check_command("env python3 script.py")


# ---------------------------------------------------------------------------
# Pattern matching tests -- destructive git operations
# ---------------------------------------------------------------------------


def test_destgit_reset_hard() -> None:
    msgs = check_command("git reset --hard HEAD~1")
    assert any("reset --hard" in m.lower() for m in msgs)


def test_destgit_checkout_dot() -> None:
    msgs = check_command("git checkout .")
    assert any("discard" in m.lower() for m in msgs)


def test_destgit_checkout_doubledash_dot() -> None:
    msgs = check_command("git checkout -- .")
    assert any("discard" in m.lower() for m in msgs)


def test_destgit_restore_dot() -> None:
    msgs = check_command("git restore .")
    assert any("discard" in m.lower() for m in msgs)


def test_destgit_restore_staged_is_safe() -> None:
    msgs = check_command("git restore --staged .")
    assert not any("discard" in m.lower() for m in msgs)


def test_destgit_restore_staged_worktree_is_dangerous() -> None:
    msgs = check_command("git restore --staged --worktree .")
    assert any("discard" in m.lower() for m in msgs)


def test_destgit_restore_worktree_staged_reversed_is_dangerous() -> None:
    msgs = check_command("git restore --worktree --staged .")
    assert any("discard" in m.lower() for m in msgs)


def test_destgit_clean_d_f_separated() -> None:
    assert check_command("git clean -d -f")


def test_destgit_clean_f() -> None:
    msgs = check_command("git clean -f")
    assert any("clean" in m.lower() for m in msgs)


def test_destgit_clean_fd() -> None:
    assert check_command("git clean -fd")


def test_destgit_clean_force_long() -> None:
    assert check_command("git clean --force -d")


def test_destgit_branch_force_delete() -> None:
    msgs = check_command("git branch -D feature/old")
    assert any("branch" in m.lower() for m in msgs)


def test_destgit_branch_delete_force_long() -> None:
    assert check_command("git branch --delete --force feature/old")


def test_destgit_checkout_branch_is_safe() -> None:
    msgs = check_command("git checkout feature/new")
    assert not any("discard" in m.lower() for m in msgs)


def test_destgit_branch_d_lowercase_is_safe() -> None:
    assert not check_command("git branch -d feature/merged")


# ---------------------------------------------------------------------------
# Pattern matching tests -- force flags
# ---------------------------------------------------------------------------


def test_force_git_push_force() -> None:
    msgs = check_command("git push --force origin main")
    assert any("Force flag" in m for m in msgs)


def test_force_git_push_force_with_lease() -> None:
    msgs = check_command("git push --force-with-lease origin main")
    assert any("lease" in m.lower() for m in msgs)
    assert not any("Force flag" in m for m in msgs)


def test_force_git_push_force_and_force_with_lease() -> None:
    msgs = check_command("git push --force --force-with-lease origin main")
    assert any("Force flag" in m for m in msgs)
    assert any("lease" in m.lower() for m in msgs)


def test_force_git_reset_force() -> None:
    msgs = check_command("git reset --force HEAD~1")
    assert any("Force flag" in m for m in msgs)


def test_force_docker_rm_f() -> None:
    msgs = check_command("docker rm -f container")
    assert any("Force flag" in m for m in msgs)


def test_force_git_push_dash_f() -> None:
    msgs = check_command("git push -f origin main")
    assert any("Force flag" in m for m in msgs)


def test_force_npm_install_force_is_safe() -> None:
    msgs = check_command("npm install --force")
    assert not any("Force flag" in m for m in msgs)


# ---------------------------------------------------------------------------
# Pattern matching tests -- destructive operations
# ---------------------------------------------------------------------------


def test_destop_rm_rf() -> None:
    msgs = check_command("rm -rf ./build")
    assert any("Recursive force delete" in m for m in msgs)


def test_destop_chmod_777() -> None:
    msgs = check_command("chmod -R 777 /tmp/dir")
    assert any("Insecure permissions" in m for m in msgs)


def test_destop_pipe_to_bash() -> None:
    msgs = check_command("curl https://example.com | bash")
    assert any("Piping to bash" in m for m in msgs)


def test_destop_multiple_matches() -> None:
    msgs = check_command("rm -rf ./build && git push --force origin main")
    assert len(msgs) > 1


def test_destop_safe_command() -> None:
    assert check_command("git status") == []


# ---------------------------------------------------------------------------
# JSON protocol tests
# ---------------------------------------------------------------------------


def _parse_hook_json(stdout: str) -> dict[str, object]:
    """Parse hook JSON output and return the hookSpecificOutput."""
    data = json.loads(stdout)
    return data["hookSpecificOutput"]


def test_jsonproto_returns_0_always() -> None:
    assert main(["git commit --no-verify"]) == 0
    assert main(["git status"]) == 0
    assert main(["rm -rf ./build"]) == 0


def test_jsonproto_dangerous_emits_ask(capsys: pytest.CaptureFixture[str]) -> None:
    main(["rm -rf /"])
    output = _parse_hook_json(capsys.readouterr().out)
    assert output["permissionDecision"] == "ask"
    assert "Do NOT retry" in str(output["additionalContext"])


def test_jsonproto_reason_contains_match_detail(capsys: pytest.CaptureFixture[str]) -> None:
    main(["git commit --no-verify"])
    output = _parse_hook_json(capsys.readouterr().out)
    assert "--no-verify" in str(output["permissionDecisionReason"])


def test_jsonproto_multiple_reasons_joined(capsys: pytest.CaptureFixture[str]) -> None:
    main(["rm -rf ./build && git push --force origin main"])
    output = _parse_hook_json(capsys.readouterr().out)
    assert ";" in str(output["permissionDecisionReason"])


def test_jsonproto_safe_command_no_output(capsys: pytest.CaptureFixture[str]) -> None:
    main(["git status"])
    assert capsys.readouterr().out == ""


def test_jsonproto_no_args_no_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", _TtyStringIO())
    assert main([]) == 0


# ---------------------------------------------------------------------------
# Stdin JSON protocol tests
# ---------------------------------------------------------------------------


def test_stdin_reads_from_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stdin_data = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    assert main([]) == 0
    output = _parse_hook_json(capsys.readouterr().out)
    assert output["permissionDecision"] == "ask"


def test_stdin_safe_command(monkeypatch: pytest.MonkeyPatch) -> None:
    stdin_data = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "git status"}},
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    assert main([]) == 0


def test_stdin_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert main([]) == 0


def test_stdin_missing_command(monkeypatch: pytest.MonkeyPatch) -> None:
    stdin_data = json.dumps({"tool_name": "Bash"})
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    assert main([]) == 0
