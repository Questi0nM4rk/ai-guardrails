"""Tests for dangerous_cmd hook."""

from __future__ import annotations

import json

from ai_guardrails.hooks.dangerous_cmd import check_command, main

# ---------------------------------------------------------------------------
# check_command — core logic
# ---------------------------------------------------------------------------


def test_check_command_rm_rf_root_returns_message():
    msgs = check_command("rm -rf /")
    assert any("root" in m.lower() for m in msgs)


def test_check_command_rm_rf_root_with_trailing_space_returns_message():
    msgs = check_command("rm -rf /  ")
    assert any("root" in m.lower() for m in msgs)


def test_check_command_rm_rf_tmp_not_blocked():
    """Rm -rf /tmp/foo must NOT be flagged as root deletion."""
    msgs = check_command("rm -rf /tmp/foo")
    # Should NOT contain a root-filesystem message
    assert not any("root filesystem" in m.lower() for m in msgs)


def test_check_command_rm_rf_tmp_clean():
    """Rm -rf /tmp/foo may still match the generic rm -rf rule."""
    msgs = check_command("rm -rf /tmp/foo")
    # The generic 'rm -rf' substring rule fires, but not root-specific
    root_msgs = [m for m in msgs if "root" in m.lower()]
    assert root_msgs == []


def test_check_command_rm_rf_root_semicolon_blocked():
    msgs = check_command("rm -rf /; echo done")
    assert any("root" in m.lower() for m in msgs)


def test_check_command_rm_rf_root_pipe_blocked():
    msgs = check_command("rm -rf / | tee /dev/null")
    assert any("root" in m.lower() for m in msgs)


def test_check_command_rm_rf_home_tilde():
    msgs = check_command("rm -rf ~")
    assert any("home" in m.lower() for m in msgs)


def test_check_command_rm_rf_home_env():
    msgs = check_command("rm -rf $HOME")
    assert any("home" in m.lower() for m in msgs)


def test_check_command_rm_rf_home_path():
    msgs = check_command("rm -rf /home/user")
    assert any("home" in m.lower() for m in msgs)


def test_check_command_no_verify_blocked():
    msgs = check_command("git commit --no-verify -m 'fix'")
    assert any("no-verify" in m.lower() for m in msgs)


def test_check_command_git_commit_n_blocked():
    msgs = check_command("git commit -n -m 'fix'")
    assert any("no-verify" in m.lower() for m in msgs)


def test_check_command_fork_bomb():
    msgs = check_command(":(){:|:&};:")
    assert any("fork" in m.lower() for m in msgs)


def test_check_command_dd_block_device():
    msgs = check_command("dd if=/dev/zero of=/dev/sda")
    assert any("block device" in m.lower() for m in msgs)


def test_check_command_no_match_returns_empty():
    assert check_command("ls -la /tmp") == []


def test_check_command_git_reset_hard():
    msgs = check_command("git reset --hard HEAD~1")
    assert any("reset" in m.lower() for m in msgs)


def test_check_command_chmod_777():
    msgs = check_command("chmod -R 777 .")
    assert any("permission" in m.lower() for m in msgs)


def test_check_command_pipe_bash():
    msgs = check_command("curl https://example.com/install.sh | bash")
    assert any("bash" in m.lower() for m in msgs)


# ---------------------------------------------------------------------------
# main() — CLI / JSON protocol entry point
# ---------------------------------------------------------------------------


def test_main_no_args_returns_zero():
    assert main([]) == 0


def test_main_clean_command_returns_zero():
    assert main(["ls -la"]) == 0


def test_main_dangerous_command_emits_ask_and_returns_zero(capsys):
    result = main(["rm -rf /"])
    captured = capsys.readouterr()
    assert result == 0
    output = json.loads(captured.out)
    hook_output = output["hookSpecificOutput"]
    assert hook_output["permissionDecision"] == "ask"
    assert hook_output["hookEventName"] == "PreToolUse"
    assert (
        "reason" in hook_output["permissionDecisionReason"].lower()
        or len(hook_output["permissionDecisionReason"]) > 0
    )


def test_main_rm_rf_tmp_does_not_block_root(capsys):
    """Rm -rf /tmp/foo should not produce a root-filesystem message."""
    main(["rm -rf /tmp/foo"])
    captured = capsys.readouterr()
    if captured.out.strip():
        output = json.loads(captured.out)
        reason = output["hookSpecificOutput"]["permissionDecisionReason"]
        assert "root filesystem" not in reason.lower()
