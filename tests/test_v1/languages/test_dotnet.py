"""Tests for DotnetPlugin."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.languages.dotnet import DotnetPlugin
from ai_guardrails.models.registry import ExceptionRegistry


def _empty_registry() -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


def test_dotnet_plugin_key(tmp_path: Path) -> None:
    assert DotnetPlugin(tmp_path).key == "dotnet"


def test_dotnet_plugin_name(tmp_path: Path) -> None:
    assert DotnetPlugin(tmp_path).name == "C#/.NET"


def test_dotnet_detect_by_csproj(tmp_path: Path) -> None:
    (tmp_path / "App.csproj").write_text("<Project Sdk='Microsoft.NET.Sdk'/>\n")
    assert DotnetPlugin(tmp_path).detect(tmp_path) is True


def test_dotnet_detect_by_sln(tmp_path: Path) -> None:
    (tmp_path / "App.sln").write_text("")
    assert DotnetPlugin(tmp_path).detect(tmp_path) is True


def test_dotnet_detect_false_for_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    assert DotnetPlugin(tmp_path).detect(tmp_path) is False


def test_dotnet_copy_files_includes_expected(tmp_path: Path) -> None:
    copy = DotnetPlugin(tmp_path).copy_files
    assert "Directory.Build.props" in copy
    assert ".globalconfig" in copy


def test_dotnet_hook_config_has_format_command(tmp_path: Path) -> None:
    config = DotnetPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "dotnet-format-and-stage" in commands


def test_dotnet_hook_config_has_build(tmp_path: Path) -> None:
    config = DotnetPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "dotnet-build" in commands


def test_dotnet_generate_returns_empty(tmp_path: Path) -> None:
    outputs = DotnetPlugin(tmp_path).generate(_empty_registry(), tmp_path)
    assert outputs == {}
