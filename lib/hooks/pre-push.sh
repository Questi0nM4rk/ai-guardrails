#!/bin/bash
# ============================================
# AI Guardrails Pre-Push Hook
# Runs before any git push
# ============================================
set -euo pipefail

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/hooks/common.sh
source "$SCRIPT_DIR/common.sh"

echo "Running pre-push checks..."

# Security scan with semgrep (if available)
if command -v semgrep &>/dev/null; then
  echo "  Security: Running semgrep scan..."
  if ! semgrep --config auto --error --quiet . 2>/dev/null; then
    echo "  Security issues found! Fix before pushing."
    exit 1
  fi
  echo "  Security scan passed"
fi

# Run full test suite (verbose mode)
echo "  Running full test suite..."
run_all_tests "" || {
  echo "  Tests failed! Fix before pushing."
  exit 1
}

echo "Pre-push checks passed"
exit 0
