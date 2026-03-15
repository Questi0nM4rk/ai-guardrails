# Phase 3 — Config-Driven Group Toggling

## Scope

Add a `disabled_groups` config field so users can disable specific rule groups without
forking the source. Wire it through the config schema, ruleset builder, and generator.

**Prerequisite:** Phase 2 (rule groups) must be implemented in this worktree. This means
also including Phase 1 (flag aliases) since Phase 2 depends on it. Include all prior
phase changes in the worktree before implementing Phase 3's additions.

## Files

| Action | File | Description |
|--------|------|-------------|
| INCLUDE | All Phase 1 + Phase 2 files | Prerequisite implementation |
| MODIFIED | `src/check/types.ts` | Add `disabledGroups` to `HooksConfig` |
| MODIFIED | `src/config/schema.ts` | Add `disabled_groups` to `HooksConfigSchema` |
| MODIFIED | `src/check/ruleset.ts` | Filter groups by `disabledGroups`, use `collectDenyGlobs` |
| MODIFIED | `src/generators/claude-settings.ts` | Use `collectDenyGlobs(activeGroups)` |
| MODIFIED | `src/check/ruleset.ts` | Update `loadHookConfig()` to map `disabled_groups` |
| NEW | `tests/check/ruleset-toggling.test.ts` | Tests for group enable/disable |
| MODIFIED | `tests/generators/claude-settings.test.ts` | Snapshot update for dynamic globs |

## Implementation

### HooksConfig addition (`src/check/types.ts`)

```typescript
export interface HooksConfig {
  managedFiles?: string[];
  managedPaths?: string[];
  protectedReadPaths?: string[];
  disabledGroups?: string[];  // NEW
}
```

### Schema addition (`src/config/schema.ts`)

```typescript
const HooksConfigSchema = z.object({
  managed_files: z.array(z.string()).optional(),
  managed_paths: z.array(z.string()).optional(),
  protected_read_paths: z.array(z.string()).optional(),
  disabled_groups: z.array(z.string()).optional(),  // NEW
});
```

### Ruleset filtering (`src/check/ruleset.ts`)

```typescript
import { recurseRule } from "@/check/builder-cmd";
import { ALL_RULE_GROUPS, collectCommandRules } from "@/check/rules/groups";

export function buildRuleSet(config: HooksConfig): RuleSet {
  const disabled = new Set(config.disabledGroups ?? []);
  const activeGroups = ALL_RULE_GROUPS.filter((g) => !disabled.has(g.id));

  const commandRules: CommandRule[] = [
    recurseRule(),  // always active — cross-cutting engine behavior
    ...collectCommandRules(activeGroups),
  ];

  // ... path rules unchanged
}
```

### loadHookConfig mapping (`src/check/ruleset.ts`)

```typescript
return {
  ...(hooks.managed_files !== undefined && { managedFiles: hooks.managed_files }),
  ...(hooks.managed_paths !== undefined && { managedPaths: hooks.managed_paths }),
  ...(hooks.protected_read_paths !== undefined && {
    protectedReadPaths: hooks.protected_read_paths,
  }),
  ...(hooks.disabled_groups !== undefined && {
    disabledGroups: hooks.disabled_groups,         // NEW
  }),
};
```

### Generator update (`src/generators/claude-settings.ts`)

```typescript
// Before:
import { DANGEROUS_DENY_GLOBS } from "@/check/rules/commands";

// After:
import { ALL_RULE_GROUPS, collectDenyGlobs } from "@/check/rules/groups";

// Inside the generator function:
// Use ALL groups for deny globs (generator doesn't respect disabled_groups —
// the settings.json deny list is a static safety net independent of config).
const denyGlobs = collectDenyGlobs(ALL_RULE_GROUPS);
```

**Design decision:** The generator uses ALL groups (not filtered by disabled_groups).
Rationale: `settings.json` deny globs are a static first-layer defense. If a user
disables a group in the hook config, the hook engine respects that, but the static
deny patterns in Claude's permission system remain as a safety net. Users who truly
want to bypass a group can remove globs from settings.json manually.

## Behavior Definitions

| Config | Effect on hooks | Effect on generator |
|--------|-----------------|---------------------|
| `disabled_groups = []` (default) | All groups active | All 29 globs generated |
| `disabled_groups = ["chmod-world-writable"]` | chmod rules skipped, all others active | All 29 globs still generated |
| `disabled_groups = ["destructive-rm", "chmod-world-writable"]` | rm + chmod skipped | All 29 globs still generated |
| No `[hooks]` section | All groups active (empty HooksConfig) | All 29 globs generated |

### buildRuleSet behavior with disabled groups

| Input | commandRules count | Expected |
|-------|-------------------|----------|
| `{}` | 12 (1 recurse + 11 domain) | All groups active |
| `{ disabledGroups: ["destructive-rm"] }` | 11 (no rm rule) | rm commands allowed |
| `{ disabledGroups: ["destructive-rm", "chmod-world-writable"] }` | 9 (no rm, no chmod) | Both allowed |
| `{ disabledGroups: ["nonexistent"] }` | 12 | Unknown group name ignored |

### RecurseRule always active

Regardless of disabled_groups, `recurseRule()` is always injected. It's not part of
any group — it's engine behavior (inline script recursion into bash -c, eval, exec).

## Definition of Done

- [ ] `disabledGroups` field on `HooksConfig` in `types.ts`
- [ ] `disabled_groups` in `HooksConfigSchema` in `schema.ts`
- [ ] `loadHookConfig()` maps `disabled_groups` → `disabledGroups`
- [ ] `buildRuleSet()` filters groups by `disabledGroups`
- [ ] `recurseRule()` always injected (not in any group)
- [ ] Generator uses `collectDenyGlobs(ALL_RULE_GROUPS)` — always full list
- [ ] Tests: disabled group excluded from commandRules
- [ ] Tests: recurseRule always present
- [ ] Tests: unknown group names ignored
- [ ] Tests: generator output unchanged (always all globs)
- [ ] `bun test && bun run typecheck && bun run lint && bun run build` all pass
- [ ] E2e: with `disabled_groups = ["destructive-rm"]`, `rm -rf /` passes through

## E2E Test Recipe

```bash
bun test && bun run typecheck && bun run lint && bun run build

# Default: rm -rf caught
echo '{"session_id":"x","transcript_path":"/tmp/t","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/test"}}' \
  | ./dist/ai-guardrails hook dangerous-cmd
# Expected: exit 0, stdout contains "permissionDecision":"ask"

# With config disabling rm group: need a config.toml in CWD
# (Unit test covers this via buildRuleSet({ disabledGroups: ["destructive-rm"] }))
# Binary e2e for config toggling is optional — unit tests are authoritative.
```

## Worker Instructions

```
After you finish implementing the change:
1. **Simplify** — Invoke the `Skill` tool with `skill: "simplify"`.
2. **Run unit tests** — `bun test`. Fix failures.
3. **Test end-to-end** — Run the e2e recipe above.
4. **Commit and push** — `feat(check): config-driven rule group toggling`
5. **Create PR** — `gh pr create --base main --title "feat(check): config-driven rule group toggling"`
6. **Report** — `PR: <url>`
```
