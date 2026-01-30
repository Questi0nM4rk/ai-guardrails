"""Shared utility functions for installer modules."""

from __future__ import annotations

from pyinfra import host
from pyinfra.facts.server import Which


def get_package_manager() -> str | None:
    """Detect the available package manager on the system.

    Checks for package managers in order of preference:
    pacman > apt > dnf > yum > apk > brew

    Returns:
        Package manager name (without -get suffix) or None if not found.

    """
    managers = ["pacman", "apt-get", "dnf", "yum", "apk", "brew"]
    for pm in managers:
        if host.get_fact(Which, command=pm):
            return pm.replace("-get", "")
    return None
