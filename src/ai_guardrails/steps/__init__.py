"""Pipeline steps for ai-guardrails v1."""

from __future__ import annotations

from ai_guardrails.steps.copy_configs import CopyConfigsStep
from ai_guardrails.steps.detect_languages import DetectLanguagesStep
from ai_guardrails.steps.generate_configs import GenerateConfigsStep
from ai_guardrails.steps.load_registry import LoadRegistryStep
from ai_guardrails.steps.scaffold_registry import ScaffoldRegistryStep
from ai_guardrails.steps.setup_agent_instructions import SetupAgentInstructionsStep
from ai_guardrails.steps.setup_ci import SetupCIStep
from ai_guardrails.steps.setup_hooks import SetupHooksStep
from ai_guardrails.steps.snapshot_step import SnapshotStep

__all__ = [
    "CopyConfigsStep",
    "DetectLanguagesStep",
    "GenerateConfigsStep",
    "LoadRegistryStep",
    "ScaffoldRegistryStep",
    "SetupAgentInstructionsStep",
    "SetupCIStep",
    "SetupHooksStep",
    "SnapshotStep",
]
