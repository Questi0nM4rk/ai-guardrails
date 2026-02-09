"""Tests for language detection via guardrails.assemble.detect_languages.

Migrated from tests/bats/test_detection.bats. Uses the real languages.yaml
registry to verify detection from file markers, glob patterns, and directories.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from guardrails.assemble import detect_languages, load_registry


@pytest.fixture
def registry() -> dict[str, Any]:
    """Load the real language registry from configs/languages.yaml."""
    repo_root = Path(__file__).parent.parent
    registry_path = repo_root / "configs" / "languages.yaml"
    return load_registry(registry_path)


# =============================================================================
# Python Detection
# =============================================================================


class TestPythonDetection:
    """Detect Python from pyproject.toml, setup.py, requirements.txt, *.py."""

    def test_detects_from_pyproject_toml(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "pyproject.toml").touch()
        result = detect_languages(tmp_path, registry)
        assert "python" in result

    def test_detects_from_setup_py(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "setup.py").touch()
        result = detect_languages(tmp_path, registry)
        assert "python" in result

    def test_detects_from_requirements_txt(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "requirements.txt").touch()
        result = detect_languages(tmp_path, registry)
        assert "python" in result

    def test_detects_from_py_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "main.py").touch()
        result = detect_languages(tmp_path, registry)
        assert "python" in result


# =============================================================================
# Rust Detection
# =============================================================================


class TestRustDetection:
    """Detect Rust from Cargo.toml, *.rs."""

    def test_detects_from_cargo_toml(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "Cargo.toml").touch()
        result = detect_languages(tmp_path, registry)
        assert "rust" in result

    def test_detects_from_rs_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "main.rs").touch()
        result = detect_languages(tmp_path, registry)
        assert "rust" in result


# =============================================================================
# Go Detection
# =============================================================================


class TestGoDetection:
    """Detect Go from go.mod, go.sum, *.go."""

    def test_detects_from_go_mod(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "go.mod").touch()
        result = detect_languages(tmp_path, registry)
        assert "go" in result

    def test_detects_from_go_sum(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "go.sum").touch()
        result = detect_languages(tmp_path, registry)
        assert "go" in result

    def test_detects_from_go_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "main.go").touch()
        result = detect_languages(tmp_path, registry)
        assert "go" in result


# =============================================================================
# Node/TypeScript Detection
# =============================================================================


class TestNodeDetection:
    """Detect Node/TypeScript from package.json, tsconfig.json, *.ts, *.js, *.tsx."""

    def test_detects_from_package_json(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "package.json").touch()
        result = detect_languages(tmp_path, registry)
        assert "node" in result

    def test_detects_from_tsconfig_json(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "tsconfig.json").touch()
        result = detect_languages(tmp_path, registry)
        assert "node" in result

    def test_detects_from_ts_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "app.ts").touch()
        result = detect_languages(tmp_path, registry)
        assert "node" in result

    def test_detects_from_js_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "app.js").touch()
        result = detect_languages(tmp_path, registry)
        assert "node" in result

    def test_detects_from_tsx_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "Component.tsx").touch()
        result = detect_languages(tmp_path, registry)
        assert "node" in result


# =============================================================================
# .NET Detection
# =============================================================================


class TestDotnetDetection:
    """Detect .NET from *.csproj, *.sln."""

    def test_detects_from_csproj_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "Project.csproj").touch()
        result = detect_languages(tmp_path, registry)
        assert "dotnet" in result

    def test_detects_from_sln_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "Solution.sln").touch()
        result = detect_languages(tmp_path, registry)
        assert "dotnet" in result


# =============================================================================
# C/C++ Detection
# =============================================================================


class TestCppDetection:
    """Detect C/C++ from CMakeLists.txt, *.cpp, *.c."""

    def test_detects_from_cmakelists(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "CMakeLists.txt").touch()
        result = detect_languages(tmp_path, registry)
        assert "cpp" in result

    def test_detects_from_cpp_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "main.cpp").touch()
        result = detect_languages(tmp_path, registry)
        assert "cpp" in result

    def test_detects_from_c_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "main.c").touch()
        result = detect_languages(tmp_path, registry)
        assert "cpp" in result


# =============================================================================
# Lua Detection
# =============================================================================


class TestLuaDetection:
    """Detect Lua from *.lua, *.rockspec, lua/ directory."""

    def test_detects_from_lua_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "init.lua").touch()
        result = detect_languages(tmp_path, registry)
        assert "lua" in result

    def test_detects_from_rockspec_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "mylib-1.0-1.rockspec").touch()
        result = detect_languages(tmp_path, registry)
        assert "lua" in result

    def test_detects_from_lua_directory(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "lua").mkdir()
        result = detect_languages(tmp_path, registry)
        assert "lua" in result


# =============================================================================
# Shell Detection
# =============================================================================


class TestShellDetection:
    """Detect Shell from *.sh, *.bash."""

    def test_detects_from_sh_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "script.sh").touch()
        result = detect_languages(tmp_path, registry)
        assert "shell" in result

    def test_detects_from_bash_files(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "script.bash").touch()
        result = detect_languages(tmp_path, registry)
        assert "shell" in result


# =============================================================================
# Multi-Language Detection
# =============================================================================


class TestMultiLanguageDetection:
    """Detect multiple languages from mixed project markers."""

    def test_detects_python_and_node(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "package.json").touch()
        result = detect_languages(tmp_path, registry)
        assert "python" in result
        assert "node" in result

    def test_detects_python_go_and_shell(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "go.mod").touch()
        (tmp_path / "script.sh").touch()
        result = detect_languages(tmp_path, registry)
        assert "python" in result
        assert "go" in result
        assert "shell" in result


# =============================================================================
# No Detection
# =============================================================================


class TestNoDetection:
    """Empty or unrecognized directories yield no detected languages."""

    def test_empty_directory_returns_empty(self, tmp_path: Path, registry: dict[str, Any]) -> None:
        result = detect_languages(tmp_path, registry)
        assert result == []

    def test_unrecognized_files_returns_empty(
        self, tmp_path: Path, registry: dict[str, Any]
    ) -> None:
        (tmp_path / "README.md").touch()
        (tmp_path / "LICENSE").touch()
        result = detect_languages(tmp_path, registry)
        assert result == []
