#!/usr/bin/env python3
"""AI Guardrails Installer - pyinfra-based.

Usage:
    python3 install.py              # Install core only
    python3 install.py --all        # Install all language tools
    python3 install.py --python     # Install Python tools only
    python3 install.py --uninstall  # Uninstall
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pyinfra.api import Config, Inventory, State
from pyinfra.api.connect import connect_all
from pyinfra.api.operations import run_ops

from lib.installers import (
    install_core,
    install_cpp_tools,
    install_go_tools,
    install_lua_tools,
    install_node_tools,
    install_python_tools,
    install_rust_tools,
    install_shell_tools,
)
from lib.installers.core import uninstall

if TYPE_CHECKING:
    from collections.abc import Callable

    # Type alias for deploy queue entries (Python 3.10 compatible)
    DeployEntry = tuple[Callable[..., object], tuple[object, ...], dict[str, object]]

# Queue of pending deploy functions to execute within pyinfra state context
_pending_deploys: list[tuple[Callable[..., object], tuple[object, ...], dict[str, object]]] = []

# ANSI colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def print_color(color: str, message: str) -> None:
    """Print a message with color."""
    print(f"{color}{message}{NC}")


def add_deploy(
    deploy_func: Callable[..., object],
    *args: object,
    **kwargs: object,
) -> None:
    """Queue a deploy function to execute within pyinfra state context.

    Deploy functions (decorated with @deploy) must be called after pyinfra
    state is initialized via connect_all(). This function queues them for
    execution at the right time.

    Args:
        deploy_func: A pyinfra @deploy decorated function.
        *args: Positional arguments to pass to the deploy function.
        **kwargs: Keyword arguments to pass to the deploy function.

    """
    _pending_deploys.append((deploy_func, args, kwargs))


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="AI Guardrails Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Installation locations:
  ~/.ai-guardrails/     Main installation directory
  ~/.local/bin/         CLI symlinks (ai-guardrails, ai-guardrails-init, etc.)

Prerequisites:
  - Python 3.10+
  - gh (GitHub CLI)

Notes:
  - pyyaml and pre-commit are always installed (required)
  - Language tools require their respective toolchains (go, cargo, npm, etc.)
  - System package manager (pacman/apt/brew) used where applicable
""",
    )

    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove AI Guardrails installation",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall (overwrite existing)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install all language tools",
    )
    parser.add_argument(
        "--python",
        action="store_true",
        help="Install Python tools (ruff, mypy, bandit, vulture, pip-audit)",
    )
    parser.add_argument(
        "--node",
        action="store_true",
        help="Install Node.js tools (biome)",
    )
    parser.add_argument(
        "--rust",
        action="store_true",
        help="Install Rust tools (cargo-audit)",
    )
    parser.add_argument(
        "--go",
        action="store_true",
        help="Install Go tools (golangci-lint, govulncheck)",
    )
    parser.add_argument(
        "--cpp",
        action="store_true",
        help="Install C/C++ tools (clang-format, clang-tidy)",
    )
    parser.add_argument(
        "--lua",
        action="store_true",
        help="Install Lua tools (stylua, luacheck)",
    )
    parser.add_argument(
        "--shell",
        action="store_true",
        help="Install Shell tools (shellcheck, shfmt)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    return parser.parse_args()


def run_pyinfra(*, dry_run: bool = False) -> bool:
    """Run queued deploy functions and return success status.

    This function:
    1. Creates pyinfra State with @local inventory
    2. Connects to the local host
    3. Executes all queued deploy functions (which register operations)
    4. Runs all registered operations

    Args:
        dry_run: If True, show what would be done without making changes.

    Returns:
        True if all operations succeeded, False otherwise.

    """
    global _pending_deploys

    # Create inventory for @local (execute on localhost via subprocess)
    inventory = Inventory((["@local"], {}))

    config = Config()
    if dry_run:
        config.DRYRUN = True

    # Set up state with inventory and config
    state = State(inventory=inventory, config=config)

    # Connect to @local host
    connect_all(state)

    # Execute all pending deploys within the state context
    # This is when @deploy functions register their operations
    for deploy_func, args, kwargs in _pending_deploys:
        deploy_func(*args, **kwargs)

    # Clear pending deploys after execution
    _pending_deploys = []

    # Run all queued operations
    return run_ops(state)


def main() -> int:
    """Run the AI Guardrails installer."""
    args = parse_args()

    print_color(BLUE, "AI Guardrails Installer (pyinfra)")
    print()

    # Uninstall
    if args.uninstall:
        print_color(BLUE, "Uninstalling AI Guardrails...")
        add_deploy(uninstall)
        if run_pyinfra(dry_run=args.dry_run):
            print_color(GREEN, "AI Guardrails uninstalled successfully!")
            return 0
        print_color(RED, "Uninstallation failed")
        return 1

    # Check Python version
    if sys.version_info < (3, 10):
        print_color(RED, f"Error: Python 3.10+ required (you have {sys.version})")
        return 1

    print(f"  Python {sys.version_info.major}.{sys.version_info.minor}")

    # Check for existing installation
    install_dir = Path.home() / ".ai-guardrails"
    if install_dir.exists() and not args.force:
        print_color(YELLOW, f"AI Guardrails is already installed at {install_dir}")
        print("Use --force to reinstall")
        return 1

    # Install core (always)
    print()
    print_color(GREEN, "Installing core components...")
    add_deploy(install_core, force=args.force)

    # Install language tools based on flags
    install_langs = args.all or any(
        [
            args.python,
            args.node,
            args.rust,
            args.go,
            args.cpp,
            args.lua,
            args.shell,
        ]
    )

    if install_langs:
        print()
        print_color(GREEN, "Installing language tools...")

        if args.all or args.python:
            print()
            print_color(BLUE, "Python tools...")
            add_deploy(install_python_tools)

        if args.all or args.node:
            print()
            print_color(BLUE, "Node.js tools...")
            add_deploy(install_node_tools)

        if args.all or args.rust:
            print()
            print_color(BLUE, "Rust tools...")
            add_deploy(install_rust_tools)

        if args.all or args.go:
            print()
            print_color(BLUE, "Go tools...")
            add_deploy(install_go_tools)

        if args.all or args.cpp:
            print()
            print_color(BLUE, "C/C++ tools...")
            add_deploy(install_cpp_tools)

        if args.all or args.lua:
            print()
            print_color(BLUE, "Lua tools...")
            add_deploy(install_lua_tools)

        if args.all or args.shell:
            print()
            print_color(BLUE, "Shell tools...")
            add_deploy(install_shell_tools)

    # Run all operations
    print()
    if args.dry_run:
        print_color(YELLOW, "Dry run - no changes made")
    success = run_pyinfra(dry_run=args.dry_run)

    if success:
        print()
        print_color(GREEN, "AI Guardrails installed successfully!")
        print()
        print("Installation summary:")
        print(f"  Main directory: {install_dir}")
        print("  CLI commands: ai-guardrails, ai-guardrails-init, ai-guardrails-generate")
        print(f"  Hooks: {install_dir}/hooks/")
        print()
        print("Quick start:")
        print("  1. cd /path/to/your/project")
        print("  2. ai-guardrails-init           # Set up CLAUDE.md and settings")
        print("  3. ai-hooks-init --pre-commit   # Set up git hooks")
        print()

        # Check PATH
        bin_dir = Path.home() / ".local" / "bin"
        if str(bin_dir) not in os.environ.get("PATH", ""):
            print_color(YELLOW, f"Note: Add {bin_dir} to your PATH:")
            print('  export PATH="$HOME/.local/bin:$PATH"')

        return 0

    print_color(RED, "Installation completed with errors")
    return 1


if __name__ == "__main__":
    sys.exit(main())
