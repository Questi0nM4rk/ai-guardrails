# AI Guardrails

Pedantic code enforcement for AI-maintained repositories.

## Philosophy

AI agents need hard stops. No warnings, no suggestions.
Everything is an error or it's ignored. Black/white only.

## Quick Start

```bash
# Install globally
python3 install.py

# In any project - auto-detects language
ai-guardrails init

# With options
ai-guardrails init --force       # Overwrite existing configs
ai-guardrails init --ci          # Also generate CI workflows
ai-guardrails init --type python # Specific language
```

## Unified CLI

All commands use `ai-guardrails <subcommand>`:

| Subcommand | Purpose |
|------------|---------|
| `ai-guardrails init` | Initialize project with configs, hooks, and CI |
| `ai-guardrails generate` | Regenerate tool configs from exception registry |
| `ai-guardrails comments` | List, reply to, and resolve PR review threads from all bots |

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
2. Suppression detection - Reject `# noqa`, `// @ts-ignore`, etc.
3. Security (gitleaks, detect-secrets, semgrep, bandit)
4. CVE scanning (pip-audit, npm-audit, cargo-audit)
5. Static analysis (check-only, already fixed above)
6. Type checking (strict mode)
7. Git hygiene (no main commits, no large files)

## Working with Review Comments

```bash
# List all unresolved review threads (compact output)
ai-guardrails comments --pr <NUMBER>

# Filter by bot
ai-guardrails comments --pr <NUMBER> --bot claude
ai-guardrails comments --pr <NUMBER> --bot coderabbit,gemini

# Reply to a thread
ai-guardrails comments --pr <NUMBER> --reply PRRT_abc123 "Fixed in commit xyz."

# Resolve a thread (with optional reply)
ai-guardrails comments --pr <NUMBER> --resolve PRRT_abc123 "Fixed."
ai-guardrails comments --pr <NUMBER> --resolve PRRT_abc123

# Batch resolve all threads from a bot
ai-guardrails comments --pr <NUMBER> --resolve-all --bot deepsource

# Full JSON output
ai-guardrails comments --pr <NUMBER> --json
```

**Supported bots:** CodeRabbit, Claude, Gemini, DeepSource

**Data flow:**

1. Fetches all review threads via GitHub GraphQL
2. Filters by bot name and resolution status
3. Reply via REST API, resolve via GraphQL mutation

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check lib/python/
uv run ruff format --check lib/python/

# Type check
uv run pyright

# Coverage
uv run pytest tests/ --cov=lib/python/guardrails --cov-report=term-missing
```

## Review Bots

All bots auto-review every push. No manual triggers needed.

| Bot | Focus | Trigger |
|-----|-------|---------|
| CodeRabbit | Static analysis, security, language conventions | Auto on push |
| Claude | Code duplication, clean code, modern patterns, architecture | Auto on PR |
| Gemini | Bugs, logic errors, security, performance | Auto on push |
| DeepSource | Anti-patterns, OWASP, code metrics | Auto on push |

### Rules for AI Agents

Every push triggers all 4 review bots. Unnecessary pushes waste review cycles
and create noise. Only push when you are confident the code is complete.

1. **Complete all changes before pushing** — Finish the entire task locally
   (all files, all fixes, all tests passing). Do not push work-in-progress
2. **Never auto-push** — Always ask the human before running `git push`.
   Explain what changed and confirm they want a review
3. **Batch into minimal commits** — Group related changes into logical
   commits. Push them all at once
4. **Address ALL review feedback before pushing again** — When bots request
   changes, fix every comment locally, then push once. Do not push after
   each individual fix
5. **Wait for all bots** — After pushing, wait for all reviews to complete
   (~5 min) before acting on feedback

## Key Constraints

- **Local auto-fix**: Fix everything possible, don't waste context on syntax
- **CI check-only**: Never modify code in CI/CD pipelines
- **Python 3.11+**: Modern type syntax (X | None, not Optional[X])
- `from __future__ import annotations`: Required in all Python files
- **85%+ test coverage**: 400+ pytest tests, pyright clean
- **Fail fast**: Clear error messages, no graceful degradation
