#!/usr/bin/env bats
# =============================================================================
# Template Assembly Tests
# =============================================================================
# Tests for the pre-commit config assembly functionality
# =============================================================================

load helpers

setup() {
  setup_test_dir
}

teardown() {
  teardown_test_dir
}

# =============================================================================
# Basic Assembly
# =============================================================================

@test "generates config with base hooks" {
  run run_assemble --dry-run
  [ "$status" -eq 0 ]

  # Base hooks should always be present
  assert_contains "$output" "gitleaks"
  assert_contains "$output" "detect-secrets"
  assert_contains "$output" "codespell"
  assert_contains "$output" "trailing-whitespace"
  assert_contains "$output" "check-yaml"
}

@test "generates config for Python language" {
  run run_assemble --languages python --dry-run
  [ "$status" -eq 0 ]

  # Python-specific hooks
  assert_contains "$output" "ruff"
  assert_contains "$output" "mypy"
  assert_contains "$output" "bandit"
  assert_contains "$output" "vulture"

  # Should not contain other language hooks
  assert_not_contains "$output" "cargo-fmt"
  assert_not_contains "$output" "golangci-lint"
}

@test "generates config for Go language" {
  run run_assemble --languages go --dry-run
  [ "$status" -eq 0 ]

  # Go-specific hooks
  assert_contains "$output" "go-fmt"
  assert_contains "$output" "go-vet"
  assert_contains "$output" "golangci-lint"
  assert_contains "$output" "go-vulncheck"

  # Should not contain other language hooks
  assert_not_contains "$output" "ruff"
  assert_not_contains "$output" "cargo-fmt"
}

@test "generates config for Rust language" {
  run run_assemble --languages rust --dry-run
  [ "$status" -eq 0 ]

  # Rust-specific hooks
  assert_contains "$output" "cargo-fmt"
  assert_contains "$output" "cargo-clippy"
  assert_contains "$output" "cargo-doc"
  assert_contains "$output" "cargo-audit"

  # Should not contain other language hooks
  assert_not_contains "$output" "ruff"
  assert_not_contains "$output" "golangci-lint"
}

@test "generates config for Node/TypeScript language" {
  run run_assemble --languages node --dry-run
  [ "$status" -eq 0 ]

  # Node-specific hooks
  assert_contains "$output" "biome-check"
  assert_contains "$output" "tsc"
  assert_contains "$output" "npm-audit"

  # Should not contain other language hooks
  assert_not_contains "$output" "ruff"
  assert_not_contains "$output" "cargo-fmt"
}

@test "generates config for .NET language" {
  run run_assemble --languages dotnet --dry-run
  [ "$status" -eq 0 ]

  # .NET-specific hooks
  assert_contains "$output" "dotnet-format"
  assert_contains "$output" "dotnet-build"

  # Should not contain other language hooks
  assert_not_contains "$output" "ruff"
  assert_not_contains "$output" "cargo-fmt"
}

@test "generates config for C++ language" {
  run run_assemble --languages cpp --dry-run
  [ "$status" -eq 0 ]

  # C++-specific hooks
  assert_contains "$output" "clang-format"
  assert_contains "$output" "clang-tidy"

  # Should not contain other language hooks
  assert_not_contains "$output" "ruff"
  assert_not_contains "$output" "cargo-fmt"
}

@test "generates config for Lua language" {
  run run_assemble --languages lua --dry-run
  [ "$status" -eq 0 ]

  # Lua-specific hooks
  assert_contains "$output" "stylua"
  assert_contains "$output" "luacheck"

  # Should not contain other language hooks
  assert_not_contains "$output" "ruff"
  assert_not_contains "$output" "cargo-fmt"
}

@test "generates config for Shell language" {
  run run_assemble --languages shell --dry-run
  [ "$status" -eq 0 ]

  # Shell-specific hooks
  assert_contains "$output" "shellcheck"
  assert_contains "$output" "shfmt"

  # Should not contain other language hooks
  assert_not_contains "$output" "ruff"
  assert_not_contains "$output" "cargo-fmt"
}

