# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

[Describe your C/C++ project here]

## Stack

- C++23 / C17
- CMake 3.20+
- [Add your libraries]

## Commands

```bash
# Configure
cmake -B build -DCMAKE_BUILD_TYPE=Release

# Build
cmake --build build --parallel

# Test
ctest --test-dir build --output-on-failure

# Test single
ctest --test-dir build -R test_name

# Clean
cmake --build build --target clean

# Lint
clang-tidy src/*.cpp -- -std=c++23

# Format
clang-format -i src/*.cpp src/*.h
```

## Architecture

[Describe your architecture]

Example:
```
src/
├── main.cpp         # Entry point
├── core/            # Core business logic
├── util/            # Utilities
└── external/        # Third-party wrappers

include/
└── project/         # Public headers

tests/
└── unit/            # Unit tests
```

## Conventions

- Use `std::expected` or custom `Result<T, E>` for errors
- RAII for resource management
- Smart pointers over raw pointers
- `const` correctness
- Use `[[nodiscard]]` where appropriate

## Build Types

```bash
# Debug (with sanitizers)
cmake -B build -DCMAKE_BUILD_TYPE=Debug -DENABLE_SANITIZERS=ON

# Release
cmake -B build -DCMAKE_BUILD_TYPE=Release

# Release with debug info
cmake -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
```

## Testing

Using [GoogleTest/Catch2/doctest]:

```bash
# All tests
ctest --test-dir build

# Verbose
ctest --test-dir build -V

# Specific test
ctest --test-dir build -R "TestSuite.TestName"
```

## Dependencies

Managed via [vcpkg/conan/FetchContent]:
- [List your dependencies]
