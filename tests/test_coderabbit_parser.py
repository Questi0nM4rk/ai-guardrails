#!/usr/bin/env python3
"""Unit tests for coderabbit_parser.

Tests the dual-source implementation that parses:
1. Review thread comments (GraphQL reviewThreads)
2. Review body summaries (🧹 Nitpicks, ⚠️ Outside diff)
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

# Path setup handled by conftest.py
from coderabbit_parser import (
    Severity,
    Task,
    TaskSource,
    extract_ai_prompt,
    extract_description,
    extract_file_blocks,
    extract_section_content,
    extract_severity,
    extract_title,
    generate_output,
    merge_tasks,
    parse_body_item,
    parse_input,
    parse_line_range,
    parse_review_body,
    parse_thread,
    parse_threads,
    strip_blockquote_prefixes,
)


class TestExtractSeverity:
    """Test severity extraction from comment body first line."""

    def test_major_emoji(self) -> None:
        """Test detecting major severity from orange emoji."""
        body = "_⚠️ Potential issue_ | _🟠 Major_\n\n**Title**\n\nDescription"
        assert extract_severity(body) == Severity.MAJOR

    def test_major_text(self) -> None:
        """Test detecting major severity from text."""
        body = "Potential issue | Major\n\n**Title**"
        assert extract_severity(body) == Severity.MAJOR

    def test_minor_emoji(self) -> None:
        """Test detecting minor severity from yellow emoji."""
        body = "_🟡 Minor_\n\n**Title**"
        assert extract_severity(body) == Severity.MINOR

    def test_minor_text(self) -> None:
        """Test detecting minor severity from text."""
        body = "Minor issue\n\n**Title**"
        assert extract_severity(body) == Severity.MINOR

    def test_suggestion_default(self) -> None:
        """Test default severity is suggestion."""
        body = "**Title**\n\nSome description"
        assert extract_severity(body) == Severity.SUGGESTION

    def test_empty_body(self) -> None:
        """Test empty body returns suggestion."""
        assert extract_severity("") == Severity.SUGGESTION


class TestExtractTitle:
    """Test title extraction from bold text."""

    def test_title_on_own_line(self) -> None:
        """Test extracting title from bold text on its own line."""
        body = "_⚠️ Potential issue_\n\n**Fix the bug**\n\nDescription here"
        assert extract_title(body) == "Fix the bug"

    def test_title_with_whitespace(self) -> None:
        """Test extracting title with surrounding whitespace."""
        body = "Severity line\n\n**  Trim whitespace  **\n\nMore text"
        assert extract_title(body) == "Trim whitespace"

    def test_first_bold_not_on_own_line(self) -> None:
        """Test fallback to any bold text."""
        body = "Some text **inline bold** more text"
        assert extract_title(body) == "inline bold"

    def test_no_bold_text(self) -> None:
        """Test fallback when no bold text."""
        body = "Plain text without any formatting"
        assert extract_title(body) == "Untitled issue"

    def test_empty_body(self) -> None:
        """Test empty body returns fallback."""
        assert extract_title("") == "Untitled issue"


class TestExtractAIPrompt:
    """Test AI prompt extraction from details blocks."""

    def test_extract_ai_prompt(self) -> None:
        """Test extracting AI prompt from standard format."""
        body = """_⚠️ Potential issue_

**Title**

Description here.

<details><summary>🤖 Prompt for AI Agents</summary>

```
Fix the issue in file.py at line 42.
Use proper error handling.
```

</details>"""
        prompt = extract_ai_prompt(body)
        assert prompt is not None
        assert "Fix the issue" in prompt
        assert "proper error handling" in prompt

    def test_no_ai_prompt_section(self) -> None:
        """Test when no AI prompt section exists."""
        body = "**Title**\n\nJust a description, no AI prompt."
        assert extract_ai_prompt(body) is None

    def test_ai_prompt_with_language_tag(self) -> None:
        """Test extracting prompt from code block with language tag."""
        body = """<details><summary>🤖 Prompt for AI Agents</summary>
