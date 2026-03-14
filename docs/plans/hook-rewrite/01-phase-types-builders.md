# Phase 1 — Types + Builders

## Deliverables

Create `src/check/types.ts`, `src/check/builder-cmd.ts`, `src/check/builder-path.ts`.
No runtime logic in this phase — pure type definitions and builder functions only.

## `src/check/types.ts`

```typescript
// Decision the engine returns for each event
export type CheckDecision = "allow" | "ask" | "deny";

// Structured result with reason for ask/deny
export type CheckResult =
  | { decision: "allow" }
  | { decision: "ask"; reason: string }
  | { decision: "deny"; reason: string };

// Normalized tool event — one type per hook
export type ToolEvent =
  | { type: "bash"; command: string }
  | { type: "write"; path: string }
  | { type: "read"; path: string };

// ---- Command rules (bash events) ----

// Matches a specific command call (e.g. "rm" with -r and -f flags)
export interface CallRule {
  kind: "call";
  cmd: string;                  // command name
  flags?: string[];             // all of these flags must be present
  noFlags?: string[];           // none of these flags may be present
  hasDdash?: boolean;           // requires "--" separator in raw args
  decision: CheckDecision;
  reason: string;
}

// Matches a pipe from one command into another (e.g. curl | bash)
export interface PipeRule {
  kind: "pipe";
  from: string[];               // source command names
  into: string[];               // destination command names
  decision: CheckDecision;
  reason: string;
}

// Matches any write redirect in the command (>, >>, >|, &>, &>>)
export interface RedirectRule {
  kind: "redirect";
  pathPattern?: RegExp;         // optional: only match if redirect target matches
  decision: CheckDecision;
  reason: string;
}

// Recurse into inline scripts (bash -c '...', eval '...', exec '...')
export interface RecurseRule {
  kind: "recurse";
  // No additional fields — recurse always applies when applicable
}

export type CommandRule = CallRule | PipeRule | RedirectRule | RecurseRule;

// ---- Path rules (write/read events) ----

export interface PathRule {
  kind: "path";
  event: "write" | "read" | "both";
  pattern: RegExp;              // matched against the file path
  decision: CheckDecision;
  reason: string;
}

// ---- Rule sets ----

export interface RuleSet {
  commandRules: CommandRule[];
  pathRules: PathRule[];
}

// ---- Config ----

export interface HooksConfig {
  managedFiles?: string[];      // extra files to protect from write
  managedPaths?: string[];      // extra path patterns to protect from write
  protectedReadPaths?: string[];// paths to protect from read
}
```

## `src/check/builder-cmd.ts`

```typescript
import type { CallRule, PipeRule, RedirectRule, RecurseRule, CheckDecision } from "@/check/types";

export function callRule(
  cmd: string,
  opts: {
    flags?: string[];
    noFlags?: string[];
    hasDdash?: boolean;
    decision?: CheckDecision;
    reason: string;
  }
): CallRule {
  return { kind: "call", cmd, decision: opts.decision ?? "ask", ...opts };
}

export function pipeRule(
  from: string[],
  into: string[],
  reason: string,
  decision: CheckDecision = "ask"
): PipeRule {
  return { kind: "pipe", from, into, decision, reason };
}

export function redirectRule(
  reason: string,
  opts: { pathPattern?: RegExp; decision?: CheckDecision } = {}
): RedirectRule {
  return { kind: "redirect", decision: opts.decision ?? "ask", reason, ...opts };
}

export function recurseRule(): RecurseRule {
  return { kind: "recurse" };
}
```

## `src/check/builder-path.ts`

```typescript
import type { PathRule, CheckDecision } from "@/check/types";

export function pathRule(
  pattern: RegExp,
  event: "write" | "read" | "both",
  reason: string,
  decision: CheckDecision = "ask"
): PathRule {
  return { kind: "path", pattern, event, decision, reason };
}

export function protectWrite(pattern: RegExp, reason: string): PathRule {
  return pathRule(pattern, "write", reason, "ask");
}

export function protectRead(pattern: RegExp, reason: string): PathRule {
  return pathRule(pattern, "read", reason, "ask");
}
```

## Tests

`tests/check/types.test.ts` — verify builders return correct discriminated shapes:

- `callRule("rm", { flags: ["-r", "-f"], reason: "..." }).kind === "call"`
- `pipeRule(["curl"], ["bash"], "...").kind === "pipe"`
- `protectWrite(/\.env$/, "...").event === "write"`
- `recurseRule().kind === "recurse"`

## Acceptance Criteria

- [ ] `bun run typecheck` passes
- [ ] Builder tests all pass
- [ ] No `any`, no `!`, no barrel files
- [ ] All types exported from their respective files (not re-exported via index)
