"""GeneratePipeline — re-generates all tool configs from exception registry.

Steps: DetectLanguages → LoadRegistry → GenerateConfigs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai_guardrails.languages._registry import discover_plugins
from ai_guardrails.pipelines.base import Pipeline, PipelineContext, StepResult
from ai_guardrails.steps.detect_languages import DetectLanguagesStep
from ai_guardrails.steps.generate_agent_rules import GenerateAgentRulesStep
from ai_guardrails.steps.generate_configs import GenerateConfigsStep
from ai_guardrails.steps.load_registry import LoadRegistryStep
from ai_guardrails.steps.validate_governance import ValidateGovernanceStep

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager
    from ai_guardrails.languages._base import LanguagePlugin
    from ai_guardrails.pipelines.base import PipelineStep


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
            check=self._options.check,
        )

        # If languages are specified, inject selected plugins matching by key
        if self._options.languages:
            all_plugins = self._get_plugins()
            plugin_map = {p.key: p for p in all_plugins}

            # M-5: Validate language keys
            unknown = [k for k in self._options.languages if k not in plugin_map]
            if unknown:
                return [
                    StepResult(
                        status="error",
                        message=f"Unknown language(s): {', '.join(unknown)}. "
                        f"Available: {', '.join(sorted(plugin_map.keys()))}",
                    )
                ]

            # B-1: Always include universal plugin
            selected: list[LanguagePlugin] = [
                p for p in all_plugins if p.key == "universal"
            ]
            selected.extend(
                plugin_map[k]
                for k in self._options.languages
                if k != "universal" and k in plugin_map
            )
            # "universal" excluded above: already prepended, avoiding double-inclusion.
            ctx.languages = selected
            steps: list[PipelineStep] = [
                LoadRegistryStep(),
                ValidateGovernanceStep(),
                GenerateConfigsStep(),
                GenerateAgentRulesStep(),
            ]
        else:
            plugins = self._get_plugins()
            steps = [
                DetectLanguagesStep(plugins=plugins),
                LoadRegistryStep(),
                ValidateGovernanceStep(),
                GenerateConfigsStep(),
                GenerateAgentRulesStep(),
            ]

        pipeline = Pipeline(steps=steps)
        return pipeline.run(ctx)
