#!/bin/bash
# ============================================
# AI Guardrails Pre-Commit Hook
# Runs pre-commit framework checks before any git commit.
# ============================================
set -euo pipefail

if command -v pre-commit &>/dev/null; then
  exec pre-commit run --hook-stage pre-commit
else
  echo "Warning: pre-commit not installed, skipping checks" >&2
fi
