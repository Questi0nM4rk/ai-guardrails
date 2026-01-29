"""Python tools installer deploy.

Installs: ruff, mypy, bandit, vulture, pip-audit
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import pip, server

TOOLS = ["ruff", "mypy", "bandit", "vulture", "pip-audit"]


@deploy("Install Python linting tools")
def install_python_tools() -> None:
    """Install Python tools via pipx (preferred) or pip."""
    pipx_available = host.get_fact(Which, command="pipx")

    if pipx_available:
        # Use pipx for isolated installations (PEP 668 compliant)
        for tool in TOOLS:
            server.shell(
                name=f"Install {tool} via pipx",
                commands=[
                    f"pipx list 2>/dev/null | grep -q 'package {tool}' && "
                    f"pipx upgrade {tool} || "
                    f"pipx install {tool}",
                ],
            )
    else:
        # Fallback to pip --user
        # Try without --break-system-packages first
        pip.packages(
            name="Install Python tools via pip",
            packages=TOOLS,
            extra_install_args="--user",
        )

    # Verify installations
    for tool in TOOLS:
        server.shell(
            name=f"Verify {tool} installation",
            commands=[f"command -v {tool} || echo '{tool} not in PATH'"],
        )
