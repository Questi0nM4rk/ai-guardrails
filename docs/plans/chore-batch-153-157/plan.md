# Chore Batch: #153, #154, #155, #156, #157

## Scope

5 trivial chores that can be done in a single PR. No code logic changes.

## Items

### #153 — Remove stale TODO in fingerprint.ts

`src/utils/fingerprint.ts:10-18` has a TODO about wiring `fingerprintIssue`
into runners. This was done in PR #143. Remove the stale NOTE/TODO block.

### #154 — Update stale comment in lint-issue.ts

`src/models/lint-issue.ts:27-30` says "All runners currently pass absolute
paths" — fixed in PR #141. Update to reflect current state.

### #155 — Test naming convention

`.claude/rules/test-conventions.md` says `test_<function>_<scenario>_<expected>`
but tests use `"returns X when Y"` style. Update the convention doc to match
reality rather than renaming 100+ tests. The descriptive style is clearer.

### #156 — Mark baseline-fingerprint-gap.md as RESOLVED

`docs/bugs/baseline-fingerprint-gap.md` documents 3 issues all fixed in
PRs #140-144. Add RESOLVED header like the other bug docs.

### #157 — Clean up untracked plan docs

6 completed plan directories in `docs/plans/`. Delete them — the work is
captured in PRs and commit history.

## Single phase

All 5 items in one commit:
- Edit fingerprint.ts (remove TODO)
- Edit lint-issue.ts (update comment)
- Edit test-conventions.md (update naming convention)
- Edit baseline-fingerprint-gap.md (add RESOLVED)
- Delete 6 plan directories
- Commit: `chore: clean up stale comments, docs, and plan artifacts (#153-157)`

## Acceptance

- No stale TODOs referencing completed work
- Bug docs all marked RESOLVED
- No untracked plan directories
- Test convention doc matches actual practice
