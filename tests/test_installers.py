"""Unit tests for pyinfra installer modules.

Tests use mocked pyinfra facts and operations to avoid actual system changes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.installers.core import (
    BIN_DIR,
    BIN_SCRIPTS,
    HOOK_SCRIPTS,
    INSTALL_DIR,
    get_source_dir,
)


class TestCoreModule:
    """Tests for lib/installers/core.py."""

    def test_install_dir_is_in_home(self) -> None:
        """Verify INSTALL_DIR is under home directory."""
        assert str(INSTALL_DIR).startswith(str(Path.home()))
        assert ".ai-guardrails" in str(INSTALL_DIR)

    def test_bin_dir_is_local_bin(self) -> None:
        """Verify BIN_DIR is ~/.local/bin."""
        assert str(BIN_DIR).endswith(".local/bin")

    def test_get_source_dir_returns_project_root(self) -> None:
        """Verify get_source_dir returns the project root."""
        source_dir = get_source_dir()
        # Should be the project root (contains install.py)
        assert (source_dir / "install.py").exists() or (source_dir / "install.sh").exists()

    def test_bin_scripts_list(self) -> None:
        """Verify BIN_SCRIPTS contains expected CLI tools."""
        assert "ai-review-tasks" in BIN_SCRIPTS
        assert "ai-hooks-init" in BIN_SCRIPTS
        assert "ai-guardrails-init" in BIN_SCRIPTS

    def test_hook_scripts_list(self) -> None:
        """Verify HOOK_SCRIPTS contains expected hooks."""
        assert "pre-commit.sh" in HOOK_SCRIPTS
        assert "pre-push.sh" in HOOK_SCRIPTS
        assert "common.sh" in HOOK_SCRIPTS


class TestPythonModule:
    """Tests for lib/installers/python.py."""

    def test_tools_list(self) -> None:
        """Verify TOOLS contains expected Python tools."""
        from lib.installers.python import TOOLS

        assert "ruff" in TOOLS
        assert "mypy" in TOOLS
        assert "bandit" in TOOLS
        assert "vulture" in TOOLS
        assert "pip-audit" in TOOLS


class TestShellModule:
    """Tests for lib/installers/shell.py."""

    def test_tools_list(self) -> None:
        """Verify TOOLS contains expected shell tools."""
        from lib.installers.shell import TOOLS

        assert "shellcheck" in TOOLS
        assert "shfmt" in TOOLS

    def test_get_package_manager_detection(self) -> None:
        """Test package manager detection logic."""
        from lib.installers._utils import get_package_manager

        # Mock host.get_fact to simulate different package managers
        with patch("lib.installers._utils.host") as mock_host:
            # Simulate pacman available
            mock_host.get_fact.side_effect = lambda _w, command=None: command == "pacman"
            assert get_package_manager() == "pacman"

            # Simulate apt-get available
            mock_host.get_fact.side_effect = lambda _w, command=None: command == "apt-get"
            assert get_package_manager() == "apt"

            # Simulate brew available
            mock_host.get_fact.side_effect = lambda _w, command=None: command == "brew"
            assert get_package_manager() == "brew"

            # Simulate no package manager
            mock_host.get_fact.side_effect = lambda _w, command=None: command is None
            assert get_package_manager() is None


class TestCppModule:
    """Tests for lib/installers/cpp.py."""

    def test_tools_list(self) -> None:
        """Verify TOOLS contains expected C++ tools."""
        from lib.installers.cpp import TOOLS

        assert "clang-format" in TOOLS
        assert "clang-tidy" in TOOLS


class TestNodeModule:
    """Tests for lib/installers/node.py."""

    def test_tools_list(self) -> None:
        """Verify TOOLS contains expected Node.js tools."""
        from lib.installers.node import TOOLS

        assert "@biomejs/biome" in TOOLS


class TestRustModule:
    """Tests for lib/installers/rust.py."""

    def test_tools_list(self) -> None:
        """Verify TOOLS contains expected Rust tools."""
        from lib.installers.rust import TOOLS

        assert "cargo-audit" in TOOLS


class TestGoModule:
    """Tests for lib/installers/go.py."""

    def test_tools_list(self) -> None:
        """Verify TOOLS contains expected Go tools."""
        from lib.installers.go import TOOLS

        tool_names = [t[0] for t in TOOLS]
        assert "golangci-lint" in tool_names
        assert "govulncheck" in tool_names

    def test_tools_have_install_paths(self) -> None:
        """Verify each tool has an install path."""
        from lib.installers.go import TOOLS

        for _tool_name, install_path in TOOLS:
            assert install_path.startswith(("github.com/", "golang.org/"))
            assert "@latest" in install_path


class TestLuaModule:
    """Tests for lib/installers/lua.py."""

    def test_tools_list(self) -> None:
        """Verify TOOLS contains expected Lua tools."""
        from lib.installers.lua import TOOLS

        assert "stylua" in TOOLS
        assert "luacheck" in TOOLS


class TestInstallPyMain:
    """Tests for install.py main module."""

    def test_parse_args_defaults(self) -> None:
        """Test argument parsing with defaults."""
        # Import parse_args from install.py
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from install import parse_args

        with patch("sys.argv", ["install.py"]):
            args = parse_args()
            assert not args.uninstall
            assert not args.force
            assert not args.all
            assert not args.python
            assert not args.node

    def test_parse_args_all_flag(self) -> None:
        """Test --all flag parsing."""
        from install import parse_args

        with patch("sys.argv", ["install.py", "--all"]):
            args = parse_args()
            assert args.all

    def test_parse_args_language_flags(self) -> None:
        """Test language-specific flag parsing."""
        from install import parse_args

        with patch("sys.argv", ["install.py", "--python", "--rust"]):
            args = parse_args()
            assert args.python
            assert args.rust
            assert not args.node
            assert not args.go

    def test_parse_args_force_flag(self) -> None:
        """Test --force flag parsing."""
        from install import parse_args

        with patch("sys.argv", ["install.py", "--force"]):
            args = parse_args()
            assert args.force

    def test_parse_args_uninstall_flag(self) -> None:
        """Test --uninstall flag parsing."""
        from install import parse_args

        with patch("sys.argv", ["install.py", "--uninstall"]):
            args = parse_args()
            assert args.uninstall

    def test_parse_args_dry_run_flag(self) -> None:
        """Test --dry-run flag parsing."""
        from install import parse_args

        with patch("sys.argv", ["install.py", "--dry-run"]):
            args = parse_args()
            assert args.dry_run

    def test_add_deploy_queues_function(self) -> None:
        """Test that add_deploy queues functions for later execution."""
        import install
        from install import add_deploy

        # Clear any existing pending deploys
        install._pending_deploys = []

        def dummy_deploy() -> None:
            pass

        add_deploy(dummy_deploy)
        assert len(install._pending_deploys) == 1
        assert install._pending_deploys[0][0] is dummy_deploy

        # Cleanup
        install._pending_deploys = []

    def test_add_deploy_preserves_args(self) -> None:
        """Test that add_deploy preserves positional and keyword arguments."""
        import install
        from install import add_deploy

        # Clear any existing pending deploys
        install._pending_deploys = []

        def dummy_deploy(a: int, b: str, *, force: bool = False) -> None:
            pass

        add_deploy(dummy_deploy, 1, "test", force=True)
        assert len(install._pending_deploys) == 1
        func, args, kwargs = install._pending_deploys[0]
        assert func is dummy_deploy
        assert args == (1, "test")
        assert kwargs == {"force": True}

        # Cleanup
        install._pending_deploys = []


class TestPackageManagerDetection:
    """Tests for package manager detection across modules."""

    @pytest.mark.parametrize(
        ("pm_command", "expected_result"),
        [
            ("pacman", "pacman"),
            ("apt-get", "apt"),
            ("dnf", "dnf"),
            ("yum", "yum"),
            ("apk", "apk"),
            ("brew", "brew"),
        ],
    )
    def test_utils_pm_detection(self, pm_command: str, expected_result: str) -> None:
        """Test package manager detection via shared utility."""
        from lib.installers._utils import get_package_manager

        with patch("lib.installers._utils.host") as mock_host:
            mock_host.get_fact.side_effect = lambda _w, command=None: command == pm_command
            assert get_package_manager() == expected_result

    def test_pm_detection_precedence_when_multiple_available(self) -> None:
        """Test that pacman takes precedence when multiple PMs are available."""
        from lib.installers._utils import get_package_manager

        # Simulate both pacman and apt-get being available
        available_pms = {"pacman", "apt-get", "brew"}

        with patch("lib.installers._utils.host") as mock_host:
            mock_host.get_fact.side_effect = lambda _w, command=None: command in available_pms
            # Should return pacman since it has highest priority
            assert get_package_manager() == "pacman"

    def test_pm_detection_apt_over_brew(self) -> None:
        """Test that apt takes precedence over brew when both available."""
        from lib.installers._utils import get_package_manager

        # Simulate apt-get and brew being available (common on macOS with Linux tools)
        available_pms = {"apt-get", "brew"}

        with patch("lib.installers._utils.host") as mock_host:
            mock_host.get_fact.side_effect = lambda _w, command=None: command in available_pms
            # Should return apt since it has higher priority than brew
            assert get_package_manager() == "apt"


class TestModuleExports:
    """Tests for lib/installers/__init__.py exports."""

    def test_all_exports_are_callables(self) -> None:
        """Verify all exported functions are callable."""
        from lib.installers import (
            install_core,
            install_cpp_tools,
            install_go_tools,
            install_lua_tools,
            install_node_tools,
            install_python_tools,
            install_rust_tools,
            install_shell_tools,
        )

        assert callable(install_core)
        assert callable(install_cpp_tools)
        assert callable(install_go_tools)
        assert callable(install_lua_tools)
        assert callable(install_node_tools)
        assert callable(install_python_tools)
        assert callable(install_rust_tools)
        assert callable(install_shell_tools)

    def test_all_list_contains_all_exports(self) -> None:
        """Verify __all__ contains all expected exports."""
        from lib.installers import __all__

        expected = [
            "install_core",
            "install_cpp_tools",
            "install_go_tools",
            "install_lua_tools",
            "install_node_tools",
            "install_python_tools",
            "install_rust_tools",
            "install_shell_tools",
        ]

        for export in expected:
            assert export in __all__
