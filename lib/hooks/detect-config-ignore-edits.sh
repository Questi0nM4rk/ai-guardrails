#!/bin/bash
# ============================================
# detect-config-ignore-edits.sh
# Pre-commit hook: defense in depth
#
# Catches ignore-pattern additions in config
# files at commit time (manual edits outside
# Claude Code).
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Config file patterns to check
CONFIG_PATTERN='pyproject\.toml$|setup\.cfg$|\.eslintrc|tsconfig\.json$|\.flake8$'

# Ignore patterns to detect (same as protect-generated-configs.sh)
IGNORE_PATTERN='ignore[-_]?words|ignore\s*=|per-file-ignores|reportMissing.*false|eslint-disable|noqa|nolint|pragma.*disable|skip\s*=.*\['

# Get staged config files (Added, Copied, Modified, Renamed)
STAGED_FILES="$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)"

if [[ -z "$STAGED_FILES" ]]; then
  exit 0
fi

# Filter to only config files
CONFIG_FILES=""
while IFS= read -r file; do
  if echo "$file" | grep -qE "$CONFIG_PATTERN"; then
    CONFIG_FILES="$CONFIG_FILES $file"
  fi
done <<<"$STAGED_FILES"

CONFIG_FILES="${CONFIG_FILES# }" # trim leading space

if [[ -z "$CONFIG_FILES" ]]; then
  exit 0
fi

FOUND_VIOLATIONS=false

for file in $CONFIG_FILES; do
  # Skip if file doesn't exist (deleted)
  [[ -f "$file" ]] || continue

  # Skip auto-generated files (validated by validate-generated-configs)
  if head -5 "$file" 2>/dev/null | grep -q "AUTO-GENERATED"; then
    continue
  fi

  # Get added lines from the staged diff
  ADDED_LINES="$(git diff --cached -U0 "$file" 2>/dev/null | grep '^+' | grep -v '^+++' || true)"

  if [[ -z "$ADDED_LINES" ]]; then
    continue
  fi

  # Check added lines for ignore patterns
  DETECTED="$(echo "$ADDED_LINES" | grep -iE "$IGNORE_PATTERN" || true)"

  if [[ -n "$DETECTED" ]]; then
    FOUND_VIOLATIONS=true
    echo -e "${RED}ERROR: Ignore pattern detected in $file${NC}"
    echo -e "${YELLOW}Detected patterns:${NC}"
    echo "$DETECTED" | while IFS= read -r line; do
      echo -e "  ${YELLOW}${line}${NC}"
    done
    echo
  fi
done

if [[ "$FOUND_VIOLATIONS" == true ]]; then
  echo -e "${RED}========================================${NC}"
  echo -e "${RED}Direct ignore-pattern edits are not allowed${NC}"
  echo -e "${RED}========================================${NC}"
  echo
  echo "Lint exceptions must go in .guardrails-exceptions.toml,"
  echo "not directly in config files."
  echo
  echo "Steps:"
  echo "  1. Add the exception to .guardrails-exceptions.toml with a reason"
  echo "  2. Run: ai-guardrails-generate"
  echo "  3. Commit the generated configs"
  echo
  exit 1
fi

exit 0
