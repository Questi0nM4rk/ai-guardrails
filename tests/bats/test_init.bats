#!/usr/bin/env bats
# =============================================================================
# CLI Init Tests
# =============================================================================
# Tests for the ai-guardrails-init CLI script
# =============================================================================

load helpers

setup() {
  setup_test_dir
  # Initialize a git repo for the tests that need it
  git init --quiet "$TEST_DIR"
}

teardown() {
  teardown_test_dir
}

# =============================================================================
# Basic Functionality
# =============================================================================

@test "shows help with --help" {
  run bash "$INIT_SCRIPT" --help
  [ "$status" -eq 0 ]
  assert_contains "$output" "Usage:"
  assert_contains "$output" "ai-guardrails-init"
}

@test "shows help with -h" {
  run bash "$INIT_SCRIPT" -h
  [ "$status" -eq 0 ]
  assert_contains "$output" "Usage:"
}

@test "fails with unknown option" {
  run bash "$INIT_SCRIPT" --invalid-option 2>&1
  [ "$status" -ne 0 ]
  assert_contains "$output" "Unknown option"
}

# =============================================================================
# Auto-Detection
# =============================================================================

@test "auto-detects Python project" {
  create_file "pyproject.toml"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_contains "$output" "Detected project type"
  assert_contains "$output" "python"
}

@test "auto-detects Go project" {
  create_file "go.mod"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_contains "$output" "Detected project type"
  assert_contains "$output" "go"
}

@test "auto-detects multiple languages" {
  create_file "pyproject.toml"
  create_file "package.json"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_contains "$output" "Detected multiple languages"
}

@test "fails when no language detected" {
  run run_init --no-coderabbit --no-ci 2>&1
  [ "$status" -ne 0 ]
  assert_contains "$output" "Could not detect project type"
}

# =============================================================================
# Config Copying
# =============================================================================

@test "copies .editorconfig" {
  create_file "pyproject.toml"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/.editorconfig"
}

@test "copies ruff.toml for Python projects" {
  create_file "pyproject.toml"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/ruff.toml"
}

@test "copies rustfmt.toml for Rust projects" {
  create_file "Cargo.toml"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/rustfmt.toml"
}

@test "copies biome.json for Node projects" {
  create_file "package.json"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/biome.json"
}

@test "copies .NET configs for .NET projects" {
  create_file "Project.csproj"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/Directory.Build.props"
  assert_file_exists "$TEST_DIR/.globalconfig"
}

@test "copies .clang-format for C++ projects" {
  create_file "CMakeLists.txt"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/.clang-format"
}

@test "copies stylua.toml for Lua projects" {
  create_file "init.lua"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/stylua.toml"
}

@test "copies all configs with --all" {
  run run_init --all --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/.editorconfig"
  assert_file_exists "$TEST_DIR/ruff.toml"
  assert_file_exists "$TEST_DIR/biome.json"
  assert_file_exists "$TEST_DIR/.clang-format"
  assert_file_exists "$TEST_DIR/stylua.toml"
  assert_file_exists "$TEST_DIR/rustfmt.toml"
  assert_file_exists "$TEST_DIR/Directory.Build.props"
  assert_file_exists "$TEST_DIR/.globalconfig"
}

# =============================================================================
# Force Mode
# =============================================================================

@test "does not overwrite existing config without --force" {
  create_file "pyproject.toml"
  echo "existing" >"$TEST_DIR/ruff.toml"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]

  local content
  content=$(cat "$TEST_DIR/ruff.toml")
  [ "$content" = "existing" ]
}

@test "overwrites existing config with --force" {
  create_file "pyproject.toml"
  echo "existing" >"$TEST_DIR/ruff.toml"

  run run_init --force --no-coderabbit --no-ci
  [ "$status" -eq 0 ]

  local content
  content=$(cat "$TEST_DIR/ruff.toml")
  [ "$content" != "existing" ]
}

# =============================================================================
# Pre-commit Config
# =============================================================================

@test "generates .pre-commit-config.yaml" {
  create_file "pyproject.toml"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/.pre-commit-config.yaml"
}

@test "skips pre-commit with --no-precommit" {
  create_file "pyproject.toml"

  run run_init --no-precommit --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_not_exists "$TEST_DIR/.pre-commit-config.yaml"
}

@test "generated pre-commit config contains detected language hooks" {
  create_file "pyproject.toml"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]

  local content
  content=$(cat "$TEST_DIR/.pre-commit-config.yaml")
  assert_contains "$content" "ruff"
  assert_contains "$content" "mypy"
}

# =============================================================================
# Explicit Type
# =============================================================================

@test "uses explicit type with --type" {
  # No detection files present, but explicit type given
  run run_init --type python --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  assert_file_exists "$TEST_DIR/ruff.toml"
}

@test "uses explicit type go with --type" {
  run run_init --type go --no-coderabbit --no-ci
  [ "$status" -eq 0 ]
  # Go doesn't need config files, but pre-commit should be generated
  assert_file_exists "$TEST_DIR/.pre-commit-config.yaml"

  local content
  content=$(cat "$TEST_DIR/.pre-commit-config.yaml")
  assert_contains "$content" "go-fmt"
}

# =============================================================================
# Gitignore
# =============================================================================

@test "adds .ai-guardrails to .gitignore" {
  create_file "pyproject.toml"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]

  local content
  content=$(cat "$TEST_DIR/.gitignore")
  assert_contains "$content" ".ai-guardrails/"
}

@test "does not duplicate .ai-guardrails in .gitignore" {
  create_file "pyproject.toml"
  echo ".ai-guardrails/" >"$TEST_DIR/.gitignore"

  run run_init --no-coderabbit --no-ci
  [ "$status" -eq 0 ]

  # Count occurrences - should be exactly 1
  local count
  count=$(grep -c "^\.ai-guardrails" "$TEST_DIR/.gitignore")
  [ "$count" -eq 1 ]
}
