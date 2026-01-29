"""Node.js tools installer deploy.

Installs: biome
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import npm, server

TOOLS = ["@biomejs/biome"]


@deploy("Install Node.js linting tools")
def install_node_tools() -> None:
    """Install biome via npm."""
    npm_available = host.get_fact(Which, command="npm")

    if not npm_available:
        server.shell(
            name="Error: npm not found",
            commands=[
                "echo 'Error: npm not found'",
                "echo 'Install Node.js first: https://nodejs.org/'",
            ],
        )
        return

    # Install biome globally
    npm.packages(
        name="Install biome via npm",
        packages=TOOLS,
        global_install=True,
    )

    # Verify installation
    server.shell(
        name="Verify biome installation",
        commands=["command -v biome && biome --version || echo 'biome: NOT FOUND'"],
    )
