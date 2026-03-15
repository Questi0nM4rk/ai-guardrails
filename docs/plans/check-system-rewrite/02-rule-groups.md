# Phase 2 — Rule Groups + Rule Collapse

## Scope

Split the flat `COMMAND_RULES` array into named `RuleGroup` objects organized by domain.
Collapse duplicate rules (leveraging flag aliases from Phase 1). Co-locate `DANGEROUS_DENY_GLOBS`
with each group. Delete the monolithic `commands.ts` file.

**Prerequisite:** Phase 1 (flag aliases) must be implemented in this worktree for collapsed
rules to function. Include `flag-aliases.ts` and the engine.ts change in this worktree.

## Files

| Action | File | Description |
|--------|------|-------------|
| NEW | `src/check/flag-aliases.ts` | Copy from Phase 1 (needed for collapsed rules) |
| NEW | `src/check/rules/rm.ts` | `RM_GROUP: RuleGroup` — 1 rule |
| NEW | `src/check/rules/git-push.ts` | `GIT_PUSH_GROUP: RuleGroup` — 1 rule |
| NEW | `src/check/rules/git-destructive.ts` | `GIT_DESTRUCTIVE_GROUP: RuleGroup` — 4 rules |
| NEW | `src/check/rules/git-workflow.ts` | `GIT_WORKFLOW_GROUP: RuleGroup` — 2 rules |
| NEW | `src/check/rules/chmod.ts` | `CHMOD_GROUP: RuleGroup` — 2 rules |
| NEW | `src/check/rules/remote-exec.ts` | `REMOTE_EXEC_GROUP: RuleGroup` — 1 pipe rule |
| NEW | `src/check/rules/groups.ts` | Aggregator: `ALL_RULE_GROUPS`, `collectCommandRules`, `collectDenyGlobs` |
| NEW | `tests/check/flag-aliases.test.ts` | Copy from Phase 1 |
| NEW | `tests/check/rules/groups.test.ts` | Tests for group aggregation |
| MODIFIED | `src/check/types.ts` | Add `RuleGroup` interface |
| MODIFIED | `src/check/engine.ts` | Use `hasFlag`/`expandFlags` (same as Phase 1) |
| MODIFIED | `src/check/ruleset.ts` | Import from `groups.ts` instead of `commands.ts` |
| MODIFIED | `tests/check/rules.test.ts` | Test group-based structure |
| MODIFIED | `tests/check/integration.test.ts` | Add alias-coverage test cases |
| MODIFIED | `tests/hooks/dangerous-cmd.test.ts` | Verify mixed-flag scenarios |
| MODIFIED | `tests/generators/claude-settings.test.ts` | Update snapshot |
| DELETED | `src/check/rules/commands.ts` | Replaced by group files + `groups.ts` |

## Implementation

### RuleGroup type (`src/check/types.ts`)

```typescript
export interface RuleGroup {
  readonly id: string;
  readonly label: string;
  readonly commandRules: readonly CommandRule[];
  readonly denyGlobs: readonly string[];
}
```

### Group file example (`src/check/rules/rm.ts`)

```typescript
import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const RM_GROUP: RuleGroup = {
  id: "destructive-rm",
  label: "Destructive rm commands",
  commandRules: [
    callRule("rm", {
      flags: ["-r", "-f"],
      reason: "rm with recursive and force flags",
    }),
  ],
  denyGlobs: [
    "Bash(rm -rf *)",
    "Bash(rm -fr *)",
    "Bash(sudo rm -rf*)",
    "Bash(sudo rm -fr*)",
  ],
};
```

### Rule collapse map

| Group | Before (commands.ts) | After (group file) | Why |
|-------|---------------------|---------------------|-----|
| rm | 4 rules: `-r -f`, `--recursive --force`, `--recursive -f`, `-r --force` | 1 rule: `flags: ["-r", "-f"]` | hasFlag resolves aliases |
| git push | 2: `--force`, `-f` | 1: `flags: ["--force"]` | -f alias of --force |
| git clean | 2: `-f`, `--force` | 1: `flags: ["-f"]` | --force alias of -f |
| git commit | 2: `--no-verify`, `-n` | 1: `flags: ["--no-verify"]` | -n alias of --no-verify |
| git branch | 3: `-D`, `--delete --force`, `-d --force` | 1: `flags: ["--delete", "--force"]` | -D expanded by expandFlags, -d alias of --delete |
| chmod | 4: `-R 777`, `--recursive 777`, `-R a+rwx`, `--recursive a+rwx` | 2: `flags: ["-R"], args: ["777"]` and `flags: ["-R"], args: ["a+rwx"]` | -R alias of --recursive |

### Aggregator (`src/check/rules/groups.ts`)

