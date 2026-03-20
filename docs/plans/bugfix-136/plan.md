# Bugfix Plan: Issue #136 — Baseline integration (check exits 1 with all baselined issues)

## Problem

`ai-guardrails check` exits 1 when ANY issues exist, even if all are baselined.
CI fails on every run in projects with pre-existing issues, defeating the
"hold-the-line" baseline contract. The baseline infrastructure exists
(`loadBaseline`, `classifyFingerprint`, `fingerprintIssue`) but isn't wired.

## Solution

Four sub-phases that build on each other:
- 3a: Wire baseline loading into checkStep (check respects baseline)
- 3b: Relative paths in fingerprints (baselines portable across machines/CI)
- 3c: Content-stable fingerprints (baselines survive tool version upgrades)
- 3d: Snapshot step uses same fingerprint method (snapshot/check consistency)

## Files

### Phase 3a — checkStep baseline loading
- `src/steps/check-step.ts` — load baseline.json, classify issues, pass/fail on new only

### Phase 3b — relative paths in fingerprints (12 runners)
- `src/runners/biome.ts`
- `src/runners/ruff.ts`
- `src/runners/pyright.ts`
- `src/runners/tsc.ts`
- `src/runners/clippy.ts`
- `src/runners/golangci-lint.ts`
- `src/runners/shellcheck.ts`
- `src/runners/shfmt.ts`
- `src/runners/selene.ts`
- `src/runners/clang-tidy.ts`
- `src/runners/codespell.ts`
- `src/runners/markdownlint.ts`

### Phase 3c — content-stable fingerprints (12 runners + utility)
- Same 12 runner files above
- `src/utils/fingerprint.ts` (already implemented, just needs wiring)

### Phase 3d — snapshot consistency
- `src/steps/snapshot-step.ts` — use same fingerprint pipeline as check
- `src/steps/run-linters.ts` — may need fileManager pass-through

---

## Phase 3a: Wire baseline into checkStep

**Current code** (`src/steps/check-step.ts:69-73`):
```typescript
// TODO(baseline): Load .ai-guardrails/baseline.json and call
// classifyFingerprint() to filter out "existing" issues...
```

**Change:** After computing `filtered` (line 67), add:

```typescript
import { join } from "node:path";
import { loadBaseline, classifyFingerprint } from "@/models/baseline";
import type { BaselineEntry } from "@/models/baseline";
import { BASELINE_PATH } from "@/models/paths";

// After filtered array is computed:
const baselinePath = join(projectDir, BASELINE_PATH);
let baseline: ReadonlyMap<string, BaselineEntry> = new Map();
try {
  const raw = await fileManager.readText(baselinePath);
  const parsed: unknown = JSON.parse(raw);
  if (Array.isArray(parsed)) {
    baseline = loadBaseline(parsed as readonly BaselineEntry[]);
  }
} catch {
  // No baseline file or invalid JSON — treat all issues as new
}

const newIssues = filtered.filter(
  (issue) => classifyFingerprint(issue.fingerprint, baseline) === "new"
);
const baselinedCount = filtered.length - newIssues.length;
```

Update the pass/fail logic to use `newIssues.length` instead of `filtered.length`.
Return all `filtered` issues for reporting but only fail on `newIssues`.

**Exit code semantics (from src/commands/check.ts):**
- Exit 0: `result.status === "ok"` — no new issues (all baselined or clean)
- Exit 1: `result.issueCount > 0` — new issues found
- Exit 2: `result.issueCount === 0` but error — config/tool error

Update `CheckStepResult` to include `newIssueCount` and `baselinedCount` for
reporting. The pipeline already has `issueCount` on `PipelineResult` — use
`newIssueCount` for the exit code decision.

---

## Phase 3b: Relative paths in fingerprints

**Current pattern** (all 12 runners):
```typescript
const fingerprint = computeFingerprint({
  rule,
  file: item.filename,  // absolute path
  lineContent: item.message,
  contextBefore: [],
  contextAfter: [],
});
```

**Change:** Each runner already receives `opts.projectDir` via `RunOptions`.
Use `relative()` to convert absolute to project-relative:

```typescript
import { relative } from "node:path";

// In the issue mapping:
const relFile = relative(opts.projectDir, absoluteFile);
const fingerprint = computeFingerprint({
  rule,
  file: relFile,  // project-relative path
  lineContent: item.message,
  contextBefore: [],
  contextAfter: [],
});
```

