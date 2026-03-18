# Phase 3: Language + Pipeline + Command Tests → Gherkin

## Task

Migrate language plugin tests (4 files) and pipeline/command tests (4 files)
to Gherkin feature files + step definitions.

## Files to create

- `tests/features/pipeline/language-detection.feature`
- `tests/features/pipeline/check-pipeline.feature`
- `tests/features/pipeline/install-pipeline.feature`
- `tests/steps/language.steps.ts`
- `tests/steps/pipeline.steps.ts`

## Files to delete

- `tests/languages/python.test.ts`
- `tests/languages/typescript.test.ts`
- `tests/languages/registry.test.ts`
- `tests/steps/detect-languages.test.ts`
- `tests/pipelines/check.test.ts`
- `tests/pipelines/install.test.ts`
- `tests/commands/check.test.ts`
- `tests/commands/install.test.ts`

## Acceptance criteria

- All ~50 test scenarios pass as Gherkin
- Old test files deleted
- `bun test` passes
- `bun run typecheck` clean
