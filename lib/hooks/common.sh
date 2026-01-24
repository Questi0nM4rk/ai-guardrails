#!/bin/bash
# ============================================
# AI Guardrails - Common Hook Functions
# Shared test detection and execution logic
# ============================================

# Detect if .NET project
is_dotnet_project() {
  ls ./*.csproj 1>/dev/null 2>&1 || ls ./*.sln 1>/dev/null 2>&1
}

# Detect if Rust project
is_rust_project() {
  [[ -f "Cargo.toml" ]]
}

# Detect if C/C++ project with build
is_cpp_project() {
  [[ -f "CMakeLists.txt" ]] || [[ -f "Makefile" ]]
}

has_cpp_build() {
  [[ -d "build" ]] && command -v ctest &>/dev/null
}

# Detect if Lua project
is_lua_project() {
  ls ./*.rockspec 1>/dev/null 2>&1 || [[ -d "spec" ]]
}

# Detect if Python project
is_python_project() {
  [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -d "tests" ]] || [[ -d "test" ]]
}

# Detect if Node project
is_node_project() {
  [[ -f "package.json" ]]
}

has_node_tests() {
  [[ -f "package.json" ]] && grep -q '"test"' package.json 2>/dev/null
}

# Run .NET tests
# Args: $1 = "quiet" for quiet mode (pre-commit), empty for verbose (pre-push)
run_dotnet_tests() {
  local mode="$1"
  if ! command -v dotnet &>/dev/null; then
    return 0
  fi
  echo "  .NET: Running tests..."
  if [[ "$mode" == "quiet" ]]; then
    dotnet test --no-build --verbosity quiet 2>/dev/null || return 1
  else
    dotnet test --verbosity quiet || return 1
  fi
  echo "  .NET tests passed"
}

# Run Rust tests
run_rust_tests() {
  local mode="$1"
  if ! command -v cargo &>/dev/null; then
    return 0
  fi
  echo "  Rust: Running tests..."
  cargo test --quiet 2>/dev/null || return 1
  echo "  Rust tests passed"
}

# Run C/C++ tests
run_cpp_tests() {
  local mode="$1"
  if ! command -v ctest &>/dev/null; then
    return 0
  fi
  echo "  C/C++: Running tests..."
  if [[ "$mode" == "quiet" ]]; then
    ctest --test-dir build --output-on-failure --quiet 2>/dev/null || return 1
  else
    ctest --test-dir build --output-on-failure || return 1
  fi
  echo "  C/C++ tests passed"
}

# Run Lua tests
run_lua_tests() {
  local mode="$1"
  if ! command -v busted &>/dev/null; then
    return 0
  fi
  echo "  Lua: Running tests..."
  if [[ "$mode" == "quiet" ]]; then
    busted --quiet 2>/dev/null || return 1
  else
    busted || return 1
  fi
  echo "  Lua tests passed"
}

# Run Python tests
run_python_tests() {
  local mode="$1"
  if ! command -v pytest &>/dev/null; then
    return 0
  fi
  if ! { [[ -d "tests" ]] || [[ -d "test" ]]; }; then
    return 0
  fi
  echo "  Python: Running tests..."
  if [[ "$mode" == "quiet" ]]; then
    pytest --quiet 2>/dev/null || return 1
  else
    pytest || return 1
  fi
  echo "  Python tests passed"
}

# Run Node tests
run_node_tests() {
  local mode="$1"
  if ! command -v npm &>/dev/null; then
    return 0
  fi
  if ! has_node_tests; then
    return 0
  fi
  echo "  Node: Running tests..."
  if [[ "$mode" == "quiet" ]]; then
    npm test --silent 2>/dev/null || return 1
  else
    npm test || return 1
  fi
  echo "  Node tests passed"
}

# Run all detected tests
# Args: $1 = "quiet" for pre-commit, empty for pre-push
run_all_tests() {
  local mode="$1"
  local failed=0

  if is_dotnet_project; then
    run_dotnet_tests "$mode" || failed=1
  fi

  if is_rust_project; then
    run_rust_tests "$mode" || failed=1
  fi

  if has_cpp_build; then
    run_cpp_tests "$mode" || failed=1
  fi

  if is_lua_project; then
    run_lua_tests "$mode" || failed=1
  fi

  if is_python_project; then
    run_python_tests "$mode" || failed=1
  fi

  if is_node_project; then
    run_node_tests "$mode" || failed=1
  fi

  return $failed
}
