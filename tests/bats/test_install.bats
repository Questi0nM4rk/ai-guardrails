#!/usr/bin/env bats
# ============================================
# Tests for install.sh and language installers
# ============================================
# shellcheck disable=SC2030,SC2031  # PATH modifications are intentional for BATS test isolation

setup() {
  # Create temp directory for test installations
  TEST_INSTALL_DIR="$(mktemp -d)"
  export TEST_INSTALL_DIR
  export TEST_BIN_DIR="$TEST_INSTALL_DIR/bin"
  mkdir -p "$TEST_BIN_DIR"

  # Mock HOME for testing
  export ORIGINAL_HOME="$HOME"
  export HOME="$TEST_INSTALL_DIR"

  # Save original PATH
  export ORIGINAL_PATH="$PATH"

  # Create mock installer scripts
  export INSTALLERS_DIR="$BATS_TEST_DIRNAME/../../lib/installers"
}

teardown() {
  # Clean up test directory
  rm -rf "$TEST_INSTALL_DIR"
  export HOME="$ORIGINAL_HOME"
  export PATH="$ORIGINAL_PATH"
}

# ============================================
# Package Manager Detection Tests
# ============================================

@test "detect_package_manager: identifies pacman" {
  # Create mock pacman in test bin
  echo '#!/bin/bash' >"$TEST_BIN_DIR/pacman"
  chmod +x "$TEST_BIN_DIR/pacman"
  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  # shellcheck source=lib/installers/detect_pm.sh
  source "$BATS_TEST_DIRNAME/../../lib/installers/detect_pm.sh"
  result=$(detect_package_manager)
  [[ "$result" == "pacman" ]]
}

@test "detect_package_manager: identifies apt" {
  # Create mock apt-get in test bin (higher priority than real pacman)
  echo '#!/bin/bash' >"$TEST_BIN_DIR/apt-get"
  chmod +x "$TEST_BIN_DIR/apt-get"
  # Remove pacman from path by using only test bin
  export PATH="$TEST_BIN_DIR"

  # shellcheck source=lib/installers/detect_pm.sh
  source "$BATS_TEST_DIRNAME/../../lib/installers/detect_pm.sh"
  result=$(detect_package_manager)
  [[ "$result" == "apt" ]]
}

@test "detect_package_manager: identifies brew" {
  # Create mock brew in test bin
  echo '#!/bin/bash' >"$TEST_BIN_DIR/brew"
  chmod +x "$TEST_BIN_DIR/brew"
  # Remove other package managers from path
  export PATH="$TEST_BIN_DIR"

  # shellcheck source=lib/installers/detect_pm.sh
  source "$BATS_TEST_DIRNAME/../../lib/installers/detect_pm.sh"
  result=$(detect_package_manager)
  [[ "$result" == "brew" ]]
}

@test "detect_package_manager: returns none when no package manager found" {
  # Use empty PATH to ensure no package managers found
  export PATH="$TEST_BIN_DIR"

  # shellcheck source=lib/installers/detect_pm.sh
  source "$BATS_TEST_DIRNAME/../../lib/installers/detect_pm.sh"
  result=$(detect_package_manager)
  [[ "$result" == "none" ]]
}

# ============================================
# Python Installer Tests
# ============================================

@test "python installer: checks for pip3" {
  skip "Requires mocking pip3"
  run "$INSTALLERS_DIR/python.sh"
  [[ "$status" -eq 0 ]] || [[ "$output" == *"pip3 not found"* ]]
}

@test "python installer: installs ruff, mypy, bandit, vulture, pip-audit" {
  skip "Integration test - requires actual pip3"
  run "$INSTALLERS_DIR/python.sh" --dry-run
  [[ "$output" == *"ruff"* ]]
  [[ "$output" == *"mypy"* ]]
  [[ "$output" == *"bandit"* ]]
  [[ "$output" == *"vulture"* ]]
  [[ "$output" == *"pip-audit"* ]]
}

# ============================================
# Node Installer Tests
# ============================================

@test "node installer: checks for npm" {
  skip "Requires mocking npm"
  run "$INSTALLERS_DIR/node.sh"
  [[ "$status" -eq 0 ]] || [[ "$output" == *"npm not found"* ]]
}

@test "node installer: installs biome globally" {
  skip "Integration test - requires actual npm"
  run "$INSTALLERS_DIR/node.sh" --dry-run
  [[ "$output" == *"@biomejs/biome"* ]]
}

# ============================================
# Shell Installer Tests
# ============================================

@test "shell installer: installs shellcheck and shfmt" {
  skip "Integration test - requires actual package manager"
  run "$INSTALLERS_DIR/shell.sh" --dry-run
  [[ "$output" == *"shellcheck"* ]]
  [[ "$output" == *"shfmt"* ]]
}

# ============================================
# Main Install Script Tests
# ============================================

@test "install.sh: accepts --python flag" {
  skip "Requires full install.sh refactor"
  run "$BATS_TEST_DIRNAME/../../install.sh" --help
  [[ "$output" == *"--python"* ]]
}

@test "install.sh: accepts --node flag" {
  skip "Requires full install.sh refactor"
  run "$BATS_TEST_DIRNAME/../../install.sh" --help
  [[ "$output" == *"--node"* ]]
}

@test "install.sh: accepts --all flag" {
  skip "Requires full install.sh refactor"
  run "$BATS_TEST_DIRNAME/../../install.sh" --help
  [[ "$output" == *"--all"* ]]
}

@test "install.sh: installs pyyaml and pre-commit by default" {
  skip "Integration test - modifies system"
  run "$BATS_TEST_DIRNAME/../../install.sh" --force --dry-run
  [[ "$output" == *"pyyaml"* ]]
  [[ "$output" == *"pre-commit"* ]]
}

@test "install.sh: copies installer scripts to installation directory" {
  skip "Integration test - requires full implementation"
  run "$BATS_TEST_DIRNAME/../../install.sh" --force
  [[ -d "$HOME/.ai-guardrails/lib/installers" ]]
  [[ -f "$HOME/.ai-guardrails/lib/installers/python.sh" ]]
  [[ -f "$HOME/.ai-guardrails/lib/installers/node.sh" ]]
}
