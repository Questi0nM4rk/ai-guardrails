# Phase 2 — Engine

## Deliverables

Create `src/check/engine.ts` and `src/check/output.ts`.

This is the core runtime: `evaluate(event, ruleset)` walks the shell AST, matches rules,
and returns a `CheckResult`. `toHookOutput` converts that result to a hook exit.

## Dependency

Requires `@questi0nm4rk/shell-ast` to be added to `package.json`:

```bash
bun add @questi0nm4rk/shell-ast
```

## `src/check/engine.ts`

```typescript
import { findCalls, parse, walk, wordToLit } from "@questi0nm4rk/shell-ast";
import type { ResolvedCall, Word } from "@questi0nm4rk/shell-ast";
import { unwrapCall } from "@questi0nm4rk/shell-ast/semantic";
import type { CheckResult, CommandRule, PathRule, RuleSet, ToolEvent } from "@/check/types";

export async function evaluate(event: ToolEvent, ruleset: RuleSet): Promise<CheckResult> {
  if (event.type === "bash") {
    return evaluateCommand(event.command, ruleset.commandRules);
  }
  return evaluatePath(event.path, event.type, ruleset.pathRules);
}
```

### Bash event evaluation

```typescript
async function evaluateCommand(
  command: string,
  rules: CommandRule[]
): Promise<CheckResult>
```

Algorithm:

1. Parse command with `parse(command)`. On parse error → `{ decision: "allow" }`.
2. `calls = findCalls(ast)` — all calls in order (pipes appear as adjacent pairs).
3. For each call `i`:
   a. `resolved = unwrapCall(calls[i])` — unwraps sudo/doas.
   b. Check **PipeRule**: if `PIPE_SHELLS.has(resolved.cmd)` and `i > 0`, check if
      previous call is in `rule.from`.
   c. Check **RecurseRule**: if cmd is in `INLINE_SHELL_CMDS`, extract inline script
      via `extractInlineScript(resolved)` and recurse.
   d. Check **CallRule**: match `cmd`, `flags`, `noFlags`, `hasDdash`.
   e. Check **RedirectRule**: use `walk(ast, { Stmt(node) {...} })` to find write redirects
      (`>`, `>>`, `>|`, `&>`, `&>>`). If `pathPattern` set, match redirect target.
4. First non-allow result wins. Return `{ decision: "allow" }` if no rule matched.

### Redirect detection

```typescript
import { walk } from "@questi0nm4rk/shell-ast";
import type { File } from "@questi0nm4rk/shell-ast";

const WRITE_OPS = new Set([">", ">>", ">|", "&>", "&>>"]);

function hasWriteRedirect(ast: File, pathPattern?: RegExp): boolean {
  let found = false;
  walk(ast, {
    Stmt(node) {
      for (const redir of node.redirs) {
        if (!WRITE_OPS.has(redir.op)) continue;
        if (!pathPattern) { found = true; return; }
        const target = wordToLit(redir.hdoc ?? redir.word);
        if (target !== null && pathPattern.test(target)) { found = true; return; }
      }
    },
  });
  return found;
}
```

### Path event evaluation

```typescript
function evaluatePath(
  path: string,
  eventType: "write" | "read",
  rules: PathRule[]
): CheckResult
```

Iterate rules in order. For each PathRule:

- If `rule.event` is `"both"` or matches `eventType`, and `rule.pattern.test(path)`:
  - Return `{ decision: rule.decision, reason: rule.reason }`.
Return `{ decision: "allow" }` if no match.

## `src/check/output.ts`

```typescript
import type { CheckResult } from "@/check/types";

export function toHookOutput(result: CheckResult, label: string): never {
  if (result.decision === "allow") {
    process.exit(0);
  }
  if (result.decision === "ask") {
    process.stdout.write(
      JSON.stringify({ permissionDecision: "ask", reason: `[${label}] ${result.reason}` })
    );
    process.exit(0);
  }
  // deny
  process.stderr.write(`[${label}] ${result.reason}\n`);
  process.exit(2);
}
```

## Helpers (internal to engine.ts)

```typescript
const PIPE_SHELLS = new Set(["bash", "sh", "dash", "zsh", "ksh", "csh", "tcsh", "fish"]);
const INLINE_SHELL_CMDS = new Set(["bash", "sh", "dash", "zsh", "ksh", "eval", "exec"]);

function wordToStr(word: Word): string | null {
  // Handles Lit, SglQuoted, DblQuoted(Lit) — see dangerous-patterns.ts in ast branch
}

function extractInlineScript(resolved: ResolvedCall): string | null {
  // Same logic as ast branch: eval/exec → args[1], bash/sh → -c next
}
```

## Tests

`tests/check/engine.test.ts`:

- Bash events — blocked patterns (mirrors dangerous-cmd.test.ts):
  - `rm -rf /path` → ask
  - `git push --force` → ask
  - `curl ... | bash` → ask
  - `bash -c 'rm -rf /tmp'` → ask (recursive)
  - `sudo rm -rf /var/log` → ask (unwrapped)

- Bash events — safe patterns (must return allow):
  - `rm foo.txt` → allow
  - `git push --force-with-lease` → allow
  - `git commit -m "rm -rf node_modules"` → allow (commit message not inspected)
  - `echo "rm -rf /"` → allow

- Write events:
  - `.env` path → ask (path rule)
  - `src/main.ts` → allow

- Read events:
  - `~/.ssh/id_rsa` → ask
  - `README.md` → allow

## Acceptance Criteria

- [ ] `bun run typecheck` passes
- [ ] All engine tests pass
- [ ] Redirect detection works for `>` and `>>`
- [ ] Inline script recursion works for `bash -c '...'` and `eval '...'`
- [ ] `toHookOutput("ask")` exits 0 with valid JSON
- [ ] `toHookOutput("deny")` exits 2
- [ ] `toHookOutput("allow")` exits 0 with no output
