#!/usr/bin/env python3
"""
CodeRabbit comment parser for gh-pr-review JSON output.

Extracts actionable tasks from CodeRabbit review comments:
- Inline comments (with file/line)
- Outside diff range comments
- Nitpick comments
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import TextIO


class TaskType(Enum):
    INLINE = "inline"
    OUTSIDE_DIFF = "outside_diff"
    NITPICK = "nitpick"


class Severity(Enum):
    CRITICAL = "critical"  # 🔴
    MAJOR = "major"  # 🟠
    MINOR = "minor"  # 🟡
    SUGGESTION = "suggestion"  # 🟢


@dataclass
class Task:
    id: str
    type: TaskType
    file: str
    line: int | None
    message: str
    severity: Severity
    analysis: str | None = None
    suggested_fix: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "severity": self.severity.value,
            "analysis": self.analysis,
            "suggested_fix": self.suggested_fix,
        }


def parse_severity(text: str) -> Severity:
    """Extract severity from CodeRabbit prefix line."""
    if "🔴" in text or "Critical" in text:
        return Severity.CRITICAL
    if "🟠" in text or "Major" in text:
        return Severity.MAJOR
    if "🟡" in text or "Minor" in text:
        return Severity.MINOR
    return Severity.SUGGESTION


def extract_title_and_body(text: str) -> tuple[str, str]:
    """Extract bold title and remaining body from comment."""
    # Pattern: **title** followed by description
    match = re.search(r"\*\*(.+?)\*\*\s*\n*(.*)", text, re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    # Fallback: first line is title
    lines = text.strip().split("\n", 1)
    return lines[0], lines[1] if len(lines) > 1 else ""


def extract_suggested_fix(text: str) -> str | None:
    """Extract suggested fix from <details> block."""
    # Look for suggested fix in details block
    match = re.search(
        r"<details>\s*<summary>[^<]*(?:Suggested|fix|update)[^<]*</summary>\s*"
        r"(.*?)</details>",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        fix = match.group(1).strip()
        # Extract diff if present
        diff_match = re.search(r"```diff\n(.*?)```", fix, re.DOTALL)
        if diff_match:
            return diff_match.group(1).strip()
        return fix
    return None


def parse_inline_comment(comment: dict, task_num: int) -> Task | None:
    """Parse a single inline comment from gh-pr-review."""
    body = comment.get("body", "")
    path = comment.get("path", "")
    line = comment.get("line")

    if not body or not path:
        return None

    # Skip if it's just a bot summary or not actionable
    if body.startswith("<!-- ") or "Summary by CodeRabbit" in body:
        return None

    severity = parse_severity(body)

    # Remove severity prefix line
    clean_body = re.sub(r"_[⚠️🔴🟠🟡🟢].*?_\s*\|\s*_.*?_\s*\n*", "", body)
    title, description = extract_title_and_body(clean_body)
    suggested_fix = extract_suggested_fix(body)

    return Task(
        id=f"task-{task_num:03d}",
        type=TaskType.INLINE,
        file=path,
        line=line,
        message=title,
        severity=severity,
        analysis=description[:500] if description else None,
        suggested_fix=suggested_fix,
    )


def parse_outside_diff_section(body: str, start_num: int) -> list[Task]:
    """Parse 'Outside diff range comments' section from PR-level body."""
    tasks = []

    # Find the outside diff section
    match = re.search(
        r"<summary>⚠️ Outside diff range comments.*?</summary>\s*<blockquote>(.*?)"
        r"</blockquote>\s*</details>",
        body,
        re.DOTALL,
    )
    if not match:
        return tasks

    section = match.group(1)

    # Parse each file's comments
    file_pattern = re.compile(
        r"<summary>([^<]+)\s*\(\d+\)</summary>\s*<blockquote>(.*?)</blockquote>",
        re.DOTALL,
    )

    for file_match in file_pattern.finditer(section):
        filename = file_match.group(1).strip()
        file_content = file_match.group(2)

        # Parse individual comments within the file
        # Format: `line-range`: **title**
        comment_pattern = re.compile(
            r"`(\d+)(?:-\d+)?`:\s*\*\*(.+?)\*\*\s*\n*(.*?)(?=(?:`\d+|---|\Z))",
            re.DOTALL,
        )

        for comment_match in comment_pattern.finditer(file_content):
            line = int(comment_match.group(1))
            title = comment_match.group(2).strip()
            description = comment_match.group(3).strip()

            suggested_fix = extract_suggested_fix(description)

            tasks.append(
                Task(
                    id=f"task-{start_num + len(tasks):03d}",
                    type=TaskType.OUTSIDE_DIFF,
                    file=filename,
                    line=line,
                    message=title,
                    severity=Severity.MINOR,
                    analysis=description[:500] if description else None,
                    suggested_fix=suggested_fix,
                )
            )

    return tasks


def parse_nitpick_section(body: str, start_num: int) -> list[Task]:
    """Parse 'Nitpick comments' section from PR-level body."""
    tasks = []

    # Find nitpick section
    match = re.search(
        r"<summary>.*?Nitpick.*?</summary>\s*<blockquote>(.*?)</blockquote>",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return tasks

    section = match.group(1)

    # Similar parsing to outside_diff
    file_pattern = re.compile(
        r"<summary>([^<]+)\s*\(\d+\)</summary>\s*<blockquote>(.*?)</blockquote>",
        re.DOTALL,
    )

    for file_match in file_pattern.finditer(section):
        filename = file_match.group(1).strip()
        file_content = file_match.group(2)

        comment_pattern = re.compile(
            r"`(\d+)(?:-\d+)?`:\s*\*\*(.+?)\*\*\s*\n*(.*?)(?=(?:`\d+|---|\Z))",
            re.DOTALL,
        )

        for comment_match in comment_pattern.finditer(file_content):
            line = int(comment_match.group(1))
            title = comment_match.group(2).strip()
            description = comment_match.group(3).strip()

            tasks.append(
                Task(
                    id=f"task-{start_num + len(tasks):03d}",
                    type=TaskType.NITPICK,
                    file=filename,
                    line=line,
                    message=title,
                    severity=Severity.SUGGESTION,
                    analysis=description[:500] if description else None,
                    suggested_fix=extract_suggested_fix(description),
                )
            )

    return tasks


def parse_reviews(data: dict) -> list[Task]:
    """Parse all reviews from gh-pr-review JSON output."""
    tasks = []
    task_num = 1

    for review in data.get("reviews", []):
        # Parse inline comments
        for comment in review.get("comments", []):
            task = parse_inline_comment(comment, task_num)
            if task:
                tasks.append(task)
                task_num += 1

        # Parse PR-level body for outside_diff and nitpick
        body = review.get("body", "")
        if body:
            outside_tasks = parse_outside_diff_section(body, task_num)
            tasks.extend(outside_tasks)
            task_num += len(outside_tasks)

            nitpick_tasks = parse_nitpick_section(body, task_num)
            tasks.extend(nitpick_tasks)
            task_num += len(nitpick_tasks)

    return tasks


def generate_output(tasks: list[Task]) -> dict:
    """Generate final output JSON."""
    summary = {
        "total": len(tasks),
        "inline": sum(1 for t in tasks if t.type == TaskType.INLINE),
        "outside_diff": sum(1 for t in tasks if t.type == TaskType.OUTSIDE_DIFF),
        "nitpick": sum(1 for t in tasks if t.type == TaskType.NITPICK),
        "by_severity": {
            "critical": sum(1 for t in tasks if t.severity == Severity.CRITICAL),
            "major": sum(1 for t in tasks if t.severity == Severity.MAJOR),
            "minor": sum(1 for t in tasks if t.severity == Severity.MINOR),
            "suggestion": sum(1 for t in tasks if t.severity == Severity.SUGGESTION),
        },
    }

    return {"tasks": [t.to_dict() for t in tasks], "summary": summary}


def parse_file(input_file: TextIO) -> dict:
    """Parse gh-pr-review JSON from file or stdin."""
    data = json.load(input_file)
    tasks = parse_reviews(data)
    return generate_output(tasks)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse CodeRabbit comments from gh-pr-review JSON output",
        epilog="Example: gh pr-review review view --pr 1 | ai-review-tasks",
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Input JSON file (default: stdin)",
    )
    parser.add_argument(
        "--pretty", "-p", action="store_true", help="Pretty-print JSON output"
    )
    parser.add_argument(
        "--severity",
        "-s",
        choices=["critical", "major", "minor", "suggestion"],
        help="Filter by minimum severity",
    )

    args = parser.parse_args()

    try:
        result = parse_file(args.input)

        # Filter by severity if requested
        if args.severity:
            severity_order = ["critical", "major", "minor", "suggestion"]
            min_idx = severity_order.index(args.severity)
            result["tasks"] = [
                t
                for t in result["tasks"]
                if severity_order.index(t["severity"]) <= min_idx
            ]
            # Recalculate summary
            result["summary"]["total"] = len(result["tasks"])

        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent))  # noqa: T201

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
