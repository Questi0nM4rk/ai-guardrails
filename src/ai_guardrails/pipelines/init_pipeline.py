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

from ai_guardrails.generators.claude_settings import ClaudeSettingsGenerator
from ai_guardrails.generators.codespell import CodespellGenerator
from ai_guardrails.generators.editorconfig import EditorconfigGenerator
from ai_guardrails.generators.lefthook import LefthookGenerator
from ai_guardrails.generators.markdownlint import MarkdownlintGenerator
from ai_guardrails.generators.ruff import RuffGenerator
from ai_guardrails.pipelines.base import Pipeline, PipelineContext, StepResult
from ai_guardrails.steps.copy_configs import CopyConfigsStep
from ai_guardrails.steps.detect_languages import DetectLanguagesStep
from ai_guardrails.steps.generate_configs import GenerateConfigsStep
from ai_guardrails.steps.load_registry import LoadRegistryStep
from ai_guardrails.steps.scaffold_registry import ScaffoldRegistryStep
from ai_guardrails.steps.setup_agent_instructions import SetupAgentInstructionsStep
from ai_guardrails.steps.setup_ci import SetupCIStep

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager


@dataclass
class InitOptions:
    """Options for the init command."""

    force: bool = False
    no_hooks: bool = False
    no_ci: bool = False
    no_agent_instructions: bool = False
    dry_run: bool = False


class InitPipeline:
    """Orchestrates full project initialization."""

    def __init__(
        self,
        options: InitOptions,
        languages_yaml: Path,
        configs_dir: Path,
        lefthook_templates_dir: Path,
        registry_template: Path,
        ci_template: Path,
        agent_template: Path,
    ) -> None:
        self._options = options
        self._languages_yaml = languages_yaml
        self._configs_dir = configs_dir
        self._lefthook_templates_dir = lefthook_templates_dir
        self._registry_template = registry_template
        self._ci_template = ci_template
        self._agent_template = agent_template

    def _make_generators(self) -> list:  # type: ignore[type-arg]
        return [
            RuffGenerator(configs_dir=self._configs_dir),
            MarkdownlintGenerator(configs_dir=self._configs_dir),
            CodespellGenerator(),
            EditorconfigGenerator(configs_dir=self._configs_dir),
            LefthookGenerator(templates_dir=self._lefthook_templates_dir),
            ClaudeSettingsGenerator(),
        ]

    def run(
        self,
        project_dir: Path,
        file_manager: FileManager,
        command_runner: CommandRunner,
        config_loader: ConfigLoader,
        console: Console,
    ) -> list[StepResult]:
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
            DetectLanguagesStep(languages_yaml=self._languages_yaml),
            CopyConfigsStep(configs_dir=self._configs_dir),
            ScaffoldRegistryStep(template_path=self._registry_template),
            LoadRegistryStep(),
            GenerateConfigsStep(generators=self._make_generators()),
        ]

        if not self._options.no_ci:
            steps.append(SetupCIStep(template_path=self._ci_template))

        if not self._options.no_agent_instructions:
            steps.append(SetupAgentInstructionsStep(template_path=self._agent_template))

        pipeline = Pipeline(steps=steps)
        return pipeline.run(ctx)
