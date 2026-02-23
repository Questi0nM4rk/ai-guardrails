"""Unit tests for guardrails.comments — parsing, filtering, and formatting."""

from __future__ import annotations

import json

from guardrails.comments import (
    BOT_ALIASES,
    _clean_body,
    _detect_pr_agent,
    _resolve_bot_name,
    _short_bot_name,
    _truncate,
    filter_threads,
    format_compact,
    format_json,
    parse_thread,
)

# ---------------------------------------------------------------------------
# BOT_ALIASES sanity check
# ---------------------------------------------------------------------------


def test_bot_aliases_contains_expected_bots() -> None:
    """BOT_ALIASES includes coderabbit, claude, and pr-agent."""
    assert "coderabbit" in BOT_ALIASES
    assert "claude" in BOT_ALIASES
    assert "pr-agent" in BOT_ALIASES
    # PR-Agent maps to "pr-agent" (the detected bot name from parse_thread),
    # not "github-actions" (the raw GitHub login), because content-based
    # detection overrides the bot name before filtering.
    assert BOT_ALIASES["pr-agent"] == "pr-agent"
    assert "deepsource" not in BOT_ALIASES
    assert "gemini" not in BOT_ALIASES


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_thread(
    *,
    bot: str = "coderabbitai",
    resolved: bool = False,
    thread_id: str = "PRRT_test1",
    comment_id: int = 123,
    path: str = "lib/foo.py",
    line: int = 42,
    body: str = "Fix this issue.",
) -> dict:
    """Create a parsed thread dict (output of parse_thread)."""
    return {
        "thread_id": thread_id,
        "comment_id": comment_id,
        "bot": bot,
        "path": path,
        "line": line,
        "start_line": None,
        "resolved": resolved,
        "body_preview": body,
        "created_at": "2026-02-15T23:34:05Z",
        "reply_count": 0,
    }


