#!/bin/bash
# ============================================
# AI Guardrails Pre-Push Hook
# Runs security scan and full test suite before push.
# ============================================
set -euo pipefail

# Security scan with semgrep (if available)
if command -v semgrep &>/dev/null; then
  echo "  Security: Running semgrep scan..."
  if ! semgrep --config auto --error --quiet . 2>/dev/null; then
    echo "  Security issues found! Fix before pushing."
    exit 1
  fi
  echo "  Security scan passed"
fi

# Run pre-commit framework (full suite)
if command -v pre-commit &>/dev/null; then
  echo "  Running pre-commit checks..."
  pre-commit run --all-files --hook-stage pre-push || {
    echo "  Pre-push checks failed!"
    exit 1
  }
fi

echo "Pre-push checks passed"
