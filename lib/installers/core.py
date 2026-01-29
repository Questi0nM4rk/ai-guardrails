"""Core installer module for AI Guardrails.

Handles:
- Installation of pyyaml and pre-commit
- File copying to ~/.ai-guardrails/
- Symlink creation for CLI tools

NOTE: This module is designed for @local deployments only.
Path.exists() checks run on the controller (local machine).
For remote deployment support, replace with pyinfra facts.
"""

from __future__ import annotations

from pathlib import Path

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import files, pip, server

# Installation paths
INSTALL_DIR = Path.home() / ".ai-guardrails"
BIN_DIR = Path.home() / ".local" / "bin"

# Files to copy (relative to source root)
BIN_SCRIPTS = ["ai-review-tasks", "ai-hooks-init", "ai-guardrails-init"]
HOOK_SCRIPTS = [
    "common.sh",
    "dangerous-command-check.sh",
    "pre-commit.sh",
    "pre-push.sh",
    "format-and-stage.sh",
]


def get_source_dir() -> Path:
    """Get the source directory (project root)."""
    # Navigate up from lib/installers/core.py to project root
    return Path(__file__).parent.parent.parent


@deploy("Install pyyaml")
def install_pyyaml() -> None:
    """Install pyyaml Python package."""
    pip.packages(
        name="Install pyyaml",
        packages=["pyyaml"],
        extra_install_args="--user",
    )


@deploy("Install pre-commit")
def install_precommit() -> None:
    """Install pre-commit via pipx (preferred) or pip."""
    pipx_available = host.get_fact(Which, command="pipx")

    if pipx_available:
        # Use pipx for isolated installation
        # Check if already installed, then upgrade or install
        server.shell(
            name="Install pre-commit via pipx",
            commands=[
                "pipx list 2>/dev/null | grep -q 'package pre-commit' && "
                "pipx upgrade pre-commit || "
                "pipx install pre-commit",
            ],
        )
    else:
        # Fallback to pip --user
        pip.packages(
            name="Install pre-commit via pip",
            packages=["pre-commit"],
            extra_install_args="--user",
        )


@deploy("Create installation directories")
def create_directories() -> None:
    """Create the installation directory structure."""
    directories = [
        INSTALL_DIR,
        INSTALL_DIR / "bin",
        INSTALL_DIR / "lib" / "hooks",
        INSTALL_DIR / "lib" / "python",
        INSTALL_DIR / "lib" / "installers",
        INSTALL_DIR / "templates",
        INSTALL_DIR / "templates" / "pre-commit",
        INSTALL_DIR / "templates" / "workflows",
        INSTALL_DIR / "configs",
        INSTALL_DIR / "hooks",
        BIN_DIR,
    ]

    for directory in directories:
        files.directory(
            name=f"Create {directory}",
            path=str(directory),
            present=True,
        )


@deploy("Copy bin scripts")
def copy_bin_scripts() -> None:
    """Copy CLI scripts to installation directory."""
    source_dir = get_source_dir()

    for script in BIN_SCRIPTS:
        src = source_dir / "bin" / script
        dst = INSTALL_DIR / "bin" / script

        if src.exists():
            files.put(
                name=f"Copy {script}",
                src=str(src),
                dest=str(dst),
                mode="755",
            )


@deploy("Copy hook scripts")
def copy_hook_scripts() -> None:
    """Copy git hook scripts to installation directory."""
    source_dir = get_source_dir()

    for hook in HOOK_SCRIPTS:
        src = source_dir / "lib" / "hooks" / hook
        dst = INSTALL_DIR / "lib" / "hooks" / hook

        if src.exists():
            files.put(
                name=f"Copy {hook}",
                src=str(src),
                dest=str(dst),
                mode="755",
            )


@deploy("Copy Python library files")
def copy_python_lib() -> None:
    """Copy Python library files to installation directory."""
    source_dir = get_source_dir()
    py_src = source_dir / "lib" / "python"

    if py_src.exists():
        for pyfile in py_src.glob("*.py"):
            files.put(
                name=f"Copy {pyfile.name}",
                src=str(pyfile),
                dest=str(INSTALL_DIR / "lib" / "python" / pyfile.name),
                mode="644",
            )


