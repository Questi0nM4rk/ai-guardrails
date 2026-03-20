# AI Guardrails — Production Release Roadmap

## Status: ACTIVE (updated 2026-03-20)

896 tests, 51 files. Baseline integration complete. Release workflow live.
All audit issues resolved. Zero `as` casts. Zero open bugs.

## Completed

- **Phase 0:** Hotfixes & suppression system (PR #109-113)
- **Check system rewrite:** Flag aliases, rule groups, config toggling (PR #106-108)
- **E2E fixture system:** 8 lang fixtures, feats integration, config merge (PR #114-117)
- **BDD test migration:** ~290 behavior tests → Gherkin feature files (PR #119-122)
- **Bugfixes #123-127:** Generator language gates, detection ignore paths, CI install,
  noConsole (PR #128-133)
- **Bugfixes #134-135:** Stale config cleanup on --force, dynamic biome schema (PR #137-139)
- **Phase 1 — Baseline integration (#136):** checkStep loads baseline, content-stable
  fingerprints, relative paths, snapshot consistency (PR #140-145)
- **Phase 2 — Test coverage:** 13 new test files, 112 tests for steps + generators (PR #148)
- **Phase 3 — Docs cleanup:** README rewritten, bug docs marked RESOLVED, stale issues
  closed (PR #149)
- **Phase 4.1-4.2 — Release infrastructure:** Dynamic version from package.json, GitHub
  Actions release workflow with pinned SHAs + SHA-256 checksums (PR #166)
- **Codebase audit (#150-157):** 34 `as` casts removed, process.stdin abstracted, stale
  hooks regenerated, TODOs cleaned (PR #163)
- **BDD framework:** @questi0nm4rk/feats v1.0.1 on npm
- **Config merge:** --config-strategy merge|replace|skip
- **Unified ignore_paths:** One config feeds check, biome, lefthook

---

## Phase 4 (remaining): Release Polish

### 4.3 Cross-platform builds

Matrix build for Linux x64, macOS arm64, macOS x64. Bun supports cross-compilation
via `--target`. Each platform binary uploaded to the same GitHub Release.

### 4.4 Install script

`curl -fsSL https://raw.githubusercontent.com/.../install.sh | sh` — detects
platform, downloads correct binary, verifies SHA-256 checksum.

---

## Phase 5: Shell Completion

Replace stub in `src/cli.ts` with real bash/zsh/fish completion generation.
Commander.js has built-in completion support — wire it.

---

## Phase 6: Baseline Diff & Trend Reporting

### 6.1 Baseline diff command

`ai-guardrails diff` — compare current issues against baseline and show:
- New issues introduced since snapshot
- Issues fixed (in baseline but no longer present)
- Unchanged baseline issues

Human-readable table + JSON output. More informative than `check` which
only says pass/fail.

### 6.2 Suppression expiry

Extend `ai-guardrails-allow` comments with optional expiry:
`ai-guardrails-allow: rule/X "reason" expires:2026-06-01`

Pre-commit hook warns 7 days before expiry. Check fails after expiry.
Forces teams to revisit exceptions instead of letting them rot.

### 6.3 Per-rule exception budgets

Config option per rule: `max_exceptions = 3`. Check fails if more than N
`ai-guardrails-allow` comments exist for that rule. Gradual debt reduction.

---

## Phase 7: Hook Audit Trail

### 7.1 Hook invocation logging

Log every hook invocation to `.ai-guardrails/hook-audit.jsonl`:
command, decision (allow/block/ask), timestamp, rule matched.

### 7.2 Hook audit report

`ai-guardrails hook-report` — summarize hook activity: most blocked patterns,
most common commands, agents that trigger the most blocks.

### 7.3 Custom dangerous patterns in config

Extend config.toml to allow project-specific dangerous patterns:
```toml
[[hooks.dangerous_patterns]]
pattern = "sudo.*rm"
reason = "never use sudo with destructive ops"
```

---

## Phase 8: Hook System Improvements

### 8.1 Code injection rules (eval, python -c)

Add `code-injection` rule group to the check engine.

### 8.2 Generator respects disabled_groups for deny globs

Filter `collectDenyGlobs()` by active groups.

### 8.3 Per-language PostToolUse lint hooks

New hook entry point: `ai-guardrails hook post-lint`. Reads PostToolUse event,
runs the appropriate linter on the edited file. Immediate feedback to agent.

---

## Phase 9: ai-guardrails-allow Integration

### 9.1 Wire allow comments into checkStep

Parse `ai-guardrails-allow` comments in source files. Filter matching issues
from check results. Distinguish from baseline (allow = intentional, baseline = legacy).

### 9.2 allow command

`ai-guardrails allow <rule> <glob> "<reason>"` — add to config.toml programmatically.

### 9.3 query command

`ai-guardrails query <rule>` — show all files where this rule is allowed/suppressed.

---

## Phase 10: Interactive Init Wizard

### 10.1 Language confirmation with auto-detection preview
### 10.2 Profile selection (strict/standard/minimal) with diff preview
### 10.3 Pre-commit hook level selection (format-only/standard/pedantic)
### 10.4 CI provider detection (GitHub Actions/GitLab CI/none)
### 10.5 Fix init --force overwriting config.toml — preserve user settings

---

## Phase 11: Cross-Tool Issue Deduplication

When multiple linters report the same issue (e.g., both ruff and pyright flag
an unused import), deduplicate in reports and baseline. Uses file+line+category
matching. Prevents baseline pollution and noisy reports.

---

## Phase 12: Interactive Triage CLI

`ai-guardrails triage` — interactive TUI that walks through new issues.
Per-issue decisions: fix, allow, baseline, skip. Outputs a curated baseline
instead of wholesale snapshot. For teams onboarding with existing debt.

---

## Phase 13: Monorepo / Workspace Support

### 13.1 Workspace-level baseline

Single baseline spanning a monorepo. Each package inherits from root but
can override per-rule.

### 13.2 Workspace-level config

Root `.ai-guardrails/config.toml` inherited by packages. Package-level
overrides for profile, ignore_paths, allow rules.

---

## Phase 14: .NET Runner

### 14.1 MSBuild JSON log parser
### 14.2 dotnet-format runner

---

## Phase 15+: Advanced Features (v4+)

### 15.1 Governance hierarchy — org → team → project config inheritance
### 15.2 Agent attribution — detect AI-generated commits, auto-apply strict profile
### 15.3 Baseline burn-down dashboard — track issue reduction over time
### 15.4 Version pinning and drift detection (#42)
### 15.5 Linter version capture in baseline — warn on version drift between snapshot and check
### 15.6 Issue context caching — store ±3 source lines per baseline entry for historical context

---

## Known Bugs

- **cc-review can't submit formal reviews** — file write permission bug (cc-review#1)
- **init --force overwrites config.toml** — should preserve user settings (tracked in Phase 10.5)
- **feats .d.ts files have unresolved @/ aliases** — skipLibCheck workaround in consumers

---

## Current State (2026-03-20, PR #166 merge)

| Component | Status |
|-----------|--------|
| CLI commands (8) | All working, completion is stub |
| Language plugins (9) | 8 with runners, .NET stub |
| Linter runners (12) | All functional, content-stable fingerprints |
| Config generators (10) | Language-gated + ignore_paths + dynamic schema |
| Hook system | AST engine + flag aliases + rule groups + config toggling |
| Baseline | Fully wired — hold-the-line with portable fingerprints |
| Config merge | merge/replace/skip + stale cleanup on --force |
| Tests | 896 passing (51 files, 17 snapshots) |
| E2E fixtures | 8 languages, bare + preconfigured, monorepo combo |
| BDD framework | @questi0nm4rk/feats v1.0.1 on npm |
| SARIF output | Implemented |
| CI | lint + test + semgrep + self-dogfood + cc-review |
| Release | Tag-push workflow, binary + SHA-256, dynamic version |
| Type safety | Zero `as` casts, strict mode, Zod at boundaries |
| DI | Full — no direct process/infra access in domain code |
