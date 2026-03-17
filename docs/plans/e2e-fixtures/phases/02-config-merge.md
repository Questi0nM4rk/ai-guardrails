# Phase 2: Config Merge Strategy

## Task

When `ai-guardrails init` finds existing lang configs, implement merge/replace/skip.

## Files to modify/create

- `src/utils/deep-merge.ts` — NEW: deep merge for JSON/TOML objects
- `src/steps/generate-configs.ts` — MODIFY: detect existing configs, apply merge strategy
- `src/pipelines/init.ts` — MODIFY: add --merge/--replace/--skip flags
- `src/commands/init.ts` — MODIFY: add CLI flags
- `tests/utils/deep-merge.test.ts` — NEW: deep merge unit tests

## Deep merge behavior

```typescript
function deepMerge(existing: Record<string, unknown>, generated: Record<string, unknown>): Record<string, unknown>
```

- generated values WIN on key collision (our rules take precedence)
- existing extra keys PRESERVED (user customizations kept)
- Nested objects merged recursively
- Arrays: generated wins (no array merge — too ambiguous)

## Merge strategy flow

1. Before writing each config file, check if it exists on disk
2. If exists + interactive: prompt merge/replace/skip
3. If exists + non-interactive: use --merge (default), --replace, or --skip flag
4. merge: deepMerge(existing, generated), write result
5. replace: overwrite with generated
6. skip: leave existing, continue

## CLI flags

```
ai-guardrails init --non-interactive --config-strategy merge|replace|skip
```

Default: `merge` (safest — preserves user settings)

## Acceptance criteria

- `deepMerge({a:1, b:2}, {b:3, c:4})` returns `{a:1, b:3, c:4}`
- `deepMerge({nested:{x:1}}, {nested:{y:2}})` returns `{nested:{x:1, y:2}}`
- Init with --config-strategy=merge preserves user's tsconfig target but upgrades strict
- Init with --config-strategy=replace overwrites completely
- Init with --config-strategy=skip leaves existing untouched
- All existing unit tests still pass (no regressions)
