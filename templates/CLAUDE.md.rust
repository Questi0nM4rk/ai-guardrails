# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

[Describe your Rust project here]

## Stack

- Rust (stable/nightly)
- [Add your frameworks: Tokio, Axum, Diesel, etc.]

## Commands

```bash
# Build
cargo build

# Build release
cargo build --release

# Test
cargo test

# Test single
cargo test test_name

# Run
cargo run

# Lint
cargo clippy -- -D warnings

# Format
cargo fmt

# Check
cargo check

# Audit dependencies
cargo audit
```

## Architecture

[Describe your architecture]

Example:

```text
src/
├── lib.rs           # Library root
├── main.rs          # Binary entry point
├── domain/          # Core business logic
├── infrastructure/  # External concerns
└── api/             # HTTP handlers
```

## Conventions

- Use `Result<T, E>` for fallible operations
- Prefer `thiserror` for custom errors
- Use `#[derive]` macros where appropriate
- Document public APIs with `///` comments
- Use `clippy` warnings as errors

## Error Handling

```rust
// Use thiserror for custom errors
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("Not found: {0}")]
    NotFound(String),
    #[error("Validation failed: {0}")]
    Validation(String),
}
```

## Testing

```bash
# All tests
cargo test

# With output
cargo test -- --nocapture

# Specific test
cargo test test_name

# Integration tests
cargo test --test integration
```

## Dependencies

Key crates:

- [List your main dependencies]
