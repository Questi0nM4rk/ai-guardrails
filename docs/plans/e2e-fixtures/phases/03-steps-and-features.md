# Phase 3: Step Definitions and Feature Files

## Task

Write BDD step definitions using @questi0nm4rk/feats and Gherkin feature files
that exercise the init and check pipelines against the fixture projects.

## Dependencies

- Phase 1 (fixture files exist)
- Phase 2 (config merge strategy exists)

## Files to create

```
tests/e2e/
  features/
    init-fresh.feature
    init-existing.feature
    check.feature
    monorepo.feature
  steps/
    project.steps.ts
    init.steps.ts
    check.steps.ts
  runner.test.ts
```

## Step definitions

### project.steps.ts

- `Given a bare "{lang}" fixture project` — setupFixture(lang + "/bare")
- `Given a preconfigured "{lang}" fixture project` — setupFixture(lang + "/preconfigured")
- `Given a monorepo combining bare "{a}" and bare "{b}"` — composeFixtures
- `Given a monorepo with {int} random bare languages` — rng.sample + composeFixtures

### init.steps.ts

- `When I run ai-guardrails init` — exec binary with --non-interactive
- `When I run ai-guardrails init with merge strategy` — exec with --config-strategy=merge
- `When I run ai-guardrails init with replace strategy` — --config-strategy=replace
- `When I run ai-guardrails init with skip strategy` — --config-strategy=skip
- `Given ai-guardrails has been initialized` — run init as setup step

### check.steps.ts

- `When I run ai-guardrails check` — exec binary with --project-dir
- `Then the output should contain at least {int} violation` — parse output
- `Then all detected languages should have configs` — check per-lang config files

## Acceptance criteria

- `bun test tests/e2e/runner.test.ts` runs without errors
- Feature scenarios for installed tools pass
- Scenarios for missing tools skip gracefully (not fail)
- Monorepo scenarios compose fixtures correctly
