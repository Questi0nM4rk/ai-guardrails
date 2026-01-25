#!/usr/bin/env bats
# ============================================
# Tests for Python installer improvements (Group F)
# ============================================
# shellcheck disable=SC2016,SC2030,SC2031,SC2317  # Single quotes in heredocs, PATH modifications, and BATS test functions are intentional

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

  # Reference installer script
  export INSTALLERS_DIR="$BATS_TEST_DIRNAME/../../lib/installers"
}

teardown() {
  # Restore PATH first so rm is available
  export PATH="$ORIGINAL_PATH"
  export HOME="$ORIGINAL_HOME"
  # Clean up test directory
  rm -rf "$TEST_INSTALL_DIR"
}

# ============================================
# PATH Check Tests (Improvement 1)
# ============================================

@test "python installer with pip3: warns about PATH when user bin not in PATH" {
  # Create mock python3 that returns a user bin directory
  echo '#!/bin/bash
if [[ "$1" == "-m" && "$2" == "site" && "$3" == "--user-base" ]]; then
	echo "/mock/user/python"
fi' >"$TEST_BIN_DIR/python3"
  chmod +x "$TEST_BIN_DIR/python3"

  # Create mock pip3 that succeeds
  echo '#!/bin/bash
exit 0' >"$TEST_BIN_DIR/pip3"
  chmod +x "$TEST_BIN_DIR/pip3"

  # Set PATH without the user bin
  export PATH="$TEST_BIN_DIR"

  run "$INSTALLERS_DIR/python.sh"
  [[ "$status" -eq 0 ]]
  [[ "$output" == *"Note: Add to PATH for tool access: /mock/user/python/bin"* ]]
}

@test "python installer with pip3: no PATH warning when user bin already in PATH" {
  # Create mock python3 that returns a user bin directory
  echo '#!/bin/bash
if [[ "$1" == "-m" && "$2" == "site" && "$3" == "--user-base" ]]; then
	echo "/mock/user/python"
fi' >"$TEST_BIN_DIR/python3"
  chmod +x "$TEST_BIN_DIR/python3"

  # Create mock pip3 that succeeds
  echo '#!/bin/bash
exit 0' >"$TEST_BIN_DIR/pip3"
  chmod +x "$TEST_BIN_DIR/pip3"

  # Set PATH with the user bin already included
  export PATH="$TEST_BIN_DIR:/mock/user/python/bin"

  run "$INSTALLERS_DIR/python.sh"
  [[ "$status" -eq 0 ]]
  [[ "$output" != *"Note: Add to PATH for tool access"* ]]
}

# ============================================
# pipx Install/Upgrade Pattern Tests (Improvement 2)
# ============================================

@test "python installer with pipx: upgrades when package already installed" {
  # Create mock pipx list that shows all packages installed
  echo '#!/bin/bash
if [[ "$1" == "list" ]]; then
	echo "venvs are in /mock/.local/pipx/venvs"
	echo "apps are in /mock/.local/bin"
	echo "   package ruff 0.1.0, installed using Python 3.12.0"
	echo "   package mypy 1.0.0, installed using Python 3.12.0"
	echo "   package bandit 1.0.0, installed using Python 3.12.0"
	echo "   package vulture 1.0.0, installed using Python 3.12.0"
	echo "   package pip-audit 1.0.0, installed using Python 3.12.0"
fi
# Handle upgrade for any tool
if [[ "$1" == "upgrade" ]]; then
	exit 0
fi' >"$TEST_BIN_DIR/pipx"
  chmod +x "$TEST_BIN_DIR/pipx"

  export PATH="$TEST_BIN_DIR"

  run "$INSTALLERS_DIR/python.sh"
  [[ "$status" -eq 0 ]]
  [[ "$output" == *"(upgraded)"* ]]
}

@test "python installer with pipx: installs when package not present" {
  # Create mock pipx that shows no packages
  echo '#!/bin/bash
if [[ "$1" == "list" ]]; then
	echo "venvs are in /mock/.local/pipx/venvs"
	echo "apps are in /mock/.local/bin"
fi
if [[ "$1" == "install" ]]; then
	exit 0
fi' >"$TEST_BIN_DIR/pipx"
  chmod +x "$TEST_BIN_DIR/pipx"

  export PATH="$TEST_BIN_DIR"

  run "$INSTALLERS_DIR/python.sh"
  [[ "$status" -eq 0 ]]
  # Should not say "already installed" for new installations
  [[ "$output" != *"already installed"* ]] || [[ "$output" == *"✓"* ]]
}

@test "python installer with pipx: shows 'upgrade skipped' when upgrade fails" {
  # Create mock pipx that shows package installed but upgrade fails
  echo '#!/bin/bash
if [[ "$1" == "list" ]]; then
	echo "   package ruff 0.1.0, installed using Python 3.12.0"
fi
if [[ "$1" == "upgrade" ]]; then
	exit 1
fi' >"$TEST_BIN_DIR/pipx"
  chmod +x "$TEST_BIN_DIR/pipx"

  export PATH="$TEST_BIN_DIR"

  run "$INSTALLERS_DIR/python.sh"
  [[ "$status" -eq 0 ]]
  [[ "$output" == *"upgrade skipped"* ]]
}
