"""Installation path resolution for ai-guardrails.

Handles finding configs, templates, and lib directories in both
development (repo checkout) and installed (~/.ai-guardrails/) contexts.
"""

from __future__ import annotations

from pathlib import Path

_GLOBAL_INSTALL = Path.home() / ".ai-guardrails"


def _repo_root() -> Path:
    """Return the ai-guardrails repo root (lib/python/guardrails → repo)."""
    return Path(__file__).resolve().parent.parent.parent.parent


def find_configs_dir() -> Path:
    """Find the ai-guardrails configs directory.

    Prefers local repo over global install (development takes precedence).

    Raises:
        FileNotFoundError: If no configs directory found.

    """
    # Local repo first (development)
    local = _repo_root() / "configs"
    if local.exists():
        return local

    # Global installation
    global_configs = _GLOBAL_INSTALL / "configs"
    if global_configs.exists():
        return global_configs

    msg = "Could not find ai-guardrails configs directory"
    raise FileNotFoundError(msg)


def find_templates_dir() -> Path:
    """Find the ai-guardrails templates directory.

    Raises:
        FileNotFoundError: If no templates directory found.

    """
    local = _repo_root() / "templates"
    if local.exists():
        return local

    global_templates = _GLOBAL_INSTALL / "templates"
    if global_templates.exists():
        return global_templates

    msg = "Could not find ai-guardrails templates directory"
    raise FileNotFoundError(msg)


def find_lib_dir() -> Path:
    """Find the ai-guardrails lib directory.

    Raises:
        FileNotFoundError: If no lib directory found.

    """
    local = _repo_root() / "lib"
    if local.exists():
        return local

    global_lib = _GLOBAL_INSTALL / "lib"
    if global_lib.exists():
        return global_lib

    msg = "Could not find ai-guardrails lib directory"
    raise FileNotFoundError(msg)


def find_base_config(name: str, project_path: Path) -> Path | None:
    """Find a base config template, preferring project-local over global.

    Args:
        name: Config filename (e.g. "ruff.toml").
        project_path: Path to the consumer project.

    Returns:
        Path to the base config, or None if not found.

    """
    # Project-local configs/ directory
    local = project_path / "configs" / name
    if local.exists():
        return local

    # Global ai-guardrails configs
    try:
        global_configs = find_configs_dir()
    except FileNotFoundError:
        return None

    global_path = global_configs / name
    return global_path if global_path.exists() else None
