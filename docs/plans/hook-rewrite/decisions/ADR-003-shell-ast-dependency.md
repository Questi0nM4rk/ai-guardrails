# ADR-003: Use `@questi0nm4rk/shell-ast` as shell parser

**Status**: Accepted
**Date**: 2026-03-14

## Context

Hook checking requires correct shell parsing. Previous `shell-quote` tokenizer had
documented deficiencies (see `docs/bugs/hook-bypass-regex-limitations.md`):

- Cannot handle quoted arguments (`bash -c 'rm -rf /tmp'`)
- Cannot split combined short flags (`-rf` → `["-r", "-f"]`)
- Cannot detect pipes or redirects structurally

## Decision

Use `@questi0nm4rk/shell-ast@0.1.0` — a WASM package wrapping `mvdan/sh` Go parser,
exposing full shell AST as TypeScript discriminated unions.

API used:

- `parse(command)` → `File` AST (async, WASM)
- `findCalls(ast)` → `CallExprNode[]` in execution order (traverses pipes, sequences)
- `walk(ast, visitor)` → visits all AST nodes by type name
- `wordToLit(word)` → extracts `Lit` node value (null for quoted/complex)
- `unwrapCall(call)` → resolves sudo/doas, splits combined flags, returns `ResolvedCall`

Package is published to npm under the `@questi0nm4rk` scope.
Source: `/home/qs_m4rk/Projects/ai-guardrails-ast` (sister project).

## Alternatives Rejected

- **`shell-quote`**: Too limited — already replaced in the ast sister project.
- **`node-shell-parser`**: Unmaintained, no TypeScript types.
- **Custom regex parser**: Cannot correctly parse shell. Documented as a class of
  problems in `hook-bypass-regex-limitations.md`.
- **`bash-parser`**: Node.js only, not Bun-compatible, no WASM option.

## Consequences

- WASM initialization adds ~2ms to first hook invocation (negligible)
- Shell AST is the source of truth — no regex fallbacks
- `shell-quote` removed as a dependency
- The sister project `ai-guardrails-ast` is now a dependency of `ai-guardrails`
- Breaking changes to `@questi0nm4rk/shell-ast` require coordinated updates here
