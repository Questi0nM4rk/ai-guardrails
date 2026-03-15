# ADR-002: Default to `ask` instead of hard deny

**Status**: Accepted
**Date**: 2026-03-14

## Context

The current hooks use exit 2 (hard deny) for all blocked commands. This means:

- The AI cannot proceed even when the user would approve the action
- Session permission mode (`--dangerously-skip-permissions` etc.) is ignored
- Users get blocked with no way to override without editing config files

Claude Code supports a third outcome: exit 0 + `{ "permissionDecision": "ask" }`.
This causes Claude Code to surface the decision to the user interactively.

## Decision

All rules in `src/check/rules/` default to `decision: "ask"`. The engine emits
`{ decision: "ask", reason: string }` which `toHookOutput` converts to:

```
exit 0
stdout: {"permissionDecision":"ask","reason":"[label] reason text"}
```

Hard deny (`decision: "deny"`, exit 2) is reserved for cases where:

- The operation is categorically unrecoverable (e.g. `rm -rf /`)
- No legitimate use case exists in the context of AI-assisted coding

For the initial rewrite, everything is `ask`. Specific rules may be upgraded to `deny`
as operational experience accumulates.

## Alternatives Rejected

- **Always deny**: Too aggressive. Blocks legitimate operations. Users work around it
  by disabling hooks entirely, which is worse.

- **Always allow with logging**: No protection. Defeats the purpose.

- **User-configurable per-rule**: Premature. We don't know which rules users want as
  deny vs ask yet. Default to ask, let users promote to deny via config if needed.

## Consequences

- Users see prompts instead of hard blocks for dangerous commands
- Operators can promote specific rules to `deny` via `[hooks]` config in future
- `deny` output path still exists in `toHookOutput` for future use
- The test suite checks for `decision !== "allow"` not `decision === "deny"`
