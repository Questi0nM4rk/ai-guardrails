"""Tests for SARIF 2.1.0 output writer."""

from __future__ import annotations

import json

from ai_guardrails.writers.sarif import build_sarif

from ai_guardrails.models.lint_issue import LintIssue


def _issue(rule: str = "UP007", file: str = "src/foo.py", line: int = 10) -> LintIssue:
    return LintIssue(
        rule=rule,
        linter="ruff",
        file=file,
        line=line,
        col=1,
        message="test message",
        fingerprint="abc123",
    )


def test_build_sarif_empty() -> None:
    output = json.loads(build_sarif([]))
    assert output["version"] == "2.1.0"
    assert output["runs"][0]["results"] == []


def test_build_sarif_single_issue() -> None:
    output = json.loads(build_sarif([_issue()]))
    result = output["runs"][0]["results"][0]
    assert result["ruleId"] == "UP007"
    assert (
        result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        == "src/foo.py"
    )
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 10


def test_build_sarif_includes_rules() -> None:
    output = json.loads(build_sarif([_issue("UP007"), _issue("E501")]))
    rule_ids = {r["id"] for r in output["runs"][0]["tool"]["driver"]["rules"]}
    assert rule_ids == {"UP007", "E501"}


def test_build_sarif_deduplicates_rules() -> None:
    output = json.loads(build_sarif([_issue("UP007"), _issue("UP007")]))
    rules = output["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1


def test_build_sarif_schema_field() -> None:
    output = json.loads(build_sarif([]))
    assert output["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"


def test_build_sarif_tool_name() -> None:
    output = json.loads(build_sarif([]))
    assert output["runs"][0]["tool"]["driver"]["name"] == "ai-guardrails"


def test_build_sarif_custom_version() -> None:
    output = json.loads(build_sarif([], tool_version="1.2.3"))
    assert output["runs"][0]["tool"]["driver"]["version"] == "1.2.3"


def test_build_sarif_result_level() -> None:
    output = json.loads(build_sarif([_issue()]))
    result = output["runs"][0]["results"][0]
    assert result["level"] == "error"


def test_build_sarif_result_message() -> None:
    output = json.loads(build_sarif([_issue()]))
    result = output["runs"][0]["results"][0]
    assert result["message"]["text"] == "test message"


def test_build_sarif_result_column() -> None:
    issue = LintIssue(
        rule="E501",
        linter="ruff",
        file="src/bar.py",
        line=5,
        col=80,
        message="line too long",
        fingerprint="def456",
    )
    output = json.loads(build_sarif([issue]))
    region = output["runs"][0]["results"][0]["locations"][0]["physicalLocation"][
        "region"
    ]
    assert region["startColumn"] == 80
