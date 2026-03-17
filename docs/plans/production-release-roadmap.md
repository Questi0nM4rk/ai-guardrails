# AI Guardrails — Production Release Roadmap

## Status: ACTIVE

Ordered by implementation dependency — each phase builds on the previous.
No time estimates or story points. Just features, descriptions, and how to verify.

---

## Phase 0: Hotfixes and Suppression System (Immediate)

Bugs and gaps that undermine the tool's own integrity. Fix before feature work.

### 0.1 Add nosemgrep to SUPPRESSION_PATTERNS

**What:** `nosemgrep` comments are not detected by the suppress-comments hook.
Semgrep suppression flies completely under the radar — our own codebase has 4
instances that bypass the `ai-guardrails-allow` system.

**Files:** `src/hooks/suppress-comments.ts`

**How:** Add `/nosemgrep/` to the `typescript` patterns array in `SUPPRESSION_PATTERNS`.

**Test:** Create a file with `// nosemgrep: some-rule`, run suppress-comments hook,
verify it's flagged.

### 0.2 Replace nosemgrep comments with ai-guardrails-allow

**What:** Replace 4 `nosemgrep` comments in `src/check/ruleset.ts` with proper
`ai-guardrails-allow` syntax.

**Files:** `src/check/ruleset.ts`

**How:** Change `// nosemgrep: detect-non-literal-regexp — fully escaped` to
`// ai-guardrails-allow: semgrep/detect-non-literal-regexp "input fully escaped via escapeRegExp; no ReDoS risk"`

**Test:** `bun test` + semgrep still suppresses the finding (verify semgrep
also respects the ai-guardrails-allow comment, or keep nosemgrep alongside).

**Note:** May need both comments — `ai-guardrails-allow` for our system,
`nosemgrep` for semgrep itself. The hook already skips lines with
`ai-guardrails-allow`, so the nosemgrep on the same line is tolerated.

### 0.3 Generic suppression keyword scanner

**What:** A catch-all regex scan that flags comment lines containing suppression-like
keywords that don't have an `ai-guardrails-allow` directive. Acts as a safety net
so new tool suppressions can't slip through undetected.

**Files:** `src/hooks/suppress-comments.ts`

**How:** Add a second pass after the explicit pattern check. Two-step detection:

1. First check if the line IS a comment (starts with `//`, `#`, `--`, `/*`, or
   the keyword appears after a comment marker mid-line like `code // nosemgrep`).
   Do NOT flag method/function names like `suppressWarning()` or `disableCache()`.

2. Then check for generic suppression keywords in the comment portion only:

   ```
   /\b(nolint|nocheck|nosemgrep|no-verify|suppress|pragma\s+ignore|NOLINT)\b/
   ```

If a comment matches AND is not already flagged by explicit patterns AND doesn't
have `ai-guardrails-allow`, emit a warning (not a hard block):
"Possible suppression comment detected — verify or add ai-guardrails-allow."

**Key:** Only scan comment text, not code. A line like `const disableCache = true;`
must NOT be flagged. A line like `// disable-next-line` MUST be flagged.

**Test:**

- `// nosemgrep: rule` on its own → flagged
- `code(); // NOLINT` → flagged (comment portion)
- `const disableFeature = false;` → NOT flagged (code, not comment)
- `suppressWarning(err);` → NOT flagged (method name, not comment)
- `# nolint:SA1000` → flagged (comment in Python/shell)
- `// ai-guardrails-allow: semgrep/rule "reason" // nosemgrep` → NOT flagged (has allow)

**Dogfood:** Run on this repo — should catch any future suppression comments
from new tools added to CI.

### 0.4 Direct infra access in domain code

**What:** Several domain files use `process.stdout`, `process.stderr`, or
`console.error` directly instead of the injected `Console` from `PipelineContext`.
This violates CLAUDE.md: "never import infra directly in domain code."

**Files and violations:**

- `src/steps/report-step.ts:23` — `process.stdout.write(sarifJson)` (should use Console)
- `src/steps/report-step.ts:29` — `console.error(text)` (should use Console)
- `src/check/ruleset.ts:76` — `process.stderr.write(config error)` (should use Console or drop)
- `src/steps/install-prerequisites.ts:67,74` — direct `process.stdin`/`process.stdout` for readline
- `src/pipelines/init.ts:19,120` — direct `process.stdin`/`process.stdout` for readline

