#!/bin/bash
# =============================================================================
# Format and Stage Hook
# =============================================================================
# Automatically fixes ALL auto-fixable issues in staged files and re-stages them.
# This ensures no context is wasted on syntax/formatting issues.
#
# Workflow: auto-fix everything → re-stage → checks → commit
# CI/CD: Skipped (SKIP=format-and-stage pre-commit run --all-files)
#
# Philosophy:
#   - Local: Auto-fix EVERYTHING possible, don't waste context on syntax
#   - CI/CD: Check only, never modify (SKIP=format-and-stage)
# =============================================================================
set -euo pipefail

# Get list of staged files (Added, Copied, Modified)
STAGED=$(git diff --cached --name-only --diff-filter=ACM)
[[ -z "$STAGED" ]] && exit 0

# Python: format + lint fixes
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  ruff format "$file" 2>/dev/null || true
  ruff check --fix "$file" 2>/dev/null || true
done < <(echo "$STAGED" | grep -E '\.py$' || true)

# Shell: format
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  shfmt -w -i 2 -ci -bn "$file" 2>/dev/null || true
done < <(echo "$STAGED" | grep -E '\.(sh|bash)$' || true)

# Markdown: fix
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  markdownlint-cli2 --fix "$file" 2>/dev/null || true
done < <(echo "$STAGED" | grep -E '\.md$' || true)

# TypeScript/JavaScript: format + lint fixes
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  biome check --write "$file" 2>/dev/null || true
done < <(echo "$STAGED" | grep -E '\.(ts|tsx|js|jsx|json)$' || true)

# TOML: format
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  taplo format "$file" 2>/dev/null || true
done < <(echo "$STAGED" | grep -E '\.toml$' || true)

# Re-stage all originally staged files (picks up fixes)
echo "$STAGED" | while IFS= read -r file; do
  [[ -f "$file" ]] && git add "$file"
done

exit 0