```text
This is the prompt.
```
</details>"""
        prompt = extract_ai_prompt(body)
        assert prompt is not None
        assert "This is the prompt" in prompt

    def test_case_insensitive_summary(self) -> None:
        """Test case insensitive summary matching."""
        body = """<details><summary>🤖 PROMPT FOR AI AGENTS</summary>
```
Prompt text
```
</details>"""
        prompt = extract_ai_prompt(body)
        assert prompt is not None


class TestExtractDescription:
    """Test description extraction from comment body."""

    def test_extract_description(self) -> None:
        """Test extracting description between title and details."""
        body = """_⚠️ Potential issue_

**Title Here**

This is the description.
It spans multiple lines.

<details><summary>🤖 Prompt for AI Agents</summary>
```
prompt
```
</details>"""
        desc = extract_description(body)
        assert desc is not None
        assert "This is the description" in desc
        assert "multiple lines" in desc
        assert "Prompt for AI Agents" not in desc

    def test_no_description(self) -> None:
        """Test when only title exists."""
        body = "_⚠️ Potential issue_\n\n**Title**"
        desc = extract_description(body)
        assert desc is None or desc.strip() == ""

    def test_removes_html_comments(self) -> None:
        """Test HTML comments are removed."""
        body = """_⚠️ Potential issue_

**Title**