**How:** For report-step and ruleset: accept `Console` parameter or use PipelineContext.
For readline in install/init: inject a `readline` factory or accept stdin/stdout as params.

**Test:** Grep for `process\.std` and `console\.` in `src/steps/` and `src/pipelines/`.
Zero hits after fix.

### 0.5 Clean up Python-era artifacts from disk

**What:** 26 `__pycache__` directories, old `.test/*.py` files, `src/ai_guardrails/`
Python source, `.ai-guardrails/lib/python/` runtime — all still on disk from the
Python era. Not tracked in git but cluttering the workspace.

**How:** `find . -name __pycache__ -exec rm -rf {} +`, `rm -rf src/ai_guardrails/`,
`rm -rf .ai-guardrails/`, `rm -rf .test/`, `rm -rf .venv/`.

**Test:** `find . -name "*.pyc" -o -name "__pycache__"` returns nothing.

### 0.6 Evaluate shell-quote dependency

**What:** `shell-quote` is still imported in `src/steps/install-prerequisites.ts:2`
to parse install hint commands. This was the old parser that the AST engine replaced
for dangerous-cmd. Can we use `@questi0nm4rk/shell-ast` here instead, or is
shell-quote appropriate for this simpler use case?

**Files:** `src/steps/install-prerequisites.ts`

**How:** Evaluate if `shell-ast.parse()` is overkill for splitting install commands
like `npm install -D typescript`. If shell-quote is the right tool here (simple
tokenization, no AST needed), document why. If not, replace and `bun remove shell-quote`.

---

## Phase 0.7: TypeScript Strictness Profiles

ai-guardrails generates biome, ruff, lefthook configs but does NOT generate or
enforce tsconfig strictness. Our own tsconfig is hand-written, not dogfooded.

### 0.5.1 TypeScript strictness profile generator

**What:** New generator that creates or merges tsconfig compiler options based
on a strictness profile.

**Files:** `src/generators/tsconfig.ts` (new), `src/config/schema.ts` (add profile field)

**How:** Three profiles:

- `standard` — `strict: true` (covers 80% of safety)
- `strict` — adds `noUncheckedIndexedAccess`, `noImplicitOverride`
- `pedantic` — adds `exactOptionalPropertyTypes`, `verbatimModuleSyntax`,
  `noFallthroughCasesInSwitch`

Generator reads existing `tsconfig.json`, merges profile settings into
`compilerOptions` without overwriting project-specific fields (target, module,
paths, include/exclude).

**Test:** Fixture tsconfig with `strict: false` + run generator with "pedantic"
profile, verify all flags are set. Verify project-specific fields preserved.

**Dogfood:** This repo uses pedantic profile — verify generated output matches
our hand-written tsconfig.

### 0.5.2 Profile selection in config

**What:** `.ai-guardrails/config.toml` gets a `[typescript]` section:

```toml
[typescript]
profile = "pedantic"  # standard | strict | pedantic
```

**Files:** `src/config/schema.ts`, `src/generators/tsconfig.ts`

**Test:** Change profile, re-run generate, verify tsconfig changes.

---

## Phase 1: Baseline Integration (Core Product Value)

The "hold-the-line" feature is the core differentiator. Without it, `check` is just
"run linters and fail on everything." The code exists but isn't wired.

### 1.1 Wire baseline loading into checkStep

**What:** `src/steps/check-step.ts` loads `baseline.json`, calls `classifyFingerprint()`
per issue, and only fails on NEW issues (not existing ones).

**Files:** `src/steps/check-step.ts`, `src/pipelines/check.ts`

**How:** Load baseline via `fileManager.readText(BASELINE_PATH)`, parse as
`BaselineEntry[]`, build fingerprint map via `loadBaseline()`, filter issues
through `classifyFingerprint()`. Report existing issues as informational,
fail only on new ones.

**Test:** `bun test` + manual: run `snapshot` on a project with issues, add a new
issue, run `check` — only the new issue should fail. Existing issues should show
as "baseline" in output.

**Dogfood:** Run `ai-guardrails snapshot` on this repo, introduce a lint violation,
verify `ai-guardrails check` catches only the new one.

