# AI Guardrails — Production Release Roadmap

## Status: ACTIVE (updated 2026-03-18)

Ordered by implementation dependency. No time estimates.

## Completed

- **Phase 0:** Hotfixes (PR #113) — nosemgrep detection, generic scanner, infra fixes
- **E2E fixture test system** (PR #117) — 8 lang fixtures, feats integration
- **BDD test package** (feats v1.0.1 published to npm)
- **Bugfixes #123-127** (PR #133) — generator language gates, detection ignore paths, CI install step, context-aware noConsole
- **Config merge strategy** (PR #117) — `--config-strategy merge|replace|skip`
- **Unified ignore_paths** (PR #117) — one config feeds check, biome, lefthook
- **Biome v2 runner update** (PR #117) — rdjson format changes for v2.3+
- **CI build step** — binary built before tests, Node 24 opt-in

---

## Phase 1: Test Migration to Gherkin

Migrate behavior tests from raw bun:test to feats/Gherkin. Keep pure unit
tests (runners, utils, models) as bun:test. Only migrate STABLE code — don't
write Gherkin for features we're about to rebuild (runners, check-step).

### 1.1 Migrate hook tests (stable — won't change)

Dangerous-cmd, protect-configs, protect-reads, suppress-comments, allow-comment,
format-stage → 6 .feature files, ~99 scenarios.

### 1.2 Migrate rule engine tests (stable)

Engine, integration, rules, rule-groups, ruleset-toggling → 2 .feature files, ~76 scenarios.

### 1.3 Migrate config/generator tests (stable)

Config loader, generators (biome, ruff, lefthook, claude-settings, agent-rules),
language detection → 3 .feature files, ~112 scenarios.

### 1.4 Migrate pipeline/command tests (stable-ish)

Check pipeline, install pipeline, CLI commands → 2 .feature files, ~20 scenarios.

### 1.5 Do NOT migrate yet (will change in Phase 2)

- Runner tests (12 files, ~135 tests) — will change with fingerprint integration
- Check-step tests — will change with baseline wiring
- Status-step tests — may change with new features

---

## Phase 2: Baseline Integration (Core Product Value)

The "hold-the-line" feature. After this, `check` only fails on NEW issues.

### 2.1 Wire baseline loading into checkStep

Load `baseline.json`, call `classifyFingerprint()`, filter to new issues only.

### 2.2 Content-stable fingerprints

Replace `computeFingerprint()` in all 12 runners with `fingerprintIssue()`
that reads actual source lines. Fingerprints survive tool version upgrades.

### 2.3 Portable fingerprints (relative paths)

Use `relative(projectDir, absoluteFile)` for fingerprinting so baselines
work across machines and CI.

### 2.4 Migrate runner + check-step tests to Gherkin

Now that runners and check-step are stable, migrate remaining tests.

---

## Phase 3: PostToolUse Lint Hooks

Per-edit lint feedback for AI agents. NOT replacing pre-commit hooks —
an additional early feedback layer.

### 3.1 post-lint hook implementation

New hook entry point: `ai-guardrails hook post-lint`. Reads PostToolUse
event, determines language from file extension, runs appropriate linter.
Exit 0 always (informational). Structured output for agent consumption.

### 3.2 Generator emits PostToolUse hooks

`claude-settings.ts` generates PostToolUse entries matching `Edit|Write`.
Each detected language gets its linter wired.

### 3.3 Modular per-language lint config

Each language's lint command is a data declaration in
`src/hooks/post-lint-rules/`. Adding a language = adding a file.

---

## Phase 4: TypeScript Strictness Profiles

### 4.1 tsconfig generator

Three profiles: standard (strict), strict (+noUncheckedIndexedAccess),
pedantic (+exactOptionalPropertyTypes, verbatimModuleSyntax).

### 4.2 Profile selection in config

```toml
[typescript]
profile = "pedantic"
```

### 4.3 Merge with existing tsconfig

Uses the config merge strategy (already built) to upgrade user's tsconfig
without losing their project-specific fields.

---

## Phase 5: Versioning and Release Infrastructure

### 5.1 Semantic versioning

Version bumps via `npm version patch|minor|major`. Git tags.
Current: v3.0.0 — next feature release should be v3.1.0.

### 5.2 Release workflow

GitHub Actions: tag push triggers build + GitHub Release with binary.

### 5.3 Cross-platform builds

Matrix build for Linux x64, macOS arm64, macOS x64.

### 5.4 Install script

`curl | sh` one-liner that downloads the right binary for the platform.
Must include SHA-256 checksum verification against the GitHub Release manifest.

### 5.5 Changelog generation

Conventional commits → auto-generated CHANGELOG.md per release.

---

## Phase 6: Example Projects

Full working example projects for each supported language showing
ai-guardrails in action. Not test fixtures (those exist) — real
project templates users can clone.

### 6.1 Per-language example repos or directories

```
examples/
  typescript-starter/    ← package.json, tsconfig, src/
  python-starter/        ← pyproject.toml, src/
  rust-starter/          ← Cargo.toml, src/
  go-starter/            ← go.mod, main.go
  multi-lang/            ← typescript + python monorepo
```

Each has: README, ai-guardrails already initialized, sample CI workflow,
documented violations that `check` catches.

### 6.2 "Getting Started" guide

Step-by-step: clone example → run init → see configs → introduce violation →
run check → see it caught.

---

## Phase 7: Stale Docs Cleanup

### 7.1 Mark hook-bypass-regex-limitations as RESOLVED

All 3 issues fixed by AST engine.

### 7.2 Mark fresh-install-bugs as RESOLVED

All 6 bugs from Python era eliminated by TS rewrite.

### 7.3 Update README

Separate shipped (v3) from planned (v4). Reflect current CLI, hook system,
config merge, ignore_paths.

### 7.4 Update roadmap itself

Remove completed items, add new discoveries.

---

## Phase 8: cc-review Updates

### 8.1 Pull review logging feature

cc-review has a `claude/add-review-logging-xcGnC` branch with conversation
logging to a memory branch. Evaluate and merge if stable.

### 8.2 Document cc-review setup for new repos

The feats repo setup exposed the process: need App secrets (REVIEWER_APP_ID,
REVIEWER_APP_PRIVATE_KEY, CLAUDE_CODE_OAUTH_TOKEN), workflows on main branch,
App installed with repo access. Document this as a setup guide.

### 8.3 Fix cc-review "finished reviewing" without formal review

cc-review sometimes says "finished reviewing" without submitting APPROVED.
Requires explicit follow-up request. Investigate and fix in cc-review repo.

---

## Phase 9: Shell Completion

Replace stub in `src/cli.ts` with real bash/zsh/fish completion generation.

---

## Phase 10: Hook System Improvements

### 10.1 eval/python-c patterns as engine rules

Add `code-injection` rule group.

### 10.2 Generator respects disabled_groups for deny globs

Filter `collectDenyGlobs()` by active groups.

### 10.3 Per-subcommand flag scoping

Extend FLAG_GROUPS to support `(cmd, sub)` scoping if needed.

---

## Phase 11: Interactive Init Wizard

### 11.1 Branch protection setup prompt

Detect GitHub/GitLab, prompt for protection level (none/standard/strict).

### 11.2 Pre-commit hook level selection

format-only / standard / pedantic.

### 11.3 TypeScript profile prompt

If TS detected, prompt for strictness profile.

### 11.4 Language confirmation

Auto-detect + confirm/modify.

### 11.5 CI setup prompt

GitHub Actions / GitLab CI / none.

### 11.6 Fix init --force overwriting config.toml

`--force` should regenerate configs but preserve user's config.toml settings
(ignore_paths, profile, disabled_groups). Currently overwrites everything.

---

## Phase 12: ai-guardrails-allow Integration

### 12.1 Wire allow comments into checkStep

### 12.2 allow command

### 12.3 query command

---

## Phase 13: .NET Runner

### 13.1 MSBuild JSON log parser

### 13.2 dotnet-format runner

---

## Phase 14: Advanced Features (v4+)

### 14.1 Governance hierarchy

### 14.2 Agent attribution + auto-strict

### 14.3 Team features

### 14.4 Baseline burn-down

---

## Known Bugs (track and fix as encountered)

- **init --force overwrites config.toml** — should preserve user settings
- **feats .d.ts files have unresolved @/ aliases** — skipLibCheck workaround,
  needs tsc-alias or relative imports in feats
- **cc-review "finished reviewing" without APPROVED** — intermittent,
  needs investigation in cc-review repo
- **Staleness detection disabled** — removed in PR #117 because merged files
  are indistinguishable from generated by hash alone. Needs provenance tracking.

---

## Current State (as of 2026-03-19, PR #133 merge)

| Component | Status |
|-----------|--------|
| CLI commands (8) | All working, completion is stub |
| Language plugins (9) | 8 with runners, .NET stub |
| Linter runners (12) | All functional, biome v2 updated |
| Config generators (10) | All functional + ignore_paths |
| Hook system | AST engine + flag aliases + rule groups + config toggling |
| Config merge | merge/replace/skip strategy, deep merge |
| Unified ignore_paths | Feeds check, biome, lefthook from one config |
| Tests | 752 passing (35 files, 5 snapshots) |
| E2E fixtures | 8 languages, bare + preconfigured, monorepo combo |
| BDD framework | @questi0nm4rk/feats v1.0.1 on npm |
| Baseline | Code exists, not wired |
| SARIF output | Implemented |
| CI | lint + test + semgrep + self-dogfood + cc-review |
| Release automation | None (v3.0.0 hardcoded) |
| Version | 3.0.0 |
