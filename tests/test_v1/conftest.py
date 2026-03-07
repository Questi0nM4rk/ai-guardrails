"""Shared fakes and fixtures for test_v1 suite."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# FakeFileManager
# ---------------------------------------------------------------------------


class FakeFileManager:
    """In-memory filesystem double for unit tests."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._files: dict[Path, str] = {}
        self._dirs: set[Path] = set()
        self.written: list[tuple[Path, str]] = []
        self.copied: list[tuple[Path, Path]] = []
        self.symlinked: list[tuple[Path, str]] = []

    def read_text(self, path: Path) -> str:
        if path not in self._files:
            raise FileNotFoundError(path)
        return self._files[path]

    def write_text(self, path: Path, content: str) -> str | None:
        if self.dry_run:
            return f"would write {path}"
        self._files[path] = content
        self.written.append((path, content))
        return None

    def copy(self, src: Path, dst: Path) -> str | None:
        if self.dry_run:
            return f"would copy {src} -> {dst}"
        content = self.read_text(src)
        self._files[dst] = content
        self.copied.append((src, dst))
        return None

    def exists(self, path: Path) -> bool:
        return path in self._files or path in self._dirs

    def glob(self, directory: Path, pattern: str) -> list[Path]:
        results = []
        for p in self._files:
            try:
                p.relative_to(directory)
                if p.match(pattern):
                    results.append(p)
            except ValueError:
                pass
        return sorted(results)

    def mkdir(
        self, path: Path, *, parents: bool = False, exist_ok: bool = False
    ) -> str | None:
        if self.dry_run:
            return f"would create directory {path}"
        if not exist_ok and path in self._dirs:
            raise FileExistsError(path)
        self._dirs.add(path)
        return None

    def symlink(self, link: Path, target: str) -> str | None:
        if self.dry_run:
            return f"would symlink {link} -> {target}"
        if not self.exists(link):
            self._files[link] = f"-> {target}"
            self.symlinked.append((link, target))
        return None

    def append_text(self, path: Path, text: str) -> str | None:
        if self.dry_run:
            return f"would append to {path}"
        existing = self._files.get(path, "")
        self._files[path] = existing + text
        self.written.append((path, text))
        return None

    def seed(self, path: Path, content: str) -> None:
        """Pre-populate a file for test setup."""
        self._files[path] = content


# ---------------------------------------------------------------------------
# FakeCommandRunner
# ---------------------------------------------------------------------------


class FakeCommandRunner:
    """Records commands without executing them."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self._responses: dict[tuple[str, ...], subprocess.CompletedProcess[str]] = {}
        self._default_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

    def register(
        self,
        args: list[str],
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Pre-register a canned response for specific args."""
        self._responses[tuple(args)] = subprocess.CompletedProcess(
            args=args, returncode=returncode, stdout=stdout, stderr=stderr
        )

    def run(
        self,
        args: list[str],
        *,
        timeout: int = 30,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        key = tuple(args)
        return self._responses.get(key, self._default_result)


# ---------------------------------------------------------------------------
# FakeConsole
# ---------------------------------------------------------------------------


class FakeConsole:
    """Captures all output for assertion in tests."""

    def __init__(self, *, quiet: bool = False) -> None:
        self.quiet = quiet
        self.messages: list[tuple[str, str]] = []  # (level, text)

    def info(self, text: str) -> None:
        if not self.quiet:
            self.messages.append(("info", text))

    def success(self, text: str) -> None:
        if not self.quiet:
            self.messages.append(("success", text))

    def warning(self, text: str) -> None:
        self.messages.append(("warning", text))

    def error(self, text: str) -> None:
        self.messages.append(("error", text))

    def step(self, text: str) -> None:
        self.messages.append(("step", text))

    def has(self, level: str, substring: str) -> bool:
        return any(lvl == level and substring in txt for lvl, txt in self.messages)

    def all_text(self) -> list[str]:
        return [txt for _, txt in self.messages]


# ---------------------------------------------------------------------------
# FakePythonPlugin
# ---------------------------------------------------------------------------


class FakePythonPlugin:
    """Minimal stub satisfying LanguagePlugin protocol for Python."""

    key = "python"
    name = "Python"
    linter = "ruff"
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = []

    def detect(self, project_dir: Path) -> bool:
        return True

    def generate(self, registry: object, project_dir: Path) -> dict[Path, str]:
        return {}

    def check(self, registry: object, project_dir: Path) -> list[str]:
        return []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_files() -> FakeFileManager:
    return FakeFileManager()


@pytest.fixture()
def fake_files_dry() -> FakeFileManager:
    return FakeFileManager(dry_run=True)


@pytest.fixture()
def fake_runner() -> FakeCommandRunner:
    return FakeCommandRunner()


@pytest.fixture()
def fake_console() -> FakeConsole:
    return FakeConsole()


@pytest.fixture()
def fake_console_quiet() -> FakeConsole:
    return FakeConsole(quiet=True)


@pytest.fixture()
def sample_exceptions_toml() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "global_rules": {
            "ruff": {"ignore": ["E501", "W503"]},
        },
        "exceptions": [
            {
                "tool": "ruff",
                "rule": "T201",
                "reason": "Print used in CLI entry points",
                "scope": "src/cli.py",
            },
        ],
        "file_exceptions": [
            {
                "glob": "tests/**/*.py",
                "tool": "ruff",
                "rules": ["S101", "PLR2004"],
                "reason": "Assertions and magic values OK in tests",
            },
        ],
        "custom": {},
        "inline_suppressions": [],
    }
