"""Tests for guardrails.coderabbit.run_review -- the CLI review runner.

The parsing functions are covered by test_coderabbit.py.
This module tests run_review() which shells out to gh CLI.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from guardrails.coderabbit import run_review

if TYPE_CHECKING:
    import pytest


def _make_subprocess_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Create a mock subprocess.CompletedProcess."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# subprocess is imported inside run_review() so we patch the stdlib module
_SUBPROCESS_RUN = "subprocess.run"


class TestRunReviewNoPR:
    """Test run_review when no PR can be found."""

    @patch(_SUBPROCESS_RUN)
    def test_returns_1_when_no_pr_found(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.return_value = _make_subprocess_result(returncode=1, stdout="")
        result = run_review()
        assert result == 1
        captured = capsys.readouterr()
        assert "No PR found" in captured.err

    @patch(_SUBPROCESS_RUN)
    def test_returns_1_when_pr_number_invalid(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.return_value = _make_subprocess_result(stdout="not-a-number\n")
        result = run_review()
        assert result == 1
        captured = capsys.readouterr()
        assert "Unexpected PR number" in captured.err


class TestRunReviewRepoInfo:
    """Test run_review when repo info cannot be determined."""

    @patch(_SUBPROCESS_RUN)
    def test_returns_1_when_repo_info_fails(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _make_subprocess_result(stdout="42\n"),
            _make_subprocess_result(returncode=1),
        ]
        result = run_review()
        assert result == 1
        captured = capsys.readouterr()
        assert "repository info" in captured.err.lower()

    @patch(_SUBPROCESS_RUN)
    def test_returns_1_when_repo_info_malformed(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _make_subprocess_result(stdout="42\n"),
            _make_subprocess_result(stdout="only-one-word\n"),
        ]
        result = run_review()
        assert result == 1
        captured = capsys.readouterr()
        assert "Unexpected repo info" in captured.err


class TestRunReviewSuccess:
    """Test run_review with successful gh calls."""

    @patch(_SUBPROCESS_RUN)
    def test_successful_run_with_explicit_pr(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test with explicit PR number (skips PR detection)."""
        mock_run.side_effect = [
            _make_subprocess_result(stdout="owner repo\n"),
            _make_subprocess_result(stdout="[]"),
            _make_subprocess_result(stdout="[]"),
        ]
        result = run_review(pr=42)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"]["total"] == 0

    @patch(_SUBPROCESS_RUN)
    def test_successful_run_with_threads(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        threads = [
            {
                "path": "src/main.py",
                "line": 10,
                "body": "_\U0001f7e0 Major_\n\n**Fix the bug**\n\nDescription",
            }
        ]
        mock_run.side_effect = [
            _make_subprocess_result(stdout="owner repo\n"),
            _make_subprocess_result(stdout=json.dumps(threads)),
            _make_subprocess_result(stdout="[]"),
        ]
        result = run_review(pr=1)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"]["total"] == 1
        assert output["tasks"][0]["file"] == "src/main.py"

    @patch(_SUBPROCESS_RUN)
    def test_pretty_output(self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
        mock_run.side_effect = [
            _make_subprocess_result(stdout="owner repo\n"),
            _make_subprocess_result(stdout="[]"),
            _make_subprocess_result(stdout="[]"),
        ]
        result = run_review(pr=1, pretty=True)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"]["total"] == 0
        # Pretty-printed JSON starts with {\n and contains indentation
        assert captured.out.startswith("{\n")
        assert json.dumps(output, indent=2) + "\n" == captured.out


class TestRunReviewSeverityFilter:
    """Test run_review with severity filtering."""

    @patch(_SUBPROCESS_RUN)
    def test_filters_by_major(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        threads = [
            {"path": "a.py", "line": 1, "body": "_\U0001f7e0 Major_\n\n**Issue 1**"},
            {"path": "b.py", "line": 2, "body": "_\U0001f7e1 Minor_\n\n**Issue 2**"},
        ]
        mock_run.side_effect = [
            _make_subprocess_result(stdout="owner repo\n"),
            _make_subprocess_result(stdout=json.dumps(threads)),
            _make_subprocess_result(stdout="[]"),
        ]
        result = run_review(pr=1, severity="major")
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"]["total"] == 1
        assert output["tasks"][0]["severity"] == "major"

    @patch(_SUBPROCESS_RUN)
    def test_invalid_severity_returns_1(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _make_subprocess_result(stdout="owner repo\n"),
            _make_subprocess_result(stdout="[]"),
            _make_subprocess_result(stdout="[]"),
        ]
        result = run_review(pr=1, severity="invalid")
        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid severity" in captured.err


class TestRunReviewGraphQLFailure:
    """Test run_review handles GraphQL failures gracefully."""

    @patch(_SUBPROCESS_RUN)
    def test_continues_on_graphql_failure(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _make_subprocess_result(stdout="owner repo\n"),
            _make_subprocess_result(returncode=1),
            _make_subprocess_result(stdout="[]"),
        ]
        result = run_review(pr=1)
        assert result == 0
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        output = json.loads(captured.out)
        assert output["summary"]["total"] == 0

    @patch(_SUBPROCESS_RUN)
    def test_continues_on_body_fetch_failure(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _make_subprocess_result(stdout="owner repo\n"),
            _make_subprocess_result(stdout="[]"),
            _make_subprocess_result(returncode=1),
        ]
        result = run_review(pr=1)
        assert result == 0
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        output = json.loads(captured.out)
        assert output["summary"]["total"] == 0
