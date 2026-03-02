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
- 319 v1 tests + 664 legacy tests, all passing
- Package configured: `uv run python -c "from ai_guardrails.cli import app"` works
- Branch: `refactor/extract-lang-config`, PR #53 open
- Review bot: `minimax/minimax-m2.5` via `.guardrails-review.toml`
- Sibling project: `guardrails-review` at `~/Projects/guardrails-review/`
