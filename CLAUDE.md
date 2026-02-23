# AI Guardrails — Agent Instructions

## Build & Test

- `uv run pytest tests/ -v` — run all tests
- `uv run pytest tests/test_X.py -v` — run single file
- `uv run ruff check lib/python/` — lint
- `uv run ruff format --check lib/python/` — format check
- `uv run pyright` — type check

## Architecture

Pipeline + Plugin. See @docs/ADR-002-greenfield-architecture.md
Source: lib/python/guardrails/ | Tests: tests/

Each subcommand (init, generate, comments, status) is an entry point.
Helper functions are in lib/python/guardrails/ (flat module layout).
Target architecture: Pipeline + Plugin with DI (see ADR-002).

## Key Constraints

- Python 3.11+, `from __future__ import annotations` in all files
- 85%+ test coverage, pyright clean
- Everything is an error or it's ignored. No warnings.
- See @.claude/rules/ for detailed conventions

## DONTs

- NEVER `except Exception: pass` — catch specific exceptions
- NEVER add new subprocess.run call sites — minimize for future CommandRunner migration
- NEVER duplicate constants — single source in constants.py or languages.yaml
- NEVER use test classes for new tests without shared state — prefer standalone functions
- NEVER push without asking — complete all changes locally first
- NEVER use dict[str, Any] across module boundaries — use dataclasses

## When adding features

- New pipeline step: `/new-step`
- New config generator: `/new-generator`
- New language support: `/new-language`
