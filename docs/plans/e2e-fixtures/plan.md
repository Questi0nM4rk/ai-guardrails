# E2E Fixture Test System for ai-guardrails

## Context

ai-guardrails has 589 unit tests but never runs `init` or `check` on a real project.
This builds the E2E test infrastructure using `@questi0nm4rk/feats`.

Each language has TWO fixture variants:

- **bare/** — no existing lang config (tests fresh generation)
- **preconfigured/** — has existing tsconfig.json/ruff.toml/etc (tests merge/replace flow)

This also requires implementing a **config merge strategy** in the init pipeline:
when existing configs are found, prompt the user to merge, replace, or skip.

## Structure

```
tests/e2e/
  features/
    init-fresh.feature        ← init on bare projects
    init-existing.feature     ← init when configs already exist (merge/replace)
    check.feature             ← check catches violations
    monorepo.feature          ← random multi-lang combination
  steps/
    project.steps.ts          ← fixture setup + monorepo composition
    init.steps.ts             ← init execution + config assertions
    check.steps.ts            ← check execution + violation assertions
  fixtures/
    typescript/
      bare/                   ← package.json + src/main.ts (no tsconfig/biome)
      preconfigured/          ← same + existing tsconfig.json with custom settings
    python/
      bare/                   ← pyproject.toml + src/main.py
      preconfigured/          ← same + existing ruff.toml with custom rules
    rust/
      bare/                   ← Cargo.toml + src/lib.rs
      preconfigured/          ← same + existing clippy.toml
    go/
      bare/                   ← go.mod + main.go
      preconfigured/          ← same + existing .golangci.yml
    shell/
      bare/                   ← script.sh
      preconfigured/          ← same + existing .shellcheckrc
    cpp/
      bare/                   ← CMakeLists.txt + src/main.cpp
      preconfigured/          ← same + existing .clang-tidy
    lua/
      bare/                   ← main.lua
      preconfigured/          ← same + existing selene.toml
    universal/
      bare/                   ← README.md + notes.txt (typos/markdown violations)
  runner.test.ts
```

## Config merge strategy (new init feature)

When `ai-guardrails init` finds an existing lang config, three options:

### Option 1: Git-based merge

1. Init a temp git repo in the project dir (or use existing)
2. Stage + commit the existing config as "base"
3. Create branch, write our generated config, commit as "ours"
4. Merge — if clean, done. If conflict, present to user.
5. Clean up temp git state if we created it

### Option 2: Simple prompt

```
Found existing tsconfig.json. What to do?
  [m] Merge (keep your settings, add ours)
  [r] Replace (overwrite with ai-guardrails defaults)
  [s] Skip (leave as-is)
```

For merge without git: deep-merge JSON/TOML objects — our settings win on conflict,
user's extra settings preserved. This is simpler and works without git.

### Option 3: Copy to .ai-guardrails/

Copy existing config to `.ai-guardrails/original/tsconfig.json` as backup,
then write our version. User can manually reconcile.

**Recommended: Option 2 (simple prompt + deep merge).** Git merge is elegant but
heavyweight for config files. Deep merge handles 90% of cases:

```typescript
// For JSON configs (tsconfig, biome):
const merged = deepMerge(existingConfig, generatedConfig);
// generatedConfig values win on key collision
// existingConfig's extra keys preserved

// For TOML configs (ruff):
const merged = deepMerge(existingToml, generatedToml);
```

## Fixture variants — what each tests

### bare/ (no existing config)

- Init creates all configs from scratch
- No merge prompts
- Tests the default generation path

### preconfigured/ (has existing config)

- Init detects existing configs
- Prompts user for merge/replace/skip
- Tests that user settings are preserved in merge mode
- Tests that replace mode overwrites cleanly
- Tests that skip mode leaves files untouched

Example for TypeScript preconfigured:

```json
// existing tsconfig.json with user customizations
{
  "compilerOptions": {
    "target": "ES2020",           // user's choice
    "strict": false,              // user chose loose
    "baseUrl": "./src",           // user's path alias
    "outDir": "./dist"            // user's build output
  },
  "include": ["src/**/*"]
}
```

After merge with ai-guardrails pedantic profile:

```json
{
  "compilerOptions": {
    "target": "ES2020",                    // preserved
    "strict": true,                         // upgraded by guardrails
    "exactOptionalPropertyTypes": true,     // added by guardrails
    "noUncheckedIndexedAccess": true,       // added by guardrails
    "baseUrl": "./src",                     // preserved
    "outDir": "./dist"                      // preserved
  },
  "include": ["src/**/*"]                   // preserved
}
```

## Feature files

### init-fresh.feature

```gherkin
Feature: Fresh project initialization

  Scenario Outline: Init on bare <lang> project
    Given a bare "<lang>" fixture project
    When I run ai-guardrails init --non-interactive
    Then the exit code should be 0
    And ".lefthook.yml" should exist
    And ".claude/settings.json" should exist

    Examples:
      | lang       |
      | typescript |
      | python     |
      | rust       |
      | go         |
      | shell      |
      | cpp        |
      | lua        |
