#!/usr/bin/env python3
"""Unit tests for coderabbit_parser."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "lib" / "python"))

from coderabbit_parser import (
    Severity,
    Task,
    TaskType,
    extract_ai_prompts,
    extract_file_blocks,
    extract_nitpicks,
    extract_outside_diff,
    generate_output,
    parse_file,
    parse_review_body,
    strip_blockquote_prefixes,
)


class TestStripBlockquotePrefixes:
    """Test blockquote prefix stripping."""

    def test_single_prefix(self):
        """Test stripping single > prefix."""
        text = "> line 1\n> line 2\n> line 3"
        expected = "line 1\nline 2\nline 3"
        assert strip_blockquote_prefixes(text) == expected

    def test_nested_prefixes(self):
        """Test stripping nested >> prefixes."""
        text = "> > line 1\n> line 2"
        expected = "line 1\nline 2"
        assert strip_blockquote_prefixes(text) == expected

    def test_bare_gt(self):
        """Test handling bare > without space."""
        text = ">\n> line"
        expected = "\nline"
        assert strip_blockquote_prefixes(text) == expected

    def test_no_prefixes(self):
        """Test text without prefixes."""
        text = "line 1\nline 2"
        assert strip_blockquote_prefixes(text) == text


class TestExtractAIPrompts:
    """Test AI prompt extraction."""

    def test_extract_single_file_single_issue(self):
        """Test extracting single issue from single file."""
        body = """
<details>
<summary>🤖 Fix all issues with AI agents</summary>

````
In `@framework/test.md`:
- Around line 10-20: Fix the markdown formatting issues by adding blank lines.
````

</details>
"""
        tasks = extract_ai_prompts(body)
        assert len(tasks) == 1
        assert tasks[0].type == TaskType.AI_PROMPT
        assert tasks[0].file == "framework/test.md"
        assert tasks[0].line_range == "10-20"
        assert "markdown formatting" in tasks[0].message
        assert tasks[0].severity == Severity.MAJOR

    def test_extract_multiple_files_multiple_issues(self):
        """Test extracting multiple issues from multiple files."""
        body = """
<details>
<summary>🤖 Fix all issues with AI agents</summary>

````
In `@file1.md`:
- Around line 1-10: Issue 1
- Around line 20-30: Issue 2

In `@file2.py`:
- Around line 5-15: Issue 3
````

</details>
"""
        tasks = extract_ai_prompts(body)
        assert len(tasks) == 3
        assert tasks[0].file == "file1.md"
        assert tasks[0].line_range == "1-10"
        assert tasks[1].file == "file1.md"
        assert tasks[1].line_range == "20-30"
        assert tasks[2].file == "file2.py"
        assert tasks[2].line_range == "5-15"

    def test_no_ai_prompts_section(self):
        """Test when AI prompts section is missing."""
        body = "Some other content"
        tasks = extract_ai_prompts(body)
        assert len(tasks) == 0


class TestExtractFileBlocks:
    """Test file block extraction for outside_diff and nitpicks."""

    def test_extract_single_file_single_comment(self):
        """Test extracting single comment from single file."""
        section = """
<details>
<summary>test.md (1)</summary><blockquote>

`10-20`: **Fix formatting**

This is the description.

</blockquote></details>
"""
        tasks = extract_file_blocks(section, TaskType.OUTSIDE_DIFF)
        assert len(tasks) == 1
        assert tasks[0].file == "test.md"
        assert tasks[0].line_range == "10-20"
        assert tasks[0].message == "Fix formatting"
        assert "description" in tasks[0].description
        assert tasks[0].severity == Severity.MINOR

    def test_extract_multiple_comments_in_file(self):
        """Test extracting multiple comments from same file."""
        section = """
<details>
<summary>test.md (2)</summary><blockquote>

`10-20`: **Issue 1**

Description 1.

`30-40`: **Issue 2**

Description 2.