Description here.
<!-- hidden comment -->
More description."""
        desc = extract_description(body)
        assert desc is not None
        assert "hidden comment" not in desc
        assert "Description here" in desc

    def test_truncates_long_description(self) -> None:
        """Test description is truncated at 500 chars."""
        long_text = "x" * 600
        body = f"_⚠️ Potential issue_\n\n**Title**\n\n{long_text}"
        desc = extract_description(body)
        assert desc is not None
        assert len(desc) <= 500
        assert desc.endswith("...")


class TestParseThread:
    """Test parsing individual thread into Task."""

    def test_parse_valid_thread(self) -> None:
        """Test parsing a complete valid thread."""
        thread = {
            "path": "src/main.py",
            "line": 42,
            "startLine": 40,
            "body": "_🟠 Major_\n\n**Fix null check**\n\nAdd validation.",
        }
        task = parse_thread(thread)
        assert task is not None
        assert task.file == "src/main.py"
        assert task.line == 42
        assert task.start_line == 40
        assert task.title == "Fix null check"
        assert task.severity == Severity.MAJOR

    def test_parse_thread_missing_body(self) -> None:
        """Test thread without body returns None."""
        thread = {"path": "test.py", "line": 10, "body": ""}
        assert parse_thread(thread) is None

    def test_parse_thread_missing_path(self) -> None:
        """Test thread without path returns None."""
        thread = {"path": "", "line": 10, "body": "**Title**"}
        assert parse_thread(thread) is None

    def test_parse_thread_missing_line(self) -> None:
        """Test thread without line returns None."""
        thread = {"path": "test.py", "line": None, "body": "**Title**"}
        assert parse_thread(thread) is None

    def test_parse_thread_optional_start_line(self) -> None:
        """Test thread without startLine sets None."""
        thread = {"path": "test.py", "line": 10, "body": "**Title**"}
        task = parse_thread(thread)
        assert task is not None
        assert task.start_line is None


class TestParseThreads:
    """Test parsing multiple threads."""

    def test_parse_multiple_threads(self) -> None:
        """Test parsing multiple threads (IDs assigned in parse_input)."""
        data = {
            "threads": [
                {
                    "path": "file1.py",
                    "line": 10,
                    "body": "_🟠 Major_\n\n**Issue 1**",
                },
                {
                    "path": "file2.py",
                    "line": 20,
                    "body": "_🟡 Minor_\n\n**Issue 2**",
                },
                {
                    "path": "file1.py",
                    "line": 30,
                    "body": "**Issue 3**",
                },
            ]
        }
        tasks = parse_threads(data)
        assert len(tasks) == 3
        # IDs are empty until parse_input assigns them
        assert tasks[0].id == ""
        assert tasks[0].severity == Severity.MAJOR
        assert tasks[1].severity == Severity.MINOR
        assert tasks[2].severity == Severity.SUGGESTION

    def test_parse_empty_threads(self) -> None:
        """Test empty threads list."""
        data = {"threads": []}
        tasks = parse_threads(data)
        assert tasks == []

    def test_parse_skips_invalid_threads(self) -> None:
        """Test invalid threads are skipped."""
        data = {
            "threads": [
                {"path": "valid.py", "line": 10, "body": "**Valid**"},
                {"path": "", "line": 20, "body": "**Invalid path**"},
                {"path": "valid2.py", "line": 30, "body": "**Valid 2**"},
            ]
        }
        tasks = parse_threads(data)
        assert len(tasks) == 2
        # Verify correct files parsed (IDs assigned later)
        assert tasks[0].file == "valid.py"
        assert tasks[1].file == "valid2.py"


class TestGenerateOutput:
    """Test output generation with summary."""

    def test_generate_output_summary(self) -> None:
        """Test summary calculation."""
        tasks = [
            Task(
                id="task-001",
                file="file1.py",
                line=10,
                title="Issue 1",
                severity=Severity.MAJOR,
            ),
            Task(
                id="task-002",
                file="file1.py",
                line=20,
                title="Issue 2",
                severity=Severity.MINOR,
            ),
            Task(
                id="task-003",
                file="file2.py",
                line=30,
                title="Issue 3",
                severity=Severity.SUGGESTION,
            ),
        ]
        output = generate_output(tasks)

        assert output["summary"]["total"] == 3
        assert output["summary"]["by_severity"]["major"] == 1
        assert output["summary"]["by_severity"]["minor"] == 1
        assert output["summary"]["by_severity"]["suggestion"] == 1
        assert output["summary"]["by_file"]["file1.py"] == 2
        assert output["summary"]["by_file"]["file2.py"] == 1

    def test_generate_output_empty(self) -> None:
        """Test output with no tasks."""
        output = generate_output([])
        assert output["summary"]["total"] == 0
        assert output["tasks"] == []


class TestTaskToDict:
    """Test Task serialization."""

    def test_task_to_dict_minimal(self) -> None:
        """Test minimal task serialization."""
        task = Task(
            id="task-001",
            file="test.py",
            line=42,
            title="Fix bug",
            severity=Severity.MAJOR,
        )
        d = task.to_dict()
        assert d["id"] == "task-001"
        assert d["file"] == "test.py"
        assert d["line"] == 42
        assert d["title"] == "Fix bug"
        assert d["severity"] == "major"
        assert "start_line" not in d
        assert "ai_prompt" not in d
        assert "description" not in d

    def test_task_to_dict_full(self) -> None:
        """Test full task serialization."""
        task = Task(
            id="task-001",
            file="test.py",
            line=42,
            title="Fix bug",
            severity=Severity.MAJOR,
            start_line=40,
            ai_prompt="Fix the null check",
            description="Missing validation",
        )
        d = task.to_dict()
        assert d["start_line"] == 40
        assert d["ai_prompt"] == "Fix the null check"
        assert d["description"] == "Missing validation"


class TestParseInput:
    """Test full input parsing from file."""

    def test_parse_input_json(self) -> None:
        """Test parsing JSON input from file object."""
        data = {
            "threads": [
                {
                    "path": "src/main.py",
                    "line": 42,
                    "startLine": 40,
                    "body": "_🟠 Major_\n\n**Fix the bug**\n\nDescription here.",
                }
            ]
        }
        input_file = io.StringIO(json.dumps(data))
        result = parse_input(input_file)

        assert result["summary"]["total"] == 1
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["file"] == "src/main.py"
        assert result["tasks"][0]["line"] == 42
        assert result["tasks"][0]["title"] == "Fix the bug"


# =============================================================================
# Review Body Parsing Tests (🧹 Nitpicks, ⚠️ Outside diff)
# =============================================================================


class TestStripBlockquotePrefixes:
    """Test blockquote prefix stripping."""

    def test_single_prefix(self) -> None:
        """Test stripping single > prefix."""
        text = "> line 1\n> line 2"
        assert strip_blockquote_prefixes(text) == "line 1\nline 2"

    def test_nested_prefixes(self) -> None:
        """Test stripping nested >> prefixes."""
        text = "> > nested\n> single"
        result = strip_blockquote_prefixes(text)
        assert "nested" in result
        assert "single" in result

    def test_no_prefixes(self) -> None:
        """Test text without prefixes is unchanged."""
        text = "no prefix here"
        assert strip_blockquote_prefixes(text) == text


class TestParseLineRange:
    """Test line range parsing."""

    def test_range(self) -> None:
        """Test parsing range like 40-50."""
        assert parse_line_range("40-50") == (40, 50)

    def test_single_line(self) -> None:
        """Test parsing single line."""
        assert parse_line_range("42") == (42, 42)

    def test_with_backticks(self) -> None:
        """Test parsing with backticks."""
        assert parse_line_range("`133-134`") == (133, 134)


class TestExtractSectionContent:
    """Test section content extraction."""

    def test_extract_nitpick_section(self) -> None:
        """Test extracting nitpick section."""
        body = """
