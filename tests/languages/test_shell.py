"""Tests for ShellPlugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.languages.shell import ShellPlugin
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


def test_shell_plugin_key(tmp_path: Path) -> None:
    assert ShellPlugin(tmp_path).key == "shell"


def test_shell_plugin_name(tmp_path: Path) -> None:
    assert ShellPlugin(tmp_path).name == "Shell"


def test_shell_detect_by_sh_file(tmp_path: Path) -> None:
    (tmp_path / "run.sh").write_text("#!/bin/sh\n")
    assert ShellPlugin(tmp_path).detect(tmp_path) is True


def test_shell_detect_by_bash_file(tmp_path: Path) -> None:
    (tmp_path / "install.bash").write_text("#!/usr/bin/env bash\n")
    assert ShellPlugin(tmp_path).detect(tmp_path) is True


def test_shell_detect_false_for_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    assert ShellPlugin(tmp_path).detect(tmp_path) is False


def test_shell_copy_files_is_empty(tmp_path: Path) -> None:
    assert ShellPlugin(tmp_path).copy_files == []


def test_shell_generate_returns_empty(tmp_path: Path) -> None:
    outputs = ShellPlugin(tmp_path).generate(_empty_registry(), tmp_path)
    assert outputs == {}
