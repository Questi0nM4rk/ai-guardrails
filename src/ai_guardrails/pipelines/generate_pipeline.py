"""GeneratePipeline — re-generates all tool configs from exception registry.

Steps: DetectLanguages → LoadRegistry → GenerateConfigs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai_guardrails.languages._base import BaseLanguagePlugin
from ai_guardrails.languages._registry import discover_plugins
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
    from ai_guardrails.languages._base import LanguagePlugin


@dataclass
class GenerateOptions:
    """Options for the generate command."""

    check: bool = False
    languages: list[str] | None = None
    dry_run: bool = False


class _ExplicitLanguagePlugin(BaseLanguagePlugin):
    """Synthetic plugin representing an explicitly specified language key."""

    def __init__(self, key: str) -> None:
        self.key = key
        self.name = key
        self.copy_files: list[str] = []
        self.generated_configs: list[str] = []

    def detect(self, project_dir: Path) -> bool:
        return True


class GeneratePipeline:
    """Orchestrates config regeneration from the exception registry."""

    def __init__(
        self,
        options: GenerateOptions,
        data_dir: Path,
        custom_plugins_dir: Path | None = None,
    ) -> None:
        self._options = options
        self._data_dir = data_dir
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

        # If languages are specified, inject synthetic plugins matching by key
        if self._options.languages:
            all_plugins = self._get_plugins()
            plugin_map = {p.key: p for p in all_plugins}
            selected: list[LanguagePlugin] = []
            for lang_key in self._options.languages:
                if lang_key in plugin_map:
                    selected.append(plugin_map[lang_key])
                else:
                    selected.append(_ExplicitLanguagePlugin(lang_key))
            ctx.languages = selected
            steps: list = [
                LoadRegistryStep(),
                GenerateConfigsStep(),
            ]
        else:
            plugins = self._get_plugins()
            steps = [
                DetectLanguagesStep(plugins=plugins),
                LoadRegistryStep(),
                GenerateConfigsStep(),
            ]

        pipeline = Pipeline(steps=steps)
        return pipeline.run(ctx)
