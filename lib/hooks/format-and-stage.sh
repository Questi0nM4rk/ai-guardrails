#!/bin/bash
# =============================================================================
# Format and Stage Hook
# =============================================================================
# Automatically formats staged files and re-stages them before checks run.
# This ensures formatters fix issues before linters complain about them.
#
# Workflow: format → stage → checks → commit
# CI/CD: Skipped (SKIP=format-and-stage pre-commit run --all-files)
# =============================================================================
set -euo pipefail

# Get list of staged files (Added, Copied, Modified)
STAGED=$(git diff --cached --name-only --diff-filter=ACM)
[[ -z "$STAGED" ]] && exit 0

# Format Python files
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  ruff format "$file" 2>/dev/null || true
  ruff check --fix "$file" 2>/dev/null || true
done < <(echo "$STAGED" | grep -E '\.py$' || true)

# Format Shell files
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  shfmt -w -i 2 -ci -bn "$file" 2>/dev/null || true
done < <(echo "$STAGED" | grep -E '\.(sh|bash)$' || true)

# Re-stage only the originally staged files (not all modified files)
echo "$STAGED" | while IFS= read -r file; do
  [[ -f "$file" ]] && git add "$file"
done

exit 0
