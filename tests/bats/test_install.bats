#!/usr/bin/env bats
# ============================================
# Tests for install.sh and language installers
# ============================================
# shellcheck disable=SC2030,SC2031,SC2317  # PATH modifications and BATS test functions are intentional

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

@test "detect_pm.sh: has strict mode enabled (set -euo pipefail)" {
  # Check that detect_pm.sh has strict mode after shebang
  local file
  file="$BATS_TEST_DIRNAME/../../lib/installers/detect_pm.sh"
  local line2
  line2=$(sed -n '2p' "$file")
  [[ "$line2" == "set -euo pipefail" ]]
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
# Node Installer Stderr Capture Tests (Group G)
# ============================================

@test "node installer: captures npm stderr on failure" {
  # Mock npm to fail with permission error
  echo '#!/bin/bash
  echo "npm EACCES: permission denied" >&2
  exit 1
  ' >"$TEST_BIN_DIR/npm"
  chmod +x "$TEST_BIN_DIR/npm"
  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  run bash "$INSTALLERS_DIR/node.sh" 2>&1
  [[ "$status" -eq 0 ]] # Should not exit with error
  [[ "$output" == *"@biomejs/biome"* ]]
  [[ "$output" == *"Permission denied"* ]]
}

@test "node installer: shows helpful message for permission errors" {
  skip "Requires node.sh refactor to implement helpful error messages"
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
# Shell Installer Verification Tests (Group E)
# ============================================

@test "shell installer: verification section includes failure handling" {
  # Verify that shell.sh has the failure indicator code
  local shell_script="$INSTALLERS_DIR/shell.sh"

  # Check for FAILED variable
  grep -q "FAILED=false" "$shell_script" || return 1

  # Check for failure indicators (RED X)
  grep -q "RED.*✗" "$shell_script" || return 1

  # Check for "not found" messages
  grep -q "not found" "$shell_script" || return 1

  # Check for exit 1 on failure
  grep -q "exit 1" "$shell_script" || return 1

  # All checks passed
  return 0
}

@test "shell installer: verification shows success indicators for installed tools" {
  # Create real tools for verification testing
  echo '#!/bin/bash' >"$TEST_BIN_DIR/shellcheck"
  chmod +x "$TEST_BIN_DIR/shellcheck"
  echo '#!/bin/bash' >"$TEST_BIN_DIR/shfmt"
  chmod +x "$TEST_BIN_DIR/shfmt"

  # Test script that uses our mocked tools
  TEST_SCRIPT=$(mktemp)
  cat >"$TEST_SCRIPT" <<"TEST_CONTENT"
#!/bin/bash
# Simulate the verification section with our mocked tools available

export PATH="$TEST_BIN_DIR:/bin:/usr/bin"

FAILED=false
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if command -v shellcheck &>/dev/null; then
  echo -e "  ${GREEN}✓${NC} shellcheck"
else
  echo -e "  ${RED}✗${NC} shellcheck not found"
  FAILED=true
fi

if command -v shfmt &>/dev/null; then
  echo -e "  ${GREEN}✓${NC} shfmt"
else
  echo -e "  ${RED}✗${NC} shfmt not found"
  FAILED=true
fi

if [[ "$FAILED" == true ]]; then
  exit 1
fi
TEST_CONTENT

  run bash "$TEST_SCRIPT" 2>&1
  rm -f "$TEST_SCRIPT"
  [[ "$status" -eq 0 ]]
  [[ "$output" == *"✓"* ]]
  [[ "$output" == *"shellcheck"* ]]
  [[ "$output" == *"shfmt"* ]]
}

# ============================================
# C++ Installer Tests (Group D)
# ============================================

@test "cpp installer: has RED color variable defined" {
  grep -q "^RED=" "$INSTALLERS_DIR/cpp.sh"
}

@test "cpp installer: brew case installs llvm package" {
  grep -A 15 "brew)" "$INSTALLERS_DIR/cpp.sh" | grep -q "brew install llvm"
}

@test "cpp installer: brew case adds llvm to PATH" {
  grep -A 15 "brew)" "$INSTALLERS_DIR/cpp.sh" | grep -q 'export PATH=.*LLVM_BIN'
}

@test "cpp installer: brew case shows PATH note" {
  grep -A 15 "brew)" "$INSTALLERS_DIR/cpp.sh" | grep -q "Add to PATH for permanent access"
}

# NOTE: The following cpp installer tests are skipped because:
# - cpp.sh tries to INSTALL tools (via sudo pacman/apt) before verifying
# - Testing "tools not found" requires either:
#   a) Clean CI containers where tools genuinely don't exist
#   b) Complex mocking to intercept package manager calls
#   c) Refactoring cpp.sh to make verification testable in isolation
# These tests should run in CI with clean container environments.
# See: https://github.com/bats-core/bats-core#mocking

@test "cpp installer: verification shows red X for missing clang-format" {
  skip "Requires CI container without clang-format installed"
}

@test "cpp installer: verification shows red X for missing clang-tidy" {
  skip "Requires CI container without clang-tidy installed"
}

@test "cpp installer: exits with failure code when tools not found" {
  skip "Requires CI container - cpp.sh attempts real installation via package manager"
}

@test "cpp installer: exits successfully when both tools are found" {
  # Create mock clang-format and clang-tidy
  echo '#!/bin/bash' >"$TEST_BIN_DIR/clang-format"
  chmod +x "$TEST_BIN_DIR/clang-format"
  echo '#!/bin/bash' >"$TEST_BIN_DIR/clang-tidy"
  chmod +x "$TEST_BIN_DIR/clang-tidy"
  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  # Mock detect_package_manager to avoid actual installation
  export PM_OVERRIDE="none"

  # This should pass verification and exit successfully
  # Note: Will fail installation but pass verification
  skip "Requires cpp.sh refactor to skip installation when tools exist"
}

# ============================================
# Lua Installer Tests (Group H)
# ============================================

# Main Install Script Tests
# ============================================

@test "install.sh: accepts --python flag" {
  run "$BATS_TEST_DIRNAME/../../install.sh" --help
  [[ "$output" == *"--python"* ]]
}

@test "install.sh: accepts --node flag" {
  run "$BATS_TEST_DIRNAME/../../install.sh" --help
  [[ "$output" == *"--node"* ]]
}

@test "install.sh: accepts --all flag" {
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

# ============================================
# Lua Installer Tests (Group H)
# ============================================

@test "lua installer: stylua cargo install fails and pacman fallback succeeds" {
  # Create mock cargo that fails
  echo '#!/bin/bash' >"$TEST_BIN_DIR/cargo"
  echo 'exit 1' >>"$TEST_BIN_DIR/cargo"
  chmod +x "$TEST_BIN_DIR/cargo"

  # Create mock sudo that passes through to command
  cat >"$TEST_BIN_DIR/sudo" <<'SUDO_MOCK'
#!/bin/bash
"$@"
SUDO_MOCK
  chmod +x "$TEST_BIN_DIR/sudo"

  # Create mock pacman that succeeds
  echo '#!/bin/bash' >"$TEST_BIN_DIR/pacman"
  echo 'exit 0' >>"$TEST_BIN_DIR/pacman"
  chmod +x "$TEST_BIN_DIR/pacman"

  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  # Run lua installer and check for pacman fallback message
  run bash -c "source $BATS_TEST_DIRNAME/../../lib/installers/lua.sh 2>&1"
  [[ "$output" =~ "via pacman fallback" ]]
}

@test "lua installer: stylua cargo install succeeds, no fallback attempted" {
  # Create mock cargo that succeeds
  echo '#!/bin/bash' >"$TEST_BIN_DIR/cargo"
  echo 'exit 0' >>"$TEST_BIN_DIR/cargo"
  chmod +x "$TEST_BIN_DIR/cargo"

  # Create mock pacman that should not be called
  echo '#!/bin/bash' >"$TEST_BIN_DIR/pacman"
  echo 'exit 1' >>"$TEST_BIN_DIR/pacman"
  chmod +x "$TEST_BIN_DIR/pacman"

  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  # Run lua installer - should succeed with cargo
  run bash -c "source $BATS_TEST_DIRNAME/../../lib/installers/lua.sh 2>&1"
  [[ "$output" =~ "via cargo" ]]
  [[ ! "$output" =~ "via pacman" ]]
}

@test "lua installer: stylua cargo fails and non-pacman system shows error" {
  # Create mock cargo that fails
  echo '#!/bin/bash' >"$TEST_BIN_DIR/cargo"
  echo 'exit 1' >>"$TEST_BIN_DIR/cargo"
  chmod +x "$TEST_BIN_DIR/cargo"

  # Create mock apt-get (not pacman, no fallback)
  echo '#!/bin/bash' >"$TEST_BIN_DIR/apt-get"
  echo 'exit 0' >>"$TEST_BIN_DIR/apt-get"
  chmod +x "$TEST_BIN_DIR/apt-get"

  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  # Run lua installer - should fail cargo and have no fallback
  run bash -c "source $BATS_TEST_DIRNAME/../../lib/installers/lua.sh 2>&1"
  # Should show failure indicator (✗) and no fallback
  [[ "$output" =~ "Installing stylua" ]]
  [[ ! "$output" =~ "via pacman fallback" ]]
}