**Keep `LintIssue.file` absolute** for display/reporting. Only the fingerprint
uses the relative path. This means the `file` field in computeFingerprint differs
from `LintIssue.file` — that's intentional.

Each of the 12 runners needs ~2 lines changed.

---

## Phase 3c: Content-stable fingerprints

**Current problem:** Runners pass `item.message` (tool's error text) as
`lineContent`. When tools upgrade and change error messages, fingerprints break,
invalidating baselines silently.

**Fix:** Use `fingerprintIssue()` from `src/utils/fingerprint.ts` which reads
actual source lines. This function already exists and is tested — just not wired.

**Pattern for each runner:**

```typescript
import { fingerprintIssue } from "@/utils/fingerprint";

// In run():
// 1. Parse tool output into raw issues (without fingerprints)
// 2. Group by file
// 3. Read each file once via fileManager
// 4. Compute fingerprints using source content

const rawIssues = parseOutput(stdout, opts.projectDir);
const issuesByFile = groupBy(rawIssues, (i) => i.file);
const result: LintIssue[] = [];

for (const [file, issues] of issuesByFile) {
  let sourceLines: string[] = [];
  try {
    const content = await opts.fileManager.readText(file);
    sourceLines = content.split("\n");
  } catch {
    // File unreadable — fall back to empty context
  }

  const relFile = relative(opts.projectDir, file);
  for (const issue of issues) {
    const fingerprint = fingerprintIssue(
      { ...issue, file: relFile },
      sourceLines
    );
    result.push({ ...issue, fingerprint });
  }
}
```

**Utility needed:** `groupBy<T>(items: T[], key: (item: T) => string): Map<string, T[]>`.
Check if this exists in utils/ — if not, add to `src/utils/collections.ts`.

Each runner needs restructuring: parse output → group by file → read files →
compute fingerprints. This is the biggest change (~20-30 LOC per runner).

---

## Phase 3d: Snapshot consistency

**Current:** `snapshotStep` calls `runLinterCollection()` which calls each
runner's `run()`. If runners are updated in 3b/3c, snapshot automatically
gets the same fingerprints. But verify:

- `runLinterCollection` passes `fileManager` through `RunOptions` ✓
- `snapshotStep.issueToEntry` copies `issue.fingerprint` directly ✓
- `BaselineEntry.file` should use the same relative path as the fingerprint

**Change:** `issueToEntry` should store the relative file path:
```typescript
function issueToEntry(issue: LintIssue, projectDir: string): BaselineEntry {
  return {
    fingerprint: issue.fingerprint,
    rule: issue.rule,
    linter: issue.linter,
    file: relative(projectDir, issue.file),  // relative for portability
    line: issue.line,
    message: issue.message,
    capturedAt: new Date().toISOString(),
  };
}
```

---

## Tests

### 3a tests
- checkStep with baseline file containing all issue fingerprints → status "ok"
- checkStep with baseline missing one fingerprint → status "error", 1 new issue
- checkStep with no baseline file → all issues are "new" (backward compatible)
- checkStep with empty baseline → all issues are "new"
- CheckStepResult includes newIssueCount and baselinedCount

### 3b tests
- Each runner produces fingerprints with relative paths (not absolute)
- Same issue at different absolute paths but same relative path → same fingerprint
- Snapshot then check on same project → all issues classified as "existing"

### 3c tests
- fingerprintIssue with source lines produces different fingerprint than message-based
- Same issue with different error message but same source → same fingerprint
- Runner integration: mock tool output + mock file content → stable fingerprint

### 3d tests
- snapshotStep stores relative file paths in baseline entries
- Baseline created by snapshot is loadable by checkStep

## Verification

End-to-end:
```bash
bun run build
mkdir /tmp/baseline-test && cd /tmp/baseline-test
echo '{}' > package.json
echo 'let x = 1;' > src/test.ts  # useConst violation
../ai-guardrails init --force --no-hooks --no-ci
../ai-guardrails snapshot
../ai-guardrails check  # should exit 0 (all baselined)
echo 'let y = 2;' >> src/test.ts  # add new violation
../ai-guardrails check  # should exit 1 (1 new issue)
```

## Execution Strategy

3a → 3b → 3c → 3d sequentially. Each sub-phase builds on the previous.
Can be split into separate commits within the same PR.
