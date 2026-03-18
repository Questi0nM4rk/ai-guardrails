# Test Migration to Gherkin — Overnight Plan

## Context

ai-guardrails has 646 tests. 14 are already Gherkin (E2E). The remaining 632
are raw bun:test. We're migrating BEHAVIOR tests to Gherkin feature files
using @questi0nm4rk/feats, keeping UNIT tests (pure functions) as bun:test.

This migration covers the stable parts of the codebase that won't change
in upcoming phases (baseline integration changes runners + check-step, so
those stay as bun:test for now).

## Scope: ~290 tests across 27 files → ~15 feature files

### What moves to Gherkin

| Group | Files | Tests | Feature files |
|-------|-------|-------|---------------|
| Hook tests | 6 | ~99 | 6 |
| Rule engine | 5 | ~76 | 2 |
| Config + generators | 10 | ~85 | 4 |
| Languages + detection | 4 | ~30 | 1 |
| Pipelines + commands | 4 | ~20 | 2 |
| **Total** | **29** | **~310** | **15** |

### What stays as bun:test (pure unit tests)

Runners (12), utils (3), models (3), writers (2), infra (2), config/schema (1),
check/types (1), check/flag-aliases (1) — ~340 tests that test pure functions.

## File structure

```
tests/
  features/                          ← NEW: all .feature files
    hooks/
      dangerous-commands.feature     ← 46 scenarios
      config-protection.feature      ← 7 scenarios
      read-protection.feature        ← 4 scenarios
      suppression-detection.feature  ← 20 scenarios
      allow-comments.feature         ← 10 scenarios
      format-stage.feature           ← 12 scenarios
    check/
      policy-engine.feature          ← 46 scenarios (engine + integration)
      rule-groups.feature            ← 24 scenarios (rules + groups + toggling)
    config/
      config-loading.feature         ← 18 scenarios
      config-generation.feature      ← 40 scenarios (all generators)
    pipeline/
      language-detection.feature     ← 30 scenarios (plugins + detect step)
      check-pipeline.feature         ← 14 scenarios (step + pipeline + command)
      install-pipeline.feature       ← 12 scenarios (step + pipeline + command)
  steps/                             ← NEW: shared step definitions
    hooks.steps.ts                   ← Given command X / Then blocked/allowed
    engine.steps.ts                  ← evaluate() wrapper steps
    config.steps.ts                  ← config loading/merging steps
    generator.steps.ts               ← generator output assertion steps
    language.steps.ts                ← language detection steps
    pipeline.steps.ts                ← pipeline execution steps with fakes
  e2e/                               ← EXISTING: stays as-is
    features/ steps/ fixtures/
  runners/ utils/ models/ ...        ← EXISTING: stays as bun:test
  feature-runner.test.ts             ← NEW: loads all features + runs them
```

## Step definition design

### hooks.steps.ts — shared across all hook features

```gherkin
Given a bash command "{command}"
When evaluated against the default ruleset
Then the decision should be "ask"
Then the decision should be "allow"
Then the result should be null

Given a file "{path}" with content:
  \"\"\"
  {content}
  \"\"\"
When scanned for suppression comments
Then {count} finding(s) should be detected
Then the finding pattern should be "{pattern}"

When the comment is extracted from "{line}" for language "{lang}"
Then the extracted comment should be "{expected}"
```

### engine.steps.ts — policy engine evaluation

```gherkin
Given the default ruleset
Given a ruleset with disabled groups "{groups}"
When I evaluate bash command "{command}"
When I evaluate a write event for path "{path}"
When I evaluate a read event for path "{path}"
Then the decision should be "{decision}"
Then the reason should contain "{text}"
```

### config.steps.ts — config loading

```gherkin
Given a machine config:
  \"\"\"
  {toml}
  \"\"\"
Given a project config:
  \"\"\"
  {toml}
  \"\"\"
When configs are resolved
Then the profile should be "{profile}"
Then the rule "{rule}" should be allowed
Then ignored rules should contain "{rule}"
```

### generator.steps.ts — generator assertions

```gherkin
Given a resolved config with profile "{profile}"
When the "{generator}" generator runs
Then the output should be valid JSON
Then the output should contain "{text}"
Then the output should have a valid hash header
Then the output should match the snapshot
```

### language.steps.ts — language detection

```gherkin
Given a project with file "{path}"
When languages are detected
Then "{language}" should be detected
Then the universal plugin should always be included
```

