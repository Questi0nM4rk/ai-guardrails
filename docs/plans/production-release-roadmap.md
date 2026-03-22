# AI Guardrails — Production Release Roadmap

## Status: ACTIVE (updated 2026-03-21)

896 tests, 51 files. All infrastructure complete. Spec suite written.

## Completed

- **Phase 0:** Hotfixes & suppression system (PR #109-113)
- **Check system rewrite:** Flag aliases, rule groups, config toggling (PR #106-108)
- **E2E fixture system:** 8 lang fixtures, feats integration, config merge (PR #114-117)
- **BDD test migration:** ~290 behavior tests → Gherkin feature files (PR #119-122)
- **Bugfixes #123-127:** Generator language gates, detection ignore paths, CI install,
  noConsole (PR #128-133)
- **Bugfixes #134-135:** Stale config cleanup on --force, dynamic biome schema (PR #137-139)
- **Baseline integration (#136):** checkStep loads baseline, content-stable fingerprints,
  relative paths, snapshot consistency (PR #140-145)
- **Test coverage:** 13 new test files, 112 tests for steps + generators (PR #148)
- **Docs cleanup:** README rewritten, bug docs marked RESOLVED, issues closed (PR #149)
- **Codebase audit (#150-157):** 34 `as` casts removed, stdin abstracted, hooks
  regenerated, TODOs cleaned (PR #163)
- **Release infrastructure:** Dynamic version, GitHub Actions release workflow with
  pinned SHAs, cross-platform builds (linux/macOS x64/arm64), install script with
  SHA-256 verification (PR #166, #169, #170)
- **Spec suite v3.1:** 10 SPEC files + index written from actual code

---

## v3.1 Release Scope (decided 2026-03-21)

Target: team rollout, then public. Ship when ready.

### Phase 5: Interactive Init Wizard

Modular init with y/n prompts per feature. Fast, opinionated defaults.
Per-file conflict detection: "biome.jsonc exists. Merge? [Y/n]"

- InitModule interface (13 modules)
- Wizard with readline prompts (no TUI framework)
- Dependency-aware execution (topological sort)
- `--yes` for backward compat
- Per `--no-X` flag per module

### Phase 6: Profiles with Real Teeth

Profiles (strict/standard/minimal) currently don't change rule selection.
Make them actually filter linter rules.

- strict = all rules enabled
- standard = recommended rules only
- minimal = critical rules only
- Each generator reads profile and adjusts rule config

### Phase 7: ai-guardrails-allow Integration

Parse `ai-guardrails-allow` comments in source files during check.
Allow = permanent conscious decision. Baseline = temporary debt.
Snapshot excludes allowed issues.

- Wire allow comment parsing into checkStep
- `allow` command: add to config.toml programmatically
- `query` command: show where rules are allowed/suppressed

### Phase 8: Shell Completion

Wire Commander.js built-in completion for bash/zsh/fish.

### Phase 9: Basic .NET Runner

`dotnet build` with warning parsing. Not full analyzer support.

### Phase 10: npm Publish

Publish to npm so `npx ai-guardrails` works alongside binary install.

---

## v3.2 Release Scope

### Baseline burn-down reporting

Enhanced `status` showing fixed/remaining/new counts.
Track progress toward zero baseline.

### Suppression expiry

`ai-guardrails-allow: rule/X "reason" expires:2026-06-01`
Check fails after expiry date.

### Per-rule exception budgets

Config: `max_exceptions = 3` per rule. Check fails if exceeded.

### Hook audit trail

JSONL logging of hook invocations. `hook-report` command.

### Custom dangerous patterns in config

Project-specific patterns in config.toml.

---

## v4+ (Future)

- Interactive triage CLI
- Monorepo / workspace support
- Cross-tool issue deduplication
- Code injection rule group (eval, python -c)
- PostToolUse lint hooks
- Governance hierarchy (org → team → project)
- Agent attribution (detect AI commits)
- Baseline burn-down dashboard
- Version pinning and drift detection (#42)
- Linter version capture in baseline

---

## Known Bugs

- **cc-review can't submit formal reviews** — file write permission (cc-review#1)
- **init --force overwrites config.toml** — should preserve user settings
- **feats .d.ts unresolved @/ aliases** — skipLibCheck workaround

---

## Current State (2026-03-21)

| Component | Status |
|-----------|--------|
| CLI commands (8) | All working, completion is stub |
| Language plugins (9) | 8 with runners, .NET stub |
| Linter runners (12) | All functional, content-stable fingerprints |
| Config generators (8) | Language-gated + ignore_paths + dynamic schema |
| Hook system | AST engine + flag aliases + rule groups + config toggling |
| Baseline | Fully wired — hold-the-line with portable fingerprints |
| Config merge | merge/replace/skip + stale cleanup on --force |
| Profiles | Defined but no rule filtering (Phase 6 will fix) |
| Allow comments | Hook detects, check ignores (Phase 7 will wire) |
| Tests | 896 passing (51 files, 17 snapshots) |
| CI | lint + test + semgrep + self-dogfood + cc-review |
| Release | Tag-push workflow, 4 platform binaries, SHA-256 |
| Install | curl script + GitHub Releases (npm publish in Phase 10) |
| Specs | v3.1 suite: 10 SPEC files in docs/specs/v3.1/ |
| Type safety | Zero `as` casts, strict mode, Zod at boundaries |
