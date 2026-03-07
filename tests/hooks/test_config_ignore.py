"""Tests for config_ignore hook."""

from __future__ import annotations

from unittest.mock import patch

from ai_guardrails.hooks.config_ignore import (
    _is_config_file,
    main,
)

# ---------------------------------------------------------------------------
# _is_config_file
# ---------------------------------------------------------------------------


def test_is_config_file_pyproject():
    assert _is_config_file("pyproject.toml") is True


def test_is_config_file_setup_cfg():
    assert _is_config_file("setup.cfg") is True


def test_is_config_file_eslintrc():
    assert _is_config_file(".eslintrc.json") is True


def test_is_config_file_main_py():
    assert _is_config_file("main.py") is False


def test_is_config_file_tsconfig():
    assert _is_config_file("tsconfig.json") is True


# ---------------------------------------------------------------------------
# main() — integration with subprocess injection
# ---------------------------------------------------------------------------


def test_main_no_staged_files_returns_zero():
    with patch("ai_guardrails.hooks.config_ignore._staged_files", return_value=[]):
        assert main() == 0


def test_main_no_config_files_in_staged_returns_zero():
    with patch(
        "ai_guardrails.hooks.config_ignore._staged_files",
        return_value=["src/main.py", "README.md"],
    ):
        assert main() == 0


def test_main_ignore_pattern_in_pyproject_returns_one(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\n")

    with (
        patch(
            "ai_guardrails.hooks.config_ignore._staged_files",
            return_value=[str(pyproject)],
        ),
        patch(
            "ai_guardrails.hooks.config_ignore._added_lines_for",
            return_value=['+ignore = ["E501"]'],
        ),
        patch(
            "ai_guardrails.hooks.config_ignore.has_hash_header",
            return_value=False,
        ),
    ):
        result = main()

    assert result == 1
    captured = capsys.readouterr()
    assert "ignore" in captured.out.lower() or "pattern" in captured.out.lower()


def test_main_generated_file_skipped(tmp_path):
    ruff = tmp_path / "ruff.toml"
    ruff.write_text('# ai-guardrails:hash:sha256:abc123\n[lint]\nignore = ["E501"]\n')

    with (
        patch(
            "ai_guardrails.hooks.config_ignore._staged_files",
            return_value=[str(ruff)],
        ),
        patch(
            "ai_guardrails.hooks.config_ignore._added_lines_for",
            return_value=['+ignore = ["E501"]'],
        ),
        patch(
            "ai_guardrails.hooks.config_ignore.has_hash_header",
            return_value=True,
        ),
    ):
        result = main()

    # Generated files are skipped — ignore pattern should not be flagged
    assert result == 0


def test_main_clean_diff_returns_zero(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\n")

    with (
        patch(
            "ai_guardrails.hooks.config_ignore._staged_files",
            return_value=[str(pyproject)],
        ),
        patch(
            "ai_guardrails.hooks.config_ignore._added_lines_for",
            return_value=["+line-length = 100"],
        ),
        patch(
            "ai_guardrails.hooks.config_ignore.has_hash_header",
            return_value=False,
        ),
    ):
        result = main()

    assert result == 0


def test_main_nonexistent_file_skipped(tmp_path):
    missing = str(tmp_path / "nonexistent.toml")

    with (
        patch(
            "ai_guardrails.hooks.config_ignore._staged_files",
            return_value=[missing],
        ),
    ):
        result = main()

    assert result == 0


def test_main_empty_added_lines_returns_zero(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\n")

    with (
        patch(
            "ai_guardrails.hooks.config_ignore._staged_files",
            return_value=[str(pyproject)],
        ),
        patch(
            "ai_guardrails.hooks.config_ignore._added_lines_for",
            return_value=[],
        ),
        patch(
            "ai_guardrails.hooks.config_ignore.has_hash_header",
            return_value=False,
        ),
    ):
        result = main()

    assert result == 0