<details>
<summary>🧹 Nitpick comments (1)</summary><blockquote>
<details>
<summary>test.py (1)</summary><blockquote>
`10-20`: **Test issue**
Description here.
</blockquote></details>
</blockquote></details>
"""
        content = extract_section_content(body, "🧹")
        assert content is not None
        assert "test.py" in content
        assert "Test issue" in content

    def test_missing_section(self) -> None:
        """Test when section doesn't exist."""
        body = "No sections here"
        assert extract_section_content(body, "🧹") is None


class TestExtractFileBlocks:
    """Test file block extraction."""

    def test_single_file_block(self) -> None:
        """Test extracting single file block."""
        section = """
<details>
<summary>test.py (1)</summary><blockquote>
`10-20`: **Issue title**
Description
</blockquote></details>
"""
        blocks = extract_file_blocks(section)
        assert len(blocks) == 1
        assert blocks[0][0] == "test.py"
        assert "Issue title" in blocks[0][1]

    def test_multiple_file_blocks(self) -> None:
        """Test extracting multiple file blocks."""
        section = """
<details>
<summary>file1.py (1)</summary><blockquote>
`10-20`: **Issue 1**
</blockquote></details>
<details>
<summary>file2.py (1)</summary><blockquote>
`30-40`: **Issue 2**
</blockquote></details>
"""
        blocks = extract_file_blocks(section)
        assert len(blocks) == 2
        assert blocks[0][0] == "file1.py"
        assert blocks[1][0] == "file2.py"


class TestParseBodyItem:
    """Test individual body item parsing."""

    def test_parse_valid_item(self) -> None:
        """Test parsing a valid item."""
        item = "`10-20`: **Fix the bug**\n\nDescription here."
        task = parse_body_item("test.py", item, TaskSource.NITPICK, Severity.SUGGESTION)
        assert task is not None
        assert task.file == "test.py"
        assert task.line == 20
        assert task.start_line == 10
        assert task.title == "Fix the bug"
        assert task.source == TaskSource.NITPICK

    def test_parse_single_line(self) -> None:
        """Test parsing item with single line."""
        item = "`42`: **Single line issue**"
        task = parse_body_item("test.py", item, TaskSource.OUTSIDE_DIFF, Severity.MINOR)
        assert task is not None
        assert task.line == 42
        assert task.start_line is None

    def test_invalid_format(self) -> None:
        """Test invalid format returns None."""
        item = "No backticks or bold"
        assert (
            parse_body_item("test.py", item, TaskSource.NITPICK, Severity.SUGGESTION)
            is None
        )


