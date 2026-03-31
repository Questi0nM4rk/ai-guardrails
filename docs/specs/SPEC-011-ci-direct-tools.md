# SPEC-011: CI Workflow with Direct Tool Invocations

## Status: Draft
## Version: 1.0
## Last Updated: 2026-03-31
## Depends on: SPEC-004 (Commands), SPEC-009 (Interactive Init)

---

## Problem

The generated CI workflow (`.github/workflows/ai-guardrails.yml`) runs
`bunx ai-guardrails check`. This is broken for every consumer project:

1. **Wrong npm package.** `bunx` resolves `ai-guardrails@1.0.0` on npm — an unrelated
   package with no `bin` field. `bunx` exits 1: "could not determine executable."

2. **No GitHub release.** The `install.sh` fallback calls
   `api.github.com/repos/.../releases/latest` which 404s until the first release is
   published. New adopters cannot bootstrap their own CI.

The result: `ai-guardrails init` generates a CI workflow that fails on the very first push.

## Solution

Update the `githubActionsModule` to emit direct tool invocations (biome, ruff, tsc,
pyright, codespell, markdownlint, gitleaks) instead of `bunx ai-guardrails check`.
The template becomes language-aware — it reads detected languages from `InitContext`
and emits only relevant steps.

Chose updating the existing init template over a new `generate-ci` subcommand because:
- Fewer moving parts — one code path, not two
- Init already has language detection — no need to re-detect
- Users re-generate by running `init --force`, which already works

The binary-based `ai-guardrails check` remains valuable locally for baseline diffing
and hold-the-line semantics. CI just doesn't need it.

---

## Affected Components

| Component | File/Path | Change Type |
|-----------|-----------|-------------|
| CI step | `src/steps/setup-ci.ts` | modify |
| GitHub Actions module | `src/init/modules/github-actions.ts` | modify |
| InitContext type | `src/init/types.ts` | modify (add languages) |
| CI step tests | `tests/steps/setup-ci.test.ts` | modify |
| CI snapshot | `tests/steps/__snapshots__/setup-ci.test.ts.snap` | modify |

---

## Acceptance Criteria

1. When `init` detects TypeScript, the CI workflow includes `biome check .` and
   `tsc --noEmit` steps with `oven-sh/setup-bun@v2`.
2. When `init` detects Python, the CI workflow includes `ruff check .` and
   `pyright` steps with `actions/setup-python@v5` and `pip install` for tools.
3. When both languages are detected, all language-specific steps are present.
4. The CI workflow always includes `codespell`, `markdownlint-cli2`, and
   `gitleaks detect` regardless of detected languages.
5. The CI workflow does NOT reference `ai-guardrails` binary, `bunx`, or `install.sh`.
6. The generated workflow passes CI on the very first push of a new project.

---

## Template Structure

`setupCiStep()` receives a `ReadonlySet<string>` of detected language plugin IDs
and builds the YAML dynamically:

```yaml
name: AI Guardrails Check
on:
  push:
    branches: ["**"]
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # --- Language setup (conditional) ---
      - uses: oven-sh/setup-bun@v2          # if typescript detected
      - uses: actions/setup-python@v5        # if python detected
        with:
          python-version: "3.12"

      # --- Install (conditional) ---
      - name: Install JS dependencies
        run: bun install --frozen-lockfile    # if bun.lock exists
        if: hashFiles('bun.lock', 'bun.lockb') != ''
      - name: Install Python tools
        run: pip install ruff pyright codespell  # if python detected

      # --- Language-specific checks ---
      - name: Lint (biome)                   # if typescript
        run: bunx biome check .
      - name: Typecheck (tsc)                # if typescript
        run: bunx tsc --noEmit
      - name: Lint (ruff)                    # if python
        run: ruff check .
      - name: Typecheck (pyright)            # if python
        run: pyright

      # --- Universal checks (always) ---
      - name: Spell check
        run: codespell --skip="*.lock,node_modules,dist" .
      - name: Markdown lint
        run: bunx markdownlint-cli2 "**/*.md" "#node_modules"
      - name: Secret scan
        run: gitleaks detect --no-banner
```

---

## Implementation Detail

**`src/steps/setup-ci.ts`** — Replace the static `CI_WORKFLOW` string with a
`buildCiWorkflow(languages: ReadonlySet<string>)` function that constructs
the YAML from conditional sections.

**`src/init/modules/github-actions.ts`** — Pass `ctx.languages` (the set of
detected language plugin IDs) to `setupCiStep()`. The module's `execute()`
method already receives `InitContext` which carries language detection results.

**`src/init/types.ts`** — Ensure `InitContext` exposes `languages: ReadonlySet<string>`
(the set of active plugin IDs like `"typescript"`, `"python"`). This is populated
by the `detect-languages` phase which runs before all config modules (see SPEC-009
§Module Registry — `githubActionsModule` depends on `config-tuning` which depends on
`profile-selection`, and language detection runs before all of them in
`src/pipelines/init.ts:81-87`).

---

## Edge Cases

| Scenario | Expected Behavior | Priority |
|----------|-------------------|----------|
| No languages detected (empty repo) | Only universal checks emitted (codespell, markdownlint, gitleaks) | medium |
| TypeScript-only project | No Python setup/steps, no pip install | high |
| Python-only project | No Bun setup. codespell installed via pip. markdownlint via `npx` or `pipx` | high |
| Project with Go, Rust, etc. | Only universal checks — no Go/Rust CI steps yet (future work) | low |
| `bun.lock` doesn't exist yet | `if: hashFiles(...)` skips the install step | medium |

---

## Cross-References

- SPEC-004 §init — defines the init pipeline steps.
  **Note:** SPEC-004 currently says init calls `setupCiStep()`. After this spec,
  SPEC-004 should note that the CI step emits direct tool invocations, not binary.
- SPEC-009 §githubActionsModule — the init module that writes CI
- GitHub: #184 (feature request), #183 (bug report, closed as duplicate)
