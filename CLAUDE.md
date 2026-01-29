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

**Local:** auto-fix everything → re-stage → checks → commit
**CI/CD:** checks only, never modify (SKIP=format-and-stage)

Hook execution order:

1. `format-and-stage` - Auto-fix ALL fixable issues (local only)
   - Python: `ruff format` + `ruff check --fix`
   - Shell: `shfmt`
   - Markdown: `markdownlint --fix`
   - TypeScript/JS: `biome check --write`
   - TOML: `taplo format`
2. Security (gitleaks, detect-secrets, semgrep, bandit)
3. CVE scanning (pip-audit, npm-audit, cargo-audit)
4. Static analysis (check-only, already fixed above)
5. Type checking (strict mode)
6. Git hygiene (no main commits, no large files)

## Working with CodeRabbit Reviews

When addressing CodeRabbit PR comments:

```bash
# Pull ALL unresolved comments as structured JSON tasks
bin/ai-review-tasks --pr <NUMBER> --pretty

# Filter by severity
bin/ai-review-tasks --pr <NUMBER> --severity major
```

**Important:**

- This is a BASH script, not Python - don't run with `python3`
- Use `--pr NUMBER` flag, not positional argument
- Tool filters `isResolved=false` automatically
- Output includes AI prompts with exact fix instructions
- Create TaskCreate items for each task returned

**Data flow:**

1. Fetches review threads via GitHub GraphQL (inline comments)
2. Fetches review bodies via `gh pr view` (🧹 Nitpicks, ⚠️ sections)
3. Filters: author=coderabbit AND isResolved=false
4. Pipes to `lib/python/coderabbit_parser.py` for parsing
5. Outputs structured JSON with actionable tasks

## Detailed Specifications

See `docs/specs/project_specs.xml` for:

- Complete component specifications
- Parsing requirements for coderabbit_parser.py
- Output JSON schema
- Known issues with severity levels
- Quality standards and review criteria

## Key Constraints

- **Local auto-fix**: Fix everything possible, don't waste context on syntax
- **CI check-only**: Never modify code in CI/CD pipelines
- **Python 3.10+**: Modern type syntax (X | None, not Optional[X])
- `from __future__ import annotations`: Required in all Python files (auto-added)
- **85%+ test coverage**: Type checking alone is NOT sufficient
- **Fail fast**: Clear error messages, no graceful degradation
