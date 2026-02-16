# Enterprise Readiness Assessment

**Date:** 2026-02-16
**Version:** 0.2.0
**Overall Score:** 70% production-ready

## Executive Summary

AI Guardrails is feature-complete for single-language Python/TS/Rust projects
with excellent code quality (429 tests, 85%+ coverage, pedantic configs). But it
has critical gaps in distribution, observability, and enterprise workflows that
block real-world team adoption.

## What Works Well

- 7 language configs (Python, TS/JS, Rust, C/C++, C#, Go, Lua, Shell)
- 40+ pre-commit hooks with auto-fix-then-check workflow
- Universal PR comment tool (`ai-guardrails comments`) for 4 review bots
- Exception registry (`.guardrails-exceptions.toml`) with config generation
- Claude Code PreToolUse hooks (protect-generated-configs, dangerous-command-check)
- Modular pre-commit assembly from language templates
- 429 tests across 24 test files

## Critical Gaps

### P0: Distribution

**Problem:** No PyPI package. Source-only installation via `python3 install.py`.

**Impact:** Teams can't `pip install ai-guardrails` or `uv tool install ai-guardrails`.
Blocks adoption outside developer workstations.

**Fix:**

- `pyproject.toml` already has entry point `ai-guardrails = "guardrails.cli:main"`
  (added in PR #35), but wheel config needs `packages = ["lib/python/guardrails"]`
  with sources mapping (also fixed in PR #35)
- Build + test wheel locally: `uv build && uv pip install dist/*.whl`
- Publish to PyPI: `uv publish`
- Add GitHub Actions release workflow

### P0: Status & Diagnostics

**Problem:** No way to check if a project is correctly configured. When things
break, no diagnostic output.

**Impact:** Users can't tell if hooks are installed, configs are fresh, or
dependencies are missing. Support burden is high.

**Fix:** New subcommands:

```bash
ai-guardrails status          # Quick health check
ai-guardrails status --verbose # Detailed component status
ai-guardrails diagnose        # Run all checks, report issues
```

### P1: Init Validation

**Problem:** After `ai-guardrails init`, no verification that everything worked.
Hooks might not be installed, configs might be stale, dependencies might be
missing.

**Impact:** Silent failures. User thinks they're protected but hooks don't run.

**Fix:** Add `--verify` flag to `init` or automatic post-init validation.

### P1: Dangerous Command Checker Gaps

**Problem:** Only 14 blocked patterns, all string-matching. Easily bypassed:

```bash
# Blocked:
git push --force

# NOT blocked (variations):
git push -f
command git push --force
env git push --force
```

**Fix:** Parse git commands properly, not just substring match.

### P2: Missing Language Support

| Language | Config | Template | Installer | Gap |
|----------|--------|----------|-----------|-----|
| Go | None | Yes | Yes | No config file template |
| Shell | None | Yes | Yes | No config file template |
| Java | None | None | None | Full stack missing |
| Kotlin | None | None | None | Full stack missing |

### P2: Exception Registry Limitations

**Current:** Per-file-glob exceptions only.

**Missing:**

- Time-limited exceptions (`expires = "2026-06-01"`)
- Approval workflow (who approved, when)
- Usage tracking (is this exception still needed?)
- Per-function/per-class scoping

### P3: Team/Workspace Features

**Problem:** Each project is an island. No shared policies.

**Missing:**

- Global exception registry (`~/.ai-guardrails/global-exceptions.toml`)
- Team config inheritance
- Remote registry server support
- Centralized policy dashboard

### P3: Review Bot Analytics

**Problem:** 4 bots review every push. No way to measure their value or track
false positive rates.

**Missing:**

- Bot effectiveness metrics (findings vs false positives)
- Cost tracking for paid bots
- Auto-suppress recurring false positives
- Findings-to-registry integration

## Recommended Roadmap

### Phase 1: Foundation (This Sprint)

1. **`ai-guardrails status` command** — Quick health check showing:
   - Installed hooks, detected languages, config freshness
   - Missing dependencies, stale configs
   - Pre-commit hook status
2. **Improve dangerous-command-check** — Parse git flags properly
3. **PyPI distribution** — Build wheel, test install, publish

### Phase 2: Reliability (Next Sprint)

1. **`ai-guardrails diagnose`** — Run all checks, report issues with fixes
2. **Init verification** — Post-init validation
3. **init.py coverage** — Remove from omit list, add integration tests

### Phase 3: Enterprise (Future)

1. **Java/Kotlin support** — checkstyle, ktlint, spotless
2. **Global exception registry** — Shared policies across projects
3. **Docker image** — For containerized CI/CD
4. **Release workflow** — Automated PyPI publishing on tags
