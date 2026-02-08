#!/bin/bash
# ============================================
# protect-generated-configs.sh
# Claude Code PreToolUse hook for Write|Edit events
#
# Prompts user approval before:
# 1. Editing auto-generated config files
# 2. Editing .guardrails-exceptions.toml
# 3. Adding ignore patterns to config files
# ============================================

set -euo pipefail

# Bail out gracefully if jq is not available
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Not a guardrails project if no registry file exists
if [[ ! -f ".guardrails-exceptions.toml" ]]; then
  exit 0
fi

# Source shared constants
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=guardrails-patterns.sh disable=SC1091
source "$SCRIPT_DIR/guardrails-patterns.sh"

# Read JSON from stdin
INPUT="$(cat)"

# Extract file_path from tool_input
FILE_PATH="$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')"

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Normalize: extract basename for pattern matching
BASENAME="$(basename "$FILE_PATH")"

# --- Helper: emit PreToolUse ask decision ---
emit_ask() {
  local reason="$1"
  jq -n \
    --arg reason "$reason" \
    '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "ask",
        permissionDecisionReason: $reason
      }
    }'
  exit 0
}

# --- Check 1: Auto-generated config files ---
for cfg in $GENERATED_CONFIGS; do
  if [[ "$BASENAME" == "$cfg" ]]; then
    # File must exist AND contain AUTO-GENERATED in first 5 lines
    if [[ -f "$FILE_PATH" ]] && head -5 "$FILE_PATH" 2>/dev/null | grep -q "AUTO-GENERATED"; then
      emit_ask "This file is auto-generated from .guardrails-exceptions.toml by ai-guardrails-generate. Direct edits will be overwritten on next run. Edit .guardrails-exceptions.toml instead, then run ai-guardrails-generate. Explain why editing directly is the only solution."
    fi
    break
  fi
done

# --- Check 2: .guardrails-exceptions.toml itself ---
if [[ "$BASENAME" == ".guardrails-exceptions.toml" ]]; then
  emit_ask "This is the single source of truth for all lint exceptions in this project. Every change MUST have a documented reason. Explain why this exception is necessary and cannot be fixed in the code."
fi

# --- Check 3: Ignore patterns in config files ---
for cfg in $CONFIG_FILES; do
  if [[ "$BASENAME" == "$cfg" ]]; then
    # Get the new content from tool_input (Edit uses new_string, Write uses content)
    NEW_CONTENT="$(echo "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // empty')"

    if [[ -n "$NEW_CONTENT" ]] && echo "$NEW_CONTENT" | grep -iEq "$IGNORE_PATTERN"; then
      emit_ask "Ignore pattern detected in $BASENAME. Lint exceptions must go in .guardrails-exceptions.toml, not directly in config files. Run ai-guardrails-generate to apply changes. Explain why this is the only solution."
    fi
    break
  fi
done

# Everything else: allow silently
exit 0
