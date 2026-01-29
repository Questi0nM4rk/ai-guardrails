#!/usr/bin/env bats
# ============================================
# Tests for Group A: Critical Dependency Handling
# ============================================
# shellcheck disable=SC2030,SC2031,SC2317,SC2329  # PATH modifications, inline functions, and BATS test functions are intentional

setup() {
  # Create temp directory for test installations
  TEST_INSTALL_DIR="$(mktemp -d)"
  export TEST_INSTALL_DIR
  export TEST_BIN_DIR="$TEST_INSTALL_DIR/bin"
  mkdir -p "$TEST_BIN_DIR"

  # Save original PATH
  export ORIGINAL_PATH="$PATH"
}

teardown() {
  # Clean up test directory
  rm -rf "$TEST_INSTALL_DIR"
  export PATH="$ORIGINAL_PATH"
}

# ============================================
# pyyaml Verification Tests
# ============================================

@test "pyyaml verification: reports 'already installed' only when import succeeds" {
  # Create mock python3 that successfully imports yaml
  cat >"$TEST_BIN_DIR/python3" <<'EOF'
#!/bin/bash
if [[ "$*" == *"import yaml"* ]]; then
  exit 0  # yaml import succeeds
fi
exec /usr/bin/python3 "$@"
EOF
  chmod +x "$TEST_BIN_DIR/python3"
  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  # Extract pyyaml installation logic into testable function
  check_pyyaml_installed() {
    if python3 -c "import yaml" &>/dev/null; then
      echo "already installed"
      return 0
    else
      return 1
    fi
  }

  run check_pyyaml_installed
  [[ "$status" -eq 0 ]]
  [[ "$output" == "already installed" ]]
}

@test "pyyaml verification: does not report 'already installed' when import fails" {
  # Create mock python3 that fails to import yaml
  cat >"$TEST_BIN_DIR/python3" <<'EOF'
#!/bin/bash
if [[ "$*" == *"import yaml"* ]]; then
  exit 1  # yaml import fails
fi
exec /usr/bin/python3 "$@"
EOF
  chmod +x "$TEST_BIN_DIR/python3"
  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  check_pyyaml_installed() {
    if python3 -c "import yaml" &>/dev/null; then
      echo "already installed"
      return 0
    else
      return 1
    fi
  }

  run check_pyyaml_installed
  [[ "$status" -eq 1 ]]
  [[ "$output" != "already installed" ]]
}

@test "pyyaml installation: exits with error when all install methods fail" {
  # This test verifies the NEW behavior where:
  # 1. pip install appears to succeed
  # 2. But verification (import yaml) still fails
  # 3. Script exits with error

  # Create mock python3 that fails yaml import always
  cat >"$TEST_BIN_DIR/python3" <<'EOF'
#!/bin/bash
if [[ "$*" == *"import yaml"* ]]; then
  exit 1  # yaml never available (even after "install")
fi
# Pass through to real python3 for pip operations
exec /usr/bin/python3 "$@"
EOF
  chmod +x "$TEST_BIN_DIR/python3"
  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  # Simulate the install.sh logic exactly
  install_pyyaml_with_verification() {
    if ! python3 -c "import yaml" &>/dev/null; then
      # Try first installation method
      if python3 -m pip install --user --quiet pyyaml 2>/dev/null; then
        # Verify installation succeeded
        if python3 -c "import yaml" &>/dev/null; then
          echo "Success"
          return 0
        else
          echo "Error: Failed to install pyyaml"
          return 1
        fi
      elif python3 -m pip install --user --break-system-packages --quiet pyyaml 2>/dev/null; then
        # Verify installation succeeded
        if python3 -c "import yaml" &>/dev/null; then
          echo "Success (--break-system-packages)"
          return 0
        else
          echo "Error: Failed to install pyyaml"
          return 1
        fi
      else
        # Installation commands failed, verify not already installed
        if python3 -c "import yaml" &>/dev/null; then
          echo "Already installed"
          return 0
        else
          echo "Error: Failed to install pyyaml"
          return 1
        fi
      fi
    fi
    return 0
  }

  run install_pyyaml_with_verification
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"Error: Failed to install pyyaml"* ]]
}

# ============================================
# pre-commit Verification Tests
# ============================================

@test "pre-commit verification: reports 'already installed' only when command exists" {
  # Create mock pre-commit command
  cat >"$TEST_BIN_DIR/pre-commit" <<'EOF'
#!/bin/bash
echo "pre-commit 3.0.0"
EOF
  chmod +x "$TEST_BIN_DIR/pre-commit"
  export PATH="$TEST_BIN_DIR:$ORIGINAL_PATH"

  check_precommit_installed() {
    if command -v pre-commit &>/dev/null; then
      echo "already installed"
      return 0
    else
      return 1
    fi
  }

  run check_precommit_installed
  [[ "$status" -eq 0 ]]
  [[ "$output" == "already installed" ]]
}

@test "pre-commit verification: does not report 'already installed' when command missing" {
  # Ensure pre-commit not in PATH
  export PATH="$TEST_BIN_DIR"

  check_precommit_installed() {
    if command -v pre-commit &>/dev/null; then
      echo "already installed"
      return 0
    else
      return 1
    fi
  }

  run check_precommit_installed
  [[ "$status" -eq 1 ]]
  [[ "$output" != "already installed" ]]
}

@test "pre-commit installation: exits with error when all install methods fail" {
  # This test verifies the NEW behavior where:
  # 1. pipx install/upgrade appears to succeed
  # 2. But verification (command -v pre-commit) still fails
  # 3. Script exits with error

  # Mock pipx that succeeds (returns 0) but doesn't actually install pre-commit
  /usr/bin/cat >"$TEST_BIN_DIR/pipx" <<'EOF'
#!/bin/bash
# Simulate successful pipx command that doesn't actually install
exit 0
EOF
  /bin/chmod +x "$TEST_BIN_DIR/pipx"

  # Create minimal PATH that excludes ALL system directories where pre-commit might exist
  # Only include our test bin directory
  export PATH="$TEST_BIN_DIR"

  # Simulate the install.sh logic exactly
  install_precommit_with_verification() {
    if ! command -v pre-commit &>/dev/null; then
      # Try install with pipx
      if pipx install pre-commit &>/dev/null; then
        # Verify installation succeeded
        if command -v pre-commit &>/dev/null; then
          echo "Success"
          return 0
        else
          echo "Error: Failed to install pre-commit"
          return 1
        fi
      elif pipx upgrade pre-commit &>/dev/null 2>&1; then
        # Verify installation succeeded
        if command -v pre-commit &>/dev/null; then
          echo "Success"
          return 0
        else
          echo "Error: Failed to install pre-commit"
          return 1
        fi
      else
        # Installation commands failed, verify not already installed
        if command -v pre-commit &>/dev/null; then
          echo "Already installed"
          return 0
        else
          echo "Error: Failed to install pre-commit"
          return 1
        fi
      fi
    fi
    return 0
  }

  run install_precommit_with_verification
  [[ "$status" -eq 1 ]]
  [[ "$output" == *"Error: Failed to install pre-commit"* ]]
}
