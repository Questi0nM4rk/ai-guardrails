"""GeneratePipeline — re-generates all tool configs from exception registry.

Steps: DetectLanguages → LoadRegistry → GenerateConfigs
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
from ai_guardrails.models.language import DetectionRules, LanguageConfig
from ai_guardrails.pipelines.base import Pipeline, PipelineContext, StepResult
from ai_guardrails.steps.detect_languages import DetectLanguagesStep
from ai_guardrails.steps.generate_configs import GenerateConfigsStep
from ai_guardrails.steps.load_registry import LoadRegistryStep

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager


@dataclass
class GenerateOptions:
    """Options for the generate command."""

    check: bool = False
    languages: list[str] | None = None
    dry_run: bool = False


class GeneratePipeline:
    """Orchestrates config regeneration from the exception registry."""

    def __init__(
        self,
        options: GenerateOptions,
        languages_yaml: Path,
        configs_dir: Path,
        lefthook_templates_dir: Path,
    ) -> None:
        self._options = options
        self._languages_yaml = languages_yaml
        self._configs_dir = configs_dir
        self._lefthook_templates_dir = lefthook_templates_dir

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
            force=False,
        )

        # If languages are specified, inject them directly
        if self._options.languages:
            ctx.languages = [
                LanguageConfig(
                    key=lang,
                    name=lang,
                    detect=DetectionRules(files=[], patterns=[], directories=[]),
                    configs=[],
                    hook_template="",
                )
                for lang in self._options.languages
            ]
            steps = [
                LoadRegistryStep(),
                GenerateConfigsStep(generators=self._make_generators()),
            ]
        else:
            steps = [
                DetectLanguagesStep(languages_yaml=self._languages_yaml),
                LoadRegistryStep(),
                GenerateConfigsStep(generators=self._make_generators()),
            ]

        pipeline = Pipeline(steps=steps)  # type: ignore[arg-type]
        return pipeline.run(ctx)
