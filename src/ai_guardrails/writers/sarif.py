"""Build SARIF 2.1.0 output from LintIssue findings."""

from __future__ import annotations

from importlib.metadata import version as _pkg_version
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_guardrails.models.lint_issue import LintIssue

_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_TOOL_VERSION = _pkg_version("ai-guardrails")


def build_sarif(issues: list[LintIssue], *, tool_version: str = _TOOL_VERSION) -> str:
    """Return SARIF 2.1.0 JSON string for the given lint issues."""
    rules = {i.rule: {"id": i.rule, "name": i.rule} for i in issues}
    results = [
        {
            "ruleId": i.rule,
            "level": "error",
            "message": {"text": i.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": i.file},
                        "region": {"startLine": i.line, "startColumn": i.col},
                    }
                }
            ],
        }
        for i in issues
    ]
    sarif = {
        "$schema": _SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ai-guardrails",
                        "version": tool_version,
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2)