@deploy("Copy templates")
def copy_templates() -> None:
    """Copy template files to installation directory."""
    source_dir = get_source_dir()
    templates_src = source_dir / "templates"

    if not templates_src.exists():
        return

    # Copy top-level template files (including dotfiles)
    for template in templates_src.iterdir():
        if template.is_file():
            files.put(
                name=f"Copy template {template.name}",
                src=str(template),
                dest=str(INSTALL_DIR / "templates" / template.name),
                mode="644",
            )

    # Copy pre-commit templates
    precommit_src = templates_src / "pre-commit"
    if precommit_src.exists():
        for template in precommit_src.glob("*.yaml"):
            files.put(
                name=f"Copy pre-commit/{template.name}",
                src=str(template),
                dest=str(INSTALL_DIR / "templates" / "pre-commit" / template.name),
                mode="644",
            )

    # Copy workflow templates
    workflows_src = templates_src / "workflows"
    if workflows_src.exists():
        for template in workflows_src.iterdir():
            if template.is_file():
                files.put(
                    name=f"Copy workflow {template.name}",
                    src=str(template),
                    dest=str(INSTALL_DIR / "templates" / "workflows" / template.name),
                    mode="644",
                )


@deploy("Copy config files")
def copy_configs() -> None:
    """Copy configuration files to installation directory."""
    source_dir = get_source_dir()
    configs_src = source_dir / "configs"

    if not configs_src.exists():
        return

    for config in configs_src.iterdir():
        if config.is_file():
            files.put(
                name=f"Copy config {config.name}",
                src=str(config),
                dest=str(INSTALL_DIR / "configs" / config.name),
                mode="644",
            )


@deploy("Create CLI symlinks")
def create_symlinks() -> None:
    """Create symlinks in ~/.local/bin for CLI commands."""
    for cmd in BIN_SCRIPTS:
        src = INSTALL_DIR / "bin" / cmd
        dst = BIN_DIR / cmd

        # Only create symlink if source exists (avoids broken symlinks)
        if not src.exists():
            server.shell(
                name=f"Warn: {cmd} not found",
                commands=[f"echo 'Warning: {src} not found, skipping symlink'"],
            )
            continue

        files.link(
            name=f"Symlink {cmd}",
            path=str(dst),
            target=str(src),
            symbolic=True,
            force=True,
        )


@deploy("Create hook symlinks")
def create_hook_symlinks() -> None:
    """Create symlinks in hooks/ for easy access."""
    for hook in HOOK_SCRIPTS:
        src = INSTALL_DIR / "lib" / "hooks" / hook
        dst = INSTALL_DIR / "hooks" / hook

        # Only create symlink if source exists
        if not src.exists():
            continue

        files.link(
            name=f"Symlink hook {hook}",
            path=str(dst),
            target=str(src),
            symbolic=True,
            force=True,
        )


@deploy("Uninstall AI Guardrails")
def uninstall() -> None:
    """Remove AI Guardrails installation."""
    # Remove symlinks
    for cmd in BIN_SCRIPTS:
        dst = BIN_DIR / cmd
        files.file(
            name=f"Remove symlink {cmd}",
            path=str(dst),
            present=False,
        )

    # Remove installation directory
    files.directory(
        name="Remove installation directory",
        path=str(INSTALL_DIR),
        present=False,
    )


@deploy("Install core AI Guardrails")
def install_core(*, force: bool = False) -> None:
    """Install core AI Guardrails components.

    Args:
        force: If True, remove existing installation first.

    """
    if force and INSTALL_DIR.exists():
        files.directory(
            name="Remove existing installation",
            path=str(INSTALL_DIR),
            present=False,
        )

    # Install Python dependencies
    install_pyyaml()
    install_precommit()

    # Create directory structure
    create_directories()

    # Copy files
    copy_bin_scripts()
    copy_hook_scripts()
    copy_python_lib()
    copy_templates()
    copy_configs()

    # Create symlinks
    create_symlinks()
    create_hook_symlinks()
