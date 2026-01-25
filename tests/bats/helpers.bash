#!/bin/bash
# =============================================================================
# Bats Test Helpers
# =============================================================================
# Shared utilities for bats tests
# =============================================================================
# shellcheck disable=SC2154  # $output, $status, $BATS_TEST_FILENAME are bats builtins

# Get the repository root directory
REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/../.." && pwd)"
export REPO_ROOT

# Assembly script path
ASSEMBLE_SCRIPT="$REPO_ROOT/lib/python/assemble_precommit.py"
export ASSEMBLE_SCRIPT

# CLI script path
INIT_SCRIPT="$REPO_ROOT/bin/ai-guardrails-init"
export INIT_SCRIPT

# Create a temporary test directory
setup_test_dir() {
  TEST_DIR="$(mktemp -d)"
  export TEST_DIR
  cd "$TEST_DIR" || exit 1
}

# Clean up the temporary test directory
teardown_test_dir() {
  if [[ -n "${TEST_DIR:-}" && -d "$TEST_DIR" ]]; then
    rm -rf "$TEST_DIR"
  fi
}

# Create a file in the test directory
create_file() {
  local path="$1"
  local content="${2:-}"

  mkdir -p "$(dirname "$TEST_DIR/$path")"

  if [[ -n "$content" ]]; then
    echo "$content" >"$TEST_DIR/$path"
  else
    touch "$TEST_DIR/$path"
  fi
}

# Run the assembly script with test directory
run_assemble() {
  python3 "$ASSEMBLE_SCRIPT" --project-dir "$TEST_DIR" "$@"
}

# Run the init script in test directory
run_init() {
  cd "$TEST_DIR" || exit 1
  bash "$INIT_SCRIPT" "$@"
}

# Check if a string contains a substring
assert_contains() {
  local haystack="$1"
  local needle="$2"

  if [[ "$haystack" != *"$needle"* ]]; then
    echo "Expected to contain: $needle"
    echo "Actual: $haystack"
    return 1
  fi
}

# Check if a string does not contain a substring
assert_not_contains() {
  local haystack="$1"
  local needle="$2"

  if [[ "$haystack" == *"$needle"* ]]; then
    echo "Expected NOT to contain: $needle"
    echo "Actual: $haystack"
    return 1
  fi
}

# Check if a file exists
assert_file_exists() {
  local path="$1"

  if [[ ! -f "$path" ]]; then
    echo "Expected file to exist: $path"
    return 1
  fi
}

# Check if a file does not exist
assert_file_not_exists() {
  local path="$1"

  if [[ -f "$path" ]]; then
    echo "Expected file NOT to exist: $path"
    return 1
  fi
}

# Check if output matches a regex
assert_output_matches() {
  local pattern="$1"

  if [[ ! "$output" =~ $pattern ]]; then
    echo "Expected output to match: $pattern"
    echo "Actual output: $output"
    return 1
  fi
}
