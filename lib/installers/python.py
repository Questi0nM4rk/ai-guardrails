"""Python tools installer deploy.

Installs: ruff, mypy, bandit, vulture, pip-audit
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import server

from lib.installers._utils import fail_no_uv_or_pipx

TOOLS = ["ruff", "mypy", "bandit", "vulture", "pip-audit"]


@deploy("Install Python linting tools")
def install_python_tools() -> None:
    """Install Python tools via uv (preferred) or pipx."""
    uv_available = host.get_fact(Which, command="uv")
    if uv_available:
        for tool in TOOLS:
            server.shell(
                name=f"Install {tool} via uv",
                commands=[f"uv tool install {tool}"],
            )
    else:
        pipx_available = host.get_fact(Which, command="pipx")
        if pipx_available:
            for tool in TOOLS:
                server.shell(
                    name=f"Install {tool} via pipx",
                    commands=[f"pipx install {tool}"],
                )
        else:
            fail_no_uv_or_pipx()
            return

    for tool in TOOLS:
        server.shell(
            name=f"Verify {tool} installation",
            commands=[
                f"command -v {tool} || echo '{tool} not in PATH'",
            ],
        )
