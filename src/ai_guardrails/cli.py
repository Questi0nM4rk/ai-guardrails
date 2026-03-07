"""CLI entry point for ai-guardrails using cyclopts."""

from __future__ import annotations

from importlib import (  # nosemgrep: python37-compatibility-importlib2
    resources as _importlib_resources,
)
from pathlib import Path
from typing import TYPE_CHECKING

import cyclopts

from ai_guardrails.infra.command_runner import CommandRunner
from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.infra.console import Console
from ai_guardrails.infra.file_manager import FileManager
from ai_guardrails.infra.prompt_ui import is_tty
from ai_guardrails.pipelines.check_pipeline import CheckOptions, CheckPipeline
from ai_guardrails.pipelines.generate_pipeline import GenerateOptions, GeneratePipeline
from ai_guardrails.pipelines.init_pipeline import InitOptions, InitPipeline
from ai_guardrails.pipelines.install_pipeline import InstallOptions, InstallPipeline
from ai_guardrails.pipelines.report_pipeline import ReportPipeline
from ai_guardrails.pipelines.snapshot_pipeline import SnapshotOptions, SnapshotPipeline
from ai_guardrails.pipelines.status_pipeline import StatusPipeline

if TYPE_CHECKING:
    from ai_guardrails.pipelines.base import StepResult

app = cyclopts.App(
    name="ai-guardrails", help="Pedantic code enforcement for AI-maintained repos."
)

_DATA_DIR = Path(str(_importlib_resources.files("ai_guardrails"))) / "_data"
_CONFIGS_DIR = _DATA_DIR / "configs"
_TEMPLATES_DIR = _DATA_DIR / "templates"
_REGISTRY_TEMPLATE = _TEMPLATES_DIR / "guardrails-exceptions.toml"
_CI_TEMPLATE = _TEMPLATES_DIR / "workflows" / "check.yml"
_AGENT_TEMPLATE = _TEMPLATES_DIR / "CLAUDE.md.guardrails"
_GLOBAL_CONFIG_DIR = Path.home() / ".ai-guardrails"
_CUSTOM_PLUGINS_DIR = _GLOBAL_CONFIG_DIR / "plugins"


def _resolve_project_dir(project_dir: Path | None) -> Path:
    """Resolve and validate the project directory is a git repo.

    Accepts both normal repos (.git is a directory) and git worktrees
    (.git is a file pointing at the main repo's worktree state).
    """
    resolved = (project_dir or Path.cwd()).resolve()
    if not (resolved / ".git").exists():
        raise SystemExit(
            f"Error: {resolved} is not a git repository. Run 'git init' first."
        )
    return resolved


def _make_infra(
    *,
    dry_run: bool = False,
) -> tuple[FileManager, CommandRunner, ConfigLoader, Console]:
    """Create infrastructure objects for pipeline execution."""
    return (
        FileManager(dry_run=dry_run),
        CommandRunner(),
        ConfigLoader(),
        Console(),
    )


def _print_results(results: list[StepResult], console: Console) -> None:
    """Print step results using appropriate severity formatting."""
    for result in results:
        if result.status == "error":
            console.error(f"  {result.message}")
        elif result.status == "warn":
            console.warning(f"  {result.message}")
        elif result.status == "skip":
            console.info(f"  (skip) {result.message}")
        else:
            console.success(f"  {result.message}")


@app.command
def install(*, upgrade: bool = False) -> None:
    """Install ai-guardrails globally (once per machine).

    Creates ~/.ai-guardrails/config.toml and merges PreToolUse hooks
    into ~/.claude/settings.json for dangerous command detection and
    config protection.

    Use --upgrade to re-run after updating ai-guardrails.
    """
    options = InstallOptions(upgrade=upgrade)
    pipeline = InstallPipeline(options=options, global_config_dir=_GLOBAL_CONFIG_DIR)
    fm, runner, loader, console = _make_infra()
    results = pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
    _print_results(results, console)


