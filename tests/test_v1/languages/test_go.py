"""Tests for GoPlugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.languages.go import GoPlugin
from ai_guardrails.models.registry import ExceptionRegistry

if TYPE_CHECKING:
    from pathlib import Path


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


def test_go_plugin_key(tmp_path: Path) -> None:
    assert GoPlugin(tmp_path).key == "go"


def test_go_plugin_name(tmp_path: Path) -> None:
    assert GoPlugin(tmp_path).name == "Go"


def test_go_detect_by_go_mod(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/foo\n")
    assert GoPlugin(tmp_path).detect(tmp_path) is True


def test_go_detect_by_go_file(tmp_path: Path) -> None:
    (tmp_path / "main.go").write_text("package main\n")
    assert GoPlugin(tmp_path).detect(tmp_path) is True


def test_go_detect_false_for_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    assert GoPlugin(tmp_path).detect(tmp_path) is False


def test_go_copy_files_is_empty(tmp_path: Path) -> None:
    assert GoPlugin(tmp_path).copy_files == []


def test_go_hook_config_has_format_command(tmp_path: Path) -> None:
    config = GoPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "go-format-and-stage" in commands


def test_go_hook_config_has_go_vet(tmp_path: Path) -> None:
    config = GoPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "go-vet" in commands


def test_go_generate_returns_empty(tmp_path: Path) -> None:
    outputs = GoPlugin(tmp_path).generate(_empty_registry(), tmp_path)
    assert outputs == {}
