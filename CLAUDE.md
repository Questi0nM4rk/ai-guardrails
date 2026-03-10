# AI Guardrails — Agent Instructions

## Build & Test

```bash
# v1 code (active development)
uv run pytest tests/test_v1/ -v          # v1 tests (319 tests)
uv run ruff check src/ai_guardrails/     # lint v1
uv run ruff format --check src/          # format check

# Legacy code (still functional, being replaced)
uv run pytest tests/ -v                  # all tests (v1 + legacy)
uv run ruff check lib/python/            # lint legacy
uv run pyright                           # type check
```

## Architecture

Pipeline + Plugin with DI. Spec: `docs/features/SPEC-v1.md` (source of truth).
ADR-002 is superseded except for DONTs (section 2) and competitive landscape (section 7).

### v1 Layout (`src/ai_guardrails/`)

| Layer | Path | Purpose |
|-------|------|---------|
| CLI | `cli.py` | cyclopts app → Command dataclasses → dispatch |
| Pipelines | `pipelines/` | install, init, generate — orchestrate steps |
| Steps | `steps/` | 7 steps: detect_languages, copy_configs, scaffold_registry, load_registry, generate_configs, setup_ci, setup_agent_instructions |
| Generators | `generators/` | ruff, markdownlint, codespell, editorconfig, lefthook, claude_settings |
| Hooks | `hooks/` | dangerous_cmd, suppress_comments, protect_configs, format_stage, config_ignore |
| Infra | `infra/` | FileManager, CommandRunner, ConfigLoader, Console (all injected) |
| Models | `models/` | ExceptionRegistry, LanguageConfig, ProjectInfo |
| Constants | `constants.py` | All shared constants — single source of truth |

### Legacy Layout (`lib/python/guardrails/`)

Old code. Being replaced by v1. Don't add new features here.

## Key Constraints

- Python 3.11+, `from __future__ import annotations` in all files
- 85%+ test coverage, ruff clean
- Everything is an error or it's ignored. No warnings.
- See `@.claude/rules/` for detailed conventions

## DONTs

- NEVER `except Exception: pass` — catch specific exceptions
- NEVER add new `subprocess.run` call sites — use CommandRunner in v1
- NEVER duplicate constants — single source in `constants.py` or `languages.yaml`
- NEVER use test classes for new tests without shared state — prefer standalone functions
- NEVER push without asking — complete all changes locally first
- NEVER use `dict[str, Any]` across module boundaries — use dataclasses
- NEVER read/write files directly in steps — use FileManager
- NEVER use `print()` for output — use Console

## When adding features

- New pipeline step: `/new-step`
- New config generator: `/new-generator`
- New language support: `/new-language`

## Current State (2026-03-02)

- v1 MVP code complete: infra, models, generators, steps, pipelines, CLI, hooks
- 434 v1 tests + 597 legacy tests, all passing
- Package configured: `uv run python -c "from ai_guardrails.cli import app"` works
- Branch: `refactor/extract-lang-config`, PR #53 open
- Review bot: cc-review (Claude Code) — auto-reviews on PR open


## AI Guardrails - Code Standards

This project uses [ai-guardrails](https://github.com/Questi0nM4rk/ai-guardrails) for pedantic code enforcement.
Pre-commit hooks auto-fix formatting, then run security scans, linting, and type checks.
cc-review auto-reviews every PR on open. Interactive via `@cc-review` comments.

### Review Bot (cc-review)

cc-review auto-reviews on PR open. It posts REQUEST_CHANGES with inline comments
for bugs, security issues, and logic errors. Supports 4 modes: standard, strict,
bug-hunt, simplify (via labels or workflow_dispatch). Interactive via `@cc-review`.

**Fix every review comment that is not a false positive. Even nitpicks. Even style.**

- Fix ALL findings locally, then push once. One push per review round.
- Ask the human before pushing. Explain what changed.

**Do not:**

- **Never dismiss a review comment because it's "just a nitpick."**
  Nitpicks are how code quality compounds. A style fix takes 30 seconds. Ignoring
  it means the next reviewer wastes time on the same thing. Fix it and move on.

- **Never resolve a thread without fixing it or explaining why it's a false positive.**
  Resolving a thread means "this is handled." If it's not handled, it's lying to the
  reviewer. If you disagree with a finding, reply with a reason — don't silently resolve.

- **Never batch-resolve threads you haven't read.**
  Each thread exists because a reviewer flagged something. Read it, decide if it's real
  or false positive, then act. `--resolve-all` is for documented false positives you've
  already triaged (e.g. a bot that always flags pytest `self`), not for blindly closing.

- **Never push after each individual fix.**
  Every push triggers all bots. Fixing 5 comments in 5 pushes creates 5 full review
  cycles of noise. Fix everything locally, push once.

- **Never skip a false positive without documenting it.**
  If a bot repeatedly flags something that's wrong, that's useful information for tuning
  the bot's config. Log it so it can be fixed upstream. Resolve with a reference to
  where it's documented.

### Pre-commit Workflow

```
auto-fix → re-stage → checks → commit
```

1. `format-and-stage` auto-fixes formatting and re-stages (local only, skipped in CI)
2. Security scans (gitleaks, detect-secrets, semgrep, bandit)
3. Linting (check-only — already fixed above)
4. Type checking (strict mode)
5. Git hygiene (no commits to main, no large files)

### When Pre-commit Fails

Most formatting is auto-fixed. If it still fails, read the error — it's a real issue
(missing docstring, type error, security problem). Fix it, stage, commit again.
