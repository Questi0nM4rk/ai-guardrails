"""CLI integration tests for guardrails.comments — subprocess mocking."""

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

# Sample GraphQL response with pageInfo wrapper and three threads from different bots
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
            {
                "id": "PRRT_def",
                "isResolved": False,
                "comments": {
                    "totalCount": 2,
                    "nodes": [
                        {
                            "id": "PRRC_2",
                            "databaseId": 1002,
                            "author": {"login": "claude[bot]"},
                            "body": "Consider extracting this to a helper.",
                            "path": "lib/bar.py",
                            "line": 25,
                            "startLine": 20,
                            "createdAt": "2026-02-15T11:00:00Z",
                        }
                    ],
                },
            },
            {
                "id": "PRRT_ghi",
                "isResolved": True,
                "comments": {
                    "totalCount": 1,
                    "nodes": [
                        {
                            "id": "PRRC_3",
                            "databaseId": 1003,
                            "author": {"login": "deepsource-io[bot]"},
                            "body": "Unused variable.",
                            "path": "lib/baz.py",
                            "line": 5,
                            "startLine": None,
                            "createdAt": "2026-02-15T09:00:00Z",
                        }
                    ],
                },
            },
        ],
        "pageInfo": {
            "hasNextPage": False,
            "endCursor": None,
        },
    }
)


def _repo_info_result() -> MagicMock:
    return _make_subprocess_result(stdout="TestOwner test-repo\n")


def _graphql_result() -> MagicMock:
    return _make_subprocess_result(stdout=_GRAPHQL_THREADS)


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------


