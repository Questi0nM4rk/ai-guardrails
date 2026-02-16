"""Universal PR review comments — list, reply, and resolve threads from all bots.

Supports CodeRabbit, Claude, Gemini, and DeepSource review threads.
Uses GitHub GraphQL API for fetching/resolving threads and REST API for replies.

Usage::

    ai-guardrails comments --pr 31
    ai-guardrails comments --pr 31 --bot claude
    ai-guardrails comments --pr 31 --reply PRRT_abc "Fixed."
    ai-guardrails comments --pr 31 --resolve PRRT_abc "Fixed."
    ai-guardrails comments --pr 31 --resolve-all --bot deepsource "Config updated."
    ai-guardrails comments --pr 31 --json
"""

from __future__ import annotations

import json
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMPACT_PREVIEW_LENGTH = 80
JSON_PREVIEW_LENGTH = 120

BOT_ALIASES: dict[str, str] = {
    "coderabbit": "coderabbitai",
    "deepsource": "deepsource-io",
    "gemini": "gemini-code-assist",
    "claude": "claude",
}

# Reverse mapping: full login -> short alias (for compact display)
_LOGIN_TO_ALIAS: dict[str, str] = {v: k for k, v in BOT_ALIASES.items()}

GRAPHQL_THREADS_QUERY = """
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 5) {
            totalCount
            nodes {
              id
              databaseId
              author { login }
              body
              path
              line
              startLine
              createdAt
            }
          }
        }
      }
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Thread parsing
# ---------------------------------------------------------------------------


def _clean_body(body: str) -> str:
    """Strip HTML tags and collapse whitespace for preview."""
    import re

    text = re.sub(r"<[^>]*>", "", body)
    text = re.sub(r"\n+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _truncate(text: str, length: int) -> str:
    """Truncate text to length with ellipsis."""
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."


def _short_bot_name(login: str) -> str:
    """Convert full bot login to short alias for display."""
    return _LOGIN_TO_ALIAS.get(login, login)


def parse_thread(node: dict) -> dict | None:
    """Parse a GraphQL reviewThread node into a flat dict.

    Returns None if the thread has no comments.
    """
    comments = node.get("comments", {}).get("nodes", [])
    if not comments:
        return None

    first = comments[0]
    author = first.get("author", {}).get("login", "unknown")
    raw_body = first.get("body", "")

    return {
        "thread_id": node.get("id", ""),
        "comment_id": first.get("databaseId"),
        "bot": author.removesuffix("[bot]"),
        "path": first.get("path", ""),
        "line": first.get("line"),
        "start_line": first.get("startLine"),
        "resolved": node.get("isResolved", False),
        "body_preview": _clean_body(raw_body),
        "created_at": first.get("createdAt", ""),
        "reply_count": node.get("comments", {}).get("totalCount", 1) - 1,
    }


def _resolve_bot_name(name: str) -> str:
    """Resolve a bot alias or full name to the GitHub login."""
    lower = name.lower().removesuffix("[bot]")
    if lower in BOT_ALIASES:
        return BOT_ALIASES[lower]
    # Check if it's already a full login
    for login in BOT_ALIASES.values():
        if lower == login.lower():
            return login
    return lower


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def filter_threads(
    threads: list[dict],
    *,
    bots: list[str] | None = None,
    unresolved_only: bool = True,
) -> list[dict]:
    """Filter threads by bot name and resolution status."""
    result = threads

    if unresolved_only:
        result = [t for t in result if not t["resolved"]]

    if bots:
        resolved_names = {_resolve_bot_name(b) for b in bots}
        result = [t for t in result if t["bot"] in resolved_names]

    return result


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _build_summary(threads: list[dict]) -> dict:
    """Build summary statistics from thread list."""
    by_bot: dict[str, int] = {}
    unresolved = 0
    for t in threads:
        bot = t["bot"]
        by_bot[bot] = by_bot.get(bot, 0) + 1
        if not t["resolved"]:
            unresolved += 1
    return {
        "total": len(threads),
        "unresolved": unresolved,
        "by_bot": dict(sorted(by_bot.items())),
    }


def format_compact(threads: list[dict]) -> str:
    """Format threads as compact one-line-per-thread output.

    Example::

        # 60 unresolved | claude: 11, deepsource: 43, gemini: 5, coderabbit: 1

        PRRT_kwDO...eFH  deepsource  core.py:48       line too long (99 > 88 characters)
        PRRT_kwDO...qNJ  claude      python.py:20     Code duplication: This _fail_no_uv...
    """
    summary = _build_summary(threads)
    bot_counts = ", ".join(
        f"{_short_bot_name(bot)}: {count}" for bot, count in summary["by_bot"].items()
    )

    lines = [f"# {summary['unresolved']} unresolved | {bot_counts}", ""]

    for t in threads:
        tid = t["thread_id"]
        bot = _short_bot_name(t["bot"])
        path = t["path"].rsplit("/", 1)[-1] if t["path"] else "?"
        loc = f"{path}:{t['line']}" if t["line"] else path
        preview = _truncate(t["body_preview"], COMPACT_PREVIEW_LENGTH)
        resolved = " [resolved]" if t["resolved"] else ""

        lines.append(f"{tid}  {bot:<12s} {loc:<20s} {preview}{resolved}")

    return "\n".join(lines)


def format_json(threads: list[dict], *, pretty: bool = False) -> str:
    """Format threads as JSON with summary statistics."""
    summary = _build_summary(threads)

    # Truncate body previews for JSON output
    json_threads = []
    for t in threads:
        t_copy = dict(t)
        t_copy["body_preview"] = _truncate(t["body_preview"], JSON_PREVIEW_LENGTH)
        json_threads.append(t_copy)

    output = {"threads": json_threads, "summary": summary}
    indent = 2 if pretty else None
    return json.dumps(output, indent=indent)


# ---------------------------------------------------------------------------
# GitHub API interactions
# ---------------------------------------------------------------------------


def _get_pr_number() -> int | None:
    """Get PR number from current branch via gh CLI."""
    import subprocess

    result = subprocess.run(
        ["gh", "pr", "view", "--json", "number", "--jq", ".number"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def _get_repo_info() -> tuple[str, str] | None:
    """Get (owner, repo) from current git context via gh CLI."""
    import subprocess

    result = subprocess.run(
        ["gh", "repo", "view", "--json", "owner,name", "--jq", r'"\(.owner.login) \(.name)"'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    parts = result.stdout.strip().split()
    expected_parts = 2
    if len(parts) != expected_parts:
        return None
    return (parts[0], parts[1])


def fetch_threads(owner: str, repo: str, pr: int) -> list[dict]:
    """Fetch all review threads via GraphQL.

    Returns parsed thread dicts (not filtered by bot or resolution status).
    """
    import subprocess

    jq_filter = ".data.repository.pullRequest.reviewThreads.nodes"
    result = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={GRAPHQL_THREADS_QUERY}",
            "-f",
            f"owner={owner}",
            "-f",
            f"repo={repo}",
            "-F",
            f"pr={pr}",
            "--jq",
            jq_filter,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("Warning: Failed to fetch review threads via GraphQL", file=sys.stderr)
        return []

    try:
        raw_nodes = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        print("Warning: Invalid JSON from GraphQL response", file=sys.stderr)
        return []

    threads = []
    for node in raw_nodes:
        parsed = parse_thread(node)
        if parsed:
            threads.append(parsed)
    return threads


def reply_to_thread(owner: str, repo: str, pr: int, comment_id: int, body: str) -> bool:
    """Reply to a review comment via REST API.

    Returns True on success, False on failure.
    """
    import subprocess

    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies",
            "-f",
            f"body={body}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Error: Failed to reply to comment {comment_id}", file=sys.stderr)
        return False
    return True


def resolve_thread(thread_id: str) -> bool:
    """Resolve a review thread via GraphQL mutation.

    Returns True on success, False on failure.
    """
    import subprocess

    mutation = """
    mutation($threadId: ID!) {
      resolveReviewThread(input: {threadId: $threadId}) {
        thread { isResolved }
      }
    }
    """
    result = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-f",
            f"threadId={thread_id}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Error: Failed to resolve thread {thread_id}", file=sys.stderr)
        return False
    return True


def resolve_threads(
    owner: str,
    repo: str,
    pr: int,
    threads: list[dict],
    *,
    reply_body: str | None = None,
) -> tuple[int, int]:
    """Resolve multiple threads, optionally replying first.

    Returns (resolved_count, failed_count).
    """
    resolved = 0
    failed = 0
    for thread in threads:
        if thread["resolved"]:
            continue

        if reply_body and thread["comment_id"]:
            reply_to_thread(owner, repo, pr, thread["comment_id"], reply_body)

        if resolve_thread(thread["thread_id"]):
            resolved += 1
        else:
            failed += 1

    return resolved, failed


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_comments(
    *,
    pr: int | None = None,
    bot: str | None = None,
    reply: tuple[str, str] | None = None,
    resolve: tuple[str, str | None] | None = None,
    resolve_all: bool = False,
    show_all: bool = False,
    output_json: bool = False,
) -> int:
    """Main entry point for the ``comments`` subcommand.

    Args:
        pr: PR number (default: current branch's PR).
        bot: Comma-separated bot filter (e.g. "coderabbit,claude").
        reply: (thread_id, body) tuple for replying to a thread.
        resolve: (thread_id, optional_body) tuple for resolving a thread.
        resolve_all: Resolve all unresolved threads (filtered by --bot).
        show_all: Show resolved threads too.
        output_json: Output full JSON instead of compact format.

    Returns:
        Exit code (0 success, 1 error).

    """
    # Get PR number
    if pr is None:
        pr = _get_pr_number()
        if pr is None:
            print("Error: No PR found for current branch. Use --pr NUMBER", file=sys.stderr)
            return 1

    # Get repo info
    repo_info = _get_repo_info()
    if repo_info is None:
        print("Error: Could not determine repository info", file=sys.stderr)
        return 1
    owner, repo = repo_info

    # Parse bot filter
    bot_list = [b.strip() for b in bot.split(",")] if bot else None

    # Fetch all threads
    all_threads = fetch_threads(owner, repo, pr)

    # Handle reply action
    if reply is not None:
        thread_id, body = reply
        target = next((t for t in all_threads if t["thread_id"] == thread_id), None)
        if target is None:
            print(f"Error: Thread {thread_id} not found", file=sys.stderr)
            return 1
        if target["comment_id"] is None:
            print("Error: Thread has no comment ID for reply", file=sys.stderr)
            return 1
        ok = reply_to_thread(owner, repo, pr, target["comment_id"], body)
        return 0 if ok else 1

    # Handle resolve action
    if resolve is not None:
        thread_id, body = resolve
        target = next((t for t in all_threads if t["thread_id"] == thread_id), None)
        if target is None:
            print(f"Error: Thread {thread_id} not found", file=sys.stderr)
            return 1
        if body and target["comment_id"]:
            reply_to_thread(owner, repo, pr, target["comment_id"], body)
        ok = resolve_thread(thread_id)
        return 0 if ok else 1

    # Handle resolve-all action
    if resolve_all:
        filtered = filter_threads(all_threads, bots=bot_list, unresolved_only=True)
        if not filtered:
            print("No unresolved threads to resolve", file=sys.stderr)
            return 0
        resolved, failed = resolve_threads(owner, repo, pr, filtered)
        print(f"Resolved {resolved} thread(s), {failed} failed", file=sys.stderr)
        return 0 if failed == 0 else 1

    # Default: list threads
    filtered = filter_threads(all_threads, bots=bot_list, unresolved_only=not show_all)
    if output_json:
        print(format_json(filtered, pretty=True))
    else:
        print(format_compact(filtered))
    return 0
