"""Tests for RustPlugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.languages.rust import RustPlugin
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


def test_rust_plugin_key(tmp_path: Path) -> None:
    assert RustPlugin(tmp_path).key == "rust"


def test_rust_plugin_name(tmp_path: Path) -> None:
    assert RustPlugin(tmp_path).name == "Rust"


def test_rust_detect_by_cargo_toml(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'\n")
    assert RustPlugin(tmp_path).detect(tmp_path) is True


def test_rust_detect_by_rs_file(tmp_path: Path) -> None:
    (tmp_path / "main.rs").write_text("fn main() {}\n")
    assert RustPlugin(tmp_path).detect(tmp_path) is True


def test_rust_detect_false_for_python_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    assert RustPlugin(tmp_path).detect(tmp_path) is False


def test_rust_copy_files_includes_rustfmt(tmp_path: Path) -> None:
    assert "rustfmt.toml" in RustPlugin(tmp_path).copy_files


def test_rust_hook_config_has_format_command(tmp_path: Path) -> None:
    config = RustPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "rust-format-and-stage" in commands


def test_rust_hook_config_has_clippy(tmp_path: Path) -> None:
    config = RustPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "cargo-clippy" in commands


def test_rust_generate_returns_empty(tmp_path: Path) -> None:
    outputs = RustPlugin(tmp_path).generate(_empty_registry(), tmp_path)
    assert outputs == {}
