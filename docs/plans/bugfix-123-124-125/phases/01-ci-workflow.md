# Phase 1: CI Workflow Fix (#125, #126)

## Files
- `src/steps/setup-ci.ts`

## Task
Add conditional `bun install --frozen-lockfile` with hashFiles guard to the generated CI workflow.

The install step must:
1. Come after setup-bun and before the check step
2. Have an `if` condition using `hashFiles('bun.lock', 'bun.lockb', 'package.json')`
3. Use `bun install --frozen-lockfile`

## Acceptance Criteria
- CI workflow YAML contains `bun install --frozen-lockfile`
- Install step has hashFiles condition
- Step ordering: checkout → setup-bun → install → check
- All existing tests pass
- `bun run typecheck` clean
- `bun run lint` clean
