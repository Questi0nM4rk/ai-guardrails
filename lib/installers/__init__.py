"""AI Guardrails installer modules using pyinfra.

This package provides modular deploy functions for installing
language-specific linting and security tools.
"""

from __future__ import annotations

from lib.installers.core import install_core
from lib.installers.cpp import install_cpp_tools
from lib.installers.go import install_go_tools
from lib.installers.lua import install_lua_tools
from lib.installers.node import install_node_tools
from lib.installers.python import install_python_tools
from lib.installers.rust import install_rust_tools
from lib.installers.shell import install_shell_tools

__all__ = [
    "install_core",
    "install_cpp_tools",
    "install_go_tools",
    "install_lua_tools",
    "install_node_tools",
    "install_python_tools",
    "install_rust_tools",
    "install_shell_tools",
]
