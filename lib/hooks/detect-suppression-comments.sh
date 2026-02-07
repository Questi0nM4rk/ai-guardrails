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

# ============================================
# Allowlist support
# ============================================
# A `.suppression-allowlist` file in the repo root lists approved suppressions.
# Format: one entry per line, each is a grep -E pattern matched against
# the full line text (file:lineno:content). Blank lines and # comments ignored.
#
# Example .suppression-allowlist:
#   # MCP tool boundaries need catch-all
#   # noqa: BLE001
#   # MCP tools have many params by design
#   # noqa: PLR0913
#   # shellcheck disable=SC2317
#
ALLOWLIST_FILE=".suppression-allowlist"
ALLOWLIST_PATTERNS=()
if [[ -f "$ALLOWLIST_FILE" ]]; then
  while IFS= read -r line; do
    # Skip blank lines and comments
    [[ -z "$line" || "$line" == \#* ]] && continue
    ALLOWLIST_PATTERNS+=("$line")
  done <"$ALLOWLIST_FILE"
fi

# Check if a line is allowlisted
is_allowlisted() {
  local line_text="$1"
  for allowed in "${ALLOWLIST_PATTERNS[@]}"; do
    if grep -qiE "$allowed" <<<"$line_text" 2>/dev/null; then
      return 0
    fi
  done
  return 1
}

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
    # Filter out allowlisted lines, only report non-allowlisted matches
    has_violation=false
    violation_lines=()
    while IFS= read -r match_line; do
      if ! is_allowlisted "$match_line"; then
        has_violation=true
        violation_lines+=("$match_line")
      fi
    done < <(grep -niE -m 10 "$pattern" "$file" 2>/dev/null)

    if [[ "$has_violation" == true ]]; then
      FOUND_SUPPRESSIONS=true
      ((SUPPRESSION_COUNT++)) || true

      echo -e "${RED}ERROR: $desc found in $file${NC}"
      for vline in "${violation_lines[@]}"; do
        echo -e "  ${YELLOW}$vline${NC}"
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
  echo "  3. For legitimate exceptions, add pattern to .suppression-allowlist"
  echo "     (requires user approval and documented reason)"
  echo
  exit 1
fi

exit 0