### pipeline.steps.ts — pipeline execution with fakes

```gherkin
Given a fake project with no lint issues
Given a fake project with {count} lint issue(s)
When the check pipeline runs
Then the result status should be "{status}"
Then the exit code should be {code}
```

## Work units (3 parallel agents)

### Unit 1: Hook feature files + steps

**Creates:**

- `tests/features/hooks/dangerous-commands.feature`
- `tests/features/hooks/config-protection.feature`
- `tests/features/hooks/read-protection.feature`
- `tests/features/hooks/suppression-detection.feature`
- `tests/features/hooks/allow-comments.feature`
- `tests/features/hooks/format-stage.feature`
- `tests/steps/hooks.steps.ts`

**Deletes:**

- `tests/hooks/dangerous-cmd.test.ts`
- `tests/hooks/protect-configs.test.ts`
- `tests/hooks/protect-reads.test.ts`
- `tests/hooks/suppress-comments.test.ts`
- `tests/hooks/allow-comment.test.ts`
- `tests/hooks/format-stage.test.ts`

**Key pattern:** dangerous-commands.feature uses Scenario Outline with Examples
table for the ~37 parameterized commands. suppress-comments uses parameterized
language/pattern tests.

### Unit 2: Rule engine + config feature files + steps

**Creates:**

- `tests/features/check/policy-engine.feature`
- `tests/features/check/rule-groups.feature`
- `tests/features/config/config-loading.feature`
- `tests/features/config/config-generation.feature`
- `tests/steps/engine.steps.ts`
- `tests/steps/config.steps.ts`
- `tests/steps/generator.steps.ts`

**Deletes:**

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

**Key pattern:** policy-engine.feature has Scenario Outline with BLOCKED and
SAFE command lists. config-generation.feature covers all 5 generators.
config-loading uses DocStrings for TOML input.

### Unit 3: Language + pipeline feature files + steps

**Creates:**

- `tests/features/pipeline/language-detection.feature`
- `tests/features/pipeline/check-pipeline.feature`
- `tests/features/pipeline/install-pipeline.feature`
- `tests/steps/language.steps.ts`
- `tests/steps/pipeline.steps.ts`

**Deletes:**

- `tests/languages/python.test.ts`
- `tests/languages/typescript.test.ts`
- `tests/languages/registry.test.ts`
- `tests/steps/detect-languages.test.ts`
- `tests/pipelines/check.test.ts`
- `tests/pipelines/install.test.ts`
- `tests/commands/check.test.ts`
- `tests/commands/install.test.ts`

**Key pattern:** language-detection uses Scenario Outline with language name +
marker file. Pipeline tests use fake infrastructure (FakeFileManager, etc.)
exposed via step definitions.

### Shared: Feature runner

**Creates:**

- `tests/feature-runner.test.ts` — loads ALL feature files from `tests/features/`
  and runs them via feats. Single entry point.

```typescript
import { loadFeatures, runFeatures } from "@questi0nm4rk/feats";
import "./steps/hooks.steps";
import "./steps/engine.steps";
import "./steps/config.steps";
import "./steps/generator.steps";
import "./steps/language.steps";
import "./steps/pipeline.steps";

const features = loadFeatures("tests/features/**/*.feature");
runFeatures(features);
```

## Snapshot tests note

Generator tests currently use `toMatchSnapshot()`. In Gherkin, snapshots
don't have a direct equivalent. Options:

1. Keep generator snapshot tests as bun:test alongside the feature tests
2. Use `Then the output should match the snapshot` step that internally
   calls `expect().toMatchSnapshot()` from bun:test

Option 2 is cleaner — the step definition wraps the snapshot assertion.
The snapshot files stay in `tests/generators/__snapshots__/`.

## Verification

For each unit:

1. `bun test` — all tests pass (same count ± new scenarios)
2. `bun run typecheck` — clean
3. `bun run lint` — clean
4. Old test files deleted, new feature files exist
5. No behavior coverage lost (same scenarios, different format)

## Worker instructions

Each agent:

1. Read the existing test files being migrated
2. Create the .feature files with equivalent scenarios
3. Create the step definition files
4. Update feature-runner.test.ts with imports
5. Delete the old test files
6. Run `bun test` — verify same coverage
7. Run simplify on changes
8. Commit, push, create PR targeting `feat/test-migration`
