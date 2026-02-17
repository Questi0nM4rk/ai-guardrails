# Plan: `ai-guardrails status` Subcommand

## Problem

No way to check if a project is correctly configured. Users run `ai-guardrails
init` and have no feedback about whether hooks are installed, configs are fresh,
or dependencies are available.

## Design

```bash
# Quick health check
ai-guardrails status
# Output:
#   Project: /path/to/project
#   Languages: python, shell
#   Pre-commit: installed (8 hooks)
#   Hooks: 6/8 deployed
#   Configs: 3 installed, 1 stale
#   Registry: valid (2 exceptions)
#   Dependencies: ruff ok, mypy ok, bandit MISSING
#   Overall: DEGRADED (1 missing dependency)

# JSON output for CI/scripts
ai-guardrails status --json

# Verbose with per-component details
ai-guardrails status --verbose
```

## Checks

| Check | How | Status Values |
|-------|-----|---------------|
| Git repo | `.git/` exists | ok / not-a-git-repo |
| Languages | Auto-detect via `assemble.detect_languages()` | list |
| Pre-commit installed | `shutil.which("pre-commit")` | ok / missing |
| Pre-commit hooks | `.git/hooks/pre-commit` exists | installed / not-installed |
| Hook scripts | Count `.ai-guardrails/hooks/*.sh` | N/M deployed |
| Config files | Compare installed vs expected for languages | installed / stale / missing |
| Registry | Parse `.guardrails-exceptions.toml` | valid / invalid / missing |
| Agent instructions | Check CLAUDE.md has guardrails marker | present / missing |
| Review bot configs | Check .coderabbit.yaml, .deepsource.toml, .gemini/ | present / missing |
| CI workflow | Check .github/workflows/check.yml | present / missing |

## Files

| File | Purpose |
|------|---------|
| `lib/python/guardrails/status.py` | Core status module |
| `tests/test_status.py` | Unit tests |
| `lib/python/guardrails/cli.py` | Add `status` subparser |

## Exit Codes

- 0: All checks pass
- 1: Degraded (some checks warn)
- 2: Error (critical checks fail)
