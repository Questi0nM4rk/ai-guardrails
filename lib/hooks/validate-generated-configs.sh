#!/usr/bin/env bash
# Thin shim — delegates to Python generate --check.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_PYTHON="$SCRIPT_DIR/../python"
[[ -d "$LIB_PYTHON/guardrails" ]] || LIB_PYTHON="$HOME/.ai-guardrails/lib/python"
export PYTHONPATH="$LIB_PYTHON:${PYTHONPATH:-}"

# Only run if registry exists
[[ -f ".guardrails-exceptions.toml" ]] || exit 0
exec python3 -m guardrails.generate --check
