"""Python tools installer deploy.

Installs: ruff, mypy, bandit, vulture, pip-audit
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import server

TOOLS = ["ruff", "mypy", "bandit", "vulture", "pip-audit"]


@deploy("Install Python linting tools")
def install_python_tools() -> None:
    """Install Python tools via pipx (preferred) or pip."""
    pipx_available = host.get_fact(Which, command="pipx")

    if pipx_available:
        # Use pipx for isolated installations (PEP 668 compliant)
        # Try upgrade first (fails if not installed), then install as fallback
        for tool in TOOLS:
            server.shell(
                name=f"Install {tool} via pipx",
                commands=[
                    f"pipx upgrade {tool} 2>/dev/null || pipx install {tool}",
                ],
            )
    else:
        # Fallback to pip --user with PEP 668 handling
        tools_str = " ".join(TOOLS)
        server.shell(
            name="Install Python tools via pip",
            commands=[
                f"python3 -m pip install --user {tools_str} 2>/dev/null || "
                f"python3 -m pip install --user --break-system-packages {tools_str}"
            ],
        )

    # Verify installations
    for tool in TOOLS:
        server.shell(
            name=f"Verify {tool} installation",
            commands=[f"command -v {tool} || echo '{tool} not in PATH'"],
        )