### 1.2 Content-stable fingerprints

**What:** Replace `computeFingerprint()` calls in all 12 runners with
`fingerprintIssue()` which reads actual source lines for stable fingerprints.

**Files:** All `src/runners/*.ts` (12 files), `src/utils/fingerprint.ts`

**How:** Each runner's `run()` groups issues by file, reads the source file once
via `fileManager.readText()`, splits to lines, calls `fingerprintIssue(issue, lines)`
instead of `computeFingerprint()` with error message text.

**Test:** Verify fingerprints survive tool version upgrades (mock same issue with
different error message — fingerprint should be identical).

**Dogfood:** Upgrade ruff/biome minor version, verify baseline doesn't break.

### 1.3 Portable fingerprints (relative paths)

**What:** Fingerprints use project-relative paths instead of absolute paths so
baselines work across machines and CI.

**Files:** All `src/runners/*.ts`, `src/models/lint-issue.ts`

**How:** `relative(projectDir, absoluteFile)` for fingerprint computation.
Keep `LintIssue.file` absolute for display.

**Test:** Compute fingerprint at `/home/dev/project/src/main.ts` and
`/home/runner/work/project/src/main.ts` — should be identical.

**Dogfood:** Run `snapshot` locally, run `check` in CI — baseline should match.

---

## Phase 2: Test Coverage

Fill gaps in command, step, and generator tests. Required for confidence
before any release.

### 2.1 Command tests

**What:** Add tests for `generate`, `init`, `snapshot`, `status`, `report`, `hook` commands.

**Files:** `tests/commands/{generate,init,snapshot,status,report,hook}.test.ts` (6 new)

**How:** Use `FakeFileManager`, `FakeCommandRunner`, `FakeConsole` to test
command dispatch, flag parsing, error handling without real I/O.

**Test:** `bun test tests/commands/`

**Dogfood:** Coverage report shows commands/ at 85%+.

### 2.2 Step tests

**What:** Add tests for `load-config`, `run-linters`, `report-step`,
`setup-agent-instructions`, `setup-ci`, `setup-hooks`, `snapshot-step`,
`validate-configs`.

**Files:** `tests/steps/*.test.ts` (8 new)

**How:** Use fakes. Test step return values (`StepResult`), error handling,
config propagation.

**Test:** `bun test tests/steps/`

### 2.3 Generator tests

**What:** Add snapshot tests for `codespell`, `editorconfig`, `markdownlint` generators.

**Files:** `tests/generators/{codespell,editorconfig,markdownlint}.test.ts` (3 new)

**How:** Call `generateConfig()`, `expect(output).toMatchSnapshot()`.

**Test:** `bun test tests/generators/`

---

## Phase 3: Stale Docs Cleanup

### 3.1 Mark hook-bypass-regex-limitations as RESOLVED

**What:** `docs/bugs/hook-bypass-regex-limitations.md` references `dangerous-patterns.ts`
(deleted) and regex parsing (replaced by AST engine). All 3 issues are fixed:

- Multi-target rm: AST engine checks flags, not trailing path anchor
- Sudo unwrapper: `@questi0nm4rk/shell-ast` `unwrapCall()` handles this
- protect-configs false positives: `checkWriteArgCommands()` checks last-arg destination

**Files:** `docs/bugs/hook-bypass-regex-limitations.md`

**How:** Update status to RESOLVED with references to the fix commits.

### 3.2 Mark fresh-install-bugs as RESOLVED

**What:** All 6 bugs are from the Python era. The TS rewrite eliminated them.

**Files:** `docs/bugs/fresh-install-bugs.md`

**How:** Add header: "All bugs in this document were fixed by the TypeScript rewrite (PR #95)."

### 3.3 Update README

**What:** README references Python-era patterns, old script names, and lists
v2 features without clearly separating shipped vs planned.

**Files:** `README.md`

**How:** Rewrite to reflect TS binary, current CLI commands, current hook system.
Separate "Shipped in v3" from "Planned for v4" sections.

---

## Phase 4: Release Infrastructure

### 4.1 Version management

**What:** Add `version` field to `package.json`, add `bun run version` script
that bumps version + creates git tag.

**Files:** `package.json`

**How:** Use `npm version patch/minor/major` or manual script.

