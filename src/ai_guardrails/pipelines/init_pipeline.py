"""InitPipeline — full per-project setup.

Steps:
  1. DetectLanguages
  2. CopyConfigs (language-specific base configs)
  3. ScaffoldRegistry (create .guardrails-exceptions.toml)
  4. LoadRegistry
  5. GenerateConfigs
  6. SetupCI (if not --no-ci)
  7. SetupAgentInstructions (if not --no-agent-instructions)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai_guardrails.infra.profile_loader import load_profile
from ai_guardrails.infra.prompt_ui import ask_yes_no
from ai_guardrails.languages._registry import discover_plugins
from ai_guardrails.pipelines.base import Pipeline, PipelineContext, StepResult
from ai_guardrails.steps.copy_configs import CopyConfigsStep
from ai_guardrails.steps.detect_languages import DetectLanguagesStep
from ai_guardrails.steps.generate_agent_rules import GenerateAgentRulesStep
from ai_guardrails.steps.generate_configs import GenerateConfigsStep
from ai_guardrails.steps.load_registry import LoadRegistryStep
from ai_guardrails.steps.scaffold_registry import ScaffoldRegistryStep
from ai_guardrails.steps.setup_agent_instructions import SetupAgentInstructionsStep
from ai_guardrails.steps.setup_ci import SetupCIStep
from ai_guardrails.steps.setup_hooks import SetupHooksStep

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager
    from ai_guardrails.languages._base import LanguagePlugin


@dataclass
class InitOptions:
    """Options for the init command."""

    force: bool = False
    no_hooks: bool = False
    no_ci: bool = False
    no_agent_instructions: bool = False
    dry_run: bool = False
    profile: str = "standard"
    interactive: bool = False


class InitPipeline:
    """Orchestrates full project initialization."""

    def __init__(  # noqa: PLR0913
        self,
        options: InitOptions,
        data_dir: Path,
        configs_dir: Path,
        registry_template: Path,
        ci_template: Path,
        agent_template: Path,
        custom_plugins_dir: Path | None = None,
    ) -> None:
        self._options = options
        self._data_dir = data_dir
        self._configs_dir = configs_dir
        self._registry_template = registry_template
        self._ci_template = ci_template
        self._agent_template = agent_template
        self._custom_plugins_dir = custom_plugins_dir

    def _get_plugins(self) -> list[LanguagePlugin]:
        return discover_plugins(self._data_dir, custom_dir=self._custom_plugins_dir)

    def run(
        self,
        project_dir: Path,
        file_manager: FileManager,
        command_runner: CommandRunner,
        config_loader: ConfigLoader,
        console: Console,
    ) -> list[StepResult]:
        try:
            load_profile(self._options.profile)
        except ValueError as exc:
            return [StepResult(status="error", message=str(exc))]

        plugins = self._get_plugins()
        ctx = PipelineContext(
            project_dir=project_dir,
            file_manager=file_manager,
            command_runner=command_runner,
            config_loader=config_loader,
            console=console,
            languages=[],
            registry=None,
            dry_run=self._options.dry_run,
            force=self._options.force,
        )

        steps: list = [
            DetectLanguagesStep(plugins=plugins),
            CopyConfigsStep(configs_dir=self._configs_dir),
            ScaffoldRegistryStep(template_path=self._registry_template),
            LoadRegistryStep(),
            GenerateConfigsStep(),
        ]

        run_hooks = not self._options.no_hooks
        run_ci = not self._options.no_ci
        run_agent = not self._options.no_agent_instructions

        if self._options.interactive:
            try:
                if run_hooks:
                    run_hooks = ask_yes_no("Install lefthook hooks?")
                if run_ci:
                    run_ci = ask_yes_no("Generate CI workflow?")
                if run_agent:
                    run_agent = ask_yes_no("Install Claude Code agent instructions?")
            except EOFError:
                pass  # non-TTY pipe with --interactive: use defaults

        if run_hooks:
            steps.append(SetupHooksStep())

        if run_ci:
            steps.append(SetupCIStep(template_path=self._ci_template))

        if run_agent:
            steps.append(SetupAgentInstructionsStep(template_path=self._agent_template))
            steps.append(GenerateAgentRulesStep())

        pipeline = Pipeline(steps=steps)
        return pipeline.run(ctx)
