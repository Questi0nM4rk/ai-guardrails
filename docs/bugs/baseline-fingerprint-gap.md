# Bug: Baseline Filtering and Stable Fingerprints Not Wired into Check Pipeline

**Discovered:** Round 7 full codebase scan (PR #95, 2026-03-08)
**Severity:** Critical — the core "hold-the-line" feature of `ai-guardrails check` is non-functional
**Status:** Deferred — models and utilities exist, integration is the missing piece

---

## Summary

`ai-guardrails check` is supposed to enforce "hold-the-line": it compares current lint
issues against a saved baseline snapshot and only fails if NEW issues exist since the
baseline was captured. The baseline model (`src/models/baseline.ts`) and snapshot
pipeline (`src/steps/snapshot-step.ts`) are fully implemented and correct. However,
`checkStep` (`src/steps/check-step.ts`) never loads the baseline or calls
`classifyFingerprint()`. It reports ALL current issues as failures, not just new ones.

Additionally, `fingerprintIssue()` (`src/utils/fingerprint.ts`) was designed to compute
content-stable fingerprints from actual source lines (with surrounding context), making
fingerprints survive file moves and minor reformats. It is never called — all 12 runners
call `computeFingerprint()` directly and pass the error message string (or empty string
for clang-tidy) as `lineContent`. This means fingerprints change when tool error messages
change (e.g. during tool version upgrades), which will cause baseline entries to become
stale and trigger false "new issue" alarms.

Both issues must be fixed together for the baseline system to be reliable.

---

## Issue 1: Check step does not filter by baseline

### What should happen

```
ai-guardrails snapshot   # captures current issues as baseline
# ... developer makes changes ...
ai-guardrails check      # only fails if issues ADDED since snapshot
```

### What actually happens

`checkStep` filters issues only via `config.isAllowed()` (the per-rule allow-list).
It does not:

- Load `baseline.json` from disk
- Call `loadBaseline()` to build the fingerprint map
- Call `classifyFingerprint()` per issue to determine "new" vs "existing"
- Filter out "existing" issues from the failure set

Result: every run of `ai-guardrails check` reports every current issue as a failure,
regardless of whether it existed before. The baseline snapshot is written but never read.

### Relevant files

| File | Role |
|------|------|
| `src/steps/check-step.ts:54–57` | Filters only by allow-list, not baseline |
| `src/models/baseline.ts` | `loadBaseline()`, `classifyFingerprint()` — implemented, unused |
| `src/models/paths.ts` | `BASELINE_PATH` constant |
| `src/steps/snapshot-step.ts` | Writes baseline correctly |
| `src/pipelines/check.ts` | Orchestrates check — does not pass baseline path |

### Fix outline

```typescript
// In checkStep, after collecting allIssues:
const baselineJson = await fileManager.readText(
    join(projectDir, BASELINE_PATH)
).catch(() => null);

const baseline = baselineJson
    ? loadBaseline(JSON.parse(baselineJson) as BaselineEntry[])
    : new Map<string, BaselineEntry>();

const newIssues = filtered.filter(
    (issue) => classifyFingerprint(issue.fingerprint, baseline) === "new"
);
// Use newIssues instead of filtered for pass/fail decision
// Keep filtered for reporting (so existing issues are still visible)
```

---

## Issue 2: `fingerprintIssue()` is dead code — fingerprints are not content-stable

### Issue 2: What should happen

Each runner produces a `LintIssue` without a fingerprint, then calls `fingerprintIssue()`
with the actual source file lines to compute a fingerprint that:

- Includes the flagged line's content (survives rule-message rewording)
- Includes ±2 lines of context (survives minor code reformatting)
- Survives file renames if content is unchanged

### Issue 2: What actually happens

All 12 runners call `computeFingerprint()` directly and pass:

- The lint tool's error message string as `lineContent` (ruff, biome, shellcheck, etc.)
- An empty string `""` as `lineContent` (clang-tidy, before R7 fix which now uses message)
- Empty `contextBefore`/`contextAfter` arrays

This means fingerprints are based on the tool's output text, not the source code.
Fingerprints break when:

- The tool changes its error message wording in an upgrade
- The same issue is reported slightly differently across runs
- A file is reformatted without fixing the issue (line numbers shift → different message)

`fingerprintIssue()` in `src/utils/fingerprint.ts` is never imported outside its own file.

### Issue 2: Relevant files

| File | Role |
|------|------|
| `src/utils/fingerprint.ts` | `fingerprintIssue()` — implemented, 0 callers |
| `src/runners/*.ts` | All call `computeFingerprint()` directly |
| `src/models/lint-issue.ts` | `computeFingerprint()` — the lower-level primitive |

### Issue 2: Fix outline

Each runner's `run()` method needs to:

1. Read each affected source file (via `fileManager.readText()`)
2. Split into lines
3. Call `fingerprintIssue(issueWithoutFingerprint, lines)` instead of `computeFingerprint()`

This is more expensive (one file read per unique file in results) but results in stable
fingerprints. Group issues by file to amortize reads:

```typescript
// After parsing raw runner output into issues-without-fingerprints:
const byFile = Map.groupBy(rawIssues, (i) => i.file);
const issues: LintIssue[] = [];
for (const [file, group] of byFile) {
    const src = await opts.fileManager.readText(file).catch(() => "");
    const lines = src.split("\n");
    for (const raw of group) {
        issues.push({ ...raw, fingerprint: fingerprintIssue(raw, lines) });
    }
}
```

---

## Issue 3: Fingerprints include absolute paths — baselines are not portable

**Discovered:** cc-review bot (PR #95, 2026-03-09)

`computeFingerprint()` hashes the `file` field of `FingerprintOpts`, which runners
populate with the raw absolute path from linter output (e.g. `/home/dev/project/src/main.py`).
When `ai-guardrails snapshot` is run locally and `ai-guardrails check` runs in CI at a
different checkout root (e.g. `/home/runner/work/project/src/main.py`), every fingerprint
mismatches and every issue is classified as "new", causing all checks to fail.

This also creates an inconsistency: `LintIssue.file` is documented as absolute (correct —
useful for display and file reads), while `BaselineEntry.file` in `snapshot-step.ts` is
documented as project-relative (correct for portability). The fingerprint should use the
project-relative path but currently uses the absolute path.

### Issue 3: Relevant files

| File | Role |
|------|------|
| `src/models/lint-issue.ts` | `computeFingerprint()` hashes `file` — the absolute path |
| `src/runners/*.ts` | Pass absolute paths via `LintIssue.file` (correct for display) |
| `src/steps/snapshot-step.ts` | `BaselineEntry.file` — project-relative |

### Issue 3: Fix outline

In each runner's `run()` method, compute a relative path for fingerprinting:

```typescript
import { relative } from "node:path";

// When building the fingerprint input:
const relFile = relative(opts.projectDir, absoluteFile);
computeFingerprint({ rule, file: relFile, lineContent, contextBefore, contextAfter });
// Keep LintIssue.file as absolute for display/file reads
```

This fix should be applied alongside the Issue 1 and Issue 2 fixes since they all
require touching the runner `run()` methods.

---

## Why deferred

Both fixes require non-trivial changes across multiple files:

- Issue 1: touch `check-step.ts`, `check.ts` (add baseline path to context/flags)
- Issue 2: touch all 12 runner `run()` methods + their tests (add file reads)

The MVP milestone is "generate configs + run linters + report issues." Baseline
integration is Phase 2 / post-MVP. The snapshot command still works correctly for
capturing state; the issue is only in the check comparison.

---

## Related specs

- `SPEC-004-commands.md` — describes `check` and `snapshot` behaviour including hold-the-line
- `SPEC-003-linter-system.md` — `fingerprintIssue()` design documented
