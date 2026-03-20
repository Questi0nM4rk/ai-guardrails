# Phase 2: Language-Gate Generators (#123)

## Files
- `src/generators/types.ts` — add `readonly languages?: readonly string[]`
- `src/generators/ruff.ts` — add `languages: ["python"]`
- `src/generators/biome.ts` — add `languages: ["typescript"]`
- `src/steps/generate-configs.ts` — filter generators by active language IDs

## Task
Generators should only run when their target language is detected. Add an optional
`languages` field to the Generator type. If set, the generator only runs when at
least one of its languages is in the detected set. If unset, it always runs (universal).

Filter logic in generate-configs step:
```typescript
const activeIds = new Set(languages.map(l => l.id));
const applicable = ALL_GENERATORS.filter(g =>
  g.languages === undefined || g.languages.some(id => activeIds.has(id))
);
```

## Acceptance Criteria
- Python-only project: ruff.toml YES, biome.jsonc NO
- TypeScript-only: biome.jsonc YES, ruff.toml NO
- Rust/Go/Shell/C++/Lua/dotnet-only: neither ruff nor biome
- Polyglot Python+TS: both
- Universal generators (editorconfig, codespell, lefthook, etc.) always run
- All existing tests pass + typecheck + lint clean