```typescript
import { RM_GROUP } from "@/check/rules/rm";
import { GIT_PUSH_GROUP } from "@/check/rules/git-push";
// ... other imports

export const ALL_RULE_GROUPS: readonly RuleGroup[] = [
  RM_GROUP, GIT_PUSH_GROUP, GIT_DESTRUCTIVE_GROUP,
  GIT_WORKFLOW_GROUP, CHMOD_GROUP, REMOTE_EXEC_GROUP,
];

export function collectCommandRules(groups: readonly RuleGroup[]): CommandRule[] {
  return groups.flatMap((g) => [...g.commandRules]);
}

export function collectDenyGlobs(groups: readonly RuleGroup[]): string[] {
  return groups.flatMap((g) => [...g.denyGlobs]);
}

// Backward compatibility exports
export const COMMAND_RULES: CommandRule[] = collectCommandRules(ALL_RULE_GROUPS);
export const DANGEROUS_DENY_GLOBS: string[] = collectDenyGlobs(ALL_RULE_GROUPS);
```

### Ruleset change (`src/check/ruleset.ts`)

```typescript
// Before:
import { COMMAND_RULES } from "@/check/rules/commands";

// After:
import { recurseRule } from "@/check/builder-cmd";
import { ALL_RULE_GROUPS, collectCommandRules } from "@/check/rules/groups";

export function buildRuleSet(config: HooksConfig): RuleSet {
  const commandRules: CommandRule[] = [
    recurseRule(),  // cross-cutting, always active
    ...collectCommandRules(ALL_RULE_GROUPS),
  ];
  // ... path rules unchanged
}
```

### Pipe glob helper (`src/check/rules/remote-exec.ts`)

```typescript
function pipeDenyGlobs(from: readonly string[], into: readonly string[]): string[] {
  const globs: string[] = [];
  for (const f of from) {
    for (const i of into) {
      globs.push(`Bash(${f} * | ${i})`);
    }
  }
  return globs;
}
```

## Behavior Definitions

| Scenario | Expected | Why |
|----------|----------|-----|
| `rm --recursive --force /path` | ask | Matched by `rm` rule with `flags: ["-r", "-f"]` via aliases |
| `rm -r --force /path` | ask | Same rule, -r exact match, --force alias of -f |
| `git branch -D my-branch` | ask | `-D` expanded to `--delete --force` by expandFlags |
| `git push -f` without `--force-with-lease` | ask | `-f` alias of `--force` |
| `git push --force --force-with-lease` | allow | `noFlags: ["--force-with-lease"]` blocks |
| `COMMAND_RULES.length` | 12 (1 recurse + 11 call/pipe) | Down from 22 |
| `DANGEROUS_DENY_GLOBS.length` | 29 | Same as before, derived from groups |
| `collectDenyGlobs([RM_GROUP])` | 4 globs | Only rm globs |

## Definition of Done

- [ ] `RuleGroup` interface in `types.ts`
- [ ] 6 domain group files created with collapsed rules
- [ ] `groups.ts` aggregates groups and exports backward-compat `COMMAND_RULES` + `DANGEROUS_DENY_GLOBS`
- [ ] `commands.ts` deleted
- [ ] `ruleset.ts` uses `ALL_RULE_GROUPS` + injects `recurseRule()`
- [ ] All existing tests pass (regression)
- [ ] New tests: group structure, aggregation, glob collection
- [ ] Integration tests: alias-matched commands caught (rm --recursive --force, git branch -D)
- [ ] `DANGEROUS_DENY_GLOBS` has exactly 29 entries (same as before)
- [ ] `bun test && bun run typecheck && bun run lint && bun run build` all pass
- [ ] E2e: binary catches `rm --recursive --force` via alias matching

## E2E Test Recipe

```bash
bun test && bun run typecheck && bun run lint && bun run build

# Alias-matched: rm --recursive --force (only rule is flags: [-r, -f])
echo '{"session_id":"x","transcript_path":"/tmp/t","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm --recursive --force /tmp/test"}}' \
  | ./dist/ai-guardrails hook dangerous-cmd
# Expected: exit 0, stdout contains "permissionDecision":"ask"

# expandFlags: git branch -D (expanded to --delete --force)
echo '{"session_id":"x","transcript_path":"/tmp/t","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git branch -D my-branch"}}' \
  | ./dist/ai-guardrails hook dangerous-cmd
# Expected: exit 0, stdout contains "permissionDecision":"ask"

# Safe: git push --force --force-with-lease (should NOT be caught)
echo '{"session_id":"x","transcript_path":"/tmp/t","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push --force --force-with-lease"}}' \
  | ./dist/ai-guardrails hook dangerous-cmd
# Expected: exit 0, no stdout
```

## Worker Instructions

```
After you finish implementing the change:
1. **Simplify** — Invoke the `Skill` tool with `skill: "simplify"`.
2. **Run unit tests** — `bun test`. Fix failures.
3. **Test end-to-end** — Run the e2e recipe above.
4. **Commit and push** — `feat(check): rule groups with alias-aware rule collapse`
5. **Create PR** — `gh pr create --base main --title "feat(check): rule groups with alias-aware rule collapse"`
6. **Report** — `PR: <url>`
```
