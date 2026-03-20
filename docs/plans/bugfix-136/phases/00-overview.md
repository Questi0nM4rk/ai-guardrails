# Bugfix #136 — Phases Overview

4 sequential phases (each builds on previous).

```
Phase 1 (baseline-loading)     → Phase 2 (relative-paths)
  → Phase 3 (content-stable)   → Phase 4 (snapshot-consistency)
```

## Phase 1: baseline-loading
- Wire baseline.json loading into checkStep, pass/fail on new issues only
- Files: src/steps/check-step.ts
- Depends on: nothing

## Phase 2: relative-fingerprints
- Use relative paths in computeFingerprint across all 12 runners
- Files: all src/runners/*.ts
- Depends on: Phase 1

## Phase 3: content-stable-fingerprints
- Replace message-based fingerprints with source-line-based via fingerprintIssue()
- Files: all src/runners/*.ts, src/utils/collections.ts (new groupBy)
- Depends on: Phase 2

## Phase 4: snapshot-consistency
- Snapshot step stores relative paths, uses same fingerprint pipeline
- Files: src/steps/snapshot-step.ts
- Depends on: Phase 3
