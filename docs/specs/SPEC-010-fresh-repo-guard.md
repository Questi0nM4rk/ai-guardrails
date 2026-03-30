# SPEC-010: Fresh Repo Guard for no-commits-to-main

## Status: Draft
## Version: 1.0
## Last Updated: 2026-03-31
## Depends on: SPEC-005 (Hooks), SPEC-009 (Interactive Init)

---

## Problem

`ai-guardrails init` installs a lefthook `no-commits-to-main` rule that blocks all
direct commits to `main`/`master`. On a freshly initialized repo, the first commit
(which contains the guardrails config itself — lefthook.yml, .editorconfig, CI workflow,
etc.) is blocked because there are no other branches to commit to yet.

The user must manually work around this (edit lefthook.yml, create an orphan branch, or
use `--no-verify`) just to land the initial commit. This is the first interaction with
ai-guardrails and it fails — a terrible first-use experience.

## Solution

Add a self-disabling guard to the `no-commits-to-main` lefthook script. The guard
runs `git rev-list --count HEAD` — on a fresh repo with no commits, HEAD doesn't resolve
and the command fails (exit 128). The `|| exit 0` fallback lets the commit through.
Once the first commit exists, `rev-list --count` succeeds and the branch check activates.

Chose self-disabling guard over omitting the rule entirely because:
- The rule stays in lefthook.yml from the start — no second `init --force` needed
- No marker files or state to manage
- The guard is visible and auditable in the YAML
- Behavior is automatic: first commit works, protection kicks in immediately after

### Design principle: silent exit 0 on unknown state

This spec follows the same principle as SPEC-012 (hook binary resolution): when the
guard cannot determine state (git not available, HEAD unresolvable), it exits 0 rather
than blocking. This is deliberate — guardrails should degrade gracefully, not brick the
user's workflow. The trade-off is that broken git state silently disables the guard.

---

## Affected Components

| Component | File/Path | Change Type |
|-----------|-----------|-------------|
| Lefthook generator | `src/generators/lefthook.ts` | modify |
| Lefthook tests | `tests/generators/lefthook.test.ts` | modify |
| Lefthook snapshot | `tests/generators/__snapshots__/lefthook.test.ts.snap` | modify |

---

## Acceptance Criteria

1. When `ai-guardrails init` runs on a repo with zero commits, the generated
   `lefthook.yml` contains `no-commits-to-main` with a guard that allows the
   first commit on `main`.
2. When a repo has at least one commit, the `no-commits-to-main` rule blocks
   direct commits to `main` and `master` (unchanged behavior).
3. When `git rev-list --count HEAD` fails (no commits), the hook exits 0.
4. When `git rev-list --count HEAD` returns >= 1, the hook checks the branch
   name and blocks if on `main`/`master`.

---

## Implementation Detail

Current script (`src/generators/lefthook.ts:88-96`):

```bash
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
  echo "Direct commits to main are not allowed"
  exit 1
fi
```

Updated script:

```bash
git rev-list --count HEAD >/dev/null 2>&1 || exit 0
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
  echo "Direct commits to main are not allowed"
  exit 1
fi
```

Note: On a fresh repo, `git rev-list --count HEAD` exits 128 (HEAD unresolvable).
The `|| exit 0` catches this — the script never reaches the branch check. Once the
first commit exists, `rev-list` succeeds (exit 0) and the branch check runs normally.
There is no intermediate state where `rev-list` returns `"0"` — the command either
succeeds (1+ commits) or fails (0 commits).

The guard is entirely in the shell script — no TypeScript changes beyond the
template string. `renderLefthookYml()` signature is unchanged.

---

## Edge Cases

| Scenario | Expected Behavior | Priority |
|----------|-------------------|----------|
| Repo with 0 commits, committing on `main` | Hook exits 0 — commit allowed | high |
| Repo with 1+ commits, committing on `main` | Hook exits 1 — commit blocked | high |
| Repo with 1+ commits, committing on feature branch | Hook exits 0 — commit allowed | high |
| `git rev-list` not available (ancient git) | `|| exit 0` — hook exits 0 gracefully | low |
| Detached HEAD state | `git rev-parse --abbrev-ref HEAD` returns `HEAD` — not `main`, exits 0 | low |

---

## Cross-References

- SPEC-005 §Lefthook commit hooks — defines the hook installation mechanism.
  **Note:** SPEC-005 shows the pre-guard version of the script. After this spec is
  implemented, SPEC-005 should be updated to reflect the new guard logic.
- SPEC-009 §lefthookModule — the init module that calls `generateLefthookConfig()`
- SPEC-012 — shares the "silent exit 0 on unknown state" design principle
- GitHub: #185 (feature request), #182 (original bug report, closed as duplicate)
