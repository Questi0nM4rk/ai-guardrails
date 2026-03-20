# Phase 5: Comprehensive Test Scenarios (depends on phases 1-4)

## Depends On
Phases 1, 2, 3, 4 must all be merged first.

## Task
Create ~95 new test scenarios across 6 feature files covering all bugfixes:

### A. generator-language-filtering.feature (~30 scenarios)
Every single-language project skips wrong generators. Scenario Outlines for all combos.

### B. language-detection-ignore.feature (~30 scenarios)
Every ignored directory for every language. Marker file overrides. DEFAULT_IGNORE assertions.

### C. ci-workflow.feature (~15 scenarios)
CI workflow content, structure, step ordering, hashFiles, YAML validity.

### D. no-console-detection.feature (~20 scenarios)
Every project type: bin, browser frameworks, mixed, server, minimal, none.

### E. bug-fixes.feature (E2E, ~15 scenarios)
Binary against fixtures: correct configs present/absent per language.

### F. regression-prevention.feature (~10 scenarios)
Explicit regression tests for each bug number.

### New step definition files
1. `tests/steps/generator-filtering.steps.ts`
2. `tests/steps/ci-workflow.steps.ts`
3. `tests/steps/no-console.steps.ts`

### Existing step files to extend
1. `tests/steps/language.steps.ts` — ignore path assertions
2. `tests/e2e/steps/init.steps.ts` — file absence assertions
3. `tests/e2e/steps/project.steps.ts` — node_modules fixture

## Acceptance Criteria
- All ~95 new scenarios pass
- All existing 627 tests still pass
- `bun run typecheck` clean
- `bun run lint` clean
- `bun run build && ./dist/ai-guardrails check` self-dogfood passes
