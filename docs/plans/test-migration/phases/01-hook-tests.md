# Phase 1: Hook Tests → Gherkin

## Task

Migrate 6 hook test files to Gherkin feature files + shared step definitions.

## Files to create

- `tests/features/hooks/dangerous-commands.feature`
- `tests/features/hooks/config-protection.feature`
- `tests/features/hooks/read-protection.feature`
- `tests/features/hooks/suppression-detection.feature`
- `tests/features/hooks/allow-comments.feature`
- `tests/features/hooks/format-stage.feature`
- `tests/steps/hooks.steps.ts`
- `tests/feature-runner.test.ts` (shared entry point)

## Files to delete

- `tests/hooks/dangerous-cmd.test.ts`
- `tests/hooks/protect-configs.test.ts`
- `tests/hooks/protect-reads.test.ts`
- `tests/hooks/suppress-comments.test.ts`
- `tests/hooks/allow-comment.test.ts`
- `tests/hooks/format-stage.test.ts`

## Acceptance criteria

- All ~99 hook test scenarios pass as Gherkin
- Old test files deleted
- `bun test` passes with same or higher test count
- `bun run typecheck` clean
- `bun run lint` clean
