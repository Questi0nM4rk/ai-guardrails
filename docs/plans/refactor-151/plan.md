# Refactor #151 — Remove 34 `as` type casts + #152 abstract process.stdin

## Problem

34 `as` casts violate the NON-NEGOTIABLE no-cast rule. Also `process.stdin`
direct access in 2 step files violates the infra injection rule.

## Grouping

Combining #151 and #152 since both are refactors touching similar areas.

## Cast Categories and Fixes

### Category A: Runner JSON type guards (15 casts) — Zod schemas

Files: biome.ts (3), pyright.ts (5), ruff.ts (3), clippy.ts (1), shellcheck.ts (1),
       run-linters.ts (1), check-step.ts (1)

These parse external tool JSON output. The proper fix is Zod schemas at the
boundary — each runner already has interface types, just need matching schemas.

Pattern:
```typescript
// Before (as cast):
const v = value as RuffItem & { location: unknown };

// After (Zod):
const RuffItemSchema = z.object({
  code: z.string(),
  filename: z.string(),
  location: z.object({ row: z.number(), column: z.number() }),
  message: z.string(),
});
const items = z.array(RuffItemSchema).parse(parsed);
```

For `run-linters.ts:23` and `check-step.ts:42`: `[] as LintIssue[]` — just
use explicit type annotation: `const empty: LintIssue[] = []; return empty;`

### Category B: CLI/Pipeline flag casting (3 casts)

- `src/cli.ts:25` — `program.opts() as { projectDir?: string }`
  Fix: Use Commander's typed opts via `@commander-js/extra-typings`
  (already a dependency — check if `.opts<T>()` is available)

- `src/pipelines/check.ts:46` — `ctx.flags.format as ReportFormat`
  Fix: Validate with Zod: `ReportFormatSchema.parse(ctx.flags.format)`

- `src/pipelines/init.ts:15` — `(PROFILES as readonly string[]).includes(value)`
  Fix: Use a type guard: `function isProfile(v: unknown): v is Profile { return PROFILES.includes(v as Profile); }`
  Actually — just use `PROFILES.some(p => p === value)` which avoids the cast.

### Category C: Config parsing (1 cast)

- `src/config/loader.ts:27` — `parseToml(text) as Record<string, unknown>`
  Fix: smol-toml's `parse()` returns `Record<string, unknown>` already.
  Check return type — may just need a type annotation, not a cast.

### Category D: Utility casts (3 casts)

- `src/check/engine-helpers.ts:172` — `(parts as string[]).join(" ")`
  Fix: Type the array properly upstream or use `.filter((p): p is string => typeof p === "string")`

- `src/check/ruleset.ts:82` — `(e as { code: unknown }).code === "ENOENT"`
  Fix: Same `isEnoent()` pattern already in file-manager.ts — extract to shared util

- `src/steps/setup-agent-instructions.ts:32` — `Object.keys(tools) as Array<keyof T>`
  Fix: Use a typed entries helper or type-narrow the keys

### Category E: process.stdin abstraction (#152)

- `src/steps/install-prerequisites.ts:69,76`
- `src/pipelines/init.ts:19,120`

Fix: Add `readline` factory to PipelineContext:
```typescript
interface PipelineContext {
  // existing...
  createReadline?: () => readline.Interface;
  isTTY?: boolean;
}
```

Steps use `ctx.createReadline?.()` instead of `createInterface({ input: process.stdin })`.
Tests inject a fake readline. Default in production: real stdin.

## Phases (3 sequential)

### Phase 1: Runner Zod schemas (15 casts, largest batch)
- Add Zod schemas for biome, pyright, ruff, clippy, shellcheck output
- Replace type guard casts with `.parse()` / `.safeParse()`
- Fix `[] as LintIssue[]` with typed variables
- Files: 7 runner files

### Phase 2: CLI/config/utility casts (7 casts)
- Commander typed opts
- Zod for flag validation
- isEnoent shared util
- Typed Object.keys
- Files: cli.ts, check.ts, init.ts, loader.ts, engine-helpers.ts, ruleset.ts, setup-agent-instructions.ts

### Phase 3: process.stdin abstraction (#152)
- Add createReadline + isTTY to PipelineContext
- Update install-prerequisites and init pipeline
- Add FakeReadline for tests
- Files: types.ts, install-prerequisites.ts, init.ts, context.ts

## Acceptance

- `grep -rn ' as ' src/ --include='*.ts' | grep -v 'as const' | grep -v 'import.*as'` returns 0 real casts
- All 896+ tests pass
- typecheck + lint clean
- process.stdin not referenced in src/steps/ or src/pipelines/
