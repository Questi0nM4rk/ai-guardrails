#!/bin/bash
# ============================================
# validate-generated-configs
# Check that generated configs match the exception registry.
# Fails if configs are stale or missing.
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find the generate_configs.py script (prefer local repo over global install)
GENERATE_SCRIPT=""
if [[ -f "$SCRIPT_DIR/../python/generate_configs.py" ]]; then
  GENERATE_SCRIPT="$SCRIPT_DIR/../python/generate_configs.py"
elif [[ -f "$HOME/.ai-guardrails/lib/python/generate_configs.py" ]]; then
  GENERATE_SCRIPT="$HOME/.ai-guardrails/lib/python/generate_configs.py"
fi

if [[ -z "$GENERATE_SCRIPT" ]]; then
  echo "Warning: generate_configs.py not found, skipping freshness check" >&2
  exit 0
fi

# Only run if registry exists
if [[ ! -f ".guardrails-exceptions.toml" ]]; then
  exit 0
fi

exec python3 "$GENERATE_SCRIPT" --check
