# SPEC-007: Implementation Guide

## Status: Draft

---

## Build Setup

```bash
# Runtime
bun >= 1.2.0

# Install deps
bun install

# Dev
bun run dev          # watch mode
bun test             # run all tests
bun test --watch     # watch tests
bun run build        # compile single binary

# Lint/format (dogfooded — ai-guardrails checks itself)
bun run lint         # biome check src/
bun run typecheck    # tsc --noEmit
```

### `package.json` structure

```json
{
  "name": "ai-guardrails",
  "version": "3.0.0",
  "type": "module",
  "bin": { "ai-guardrails": "./dist/ai-guardrails" },
  "scripts": {
    "dev": "bun run --watch src/cli.ts",
    "build": "bun build src/cli.ts --compile --bytecode --production --outfile dist/ai-guardrails",
    "test": "bun test",
    "lint": "biome check src/ tests/",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@commander-js/extra-typings": "^13.0.0",
    "zod": "^3.24.0",
    "minimatch": "^10.0.0"
  },
  "devDependencies": {
    "@biomejs/biome": "^1.9.0",
    "typescript": "^5.8.0",
    "@types/bun": "latest",
    "@types/minimatch": "^5.1.0"
  }
}
```

### `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "Bundler",
    "moduleResolution": "Bundler",
    "lib": ["ESNext"],
    "types": ["bun-types"],
    "strict": true,
    "exactOptionalPropertyTypes": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "verbatimModuleSyntax": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src", "tests"]
}
```

---

## Implementation Order

### Phase 1: Foundation (no external tool calls)

**Goal:** Core types + config system + fakes compiling and tested.

1. `models/lint-issue.ts` + tests
2. `models/baseline.ts` + tests
3. `models/step-result.ts`
4. `models/audit-record.ts`
5. `infra/` interfaces + real implementations + fakes
6. `config/schema.ts` (Zod schemas) + tests
7. `config/loader.ts` (merge logic) + tests
8. `utils/hash.ts` + tests
9. `utils/fingerprint.ts` + tests
10. `hooks/allow-comment.ts` (parser only) + tests

**Deliverable:** All core types tested. No CLI yet.

---

### Phase 2: Runners (linter output parsers)

**Goal:** Each runner parses its linter's output format correctly.

For each runner:
1. Add fixture file to `tests/fixtures/<runner>-output.*`
2. Write unit tests for the parser
3. Implement parser in `runners/<runner>.ts`
4. Implement `generateConfig()` — rendered from template + config values

**Order:** ruff → mypy → shellcheck → biome → clippy → go-vet → staticcheck
→ clang-tidy → luacheck → codespell → markdownlint

**Deliverable:** All runners parse their fixture output correctly.

---

### Phase 3: Language plugins + generators

**Goal:** Language detection working. Config generation working.

1. `languages/types.ts` + `languages/registry.ts`
2. Each language plugin (detection logic is simple — most are one file existence check)
3. `generators/types.ts` + `generators/registry.ts`
4. Each generator (template rendering + hash header)
5. Snapshot tests for generated output

**Deliverable:** `detect-languages` step + `generate-configs` step tested.

---

### Phase 4: Pipelines + steps

**Goal:** Each pipeline runs end-to-end with fakes.

1. `pipelines/types.ts`
2. Individual steps (each step has its own test file)
3. Pipeline orchestrators (integration tests with FakeCommandRunner + FakeFileManager)

**Step implementation order:**
- `detect-languages`
- `load-config`
- `generate-configs`
- `validate-configs` (for `generate --check`)
- `snapshot-step`
- `check-step`
- `status-step`
- `report-step`
- `setup-hooks`
- `setup-ci`
- `setup-agent-instructions`
- `generate-agent-rules`

---

### Phase 5: CLI + hooks

**Goal:** Binary compiles and all commands work end-to-end.

1. `cli.ts` — wire all commands via Commander
2. `commands/` — one file per command
3. `hooks/` — all hook implementations
4. `writers/sarif.ts` + `writers/text.ts`
5. Shell completion generation

**Deliverable:** `bun build` produces working binary. Manual smoke test on
ai-guardrails own repo.

---

### Phase 6: Dogfood

1. Run `ai-guardrails install` on dev machine
2. Run `ai-guardrails init` on ai-guardrails repo itself
3. Verify `ai-guardrails generate --check` passes
4. Verify `ai-guardrails check` passes (capture snapshot first)
5. Verify lefthook hooks fire correctly on a test commit
6. Fix any issues found

---

## Testing Conventions

### Fakes

```typescript
// tests/fakes/fake-file-manager.ts
export class FakeFileManager implements FileManager {
  private files = new Map<string, string>();
  written: Array<[string, string]> = [];

