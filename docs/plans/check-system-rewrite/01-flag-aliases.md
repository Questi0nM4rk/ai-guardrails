# Phase 1 — Flag Alias Resolution

## Scope

Create a flag alias system and integrate it into the engine's flag matching logic.
After this phase, the engine matches `-r` when a rule says `--recursive` (and vice versa).

**This phase does NOT collapse rules** — existing duplicate rules stay. The engine
just gains the ability to resolve aliases, which Phase 2 leverages to remove duplicates.

## Files

| Action | File | Description |
|--------|------|-------------|
| NEW | `src/check/flag-aliases.ts` | `FLAG_ALIASES` map, `FLAG_EXPANSIONS` map, `hasFlag()`, `expandFlags()` |
| NEW | `tests/check/flag-aliases.test.ts` | Unit tests for alias resolution |
| MODIFIED | `src/check/engine.ts` | Replace `flags.includes()` with `hasFlag(expandFlags(flags), ...)` |

## Implementation

### `src/check/flag-aliases.ts` (~40 lines)

```typescript
// Bidirectional alias map — each flag lists its equivalents
const FLAG_ALIASES: ReadonlyMap<string, readonly string[]> = new Map([
  ["-r",          ["--recursive"]],
  ["--recursive", ["-r", "-R"]],
  ["-R",          ["--recursive"]],
  ["-f",          ["--force"]],
  ["--force",     ["-f"]],
  ["-d",          ["--delete"]],
  ["--delete",    ["-d"]],
  ["-n",          ["--no-verify"]],
  ["--no-verify", ["-n"]],
]);

// Multi-flag expansions (one flag = multiple canonical flags)
const FLAG_EXPANSIONS: ReadonlyMap<string, readonly string[]> = new Map([
  ["-D", ["--delete", "--force"]],  // git branch -D = --delete --force
]);

export function hasFlag(flags: readonly string[], wanted: string): boolean
export function expandFlags(flags: readonly string[]): string[]
```

### `src/check/engine.ts` — 3 lines change (lines 88-92)

```typescript
// Before:
const allFlagsPresent = (rule.flags ?? []).every((f) => flags.includes(f));
const noFlagPresent = (rule.noFlags ?? []).every(
  (f) => !flags.some((flag) => flag === f || flag.startsWith(`${f}=`))
);

// After:
const expanded = expandFlags(flags);
const allFlagsPresent = (rule.flags ?? []).every((f) => hasFlag(expanded, f));
const noFlagPresent = (rule.noFlags ?? []).every((f) => !hasFlag(expanded, f));
```

`hasFlag()` handles `startsWith` for parameterized flags (e.g. `--force-with-lease=refspec`)
internally, so the explicit `startsWith` hack in noFlags is absorbed.

## Behavior Definitions

| Input | Expected | Why |
|-------|----------|-----|
| `hasFlag(["-r", "-f"], "--recursive")` | `true` | `-r` is alias of `--recursive` |
| `hasFlag(["--force"], "-f")` | `true` | `--force` is alias of `-f` |
| `hasFlag(["--verbose"], "-v")` | `false` | `-v` not in alias map (pass-through) |
| `hasFlag(["--force-with-lease=origin/main"], "--force-with-lease")` | `true` | startsWith handling |
| `hasFlag(["--force-with-lease"], "--force")` | `false` | different flag entirely |
| `expandFlags(["-D"])` | `["--delete", "--force"]` | FLAG_EXPANSIONS entry |
| `expandFlags(["-r", "-f"])` | `["-r", "-f"]` | no expansion, pass-through |
| `expandFlags(["-D", "-v"])` | `["--delete", "--force", "-v"]` | expand -D, pass -v |

## Definition of Done

- [ ] `flag-aliases.ts` exports `hasFlag()` and `expandFlags()`
- [ ] `engine.ts` uses `hasFlag`/`expandFlags` instead of `includes`/`startsWith`
- [ ] All **existing** tests pass unchanged (hasFlag is superset of includes)
- [ ] New tests cover: every alias pair, FLAG_EXPANSIONS, parameterized flags, unknown flags
- [ ] `bun test && bun run typecheck && bun run lint` all pass
- [ ] No binary e2e needed (no behavior change for existing rules)

## Test Plan

```typescript
// tests/check/flag-aliases.test.ts
describe("hasFlag", () => {
  test("matches exact flag", ...);
  test("matches short alias for long flag", ...);
  test("matches long alias for short flag", ...);
  test("handles parameterized flag (--force-with-lease=refspec)", ...);
  test("does not match unrelated flags", ...);
  test("does not match --force-with-lease as alias of --force", ...);
});

describe("expandFlags", () => {
  test("expands -D to --delete and --force", ...);
  test("passes through flags without expansions", ...);
  test("handles mixed expanded and non-expanded flags", ...);
});
```

## Worker Instructions

```
After you finish implementing the change:
1. **Simplify** — Invoke the `Skill` tool with `skill: "simplify"`.
2. **Run unit tests** — `bun test`. Fix failures.
3. **Skip e2e** — No behavior change for existing rules.
4. **Commit and push** — `feat(check): add flag alias resolution system`
5. **Create PR** — `gh pr create --base main --title "feat(check): flag alias resolution system"`
6. **Report** — `PR: <url>`
```
