"""Tests for prompt_ui — TTY detection and Y/N prompt helpers."""

from __future__ import annotations

from unittest.mock import patch

from ai_guardrails.infra.prompt_ui import ask_yes_no, is_tty


def test_is_tty_returns_bool() -> None:
    result = is_tty()
    assert isinstance(result, bool)


def test_is_tty_false_when_stdin_not_tty() -> None:
    with (
        patch("ai_guardrails.infra.prompt_ui.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = False
        mock_sys.stdout.isatty.return_value = True
        assert is_tty() is False


def test_is_tty_false_when_stdout_not_tty() -> None:
    with (
        patch("ai_guardrails.infra.prompt_ui.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = False
        assert is_tty() is False


def test_is_tty_true_when_both_tty() -> None:
    with (
        patch("ai_guardrails.infra.prompt_ui.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        assert is_tty() is True


def test_ask_yes_no_yes_input_returns_true() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", return_value="y"):
        assert ask_yes_no("Install hooks?") is True


def test_ask_yes_no_yes_uppercase_returns_true() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", return_value="Y"):
        assert ask_yes_no("Install hooks?") is True


def test_ask_yes_no_yes_word_returns_true() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", return_value="yes"):
        assert ask_yes_no("Install hooks?") is True


def test_ask_yes_no_no_input_returns_false() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", return_value="n"):
        assert ask_yes_no("Install hooks?") is False


def test_ask_yes_no_no_uppercase_returns_false() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", return_value="N"):
        assert ask_yes_no("Install hooks?") is False


def test_ask_yes_no_no_word_returns_false() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", return_value="no"):
        assert ask_yes_no("Install hooks?") is False


def test_ask_yes_no_empty_input_uses_default_true() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", return_value=""):
        assert ask_yes_no("Install hooks?", default=True) is True


def test_ask_yes_no_empty_input_uses_default_false() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", return_value=""):
        assert ask_yes_no("Install hooks?", default=False) is False


def test_ask_yes_no_eof_raises() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", side_effect=EOFError):
        try:
            ask_yes_no("Install hooks?")
            raised = False
        except EOFError:
            raised = True
    assert raised, "ask_yes_no should re-raise EOFError"


def test_ask_yes_no_whitespace_stripped() -> None:
    with patch("ai_guardrails.infra.prompt_ui.input", return_value="  y  "):
        assert ask_yes_no("Install hooks?") is True
