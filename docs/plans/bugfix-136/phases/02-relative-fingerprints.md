# Phase 2: Relative paths in fingerprints

## Task
Change all 12 runners to use project-relative paths when computing fingerprints. Keep LintIssue.file absolute for display.

## Files
All 12 runners in `src/runners/`:
biome.ts, ruff.ts, pyright.ts, tsc.ts, clippy.ts, golangci-lint.ts, shellcheck.ts, shfmt.ts, selene.ts, clang-tidy.ts, codespell.ts, markdownlint.ts

## Pattern
Each runner: add `import { relative } from "node:path"`, then:
```typescript
const relFile = relative(opts.projectDir, absoluteFile);
const fingerprint = computeFingerprint({ rule, file: relFile, ... });
// LintIssue.file stays absolute
```

## Acceptance Criteria
- Fingerprints use relative paths (verify by inspecting computed fingerprint inputs)
- Same issue at /home/dev/project/src/main.ts and /ci/work/src/main.ts → same fingerprint
- Snapshot then check → all issues classified as "existing"
- All existing runner tests pass (update expected fingerprints)
- typecheck + lint clean
