# Phase 2: Engine + Config + Generator Tests → Gherkin

## Task

Migrate rule engine tests (5 files) and config/generator tests (6 files) to
Gherkin feature files + step definitions.

## Files to create

- `tests/features/check/policy-engine.feature`
- `tests/features/check/rule-groups.feature`
- `tests/features/config/config-loading.feature`
- `tests/features/config/config-generation.feature`
- `tests/steps/engine.steps.ts`
- `tests/steps/config.steps.ts`
- `tests/steps/generator.steps.ts`

## Files to delete

- `tests/check/engine.test.ts`
- `tests/check/integration.test.ts`
- `tests/check/rules.test.ts`
- `tests/check/rule-groups.test.ts`
- `tests/check/ruleset-toggling.test.ts`
- `tests/config/loader.test.ts`
- `tests/generators/biome.test.ts`
- `tests/generators/ruff.test.ts`
- `tests/generators/lefthook.test.ts`
- `tests/generators/claude-settings.test.ts`
- `tests/generators/agent-rules.test.ts`

## Acceptance criteria

- All ~161 test scenarios pass as Gherkin
- Old test files deleted
- Snapshot tests preserved (step wraps toMatchSnapshot)
- `bun test` passes
- `bun run typecheck` clean
