#!/usr/bin/env bats
# ============================================
# Tests for install.py CLI
# ============================================
# NOTE: Language installer tests have been migrated to Python unit tests
# in tests/test_installers.py. The bash installer scripts (lib/installers/*.sh)
# have been replaced by Python modules (lib/installers/*.py).
#
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
}

teardown() {
  # Restore PATH first to ensure system commands work
  export PATH="$ORIGINAL_PATH"
  export HOME="$ORIGINAL_HOME"
  # Clean up test directory
  rm -rf "$TEST_INSTALL_DIR"
}

# ============================================
# install.py CLI Tests
# ============================================
# NOTE: These tests verify CLI argument parsing. Full installer tests
# are in tests/test_installers.py using pytest with mocked pyinfra.

@test "install.py: accepts --python flag" {
  # Check if pyinfra is available, skip if not
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--python"* ]]
}

@test "install.py: accepts --node flag" {
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--node"* ]]
}

@test "install.py: accepts --all flag" {
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--all"* ]]
}

@test "install.py: accepts --shell flag" {
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--shell"* ]]
}

@test "install.py: accepts --rust flag" {
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--rust"* ]]
}

@test "install.py: accepts --go flag" {
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--go"* ]]
}

@test "install.py: accepts --cpp flag" {
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--cpp"* ]]
}

@test "install.py: accepts --lua flag" {
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--lua"* ]]
}

@test "install.py: accepts --force flag" {
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--force"* ]]
}

@test "install.py: accepts --uninstall flag" {
  if ! python3 -c "import pyinfra" 2>/dev/null; then
    skip "pyinfra not installed"
  fi
  run python3 "$BATS_TEST_DIRNAME/../../install.py" --help
  [[ "$output" == *"--uninstall"* ]]
}

@test "install.py: dry-run shows what would be installed" {
  skip "Integration test - requires pyinfra runtime"
}

@test "install.py: creates installation directory structure" {
  skip "Integration test - requires pyinfra runtime"
}
