"""Tests for Console infrastructure."""

from __future__ import annotations

import io

from ai_guardrails.infra.console import Console


def _make_console(
    *, tty: bool = False, quiet: bool = False
) -> tuple[Console, io.StringIO]:
    stream = io.StringIO()
    # Simulate TTY by patching isatty
    stream.isatty = lambda: tty  # type: ignore[method-assign]
    console = Console(stream=stream, quiet=quiet)
    return console, stream


def test_info_writes_to_stream() -> None:
    console, stream = _make_console()
    console.info("hello info")
    assert "hello info" in stream.getvalue()


def test_success_writes_to_stream() -> None:
    console, stream = _make_console()
    console.success("all good")
    assert "all good" in stream.getvalue()


def test_warning_writes_to_stream() -> None:
    console, stream = _make_console()
    console.warning("watch out")
    assert "watch out" in stream.getvalue()


def test_error_writes_to_stream() -> None:
    console, stream = _make_console()
    console.error("something failed")
    assert "something failed" in stream.getvalue()


def test_step_writes_to_stream() -> None:
    console, stream = _make_console()
    console.step("doing step 1")
    assert "doing step 1" in stream.getvalue()


def test_quiet_mode_suppresses_info() -> None:
    console, stream = _make_console(quiet=True)
    console.info("suppressed info")
    assert "suppressed info" not in stream.getvalue()


def test_quiet_mode_suppresses_success() -> None:
    console, stream = _make_console(quiet=True)
    console.success("suppressed success")
    assert "suppressed success" not in stream.getvalue()


def test_quiet_mode_keeps_warnings() -> None:
    console, stream = _make_console(quiet=True)
    console.warning("important warning")
    assert "important warning" in stream.getvalue()


def test_quiet_mode_keeps_errors() -> None:
    console, stream = _make_console(quiet=True)
    console.error("critical error")
    assert "critical error" in stream.getvalue()


def test_tty_mode_includes_ansi_codes() -> None:
    console, stream = _make_console(tty=True)
    console.success("colored output")
    output = stream.getvalue()
    # ANSI escape codes start with ESC
    assert "\033[" in output


def test_non_tty_no_ansi_codes() -> None:
    console, stream = _make_console(tty=False)
    console.success("plain output")
    output = stream.getvalue()
    assert "\033[" not in output