def _make_graphql_node(
    *,
    thread_id: str = "PRRT_test1",
    resolved: bool = False,
    author: str = "coderabbitai[bot]",
    body: str = "Fix this issue.",
    database_id: int = 123,
    path: str = "lib/foo.py",
    line: int = 42,
) -> dict:
    """Create a raw GraphQL reviewThread node."""
    return {
        "id": thread_id,
        "isResolved": resolved,
        "comments": {
            "totalCount": 1,
            "nodes": [
                {
                    "id": "PRRC_test1",
                    "databaseId": database_id,
                    "author": {"login": author},
                    "body": body,
                    "path": path,
                    "line": line,
                    "startLine": None,
                    "createdAt": "2026-02-15T23:34:05Z",
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# parse_thread
# ---------------------------------------------------------------------------


class TestParseThread:
    """Test GraphQL node parsing into flat dicts."""

    def test_parses_basic_node(self) -> None:
        node = _make_graphql_node()
        result = parse_thread(node)
        assert result is not None
        assert result["thread_id"] == "PRRT_test1"
        assert result["comment_id"] == 123
        assert result["bot"] == "coderabbitai"
        assert result["path"] == "lib/foo.py"
        assert result["line"] == 42
        assert result["resolved"] is False
        assert result["reply_count"] == 0

    def test_returns_none_for_empty_comments(self) -> None:
        node = {"id": "PRRT_x", "isResolved": False, "comments": {"nodes": []}}
        assert parse_thread(node) is None

    def test_strips_bot_suffix(self) -> None:
        """Bot suffix [bot] is stripped from author login."""
        node = _make_graphql_node(author="coderabbitai[bot]")
        result = parse_thread(node)
        assert result is not None
        assert result["bot"] == "coderabbitai"

    def test_reply_count_with_multiple_comments(self) -> None:
        node = _make_graphql_node()
        node["comments"]["totalCount"] = 3
        result = parse_thread(node)
        assert result is not None
        assert result["reply_count"] == 2

    def test_handles_null_author(self) -> None:
        """author: null (deleted accounts) should produce 'unknown'."""
        node = _make_graphql_node()
        node["comments"]["nodes"][0]["author"] = None
        result = parse_thread(node)
        assert result is not None
        assert result["bot"] == "unknown"

    def test_handles_missing_author_key(self) -> None:
        """Missing author key entirely should produce 'unknown'."""
        node = _make_graphql_node()
        del node["comments"]["nodes"][0]["author"]
        result = parse_thread(node)
        assert result is not None
        assert result["bot"] == "unknown"


# ---------------------------------------------------------------------------
# _clean_body / _truncate / _short_bot_name
# ---------------------------------------------------------------------------


class TestHelpers:
    """Test body cleaning, truncation, and bot name helpers."""

    def test_strips_html_tags(self) -> None:
        assert _clean_body("<b>bold</b> text") == "bold text"

    def test_strips_self_closing_tags(self) -> None:
        assert _clean_body("image <img src='x'/> here") == "image here"

    def test_preserves_non_html_angle_brackets(self) -> None:
        """Comparison operators like a < b > c should not be stripped."""
        assert _clean_body("if a < b > c then") == "if a < b > c then"

    def test_collapses_whitespace(self) -> None:
        assert _clean_body("line1\n\nline2\n  extra") == "line1 line2 extra"

    def test_truncate_short(self) -> None:
        assert _truncate("short", 120) == "short"

    def test_truncate_exact_length(self) -> None:
        text = "x" * 80
        assert _truncate(text, 80) == text

    def test_truncate_long(self) -> None:
        long_text = "x" * 200
        result = _truncate(long_text, 120)
        assert len(result) == 120
        assert result.endswith("...")

    def test_truncate_small_length_no_ellipsis(self) -> None:
        """When length <= 3, truncate without adding '...' to avoid exceeding limit."""
        assert _truncate("abcdef", 3) == "abc"
        assert _truncate("abcdef", 2) == "ab"
        assert _truncate("abcdef", 1) == "a"

    def test_short_bot_name_known(self) -> None:
        """Registered bot aliases: coderabbit, claude, and pr-agent."""
        assert _short_bot_name("coderabbitai") == "coderabbit"
        assert _short_bot_name("claude") == "claude"
        assert _short_bot_name("pr-agent") == "pr-agent"

    def test_short_bot_name_unknown_passthrough(self) -> None:
        assert _short_bot_name("some-random-bot") == "some-random-bot"


# ---------------------------------------------------------------------------
# _resolve_bot_name
# ---------------------------------------------------------------------------


class TestResolveBotName:
    """Test bot alias resolution."""

    def test_short_alias_to_login(self) -> None:
        """Registered aliases: coderabbit, claude, and pr-agent."""
        assert _resolve_bot_name("coderabbit") == "coderabbitai"
        assert _resolve_bot_name("claude") == "claude"
        assert _resolve_bot_name("pr-agent") == "pr-agent"

    def test_case_insensitive(self) -> None:
        """Alias resolution is case-insensitive."""
        assert _resolve_bot_name("CodeRabbit") == "coderabbitai"
        assert _resolve_bot_name("CLAUDE") == "claude"

    def test_full_login_passthrough(self) -> None:
        """Full GitHub login names pass through unchanged."""
        assert _resolve_bot_name("coderabbitai") == "coderabbitai"

    def test_unknown_name_passthrough(self) -> None:
        assert _resolve_bot_name("some-bot") == "some-bot"


# ---------------------------------------------------------------------------
# filter_threads
# ---------------------------------------------------------------------------


class TestFilterThreads:
    """Test thread filtering by bot and resolution status."""

    def test_filters_by_single_bot(self) -> None:
        """Filter by a single registered bot alias."""
        threads = [
            _make_thread(bot="coderabbitai"),
            _make_thread(bot="some-other-bot", thread_id="PRRT_2"),
            _make_thread(bot="claude", thread_id="PRRT_3"),
        ]
        result = filter_threads(threads, bots=["coderabbit"], unresolved_only=False)
        assert len(result) == 1
        assert result[0]["bot"] == "coderabbitai"

    def test_filters_by_multiple_bots(self) -> None:
        """Filter by multiple bot aliases at once."""
        threads = [
            _make_thread(bot="coderabbitai"),
            _make_thread(bot="some-other-bot", thread_id="PRRT_2"),
            _make_thread(bot="claude", thread_id="PRRT_3"),
        ]
        result = filter_threads(threads, bots=["coderabbit", "claude"], unresolved_only=False)
        assert len(result) == 2

    def test_unresolved_only_default(self) -> None:
        threads = [
            _make_thread(resolved=False),
            _make_thread(resolved=True, thread_id="PRRT_2"),
        ]
        result = filter_threads(threads, unresolved_only=True)
        assert len(result) == 1
        assert result[0]["resolved"] is False

    def test_show_all_includes_resolved(self) -> None:
        threads = [
            _make_thread(resolved=False),
            _make_thread(resolved=True, thread_id="PRRT_2"),
        ]
        result = filter_threads(threads, unresolved_only=False)
        assert len(result) == 2

    def test_no_match_returns_empty(self) -> None:
        threads = [_make_thread(bot="coderabbitai")]
        result = filter_threads(threads, bots=["unknown-bot"], unresolved_only=False)
        assert result == []

    def test_filters_case_insensitive_unknown_bot(self) -> None:
        threads = [_make_thread(bot="custombot")]
        result = filter_threads(threads, bots=["CustomBot"], unresolved_only=False)
        assert len(result) == 1

    def test_no_filter_returns_all_unresolved(self) -> None:
        """Without bot filter, all unresolved threads are returned."""
        threads = [
            _make_thread(bot="coderabbitai"),
            _make_thread(bot="claude", thread_id="PRRT_2"),
            _make_thread(bot="some-bot", thread_id="PRRT_3", resolved=True),
        ]
        result = filter_threads(threads)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# format_compact
# ---------------------------------------------------------------------------


class TestFormatCompact:
    """Test compact one-line-per-thread output."""

    def test_summary_header(self) -> None:
        threads = [
            _make_thread(bot="coderabbitai"),
            _make_thread(bot="claude", thread_id="PRRT_2"),
        ]
        output = format_compact(threads)
        assert output.startswith("# 2 unresolved")
        assert "coderabbit: 1" in output
        assert "claude: 1" in output

    def test_thread_line_contains_full_id(self) -> None:
        threads = [_make_thread(thread_id="PRRT_kwDOQ91llM5uveFH")]
        output = format_compact(threads)
        assert "PRRT_kwDOQ91llM5uveFH" in output

    def test_thread_line_contains_bot_and_location(self) -> None:
        threads = [_make_thread(bot="claude", path="lib/foo.py", line=42)]
        output = format_compact(threads)
        assert "claude" in output
        assert "foo.py:42" in output

    def test_thread_line_contains_preview(self) -> None:
        threads = [_make_thread(body="Fix this issue.")]
        output = format_compact(threads)
        assert "Fix this issue." in output

    def test_resolved_tag_shown(self) -> None:
        threads = [_make_thread(resolved=True)]
        output = format_compact(threads)
        assert "[resolved]" in output

    def test_no_resolved_tag_for_unresolved(self) -> None:
        threads = [_make_thread(resolved=False)]
        output = format_compact(threads)
        assert "[resolved]" not in output

    def test_empty_threads(self) -> None:
        output = format_compact([])
        assert "# 0 unresolved" in output

    def test_dynamic_column_widths(self) -> None:
        """Columns should expand for long bot names or file paths."""
        threads = [_make_thread(bot="some-long-bot-name", path="deeply/nested/long-filename.py")]
        output = format_compact(threads)
        # Bot and location should not be truncated
        assert "some-long-bot-name" in output
        assert "long-filename.py:42" in output


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


class TestFormatJson:
    """Test JSON output formatting."""

    def test_json_schema(self) -> None:
        threads = [
            _make_thread(bot="coderabbitai"),
            _make_thread(bot="claude", thread_id="PRRT_2"),
        ]
        output = json.loads(format_json(threads))
        assert "threads" in output
        assert "summary" in output
        assert output["summary"]["total"] == 2
        assert output["summary"]["by_bot"] == {"claude": 1, "coderabbitai": 1}

    def test_unresolved_count(self) -> None:
        threads = [
            _make_thread(resolved=False),
            _make_thread(resolved=True, thread_id="PRRT_2"),
        ]
        output = json.loads(format_json(threads))
        assert output["summary"]["unresolved"] == 1

    def test_pretty_flag(self) -> None:
        threads = [_make_thread()]
        result = format_json(threads, pretty=True)
        assert "\n" in result
        assert "  " in result

    def test_compact_default(self) -> None:
        threads = [_make_thread()]
        result = format_json(threads, pretty=False)
        assert "\n" not in result

    def test_empty_threads(self) -> None:
        output = json.loads(format_json([]))
        assert output["threads"] == []
        assert output["summary"]["total"] == 0
        assert output["summary"]["unresolved"] == 0
        assert output["summary"]["by_bot"] == {}

    def test_body_preview_truncated_at_parse_time(self) -> None:
        """Body preview should be truncated once at parse time, not again in format_json.

        parse_thread should truncate body_preview to JSON_PREVIEW_LENGTH.
        format_json should pass it through without re-truncating.
        """
        from guardrails.comments import JSON_PREVIEW_LENGTH

        long_body = "x" * (JSON_PREVIEW_LENGTH + 50)
        node = _make_graphql_node(body=long_body)
        parsed = parse_thread(node)
        assert parsed is not None

        # parse_thread should truncate body_preview at parse time
        assert len(parsed["body_preview"]) <= JSON_PREVIEW_LENGTH

        # format_json should not further truncate
        threads = [parsed]
        output = json.loads(format_json(threads))
        json_preview = output["threads"][0]["body_preview"]
        assert json_preview == parsed["body_preview"]


# ---------------------------------------------------------------------------
# _detect_pr_agent
# ---------------------------------------------------------------------------


class TestDetectPrAgent:
    """Test content-based PR-Agent comment detection."""

    def test_detects_pr_agent_marker(self) -> None:
        """Comment body containing 'pr-agent' is detected."""
        assert _detect_pr_agent("This review was generated by PR-Agent.") is True

    def test_detects_qodo_marker(self) -> None:
        """Comment body containing 'qodo' is detected."""
        assert _detect_pr_agent("Powered by Qodo Merge") is True

    def test_detects_review_command(self) -> None:
        """Comment body containing '/review' is detected."""
        assert _detect_pr_agent("Run /review to re-trigger analysis.") is True

    def test_detects_improve_command(self) -> None:
        """Comment body containing '/improve' is detected."""
        assert _detect_pr_agent("Use /improve to get suggestions.") is True

    def test_case_insensitive(self) -> None:
        """Detection is case-insensitive."""
        assert _detect_pr_agent("PR-AGENT review results") is True
        assert _detect_pr_agent("QODO merge output") is True

    def test_rejects_unrelated_comment(self) -> None:
        """Unrelated github-actions comments are not detected as PR-Agent."""
        assert _detect_pr_agent("Deployment successful to staging.") is False

    def test_rejects_empty_body(self) -> None:
        """Empty body is not detected as PR-Agent."""
        assert _detect_pr_agent("") is False


class TestParseThreadPrAgent:
    """Test parse_thread with PR-Agent content-based detection."""

    def test_github_actions_with_pr_agent_body_detected(self) -> None:
        """github-actions[bot] with PR-Agent markers in body sets bot to 'pr-agent'."""
        node = _make_graphql_node(
            author="github-actions[bot]",
            body="## PR-Agent Review\nThis code has issues.",
        )
        result = parse_thread(node)
        assert result is not None
        assert result["bot"] == "pr-agent"

    def test_github_actions_without_pr_agent_body_unchanged(self) -> None:
        """github-actions[bot] without PR-Agent markers keeps 'github-actions' bot name."""
        node = _make_graphql_node(
            author="github-actions[bot]",
            body="Deployment completed successfully.",
        )
        result = parse_thread(node)
        assert result is not None
        assert result["bot"] == "github-actions"

    def test_pr_agent_alias_resolves_for_filtering(self) -> None:
        """The 'pr-agent' alias resolves to 'pr-agent' (the detected bot name)."""
        assert _resolve_bot_name("pr-agent") == "pr-agent"

    def test_filter_by_pr_agent_matches_detected_threads(self) -> None:
        """Filtering by 'pr-agent' matches threads with bot='pr-agent'."""
        threads = [
            _make_thread(bot="pr-agent", thread_id="PRRT_1"),
            _make_thread(bot="github-actions", thread_id="PRRT_2"),
            _make_thread(bot="coderabbitai", thread_id="PRRT_3"),
        ]
        result = filter_threads(threads, bots=["pr-agent"], unresolved_only=False)
        assert len(result) == 1
        assert result[0]["bot"] == "pr-agent"