</blockquote></details>
"""
        tasks = extract_file_blocks(section, TaskType.NITPICK)
        assert len(tasks) == 2
        assert tasks[0].line_range == "10-20"
        assert tasks[0].message == "Issue 1"
        assert tasks[1].line_range == "30-40"
        assert tasks[1].message == "Issue 2"
        assert tasks[0].severity == Severity.SUGGESTION

    def test_remove_nested_details_blocks(self):
        """Test that nested details blocks are removed from description."""
        section = """
<details>
<summary>test.md (1)</summary><blockquote>

`10-20`: **Fix issue**

Description here.

<details>
<summary>🧹 Suggested fix</summary>
```diff
...
```
</details>

</blockquote></details>
"""
        tasks = extract_file_blocks(section, TaskType.OUTSIDE_DIFF)
        assert len(tasks) == 1
        assert "Description here" in tasks[0].description
        assert "Suggested fix" not in tasks[0].description


class TestExtractOutsideDiff:
    """Test outside diff extraction."""

    def test_extract_outside_diff_section(self):
        """Test extracting outside diff section."""
        body = """
> <details>
> <summary>⚠️ Outside diff range comments (1)</summary><blockquote>
>
> <details>
> <summary>test.md (1)</summary><blockquote>
>
> `10-20`: **Outside diff issue**
>
> This comment is outside the diff.
>
> </blockquote></details>
>
> </blockquote></details>
"""
        clean_body = strip_blockquote_prefixes(body)
        tasks = extract_outside_diff(clean_body)
        assert len(tasks) == 1
        assert tasks[0].type == TaskType.OUTSIDE_DIFF
        assert tasks[0].file == "test.md"
        assert tasks[0].message == "Outside diff issue"

    def test_multiple_outside_diff_sections(self):
        """Test handling multiple outside diff sections."""
        body = """
<details>
<summary>⚠️ Outside diff range comments (1)</summary><blockquote>
<details>
<summary>file1.md (1)</summary><blockquote>
`10-20`: **Issue 1**
</blockquote></details>
</blockquote></details>

Some other content

<details>
<summary>⚠️ Outside diff range comments (1)</summary><blockquote>
<details>
<summary>file2.md (1)</summary><blockquote>
`30-40`: **Issue 2**
</blockquote></details>
</blockquote></details>
"""
        tasks = extract_outside_diff(body)
        assert len(tasks) == 2


class TestExtractNitpicks:
    """Test nitpick extraction."""

    def test_extract_nitpick_section(self):
        """Test extracting nitpick section."""
        body = """
<details>
<summary>🧹 Nitpick comments (1)</summary><blockquote>
<details>
<summary>test.md (1)</summary><blockquote>

`10-20`: **Nitpick suggestion**

This is optional.

</blockquote></details>
</blockquote></details>
"""
        tasks = extract_nitpicks(body)
        assert len(tasks) == 1
        assert tasks[0].type == TaskType.NITPICK
        assert tasks[0].severity == Severity.SUGGESTION


class TestParseReviewBody:
    """Test complete review body parsing."""

    def test_parse_all_three_sections(self):
        """Test parsing all three sections together."""
        body = """
<details>
<summary>🤖 Fix all issues with AI agents</summary>

````
In `@file1.md`:
- Around line 1-10: AI prompt
````

</details>

<details>
<summary>⚠️ Outside diff range comments (1)</summary><blockquote>
<details>
<summary>file2.md (1)</summary><blockquote>
`20-30`: **Outside diff**
</blockquote></details>
</blockquote></details>

