# ADR-001: Centralized check module with declarative rules

**Status**: Accepted
**Date**: 2026-03-14

## Context

The hook system had three separate files with duplicated parsing logic:

- `dangerous-cmd.ts` / `dangerous-patterns.ts` — string-based tokenization via `shell-quote`
- `protect-configs.ts` — regex matching against bash command string (not file path)
- No read protection hook

Each hook was an island. Adding a new rule required touching multiple files. The
`shell-quote` tokenizer could not handle quoted strings, combined flags, or inline scripts.

## Decision

Create `src/check/` as a dedicated module that owns all hook policy:

1. **Single evaluate function** — `evaluate(event: ToolEvent, ruleset: RuleSet)` is the
   only entry point. All hooks call it.

2. **Declarative rules** — `CommandRule[]` and `PathRule[]` in `rules/` files. Rules are
   data, not imperative code. Adding a new rule = adding one builder call.

3. **AST-based command parsing** — replace `shell-quote` with `@questi0nm4rk/shell-ast`
   (wraps `mvdan/sh` via WASM). Handles quoted strings, combined flags, pipes, redirects,
   inline scripts, sudo unwrapping correctly.

4. **`ask` by default** — all rules default to `{ decision: "ask" }`. Exit 0 +
   `permissionDecision: "ask"` is sent to Claude Code, which prompts the user.
   Hard deny (exit 2) is reserved for unambiguous destructive operations.

5. **Hooks as thin wrappers** — hook files only read input, call evaluate, call toHookOutput.
   No parsing or matching logic in hook files.

## Alternatives Rejected

- **Extend `dangerous-patterns.ts` in place**: Would not fix the Edit/Write path bug in
  `protect-configs.ts`. Would require two different parsers for command vs path events.

- **Regex-based command parser**: Regex cannot correctly parse shell — quoted strings,
  nested substitutions, combined flags all require a real parser. Already burned by this
  with `shell-quote` false positives documented in `hook-bypass-regex-limitations.md`.

- **Per-hook rule arrays**: Keeps logic scattered. Same rule would need to be declared
  twice if it applied to both bash and write events (e.g. protecting `.env` from
  redirect writes AND direct writes).

## Consequences

- New dependency: `@questi0nm4rk/shell-ast` (published by this project)
- WASM parse adds ~2ms cold-start per hook invocation (acceptable for interactive use)
- `shell-quote` removed as dependency
- `dangerous-patterns.ts` deleted after rewrite
- Generator import updated to `@/check/rules/commands`
