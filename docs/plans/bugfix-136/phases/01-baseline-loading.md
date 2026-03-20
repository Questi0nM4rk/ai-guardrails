# Phase 1: Wire baseline loading into checkStep

## Task
Load .ai-guardrails/baseline.json in checkStep, classify each issue as "new" or "existing" using the existing loadBaseline() and classifyFingerprint() functions. Only fail on NEW issues.

## Files
- `src/steps/check-step.ts` — load baseline after filtering, classify issues, update pass/fail logic
- `src/pipelines/check.ts` — may need to pass newIssueCount through PipelineResult

## Key Details
- Import `loadBaseline`, `classifyFingerprint` from `@/models/baseline`
- Import `BASELINE_PATH` from `@/models/paths`
- Load baseline with try/catch (missing file = all issues are new)
- Validate parsed JSON is array before passing to loadBaseline
- Update CheckStepResult to include `newIssueCount` and `baselinedCount`
- Exit code: 0 if newIssues.length === 0, 1 if newIssues.length > 0

## Acceptance Criteria
- checkStep with baseline containing all fingerprints → status "ok", exit 0
- checkStep with baseline missing one fingerprint → status "error", 1 new issue
- checkStep with no baseline file → all issues "new" (backward compatible)
- checkStep with empty baseline → all issues "new"
- All existing tests pass + new baseline tests
- typecheck + lint clean
