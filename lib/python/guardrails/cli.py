"""Unified CLI for ai-guardrails.

Replaces separate bin scripts with a single ``ai-guardrails`` command using subcommands.

Usage::

    ai-guardrails init [--type X] [--force] [--ci] [--gemini] [--deepsource] [--review-all]
    ai-guardrails generate [--check] [--dry-run]
    ai-guardrails comments [--pr N] [--bot X] [--reply ID BODY] [--resolve ID [BODY]]

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
        "--review-all",
        action="store_true",
        default=None,
        help="Install /review-all workflow",
    )
    p.add_argument("--no-review-all", action="store_true", help="Skip /review-all workflow")


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


def _add_comments_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "comments",
        help="List, reply to, and resolve PR review threads from all bots",
        description="Universal PR review comments — list, reply, and resolve threads.",
    )
    p.add_argument("--pr", type=int, help="PR number (default: current branch)")
    p.add_argument("--bot", "-b", help="Filter by bot (comma-separated: coderabbit,claude,...)")
    p.add_argument("--all", "-a", action="store_true", help="Include resolved threads")
    p.add_argument("--json", action="store_true", help="Output full JSON instead of compact")
    p.add_argument(
        "--reply",
        nargs=2,
        metavar=("THREAD_ID", "BODY"),
        help="Reply to a review thread",
    )
    p.add_argument(
        "--resolve",
        nargs="+",
        metavar="ARG",
        help="Resolve a thread: THREAD_ID [BODY]",
    )
    p.add_argument(
        "--resolve-all",
        action="store_true",
        help="Resolve all unresolved threads (filtered by --bot)",
    )


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
        install_review_all=_resolve_flag(args, "review_all"),
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


def _cmd_comments(args: argparse.Namespace) -> int:
    """Run the ``comments`` subcommand to list/reply/resolve review threads."""
    from guardrails.comments import run_comments

    reply = tuple(args.reply) if args.reply else None
    resolve = None
    if args.resolve:
        thread_id = args.resolve[0]
        body = args.resolve[1] if len(args.resolve) > 1 else None
        resolve = (thread_id, body)

    return run_comments(
        pr=args.pr,
        bot=args.bot,
        reply=reply,
        resolve=resolve,
        resolve_all=args.resolve_all,
        show_all=args.all,
        output_json=args.json,
    )


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
    _add_comments_parser(subparsers)

    args = parser.parse_args(argv)

    dispatch: dict[str, typing.Callable[[argparse.Namespace], int]] = {
        "init": _cmd_init,
        "generate": _cmd_generate,
        "comments": _cmd_comments,
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
