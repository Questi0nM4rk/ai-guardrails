#!/usr/bin/env bats
# =============================================================================
# Language Detection Tests
# =============================================================================
# Tests for the language detection functionality in assemble_precommit.py
# =============================================================================

load helpers

setup() {
  setup_test_dir
}

teardown() {
  teardown_test_dir
}

# =============================================================================
# Python Detection
# =============================================================================

@test "detects Python from pyproject.toml" {
  create_file "pyproject.toml"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "python"
}

@test "detects Python from setup.py" {
  create_file "setup.py"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "python"
}

@test "detects Python from requirements.txt" {
  create_file "requirements.txt"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "python"
}

@test "detects Python from .py files" {
  create_file "main.py"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "python"
}

# =============================================================================
# Rust Detection
# =============================================================================

@test "detects Rust from Cargo.toml" {
  create_file "Cargo.toml"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "rust"
}

# =============================================================================
# Go Detection
# =============================================================================

@test "detects Go from go.mod" {
  create_file "go.mod"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "go"
}

@test "detects Go from go.sum" {
  create_file "go.sum"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "go"
}

@test "detects Go from .go files" {
  create_file "main.go"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "go"
}

# =============================================================================
# Node/TypeScript Detection
# =============================================================================

@test "detects Node from package.json" {
  create_file "package.json"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "node"
}

@test "detects Node from tsconfig.json" {
  create_file "tsconfig.json"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "node"
}

# =============================================================================
# .NET Detection
# =============================================================================

@test "detects .NET from .csproj files" {
  create_file "Project.csproj"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "dotnet"
}

@test "detects .NET from .sln files" {
  create_file "Solution.sln"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "dotnet"
}

# =============================================================================
# C/C++ Detection
# =============================================================================

@test "detects C++ from CMakeLists.txt" {
  create_file "CMakeLists.txt"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "cpp"
}

@test "detects C++ from Makefile" {
  create_file "Makefile"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "cpp"
}

@test "detects C++ from .cpp files" {
  create_file "main.cpp"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "cpp"
}

@test "detects C from .c files" {
  create_file "main.c"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "cpp"
}

# =============================================================================
# Lua Detection
# =============================================================================

@test "detects Lua from .lua files" {
  create_file "init.lua"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "lua"
}

@test "detects Lua from .rockspec files" {
  create_file "mylib-1.0-1.rockspec"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "lua"
}

@test "detects Lua from lua/ directory" {
  mkdir -p "$TEST_DIR/lua"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "lua"
}

# =============================================================================
# Shell Detection
# =============================================================================

@test "detects Shell from .sh files" {
  create_file "script.sh"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "shell"
}

@test "detects Shell from .bash files" {
  create_file "script.bash"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "shell"
}

# =============================================================================
# Multi-Language Detection
# =============================================================================

@test "detects multiple languages" {
  create_file "pyproject.toml"
  create_file "package.json"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "python"
  assert_contains "$output" "node"
}

@test "detects Python, Go, and Shell" {
  create_file "pyproject.toml"
  create_file "go.mod"
  create_file "script.sh"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "python"
  assert_contains "$output" "go"
  assert_contains "$output" "shell"
}

# =============================================================================
# No Detection
# =============================================================================

@test "returns empty for empty directory" {
  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "No languages detected"
}

@test "returns empty for unrecognized files" {
  create_file "README.md"
  create_file "LICENSE"

  run run_assemble --list-detected
  [ "$status" -eq 0 ]
  assert_contains "$output" "No languages detected"
}