**Dogfood:** `bun run version minor` creates tag `v3.1.0`, pushes tag.

### 4.2 Release workflow

**What:** GitHub Actions workflow that builds binary on tag push, creates
GitHub Release with binary attached.

**Files:** `.github/workflows/release.yml`

**How:** Trigger on `v*` tag push. `bun run build` then upload `dist/ai-guardrails`
as release asset. Build for Linux x64 (primary target).

**Test:** Push a test tag `v0.0.1-test`, verify release is created with binary.

### 4.3 Cross-platform builds

**What:** Build binaries for Linux x64, macOS arm64, macOS x64.

**Files:** `.github/workflows/release.yml` (matrix build)

**How:** Use `bun build --compile --target=` for each platform.
Upload all binaries to the GitHub Release.

**Test:** Download each binary on respective platform, run `--version`.

### 4.4 Install script

**What:** `curl | sh` one-liner that downloads the right binary for the platform.

**Files:** `install.sh` (new, hosted on repo or GitHub Pages)

**How:** Detect OS/arch, download from GitHub Releases, install to `/usr/local/bin`.

**Test:** Run install script on clean machine, verify binary works.

---

## Phase 5: Shell Completion

### 5.1 Implement completion command

**What:** Replace the stub in `src/cli.ts:129-137` with real completion generation.

**Files:** `src/cli.ts`

**How:** Use Commander.js built-in completion or generate scripts manually
for bash, zsh, fish.

**Test:** `ai-guardrails completion bash | source /dev/stdin` then tab-complete.

**Dogfood:** Add to our own shell profile. Verify all subcommands + flags complete.

---

## Phase 6: Hook System Improvements

### 6.1 eval/python-c patterns as engine rules

**What:** `eval $(...)` and `python -c '...'` with dangerous imports are in
`DANGEROUS_DENY_GLOBS` but not in the AST engine rules.

**Files:** `src/check/rules/groups/` (new group file)

**How:** Create `code-injection` rule group:

- `callRule("eval", { reason: "eval command (arbitrary code execution)" })`
- `callRule("python", { flags: ["-c"], reason: "python -c (inline code execution)" })`

**Test:** `evaluate({ type: "bash", command: 'eval "$(curl ...)"' })` returns ask.

### 6.2 Generator respects disabled_groups for deny globs

**What:** Currently `claude-settings.ts` always emits ALL deny globs. Optionally
filter by `disabled_groups` so users who disable a group also remove its globs.

**Files:** `src/generators/claude-settings.ts`, `src/check/ruleset.ts`

**How:** Pass `HooksConfig` to the generator. Filter `collectDenyGlobs()` by
active groups. Make this opt-in (default: all globs for safety).

**Test:** Generate with `disabled_groups: ["chmod"]` — chmod globs absent.

### 6.3 Per-subcommand flag scoping

**What:** If future rules need `-n` aliased differently per git subcommand,
extend `FLAG_GROUPS` to support `(cmd, sub)` scoping.

**Files:** `src/check/flag-aliases.ts`, `src/check/engine.ts`

**How:** Change `expandFlags(flags)` to `expandFlags(cmd, sub, flags)`. Look up
aliases from a `(cmd, sub)`-scoped map first, fall back to global.

**Test:** `-n` resolves to `--no-verify` for `git commit` but `--dry-run` for `git push`.

**Note:** Current workaround (explicit `-n` rule) is fine. Only implement if needed.

### 6.4 Per-language PostToolUse lint hooks

**What:** Generate PostToolUse hooks that run language-appropriate linters after
any Edit/Write/NotebookEdit that touches a file of that language. These are our
hooks (not Claude Code built-ins), emitted as PostToolUse entries in
`.claude/settings.json` with glob matchers.

**Why:** Currently hooks only fire on PreToolUse (blocking dangerous commands).
PostToolUse hooks give the agent instant per-edit lint feedback so issues are
caught individually rather than batched at commit time. Pre-commit hooks remain
the full enforcement suite (format + lint + typecheck + gitleaks + semgrep) —
PostToolUse is an additional lightweight early layer, not a replacement.

**Files:** `src/generators/claude-settings.ts` (add PostToolUse section),
`src/hooks/post-lint.ts` (new hook entry point)

