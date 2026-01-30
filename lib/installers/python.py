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
        # pipx install is idempotent - reinstalls if already present
        for tool in TOOLS:
            server.shell(
                name=f"Install {tool} via pipx",
                commands=[f"pipx install {tool}"],
            )
    else:
        # Fallback to pip --user
        tools_str = " ".join(TOOLS)
        server.shell(
            name="Install Python tools via pip",
            commands=[f"python3 -m pip install --user {tools_str}"],
        )

    # Verify installations
    for tool in TOOLS:
        server.shell(
            name=f"Verify {tool} installation",
            commands=[f"command -v {tool} || echo '{tool} not in PATH'"],
        )
