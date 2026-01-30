#!/bin/bash
# ============================================
# detect-suppression-comments.sh
# Detect and reject lint/type suppression comments
#
# Philosophy: "Everything is an error or it's ignored"
# Suppression comments create gray areas - they're not allowed.
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Patterns to detect (all matching is case-insensitive via grep -i)
# Format: "pattern|description|file_types"
PATTERNS=(
  # Python
  '# noqa|Python noqa suppression|py'
  '# type: ignore|Python type ignore|py'
  '# pylint: disable|Pylint disable|py'
  '# pragma: no cover|Coverage exclusion|py'

  # TypeScript/JavaScript
  '// @ts-ignore|TypeScript ignore|ts,tsx,js,jsx'
  '// @ts-expect-error|TypeScript expect-error|ts,tsx,js,jsx'
  '// @ts-nocheck|TypeScript nocheck|ts,tsx,js,jsx'
  '/\* eslint-disable|ESLint disable block|ts,tsx,js,jsx'
  '// eslint-disable|ESLint disable line|ts,tsx,js,jsx'

  # C#
  '#pragma warning disable|C# pragma disable|cs'
  '// ReSharper disable|ReSharper disable|cs'
  '\[SuppressMessage|SuppressMessage attribute|cs'

  # Rust
  '#\[allow\(|Rust allow attribute|rs'
  '#!\[allow\(|Rust crate-level allow|rs'

  # Go
  '//nolint|Go nolint directive|go'

  # Shell
  '# shellcheck disable|ShellCheck disable|sh,bash'

  # Lua
  '--luacheck: ignore|Luacheck ignore|lua'

  # C/C++
  '// NOLINT|Clang-Tidy NOLINT|c,cpp,h,hpp'
  '/\* NOLINT|Clang-Tidy NOLINT block|c,cpp,h,hpp'
  '#pragma clang diagnostic ignored|Clang diagnostic ignore|c,cpp,h,hpp'
  '#pragma GCC diagnostic ignored|GCC diagnostic ignore|c,cpp,h,hpp'
)

# Files to check (passed as arguments)
FILES=("$@")

if [[ ${#FILES[@]} -eq 0 ]]; then
  # No files passed, nothing to check
  exit 0
fi

FOUND_SUPPRESSIONS=false
SUPPRESSION_COUNT=0

for file in "${FILES[@]}"; do
  # Skip if file doesn't exist (might be deleted)
  [[ -f "$file" ]] || continue

  # Skip test files and fixtures (tests may need relaxed rules)
  # Covers: tests/, test/, __tests__/, spec/, *_test.*, test_*, *_spec.*, *.spec.*
  if [[ "$file" == *"/tests/"* ]] || [[ "$file" == *"/test/"* ]] \
    || [[ "$file" == *"/__tests__/"* ]] || [[ "$file" == *"/spec/"* ]] \
    || [[ "$file" == *"/test_"* ]] || [[ "$file" == *"_test."* ]] \
    || [[ "$file" == *"_spec."* ]] || [[ "$file" == *".spec."* ]]; then
    continue
  fi

  # Get file extension
  ext="${file##*.}"
  basename="${file##*/}"

  # Handle extensionless files and dotfiles by inferring type
  if [[ "$ext" == "$basename" ]] || [[ -z "$ext" ]] || [[ "$basename" == .* ]]; then
    # Map common dotfiles to their shell type
    case "$basename" in
      .bashrc | .bash_profile | .bash_aliases) ext="bash" ;;
      .zshrc | .zprofile | .zshenv) ext="bash" ;; # zsh uses same patterns as bash
      .profile) ext="sh" ;;
      *)
        # Try to infer from shebang
        if shebang=$(head -1 "$file" 2>/dev/null); then
          case "$shebang" in
            *"/bash"* | *"env bash"*) ext="bash" ;;
            *"/sh"* | *"env sh"*) ext="sh" ;;
            *"/zsh"* | *"env zsh"*) ext="bash" ;; # zsh uses same patterns
            *"/python"* | *"env python"*) ext="py" ;;
            *"/node"* | *"env node"*) ext="js" ;;
          esac
        fi
        ;;
    esac
  fi

  for pattern_spec in "${PATTERNS[@]}"; do
    IFS='|' read -r pattern desc file_types <<<"$pattern_spec"

    # Check if this pattern applies to this file type
    if [[ ",$file_types," != *",$ext,"* ]]; then
      continue
    fi

    # Search for the pattern (case-insensitive to catch NOQA, TYPE: IGNORE, etc.)
    if grep -qiE "$pattern" "$file" 2>/dev/null; then
      FOUND_SUPPRESSIONS=true
      ((SUPPRESSION_COUNT++)) || true

      # Show the offending lines (use -m 5 to avoid SIGPIPE with pipefail)
      echo -e "${RED}ERROR: $desc found in $file${NC}"
      grep -niE -m 5 "$pattern" "$file" | while read -r line; do
        echo -e "  ${YELLOW}$line${NC}"
      done
      echo
    fi
  done
done

if [[ "$FOUND_SUPPRESSIONS" == true ]]; then
  echo -e "${RED}========================================${NC}"
  echo -e "${RED}Found $SUPPRESSION_COUNT suppression comment(s)${NC}"
  echo -e "${RED}========================================${NC}"
  echo
  echo "AI Guardrails philosophy: 'Everything is an error or it's ignored.'"
  echo "Suppression comments create gray areas and are not allowed."
  echo
  echo "Options:"
  echo "  1. Fix the underlying issue that triggered the lint/type error"
  echo "  2. If the rule is wrong for this project, disable it in config"
  echo "  3. For legitimate exceptions, document in project EXCEPTIONS.md"
  echo
  exit 1
fi

exit 0
