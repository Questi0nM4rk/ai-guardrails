"""Tests for CLI enforcement of resolve category requirements.

The --resolve flag must require a valid category prefix in the message.
The --resolve-all --body must also enforce category validation.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from guardrails.cli import main
from guardrails.comments import run_comments

if TYPE_CHECKING:
    import pytest


def _make_subprocess_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Create a mock subprocess.CompletedProcess."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


_PATCH_SUBPROCESS_RUN = "subprocess.run"

_GRAPHQL_THREADS = json.dumps(
    {
        "nodes": [
            {
                "id": "PRRT_abc",
                "isResolved": False,
                "comments": {
                    "totalCount": 1,
                    "nodes": [
                        {
                            "id": "PRRC_1",
                            "databaseId": 1001,
                            "author": {"login": "coderabbitai[bot]"},
                            "body": "Fix the import order.",
                            "path": "lib/foo.py",
                            "line": 10,
                            "startLine": None,
                            "createdAt": "2026-02-15T10:00:00Z",
                        }
                    ],
                },
            },
        ],
        "pageInfo": {"hasNextPage": False, "endCursor": None},
    }
)


def _repo_info_result() -> MagicMock:
    """Create mock repo info response."""
    return _make_subprocess_result(stdout="TestOwner test-repo\n")


def _graphql_result() -> MagicMock:
    """Create mock GraphQL threads response."""
    return _make_subprocess_result(stdout=_GRAPHQL_THREADS)


# ---------------------------------------------------------------------------
# run_comments — resolve with category enforcement
# ---------------------------------------------------------------------------


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_with_valid_category_succeeds(mock_run: MagicMock) -> None:
    """Resolving with 'Fixed in <hash>' should succeed."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
        _make_subprocess_result(),  # reply POST
        _make_subprocess_result(),  # resolve mutation
    ]
    result = run_comments(pr=31, resolve=("PRRT_abc", "Fixed in abc1234"))
    assert result == 0


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_with_acknowledged_fails(
    mock_run: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Resolving with 'Acknowledged' should be rejected."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
    ]
    result = run_comments(pr=31, resolve=("PRRT_abc", "Acknowledged"))
    assert result == 1
    captured = capsys.readouterr()
    assert "category" in captured.err.lower() or "valid" in captured.err.lower()


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_with_noted_fails(
    mock_run: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Resolving with 'Noted' should be rejected."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
    ]
    result = run_comments(pr=31, resolve=("PRRT_abc", "Noted"))
    assert result == 1


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_with_arbitrary_text_fails(
    mock_run: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Resolving with arbitrary text should be rejected."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
    ]
    result = run_comments(pr=31, resolve=("PRRT_abc", "Looks fine to me"))
    assert result == 1


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_without_body_fails(
    mock_run: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Resolving without a message body should be rejected."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
    ]
    result = run_comments(pr=31, resolve=("PRRT_abc", None))
    assert result == 1
    captured = capsys.readouterr()
    assert "category" in captured.err.lower() or "require" in captured.err.lower()


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_false_positive_succeeds(mock_run: MagicMock) -> None:
    """Resolving with 'False positive: <reason>' should succeed."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
        _make_subprocess_result(),  # reply POST
        _make_subprocess_result(),  # resolve mutation
    ]
    result = run_comments(
        pr=31, resolve=("PRRT_abc", "False positive: rule doesn't apply to test files")
    )
    assert result == 0


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_wont_fix_succeeds(mock_run: MagicMock) -> None:
    """Resolving with a won't-fix reason should succeed."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
        _make_subprocess_result(),  # reply POST
        _make_subprocess_result(),  # resolve mutation
    ]
    result = run_comments(pr=31, resolve=("PRRT_abc", "Won't fix: intentional design choice"))
    assert result == 0


# ---------------------------------------------------------------------------
# run_comments — resolve-all with category enforcement
# ---------------------------------------------------------------------------


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_all_with_invalid_body_fails(
    mock_run: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Batch resolve with invalid body should be rejected."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
    ]
    result = run_comments(pr=31, resolve_all=True, resolve_all_body="Acknowledged.")
    assert result == 1
    captured = capsys.readouterr()
    assert "category" in captured.err.lower() or "valid" in captured.err.lower()


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_all_with_valid_body_succeeds(
    mock_run: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Batch resolve with valid category body should succeed."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
        _make_subprocess_result(),  # reply POST
        _make_subprocess_result(),  # resolve mutation
    ]
    result = run_comments(pr=31, resolve_all=True, resolve_all_body="Fixed in abc1234")
    assert result == 0


@patch(_PATCH_SUBPROCESS_RUN)
def test_resolve_all_without_body_still_works(
    mock_run: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Batch resolve without a body (no reply) should still be allowed."""
    mock_run.side_effect = [
        _repo_info_result(),
        _graphql_result(),
        _make_subprocess_result(),  # resolve mutation
    ]
    result = run_comments(pr=31, resolve_all=True)
    assert result == 0


# ---------------------------------------------------------------------------
# CLI --resolve argument validation via main()
# ---------------------------------------------------------------------------


@patch("guardrails.cli._cmd_comments")
def test_cli_resolve_with_category_message(mock_cmd: MagicMock) -> None:
    """CLI --resolve with valid category message parses correctly."""
    mock_cmd.return_value = 0
    main(["comments", "--pr", "31", "--resolve", "PRRT_abc", "Fixed in abc1234"])
    args = mock_cmd.call_args[0][0]
    assert args.resolve == ["PRRT_abc", "Fixed in abc1234"]