<details>
<summary>🧹 Nitpick comments (1)</summary><blockquote>
<details>
<summary>file3.md (1)</summary><blockquote>
`40-50`: **Nitpick**
</blockquote></details>
</blockquote></details>
"""
        tasks = parse_review_body(body)
        assert len(tasks) == 3
        assert tasks[0].type == TaskType.AI_PROMPT
        assert tasks[1].type == TaskType.OUTSIDE_DIFF
        assert tasks[2].type == TaskType.NITPICK
        # Check IDs are assigned
        assert tasks[0].id == "task-001"
        assert tasks[1].id == "task-002"
        assert tasks[2].id == "task-003"


class TestGenerateOutput:
    """Test output generation."""

    def test_generate_output_summary(self):
        """Test summary generation."""
        tasks = [
            Task(
                id="task-001",
                type=TaskType.AI_PROMPT,
                file="test.md",
                line_range="1-10",
                message="Test",
                severity=Severity.MAJOR,
            ),
            Task(
                id="task-002",
                type=TaskType.OUTSIDE_DIFF,
                file="test.md",
                line_range="20-30",
                message="Test",
                severity=Severity.MINOR,
            ),
            Task(
                id="task-003",
                type=TaskType.NITPICK,
                file="test.md",
                line_range="40-50",
                message="Test",
                severity=Severity.SUGGESTION,
            ),
        ]
        output = generate_output(tasks)

        assert output["summary"]["total"] == 3
        assert output["summary"]["ai_prompts"] == 1
        assert output["summary"]["outside_diff"] == 1
        assert output["summary"]["nitpicks"] == 1
        assert output["summary"]["by_severity"]["major"] == 1
        assert output["summary"]["by_severity"]["minor"] == 1
        assert output["summary"]["by_severity"]["suggestion"] == 1


class TestIntegrationRealData:
    """Integration tests with real CodeRabbit PR data."""

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_parse_codeagent_pr2(self, fixtures_dir):
        """Test parsing codeagent PR #2 (comprehensive test).

        Note: parse_file() extracts only the first CodeRabbit review.
        The fixture has multiple reviews, but we only parse one.
        """
        fixture_file = fixtures_dir / "codeagent_pr2_reviews.json"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        with fixture_file.open() as f:
            result = parse_file(f)

        # Verify we got tasks from the first CodeRabbit review
        # (First review has 5 AI prompts, 1 outside_diff, 1 nitpick = 7 total)
        assert result["summary"]["total"] == 7
        assert result["summary"]["ai_prompts"] == 5
        assert result["summary"]["outside_diff"] == 1
        assert result["summary"]["nitpicks"] == 1

        # Verify task structure
        for task in result["tasks"]:
            assert "id" in task
            assert "type" in task
            assert "file" in task
            assert "line_range" in task
            assert "message" in task
            assert "severity" in task
            assert task["type"] in ["ai_prompt", "outside_diff", "nitpick"]
            assert task["severity"] in ["major", "minor", "suggestion"]

    def test_parse_codeagent_pr2_all_sections(self, fixtures_dir):
        """Test that all three section types are present in parsed output."""
        fixture_file = fixtures_dir / "codeagent_pr2_reviews.json"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        with fixture_file.open() as f:
            result = parse_file(f)

        # Verify all three section types are present
        assert result["summary"]["ai_prompts"] > 0
        assert result["summary"]["outside_diff"] > 0
        assert result["summary"]["nitpicks"] > 0

        # Verify we have all three severities
        assert result["summary"]["by_severity"]["major"] > 0
        assert result["summary"]["by_severity"]["minor"] > 0
        assert result["summary"]["by_severity"]["suggestion"] > 0

    def test_parse_ai_guardrails_pr1(self, fixtures_dir):
        """Test parsing ai-guardrails PR #1."""
        fixture_file = fixtures_dir / "ai-guardrails_pr1_reviews.json"
        if not fixture_file.exists():
            pytest.skip("Fixture file not found")

        with fixture_file.open() as f:
            result = parse_file(f)

        # Should have tasks from review
        assert result["summary"]["total"] > 0

        # Verify all tasks have required fields
        for task in result["tasks"]:
            assert task["id"].startswith("task-")
            assert len(task["file"]) > 0
            assert "-" in task["line_range"]  # Should be "X-Y" format


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
