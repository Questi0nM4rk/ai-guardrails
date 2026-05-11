# ai-guardrails — bug & UX log

Live log captured while integrating ai-guardrails v4.0.0 into hook-kit
(2026-05-11). Maintainer of hook-kit dogfooding the released version
into its own repo. **Reporter paused mid-integration after finding the
following — separate agent is addressing some install bugs in parallel.**

Entries follow: **type** (bug / ux / missing) — **severity** — title, then context.
Bugs are listed roughly in the order discovered.

---

## BUG-001 — high — `ai-guardrails install` runs the full project init pipeline

**Type:** bug (routing / behavior contradicts documentation)
**Severity:** HIGH
**Reproduced in:** v4.0.0 dist binary, fresh cwd at `/home/qs_m4rk/Projects/hook-kit`

`ai-guardrails --help` documents `install` as **"One-time machine setup"**
with only `--upgrade` as an option, and `init` as **"Per-project setup"**
with `--profile`, `--yes`, `--force`, and all the `--no-X` flags.

Observed: invoking `ai-guardrails install` (no args) in a project directory
ran the **entire `init` pipeline** — wrote `.ai-guardrails/config.toml`,
`AGENTS.md`, `lefthook.yml`, `.claude/settings.json`, `ruff.toml`,
`staticcheck.conf`, `.editorconfig`, `.markdownlint.jsonc`, `.codespellrc`,
`.github/workflows/ai-guardrails.yml`, `.github/pull_request_template.md`,
appended to project `CLAUDE.md`, installed lefthook git hooks, and merged
hooks into `~/.claude/settings.json`.

User expectation per the help text: a one-time check for system-level
prereqs (lefthook binary, gitleaks, codespell, etc.) and nothing else. No
project mutation.

**Repro:**
```bash
ai-guardrails --version    # 4.0.0
cd /some/clean/project
ai-guardrails install      # observe full init flow firing
git status                 # shows lefthook.yml, .claude/, .ai-guardrails/, etc.
```

**Suspected cause:** Command routing in `src/cli.ts` may dispatch `install`
to the wrong pipeline, or `install` was meant to delegate to `init` but
got merged into it.

**Fix idea:** Either (a) make `install` actually do machine-level checks
(verify lefthook on PATH, biome on PATH, etc.) without touching the
project, or (b) remove `install` entirely and document `init` as the only
setup command. The current state where `install` silently does `init`'s
work without `--profile`, `--yes`, or any opt-outs is the worst of both.

---

## BUG-002 — high — `install` has no `--profile` flag, defaults to `standard` silently

**Type:** bug (consequence of BUG-001 + missing flag)
**Severity:** HIGH (couples with BUG-001)

Because `install` runs init's pipeline without `init`'s flags, there is
**no way to specify the profile** when invoking `install`. The pipeline
silently uses `standard` even if the user intends `strict` or `minimal`.

Output evidence:
```text
[Profile Selection] Config written with profile=standard
```

User had explicitly intended `--profile strict`. The only way to discover
this happened was to read the post-init `.ai-guardrails/config.toml`.

**Fix idea:** Fix BUG-001. If `install` is to be removed or refactored,
this issue resolves with it.

---

## BUG-003 — high — GitHub repo not detected despite valid SSH remote

**Type:** bug (remote detection)
**Severity:** HIGH

`git remote -v` clearly shows:
```text
origin  git@github.com:Questi0nM4rk/hook-kit.git (fetch)
origin  git@github.com:Questi0nM4rk/hook-kit.git (push)
```

Yet `ai-guardrails install` output:
```text
[CodeRabbit AI Reviewer] No GitHub repo detected — skipping CodeRabbit configuration
[GitHub Branch Protection] No GitHub repo detected — skipping branch protection
[GitHub Protected Branch Patterns] skipped (dependency github-branch-protection did not complete successfully)
```

The detection logic likely only handles HTTPS remotes (`https://github.com/...`)
and fails to parse the `git@github.com:` SSH form, which is the more common
remote format for users with SSH keys configured.

**Repro:**
```bash
cd /any/repo/with/ssh/origin
git remote -v   # shows git@github.com:owner/repo.git
ai-guardrails init --yes   # branch protection skipped
```

**Fix idea:** Parse both `https://github.com/<owner>/<repo>(.git)?` and
`git@github.com:<owner>/<repo>(.git)?` in the remote-detection helper.
Probably a regex needing one extra alternation.

**Impact:** Users with SSH remotes (which is most experienced users) get
silently degraded init — branch protection, CodeRabbit, protected
patterns all skipped without warning the user that detection failed.

---

## BUG-004 — high — Generates `ruff.toml` and `staticcheck.conf` for projects with no Python or Go

**Type:** bug (language detection / over-generation)
**Severity:** HIGH (regression of BUG-005 from `docs/bugs/fresh-install-bugs.md`?)

