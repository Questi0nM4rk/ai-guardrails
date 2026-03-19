# AI Guardrails — Production Release Roadmap

## Status: ACTIVE (updated 2026-03-19)

786 tests, 38 files. Baseline integration complete. All dogfooding bugs fixed.

## Completed

- **Phase 0:** Hotfixes & suppression system (PR #109-113)
- **Check system rewrite:** Flag aliases, rule groups, config toggling (PR #106-108)
- **E2E fixture system:** 8 lang fixtures, feats integration, config merge (PR #114-117)
- **BDD test migration:** ~290 behavior tests → Gherkin feature files (PR #119-122)
- **Bugfixes #123-127:** Generator language gates, detection ignore paths, CI install, noConsole (PR #128-133)
- **Bugfixes #134-135:** Stale config cleanup on --force, dynamic biome schema (PR #137-139)
- **Baseline integration (#136):** checkStep loads baseline, content-stable fingerprints, relative paths,
  snapshot consistency (PR #140-145)
- **BDD framework:** @questi0nm4rk/feats v1.0.1 on npm
- **Config merge:** --config-strategy merge|replace|skip
- **Unified ignore_paths:** One config feeds check, biome, lefthook

---

## Phase 2: Test Coverage Gaps

Fill gaps in command, step, and generator tests. Required for confidence before release.

### 2.1 Command tests

Add tests for `generate`, `init`, `snapshot`, `status`, `report`, `hook` commands.

**Files:** `tests/commands/{generate,init,snapshot,status,report,hook}.test.ts` (6 new)

Use FakeFileManager, FakeCommandRunner, FakeConsole to test command dispatch,
flag parsing, error handling without real I/O.

### 2.2 Step tests

Add tests for `load-config`, `run-linters`, `report-step`, `setup-agent-instructions`,
`setup-hooks`, `validate-configs`.

**Files:** `tests/steps/*.test.ts` (6 new — setup-ci and check-step already have tests)

### 2.3 Generator snapshot tests

Add snapshot tests for `codespell`, `editorconfig`, `markdownlint` generators.

**Files:** `tests/generators/{codespell,editorconfig,markdownlint}.test.ts` (3 new)

---

## Phase 3: Stale Docs Cleanup

### 3.1 Mark hook-bypass-regex-limitations as RESOLVED

All 3 issues fixed by AST engine. Update `docs/bugs/hook-bypass-regex-limitations.md`.

### 3.2 Mark fresh-install-bugs as RESOLVED

All 6 bugs from Python era eliminated by TS rewrite. Update `docs/bugs/fresh-install-bugs.md`.

### 3.3 Update README

Rewrite to reflect TS binary, current CLI commands, hook system. Separate shipped (v3) from planned.

### 3.4 Close stale issues

- #41: Publish to PyPI — obsolete (TS rewrite, no Python)
- #45: Review and close/update medium/low priority items

---

## Phase 4: Release Infrastructure

### 4.1 Version management — `npm version` + git tags

### 4.2 Release workflow — GitHub Actions on tag push, binary in release

### 4.3 Cross-platform builds — Linux x64, macOS arm64, macOS x64

### 4.4 Install script — curl | sh with SHA-256 checksum verification

### 4.5 Changelog generation — conventional commits → CHANGELOG.md

---

## Phase 5: Shell Completion

Replace stub in `src/cli.ts` with real bash/zsh/fish completion.

---

## Phase 6: Hook System Improvements

### 6.1 Code injection rules (eval, python -c)

### 6.2 Generator respects disabled_groups for deny globs

### 6.3 Per-language PostToolUse lint hooks

---

## Phase 7: .NET Runner

### 7.1 MSBuild JSON log parser

### 7.2 dotnet-format runner

---

## Phase 8: ai-guardrails-allow Integration

### 8.1 Wire allow comments into checkStep

### 8.2 allow command

### 8.3 query command

---

## Phase 9: Interactive Init Wizard

### 9.1 Branch protection setup prompt

### 9.2 Pre-commit hook level selection

### 9.3 TypeScript strictness profile prompt

### 9.4 Language confirmation

### 9.5 CI setup prompt

---

## Phase 10+: Advanced Features (v4+)

### 10.1 Governance hierarchy

### 10.2 Agent attribution + auto-strict

### 10.3 Team features

### 10.4 Baseline burn-down

### 10.5 Version pinning and drift detection (#42)

---

## Known Bugs

- **cc-review can't submit formal reviews** — file write permission bug (cc-review#1)
- **init --force overwrites config.toml** — should preserve user settings
- **feats .d.ts files have unresolved @/ aliases** — skipLibCheck workaround

---

## Current State (2026-03-19, PR #145 merge)

| Component | Status |
|-----------|--------|
| CLI commands (8) | All working, completion is stub |
| Language plugins (9) | 8 with runners, .NET stub |
| Linter runners (12) | All functional, content-stable fingerprints |
| Config generators (10) | All functional + ignore_paths + language gates |
| Hook system | AST engine + flag aliases + rule groups + config toggling |
| Baseline | Fully wired — check respects baseline, portable fingerprints |
| Config merge | merge/replace/skip + stale cleanup on --force |
| Tests | 786 passing (38 files, 5 snapshots) |
| E2E fixtures | 8 languages, bare + preconfigured, monorepo combo |
| BDD framework | @questi0nm4rk/feats v1.0.1 on npm |
| SARIF output | Implemented |
| CI | lint + test + semgrep + self-dogfood + cc-review |
| Release automation | None (v3.0.0 hardcoded) |