**How:** The generator detects active languages and emits PostToolUse entries:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "./dist/ai-guardrails hook post-lint"
        }]
      }
    ]
  }
}
```

The `post-lint` hook reads the tool_input to get the file path, determines
the language from extension, and runs the appropriate linter:

| Extension | Linter | Command |
|-----------|--------|---------|
| `.ts`, `.tsx`, `.js`, `.jsx` | biome + tsc | `biome check <file>` + `tsc --noEmit` |
| `.py` | ruff | `ruff check <file>` |
| `.rs` | clippy | `cargo clippy -- -W clippy::all` |
| `.go` | golangci-lint | `golangci-lint run <file>` |
| `.sh`, `.bash` | shellcheck | `shellcheck <file>` |
| `.lua` | selene | `selene <file>` |
| `.c`, `.cpp`, `.h` | clang-tidy | `clang-tidy <file>` |

The hook outputs lint findings as a structured message so Claude Code can
surface them to the agent immediately. Exit 0 always (informational, not blocking).

**Modular design:** Each language's lint config is a data declaration in
`src/hooks/post-lint-rules/` — adding a new language is adding a file, not
modifying framework code.

**Test:** Edit a `.ts` file with a biome violation → post-lint hook fires →
reports the violation. Edit a `.py` file → ruff fires. Edit a `.md` file → no
linter fires (no hook for markdown in PostToolUse).

**Dogfood:** Install on this repo. Have an AI agent introduce a type error →
verify the PostToolUse hook catches it before the next tool call.

---

## Phase 7: .NET Runner

### 7.1 MSBuild JSON log parser

**What:** Implement `dotnet build` runner with JSON diagnostic output.

**Files:** `src/runners/dotnet-build.ts` (new), `src/languages/dotnet.ts` (update stub)

**How:** `dotnet build -warnaserror` with structured output + parse diagnostics.

**Test:** Fixture-based tests with sample MSBuild JSON output.

### 7.2 dotnet-format runner

**What:** Add `dotnet format` as a formatting runner for C# projects.

**Files:** `src/runners/dotnet-format.ts` (new)

**How:** `dotnet format --verify-no-changes --report <path>` then parse JSON report.

**Test:** Fixture tests with sample report output.

---

## Phase 8: ai-guardrails-allow Integration

### 8.1 Wire allow comments into checkStep

**What:** Inline `// ai-guardrails-allow: rule-id "reason"` comments bypass
specific rules. Parser exists (`src/hooks/allow-comment.ts`), not integrated
into `checkStep`.

**Files:** `src/steps/check-step.ts`

**How:** Parse allow comments from source files, filter issues that have
matching allow directives. Require reason string.

**Test:** Add allow comment to a file with a lint issue — issue should not fail.

**Dogfood:** Add an intentional suppression to this repo, verify check passes.

### 8.2 allow command

**What:** `ai-guardrails allow <rule> <file> --reason "..."` stores an exception
in a structured exceptions file.

**Files:** `src/commands/allow.ts` (new)

**How:** Append to `.ai-guardrails/exceptions.toml`. Check step reads exceptions
alongside allow comments.

**Test:** `ai-guardrails allow ruff:E501 src/cli.ts --reason "long Commander chain"`
then `check` should skip that issue.

### 8.3 query command

**What:** `ai-guardrails query` lists active exceptions with reasons and authors.

**Files:** `src/commands/query.ts` (new)

**How:** Read `.ai-guardrails/exceptions.toml` + scan allow comments from source.
Output table of active suppressions.

**Test:** Add exceptions, run query, verify output.

---

## Phase 9: Interactive Init Wizard

`ai-guardrails init` currently dumps configs silently. It should be an interactive
setup wizard that lets users choose their enforcement level.

### 9.1 Branch protection setup

**What:** Prompt for branch protection level during init:

- none: no branch rules
- standard: require PR + 1 approval + CI pass
- strict: require PR + 1 approval + CI pass + no force push + dismiss stale reviews

**Files:** `src/steps/setup-branch-protection.ts` (new), `src/pipelines/init.ts`

**How:** Detect GitHub/GitLab via `.git/config` remote URL. Use `gh api` or
GitLab API to set branch protection rules on the default branch.

**Test:** Mock the API calls. Verify correct protection rules for each level.

