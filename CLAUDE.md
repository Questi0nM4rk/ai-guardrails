# AI Guardrails

Pedantic code enforcement for AI-maintained repositories.

## Philosophy

AI agents need hard stops. No warnings, no suggestions.
Everything is an error or it's ignored. Black/white only.

## Quick Start

```bash
# Install globally
./install.sh

# In any project - auto-detects language
ai-guardrails-init

# Install git hooks
ai-hooks-init
```

## Components

| Component | Purpose |
|-----------|---------|
| `ai-guardrails-init` | Copy pedantic configs (auto-detects language) |
| `ai-hooks-init` | Set up git hooks for pre-commit enforcement |
| `ai-review-tasks` | Extract actionable tasks from CodeRabbit PR reviews |

## Supported Languages

- **Python**: ruff.toml (ALL rules, strict typing, docstrings required)
- **TypeScript/JS**: biome.json (ALL rules, no any, no console.log)
- **C#/.NET**: .globalconfig + Directory.Build.props (warnings as errors)
- **Rust**: rustfmt.toml + clippy pedantic
- **C/C++**: .clang-format + clang-tidy
- **Lua**: stylua.toml + luacheck
- **Shell**: shellcheck + shfmt

## Pre-commit Workflow

**Local (default):** format -> stage -> checks -> commit

**CI/CD:** checks only (SKIP=format-and-stage)

Hook execution order:

1. Security (gitleaks, detect-secrets, semgrep, bandit)
2. CVE scanning (pip-audit, npm-audit, cargo-audit)
3. Commit message (conventional commits required)
4. Type checking (mypy --strict, tsc --strict)
5. Static analysis (ruff, biome, clippy, clang-tidy)
6. Formatting (check-only, no auto-fix)
7. Git hygiene (no main commits, no large files)

## Detailed Specifications

See `.claude/specs/project_specs.xml` for:

- Complete component specifications
- Parsing requirements for coderabbit_parser.py
- Output JSON schema
- Known issues with severity levels
- Quality standards and review criteria

## Key Constraints

- **No auto-fix**: AI must understand errors, not bypass them
- **Python 3.10+**: Modern type syntax (X | None, not Optional[X])
- `from __future__ import annotations`: Required in all Python files
- **90%+ test coverage**: Type checking alone is NOT sufficient
- **Fail fast**: Clear error messages, no graceful degradation
