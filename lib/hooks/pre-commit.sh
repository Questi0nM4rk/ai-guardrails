#!/bin/bash
# ============================================
# AI Guardrails Pre-Commit Hook
# Runs before any git commit
# ============================================

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/hooks/common.sh
source "$SCRIPT_DIR/common.sh"

echo "Running pre-commit checks..."

# Run tests in quiet mode
run_all_tests "quiet" || {
  echo "Pre-commit checks failed!"
  exit 1
}

echo "Pre-commit checks passed"
exit 0
