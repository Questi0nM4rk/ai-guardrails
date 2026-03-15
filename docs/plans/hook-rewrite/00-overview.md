# Hook Rewrite — Overview

## Goal

Replace the string-based hook checking system with a proper declarative policy engine
backed by real shell AST parsing (`@questi0nm4rk/shell-ast`). Every hook decision flows
through a single `evaluate(event, ruleset)` function. No regex hacks, no string splitting.

## Problem Statement

Current hooks have several structural defects:

1. **`dangerous-patterns.ts`** uses `shell-quote` string tokenization — cannot handle
   quoted args, combined short flags (`-rf`), or inline scripts (`bash -c '...'`).

2. **`protect-configs.ts`** never checks `file_path` for Edit/Write events — it only
   runs the regex against the Bash command string, which means it misses all direct file
   writes from the Edit/Write tools.

3. No protect-reads hook exists — sensitive files can be read freely.

4. All decisions are hard-deny (exit 2). Claude Code's `ask` mode (exit 0 +
   `permissionDecision: "ask"`) is not used, so the session AI permission mode is ignored.

5. Hook logic is scattered — each hook is an island with its own parsing and decision logic.

## Solution: `src/check/` Module

A layered check module with three concerns:

```
src/check/
  types.ts          — CheckDecision, CheckResult, ToolEvent, rule types
  builder-cmd.ts    — callRule(), pipeRule(), redirectRule(), recurseRule()
  builder-path.ts   — pathRule(), protectWrite(), protectRead()
  engine.ts         — evaluate(event, ruleset): Promise<CheckResult>
  ruleset.ts        — buildRuleSet(config), loadHookConfig()
  output.ts         — toHookOutput(result, label): never
  rules/
    commands.ts     — COMMAND_RULES, DANGEROUS_DENY_GLOBS
    paths.ts        — DEFAULT_PATH_RULES, DEFAULT_MANAGED_FILES
```

Hook files become thin wrappers:

```
src/hooks/
  dangerous-cmd.ts  — reads input, calls evaluate({ type: "bash", command }), toHookOutput
  protect-configs.ts — reads input, calls evaluate({ type: "write", path }), toHookOutput
  protect-reads.ts  — reads input, calls evaluate({ type: "read", path }), toHookOutput
```

## Decision Semantics

| Decision | Hook exit | Effect |
|----------|-----------|--------|
| `allow`  | exit 0 (no JSON) | Tool proceeds |
| `ask`    | exit 0 + `{"permissionDecision":"ask"}` | Claude asks user |
| `deny`   | exit 2 + message | Tool blocked |

**All rules default to `ask` for now.** Deny is reserved for unambiguous destructive
operations where user confirmation would add no value.

## Scope

- New `@questi0nm4rk/shell-ast` package (already published as 0.1.0)
- Full rewrite of `dangerous-patterns.ts` using AST
- Fix `protect-configs.ts` to check `file_path` for Edit/Write
- New `protect-reads.ts` hook
- New `runner.ts` `ask()` function
- Extended config schema: `[hooks]` section
- Updated `claude-settings.ts` generator (add Read hook)

## Out of Scope

- The linter pipeline (`runners/`, `steps/`, `pipelines/`) — untouched
- CLI commands other than `hook` subcommands
- Baseline, fingerprinting — separate deferred issues

## Phases

| Phase | Content | Branch target |
|-------|---------|---------------|
| 1 | Types + builders | feat/hook-rewrite |
| 2 | Engine (evaluate) | feat/hook-rewrite |
| 3 | Rule declarations | feat/hook-rewrite |
| 4 | Hook rewrites + protect-reads | feat/hook-rewrite |
| 5 | Generators + full test suite | feat/hook-rewrite |

Each phase is implemented in a parallel worktree agent, reviewed, then merged to
`feat/hook-rewrite`. `feat/hook-rewrite` targets `main` via final PR.

## Branch Protection

`feat/hook-rewrite` must have the same protection rules as `main`:

- Require PR before merge
- cc-review auto-review on open
- No direct push
