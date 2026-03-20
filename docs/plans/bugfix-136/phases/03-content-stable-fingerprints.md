# Phase 3: Content-stable fingerprints

## Task
Replace message-based fingerprints with source-line-based fingerprints in all 12 runners. Use existing fingerprintIssue() from src/utils/fingerprint.ts.

## Files
- All 12 runners in `src/runners/`
- `src/utils/collections.ts` (new) — add `groupBy<T>()` utility if not exists

## Pattern
Each runner restructures from:
```typescript
// old: fingerprint from tool error message
computeFingerprint({ rule, file, lineContent: item.message, contextBefore: [], contextAfter: [] })
```
To:
```typescript
// new: fingerprint from actual source lines
// 1. Parse tool output into raw issues (without fingerprint)
// 2. Group by file
// 3. Read each file once via opts.fileManager.readText()
// 4. Split to lines, call fingerprintIssue(issue, lines)
```

fallback: if file can't be read, use empty sourceLines (fingerprintIssue handles this gracefully)

## Acceptance Criteria
- Same issue with different error message but same source → same fingerprint
- Fingerprints change from old values (snapshot update needed)
- All runner tests pass (update expected fingerprints/snapshots)
- typecheck + lint clean
