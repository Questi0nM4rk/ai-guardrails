#!/usr/bin/env python3
"""CodeRabbit review parser.

Parses CodeRabbit feedback from two sources:
1. Review thread comments (GraphQL reviewThreads) - inline code comments
2. Review body summaries (🧹 Nitpicks, ⚠️ Outside diff)

Input format (from ai-review-tasks):
{
  "threads": [
    {
      "path": "path/to/file.py",
      "line": 42,
      "startLine": 40,
      "body": "_⚠️ Potential issue_ | _🟠 Major_\\n\\n**Title**\\n\\nDescription..."
    }
  ],
  "review_bodies": [
    "Full review body text with 🧹, ⚠️, 🤖 sections..."
  ]
}
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import TextIO


class Severity(Enum):
    """Task severity level extracted from comment body."""

    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


class TaskSource(Enum):
    """Source of the task - which CodeRabbit section it came from."""

    THREAD = "thread"  # GraphQL reviewThreads (inline comments with AI prompts)
    NITPICK = "nitpick"  # 🧹 Nitpick comments section
    OUTSIDE_DIFF = "outside_diff"  # ⚠️ Outside diff range comments


@dataclass
class Task:
    """Represents a single actionable task from CodeRabbit review."""

    id: str
    file: str
    line: int
    title: str
    severity: Severity
    source: TaskSource = TaskSource.THREAD
    start_line: int | None = None
    line_range: str | None = None  # Original "40-50" format from body summaries
    ai_prompt: str | None = None
    description: str | None = None

    def to_dict(self) -> dict:
        """Convert task to dictionary for JSON output."""
        result: dict = {
            "id": self.id,
            "file": self.file,
            "line": self.line,
            "title": self.title,
            "severity": self.severity.value,
            "source": self.source.value,
        }
        if self.start_line is not None:
            result["start_line"] = self.start_line
        if self.line_range:
            result["line_range"] = self.line_range
        if self.ai_prompt:
            result["ai_prompt"] = self.ai_prompt
        if self.description:
            result["description"] = self.description
        return result


def extract_severity(body: str) -> Severity:
    """Extract severity from comment body first line.

    CodeRabbit format: _⚠️ Potential issue_ | _🟠 Major_

    Args:
        body: Full comment body text

    Returns:
        Detected severity level
    """
    first_line = body.split("\n")[0] if body else ""
    first_line_lower = first_line.lower()

    if "🟠" in first_line or "major" in first_line_lower:
        return Severity.MAJOR
    if "🟡" in first_line or "minor" in first_line_lower:
        return Severity.MINOR
    return Severity.SUGGESTION


def extract_title(body: str) -> str:
    """Extract title from **bold text** in comment body.

    Args:
        body: Full comment body text

    Returns:
        Extracted title or fallback text
    """
    # Find first **bold** text that's on its own line (the title)
    match = re.search(r"^\*\*([^*]+)\*\*\s*$", body, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Fallback: any bold text
    match = re.search(r"\*\*([^*]+)\*\*", body)
    if match:
        return match.group(1).strip()

    return "Untitled issue"


def extract_ai_prompt(body: str) -> str | None:
    """Extract AI-ready prompt from details block.

    CodeRabbit includes prompts in:
    <details><summary>🤖 Prompt for AI Agents</summary>
    ```
    prompt text here
    ```
    </details>

    Args:
        body: Full comment body text

    Returns:
        Extracted prompt text or None
    """
    # Match 3 or 4 backticks (CodeRabbit uses both formats)
    pattern = re.compile(
        r"<details>\s*<summary>🤖\s*Prompt for AI Agents</summary>\s*(`{3,4})[^\n]*\n(.*?)\1\s*</details>",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(body)
    if match:
        return match.group(2).strip()
    return None


def extract_description(body: str) -> str | None:
    """Extract description from comment body.

    Description is the text between the title and any details blocks,
    excluding the severity line.

    Args:
        body: Full comment body text

    Returns:
        Cleaned description text or None
    """
    # Remove severity line (first line)
    lines = body.split("\n")
    if lines:
        lines = lines[1:]
    text = "\n".join(lines)

    # Remove details blocks (non-greedy: stops at first </details>)
    # Note: Nested <details> blocks would be partially removed. This is acceptable
    # because CodeRabbit rarely nests details in descriptions, and description is
    # supplementary text. If this becomes an issue, consider using an HTML parser.
    text = re.sub(r"<details>.*?</details>", "", text, flags=re.DOTALL)

    # Remove the title line
    text = re.sub(r"^\*\*[^*]+\*\*\s*$", "", text, flags=re.MULTILINE)

    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if not text:
        return None

    # Truncate if too long
    if len(text) > 500:
        text = text[:497] + "..."

    return text


# =============================================================================
# Review Body Summary Parsing (🧹 Nitpicks, ⚠️ Outside diff, 🤖 AI prompts)
# =============================================================================


def strip_blockquote_prefixes(text: str) -> str:
    """Remove blockquote prefixes (> ) from text lines.

    Outside diff sections are often quoted with > prefixes.

    Args:
        text: Text potentially with blockquote prefixes

    Returns:
        Text with prefixes stripped
    """
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        # Strip leading > and optional space, repeatedly for nested quotes
        while line.startswith(">"):
            line = line[1:].lstrip(" ")
        cleaned.append(line)
    return "\n".join(cleaned)


def parse_line_range(line_range: str) -> tuple[int, int]:
    """Parse line range string into start and end line numbers.

    Args:
        line_range: String like "40-50" or "42"

    Returns:
        Tuple of (start_line, end_line)
    """
    line_range = line_range.strip().strip("`")
    if "-" in line_range:
        parts = line_range.split("-", 1)
        start = int(parts[0].strip())
        end = int(parts[1].strip())
        return (start, end)
    line_num = int(line_range)
    return (line_num, line_num)


def extract_section_content(body: str, section_emoji: str) -> str | None:
    """Extract content from a specific section in review body.

    Args:
        body: Full review body text
        section_emoji: Emoji marker (🧹, ⚠️, or 🤖)

    Returns:
        Section content or None if not found
    """
    # Map emoji to section title patterns
    section_patterns = {
        "🧹": r"🧹\s*Nitpick comments?\s*\(\d+\)",
        "⚠️": r"⚠️\s*Outside diff range comments?\s*\(\d+\)",
        "🤖": r"🤖\s*Fix all issues with AI agents",
    }

    pattern = section_patterns.get(section_emoji)
    if not pattern:
        return None

    # Find the section start
    match = re.search(
        rf"<summary>{pattern}</summary>\s*<blockquote>",
        body,
        re.IGNORECASE,
    )
    if not match:
        # Try without <blockquote> for 🤖 section which uses code blocks
        if section_emoji == "🤖":
            match = re.search(rf"<summary>{pattern}</summary>", body, re.IGNORECASE)
            if match:
                # Find the closing </details> for AI prompt section
                start = match.end()
                end_match = re.search(r"</details>", body[start:])
                if end_match:
                    return body[start : start + end_match.start()]
        return None

    # Find matching closing tags - need to handle nesting
    start = match.end()
    depth = 1
    pos = start

    while depth > 0 and pos < len(body):
        next_open = body.find("<details>", pos)
        next_close = body.find("</details>", pos)

        if next_close == -1:
            break

        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + len("<details>")
        else:
            depth -= 1
            if depth == 0:
                # Find the </blockquote> before </details>
                content = body[start:next_close]
                # Remove trailing </blockquote>
                if content.rstrip().endswith("</blockquote>"):
                    content = content.rstrip()[: -len("</blockquote>")]
                return content
            pos = next_close + len("</details>")

    return None


def extract_file_blocks(section_content: str) -> list[tuple[str, str]]:
    """Extract file blocks from section content.

    Args:
        section_content: Content inside a section (between <blockquote> tags)

    Returns:
        List of (filename, block_content) tuples
    """
    results = []

    # Pattern to match file blocks: <summary>FILENAME (N)</summary><blockquote>
    file_pattern = re.compile(
        r"<details>\s*<summary>([^<(]+?)\s*\(\d+\)</summary>\s*<blockquote>(.*?)</blockquote>\s*</details>",
        re.DOTALL,
    )

    for match in file_pattern.finditer(section_content):
        filename = match.group(1).strip()
        content = match.group(2).strip()
        results.append((filename, content))

    return results


def parse_body_item(
    file: str,
    item_text: str,
    source: TaskSource,
    default_severity: Severity,
) -> Task | None:
    """Parse a single item from a file block.

    Args:
        file: Filename this item belongs to
        item_text: Text containing `line-range`: **title** and description
        source: TaskSource for this item
        default_severity: Default severity for this source type

    Returns:
        Parsed Task or None if invalid
    """
    # Pattern: `LINE-RANGE`: **TITLE**
    match = re.match(r"`([^`]+)`:\s*\*\*([^*]+)\*\*", item_text.strip())
    if not match:
        return None

    line_range_str = match.group(1)
    title = match.group(2).strip()

    try:
        start_line, end_line = parse_line_range(line_range_str)
    except ValueError:
        return None

    # Description is everything after the title line
    description = item_text[match.end() :].strip()

    # Remove nested details blocks (suggested fixes)
    description = re.sub(r"<details>.*?</details>", "", description, flags=re.DOTALL)
    description = description.strip()

    if not description:
        description = None
    elif len(description) > 500:
        description = description[:497] + "..."

    return Task(
        id="",  # Assigned later
        file=file,
        line=end_line,
        start_line=start_line if start_line != end_line else None,
        line_range=line_range_str,
        title=title,
        severity=default_severity,
        source=source,
        description=description,
    )


def parse_file_block_items(file: str, content: str) -> list[tuple[str, str]]:
    """Split file block content into individual items.

    Args:
        file: Filename
        content: Block content with multiple `line`: **title** items

    Returns:
        List of (file, item_text) tuples
    """
    # Split on backtick-line patterns, keeping the delimiter
    items = re.split(r"(?=`\d)", content)
    results = []
    for item in items:
        item = item.strip()
        if item and re.match(r"`\d", item):
            results.append((file, item))
    return results


def parse_review_body(body: str) -> list[Task]:
    """Parse review body for 🧹, ⚠️, 🤖 sections.

    Args:
        body: Full review body text

    Returns:
        List of parsed tasks (without IDs assigned)
    """
    tasks: list[Task] = []

    # Strip blockquote prefixes
    body = strip_blockquote_prefixes(body)

    # Section configs: (emoji, source, default_severity)
    sections = [
        ("🧹", TaskSource.NITPICK, Severity.SUGGESTION),
        ("⚠️", TaskSource.OUTSIDE_DIFF, Severity.MINOR),
    ]

    for emoji, source, default_severity in sections:
        section_content = extract_section_content(body, emoji)
        if not section_content:
            continue

        file_blocks = extract_file_blocks(section_content)
        for filename, block_content in file_blocks:
            items = parse_file_block_items(filename, block_content)
            for file, item_text in items:
                task = parse_body_item(file, item_text, source, default_severity)
                if task:
                    tasks.append(task)

    # Note: 🤖 AI prompts section is NOT parsed from body summaries.
    # AI prompts are extracted from thread comment bodies via extract_ai_prompt().
    # Thread comments contain the same prompts with full context (file, line, severity),
    # making body section parsing redundant.

    return tasks


# =============================================================================
# Review Thread Parsing (GraphQL reviewThreads)
# =============================================================================


def parse_thread(thread: dict) -> Task | None:
    """Parse a single review thread into a Task.

    Args:
        thread: Thread dict with path, line, startLine, body

    Returns:
        Parsed Task or None if invalid
    """
    body = thread.get("body", "")
    if not body:
        return None

    path = thread.get("path", "")
    if not path:
        return None

    line = thread.get("line")
    if line is None:
        return None

    return Task(
        id="",  # Assigned later
        file=path,
        line=line,
        start_line=thread.get("startLine"),
        title=extract_title(body),
        severity=extract_severity(body),
        source=TaskSource.THREAD,
        ai_prompt=extract_ai_prompt(body),
        description=extract_description(body),
    )


def parse_threads(data: dict) -> list[Task]:
    """Parse all threads from input JSON.

    Args:
        data: Input JSON with "threads" array

    Returns:
        List of parsed tasks with assigned IDs
    """
    threads = data.get("threads", [])
    tasks: list[Task] = []

    for thread in threads:
        task = parse_thread(thread)
        if task:
            tasks.append(task)

    return tasks


def generate_output(tasks: list[Task]) -> dict:
    """Generate final output JSON with tasks and summary.

    Args:
        tasks: List of parsed tasks

    Returns:
        Output dict with tasks array and summary
    """
    # Count by file
    by_file: Counter[str] = Counter()
    for task in tasks:
        by_file[task.file] += 1

    summary = {
        "total": len(tasks),
        "by_severity": {
            "major": sum(1 for t in tasks if t.severity == Severity.MAJOR),
            "minor": sum(1 for t in tasks if t.severity == Severity.MINOR),
            "suggestion": sum(1 for t in tasks if t.severity == Severity.SUGGESTION),
        },
        "by_source": {
            "thread": sum(1 for t in tasks if t.source == TaskSource.THREAD),
            "nitpick": sum(1 for t in tasks if t.source == TaskSource.NITPICK),
            "outside_diff": sum(
                1 for t in tasks if t.source == TaskSource.OUTSIDE_DIFF
            ),
        },
        "by_file": dict(by_file),
    }

    return {"tasks": [t.to_dict() for t in tasks], "summary": summary}


def dedup_key(task: Task) -> tuple[str, int, str]:
    """Generate deduplication key for a task.

    Args:
        task: Task to generate key for

    Returns:
        Tuple of (file, line_start, normalized_title)
    """
    line_start = task.start_line or task.line
    title_norm = task.title.lower().strip()[:50]
    return (task.file, line_start, title_norm)


def merge_tasks(thread_tasks: list[Task], body_tasks: list[Task]) -> list[Task]:
    """Merge tasks from threads and body summaries, removing duplicates.

    Thread tasks take priority over body tasks for duplicates.

    Args:
        thread_tasks: Tasks from GraphQL reviewThreads
        body_tasks: Tasks from review body summaries

    Returns:
        Merged and deduplicated task list
    """
    seen: dict[tuple[str, int, str], Task] = {}

    # Thread tasks have priority
    for task in thread_tasks:
        key = dedup_key(task)
        seen[key] = task

    # Add body tasks only if not duplicate
    for task in body_tasks:
        key = dedup_key(task)
        if key not in seen:
            seen[key] = task

    # Return in a stable order (by file, then line)
    tasks = list(seen.values())
    tasks.sort(key=lambda t: (t.file, t.start_line or t.line, t.line))

    return tasks


def parse_input(input_file: TextIO) -> dict:
    """Parse input JSON from file or stdin.

    Handles both thread comments and review body summaries.

    Args:
        input_file: File object to read from

    Returns:
        Output dict with tasks and summary
    """
    data = json.load(input_file)

    # Parse thread comments
    thread_tasks = parse_threads(data)

    # Parse review body summaries
    body_tasks: list[Task] = []
    for body in data.get("review_bodies", []):
        body_tasks.extend(parse_review_body(body))

    # Merge and deduplicate
    all_tasks = merge_tasks(thread_tasks, body_tasks)

    # Assign sequential IDs
    for i, task in enumerate(all_tasks, start=1):
        task.id = f"task-{i:03d}"

    return generate_output(all_tasks)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse CodeRabbit review thread comments into structured tasks",
        epilog="Example: ai-review-tasks --pr 1 --pretty",
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
        result = parse_input(args.input)

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
            filtered = result["tasks"]
            by_file: Counter[str] = Counter()
            for t in filtered:
                by_file[t["file"]] += 1
            result["summary"] = {
                "total": len(filtered),
                "by_severity": {
                    "major": sum(1 for t in filtered if t["severity"] == "major"),
                    "minor": sum(1 for t in filtered if t["severity"] == "minor"),
                    "suggestion": sum(
                        1 for t in filtered if t["severity"] == "suggestion"
                    ),
                },
                "by_source": {
                    "thread": sum(1 for t in filtered if t["source"] == "thread"),
                    "nitpick": sum(1 for t in filtered if t["source"] == "nitpick"),
                    "outside_diff": sum(
                        1 for t in filtered if t["source"] == "outside_diff"
                    ),
                },
                "by_file": dict(by_file),
            }

        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent))  # noqa: T201

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
