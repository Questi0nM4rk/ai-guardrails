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
| `ai-guardrails review` | Extract actionable tasks from CodeRabbit PR reviews |

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

## Working with CodeRabbit Reviews

```bash
# Pull ALL unresolved comments as structured JSON tasks
ai-guardrails review --pr <NUMBER> --pretty

# Filter by severity
ai-guardrails review --pr <NUMBER> --severity major
```

**Data flow:**

1. Fetches review threads via GitHub GraphQL (inline comments)
2. Fetches review bodies via `gh pr view` (nitpicks, issue sections)
3. Filters: author=coderabbit AND isResolved=false
4. Parses with `guardrails.coderabbit` module
5. Outputs structured JSON with actionable tasks

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
| Gemini | Bugs, logic errors, performance | Auto on push |
| DeepSource | Anti-patterns, OWASP | Auto on push |

### Rules for AI Agents

1. **Never auto-push** — Ask human before `git push`
2. **Batch fixes locally** — All changes in one commit, push once
3. **Wait for all bots** — Don't address feedback until all reviews complete (~5 min)

## Key Constraints

- **Local auto-fix**: Fix everything possible, don't waste context on syntax
- **CI check-only**: Never modify code in CI/CD pipelines
- **Python 3.11+**: Modern type syntax (X | None, not Optional[X])
- `from __future__ import annotations`: Required in all Python files
- **85%+ test coverage**: 400+ pytest tests, pyright clean
- **Fail fast**: Clear error messages, no graceful degradation
