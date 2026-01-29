"""Go tools installer deploy.

Installs: golangci-lint, govulncheck
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api.deploy import deploy
from pyinfra.facts.server import Which
from pyinfra.operations import server

TOOLS = [
    ("golangci-lint", "github.com/golangci/golangci-lint/cmd/golangci-lint@latest"),
    ("govulncheck", "golang.org/x/vuln/cmd/govulncheck@latest"),
]


@deploy("Install Go linting tools")
def install_go_tools() -> None:
    """Install golangci-lint and govulncheck via go install."""
    go_available = host.get_fact(Which, command="go")

    if not go_available:
        server.shell(
            name="Error: go not found",
            commands=[
                "echo 'Error: go not found'",
                "echo 'Install Go first: https://go.dev/doc/install'",
            ],
        )
        return

    # Install each tool
    for tool_name, install_path in TOOLS:
        server.shell(
            name=f"Install {tool_name}",
            commands=[f"go install {install_path}"],
        )

    # Note about GOBIN PATH
    server.shell(
        name="Note GOBIN path",
        commands=[
            'GOBIN="${GOBIN:-${GOPATH:-$HOME/go}/bin}"',
            'echo "Note: Ensure $GOBIN is in PATH"',
        ],
    )

    # Verify installations
    for tool_name, _ in TOOLS:
        server.shell(
            name=f"Verify {tool_name} installation",
            commands=[
                f"command -v {tool_name} && echo '{tool_name}: OK' || "
                f"echo '{tool_name}: NOT FOUND (check GOBIN in PATH)'"
            ],
        )
