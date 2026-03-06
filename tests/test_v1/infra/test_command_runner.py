"""Tests for CommandRunner infrastructure."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

from ai_guardrails.infra.command_runner import CommandRunner


def test_run_returns_completed_process() -> None:
    runner = CommandRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hi"], returncode=0, stdout="hi\n", stderr=""
        )
        result = runner.run(["echo", "hi"])
    assert result.returncode == 0
    assert result.stdout == "hi\n"


def test_run_does_not_raise_on_nonzero_exit() -> None:
    runner = CommandRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["false"], returncode=1, stdout="", stderr="error"
        )
        result = runner.run(["false"])
    assert result.returncode == 1


def test_run_passes_timeout_to_subprocess() -> None:
    runner = CommandRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        runner.run(["echo", "x"], timeout=60)
    call_kwargs = mock_run.call_args[1]
    assert call_kwargs["timeout"] == 60


def test_run_uses_default_timeout_30s() -> None:
    runner = CommandRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        runner.run(["echo", "x"])
    call_kwargs = mock_run.call_args[1]
    assert call_kwargs["timeout"] == 30


def test_run_passes_cwd_when_provided(tmp_path: Path) -> None:
    runner = CommandRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        runner.run(["pwd"], cwd=tmp_path)
    call_kwargs = mock_run.call_args[1]
    assert call_kwargs["cwd"] == tmp_path


def test_run_captures_stdout_and_stderr() -> None:
    runner = CommandRunner()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="out", stderr="err"
        )
        result = runner.run(["cmd"])
    assert result.stdout == "out"
    assert result.stderr == "err"


def test_run_returns_failed_result_when_binary_missing() -> None:
    """FileNotFoundError from missing binary returns returncode=1 instead of raising."""
    runner = CommandRunner()
    with patch("subprocess.run", side_effect=FileNotFoundError("no such file")):
        result = runner.run(["nonexistent-binary-xyz"])
    assert result.returncode == 1
    assert result.stdout == ""
    assert "no such file" in result.stderr


def test_run_returns_failed_result_on_permission_error() -> None:
    """PermissionError returns returncode=1 instead of raising."""
    runner = CommandRunner()
    with patch("subprocess.run", side_effect=PermissionError("permission denied")):
        result = runner.run(["/bin/forbidden"])
    assert result.returncode == 1
    assert "permission denied" in result.stderr


def test_run_returns_failed_result_on_timeout() -> None:
    """TimeoutExpired returns returncode=1 instead of raising."""
    runner = CommandRunner()
    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["slow-cmd"], timeout=30),
    ):
        result = runner.run(["slow-cmd"])
    assert result.returncode == 1
    assert result.stdout == ""
    assert "timed out" in result.stderr.lower() or "timeout" in result.stderr.lower()
