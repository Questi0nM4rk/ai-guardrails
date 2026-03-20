# Phase 4: Snapshot consistency

## Task
Update snapshotStep to store relative file paths in baseline entries, ensuring snapshot and check use the same fingerprint data.

## Files
- `src/steps/snapshot-step.ts` — update issueToEntry to use relative paths

## Key Details
- `issueToEntry(issue, projectDir)` — add projectDir param
- Use `relative(projectDir, issue.file)` for BaselineEntry.file
- Runners already compute fingerprints with relative paths (from Phase 2)
- snapshotStep already calls runners via runLinterCollection which passes fileManager

## Acceptance Criteria
- Baseline entries have relative file paths (not absolute)
- Baseline created by snapshot is loadable by checkStep
- Round-trip: snapshot → check → all issues classified as "existing"
- All existing tests pass
- typecheck + lint clean
