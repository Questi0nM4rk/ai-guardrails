#!/usr/bin/env bash
# ============================================
# AI Guardrails Pre-Commit Hook
# Runs pre-commit framework checks before any git commit.
# ============================================
set -euo pipefail

if command -v pre-commit &>/dev/null; then
  exec pre-commit run --hook-stage pre-commit
else
  echo "Error: pre-commit not installed. Install it: uv tool install pre-commit" >&2
  exit 1
fi