class TestCommentsCliDispatch:
    """Test that CLI dispatches to _cmd_comments."""

    @patch("guardrails.cli._cmd_comments")
    def test_dispatches_to_comments(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        result = main(["comments", "--pr", "31"])
        mock_cmd.assert_called_once()
        assert result == 0

    @patch("guardrails.cli._cmd_comments")
    def test_comments_args_parsed(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["comments", "--pr", "31", "--bot", "claude", "--json", "--all"])
        args = mock_cmd.call_args[0][0]
        assert args.pr == 31
        assert args.bot == "claude"
        assert args.json is True
        assert args.all is True

    @patch("guardrails.cli._cmd_comments")
    def test_reply_args_parsed(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["comments", "--pr", "31", "--reply", "PRRT_abc", "Fixed."])
        args = mock_cmd.call_args[0][0]
        assert args.reply == ["PRRT_abc", "Fixed."]

    @patch("guardrails.cli._cmd_comments")
    def test_resolve_args_parsed(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["comments", "--pr", "31", "--resolve", "PRRT_abc", "Done."])
        args = mock_cmd.call_args[0][0]
        assert args.resolve == ["PRRT_abc", "Done."]

    @patch("guardrails.cli._cmd_comments")
    def test_resolve_without_body(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["comments", "--pr", "31", "--resolve", "PRRT_abc"])
        args = mock_cmd.call_args[0][0]
        assert args.resolve == ["PRRT_abc"]

    @patch("guardrails.cli._cmd_comments")
    def test_body_flag_parsed(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["comments", "--pr", "31", "--resolve-all", "--body", "Done."])
        args = mock_cmd.call_args[0][0]
        assert args.resolve_all is True
        assert args.body == "Done."

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_too_many_args(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        result = main(["comments", "--pr", "31", "--resolve", "PRRT_abc", "body", "extra"])
        assert result == 1
        captured = capsys.readouterr()
        assert "at most 2" in captured.err


# ---------------------------------------------------------------------------
# run_comments — compact output (default)
# ---------------------------------------------------------------------------


class TestRunCommentsCompact:
    """Test default compact output format."""

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_compact_summary_header(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        result = run_comments(pr=31)
        assert result == 0
        captured = capsys.readouterr()
        assert "# 2 unresolved" in captured.out
        assert "coderabbit: 1" in captured.out
        assert "claude: 1" in captured.out

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_compact_contains_thread_ids(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        run_comments(pr=31)
        captured = capsys.readouterr()
        assert "PRRT_abc" in captured.out
        assert "PRRT_def" in captured.out
        # PRRT_ghi is resolved, not shown by default
        assert "PRRT_ghi" not in captured.out

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_compact_filtered_by_bot(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        run_comments(pr=31, bot="claude")
        captured = capsys.readouterr()
        assert "claude: 1" in captured.out
        assert "coderabbit" not in captured.out.split("\n", 1)[0]  # not in summary

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_compact_show_all_includes_resolved(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        run_comments(pr=31, show_all=True)
        captured = capsys.readouterr()
        # 3 total shown, 2 unresolved + 1 resolved
        assert "# 2 unresolved" in captured.out
        assert "[resolved]" in captured.out


# ---------------------------------------------------------------------------
# run_comments — JSON output
# ---------------------------------------------------------------------------


class TestRunCommentsJson:
    """Test JSON output via --json flag."""

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_json_output_schema(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        result = run_comments(pr=31, output_json=True)
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"]["total"] == 2
        assert output["summary"]["unresolved"] == 2

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_json_show_all(self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        run_comments(pr=31, show_all=True, output_json=True)
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["summary"]["total"] == 3


# ---------------------------------------------------------------------------
# run_comments — reply
# ---------------------------------------------------------------------------


class TestRunCommentsReply:
    """Test replying to threads."""

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_reply_success(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = [
            _repo_info_result(),  # repo info
            _graphql_result(),  # fetch threads
            _make_subprocess_result(),  # reply POST
        ]
        result = run_comments(pr=31, reply=("PRRT_abc", "Fixed."))
        assert result == 0
        # Verify REST API call contains /replies path
        reply_call = mock_run.call_args_list[2]
        reply_cmd = reply_call[0][0]
        assert any("replies" in str(arg) for arg in reply_cmd)

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_reply_thread_not_found(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        result = run_comments(pr=31, reply=("PRRT_nonexistent", "Fixed."))
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err


# ---------------------------------------------------------------------------
# run_comments — resolve
# ---------------------------------------------------------------------------


class TestRunCommentsResolve:
    """Test resolving threads."""

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_success(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = [
            _repo_info_result(),  # repo info
            _graphql_result(),  # fetch threads
            _make_subprocess_result(),  # resolve mutation
        ]
        result = run_comments(pr=31, resolve=("PRRT_abc", None))
        assert result == 0

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_with_reply(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = [
            _repo_info_result(),  # repo info
            _graphql_result(),  # fetch threads
            _make_subprocess_result(),  # reply POST
            _make_subprocess_result(),  # resolve mutation
        ]
        result = run_comments(pr=31, resolve=("PRRT_abc", "Fixed in abc1234."))
        assert result == 0
        # 4 subprocess calls: repo info, graphql, reply, resolve
        assert mock_run.call_count == 4

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_reply_failure_returns_error(self, mock_run: MagicMock) -> None:
        """Single-thread resolve should fail if reply fails."""
        mock_run.side_effect = [
            _repo_info_result(),  # repo info
            _graphql_result(),  # fetch threads
            _make_subprocess_result(returncode=1),  # reply POST fails
        ]
        result = run_comments(pr=31, resolve=("PRRT_abc", "Fixed."))
        assert result == 1

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_thread_not_found(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        result = run_comments(pr=31, resolve=("PRRT_nonexistent", None))
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_body_no_comment_id_warns(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Resolve with body but no comment_id should warn and still resolve."""
        # Create a thread with no comment_id
        thread_data = json.dumps(
            {
                "nodes": [
                    {
                        "id": "PRRT_noid",
                        "isResolved": False,
                        "comments": {
                            "totalCount": 1,
                            "nodes": [
                                {
                                    "id": "PRRC_4",
                                    "databaseId": None,
                                    "author": {"login": "claude[bot]"},
                                    "body": "Test.",
                                    "path": "test.py",
                                    "line": 1,
                                    "startLine": None,
                                    "createdAt": "2026-02-15T10:00:00Z",
                                }
                            ],
                        },
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        )
        mock_run.side_effect = [
            _repo_info_result(),
            _make_subprocess_result(stdout=thread_data),
            _make_subprocess_result(),  # resolve mutation
        ]
        result = run_comments(pr=31, resolve=("PRRT_noid", "Fixed."))
        assert result == 0
        captured = capsys.readouterr()
        assert "reply skipped" in captured.err


# ---------------------------------------------------------------------------
# run_comments — resolve-all
# ---------------------------------------------------------------------------


class TestRunCommentsResolveAll:
    """Test batch resolving threads."""

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_all_success(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _repo_info_result(),  # repo info
            _graphql_result(),  # fetch threads
            _make_subprocess_result(),  # resolve PRRT_abc
            _make_subprocess_result(),  # resolve PRRT_def
        ]
        result = run_comments(pr=31, resolve_all=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "Resolved 2" in captured.err

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_all_with_bot_filter(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _repo_info_result(),  # repo info
            _graphql_result(),  # fetch threads
            _make_subprocess_result(),  # resolve PRRT_abc (coderabbit only)
        ]
        result = run_comments(pr=31, resolve_all=True, bot="coderabbit")
        assert result == 0
        captured = capsys.readouterr()
        assert "Resolved 1" in captured.err

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_all_no_threads(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        empty_graphql = json.dumps(
            {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        )
        mock_run.side_effect = [
            _repo_info_result(),
            _make_subprocess_result(stdout=empty_graphql),
        ]
        result = run_comments(pr=31, resolve_all=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "No unresolved threads" in captured.err

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_all_with_body(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _repo_info_result(),  # repo info
            _graphql_result(),  # fetch threads
            _make_subprocess_result(),  # reply PRRT_abc
            _make_subprocess_result(),  # resolve PRRT_abc
            _make_subprocess_result(),  # reply PRRT_def
            _make_subprocess_result(),  # resolve PRRT_def
        ]
        result = run_comments(pr=31, resolve_all=True, resolve_all_body="Acknowledged.")
        assert result == 0
        captured = capsys.readouterr()
        assert "Resolved 2" in captured.err

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_resolve_all_reply_failure_counted(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When reply fails during resolve-all, thread is counted as failed."""
        mock_run.side_effect = [
            _repo_info_result(),  # repo info
            _graphql_result(),  # fetch threads
            _make_subprocess_result(returncode=1),  # reply PRRT_abc fails
            _make_subprocess_result(),  # reply PRRT_def
            _make_subprocess_result(),  # resolve PRRT_def
        ]
        result = run_comments(pr=31, resolve_all=True, resolve_all_body="Done.")
        assert result == 1  # has failures
        captured = capsys.readouterr()
        assert "1 failed" in captured.err


# ---------------------------------------------------------------------------
# run_comments — pagination
# ---------------------------------------------------------------------------


class TestRunCommentsPagination:
    """Test cursor-based pagination of review threads."""

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_two_page_fetch(self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
        page1 = json.dumps(
            {
                "nodes": [
                    {
                        "id": "PRRT_p1",
                        "isResolved": False,
                        "comments": {
                            "totalCount": 1,
                            "nodes": [
                                {
                                    "id": "PRRC_p1",
                                    "databaseId": 2001,
                                    "author": {"login": "claude[bot]"},
                                    "body": "Page 1 comment.",
                                    "path": "a.py",
                                    "line": 1,
                                    "startLine": None,
                                    "createdAt": "2026-02-15T10:00:00Z",
                                }
                            ],
                        },
                    }
                ],
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor_abc"},
            }
        )
        page2 = json.dumps(
            {
                "nodes": [
                    {
                        "id": "PRRT_p2",
                        "isResolved": False,
                        "comments": {
                            "totalCount": 1,
                            "nodes": [
                                {
                                    "id": "PRRC_p2",
                                    "databaseId": 2002,
                                    "author": {"login": "coderabbitai[bot]"},
                                    "body": "Page 2 comment.",
                                    "path": "b.py",
                                    "line": 5,
                                    "startLine": None,
                                    "createdAt": "2026-02-15T11:00:00Z",
                                }
                            ],
                        },
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        )
        mock_run.side_effect = [
            _repo_info_result(),
            _make_subprocess_result(stdout=page1),  # first page
            _make_subprocess_result(stdout=page2),  # second page
        ]
        result = run_comments(pr=31)
        assert result == 0
        captured = capsys.readouterr()
        assert "PRRT_p1" in captured.out
        assert "PRRT_p2" in captured.out
        assert "# 2 unresolved" in captured.out


# ---------------------------------------------------------------------------
# run_comments — error handling
# ---------------------------------------------------------------------------


class TestRunCommentsErrors:
    """Test error paths."""

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_no_pr_error(self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
        mock_run.return_value = _make_subprocess_result(returncode=1)
        result = run_comments()
        assert result == 1
        captured = capsys.readouterr()
        assert "No PR found" in captured.err

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_repo_info_failure(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _make_subprocess_result(stdout="42\n"),  # PR number
            _make_subprocess_result(returncode=1),  # repo info fails
        ]
        result = run_comments()
        assert result == 1
        captured = capsys.readouterr()
        assert "repository info" in captured.err.lower()

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_graphql_failure_returns_empty(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_run.side_effect = [
            _repo_info_result(),
            _make_subprocess_result(returncode=1),  # graphql fails
        ]
        result = run_comments(pr=31)
        assert result == 0
        captured = capsys.readouterr()
        # Default is compact, so check for summary header
        assert "# 0 unresolved" in captured.out

    @patch(_PATCH_SUBPROCESS_RUN)
    def test_empty_bot_filter_ignored(
        self, mock_run: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Bot filter with empty segments like 'claude,,deepsource' should work."""
        mock_run.side_effect = [_repo_info_result(), _graphql_result()]
        result = run_comments(pr=31, bot="claude,,")
        assert result == 0
        captured = capsys.readouterr()
        assert "claude: 1" in captured.out
