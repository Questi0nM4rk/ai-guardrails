# TypeScript Source Conventions

## Types

- No `any` — use `unknown` + Zod parsing at system boundaries
- No `!` non-null assertions — handle `undefined` explicitly with early returns or defaults
- `exactOptionalPropertyTypes` is on — no `x: string | undefined` used as optional
- Use discriminated unions over nullable fields
- `as const` for literal objects — prevents accidental widening
- No barrel files (`index.ts`) — explicit named imports only

## Imports

- `verbatimModuleSyntax` is on — use `import type` for type-only imports
- Path alias `@/*` maps to `src/*` — use it for all cross-module imports

## Classes vs Interfaces

- No `extends` (except `Error` subclasses) — composition only
- `implements` interfaces, never extend them
- Prefer plain objects with interface types over classes for singletons

## Error Handling

- No `catch (e: any)` — use `catch (e: unknown)` + type narrowing
- Never swallow errors silently
- Domain errors: return `StepResult { status: "error" }` — don't throw

## Async

- All async/await — no callback patterns, no `.then()` chains
- `Promise.all` for concurrent independent operations within a step
- Steps themselves run sequentially (pipeline enforces this)

## Infrastructure Rule

- Never `import` from `infra/` directly in domain code (runners, generators, steps)
- All I/O comes from `PipelineContext` — FileManager, CommandRunner, Console

## Module Size

- Max 200 lines per file — split if larger
- One concern per file — if you need "and" to describe it, split it
