# SPEC-012: Hook Binary Resolution

## Status: Draft
## Version: 1.0
## Last Updated: 2026-03-31
## Depends on: SPEC-005 (Hooks), SPEC-009 (Interactive Init)

---

## Problem

Generated `.claude/settings.json` hooks reference `./dist/ai-guardrails` with a
file-existence guard:

```bash
[ ! -f ./dist/ai-guardrails ] && exit 0; ./dist/ai-guardrails hook dangerous-cmd
```

`./dist/ai-guardrails` only exists inside the ai-guardrails development repo. In every
consumer project, the guard evaluates true and the hook silently exits 0 — **all three
PreToolUse hooks (dangerous-cmd, protect-configs, protect-reads) are completely inert**.

The user believes guardrails are active, but they aren't. Silent no-op on a security
hook is worse than a loud failure.

## Solution

Replace the file-existence guard with `command -v` PATH lookup:

```bash
command -v ai-guardrails >/dev/null 2>&1 || exit 0; ai-guardrails hook dangerous-cmd
```

Chose PATH-first resolution because:
- `command -v` is POSIX — works in bash, zsh, sh, dash
- Finds the binary wherever it's installed: global (`~/.local/bin/`,
  `bun add -g`), local (`node_modules/.bin/` if in PATH via npx), or dev
  (`./dist/` if directory is in PATH)
- Single lookup, no priority chain to maintain
- Exit 0 on missing binary is still the right default — projects that haven't
  installed ai-guardrails shouldn't have hook failures

### Design principle: silent exit 0 on unknown state

This spec follows the same principle as SPEC-010 (fresh repo guard): when the
tool cannot be found, the hook exits 0 rather than blocking. Guardrails degrade
gracefully — they never brick the user's workflow. The trade-off: if the binary
is genuinely missing due to a broken install, hooks silently do nothing. This is
acceptable because hooks are a defense layer, not the only check — CI and local
`check` runs catch issues independently.

### Shell compatibility note

`command -v` is specified by POSIX (IEEE 1003.1-2017, §2.9.5). Unlike `which`
(which is not POSIX and has inconsistent behavior across systems), `command -v`
only checks PATH for external commands when used without `-p`. It does not return
functions or aliases in this context because the hook runs in a non-interactive
`sh` subprocess spawned by Claude Code.

---

## Affected Components

| Component | File/Path | Change Type |
|-----------|-----------|-------------|
| Claude settings generator | `src/generators/claude-settings.ts` | modify |
| Claude settings tests | `tests/generators/claude-settings.test.ts` | modify |
| Claude settings snapshot | `tests/generators/__snapshots__/claude-settings.test.ts.snap` | modify |

---

## Acceptance Criteria

1. When `ai-guardrails init` generates `.claude/settings.json`, all hook commands
   use `command -v ai-guardrails` as the guard, not `[ ! -f ./dist/ai-guardrails ]`.
2. When `ai-guardrails` is installed globally and the user is in a consumer project,
   the hooks resolve and execute the binary.
3. When `ai-guardrails` is NOT installed (not in PATH), the hooks exit 0 gracefully
   (no error, no block).
4. The generated hook commands do not contain `./dist/` anywhere.

---

## Implementation Detail

**`src/generators/claude-settings.ts`** — Two constants change (line 32 area):

```typescript
// Before:
const guard = "[ ! -f ./dist/ai-guardrails ] && exit 0";
// Hook commands: `${guard}; ./dist/ai-guardrails hook <name>`

// After:
const guard = "command -v ai-guardrails >/dev/null 2>&1 || exit 0";
const bin = "ai-guardrails";
// Hook commands: `${guard}; ${bin} hook <name>`
```

All three hook entries (lines 44, 53, 62) update from `./dist/ai-guardrails` to `${bin}`:

| Matcher | Command |
|---------|---------|
| `Bash` | `${guard}; ${bin} hook dangerous-cmd` |
| `Edit\|Write\|NotebookEdit` | `${guard}; ${bin} hook protect-configs` |
| `Read` | `${guard}; ${bin} hook protect-reads` |

---

## Edge Cases

| Scenario | Expected Behavior | Priority |
|----------|-------------------|----------|
| Binary installed globally (`~/.local/bin/`) | `command -v` finds it — hook runs | high |
| Binary in `./node_modules/.bin/` with PATH | `command -v` finds it — hook runs | medium |
| Binary not installed at all | `command -v` fails — hook exits 0 silently | high |
| Binary in `./dist/` (dev repo) with `./dist/` in PATH | `command -v` finds it — hook runs | low |
| Multiple versions in PATH | `command -v` returns first match — standard unix behavior | low |
| Shell is not bash (zsh, dash, sh) | `command -v` is POSIX — works everywhere | medium |

---

## Cross-References

- SPEC-005 §Claude Code PreToolUse Hooks — defines the hook installation mechanism.
  **Note:** SPEC-005 shows hook commands using `ai-guardrails hook <name>` without
  the `./dist/` prefix. After this spec, SPEC-005 is accurate — it already shows
  the target state. The generator in `src/generators/claude-settings.ts` is what's
  wrong, not the spec.
- SPEC-009 §claudeSettingsModule — the init module that calls the generator
- SPEC-010 — shares the "silent exit 0 on unknown state" design principle
- GitHub: #181 (bug report)
