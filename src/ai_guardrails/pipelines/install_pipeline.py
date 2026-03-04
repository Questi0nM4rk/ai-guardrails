"""InstallPipeline — global once-per-machine setup.

Steps:
  1. CheckPrereqs (git, lefthook — required; ruff, biome — optional)
  2. InstallGlobalConfig (create ~/.ai-guardrails/config.toml)
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ai_guardrails.pipelines.base import Pipeline, PipelineContext, StepResult

if TYPE_CHECKING:
    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager

_GLOBAL_CONFIG_CONTENT = """\
[install]
version = "1.0.0"

[preferences]
default_languages = []
"""

_LEFTHOOK_INSTALL_HINT = (
    "install with: brew install lefthook"
    "  OR  go install github.com/evilmartians/lefthook@latest"
)


@dataclass
class InstallOptions:
    """Options for the install command."""

    upgrade: bool = False


class _CheckPrereqsStep:
    """Checks for required tools: git, lefthook."""

    name = "check-prereqs"

    def validate(self, _ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        missing: list[str] = []
        warned: list[str] = []

        for tool, required in [("git", True), ("lefthook", True)]:
            result = ctx.command_runner.run([tool, "--version"])
            if result.returncode != 0:
                if required:
                    missing.append(tool)
                else:
                    warned.append(tool)

        if missing:
            return StepResult(
                status="error",
                message=(
                    f"Required tools missing: {', '.join(missing)}"
                    f" — {_LEFTHOOK_INSTALL_HINT}"
                ),
            )
        if warned:
            return StepResult(
                status="warn",
                message=(
                    "Tools not found (install for full functionality):"
                    f" {', '.join(warned)}"
                ),
            )
        return StepResult(status="ok", message="All prerequisites found")


class _InstallGlobalConfigStep:
    """Creates ~/.ai-guardrails/config.toml."""

    name = "install-global-config"

    def __init__(self, global_config_dir: Path) -> None:
        self._config_dir = global_config_dir

    def validate(self, _ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        config_path = self._config_dir / "config.toml"
        with contextlib.suppress(FileExistsError, AttributeError):
            ctx.file_manager.mkdir(self._config_dir, parents=True, exist_ok=True)
        if ctx.file_manager.exists(config_path):
            return StepResult(status="skip", message="Global config already exists")
        ctx.file_manager.write_text(config_path, _GLOBAL_CONFIG_CONTENT)
        return StepResult(status="ok", message=f"Created {config_path}")


class InstallPipeline:
    """Orchestrates global ai-guardrails installation."""

    def __init__(self, options: InstallOptions, global_config_dir: Path) -> None:
        self._options = options
        self._global_config_dir = global_config_dir

    def run(
        self,
        file_manager: FileManager,
        command_runner: CommandRunner,
        config_loader: ConfigLoader,
        console: Console,
    ) -> list[StepResult]:
        ctx = PipelineContext(
            project_dir=Path(),
            file_manager=file_manager,
            command_runner=command_runner,
            config_loader=config_loader,
            console=console,
            languages=[],
            registry=None,
            dry_run=False,
            force=self._options.upgrade,
        )

        steps: list = [
            _CheckPrereqsStep(),
            _InstallGlobalConfigStep(global_config_dir=self._global_config_dir),
        ]

        pipeline = Pipeline(steps=steps)
        return pipeline.run(ctx)