@app.command
def init(  # ai-guardrails-allow: PLR0913 "CLI init requires many configuration options"
    *,
    project_dir: Path | None = None,
    force: bool = False,
    no_hooks: bool = False,
    no_ci: bool = False,
    no_agent_instructions: bool = False,
    dry_run: bool = False,
    profile: str = "standard",
    interactive: bool | None = None,
    upgrade: bool = False,
) -> None:
    """Initialize ai-guardrails in the current project.

    Detects languages, creates .guardrails-exceptions.toml, generates
    linter configs (ruff.toml, lefthook.yml, .editorconfig, etc.),
    optionally installs git hooks and CI workflow.

    Use --profile to select an enforcement posture: minimal, standard (default), strict.
    Use --interactive / --no-interactive to force or suppress Y/N prompts.
    When omitted, prompts appear only when running in an interactive terminal.
    Use --upgrade to re-run without overwriting the existing exception registry.
    """
    resolved = _resolve_project_dir(project_dir)
    run_interactive = interactive if interactive is not None else is_tty()
    options = InitOptions(
        force=force,
        no_hooks=no_hooks,
        no_ci=no_ci,
        no_agent_instructions=no_agent_instructions,
        dry_run=dry_run,
        profile=profile,
        interactive=run_interactive,
        upgrade=upgrade,
    )
    custom_dir = _CUSTOM_PLUGINS_DIR if _CUSTOM_PLUGINS_DIR.is_dir() else None
    pipeline = InitPipeline(
        options=options,
        data_dir=_DATA_DIR,
        configs_dir=_CONFIGS_DIR,
        registry_template=_REGISTRY_TEMPLATE,
        ci_template=_CI_TEMPLATE,
        agent_template=_AGENT_TEMPLATE,
        custom_plugins_dir=custom_dir,
    )
    fm, runner, loader, console = _make_infra(dry_run=dry_run)
    results = pipeline.run(
        project_dir=resolved,
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
    _print_results(results, console)


@app.command
def generate(
    *,
    project_dir: Path | None = None,
    check: bool = False,
    languages: str | None = None,
    dry_run: bool = False,
) -> None:
    """Regenerate tool configs from the exception registry.

    Reads .guardrails-exceptions.toml and regenerates all managed configs.
    Use --check in CI to verify configs are fresh without writing.
    """
    resolved = _resolve_project_dir(project_dir)
    lang_list = [lang.strip() for lang in languages.split(",")] if languages else None
    options = GenerateOptions(check=check, languages=lang_list, dry_run=dry_run)
    custom_dir = _CUSTOM_PLUGINS_DIR if _CUSTOM_PLUGINS_DIR.is_dir() else None
    pipeline = GeneratePipeline(
        options=options,
        data_dir=_DATA_DIR,
        custom_plugins_dir=custom_dir,
    )
    fm, runner, loader, console = _make_infra(dry_run=dry_run)
    results = pipeline.run(
        project_dir=resolved,
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
    _print_results(results, console)
    if options.check and any(r.status == "error" for r in results):
        raise SystemExit(1)


@app.command
def status(*, project_dir: Path | None = None) -> None:
    """Show project health: detected languages, config freshness, hook status.

    Informational only -- never fails. Use 'generate --check' for CI validation.
    """
    resolved = _resolve_project_dir(project_dir)
    custom_dir = _CUSTOM_PLUGINS_DIR if _CUSTOM_PLUGINS_DIR.is_dir() else None
    pipeline = StatusPipeline(data_dir=_DATA_DIR, custom_plugins_dir=custom_dir)
    fm, runner, loader, console = _make_infra()
    results = pipeline.run(
        project_dir=resolved,
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
    _print_results(results, console)


@app.command
def report(*, project_dir: Path | None = None) -> None:
    """Show a summary of recent ai-guardrails check runs.

    Reads .guardrails-audit.jsonl and prints the last 10 check run results.
    """
    resolved = _resolve_project_dir(project_dir)
    pipeline = ReportPipeline()
    fm, runner, loader, console = _make_infra()
    results = pipeline.run(
        project_dir=resolved,
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
    _print_results(results, console)


@app.command
def snapshot(
    *,
    project_dir: Path | None = None,
    baseline: Path | None = None,
    dry_run: bool = False,
) -> None:
    """Capture current lint issues as baseline snapshot.

    Runs linters and writes all found issues to .guardrails-baseline.json.
    After snapshotting, 'ai-guardrails check' will only flag NEW issues
    introduced after this snapshot.

    Use --dry-run to preview what would be captured without writing.
    """
    resolved = _resolve_project_dir(project_dir)
    options = SnapshotOptions(baseline_file=baseline, dry_run=dry_run)
    custom_dir = _CUSTOM_PLUGINS_DIR if _CUSTOM_PLUGINS_DIR.is_dir() else None
    pipeline = SnapshotPipeline(
        options=options,
        data_dir=_DATA_DIR,
        custom_plugins_dir=custom_dir,
    )
    fm, runner, loader, console = _make_infra(dry_run=dry_run)
    results = pipeline.run(
        project_dir=resolved,
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
    _print_results(results, console)


@app.command
def check(
    *,
    project_dir: Path | None = None,
    baseline: Path | None = None,
    output_format: str = "text",
) -> None:
    """Run linters and compare against baseline. Fails if new issues found.

    Reads .guardrails-baseline.json (or --baseline) and runs configured linters
    for detected languages. New issues — those whose fingerprint is not recorded
    in the baseline — cause exit code 1. Baseline issues are suppressed.

    Use --output-format sarif to emit SARIF 2.1.0 JSON to stdout (GitHub Code Scanning).
    Use 'ai-guardrails snapshot' to capture the current state as a new baseline.
    """
    resolved = _resolve_project_dir(project_dir)
    options = CheckOptions(baseline_file=baseline, output_format=output_format)
    custom_dir = _CUSTOM_PLUGINS_DIR if _CUSTOM_PLUGINS_DIR.is_dir() else None
    pipeline = CheckPipeline(
        options=options,
        data_dir=_DATA_DIR,
        custom_plugins_dir=custom_dir,
    )
    fm, runner, loader, console = _make_infra()
    results = pipeline.run(
        project_dir=resolved,
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
    _print_results(results, console)
    if any(r.status == "error" for r in results):
        raise SystemExit(1)
