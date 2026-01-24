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
#
# Partial staging support:
#   - Stashes unstaged changes before formatting
#   - Restores with --index to preserve staged vs unstaged hunks
# =============================================================================
set -euo pipefail

# Get list of staged files (Added, Copied, Modified)
STAGED=$(git diff --cached --name-only --diff-filter=ACM)
[[ -z "$STAGED" ]] && exit 0

# Check if there are unstaged changes to stash
HAS_UNSTAGED=false
if ! git diff --quiet 2>/dev/null; then
  HAS_UNSTAGED=true
fi

# Stash unstaged changes to avoid formatting them
# -k = keep index (staged changes stay staged)
# -u = include untracked files
if [[ "$HAS_UNSTAGED" == true ]]; then
  git stash push -k -u -m "format-and-stage: temporary stash" >/dev/null 2>&1 || true
fi

# Cleanup function to restore stash on exit
# shellcheck disable=SC2329,SC2317  # Function is invoked via trap
cleanup() {
  if [[ "$HAS_UNSTAGED" == true ]]; then
    # Restore with --index to preserve staged vs unstaged distinction
    git stash pop --index >/dev/null 2>&1 || {
      # If --index fails (can happen with conflicts), try without
      git stash pop >/dev/null 2>&1 || true
    }
  fi
}
trap cleanup EXIT

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

# Re-stage formatting changes only (not the entire file)
# Since we stashed unstaged changes, git add here only adds formatting fixes
echo "$STAGED" | while IFS= read -r file; do
  [[ -f "$file" ]] && git add "$file"
done

# Stash will be restored by cleanup trap on exit
exit 0
