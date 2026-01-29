"""Shell tools installer deploy.

Installs: shellcheck, shfmt
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import apk, apt, brew, dnf, pacman, server, yum

from lib.installers._utils import get_package_manager

TOOLS = ["shellcheck", "shfmt"]


@deploy("Install shell linting tools")
def install_shell_tools() -> None:
    """Install shellcheck and shfmt via system package manager."""
    pm = get_package_manager()

    if pm == "pacman":
        pacman.packages(
            name="Install shell tools via pacman",
            packages=["shellcheck", "shfmt"],
            _sudo=True,
        )

    elif pm == "apt":
        apt.packages(
            name="Install shellcheck via apt",
            packages=["shellcheck"],
            _sudo=True,
        )
        # shfmt not in apt by default, install via go if available
        go_available = host.get_fact(Which, command="go")
        if go_available:
            server.shell(
                name="Install shfmt via go",
                commands=["go install mvdan.cc/sh/v3/cmd/shfmt@latest"],
            )
        else:
            server.shell(
                name="Warn: shfmt requires Go",
                commands=["echo 'Warning: shfmt requires Go to install on Debian/Ubuntu'"],
            )

    elif pm == "dnf":
        dnf.packages(
            name="Install ShellCheck via dnf",
            packages=["ShellCheck"],
            _sudo=True,
        )
        # shfmt via go on RHEL/Fedora
        go_available = host.get_fact(Which, command="go")
        if go_available:
            server.shell(
                name="Install shfmt via go",
                commands=["go install mvdan.cc/sh/v3/cmd/shfmt@latest"],
            )

    elif pm == "yum":
        yum.packages(
            name="Install ShellCheck via yum",
            packages=["ShellCheck"],
            _sudo=True,
        )
        # shfmt via go on RHEL/CentOS
        go_available = host.get_fact(Which, command="go")
        if go_available:
            server.shell(
                name="Install shfmt via go",
                commands=["go install mvdan.cc/sh/v3/cmd/shfmt@latest"],
            )

    elif pm == "apk":
        apk.packages(
            name="Install shell tools via apk",
            packages=["shellcheck", "shfmt"],
            _sudo=True,
        )

    elif pm == "brew":
        brew.packages(
            name="Install shell tools via brew",
            packages=["shellcheck", "shfmt"],
        )

    else:
        server.shell(
            name="Warn: no package manager found",
            commands=["echo 'No supported package manager found for shell tools'"],
        )

    # Verify installations
    for tool in TOOLS:
        server.shell(
            name=f"Verify {tool} installation",
            commands=[f"command -v {tool} && echo '{tool}: OK' || echo '{tool}: NOT FOUND'"],
        )
