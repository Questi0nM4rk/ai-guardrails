"""Unified CLI for ai-guardrails.

Replaces the separate bin scripts (ai-guardrails-init, ai-guardrails-generate,
ai-review-tasks) with a single ``ai-guardrails`` command using subcommands.

Usage::

    ai-guardrails init [--type X] [--force] [--ci] [--gemini] [--deepsource] [--dry-run]
    ai-guardrails generate [--check] [--dry-run]
    ai-guardrails review [--pr N] [--severity X]

"""

from __future__ import annotations

import argparse
import typing


def _add_init_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "init",
        help="Set up pedantic code enforcement for a project",
        description="Initialize ai-guardrails configs, hooks, and CI for the current project.",
    )
    p.add_argument("--type", dest="project_type", help="Project type (python, rust, node, ...)")
    p.add_argument("--all", action="store_true", help="Copy ALL configs (multi-language)")
    p.add_argument("--force", action="store_true", help="Overwrite existing config files")
    p.add_argument("--no-precommit", action="store_true", help="Skip pre-commit config")
    p.add_argument("--pip-audit-pip", action="store_const", const="pip", dest="pip_audit")
    p.add_argument("--pip-audit-uv", action="store_const", const="uv", dest="pip_audit")
    p.add_argument("--no-pip-audit", action="store_const", const="none", dest="pip_audit")
    p.add_argument("--ci", action="store_true", default=None, help="Install CI workflow")
    p.add_argument("--no-ci", action="store_true", help="Skip CI workflow")
    p.add_argument("--claude-review", action="store_true", default=None)
    p.add_argument("--no-claude-review", action="store_true")
    p.add_argument("--coderabbit", action="store_true", default=None)
    p.add_argument("--no-coderabbit", action="store_true")
    p.add_argument(
        "--gemini",
        action="store_true",
        default=None,
        help="Install Gemini Code Assist config",
    )
    p.add_argument("--no-gemini", action="store_true", help="Skip Gemini config")
    p.add_argument(
        "--deepsource",
        action="store_true",
        default=None,
        help="Install DeepSource config",
    )
    p.add_argument("--no-deepsource", action="store_true", help="Skip DeepSource config")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )


def _add_generate_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "generate",
        help="Generate tool configs from exception registry",
        description="Generate tool configs from .guardrails-exceptions.toml.",
    )
    p.add_argument("project_dir", nargs="?", default=".", help="Project directory")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate registry only")
    mode.add_argument("--check", action="store_true", help="Check if configs are up to date")


def _add_review_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "review",
        help="Extract CodeRabbit review comments as tasks",
        description="Parse unresolved CodeRabbit review comments into actionable tasks.",
    )
    p.add_argument("--pr", type=int, help="PR number (default: current branch)")
    p.add_argument("--pretty", "-p", action="store_true", help="Pretty-print JSON output")
    p.add_argument("--severity", "-s", help="Filter by severity (major, minor, suggestion)")


def _resolve_flag(args: argparse.Namespace, name: str) -> str:
    """Resolve a --flag/--no-flag pair to ``"yes"``, ``"no"``, or ``"auto"``."""
    no_attr = f"no_{name}"
    if getattr(args, no_attr, False):
        return "no"
    if getattr(args, name, None):
        return "yes"
    return "auto"


def _cmd_init(args: argparse.Namespace) -> int:
    """Run the ``init`` subcommand to set up guardrails for a project.

    Resolves ``--flag/--no-flag`` pairs and delegates to :func:`run_init`.
    """
    from guardrails.init import run_init

    return run_init(
        project_type=args.project_type or ("all" if args.all else ""),
        force=args.force,
        skip_precommit=args.no_precommit,
        pip_audit_mode=args.pip_audit or "auto",
        install_ci=_resolve_flag(args, "ci"),
        install_claude_review=_resolve_flag(args, "claude_review"),
        install_coderabbit=_resolve_flag(args, "coderabbit"),
        install_gemini=_resolve_flag(args, "gemini"),
        install_deepsource=_resolve_flag(args, "deepsource"),
        dry_run=args.dry_run,
    )


def _cmd_generate(args: argparse.Namespace) -> int:
    """Run the ``generate`` subcommand to produce tool configs from the exception registry."""
    from guardrails.generate import run_generate_configs

    ok = run_generate_configs(
        project_dir=args.project_dir,
        dry_run=args.dry_run,
        check=args.check,
    )
    return 0 if ok else 1


def _cmd_review(args: argparse.Namespace) -> int:
    """Run the ``review`` subcommand to extract CodeRabbit comments as tasks."""
    from guardrails.coderabbit import run_review

    return run_review(pr=args.pr, pretty=args.pretty, severity=args.severity)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``ai-guardrails``."""
    parser = argparse.ArgumentParser(
        prog="ai-guardrails",
        description="Pedantic code enforcement for AI-maintained repositories",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_get_version()}")

    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_init_parser(subparsers)
    _add_generate_parser(subparsers)
    _add_review_parser(subparsers)

    args = parser.parse_args(argv)

    dispatch: dict[str, typing.Callable[[argparse.Namespace], int]] = {
        "init": _cmd_init,
        "generate": _cmd_generate,
        "review": _cmd_review,
    }

    return dispatch[args.command](args)


def _get_version() -> str:
    """Return package version or ``"unknown"``."""
    try:
        from guardrails import __version__
    except ImportError:
        return "unknown"
    else:
        return __version__
