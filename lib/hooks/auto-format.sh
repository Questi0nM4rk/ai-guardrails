#!/bin/bash
# ============================================
# Auto-Format Hook
# Formats files after Write/Edit based on extension
# ============================================

FILE_PATH="$1"

[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

case "$FILE_PATH" in
  *.cs)
    dotnet format --include "$FILE_PATH" 2>/dev/null || true
    ;;
  *.rs)
    rustfmt "$FILE_PATH" 2>/dev/null || true
    ;;
  *.cpp | *.c | *.h | *.hpp | *.cc)
    clang-format -i "$FILE_PATH" 2>/dev/null || true
    ;;
  *.lua)
    stylua "$FILE_PATH" 2>/dev/null || true
    ;;
  *.sh | *.bash)
    shfmt -w "$FILE_PATH" 2>/dev/null || true
    ;;
  *.py)
    black -q "$FILE_PATH" 2>/dev/null || ruff format "$FILE_PATH" 2>/dev/null || true
    ;;
  *.ts | *.tsx | *.js | *.jsx | *.json | *.css | *.scss | *.md | *.yaml | *.yml)
    prettier --write "$FILE_PATH" 2>/dev/null || true
    ;;
  *.go)
    gofmt -w "$FILE_PATH" 2>/dev/null || true
    ;;
  *.rb)
    rubocop -a "$FILE_PATH" 2>/dev/null || true
    ;;
  *.swift)
    swift-format -i "$FILE_PATH" 2>/dev/null || true
    ;;
esac

exit 0
