# Phase 2: Test Coverage Gaps

## Context

786 tests pass but 7 steps and 9 generators have no unit tests. Steps are partially
covered by Gherkin features but lack isolated unit tests. Generators have snapshot
tests via Gherkin but no dedicated generator test files for codespell, editorconfig,
markdownlint, agent-rules, claude-settings, lefthook.

Commands are 14-62 lines and just wire to pipelines — Gherkin E2E covers them.
Not worth adding unit tests for these tiny wrappers.

## Scope

### Step tests (7 files)
1. `detect-languages.ts` (26 lines) — test detection with fakes
2. `load-config.ts` (29 lines) — test config loading with missing/invalid/valid files
3. `report-step.ts` (33 lines) — test SARIF + text output
4. `run-linters.ts` (29 lines) — test linter collection orchestration
5. `setup-agent-instructions.ts` (50 lines) — test file writing
6. `setup-hooks.ts` (37 lines) — test lefthook install + hook writing
7. `validate-configs.ts` (87 lines) — test validation with hash headers, missing files, tampered

### Generator snapshot tests (6 files — biome and ruff already have runner tests)
1. `codespell.ts` (19 lines)
2. `editorconfig.ts` (35 lines)
3. `markdownlint.ts` (24 lines)
4. `agent-rules.ts` (161 lines)
5. `claude-settings.ts` (78 lines)
6. `lefthook.ts` (128 lines)

## Phases (2 parallel)

### Phase A: Step tests (7 test files)
- Independent — can run in parallel with Phase B
- Use FakeFileManager, FakeCommandRunner, FakeConsole
- Each test file follows existing pattern in tests/steps/

### Phase B: Generator snapshot tests (6 test files)
- Independent — can run in parallel with Phase A
- Use `expect(output).toMatchSnapshot()`
- Each test file follows tests/generators/ pattern (biome.test.ts, ruff.test.ts exist as reference)
