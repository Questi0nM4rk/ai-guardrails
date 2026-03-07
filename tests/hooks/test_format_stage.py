"""Tests for format_stage hook."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_guardrails.hooks.format_stage import (
    _detect_shell_by_shebang,
    _formatters_for,
    main,
)

# ---------------------------------------------------------------------------
# _detect_shell_by_shebang
# ---------------------------------------------------------------------------


def test_detect_shell_by_shebang_bash(tmp_path):
    f = tmp_path / "script"
    f.write_bytes(b"#!/bin/bash\necho hi\n")
    assert _detect_shell_by_shebang(str(f)) is True


def test_detect_shell_by_shebang_sh(tmp_path):
    f = tmp_path / "script"
    f.write_bytes(b"#!/bin/sh\necho hi\n")
    assert _detect_shell_by_shebang(str(f)) is True


def test_detect_shell_by_shebang_env_bash(tmp_path):
    f = tmp_path / "script"
    f.write_bytes(b"#!/usr/bin/env bash\necho hi\n")
    assert _detect_shell_by_shebang(str(f)) is True


def test_detect_shell_by_shebang_python_not_shell(tmp_path):
    f = tmp_path / "script"
    f.write_bytes(b"#!/usr/bin/env python3\nprint('hi')\n")
    assert _detect_shell_by_shebang(str(f)) is False


def test_detect_shell_by_shebang_no_shebang(tmp_path):
    f = tmp_path / "script"
    f.write_bytes(b"echo hi\n")
    assert _detect_shell_by_shebang(str(f)) is False


def test_detect_shell_by_shebang_missing_file():
    assert _detect_shell_by_shebang("/nonexistent/file") is False


# ---------------------------------------------------------------------------
# _formatters_for
# ---------------------------------------------------------------------------


def test_formatters_for_py(tmp_path):
    f = tmp_path / "foo.py"
    f.write_text("")
    result = _formatters_for(str(f))
    assert result is not None
    assert any("ruff" in cmd[0] for cmd in result)


def test_formatters_for_ts(tmp_path):
    f = tmp_path / "foo.ts"
    f.write_text("")
    result = _formatters_for(str(f))
    assert result is not None
    assert any("biome" in cmd[0] for cmd in result)


def test_formatters_for_unknown_extension(tmp_path):
    f = tmp_path / "foo.xyz"
    f.write_text("")
    assert _formatters_for(str(f)) is None


def test_formatters_for_shell_shebang(tmp_path):
    f = tmp_path / "script"
    f.write_bytes(b"#!/bin/bash\necho hi\n")
    result = _formatters_for(str(f))
    assert result is not None
    assert any("shfmt" in cmd[0] for cmd in result)


# ---------------------------------------------------------------------------
# main() — with subprocess injection
# ---------------------------------------------------------------------------


def test_main_no_staged_files_returns_zero():
    with patch("ai_guardrails.hooks.format_stage._git_staged_files", return_value=[]):
        assert main() == 0


def test_main_formats_and_restages_modified_file(tmp_path):
    py_file = tmp_path / "foo.py"
    py_file.write_text("x=1\n")

    def fake_staged():
        return [str(py_file)]

    def fake_formatter(cmd, filepath):
        # Simulate formatter modifying the file
        Path(filepath).write_text("x = 1\n")

    add_calls: list[str] = []

    def fake_add(filepath):
        add_calls.append(filepath)

    with (
        patch(
            "ai_guardrails.hooks.format_stage._git_staged_files",
            side_effect=fake_staged,
        ),
        patch(
            "ai_guardrails.hooks.format_stage._run_formatter",
            side_effect=fake_formatter,
        ),
        patch("ai_guardrails.hooks.format_stage._git_add", side_effect=fake_add),
    ):
        result = main()

    assert result == 0
    assert str(py_file) in add_calls


def test_main_does_not_restage_unmodified_file(tmp_path):
    py_file = tmp_path / "foo.py"
    py_file.write_text("x = 1\n")

    def fake_staged():
        return [str(py_file)]

    def fake_formatter(cmd, filepath):
        pass  # no change

    add_calls: list[str] = []

    def fake_add(filepath):
        add_calls.append(filepath)

    with (
        patch(
            "ai_guardrails.hooks.format_stage._git_staged_files",
            side_effect=fake_staged,
        ),
        patch(
            "ai_guardrails.hooks.format_stage._run_formatter",
            side_effect=fake_formatter,
        ),
        patch("ai_guardrails.hooks.format_stage._git_add", side_effect=fake_add),
    ):
        result = main()

    assert result == 0
    assert add_calls == []


def test_main_skips_missing_file(tmp_path):
    missing = str(tmp_path / "ghost.py")

    with patch(
        "ai_guardrails.hooks.format_stage._git_staged_files", return_value=[missing]
    ):
        result = main()

    assert result == 0


def test_main_skips_unknown_extension(tmp_path):
    f = tmp_path / "data.xyz"
    f.write_text("stuff")

    add_calls: list[str] = []

    with (
        patch(
            "ai_guardrails.hooks.format_stage._git_staged_files", return_value=[str(f)]
        ),
        patch(
            "ai_guardrails.hooks.format_stage._git_add", side_effect=add_calls.append
        ),
    ):
        result = main()

    assert result == 0
    assert add_calls == []
