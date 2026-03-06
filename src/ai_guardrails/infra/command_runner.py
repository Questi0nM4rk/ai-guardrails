"""CommandRunner — wraps subprocess.run.

Never raises on non-zero exit codes; callers decide what to do.
All commands are logged at debug level.
"""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class CommandRunner:
    """Subprocess abstraction with logging and configurable timeout."""

    def run(
        self,
        args: list[str],
        *,
        timeout: int = 30,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command and return CompletedProcess. Never raises on non-zero exit."""
        logger.debug("Running: %s", " ".join(args))
        try:
            return subprocess.run(  # noqa: S603
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
                cwd=cwd,
            )
        except (FileNotFoundError, PermissionError) as exc:
            return subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr=str(exc),
            )