  seed(path: string, content: string) {
    this.files.set(path, content);
  }

  async readText(path: string) {
    const content = this.files.get(path);
    if (!content) throw new Error(`File not found: ${path}`);
    return content;
  }

  async writeText(path: string, content: string) {
    this.files.set(path, content);
    this.written.push([path, content]);
  }
  // ... etc
}

// tests/fakes/fake-command-runner.ts
export class FakeCommandRunner implements CommandRunner {
  calls: string[][] = [];
  private responses = new Map<string, RunResult>();

  register(args: string[], response: RunResult) {
    this.responses.set(args.join(" "), response);
  }

  async run(args: string[]) {
    this.calls.push(args);
    return this.responses.get(args.join(" ")) ?? { stdout: "", stderr: "", exitCode: 0 };
  }
}
```

### Test file structure

```typescript
// tests/runners/ruff.test.ts
import { describe, expect, test } from "bun:test";
import { parseRuffOutput } from "@/runners/ruff";
import ruffFixture from "../fixtures/ruff-output.json";

describe("ruff runner", () => {
  test("parses JSON output into LintIssue[]", () => {
    const issues = parseRuffOutput(JSON.stringify(ruffFixture), mockConfig);
    expect(issues).toHaveLength(3);
    expect(issues[0]!.rule).toBe("E501");
    expect(issues[0]!.linter).toBe("ruff");
  });

  test("suppresses issues matching ResolvedConfig.isAllowed", () => { ... });
  test("emits AI001 for bare allow comments", () => { ... });
  test("returns [] for empty stdout", () => { ... });
});
```

### Snapshot tests for generators

```typescript
// tests/generators/ruff.test.ts
import { test, expect } from "bun:test";
import { ruffGenerator } from "@/generators/ruff";

test("ruff generator output matches snapshot", () => {
  const output = ruffGenerator.generate(standardConfig, "/fake/project");
  expect(output).toMatchSnapshot();
});
```

---

## Code Quality Standards

This project dogfoods itself. The `biome.json` and any other generated configs
it uses must be managed by `ai-guardrails` itself.

- **No `any`** — `unknown` + Zod parsing at boundaries
- **No `!` non-null assertions** — handle `undefined` explicitly
- **`exactOptionalPropertyTypes`** — no `x: string | undefined` used as optional
- **All async/await** — no callback patterns
- **`as const` for literal objects** — prevents accidental widening
- **Discriminated unions** over nullable fields
- **Pure functions** in `utils/` — no side effects, no I/O
- **No barrel files** — explicit named imports only

---

## Skills + MCPs

| Task | Agent/Skill/MCP |
|------|----------------|
| Deep research on a library or API | `Explore` subagent (keeps main context clean) |
| TypeScript, Bun, Zod, Commander docs | `context7` MCP |
| Implementing a feature TDD | `tdd` skill |
| Reviewing written code | `code-review` skill |
| Running parallel feature branches | `EnterWorktree` tool |
| Checking for past failures | `reflections` skill |
| Creating PRs / checking CI | GitHub MCP |
| Python session computation | `mcp__code-execution__run_python` |

**Rule:** Main architect context is never polluted with deep research results.
All file exploration, library research, and multi-step searches go through
subagents. Main context tracks decisions and connections only.
