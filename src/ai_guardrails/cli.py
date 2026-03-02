"""CLI entry point for ai-guardrails using cyclopts.

Commands:
  install  — one-time global setup
  init     — per-project initialization
  generate — regenerate configs from exception registry
"""

from __future__ import annotations

from pathlib import Path

import cyclopts

from ai_guardrails.infra.command_runner import CommandRunner
from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.infra.console import Console
from ai_guardrails.infra.file_manager import FileManager
from ai_guardrails.pipelines.generate_pipeline import GenerateOptions, GeneratePipeline
from ai_guardrails.pipelines.init_pipeline import InitOptions, InitPipeline
from ai_guardrails.pipelines.install_pipeline import InstallOptions, InstallPipeline

app = cyclopts.App(name="ai-guardrails", help="Pedantic code enforcement for AI-maintained repos.")

# ---------------------------------------------------------------------------
# Package data paths
# ---------------------------------------------------------------------------

_PACKAGE_ROOT = Path(__file__).parents[2]
_CONFIGS_DIR = _PACKAGE_ROOT / "configs"
_TEMPLATES_DIR = _PACKAGE_ROOT / "templates"
_REGISTRY_TEMPLATE = _TEMPLATES_DIR / "guardrails-exceptions.toml"
_CI_TEMPLATE = _TEMPLATES_DIR / "workflows" / "check.yml"
_AGENT_TEMPLATE = _TEMPLATES_DIR / "CLAUDE.md.guardrails"
_GLOBAL_CONFIG_DIR = Path.home() / ".ai-guardrails"
_CUSTOM_PLUGINS_DIR = _GLOBAL_CONFIG_DIR / "plugins"

# data_dir is the repo root — configs/ and templates/ are found relative to it
_DATA_DIR = _PACKAGE_ROOT


def _make_infra(
    *, dry_run: bool = False
) -> tuple[FileManager, CommandRunner, ConfigLoader, Console]:
    return (
        FileManager(dry_run=dry_run),
        CommandRunner(),
        ConfigLoader(),
        Console(),
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command
def install(*, upgrade: bool = False) -> None:
    """Install ai-guardrails globally (once per machine)."""
    options = InstallOptions(upgrade=upgrade)
    pipeline = InstallPipeline(options=options, global_config_dir=_GLOBAL_CONFIG_DIR)
    fm, runner, loader, console = _make_infra()
    results = pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
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
def init(
    *,
    force: bool = False,
    no_hooks: bool = False,
    no_ci: bool = False,
    no_agent_instructions: bool = False,
    dry_run: bool = False,
) -> None:
    """Initialize ai-guardrails in the current project."""
    options = InitOptions(
        force=force,
        no_hooks=no_hooks,
        no_ci=no_ci,
        no_agent_instructions=no_agent_instructions,
        dry_run=dry_run,
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
        project_dir=Path.cwd(),
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
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
def generate(
    *,
    check: bool = False,
    languages: str | None = None,
    dry_run: bool = False,
) -> None:
    """Regenerate tool configs from exception registry."""
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
        project_dir=Path.cwd(),
        file_manager=fm,
        command_runner=runner,
        config_loader=loader,
        console=console,
    )
    for result in results:
        if result.status == "error":
            console.error(f"  {result.message}")
        elif result.status == "warn":
            console.warning(f"  {result.message}")
        elif result.status == "skip":
            console.info(f"  (skip) {result.message}")
        else:
            console.success(f"  {result.message}")
