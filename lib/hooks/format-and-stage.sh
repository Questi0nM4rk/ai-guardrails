#!/usr/bin/env bash
# Thin shim — delegates to Python module.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Resolve Python lib: installed (.ai-guardrails/hooks/../lib/python) or dev (lib/hooks/../python)
LIB_PYTHON="$SCRIPT_DIR/../lib/python"
[[ -d "$LIB_PYTHON/guardrails" ]] || LIB_PYTHON="$SCRIPT_DIR/../python"
[[ -d "$LIB_PYTHON/guardrails" ]] || LIB_PYTHON="$HOME/.ai-guardrails/lib/python"
export PYTHONPATH="$LIB_PYTHON:${PYTHONPATH:-}"
exec python3 -m guardrails.hooks.format_stage
