#!/bin/bash
# ============================================
# AI Guardrails Pre-Push Hook
# Runs before any git push
# ============================================

set -e

echo "Running pre-push checks..."

# Security scan with semgrep (if available)
if command -v semgrep &>/dev/null; then
  echo "  Security: Running semgrep scan..."
  if ! semgrep --config auto --error --quiet . 2>/dev/null; then
    echo "  Security issues found! Fix before pushing."
    exit 1
  fi
  echo "  Security scan passed"
fi

# Full test suite based on project type
run_full_tests() {
  if ls *.csproj 1>/dev/null 2>&1 || ls *.sln 1>/dev/null 2>&1; then
    if command -v dotnet &>/dev/null; then
      echo "  .NET: Running full test suite..."
      dotnet test --verbosity quiet || return 1
      echo "  .NET tests passed"
    fi
  fi

  if [ -f "Cargo.toml" ] && command -v cargo &>/dev/null; then
    echo "  Rust: Running full test suite..."
    cargo test --quiet || return 1
    echo "  Rust tests passed"
  fi

  if [ -d "build" ] && command -v ctest &>/dev/null; then
    echo "  C/C++: Running full test suite..."
    ctest --test-dir build --output-on-failure || return 1
    echo "  C/C++ tests passed"
  fi

  if command -v busted &>/dev/null && [ -d "spec" ]; then
    echo "  Lua: Running full test suite..."
    busted || return 1
    echo "  Lua tests passed"
  fi

  if command -v pytest &>/dev/null && { [ -d "tests" ] || [ -d "test" ]; }; then
    echo "  Python: Running full test suite..."
    pytest || return 1
    echo "  Python tests passed"
  fi

  if [ -f "package.json" ] && grep -q '"test"' package.json 2>/dev/null; then
    echo "  Node: Running full test suite..."
    npm test || return 1
    echo "  Node tests passed"
  fi

  return 0
}

echo "  Running full test suite..."
run_full_tests || {
  echo "  Tests failed! Fix before pushing."
  exit 1
}

echo "Pre-push checks passed"
exit 0
