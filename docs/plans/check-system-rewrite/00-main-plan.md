# Check System Rewrite — Main Plan

## Status: IN PROGRESS

## Problem

The AST-based policy engine (PR #104) works correctly but has a structural flaw:
**flag combination explosion.** Every short/long flag variant requires a separate rule.

- `rm -r -f` needs 4 rules (all permutations of `-r`/`--recursive` × `-f`/`--force`)
- `git push --force` needs 2 rules (`--force`, `-f`)
- `chmod -R 777` needs 2 rules (`-R`, `--recursive`)
- **21 total rules** represent only **~10 distinct concepts**
- **29 glob strings** in `DANGEROUS_DENY_GLOBS` are manually maintained alongside

Adding a new dangerous command means: write every flag variant as a separate rule,
then manually add matching glob patterns. Easy to miss variants, hard to audit.

## Solution

Three-phase refactoring:

| Phase | Name | What | Result |
|-------|------|------|--------|
| 1 | Flag Aliases | `hasFlag()` with alias map + engine integration | Engine matches `-r` when rule says `--recursive` |
| 2 | Rule Groups | Split flat array into domain groups, collapse rules | 21→11 rules, 6 group files, globs co-located |
| 3 | Config Toggling | `disabled_groups` config field | Users can disable rule groups without forking |

## Dependency Graph

```
Phase 1 (flag aliases)  ←  Phase 2 (rule groups + collapse)  ←  Phase 3 (config toggling)
```

Each phase is a separate PR targeting `main`. Each is independently mergeable
(later phases implement earlier phases' changes in their worktree).

## Sub-Plans

| File | Phase | Scope |
|------|-------|-------|
| `01-flag-aliases.md` | 1 | Flag alias module + engine integration |
| `02-rule-groups.md` | 2 | RuleGroup type + domain files + rule collapse |
| `03-config-toggling.md` | 3 | Config schema + ruleset filtering + generator |

## Invariants Across All Phases

- `COMMAND_RULES` export preserved (backward compat)
- `DANGEROUS_DENY_GLOBS` export preserved (same 29 entries, derived from groups in Phase 2+)
- All existing tests pass unchanged (regression safety)
- `isDangerous()` API unchanged
- Hook entry points unchanged (dangerous-cmd, protect-configs, protect-reads)
- `buildRuleSet()` signature unchanged
- No `any`, no `!`, no barrel files, `import type` for types, max 200 lines
