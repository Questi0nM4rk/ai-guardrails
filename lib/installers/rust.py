"""Rust tools installer deploy.

Installs: cargo-audit
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import server

TOOLS = ["cargo-audit"]


@deploy("Install Rust security tools")
def install_rust_tools() -> None:
    """Install cargo-audit via cargo."""
    cargo_available = host.get_fact(Which, command="cargo")

    if not cargo_available:
        server.shell(
            name="Error: cargo not found",
            commands=[
                "echo 'Error: cargo not found' >&2",
                "echo 'Install Rust first: https://rustup.rs/' >&2",
                "exit 1",
            ],
        )
        return

    # Install cargo-audit (idempotent - only install if not present)
    server.shell(
        name="Install cargo-audit",
        commands=["cargo install --list | grep -q '^cargo-audit ' || cargo install cargo-audit"],
    )

    # Verify installation
    server.shell(
        name="Verify cargo-audit installation",
        commands=[
            "command -v cargo-audit && cargo-audit --version || echo 'cargo-audit: NOT FOUND'"
        ],
    )