```

### init-existing.feature

```gherkin
Feature: Init with existing configs

  Scenario: Merge preserves user settings in tsconfig
    Given a preconfigured "typescript" fixture project
    When I run ai-guardrails init with merge strategy
    Then "tsconfig.json" compilerOptions.strict should be true
    And "tsconfig.json" compilerOptions.baseUrl should be "./src"
    And "tsconfig.json" compilerOptions.exactOptionalPropertyTypes should be true

  Scenario: Replace overwrites existing config
    Given a preconfigured "python" fixture project
    When I run ai-guardrails init with replace strategy
    Then "ruff.toml" should match the generated default

  Scenario: Skip leaves existing config untouched
    Given a preconfigured "typescript" fixture project
    When I run ai-guardrails init with skip strategy
    Then "tsconfig.json" compilerOptions.strict should be false
```

### check.feature

```gherkin
Feature: Lint checking

  Scenario Outline: Check catches violations in <lang>
    Given a bare "<lang>" fixture project
    And ai-guardrails has been initialized
    When I run ai-guardrails check
    Then the exit code should not be 0
    And the output should contain at least 1 violation

    Examples:
      | lang       |
      | typescript |
      | python     |
```

### monorepo.feature

```gherkin
Feature: Multi-language monorepo

  Scenario: Two languages in monorepo
    Given a monorepo combining bare "typescript" and bare "python"
    When I run ai-guardrails init --non-interactive
    Then "biome.jsonc" should exist
    And "ruff.toml" should exist

  Scenario: Random 3-language monorepo
    Given a monorepo with 3 random bare languages
    When I run ai-guardrails init --non-interactive
    Then all detected languages should have configs
```

## Implementation phases

### Phase 1: Fixture files (static, no code)

Create all 8 language fixtures with bare/ and preconfigured/ variants.
Each has detection markers, minimal code, and intentional violations.

### Phase 2: Config merge feature in init pipeline

Implement the merge/replace/skip strategy in `src/pipelines/init.ts`:

- Detect existing configs before generation
- Prompt user (or use --merge/--replace/--skip flags for non-interactive)
- Deep merge for JSON/TOML configs
- Backup existing to `.ai-guardrails/original/` before replace

### Phase 3: Step definitions + feature files

Write all steps using feats API. Write the 4 feature files.
Wire up runner.test.ts.

### Phase 4: Binary validation

Build binary, run full E2E suite, fix what breaks.

## Key decisions

- **bare vs preconfigured naming:** `fixtures/typescript/bare/` and
  `fixtures/typescript/preconfigured/` — step definitions select variant
- **Deep merge over git merge:** simpler, no temp repo needed, handles JSON/TOML
- **--non-interactive flag:** required for CI/test use, skips all prompts
  with sensible defaults (merge strategy for preconfigured, fresh gen for bare)
- **Tool availability:** tests skip gracefully if linter not installed
- **Binary path:** tests run compiled `./dist/ai-guardrails`, not source
