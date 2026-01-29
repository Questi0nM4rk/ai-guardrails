"""C/C++ tools installer deploy.

Installs: clang-format, clang-tidy
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import apk, apt, brew, dnf, pacman, server

TOOLS = ["clang-format", "clang-tidy"]


def _get_package_manager() -> str | None:
    """Detect available package manager."""
    managers = ["pacman", "apt-get", "dnf", "yum", "apk", "brew"]
    for pm in managers:
        if host.get_fact(Which, command=pm):
            return pm.replace("-get", "")
    return None


@deploy("Install C/C++ linting tools")
def install_cpp_tools() -> None:
    """Install clang-format and clang-tidy via system package manager."""
    pm = _get_package_manager()

    if pm == "pacman":
        # On Arch, clang package includes both tools
        pacman.packages(
            name="Install clang (includes clang-format, clang-tidy)",
            packages=["clang"],
            _sudo=True,
        )

    elif pm == "apt":
        apt.packages(
            name="Install clang tools via apt",
            packages=["clang-format", "clang-tidy"],
            _sudo=True,
        )

    elif pm in ("dnf", "yum"):
        dnf.packages(
            name="Install clang tools via dnf",
            packages=["clang", "clang-tools-extra"],
            _sudo=True,
        )

    elif pm == "apk":
        apk.packages(
            name="Install clang tools via apk",
            packages=["clang", "clang-extra-tools"],
            _sudo=True,
        )

    elif pm == "brew":
        brew.packages(
            name="Install clang-format via brew",
            packages=["clang-format"],
        )
        brew.packages(
            name="Install llvm (provides clang-tidy) via brew",
            packages=["llvm"],
        )
        server.shell(
            name="Note llvm bin path",
            commands=[
                "echo 'Note: clang-tidy from llvm may need PATH update:'",
                "echo '  export PATH=\"$(brew --prefix llvm)/bin:$PATH\"'",
            ],
        )

    else:
        server.shell(
            name="Warn: no package manager found",
            commands=["echo 'No supported package manager found for C/C++ tools'"],
        )

    # Verify installations
    for tool in TOOLS:
        server.shell(
            name=f"Verify {tool} installation",
            commands=[f"command -v {tool} && echo '{tool}: OK' || echo '{tool}: NOT FOUND'"],
        )