# =============================================================================
# Multi-Language Assembly
# =============================================================================

@test "generates config for multiple languages" {
  run run_assemble --languages python go --dry-run
  [ "$status" -eq 0 ]

  # Python hooks
  assert_contains "$output" "ruff"
  assert_contains "$output" "mypy"

  # Go hooks
  assert_contains "$output" "go-fmt"
  assert_contains "$output" "golangci-lint"
}

@test "generates config for all languages" {
  run run_assemble --languages python rust dotnet cpp lua node go shell --dry-run
  [ "$status" -eq 0 ]

  # All language hooks should be present
  assert_contains "$output" "ruff"          # Python
  assert_contains "$output" "cargo-fmt"     # Rust
  assert_contains "$output" "dotnet-format" # .NET
  assert_contains "$output" "clang-format"  # C++
  assert_contains "$output" "stylua"        # Lua
  assert_contains "$output" "biome-check"   # Node
  assert_contains "$output" "go-fmt"        # Go
  assert_contains "$output" "shellcheck"    # Shell
}

# =============================================================================
# Auto-Detection Assembly
# =============================================================================

@test "auto-detects and generates config for Python project" {
  create_file "pyproject.toml"

  run run_assemble --dry-run
  [ "$status" -eq 0 ]

  # Python hooks should be present
  assert_contains "$output" "ruff"
  assert_contains "$output" "mypy"
}

@test "auto-detects and generates config for Go project" {
  create_file "go.mod"

  run run_assemble --dry-run
  [ "$status" -eq 0 ]

  # Go hooks should be present
  assert_contains "$output" "go-fmt"
  assert_contains "$output" "golangci-lint"
}

@test "auto-detects and generates config for multi-language project" {
  create_file "pyproject.toml"
  create_file "go.mod"
  create_file "script.sh"

  run run_assemble --dry-run
  [ "$status" -eq 0 ]

  # All detected language hooks should be present
  assert_contains "$output" "ruff"
  assert_contains "$output" "go-fmt"
  assert_contains "$output" "shellcheck"
}

# =============================================================================
# Output File
# =============================================================================

@test "writes config to output file" {
  create_file "pyproject.toml"

  run run_assemble --output "$TEST_DIR/.pre-commit-config.yaml"
  [ "$status" -eq 0 ]

  assert_file_exists "$TEST_DIR/.pre-commit-config.yaml"

  # Check file contents
  local content
  content=$(cat "$TEST_DIR/.pre-commit-config.yaml")
  assert_contains "$content" "ruff"
  assert_contains "$content" "mypy"
}

@test "writes config with header comment" {
  run run_assemble --languages python --output "$TEST_DIR/.pre-commit-config.yaml"
  [ "$status" -eq 0 ]

  local content
  content=$(cat "$TEST_DIR/.pre-commit-config.yaml")
  assert_contains "$content" "AI Guardrails"
  assert_contains "$content" "Auto-Generated"
}

# =============================================================================
# Error Handling
# =============================================================================

@test "fails for unknown language" {
  run run_assemble --languages invalid_language --dry-run
  [ "$status" -ne 0 ]
  assert_contains "$output" "Unknown languages"
}

@test "warns when no languages detected" {
  run run_assemble --dry-run
  [ "$status" -eq 0 ]
  # Should still generate base config
  assert_contains "$output" "gitleaks"
}

# =============================================================================
# YAML Validity
# =============================================================================

@test "generates valid YAML" {
  create_file "pyproject.toml"
  create_file "go.mod"

  run run_assemble --output "$TEST_DIR/.pre-commit-config.yaml"
  [ "$status" -eq 0 ]

  # Validate YAML syntax
  run python3 -c "import yaml; yaml.safe_load(open('$TEST_DIR/.pre-commit-config.yaml'))"
  [ "$status" -eq 0 ]
}