class TestParseReviewBody:
    """Test full review body parsing."""

    def test_parse_nitpicks(self) -> None:
        """Test parsing nitpick section."""
        body = """
<details>
<summary>🧹 Nitpick comments (2)</summary><blockquote>
<details>
<summary>test.py (2)</summary><blockquote>

`10-20`: **First issue**

Description 1.

`30-40`: **Second issue**

Description 2.

</blockquote></details>
</blockquote></details>
"""
        tasks = parse_review_body(body)
        assert len(tasks) == 2
        assert all(t.source == TaskSource.NITPICK for t in tasks)
        assert all(t.severity == Severity.SUGGESTION for t in tasks)

    def test_parse_outside_diff(self) -> None:
        """Test parsing outside diff section with blockquote prefixes."""
        body = """
> <details>
> <summary>⚠️ Outside diff range comments (1)</summary><blockquote>
> <details>
> <summary>old_file.py (1)</summary><blockquote>
>
> `100-110`: **Legacy issue**
>
> This is outside the diff.
>
> </blockquote></details>
> </blockquote></details>
"""
        tasks = parse_review_body(body)
        assert len(tasks) == 1
        assert tasks[0].source == TaskSource.OUTSIDE_DIFF
        assert tasks[0].severity == Severity.MINOR
        assert tasks[0].file == "old_file.py"


class TestMergeTasks:
    """Test task merging and deduplication."""

    def test_no_duplicates(self) -> None:
        """Test merging without duplicates."""
        thread_tasks = [
            Task(id="", file="a.py", line=10, title="Issue A", severity=Severity.MAJOR)
        ]
        body_tasks = [
            Task(
                id="",
                file="b.py",
                line=20,
                title="Issue B",
                severity=Severity.MINOR,
                source=TaskSource.NITPICK,
            )
        ]
        merged = merge_tasks(thread_tasks, body_tasks)
        assert len(merged) == 2

    def test_thread_takes_priority(self) -> None:
        """Test thread tasks take priority over body tasks."""
        thread_tasks = [
            Task(
                id="",
                file="test.py",
                line=10,
                title="Thread version",
                severity=Severity.MAJOR,
            )
        ]
        body_tasks = [
            Task(
                id="",
                file="test.py",
                line=10,
                title="thread version",  # Same normalized
                severity=Severity.SUGGESTION,
                source=TaskSource.NITPICK,
            )
        ]
        merged = merge_tasks(thread_tasks, body_tasks)
        assert len(merged) == 1
        assert merged[0].severity == Severity.MAJOR  # Thread version kept


class TestDualSourceParsing:
    """Test combined thread + body parsing."""

    def test_parse_both_sources(self) -> None:
        """Test parsing input with both threads and review bodies."""
        data = {
            "threads": [
                {
                    "path": "thread_file.py",
                    "line": 42,
                    "body": "_🟠 Major_\n\n**Thread issue**",
                }
            ],
            "review_bodies": [
                """
<details>
<summary>🧹 Nitpick comments (1)</summary><blockquote>
<details>
<summary>body_file.py (1)</summary><blockquote>
`10-20`: **Body issue**
</blockquote></details>
</blockquote></details>
"""
            ],
        }
        input_file = io.StringIO(json.dumps(data))
        result = parse_input(input_file)

        assert result["summary"]["total"] == 2
        assert result["summary"]["by_source"]["thread"] == 1
        assert result["summary"]["by_source"]["nitpick"] == 1


class TestIntegrationThreadFormat:
    """Integration tests with thread-format fixtures."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_parse_thread_fixture(self, fixtures_dir: Path) -> None:
        """Test parsing thread format fixture."""
        fixture_file = fixtures_dir / "thread_comments.json"
        if not fixture_file.exists():
            pytest.skip(
                "Fixture file not found - create tests/fixtures/thread_comments.json"
            )

        with fixture_file.open() as f:
            result = parse_input(f)

        # Verify output structure
        assert "tasks" in result
        assert "summary" in result
        for task in result["tasks"]:
            assert "id" in task
            assert "file" in task
            assert "line" in task
            assert "title" in task
            assert "severity" in task
            assert task["severity"] in ["major", "minor", "suggestion"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
