# Plan: Convert bin/ Scripts from Bash to Python/Lua

## Status: COMPLETE (PR #19 — feat/python-rewrite)

## Overview

Convert the three CLI scripts in `bin/` from Bash to Python or Lua for better testing and usability.

## Current State

| Script | Lines | Purpose |
|--------|-------|---------|
| `ai-guardrails-init` | 562 | Set up pedantic configs, pre-commit, CI workflows |
| `ai-hooks-init` | 181 | Initialize git hooks |
| `ai-review-tasks` | 151 | Extract CodeRabbit review tasks (already delegates to Python) |

## Rationale

- **Testability**: Python/Lua scripts can be unit tested; bash scripts are harder to test
- **Consistency**: Installer is already Python (pyinfra), configs are Python modules
- **Maintainability**: Type hints, IDE support, better error handling
- **Cross-platform**: Python handles OS differences better than bash

## Options

### Option A: Python with Click/Typer

- Use Click or Typer for CLI argument parsing
- Entry points in pyproject.toml
- Consistent with existing Python codebase

### Option B: Lua

- Lightweight, fast startup
- Good for simple CLI tools
- Would require Lua runtime dependency

### Option C: Hybrid

- Convert complex script (`ai-guardrails-init`) to Python
- Keep simple scripts (`ai-hooks-init`, `ai-review-tasks`) as bash

## Recommendation

**Option A (Python)** - Maintains consistency with pyinfra installer, enables full test coverage.

## Priority

Low - Current bash scripts work correctly. Convert when time permits or when adding new features.

## Notes

- `ai-review-tasks` already delegates complex logic to `lib/python/coderabbit_parser.py`
- Consider adding CLI entry points to pyproject.toml for pip-installable commands
