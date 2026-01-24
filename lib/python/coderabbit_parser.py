#!/usr/bin/env python3
"""CodeRabbit comment parser for gh pr view JSON output.

Extracts actionable tasks from CodeRabbit review comments organized into three sections:
- 🤖 Fix all issues with AI agents (AI-ready prompts)
- ⚠️ Outside diff range comments (comments outside changed lines)
- 🧹 Nitpick comments (optional improvements)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import TextIO


class TaskType(Enum):
    """Task type based on CodeRabbit section."""

    AI_PROMPT = "ai_prompt"  # From 🤖 Fix all issues
    OUTSIDE_DIFF = "outside_diff"  # From ⚠️ Outside diff
    NITPICK = "nitpick"  # From 🧹 Nitpick comments


class Severity(Enum):
    """Task severity level."""

    MAJOR = "major"  # Actionable issues (ai_prompt)
    MINOR = "minor"  # Outside diff comments
    SUGGESTION = "suggestion"  # Nitpick comments


@dataclass
class Task:
    """Represents a single actionable task from CodeRabbit."""

    id: str
    type: TaskType
    file: str
    line_range: str
    message: str
    severity: Severity
    description: str | None = None

    def to_dict(self) -> dict:
        """Convert task to dictionary for JSON output."""
        result = {
            "id": self.id,
            "type": self.type.value,
            "file": self.file,
            "line_range": self.line_range,
            "message": self.message,
            "severity": self.severity.value,
        }
        if self.description:
            result["description"] = self.description
        return result


def strip_blockquote_prefixes(text: str) -> str:
    """Strip '> ' prefixes from GitHub blockquote markdown.

    Args:
        text: Markdown text with potential blockquote prefixes

    Returns:
        Text with blockquote prefixes removed
    """
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        # Strip leading '> ' prefixes (can be nested)
        while line.startswith("> "):
            line = line[2:]
        # Also handle bare '>' without space
        if line == ">":
            line = ""
        cleaned.append(line)
    return "\n".join(cleaned)


def extract_ai_prompts(body: str) -> list[Task]:
    """Extract tasks from '🤖 Fix all issues with AI agents' section.

    Args:
        body: CodeRabbit review body (after stripping blockquote prefixes)

    Returns:
        List of AI prompt tasks
    """
    pattern = re.compile(
        r"<details>\s*<summary>🤖\s*Fix all issues with AI agents</summary>\s*````\s*(.*?)\s*````\s*</details>",
        re.DOTALL,
    )

    match = pattern.search(body)
    if not match:
        return []

    ai_block = match.group(1)

    # Split by file sections: In `@filename`:
    file_sections = re.split(r"In `@([^`]+)`:", ai_block)

    tasks = []
    # file_sections[0] is empty, then [1]=filename, [2]=content, [3]=filename, [4]=content...
    for i in range(1, len(file_sections), 2):
        filename = file_sections[i].strip()
        content = file_sections[i + 1].strip()

        # Extract issues (lines starting with "- Around line")
        issue_pattern = re.compile(
            r"- Around line (\d+)-(\d+): (.+?)(?=\n- Around line|\Z)", re.DOTALL
        )

        for issue_match in issue_pattern.finditer(content):
            start_line = issue_match.group(1)
            end_line = issue_match.group(2)
            description = issue_match.group(3).strip()

            tasks.append(
                Task(
                    id="",  # Will be assigned later
                    type=TaskType.AI_PROMPT,
                    file=filename,
                    line_range=f"{start_line}-{end_line}",
                    message=description,
                    severity=Severity.MAJOR,
                )
            )

    return tasks


def extract_file_blocks(section: str, task_type: TaskType) -> list[Task]:
    """Extract tasks from file-based sections (outside_diff or nitpick).

    Args:
        section: HTML content of the section
        task_type: TaskType.OUTSIDE_DIFF or TaskType.NITPICK

    Returns:
        List of extracted tasks
    """
    tasks = []

    # Find all file summary lines
    file_summary_pattern = re.compile(r"<summary>([^<(]+?)\s*\(\d+\)</summary>")
    matches = list(file_summary_pattern.finditer(section))

    # Determine severity based on task type
    severity = (
        Severity.MINOR if task_type == TaskType.OUTSIDE_DIFF else Severity.SUGGESTION
    )

    for i, summary_match in enumerate(matches):
        filename = summary_match.group(1).strip()

        # Get content from end of summary to start of next summary (or end of section)
        start_pos = summary_match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        file_content = section[start_pos:end_pos]

        # Parse comments in file: `123-456`: **Title**
        comment_pattern = re.compile(r"`(\d+(?:-\d+)?)`:\s*\*\*(.+?)\*\*", re.DOTALL)

        for comment_match in comment_pattern.finditer(file_content):
            line_range = comment_match.group(1)
            title = comment_match.group(2).strip()

            # Extract description (everything after title until next comment or end)
            desc_start = comment_match.end()
            next_comment = comment_pattern.search(file_content, desc_start)
            desc_end = next_comment.start() if next_comment else len(file_content)

            description = file_content[desc_start:desc_end].strip()

            # Remove nested <details> blocks from description (suggested fixes, etc.)
            description = re.sub(
                r"<details>.*?</details>", "", description, flags=re.DOTALL
            ).strip()

            # Remove markdown artifacts
            description = description.replace("</blockquote>", "").strip()

            tasks.append(
                Task(
                    id="",  # Will be assigned later
                    type=task_type,
                    file=filename,
                    line_range=line_range,
                    message=title,
                    severity=severity,
                    description=description[:500] if description else None,
                )
            )

    return tasks


def extract_outside_diff(body: str) -> list[Task]:
    """Extract tasks from '⚠️ Outside diff range comments' sections.

    Args:
        body: CodeRabbit review body (after stripping blockquote prefixes)

    Returns:
        List of outside diff tasks
    """
    tasks = []

    # Find all outside diff sections (may be multiple)
    sections = re.finditer(
        r"<summary>⚠️\s*Outside diff range comments.*?</summary><blockquote>(.*?)</blockquote>\s*</details>",
        body,
        re.DOTALL,
    )

    for section_match in sections:
        section_content = section_match.group(1)
        tasks.extend(extract_file_blocks(section_content, TaskType.OUTSIDE_DIFF))

    return tasks


def extract_nitpicks(body: str) -> list[Task]:
    """Extract tasks from '🧹 Nitpick comments' sections.

    Args:
        body: CodeRabbit review body (after stripping blockquote prefixes)

    Returns:
        List of nitpick tasks
    """
    tasks = []

    # Find all nitpick sections (may be multiple)
    sections = re.finditer(
        r"<summary>🧹\s*Nitpick comments.*?</summary><blockquote>(.*?)</blockquote>\s*</details>",
        body,
        re.DOTALL,
    )

    for section_match in sections:
        section_content = section_match.group(1)
        tasks.extend(extract_file_blocks(section_content, TaskType.NITPICK))

    return tasks


def parse_review_body(body: str) -> list[Task]:
    """Parse CodeRabbit review body and extract all tasks.

    Args:
        body: Review body from gh pr view --json reviews

    Returns:
        List of all extracted tasks with assigned IDs
    """
    # Strip blockquote prefixes first (gh-pr-review wraps in markdown blockquotes)
    clean_body = strip_blockquote_prefixes(body)

    # Extract tasks from all three sections
    tasks = []
    tasks.extend(extract_ai_prompts(clean_body))
    tasks.extend(extract_outside_diff(clean_body))
    tasks.extend(extract_nitpicks(clean_body))

    # Assign sequential IDs
    for i, task in enumerate(tasks, start=1):
        task.id = f"task-{i:03d}"

    return tasks


def generate_output(tasks: list[Task]) -> dict:
    """Generate final output JSON.

    Args:
        tasks: List of extracted tasks

    Returns:
        Dictionary with tasks and summary for JSON output
    """
    summary = {
        "total": len(tasks),
        "ai_prompts": sum(1 for t in tasks if t.type == TaskType.AI_PROMPT),
        "outside_diff": sum(1 for t in tasks if t.type == TaskType.OUTSIDE_DIFF),
        "nitpicks": sum(1 for t in tasks if t.type == TaskType.NITPICK),
        "by_severity": {
            "major": sum(1 for t in tasks if t.severity == Severity.MAJOR),
            "minor": sum(1 for t in tasks if t.severity == Severity.MINOR),
            "suggestion": sum(1 for t in tasks if t.severity == Severity.SUGGESTION),
        },
    }

    return {"tasks": [t.to_dict() for t in tasks], "summary": summary}


def parse_file(input_file: TextIO) -> dict:
    """Parse CodeRabbit review from file or stdin.

    Expects JSON with reviews array containing CodeRabbit review body.

    Args:
        input_file: File object to read from

    Returns:
        Dictionary with tasks and summary
    """
    data = json.load(input_file)

    # Extract review body from JSON
    # Expected format: {"reviews": [{"author": {"login": "coderabbitai"}, "body": "..."}]}
    review_body = None

    if isinstance(data, dict) and "reviews" in data:
        # gh pr view --json reviews format
        for review in data.get("reviews", []):
            author_login = review.get("author", {}).get("login", "")
            if "coderabbitai" in author_login.lower():
                review_body = review.get("body", "")
                break
    elif isinstance(data, str):
        # Plain review body text
        review_body = data
    else:
        # Try to extract body directly if it's a review object
        author_login = data.get("author", {}).get("login", "")
        if "coderabbitai" in author_login.lower():
            review_body = data.get("body", "")

    if not review_body:
        return {
            "tasks": [],
            "summary": {
                "total": 0,
                "ai_prompts": 0,
                "outside_diff": 0,
                "nitpicks": 0,
                "by_severity": {"major": 0, "minor": 0, "suggestion": 0},
            },
        }

    tasks = parse_review_body(review_body)
    return generate_output(tasks)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse CodeRabbit comments from gh pr view JSON output",
        epilog="Example: gh pr view 1 --json reviews | ai-review-tasks --pretty",
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
        choices=["major", "minor", "suggestion"],
        help="Filter by minimum severity",
    )

    args = parser.parse_args()

    try:
        result = parse_file(args.input)

        # Filter by severity if requested
        if args.severity:
            severity_order = ["major", "minor", "suggestion"]
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
