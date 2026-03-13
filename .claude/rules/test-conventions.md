# Test Conventions

## Framework

- `bun:test` — `import { describe, expect, test } from "bun:test"`
- No Jest, no Vitest — Bun's built-in test runner only

## Structure

- Standalone test functions preferred — no classes unless shared state is needed
- One test file per source module: `src/runners/ruff.ts` → `tests/runners/ruff.test.ts`
- Fixtures in `tests/fixtures/` — static linter output samples (JSON/text)
- Fakes in `tests/fakes/` — `FakeFileManager`, `FakeCommandRunner`, `FakeConsole`

## Fakes not Mocks

- Use fake implementations — in-memory fakes over `vi.mock()` / `spyOn`
- `FakeFileManager` — in-memory file tree, `seed(path, content)` for setup
- `FakeCommandRunner` — register canned responses per args tuple
- `FakeConsole` — captures messages for assertion

## Naming

- `test_<function>_<scenario>_<expected>` pattern
- Examples:
  - `test parseRuffOutput returns empty array for empty stdout`
  - `test filterIssues removes issues matching isAllowed`

## Snapshot Tests

- Generators are snapshot-tested: `expect(output).toMatchSnapshot()`
- Update snapshots explicitly: `bun test --update-snapshots`
- Snapshot changes require review — they represent intentional output changes

## Coverage

- Target 85%+ coverage on all modules
- No coverage suppression without documented justification