In `/home/qs_m4rk/Projects/hook-kit` — a pure TypeScript/Bun project with
no `.py`, `.pyi`, `pyproject.toml`, `requirements*.txt`, `uv.lock`, `.go`,
`go.mod`, or `go.sum` files — `ai-guardrails install` generated:

```text
[Ruff Config] ruff.toml written
[Staticcheck Config] staticcheck.conf written
```

This appears to be a regression of `BUG-005` documented in
`docs/bugs/fresh-install-bugs.md` ("Generator produces biome.json for
Python-only projects"), which was marked **Fixed** in the Python era. The
v4.0.0 TS rewrite seems to have reintroduced the same class of bug —
generators run regardless of detected languages.

Note: `ai-guardrails status` correctly reports `Detected languages:
TypeScript/JS, Universal`. So the detection works; the gating doesn't.

**Repro:**
```bash
mkdir /tmp/ts-only && cd /tmp/ts-only
git init && echo '{}' > package.json && echo 'console.log("hi")' > index.ts
ai-guardrails init --yes
ls -la ruff.toml staticcheck.conf   # both present — should NOT exist
```

**Fix idea:** Gate generator modules by detected languages. ruff-config
should only run if Python is detected; staticcheck-config only if Go; etc.
The existing detection pipeline emits the language set — generators just
need to consume it.

---

## BUG-005 — high — Mutates global `~/.claude/settings.json` without confirmation

**Type:** bug (silent destructive change to user-scoped shared config)
**Severity:** HIGH

`ai-guardrails install` (or `init`) silently appends a new hook entry to
`~/.claude/settings.json` — the **global, user-level** Claude Code
configuration — pointing PreToolUse hooks at `ai-guardrails-hk-cc-tools`
for `Bash|Edit|Write|NotebookEdit|Read` matcher.

Output trailer:
```text
Merged hooks into ~/.claude/settings.json
```

This is a side-effect on a shared resource:
- The hook will fire in **every** Claude Code session, not just the
  project where init was run.
- Other projects that don't want ai-guardrails enforcement now get it
  invisibly.
- The user wasn't asked. No `--yes` was passed (this was `install`, which
  doesn't have `--yes`).
- There is no obvious flag to opt out (no `--no-user-settings` documented).

**Why this matters:** Most users have a deliberately-curated global
`~/.claude/settings.json` (statusLine, plugins, environment, custom hooks,
permission rules). Silently adding to it is intrusive.

**Fix idea:** Either:
- (a) Only write to **project-scoped** `.claude/settings.json` — never
  touch user-scoped settings.
- (b) Require an explicit flag like `--user-settings` or interactive
  confirmation before merging into the user's global file.
- (c) Make the global hook a **no-op outside ai-guardrails-managed repos**
  — check `$PWD/.ai-guardrails/config.toml` exists before doing anything.

(c) is the most user-friendly: the global hook self-gates so users with
multiple projects don't have to maintain separate hook chains.

---

## BUG-006 — medium — Appends to project `CLAUDE.md` without confirmation

**Type:** bug (silent modification of user-authored doc)
**Severity:** MEDIUM

`ai-guardrails install` appended this section to the project's existing
`CLAUDE.md`:

```markdown
## AI Guardrails - Code Standards

This project uses [ai-guardrails](...) for pedantic code enforcement.
Pre-commit hooks auto-fix formatting, then run security scans, linting, and type checks.
```

No `--yes` was passed; the `--no-agent-rules` flag exists but isn't
documented as preventing CLAUDE.md mutation specifically.

**Repro:** any existing CLAUDE.md is silently appended to.

**Fix idea:** Treat `CLAUDE.md` and `AGENTS.md` as managed-when-absent,
not managed-when-present. If the file exists and isn't ai-guardrails-managed
(no SHA header), refuse to modify; emit a hint suggesting `--force` or
`--agents-only`. The hash header approach already exists for other
configs — apply it here too.

---

## BUG-007 — medium — `biome.jsonc` existing causes 4 unrelated modules to be skipped via false dependency

**Type:** bug (incorrect module dependency chain)
**Severity:** MEDIUM

When the user already has a `biome.jsonc` (correct behavior is to
preserve it):

```text
[Biome Config] biome.jsonc exists and is not managed by ai-guardrails — use --force to overwrite
```

Then **four unrelated downstream modules** are skipped on this dependency:

```text
[VS Code On-Save Linting] skipped (dependency biome-config did not complete successfully)
[Helix LSP On-Save]       skipped (dependency biome-config did not complete successfully)
[Zed On-Save Formatting]  skipped (dependency biome-config did not complete successfully)
[Baseline]                skipped (dependency biome-config did not complete successfully)
```

This is wrong:
- "Preserved existing file" is a success path, not a failure path.
- The IDE on-save modules need biome to be **installed**, not the config
  to be **written by ai-guardrails**.
- The Baseline module computes initial lint state — it doesn't need a
  freshly-written biome.jsonc; an existing one is fine.

**Fix idea:** Distinguish "module skipped intentionally (file preserved)"
from "module failed (write error)". Downstream dependents should only
gate on the latter. Or simply: the IDE / baseline modules should not
depend on biome-config writing the file — they should depend on biome
being on PATH and a usable biome.jsonc existing.

---

## BUG-008 — medium — Lefthook hooks invoke `ai-guardrails` from PATH, not from a versioned dist binary

**Type:** bug (version pinning at runtime)
**Severity:** MEDIUM

Generated `lefthook.yml` contains:
```yaml
check-suppress-comments:
  run: ai-guardrails check-suppress-comments {staged_files}
```

And `.claude/settings.json`:
```json
"command": "ai-guardrails-hk-cc-tools"
```

Both rely on PATH resolution. On this machine:
- PATH `ai-guardrails` → v3.0.0 (stale install.sh artifact)
- Local `~/Projects/ai-guardrails/dist/ai-guardrails` → v4.0.0 (freshly built)

So `init` ran with v4.0.0 (the user-invoked one), but every pre-commit
hook and every Claude Code hook will invoke v3.0.0 — silently version-split
without warning.

**Fix idea:** When `init` runs, record the invoking binary's path/version
in `.ai-guardrails/config.toml`. Generated hooks should reference that
path (or check at runtime that PATH version >= recorded version).
Alternatively: `ai-guardrails status` should warn loudly when PATH
binary diverges from the project's recorded min_version.

---

## BUG-009 — medium — `.claude/settings.json` ships a hardcoded `permissions.deny` list that competes with hook-kit's rules

**Type:** ux / design
**Severity:** MEDIUM

The generated project `.claude/settings.json` includes:

```json
"permissions": {
  "deny": [
    "Bash(rm -rf *)",
    "Bash(git push --force)",
    "Bash(git push --force *)",
    "Bash(git push -f)",
    ...30 more entries...
  ]
}
```

These overlap with what ai-guardrails-hk-cc-tools enforces dynamically.
They're also written in CC's pattern-matching DSL, which doesn't
understand flag aliases or shell-AST — so `git push -f origin main`
is denied but `git push -F=origin main` might slip through.

The dynamic hook is **strictly more capable** than the static deny list.
Shipping both creates two sources of truth, neither covering all cases.

**Fix idea:** Pick one. Recommendation: keep the dynamic hook (it's the
whole point of ai-guardrails), drop the static `permissions.deny` list
or shrink it to a minimal "even-if-the-hook-binary-is-missing" safety
net of 2-3 obviously-destructive patterns.

---

## UX-001 — minor — `--version` returns stale value when PATH binary not refreshed after release

**Type:** UX
**Severity:** minor

After ai-guardrails 4.0.0 was released and the local source tree at
`~/Projects/ai-guardrails` was rebuilt to `dist/ai-guardrails` (4.0.0),
the PATH-resident binary at `~/.local/bin/ai-guardrails` still reports
`3.0.0`. The install script (`curl … install.sh | sh`) is the canonical
upgrade path but isn't auto-discoverable from the running binary.

```text
$ ai-guardrails --version
3.0.0
$ ~/Projects/ai-guardrails/dist/ai-guardrails --version
4.0.0
```

**Expected:** `ai-guardrails --version` should hint that a newer release
is available, or `ai-guardrails status` should warn about the stale
binary when local source is detected.

---

## UX-002 — minor — Leftover `~/.local/bin/ai-guardrails-init` symlink from pre-v4 install

**Type:** UX (legacy cleanup)
**Severity:** minor

After installing v4.0.0, an old symlink survives:

```text
~/.local/bin/ai-guardrails-init -> ~/.ai-guardrails/bin/ai-guardrails-init
```

The v4.0.0 CLI does not ship `ai-guardrails-init` as a separate binary
(it's now `ai-guardrails init` subcommand). This dangling symlink is a
holdover from the pre-rewrite era. install.sh should remove it on upgrade.

**Fix idea:** Add a cleanup step to install.sh that removes known legacy
files.

---

## UX-003 — minor — Error message says `npm i -g` when local source is present

**Type:** UX
**Severity:** minor

When hook-kit binary is missing from PATH, ai-guardrails refuses to run
with:

```text
Error: hook-kit binary not found on PATH — ai-guardrails depends on it for escalation routing.
  Install with: npm i -g @questi0nm4rk/hook-kit  (or: bun i -g @questi0nm4rk/hook-kit)
```

This is correct for most users, but for someone who is **dogfooding
hook-kit** (e.g., the hook-kit maintainer running ai-guardrails inside
the hook-kit repo), the right move is "build the local source you're
sitting on top of" — not "fetch from npm." The error could detect
`./package.json` with `"name": "@questi0nm4rk/hook-kit"` and suggest
`bun run build:bin && ln -sf $(pwd)/dist/hook-kit ~/.local/bin/`.

Minor; mostly affects two people. But worth mentioning.

---
