"""Tests for StatusPipeline — smoke test that the pipeline runs end-to-end."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.status_pipeline import StatusPipeline
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_DATA_DIR = Path(__file__).parents[3] / "src" / "ai_guardrails" / "_data"

_MINIMAL_REGISTRY = """\
schema_version = 1

[global_rules]

[custom]
"""


def test_status_pipeline_runs_without_error(tmp_path: Path) -> None:
    """StatusPipeline completes all steps and returns ok results."""
    runner = FakeCommandRunner()
    runner.register(["lefthook", "version"], returncode=0, stdout="lefthook 1.13.6")

    fm = FakeFileManager()
    fm.seed(tmp_path / ".guardrails-exceptions.toml", _MINIMAL_REGISTRY)

    pipeline = StatusPipeline(data_dir=_DATA_DIR)
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    assert isinstance(results, list)
    assert len(results) > 0
    # StatusStep always returns ok — final result must not be error
    assert results[-1].status == "ok"
