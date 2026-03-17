# Phase 1: Fixture Files

## Task

Create static fixture projects for all 8 supported languages.
Each language has bare/ (no existing config) and preconfigured/ (has existing config) variants.

## Files to create

```
tests/e2e/fixtures/
  typescript/bare/          → package.json, src/main.ts (violations)
  typescript/preconfigured/ → same + tsconfig.json with custom settings
  python/bare/              → pyproject.toml, src/main.py (violations)
  python/preconfigured/     → same + ruff.toml with custom rules
  rust/bare/                → Cargo.toml, src/lib.rs (violations)
  rust/preconfigured/       → same + clippy.toml
  go/bare/                  → go.mod, main.go (violations)
  go/preconfigured/         → same + .golangci.yml
  shell/bare/               → script.sh (violations)
  shell/preconfigured/      → same + .shellcheckrc
  cpp/bare/                 → CMakeLists.txt, src/main.cpp (violations)
  cpp/preconfigured/        → same + .clang-tidy
  lua/bare/                 → main.lua (violations)
  lua/preconfigured/        → same + selene.toml
  universal/bare/           → README.md (markdownlint violations), notes.txt (typos)
```

## Acceptance criteria

- Every bare/ fixture has the language detection marker (triggers the language plugin)
- Every bare/ fixture has at least 1 intentional lint violation per runner
- Every preconfigured/ fixture has all of bare/ plus an existing config with custom settings
- No fixture is over 10 lines of code (minimal)
- `ls tests/e2e/fixtures/*/bare/` shows all 8 languages
