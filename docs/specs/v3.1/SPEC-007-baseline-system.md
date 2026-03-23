# SPEC-007: Baseline System

## Status: Accepted
## Version: 3.1
## Last Updated: 2026-03-20
## Depends on: SPEC-000 (Overview), SPEC-001 (Architecture), SPEC-003 (Linter System), SPEC-004 (CLI Commands)

---

## Problem

Legacy CI approaches fail on any lint issue. That works for greenfield projects
but collapses on existing codebases with technical debt. Blocking a merge because
of a 3-year-old E501 line-length violation provides zero value — the violation
existed before the current change and is unrelated to it.

The alternative — raising the threshold or disabling the rule — silently weakens
enforcement forever. Once a rule is disabled, it never comes back.

Teams adopting ai-guardrails on existing repositories need a path that:

1. Acknowledges the existing debt without requiring immediate cleanup
2. Guarantees the debt does not grow
3. Is resistant to fingerprint drift when lines are renumbered

Line-number-based baselines fail when code above the violation is added or
deleted. A baseline tied to line numbers expires the moment any file is touched.

---

## Solution

A **content-stable fingerprint** system: each issue is identified by a SHA-256
hash of its rule ID, the relative file path, the trimmed content of the flagged
line, and up to two lines of surrounding context. The fingerprint is stable when
lines above or below the violation are added or removed; it only changes when
the flagged line itself is modified.

The baseline is a JSON array written by `ai-guardrails snapshot` and consumed
by `ai-guardrails check`. Check computes fingerprints for every current issue,
looks each one up in the baseline map, and only fails if a fingerprint is not
found (i.e., the issue is new). Issues that are in the baseline but no longer
present are silently ignored — they will naturally disappear from the next
snapshot.

---

## Philosophy

1. **Hold-the-line, not zero-tolerance.** The check enforces that the debt does
   not grow, not that it does not exist.
   WHY: Zero-tolerance on existing debt blocks adoption entirely. If every
   repository must be clean before guardrails can be added, guardrails never
   get added. Hold-the-line removes the adoption barrier while still enforcing
   a hard ceiling on new debt.

2. **Content-stable fingerprints.** Fingerprints are anchored to source content,
   not line numbers.
   WHY: Line numbers change constantly during development. A line-number-based
   baseline expires on the first commit that adds a line above the violation.
   Content-stable fingerprints survive refactoring, file reorganization, and
   interleaved edits — as long as the flagged line itself is not changed.

3. **Relative paths in the baseline.** Fingerprints use project-relative paths,
   not absolute paths.
   WHY: Absolute paths are machine-specific. A baseline written on one developer's
   machine would produce different fingerprints than one written on another's, or
   in CI. Relative paths make the baseline portable across all environments.

4. **Zod at file boundaries, not at runtime.** The baseline file is Zod-parsed
   once on load. All downstream consumers work with typed `BaselineEntry` values.
   WHY: Runtime type checking is expensive and repetitive. Parsing at the
   boundary gives a single validation point; the rest of the system can trust
   the type.

5. **Null-safe baseline.** A missing or corrupt baseline file is treated as an
   empty baseline. Check never fails because a baseline file is absent.
   WHY: A repository without a baseline is not in error — it simply has not run
   `snapshot` yet. Failing `check` because no baseline exists would block CI
   for every new project.

6. **Snapshot respects allowlist.** Issues suppressed by config (`isAllowed()`)
   are not written to the baseline.
   WHY: Baselined allowed issues would be loaded and compared unnecessarily.
   The allowlist defines what the tool ignores; the baseline captures what the
   tool sees but accepts. These are different things and must not mix.

