"""Shared constants for ai-guardrails v1.

Single source of truth for suppression patterns, dangerous command rules,
generated config filenames, and test path detection patterns.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

MatchType: TypeAlias = Literal["substring", "regex"]

#: (pattern, language_description, file_extensions)
SuppressionPattern: TypeAlias = tuple[str, str, frozenset[str]]

#: (match_type, pattern, message)
DangerousRule: TypeAlias = tuple[MatchType, str, str]

# ---------------------------------------------------------------------------
# Generated configs (tamper-protected — ai-guardrails owns these)
# ---------------------------------------------------------------------------

GENERATED_CONFIGS: frozenset[str] = frozenset(
    {
        "ruff.toml",
        "biome.json",
        ".markdownlint.jsonc",
        ".codespellrc",
        ".suppression-allowlist",
        "lefthook.yml",
        "rustfmt.toml",
        "stylua.toml",
        ".clang-format",
        ".clang-tidy",
        "Directory.Build.props",
        ".globalconfig",
        ".editorconfig",
    }
)

# ---------------------------------------------------------------------------
# Exception registry filename
# ---------------------------------------------------------------------------

REGISTRY_FILENAME = ".guardrails-exceptions.toml"

# ---------------------------------------------------------------------------
# Suppression comment patterns (used by suppress_comments hook)
# ---------------------------------------------------------------------------

SUPPRESSION_PATTERNS: tuple[SuppressionPattern, ...] = (
    # Python
    (r"# noqa", "Python noqa suppression", frozenset({"py"})),
    (r"# type: ignore", "Python type ignore", frozenset({"py"})),
    (r"# pylint: disable", "Pylint disable", frozenset({"py"})),
    (r"# pragma: no cover", "Coverage exclusion", frozenset({"py"})),
    # TypeScript / JavaScript
    (r"// @ts-ignore", "TypeScript ignore", frozenset({"ts", "tsx", "js", "jsx"})),
    (
        r"// @ts-expect-error",
        "TypeScript expect-error",
        frozenset({"ts", "tsx", "js", "jsx"}),
    ),
    (r"// @ts-nocheck", "TypeScript nocheck", frozenset({"ts", "tsx", "js", "jsx"})),
    (
        r"/\* eslint-disable",
        "ESLint disable block",
        frozenset({"ts", "tsx", "js", "jsx"}),
    ),
    (
        r"// eslint-disable",
        "ESLint disable line",
        frozenset({"ts", "tsx", "js", "jsx"}),
    ),
    # C#
    (r"#pragma warning disable", "C# pragma disable", frozenset({"cs"})),
    (r"// ReSharper disable", "ReSharper disable", frozenset({"cs"})),
    (r"\[SuppressMessage", "SuppressMessage attribute", frozenset({"cs"})),
    # Rust
    (r"#\[allow\(", "Rust allow attribute", frozenset({"rs"})),
    (r"#!\[allow\(", "Rust crate-level allow", frozenset({"rs"})),
    # Go
    (r"//nolint", "Go nolint directive", frozenset({"go"})),
    # Shell
    (r"# shellcheck disable", "ShellCheck disable", frozenset({"sh", "bash"})),
    # Lua
    (r"--luacheck: ignore", "Luacheck ignore", frozenset({"lua"})),
    # C/C++
    (r"// NOLINT", "Clang-Tidy NOLINT", frozenset({"c", "cpp", "h", "hpp"})),
    (r"/\* NOLINT", "Clang-Tidy NOLINT block", frozenset({"c", "cpp", "h", "hpp"})),
    (
        r"#pragma clang diagnostic ignored",
        "Clang diagnostic ignore",
        frozenset({"c", "cpp", "h", "hpp"}),
    ),
    (
        r"#pragma GCC diagnostic ignored",
        "GCC diagnostic ignore",
        frozenset({"c", "cpp", "h", "hpp"}),
    ),
)

# ---------------------------------------------------------------------------
# Test path patterns (files matching these are exempt from suppression checks)
# ---------------------------------------------------------------------------

TEST_PATH_SEGMENTS: frozenset[str] = frozenset(
    {
        "/tests/",
        "/test/",
        "/__tests__/",
        "/spec/",
    }
)

TEST_BASENAME_PATTERNS: tuple[str, ...] = (
    "/test_",
    "_test.",
    "_spec.",
    ".spec.",
)

# ---------------------------------------------------------------------------
# File extension inference helpers (used by suppress_comments hook)
# ---------------------------------------------------------------------------

#: Dotfile name → language extension
DOTFILE_MAP: dict[str, str] = {
    ".bashrc": "bash",
    ".bash_profile": "bash",
    ".bash_aliases": "bash",
    ".zshrc": "sh",
    ".zprofile": "sh",
    ".profile": "sh",
}

#: Shebang substring → language extension
SHEBANG_MAP: dict[str, str] = {
    "/bash": "bash",
    "env bash": "bash",
    "/sh": "sh",
    "env sh": "sh",
    "/zsh": "sh",
    "env zsh": "sh",
    "/python": "py",
    "env python": "py",
    "/node": "js",
    "env node": "js",
}

# ---------------------------------------------------------------------------
# Config file patterns (used by config_ignore + protect_configs hooks)
# ---------------------------------------------------------------------------

#: Config files where direct ignore-pattern edits are flagged.
CONFIG_FILES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "setup.cfg",
        ".flake8",
        ".eslintrc.json",
        ".eslintrc.js",
        ".eslintrc.yml",
        "tsconfig.json",
        "tslint.json",
    }
)

#: Regex matching config filenames (for git diff filtering).
CONFIG_PATTERN = (
    r"pyproject\.toml$|setup\.cfg$|\.flake8$"
    r"|\.eslintrc\.(json|js|yml)$|tsconfig\.json$|tslint\.json$"
)

#: Regex matching ignore/suppression patterns in config content.
IGNORE_PATTERN = (
    r"ignore[-_]?words|ignore\s*=|per-file-ignores"
    r"|reportMissing.*false|eslint-disable|noqa|nolint"
    r"|pragma.*disable|skip\s*=.*\["
)

# ---------------------------------------------------------------------------
# Dangerous command patterns (used by dangerous_cmd hook)
# ---------------------------------------------------------------------------

DANGEROUS_COMMANDS: tuple[DangerousRule, ...] = (
    # Filesystem destruction
    ("substring", "rm -rf ~", "Refusing to delete home directory"),
    ("substring", "rm -rf $HOME", "Refusing to delete home directory"),
    ("regex", r"rm\s+-rf\s+/home(?:/|\s|$|[;&|])", "Refusing to delete home directory"),
    (
        "regex",
        r"rm\s+-rf\s+/\s*$|rm\s+-rf\s+/\s*[;&|]",
        "Refusing to delete root filesystem",
    ),
    ("substring", "> /dev/sda", "Refusing to write directly to block device"),
    ("substring", "mkfs.", "Refusing to format disk"),
    ("substring", ":(){:|:&};:", "Fork bomb detected"),
    ("regex", r"dd\s+if=.*of=/dev/", "Refusing to write directly to block device"),
    # Hook/guardrail bypass
    (
        "substring",
        "--no-verify",
        "--no-verify bypasses all pre-commit hooks and guardrails.\n"
        "  This is never allowed. Fix the issue that's causing hooks to fail.",
    ),
    (
        "regex",
        r"git\s+commit\b.*\s-n\b",
        "git commit -n is short for --no-verify.\n"
        "  This is never allowed. Fix the issue that's causing hooks to fail.",
    ),
    ("substring", "--no-gpg-sign", "--no-gpg-sign bypasses commit signing."),
    (
        "substring",
        "core.hooksPath=",
        "Overriding core.hooksPath bypasses all git hooks.",
    ),
    ("substring", "SKIP=", "Bypassing pre-commit via environment variables."),
    (
        "substring",
        "PRE_COMMIT_ALLOW_NO_CONFIG",
        "Bypassing pre-commit via environment variables.",
    ),
    # Branch protection bypass
    (
        "regex",
        r"(?<!\w)--admin(?=\s|=|$)",
        "--admin bypasses branch protection rules.\n"
        "  This is never allowed without explicit user approval.",
    ),
    # Destructive operations
    ("substring", "rm -rf", "Recursive force delete - verify target"),
    ("substring", "chmod -R 777", "Insecure permissions"),
    ("substring", "| bash", "Piping to bash - verify source"),
    (
        "substring",
        "--force-with-lease",
        "Force push with lease - safer than --force but still rewrites history",
    ),
    # Destructive git operations
    (
        "regex",
        r"git\s+reset\s+--hard\b",
        "git reset --hard discards uncommitted changes",
    ),
    (
        "regex",
        r"git\s+checkout\s+(?:--\s+)?\.(?:\s*$|\s*&&|\s*;|\s*\|)",
        "git checkout . discards all unstaged changes",
    ),
    (
        "regex",
        r"git\s+restore\s+(?!(?=.*--staged\b)(?!.*--worktree\b))"
        r"(?:--?\S+\s+)*\.(?:\s*$|\s*&&|\s*;|\s*\|)",
        "git restore . discards all unstaged changes",
    ),
    (
        "regex",
        r"git\s+clean\s+(?:-[a-zA-Z]*f|--force|\S+\s+-f\b)",
        "git clean -f removes untracked files permanently",
    ),
    (
        "regex",
        r"git\s+branch\s+(?:-D\b|(?:\S+\s+)*--delete\s+--force|(?:\S+\s+)*--force\s+--delete)",
        "git branch -D force-deletes branch without merge check",
    ),
    # Force flags on destructive commands
    (
        "regex",
        r"(?:git push|git reset|docker rm).*(?:--force(?!-with-lease)\b|\s-f\b)",
        "Force flag on destructive operation",
    ),
)
