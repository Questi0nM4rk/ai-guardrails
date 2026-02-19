"""Project health check for ai-guardrails.

Reports the status of hooks, configs, dependencies, and integrations
for the current project.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

from guardrails.constants import GREEN, NC, RED, YELLOW

# Expected hook scripts
_EXPECTED_HOOKS = [
    "format-and-stage.sh",
    "detect-suppression-comments.sh",
    "validate-generated-configs.sh",
    "protect-generated-configs.sh",
    "detect-config-ignore-edits.sh",
    "dangerous-command-check.sh",
    "pre-commit.sh",
    "pre-push.sh",
]

# Base configs always expected
_BASE_CONFIGS = [".editorconfig"]

# Language-specific configs
_LANG_CONFIGS: dict[str, list[str]] = {
    "python": ["ruff.toml"],
    "rust": ["rustfmt.toml"],
    "dotnet": ["Directory.Build.props", ".globalconfig"],
    "cpp": [".clang-format"],
    "lua": ["stylua.toml"],
    "node": ["biome.json"],
}

# Review bot config files (DeepSource and Gemini removed)
_BOT_CONFIGS = [
    (".coderabbit.yaml", "CodeRabbit"),
    (".pr_agent.toml", "PR-Agent"),
]

# Agent instruction marker
_AGENT_MARKER = "## AI Guardrails - Code Standards"

StatusValue = Literal["ok", "warn", "error", "skip"]


class Check(Enum):
    """Named checks for status report."""

    GIT_REPO = "git_repo"
    PRECOMMIT = "precommit"
    HOOKS = "hooks"
    CONFIGS = "configs"
    REGISTRY = "registry"
    AGENT_INSTRUCTIONS = "agent_instructions"
    REVIEW_BOTS = "review_bots"
    CI_WORKFLOW = "ci_workflow"


@dataclass
class CheckResult:
    """Result of a single status check."""

    check: Check
    status: StatusValue
    message: str


@dataclass
class StatusReport:
    """Aggregated status report for a project."""

    project_dir: str
    languages: list[str]
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def overall(self) -> str:
        """Compute overall status from individual checks."""
        statuses = [c.status for c in self.checks if c.status != "skip"]
        if any(s == "error" for s in statuses):
            return "error"
        if any(s == "warn" for s in statuses):
            return "degraded"
        return "ok"

    def to_json(self) -> str:
        """Serialize report to JSON."""
        return json.dumps(
            {
                "project_dir": self.project_dir,
                "languages": self.languages,
                "overall": self.overall,
                "checks": [
                    {
                        "check": c.check.value,
                        "status": c.status,
                        "message": c.message,
                    }
                    for c in self.checks
                ],
            },
            indent=2,
        )


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_git_repo(project_dir: Path) -> CheckResult:
    """Check if the directory is a git repository."""
    if (project_dir / ".git").is_dir():
        return CheckResult(Check.GIT_REPO, "ok", "Git repository")
    return CheckResult(Check.GIT_REPO, "error", "Not a git repository")


def check_precommit(project_dir: Path) -> CheckResult:
    """Check if pre-commit is installed and hooks are active."""
    if not shutil.which("pre-commit"):
        return CheckResult(Check.PRECOMMIT, "warn", "pre-commit not found in PATH")

    hook_file = project_dir / ".git" / "hooks" / "pre-commit"
    if not hook_file.exists():
        return CheckResult(
            Check.PRECOMMIT,
            "warn",
            "pre-commit found but hooks not installed (run: pre-commit install)",
        )

    return CheckResult(Check.PRECOMMIT, "ok", "pre-commit installed and hooks active")


def check_hooks(project_dir: Path) -> CheckResult:
    """Check if hook scripts are deployed to .ai-guardrails/hooks/."""
    hooks_dir = project_dir / ".ai-guardrails" / "hooks"
    if not hooks_dir.is_dir():
        return CheckResult(Check.HOOKS, "error", "No .ai-guardrails/hooks/ directory")

    deployed = [h for h in _EXPECTED_HOOKS if (hooks_dir / h).exists()]
    total = len(_EXPECTED_HOOKS)
    count = len(deployed)

    if count == total:
        return CheckResult(Check.HOOKS, "ok", f"{count}/{total} hooks deployed")

    missing = [h for h in _EXPECTED_HOOKS if h not in deployed]
    return CheckResult(
        Check.HOOKS, "warn", f"{count}/{total} hooks deployed (missing: {', '.join(missing)})"
    )


def check_configs(project_dir: Path, *, languages: list[str]) -> CheckResult:
    """Check if expected config files are present."""
    expected = list(_BASE_CONFIGS)
    for lang in languages:
        expected.extend(_LANG_CONFIGS.get(lang, []))

    present = [c for c in expected if (project_dir / c).exists()]
    missing = [c for c in expected if c not in present]

    if not missing:
        return CheckResult(Check.CONFIGS, "ok", f"{len(present)} configs installed")

    return CheckResult(
        Check.CONFIGS,
        "warn",
        f"{len(present)}/{len(expected)} configs (missing: {', '.join(missing)})",
    )


def check_registry(project_dir: Path) -> CheckResult:
    """Check if the exception registry exists and is valid TOML."""
    import tomllib

    registry_path = project_dir / ".guardrails-exceptions.toml"
    if not registry_path.exists():
        return CheckResult(Check.REGISTRY, "skip", "No exception registry")

    try:
        with registry_path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        return CheckResult(Check.REGISTRY, "error", f"Invalid TOML: {e}")
    except OSError as e:
        return CheckResult(Check.REGISTRY, "error", f"Cannot read registry: {e}")

    if "schema_version" not in data:
        return CheckResult(Check.REGISTRY, "warn", "Registry missing schema_version")

    return CheckResult(Check.REGISTRY, "ok", "Exception registry valid")


def check_agent_instructions(project_dir: Path) -> CheckResult:
    """Check if CLAUDE.md or AGENTS.md has guardrails section."""
    for name in ("CLAUDE.md", "AGENTS.md"):
        filepath = project_dir / name
        if filepath.exists():
            content = filepath.read_text()
            if _AGENT_MARKER in content:
                return CheckResult(Check.AGENT_INSTRUCTIONS, "ok", f"Guardrails rules in {name}")

    return CheckResult(
        Check.AGENT_INSTRUCTIONS,
        "warn",
        "No guardrails section in CLAUDE.md or AGENTS.md",
    )


def check_review_bots(project_dir: Path) -> CheckResult:
    """Check if review bot configs are present."""
    present = []
    missing = []

    for filename, name in _BOT_CONFIGS:
        if (project_dir / filename).exists():
            present.append(name)
        else:
            missing.append(name)

    if not missing:
        return CheckResult(
            Check.REVIEW_BOTS, "ok", f"All review bots configured: {', '.join(present)}"
        )

    if present:
        return CheckResult(
            Check.REVIEW_BOTS,
            "warn",
            f"Partial: {', '.join(present)} (missing: {', '.join(missing)})",
        )

    return CheckResult(Check.REVIEW_BOTS, "skip", "No review bot configs found")


def check_ci_workflow(project_dir: Path) -> CheckResult:
    """Check if CI workflow is installed."""
    if not (project_dir / ".github").is_dir():
        return CheckResult(Check.CI_WORKFLOW, "skip", "Not a GitHub project")

    check_yml = project_dir / ".github" / "workflows" / "check.yml"
    if check_yml.exists():
        return CheckResult(Check.CI_WORKFLOW, "ok", "CI workflow installed")

    return CheckResult(Check.CI_WORKFLOW, "warn", "CI workflow not found")


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

_STATUS_ICONS: dict[str, str] = {
    "ok": f"{GREEN}\u2713{NC}",
    "warn": f"{YELLOW}\u26a0{NC}",
    "error": f"{RED}\u2717{NC}",
    "skip": f"{YELLOW}\u2298{NC}",
}

_OVERALL_LABELS: dict[str, str] = {
    "ok": f"{GREEN}HEALTHY{NC}",
    "degraded": f"{YELLOW}DEGRADED{NC}",
    "error": f"{RED}ERROR{NC}",
}


def _format_report(report: StatusReport) -> str:
    """Format a status report for terminal output."""
    lines = []
    lines.append(f"  Project: {report.project_dir}")
    if report.languages:
        lines.append(f"  Languages: {', '.join(report.languages)}")
    lines.append("")

    for check in report.checks:
        icon = _STATUS_ICONS.get(check.status, "?")
        lines.append(f"  {icon} {check.message}")

    lines.append("")
    overall_label = _OVERALL_LABELS.get(report.overall, report.overall)
    lines.append(f"  Overall: {overall_label}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_status(
    *,
    project_dir: Path | None = None,
    output_json: bool = False,
) -> int:
    """Run the status check and print results.

    Returns:
        0 if healthy, 1 if degraded, 2 if error.

    """
    if project_dir is None:
        project_dir = Path.cwd()

    # Detect languages
    languages: list[str] = []
    try:
        from guardrails._paths import find_configs_dir
        from guardrails.assemble import detect_languages, load_registry

        configs_dir = find_configs_dir()
        registry_path = configs_dir / "languages.yaml"
        if registry_path.exists():
            registry = load_registry(registry_path)
            languages = detect_languages(project_dir, registry)
    except Exception:  # noqa: BLE001, S110
        pass

    # Run all checks
    checks = [
        check_git_repo(project_dir),
        check_precommit(project_dir),
        check_hooks(project_dir),
        check_configs(project_dir, languages=languages),
        check_registry(project_dir),
        check_agent_instructions(project_dir),
        check_review_bots(project_dir),
        check_ci_workflow(project_dir),
    ]

    report = StatusReport(
        project_dir=str(project_dir),
        languages=languages,
        checks=checks,
    )

    if output_json:
        print(report.to_json())
    else:
        print(_format_report(report))

    return {"ok": 0, "degraded": 1, "error": 2}.get(report.overall, 2)