7. **Allow comments are permanent decisions; baseline is temporary debt.**
   `ai-guardrails-allow` inline comments express a conscious, code-local
   decision ("this specific line is exempt for this reason"). Baseline entries
   express accumulated debt ("this violation existed before guardrails were
   added and we have not fixed it yet"). The two mechanisms must not be
   conflated — allow comments are never baselined, and baseline entries never
   suppress the allow-comment check.
   WHY: Mixing them creates ambiguity about whether a suppression is intentional
   or accidental debt. Keeping them separate preserves the audit trail.

---

## Constraints

### Hard Constraints

- Fingerprints use SHA-256 — no alternative hash algorithm
- Baseline file path is `.ai-guardrails/baseline.json` (constant `BASELINE_PATH`)
- Baseline entries use project-relative paths in the `file` field
- Zod schema is the single source of truth for `BaselineEntry` shape
- `applyFingerprints` receives absolute paths; converts to relative internally
- Baseline loading returns `null` on any error — never throws

### Soft Constraints

- Read source files in parallel when fingerprinting (one I/O per unique file)
- Use `CONTEXT_LINES = 2` (two lines before and after the flagged line)
- Trim all lines before hashing (whitespace-only changes must not change fingerprints)

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| SHA-256 collision probability is negligible for lint issues | Collision detected causing false "existing" | Switch to SHA-512 in `computeFingerprint`, bump baseline format version |
| Source files are readable at fingerprint time | File deleted between lint and fingerprint | `applyFingerprints` catches read errors and uses empty sourceLines — fingerprint degrades gracefully |
| Relative paths are stable across machines | Monorepo uses different root per machine | Add `rootDir` field to baseline format, normalize relative to explicit root |
| Baseline stays small enough to load fully into memory | Large projects with 10k+ baselined issues | Stream-parse baseline with a Set of fingerprint strings instead of Map of entries |

---

## 1. Baseline Data Model

The Zod schema is the single source of truth. All types are derived from it.

```typescript
// src/models/baseline.ts

export const BaselineEntrySchema = z.object({
  fingerprint: z.string(),
  rule: z.string(),
  linter: z.string(),
  file: z.string(),        // project-relative path
  line: z.number(),
  message: z.string(),
  capturedAt: z.string(),  // ISO 8601 timestamp
});

export type BaselineEntry = z.infer<typeof BaselineEntrySchema>;
export type BaselineStatus = "new" | "existing" | "resolved";
```

The baseline file on disk is a JSON array of `BaselineEntry` objects:

```json
[
  {
    "fingerprint": "a3f9b2c1...",
    "rule": "E501",
    "linter": "ruff",
    "file": "src/models/lint-issue.ts",
    "line": 42,
    "message": "Line too long (92 > 88 characters)",
    "capturedAt": "2026-03-20T12:00:00.000Z"
  }
]
```

### Loading

```typescript
export function loadBaseline(
  entries: readonly BaselineEntry[]
): ReadonlyMap<string, BaselineEntry> {
  return new Map(entries.map((e) => [e.fingerprint, e]));
}
```

The runtime representation is a `ReadonlyMap<string, BaselineEntry>` keyed by
fingerprint for O(1) lookup. The map is immutable — classification never mutates it.

### Classification

```typescript
export function classifyFingerprint(
  fingerprint: string,
  baseline: ReadonlyMap<string, BaselineEntry>
): BaselineStatus {
  return baseline.has(fingerprint) ? "existing" : "new";
}
```

`"resolved"` is not returned by `classifyFingerprint` — it describes entries in
the baseline that are no longer present in the current run. Resolution is a
property of the next snapshot, not of check.

### File Loading

```typescript
export async function loadBaselineFromFile(
  projectDir: string,
  fileManager: { readText(path: string): Promise<string> }
): Promise<ReadonlyMap<string, BaselineEntry> | null>
```

Returns `null` on any error (file not found, JSON parse error, Zod validation
failure). Callers treat `null` as an empty baseline via the `?? new Map()`
pattern.

---

## 2. Fingerprint System

The fingerprint uniquely identifies a lint issue by its content, not its
position.

### FingerprintOpts (input)

```typescript
export interface FingerprintOpts {
  rule: string;
  file: string;          // project-relative path
  lineContent: string;   // content of the flagged line
  contextBefore: string[]; // up to 2 lines before (may be fewer at file start)
  contextAfter: string[];  // up to 2 lines after (may be fewer at file end)
}
```

### Hash Input Construction

```typescript
export function computeFingerprint(opts: FingerprintOpts): string {
  const { rule, file, lineContent, contextBefore, contextAfter } = opts;
  const input = [
    rule,
    file,
    lineContent.trim(),
    ...contextBefore.map((l) => l.trim()),
    ...contextAfter.map((l) => l.trim()),
  ].join("\n");
  return createHash("sha256").update(input).digest("hex");
}
```

Hash input components (joined with `\n`):

1. `rule` — e.g. `"E501"`, `"no-unused-vars"`, `"S1481"`
2. `file` — project-relative path (e.g. `"src/models/lint-issue.ts"`)
3. `lineContent.trim()` — trimmed content of the flagged line
4. `contextBefore[0..1].trim()` — up to 2 preceding lines, trimmed
5. `contextAfter[0..1].trim()` — up to 2 following lines, trimmed

Including the file path ensures identical violations in different files produce
distinct fingerprints. Trimming eliminates indentation-only changes.

### fingerprintIssue (high-level)

```typescript
// src/utils/fingerprint.ts
const CONTEXT_LINES = 2;

export function fingerprintIssue(
  issue: Omit<LintIssue, "fingerprint">,
  sourceLines: string[]
): string
```

Converts the 1-indexed `issue.line` to a 0-indexed array offset, extracts
`CONTEXT_LINES` lines before and after (clamped to array bounds), then calls
`computeFingerprint`. If the file could not be read, `sourceLines` is `[]` and
`lineContent` is `""` — the fingerprint degrades but does not throw.

### applyFingerprints (batch)

```typescript
// src/utils/apply-fingerprints.ts

export async function applyFingerprints(
  raw: Omit<LintIssue, "fingerprint">[],
  projectDir: string,
  fileManager: FileManager
): Promise<LintIssue[]>
```

1. Groups issues by absolute file path using `groupBy`
2. Reads all unique source files in parallel (`Promise.all`)
3. Converts each absolute path to a project-relative path via `relative(projectDir, absFile)`
4. Calls `fingerprintIssue({ ...issue, file: relFile }, sourceLines)` per issue
5. Returns fully typed `LintIssue[]` with fingerprints attached

The absolute-to-relative conversion happens inside `applyFingerprints`, not
in linter runners. Runners emit absolute paths; the fingerprint layer normalizes
them. This is the single conversion point — there is no other place in the
pipeline where this transform occurs.

---

## 3. LintIssue Model

```typescript
// src/models/lint-issue.ts

export interface LintIssue {
  readonly rule: string;
  readonly linter: string;
  readonly file: string;       // absolute path (set by runner)
  readonly line: number;       // 1-indexed
  readonly col: number;        // 1-indexed
  readonly message: string;
  readonly severity: "error" | "warning";
  readonly fingerprint: string; // content-stable SHA-256
}
```

The `file` field is absolute inside `LintIssue` (runner output). The `file`
field inside `BaselineEntry` is project-relative (snapshot output). These are
different types — do not confuse them.

---

## 4. Hold-the-Line Contract

### Exit Code Semantics

| Code | Condition |
|------|-----------|
| 0 | Zero new issues (all issues are either absent or baselined) |
| 1 | One or more new issues found |
| 2 | Tool error (config missing, linter crash, unreadable file) |

```typescript
// src/commands/check.ts

export async function runCheck(
  projectDir: string,
  flags: Record<string, unknown>
): Promise<void> {
  const ctx = buildContext(projectDir, flags);
  const result = await checkPipeline.run(ctx);
  if (result.status === "error") {
    const issueCount = result.issueCount ?? 0;
    if (issueCount === 0) {
      process.stderr.write(`Error: ${result.message ?? "unknown error"}\n`);
      process.exit(2);
    }
    process.exit(1);
  }
}
```

Exit 1 means "new issues exist." Exit 2 means "the tool itself failed." CI
systems treat these differently: exit 1 means "block the PR," exit 2 means
"re-run the workflow" or "investigate the tool."

### Allow Comment Integration

`checkStep` parses source files for inline `ai-guardrails-allow` comments and
filters matching issues before baseline comparison. This is the only point in
the pipeline where allow comments are evaluated.

**Comment syntax** (language-agnostic, comment prefix varies):

```
// ai-guardrails-allow ruff/E501 "reason string"
# ai-guardrails-allow ruff/E501 "reason string"
-- ai-guardrails-allow ruff/E501 "reason string"
```

Format: `ai-guardrails-allow <linter/RULE_CODE> "<reason>"` — the reason is
required and must be quoted. Bare `ai-guardrails-allow ruff/E501` without a
reason is rejected by the suppress-comments hook at pre-commit time.

**Integration in checkStep:**

```typescript
// src/steps/check-step.ts

// 1. Filter by config allowlist (isAllowed checks config [[allow]] entries)
const configFiltered = issues.filter(
  (i) => !config.isAllowed(i.rule, i.file)
);

// 2. Filter by inline allow comments
const commentFiltered = await filterAllowComments(configFiltered, fileManager);

// 3. Compare remainder against baseline
const baseline = (await loadBaselineFromFile(projectDir, fileManager)) ?? new Map();
const newIssues = commentFiltered.filter(
  (issue) => classifyFingerprint(issue.fingerprint, baseline) === "new"
);
```

`filterAllowComments` (`src/steps/filter-allow-comments.ts`):
1. Groups issues by file path
2. For each file, reads the source and scans for `ai-guardrails-allow` patterns
3. For each issue on a line adjacent to (same line or line above) an allow comment
   matching the same rule, marks it as suppressed
4. Returns the unsuppressed subset

**Allow-baseline interaction model:**

| Issue State | In baseline? | Has allow comment? | checkStep result |
|-------------|-------------|-------------------|-----------------|
| New issue | No | No | Fails (new issue) |
| Baselined issue | Yes | No | Passes (existing debt) |
| Allowed by comment | Either | Yes | Passes (suppressed) |
| Allowed by config | Either | No (config entry) | Passes (suppressed) |

An issue with an allow comment is never reported — regardless of baseline state.
If the same issue is both baselined and has an allow comment, the allow comment
takes precedence (the baseline entry becomes stale and will naturally age out).

### checkStep Logic

```typescript
// src/steps/check-step.ts

const baseline = (await loadBaselineFromFile(projectDir, fileManager)) ?? new Map();

const newIssues = filtered.filter(
  (issue) => classifyFingerprint(issue.fingerprint, baseline) === "new"
);
const baselinedCount = filtered.length - newIssues.length;
```

Where `filtered` is the result after both config `isAllowed()` and
`filterAllowComments()` have been applied (see §Allow Comment Integration above).

The step returns:
- `result: ok(msg)` if `newIssues.length === 0`
- `result: error(msg)` if `newIssues.length > 0`
- `newIssueCount: newIssues.length` (passed through to `PipelineResult.issueCount`)
- `issues: filtered` (all filtered issues, not just new ones — used by report step)

Console message examples:
- "No issues found" — nothing at all
- "No new issues (5 baselined)" — all issues are in the baseline
- "Found 3 new issue(s) (5 baselined)" — mix of new and baselined

### Pipeline Pass-Through

```typescript
// src/pipelines/check.ts

return {
  status: "error",
  message: checkResult.message,
  issueCount: newIssueCount,  // distinguishes exit 1 from exit 2
};
```

`issueCount` is carried through `PipelineResult` so `runCheck` can distinguish
between "new issues found" (exit 1) and "pipeline error" (exit 2). Without this
field, all errors would exit 2.

---

## 5. Snapshot/Check Round-Trip

### Snapshot

```typescript
// src/steps/snapshot-step.ts

function issueToEntry(issue: LintIssue, projectDir: string): BaselineEntry {
  return {
    fingerprint: issue.fingerprint,
    rule: issue.rule,
    linter: issue.linter,
    file: relative(projectDir, issue.file),  // absolute → relative
    line: issue.line,
    message: issue.message,
    capturedAt: new Date().toISOString(),
  };
}
```

`snapshotStep` runs the full linter collection, applies the config allowlist
filter (`config.isAllowed()`), applies the inline allow-comment filter
(`filterAllowComments()`), converts each remaining issue to a `BaselineEntry`,
and writes the resulting JSON array to `.ai-guardrails/baseline.json`.

Issues suppressed by an inline `ai-guardrails-allow` comment are excluded from
the snapshot — they represent permanent decisions, not temporary debt, and must
not appear in the baseline. This is the snapshot-side complement to the
checkStep allow-comment filtering.

The `--baseline <path>` flag allows writing to a custom path. The check command
accepts the same flag for reading from a non-standard location.

### Round-Trip Invariant

For any issue `I` written by snapshot and then seen in a subsequent check:

```
snapshot: fingerprintIssue({ ...I, file: relative(dir, I.file) }, sourceLines) = F
check:    fingerprintIssue({ ...I, file: relative(dir, I.file) }, sourceLines) = F
classifyFingerprint(F, baseline) = "existing"
```

The round-trip holds as long as the flagged line and its two surrounding lines
are unchanged. If the flagged line is modified, the fingerprint changes and the
issue appears as new — which is correct: the programmer changed the code, so
the violation is a new decision.

### `ai-guardrails snapshot` Command

```
ai-guardrails snapshot [--baseline <path>]
```

Steps:
1. `detectLanguagesStep` — determine active language plugins
2. `loadConfigStep` — load merged config (allowlist, profiles)
3. `snapshotStep` — run linters, filter, fingerprint, write baseline

Exit codes: 0 on success, 2 on any error (linter crash, write failure).

---

## Testing Strategy

| Test file | What is tested |
|-----------|----------------|
| `tests/models/baseline.test.ts` | `loadBaseline`, `classifyFingerprint`, `loadBaselineFromFile` — valid JSON, corrupt JSON, missing file, empty array |
| `tests/models/lint-issue.test.ts` | `computeFingerprint` — same content = same hash, different file = different hash, trimming invariant |
| `tests/utils/fingerprint.test.ts` | `fingerprintIssue` — context extraction at file start/end, empty sourceLines, 1-indexed line conversion |
| `tests/utils/apply-fingerprints.test.ts` | `applyFingerprints` — parallel reads, absolute-to-relative conversion, unreadable file fallback |
| `tests/steps/check-step.test.ts` | New/existing/all-baselined classification, skipped runners, allowlist filtering, allow-comment filtering, ignore paths |
| `tests/steps/filter-allow-comments.test.ts` | Comment parsed correctly, issue suppressed when rule matches, unsuppressed when rule differs, missing file handled gracefully |
| `tests/steps/snapshot-step.test.ts` | Writes correct JSON, allowlist filter applied, allow-comment filter applied, `capturedAt` is ISO 8601 |
| `tests/pipelines/check.test.ts` | `issueCount` pass-through, exit 1 vs exit 2 distinction |

**Fake contract:** All tests use `FakeFileManager` and `FakeCommandRunner`.
No real files are read. No real linters are invoked.

**Round-trip test:** A single integration test seeds a `FakeFileManager` with
source content, runs snapshot, then runs check against the written baseline,
and asserts exit 0.

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| SHA-256 fingerprint algorithm | Collision detected in practice | Change hash function in `computeFingerprint`, migrate existing baselines |
| `CONTEXT_LINES = 2` | Fingerprint instability reported with 2 lines | Increase to 3 or 4, update fixtures |
| Baseline as flat JSON array | Performance issues with 10k+ entries | Switch to JSONL, stream-parse, use Set of fingerprints |
| Relative paths in baseline | Monorepo with multiple project roots | Add `rootDir` to `BaselineEntrySchema`, normalize relative to explicit root |
| `issueCount` in `PipelineResult` | Exit code semantics change | Update all pipeline callers, update SPEC-004 |
| `null` return from `loadBaselineFromFile` | Distinguish "missing file" from "corrupt file" | Split into two return states, update callers |

---

## Cross-References

- SPEC-000: Philosophy principles 1 (errors or ignored), 4 (whitelist model)
- SPEC-001: `PipelineContext`, `StepResult`, `FileManager` interface
- SPEC-003: `LintIssue` as produced by linter runners; `LinterRunner.run()` emits absolute paths
- SPEC-004: `check`, `snapshot`, `allow`, `query` commands, exit code table
