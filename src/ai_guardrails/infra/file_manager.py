"""FileManager — wraps all filesystem operations.

Supports dry-run mode (no disk writes) and treats all paths as Path objects.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class FileManager:
    """Filesystem abstraction that supports dry-run mode."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def read_text(self, path: Path) -> str:
        """Read a file and return its text content."""
        if not path.exists():
            raise FileNotFoundError(path)
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> str | None:
        """Write text to a file. In dry-run, returns a description instead."""
        if self.dry_run:
            return f"would write {path}"
        path.write_text(content, encoding="utf-8")
        return None

    def copy(self, src: Path, dst: Path) -> str | None:
        """Copy a file from src to dst. In dry-run, returns a description instead."""
        if self.dry_run:
            return f"would copy {src} -> {dst}"
        shutil.copy2(src, dst)
        return None

    def exists(self, path: Path) -> bool:
        """Return True if the path exists."""
        return path.exists()

    def glob(self, directory: Path, pattern: str) -> list[Path]:
        """Return paths matching pattern relative to directory."""
        return sorted(directory.glob(pattern))

    def mkdir(
        self, path: Path, *, parents: bool = False, exist_ok: bool = False
    ) -> str | None:
        """Create a directory. In dry-run, returns a description instead."""
        if self.dry_run:
            return f"would create directory {path}"
        if not exist_ok and path.exists():
            raise FileExistsError(path)
        path.mkdir(parents=parents, exist_ok=exist_ok)
        return None

    def symlink(self, link: Path, target: str) -> str | None:
        """Create a symlink. In dry-run, returns a description instead."""
        if self.dry_run:
            return f"would symlink {link} -> {target}"
        if not link.exists():
            link.symlink_to(target)
        return None

    def append_text(self, path: Path, text: str) -> str | None:
        """Append text to a file (creates if absent). Dry-run returns description."""
        if self.dry_run:
            return f"would append to {path}"
        with path.open("a", encoding="utf-8") as f:
            f.write(text)
        return None
