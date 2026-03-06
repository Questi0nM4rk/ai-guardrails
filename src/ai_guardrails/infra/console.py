"""Console — all user-facing output.

Auto-detects TTY for ANSI colors. Supports quiet mode that suppresses
info/success messages. Never uses print() directly elsewhere in the codebase.
"""

from __future__ import annotations

import sys
from typing import TextIO

# ANSI escape codes
_RESET = "\033[0m"
_GREEN = "\033[0;32m"
_YELLOW = "\033[1;33m"
_RED = "\033[0;31m"
_BLUE = "\033[0;34m"
_BOLD = "\033[1m"


class Console:
    """All user-facing output goes through this class."""

    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        quiet: bool = False,
    ) -> None:
        self._stream: TextIO = stream if stream is not None else sys.stdout
        self.quiet = quiet

    @property
    def _use_color(self) -> bool:
        return hasattr(self._stream, "isatty") and self._stream.isatty()

    def _colorize(self, text: str, code: str) -> str:
        if self._use_color:
            return f"{code}{text}{_RESET}"
        return text

    def info(self, text: str) -> None:
        """Print an informational message. Suppressed in quiet mode."""
        if self.quiet:
            return
        print(text, file=self._stream)

    def success(self, text: str) -> None:
        """Print a success message. Suppressed in quiet mode."""
        if self.quiet:
            return
        print(self._colorize(text, _GREEN), file=self._stream)

    def warning(self, text: str) -> None:
        """Print a warning. Always shown even in quiet mode."""
        print(self._colorize(text, _YELLOW), file=self._stream)

    def error(self, text: str) -> None:
        """Print an error. Always shown even in quiet mode."""
        print(self._colorize(text, _RED), file=self._stream)

    def step(self, text: str) -> None:
        """Print a pipeline step progress indicator."""
        print(self._colorize(text, _BOLD), file=self._stream)
