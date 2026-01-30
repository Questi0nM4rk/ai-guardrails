"""Lua tools installer deploy.

Installs: stylua, luacheck
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import pacman, server

from lib.installers._utils import get_package_manager

TOOLS = ["stylua", "luacheck"]


@deploy("Install Lua linting tools")
def install_lua_tools() -> None:
    """Install stylua and luacheck.

    - stylua: via cargo (cross-platform) or pacman (Arch)
    - luacheck: via luarocks or pacman (Arch)
    """
    pm = get_package_manager()
    cargo_available = host.get_fact(Which, command="cargo")
    luarocks_available = host.get_fact(Which, command="luarocks")

    # Install stylua
    if pm == "pacman":
        # Arch has stylua in community repo
        pacman.packages(
            name="Install stylua via pacman",
            packages=["stylua"],
            _sudo=True,
        )
    elif cargo_available:
        # Idempotent: only install if not already present
        server.shell(
            name="Install stylua via cargo",
            commands=["cargo install --list | grep -q '^stylua ' || cargo install stylua"],
        )
    else:
        server.shell(
            name="Warn: stylua requires cargo",
            commands=[
                "echo 'Warning: stylua requires cargo to install'",
                "echo 'Install Rust first: https://rustup.rs/'",
            ],
        )

    # Install luacheck
    if pm == "pacman":
        pacman.packages(
            name="Install luacheck via pacman",
            packages=["luacheck"],
            _sudo=True,
        )
    elif luarocks_available:
        # Idempotent: only install if not already present
        server.shell(
            name="Install luacheck via luarocks",
            commands=[
                "luarocks show luacheck >/dev/null 2>&1 || luarocks install --local luacheck"
            ],
        )
    else:
        server.shell(
            name="Warn: luacheck requires luarocks",
            commands=[
                "echo 'Warning: luacheck requires luarocks to install'",
                "echo 'Install luarocks first'",
            ],
        )

    # Verify installations
    for tool in TOOLS:
        server.shell(
            name=f"Verify {tool} installation",
            commands=[f"command -v {tool} && echo '{tool}: OK' || echo '{tool}: NOT FOUND'"],
        )
