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
ai-guardrails comments --pr <NUMBER> --bot coderabbit

# Reply to a thread
ai-guardrails comments --pr <NUMBER> --reply PRRT_abc123 "Fixed in commit xyz."

# Resolve a thread (requires category prefix in message)
ai-guardrails comments --pr <NUMBER> --resolve PRRT_abc123 "Fixed in abc1234"
ai-guardrails comments --pr <NUMBER> --resolve PRRT_abc123 "False positive: not applicable to tests"
ai-guardrails comments --pr <NUMBER> --resolve PRRT_abc123 "Won't fix: intentional design"

# Batch resolve all threads from a bot
ai-guardrails comments --pr <NUMBER> --resolve-all --bot coderabbit

# Full JSON output
ai-guardrails comments --pr <NUMBER> --json
```

**Supported bots:** CodeRabbit, Claude, PR-Agent

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

| Bot | Focus | Trigger |
|-----|-------|---------|
| PR-Agent | Semantic code review, inline suggestions | **Auto** on PR open; manual `/review`, `/improve` |
| CodeRabbit | Static analysis, security, language conventions | **Manual only** (`@coderabbitai review`) |
| Claude | Code quality, architecture, modern patterns | **Manual** (`@claude` in PR comment) |

### PR-Agent Setup

PR-Agent (Qodo Merge OSS) uses OpenRouter for LLM access. Setup:

1. Add `OPENROUTER_KEY` to your GitHub repo/org secrets
2. PR-Agent auto-reviews on PR open (`opened`, `reopened`, `ready_for_review`)
3. Manual commands (comment on PR): `/review`, `/improve`, `/describe`, `/ask "question"`

PR-Agent is **LLM-only** -- it does not run static analysis. Pre-commit hooks handle linting.

Config: `.pr_agent.toml` | Workflow: `.github/workflows/pr-agent.yml`

### CodeRabbit Review Workflow

CodeRabbit is rate-limited (3 reviews/hour on free tier). Auto-review is
disabled to avoid wasting reviews on WIP pushes.

1. Push changes -- CI runs automatically
2. When ready for review, trigger CodeRabbit: comment `@coderabbitai review` on the PR
3. For a full re-review: `@coderabbitai full review`

### Rules for AI Agents

Review bots are triggered on PR open (PR-Agent) or manually (CodeRabbit, Claude).
Unnecessary pushes waste CI cycles and create noise.

1. **Complete all changes before pushing** -- Finish the entire task locally
   (all files, all fixes, all tests passing). Do not push work-in-progress
2. **Never auto-push** -- Always ask the human before running `git push`.
   Explain what changed and confirm they want a review
3. **Batch into minimal commits** -- Group related changes into logical
   commits. Push them all at once
4. **Address ALL review feedback before pushing again** -- When bots request
   changes, fix every comment locally, then push once. Do not push after
   each individual fix
5. **Trigger CodeRabbit when ready** -- Comment `@coderabbitai review` as
   the final gate before merge

### Review Thread Resolution Protocol

Every review comment must be categorized and resolved properly:

| Category | Action | Comment Format |
|----------|--------|----------------|
| Actionable | Fix the code | `Fixed in <commit-hash>` |
| False positive | Explain why it's wrong | `False positive: <reason>` |
| Won't fix | Justify the decision | `Won't fix: <reason>` |
| Nitpick/style | Fix it anyway | `Fixed in <commit-hash>` |

**Never:**

- Resolve with just "Acknowledged" or "Noted"
- Batch-resolve without reading each comment
- Dismiss actionable feedback as "out of scope"

**Rule:** If a review bot flags it and it's not a false positive, fix it.

The `ai-guardrails comments --resolve` command enforces this: messages
must start with a valid category prefix (`Fixed in`, `False positive:`,
or `Won't fix:`). Messages without a proper category are rejected.

## Key Constraints

- **Local auto-fix**: Fix everything possible, don't waste context on syntax
- **CI check-only**: Never modify code in CI/CD pipelines
- **Python 3.11+**: Modern type syntax (X | None, not Optional[X])
- `from __future__ import annotations`: Required in all Python files
- **85%+ test coverage**: 400+ pytest tests, pyright clean
- **Fail fast**: Clear error messages, no graceful degradation
