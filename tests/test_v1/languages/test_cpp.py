"""Tests for CppPlugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.languages.cpp import CppPlugin
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


def test_cpp_plugin_key(tmp_path: Path) -> None:
    assert CppPlugin(tmp_path).key == "cpp"


def test_cpp_plugin_name(tmp_path: Path) -> None:
    assert CppPlugin(tmp_path).name == "C/C++"


def test_cpp_detect_by_cmake(tmp_path: Path) -> None:
    (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.20)\n")
    assert CppPlugin(tmp_path).detect(tmp_path) is True


def test_cpp_detect_by_cpp_file(tmp_path: Path) -> None:
    (tmp_path / "main.cpp").write_text("int main() {}\n")
    assert CppPlugin(tmp_path).detect(tmp_path) is True


def test_cpp_detect_by_c_file(tmp_path: Path) -> None:
    (tmp_path / "lib.c").write_text("#include <stdio.h>\n")
    assert CppPlugin(tmp_path).detect(tmp_path) is True


def test_cpp_detect_false_for_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    assert CppPlugin(tmp_path).detect(tmp_path) is False


def test_cpp_copy_files_includes_expected(tmp_path: Path) -> None:
    copy = CppPlugin(tmp_path).copy_files
    assert ".clang-format" in copy
    assert ".clang-tidy" in copy


def test_cpp_hook_config_has_format_command(tmp_path: Path) -> None:
    config = CppPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "clang-format-and-stage" in commands


def test_cpp_hook_config_has_clang_tidy(tmp_path: Path) -> None:
    config = CppPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "clang-tidy" in commands


def test_cpp_generate_returns_empty(tmp_path: Path) -> None:
    outputs = CppPlugin(tmp_path).generate(_empty_registry(), tmp_path)
    assert outputs == {}
