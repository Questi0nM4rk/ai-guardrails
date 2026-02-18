"""Unified CLI for ai-guardrails.

Replaces separate bin scripts with a single ``ai-guardrails`` command using subcommands.

Usage::

    ai-guardrails init [--type X] [--force] [--ci] [--coderabbit] [--dry-run]
    ai-guardrails generate [--check] [--dry-run]
    ai-guardrails comments [--pr N] [--bot X] [--reply ID BODY] [--resolve ID [BODY]]
    ai-guardrails status [--json]

"""

from __future__ import annotations

import argparse
import sys
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
    p.add_argument("--coderabbit", action="store_true", default=None)
    p.add_argument("--no-coderabbit", action="store_true")
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
    action = p.add_mutually_exclusive_group()
    action.add_argument(
        "--reply",
        nargs=2,
        metavar=("THREAD_ID", "BODY"),
        help="Reply to a review thread",
    )
    action.add_argument(
        "--resolve",
        nargs="+",
        metavar="ARG",
        help="Resolve a thread: THREAD_ID [BODY]",
    )
    action.add_argument(
        "--resolve-all",
        action="store_true",
        help="Resolve all unresolved threads (filtered by --bot)",
    )
    p.add_argument(
        "--body",
        help="Reply body to include when batch-resolving threads (used with --resolve-all)",
    )


def _add_status_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "status",
        help="Check project health and configuration status",
        description="Report the status of hooks, configs, dependencies, and integrations.",
    )
    p.add_argument("--json", action="store_true", help="Output JSON instead of human-readable")


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
        install_coderabbit=_resolve_flag(args, "coderabbit"),
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


def _cmd_comments(args: argparse.Namespace) -> int:
    """Run the ``comments`` subcommand to list/reply/resolve review threads."""
    from guardrails.comments import run_comments

    if args.body and not args.resolve_all:
        print("Error: --body can only be used with --resolve-all", file=sys.stderr)
        return 1

    reply = tuple(args.reply) if args.reply else None
    resolve = None
    if args.resolve:
        max_resolve_args = 2
        if len(args.resolve) > max_resolve_args:
            print(
                "Error: --resolve accepts at most 2 arguments: THREAD_ID [BODY]",
                file=sys.stderr,
            )
            return 1
        thread_id = args.resolve[0]
        body = args.resolve[1] if len(args.resolve) > 1 else None
        resolve = (thread_id, body)

    return run_comments(
        pr=args.pr,
        bot=args.bot,
        reply=reply,
        resolve=resolve,
        resolve_all=args.resolve_all,
        resolve_all_body=args.body if args.resolve_all else None,
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
    _add_status_parser(subparsers)

    args = parser.parse_args(argv)

    dispatch: dict[str, typing.Callable[[argparse.Namespace], int]] = {
        "init": _cmd_init,
        "generate": _cmd_generate,
        "comments": _cmd_comments,
        "status": _cmd_status,
    }

    return dispatch[args.command](args)


def _cmd_status(args: argparse.Namespace) -> int:
    """Run the ``status`` subcommand to check project health."""
    from guardrails.status import run_status

    return run_status(output_json=args.json)


def _get_version() -> str:
    """Return package version or ``"unknown"``."""
    try:
        from guardrails import __version__
    except ImportError:
        return "unknown"
    else:
        return __version__