### 9.2 Pre-commit hook level selection

**What:** Prompt for hook enforcement level:

- format-only: biome/ruff format + re-stage
- standard: format + lint + typecheck + gitleaks
- pedantic: standard + codespell + markdownlint + suppress-comments + semgrep

**Files:** `src/generators/lefthook.ts` (parameterize), `src/pipelines/init.ts`

### 9.3 TypeScript profile prompt

**What:** If TypeScript detected, prompt for strictness profile
(standard / strict / pedantic). Wire into the tsconfig generator from Phase 0.5.

### 9.4 Language confirmation

**What:** Auto-detect languages, show the list, let user confirm or modify.

### 9.5 CI setup prompt

**What:** Ask whether to generate CI config (GitHub Actions / GitLab CI / None).

---

## Phase 10: E2E Fixture Test System

Integration testing with per-language fixture projects.

### 10.1 Per-language fixture projects

**What:** Minimal projects for each supported language, each with intentional
violations and an `expected.toml` declaring what init should produce.

**Files:** `tests/e2e/fixtures/{typescript,python,rust,go,shell,lua,cpp}/`

### 10.2 Monorepo combinator with random language selection

**What:** Combine N random fixtures into a single monorepo. Seed-based RNG
for reproducibility on failure.

### 10.3 E2E test runner

**What:** TestProject class: setup (copy to /tmp), runInit, runCheck,
assertExpected, cleanup.

---

## Phase 11: BDD Test Package (Companion Project)

New repo: `@questi0nm4rk/bdd-test` — BDD testing framework purpose-built for
CLI tool testing, TypeScript-native (tsgo/TS7 ready), Bun-native.

First real greenfield dogfood of `ai-guardrails init`.

### 11.1 Project setup via ai-guardrails init (dogfood)

### 11.2 Gherkin parser adapter (thin layer over @cucumber/gherkin for bun:test)

### 11.3 Step registry with TypeScript-first type inference

### 11.4 Built-in fixture project management (copy/compose/cleanup)

### 11.5 Built-in CLI runner helpers (run binary, capture stdout/stderr/exit)

### 11.6 Built-in config assertions (deep TOML/JSON/YAML compare)

### 11.7 Deterministic random composition (seed-based RNG with replay)

---

## Phase 12: Advanced Features (v4+)

### 9.1 Governance hierarchy

**What:** Organization config overrides team config overrides project config, with locking.

**Depends on:** Config system refactor (SPEC-002 Phase 2).

### 9.2 Agent attribution + auto-strict

**What:** Detect AI-authored code (git author parsing) and apply stricter
rules automatically.

**Depends on:** Governance model for per-author rule sets.

### 9.3 Team features

**What:** `ai-guardrails team list`, `team status`, `report --team` for
multi-developer visibility.

**Depends on:** Governance hierarchy.

### 9.4 Baseline burn-down

**What:** `baseline promote` to move issues from baseline to active.
Track burn-down over time. Integrate with CI reporting.

**Depends on:** Baseline integration (Phase 1).

---

## Verification Strategy

### Per-phase dogfooding

Every phase must pass before merge:

1. `bun test` — all tests pass
2. `bun run typecheck` — clean
3. `bun run lint` — clean
4. `bun run build` — binary builds
5. `./dist/ai-guardrails check --project-dir .` — self-dogfood
6. Phase-specific e2e test (documented per feature above)

### CI gate

Every PR must pass:

- `check.yml` — lint, typecheck, test, semgrep
- `ai-guardrails.yml` — self-dogfood check
- cc-review — automated code review (APPROVED required)

### Release gate

Before tagging a release:

- All phases up to the release scope pass CI
- Fresh install test on clean machine
- README matches shipped features

---

## Current State (2026-03-16)

| Component | Status |
|-----------|--------|
| CLI commands (8) | All working, completion is stub |
| Language plugins (9) | 8 with runners, .NET stub |
| Linter runners (12) | All functional |
| Config generators (10) | All functional |
| Hook system | AST engine + flag aliases + rule groups + config toggling |
| Tests | 570 passing, 85%+ coverage |
| Baseline | Code exists, not wired |
| SARIF output | Implemented |
| CI | lint + test + semgrep + self-dogfood + cc-review |
| Release automation | None |
