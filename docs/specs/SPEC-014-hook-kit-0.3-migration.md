# SPEC-014 — hook-kit 0.3 migration (ai-guardrails v4.0)

**Status:** approved
**Date:** 2026-05-11
**Supersedes parts of:** SPEC-005 (hooks), SPEC-012 (hook binary resolution)

## Context

`@questi0nm4rk/hook-kit` 0.3.0 ships a breaking ideological shift: the
**shell wrapper (`hk`) is now the default** consumption mode. The
`claudeCodeAdapter` (formerly the only path) is now opt-in as a separate
companion binary (`hk-cc-tools`).

The shell wrapper is caller-agnostic: any process — agent, human, CI script —
can shell out through `hk -c "<cmd>"` and consume decisions via
stdout / stderr / exit-code. No JSON wire protocol.

ai-guardrails v3.x consumes hook-kit 0.2.x in library mode through a single
shell snippet (`HOOK_COMMAND` in `src/hooks/command.ts`) that invokes
`ai-guardrails hook run` for every Claude Code event. This couples
ai-guardrails entirely to Claude Code.

This spec defines v4.0: full adoption of the 0.3 shape — three binaries
(`ai-guardrails`, `ai-guardrails-hk`, `ai-guardrails-hk-cc-tools`), a single
hook entrypoint module (`src/hooks.ts`), and removal of the `hook` subcommand
surface.

## Goals

- Adopt hook-kit 0.3 as a major version bump, not a compat shim.
- Provide a caller-agnostic Bash gate (`ai-guardrails-hk`) usable by any
  agent or human shell.
- Keep dynamic TOML config (`managedFiles` / `managedPaths` /
  `protectedReadPaths` / `disabledGroups`) by reading config at binary startup
  inside the compiled `hooks.ts`.
- Preserve all existing rule semantics, BDD coverage, and lefthook helpers.

## Non-goals

- Per-project compiled binaries. ai-guardrails ships a single binary set;
  projects do not run `hook-kit build`.
- Bundling `hook-kit broker`. Users who want multi-agent escalation install
  `@questi0nm4rk/hook-kit` separately and put `hook-kit` on PATH.
- Backward-compat shim for `ai-guardrails hook run`. Users with stale
  `.claude/settings.json` regenerate via `ai-guardrails generate`.
- Adapter binaries for non-Claude harnesses. Documented as a v4.x
  follow-up; v4.0 ships shell + cc-tools only.

## Architecture

### Binary set

```
dist/
├── ai-guardrails              # main CLI (init, check, generate, status, …)
├── ai-guardrails-hk           # shell wrapper — replaces `bash -c`. Caller-agnostic.
└── ai-guardrails-hk-cc-tools  # CC tool-call adapter (Bash + Edit/Write/NotebookEdit/Read)
```

All three distributed via `scripts/install.sh` into `~/.local/bin/`. The
release workflow rebuilds all three per platform-matrix entry on tag push.

### Single source for both hk binaries: `src/hooks.ts`

```typescript
// src/hooks.ts — compiled into both ai-guardrails-hk and ai-guardrails-hk-cc-tools
import { createModule } from "@questi0nm4rk/hook-kit";
import { buildAllModules } from "@/check/to-hook-kit";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { suppressCommentsRule } from "@/check/rules/suppress-comments";

const LABEL = "[ai-guardrails]";

const config = await loadHookConfig();           // reads cwd()/.ai-guardrails/config.toml
const ruleset = buildRuleSet(config);

export default [
  ...buildAllModules(ruleset, LABEL),
  createModule(
    {
      id: "suppress-comments",
      name: "Suppress unjustified linter-disable comments",
      events: ["PostToolUse"],
      matchers: ["Edit", "Write", "NotebookEdit"],
    },
    [suppressCommentsRule()],
  ),
];
```

Config loading happens once per process invocation. Cold start: ~50ms (bun
bytecode) + ~1ms (smol-toml parse). Single-shot process — no caching.

### Build commands

```bash
# package.json scripts:
"build"        : bun build src/cli.ts --compile --bytecode --production --outfile dist/ai-guardrails
"build:hk"     : hook-kit build src/hooks.ts --out dist/ai-guardrails-hk --adapter shell
"build:hk-cc"  : hook-kit build src/hooks.ts --out dist/ai-guardrails-hk-cc-tools --adapter cc-tools --hook-timeout 60
"build:all"    : bun run build && bun run build:hk && bun run build:hk-cc
```

### Generated `.claude/settings.json`

```json
{
  "permissions": { "deny": [...] },
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash|Edit|Write|NotebookEdit|Read",
      "hooks": [{
        "type": "command",
        "command": "<resolved-path>/ai-guardrails-hk-cc-tools",
        "timeout": 60
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|Write|NotebookEdit",
      "hooks": [{
        "type": "command",
        "command": "<resolved-path>/ai-guardrails-hk-cc-tools",
        "timeout": 60
      }]
    }]
  }
}
```

Key changes from v3.x:
- `command -v ai-guardrails && command -v hook-kit` shell guard removed.
  Path resolved at `init` time; hook-kit fails open per its Iron Law 4.
- Single binary covers all matchers (no per-event branch).
- `HOOK_KIT_ASKPASS` not set by default — escalations fall through to CC's
  native ask UI. Documented opt-in: set `HOOK_KIT_ASKPASS=hook-kit broker --askpass`
  in project config to route through the broker tree.

### Hook timeout: 60 seconds

| Limit | Value | Source |
|---|---|---|
| CC default Bash tool timeout | 120 s | `BASH_DEFAULT_TIMEOUT_MS` |
| CC max Bash tool timeout | 600 s | `BASH_MAX_TIMEOUT_MS` |
| CC default hook timeout | 60 s | hooks.json `timeout` default |
| **ai-guardrails hook timeout** | **60 s** | `--hook-timeout 60` |

The hook process must complete (or escalate-and-receive-response) inside
the agent's Bash tool timeout, otherwise the agent abandons the call and
the hook orphans. 60 s matches CC's default hook timeout and stays well
under the 120 s default bash tool budget. Users who need longer escalation
windows bump both `BASH_DEFAULT_TIMEOUT_MS` and the hook `timeout` field.

## CLI surface (v4.0 breaking changes)

| Change | Before (v3.x) | After (v4.0) |
|---|---|---|
| Removed | `ai-guardrails hook run` | replaced by `ai-guardrails-hk-cc-tools` binary |
| Removed | `ai-guardrails hook suppress-comments` | now a `content()` rule inside hk-cc-tools, fires on PostToolUse |
| Promoted | `ai-guardrails hook format-stage` | `ai-guardrails format-stage` |
| Promoted | `ai-guardrails hook allow-comment` | `ai-guardrails allow-comment` |
| Removed | `ai-guardrails hook` (parent subcommand) | — |

`lefthook.yml` regenerator updated to call the promoted commands.

## Source layout

```
src/
├── hooks.ts                   # NEW — hook-kit module entrypoint
├── hooks/
│   ├── format-stage.ts        # KEEP — used by promoted CLI command
│   ├── allow-comment.ts       # KEEP — used by promoted CLI command
│   ├── command.ts             # DELETE
│   ├── run.ts                 # DELETE
│   └── suppress-comments.ts   # MOVE to src/check/rules/suppress-comments.ts
├── check/
│   ├── to-hook-kit.ts         # KEEP — translator unchanged
│   ├── ruleset.ts             # KEEP — TOML loader unchanged
│   └── rules/
│       ├── suppress-comments.ts  # MOVED from src/hooks/
│       ├── paths.ts           # KEEP
│       └── groups/            # KEEP
├── commands/
│   ├── hook.ts                # DELETE
│   ├── format-stage.ts        # NEW — promoted from hook subcommand
│   └── allow-comment.ts       # NEW — promoted from hook subcommand
└── generators/
    ├── claude-settings.ts     # MODIFIED — new hook command, no shell guard
    └── lefthook.ts            # MODIFIED — calls promoted commands
```

## Distribution

`scripts/install.sh` extends to download all three binaries from the
release tarball. Disk footprint: ~150 MB per platform install (3 × ~50 MB
bun-compiled binaries).

`.github/workflows/release.yml` extends the platform matrix to build
`build:all` instead of `build`.

## BDD test path

`isDangerous()` (currently in `src/hooks/run.ts`) moves to a small
`src/check/in-process.ts` helper that uses hook-kit's `evaluate()` with
synthesized events. Test imports update:

```typescript
import { isDangerous } from "@/check/in-process";
```

Existing test fixtures and step files unchanged.

## Escalation defaults

- `HOOK_KIT_ASKPASS` unset → escalations fall through to CC's native ask UI.
  This is the v4.0 default. Most users want this.
- `HOOK_KIT_ASKPASS=hook-kit broker --askpass` → routes through the broker
  tree. Requires `hook-kit` binary on PATH (`bun add -g @questi0nm4rk/hook-kit`).
  Documented in README under "Multi-agent escalation".

## Migration mechanics

v3.x users upgrade with:

```bash
ai-guardrails install --upgrade   # pulls v4 binaries into ~/.local/bin
ai-guardrails generate            # rewrites .claude/settings.json + lefthook.yml
```

No project-side config changes required. The TOML schema is unchanged.

## Acceptance criteria

1. `bun run build:all` produces three binaries totaling ~150 MB.
2. `dist/ai-guardrails-hk -c "git push --force origin main"` exits 1, prints
   `[ai-guardrails] needs review: …` to stdout.
3. `dist/ai-guardrails-hk -c "ls /tmp"` exits 0, executes ls transparently.
4. `dist/ai-guardrails-hk-cc-tools` reads CC hook event JSON on stdin,
   responds with the CC ask/deny JSON envelope.
5. `.claude/settings.json` generated by `ai-guardrails generate` contains
   exactly two PreToolUse / PostToolUse blocks, both pointing at the
   resolved `ai-guardrails-hk-cc-tools` path with `timeout: 60`.
6. All existing BDD scenarios pass (the `isDangerous()` import path
   updates; no behavior change).
7. `ai-guardrails hook ...` exits 1 with "Unknown command".
8. `ai-guardrails format-stage <files>` and `ai-guardrails allow-comment <args>`
   work identically to their previous `hook ...` invocations.
9. v3.x project with stale `.claude/settings.json` runs `generate` and gets
   a working v4 wiring without manual edits.
10. Cold start of `ai-guardrails-hk-cc-tools` against a synthetic
    PreToolUse event ≤ 100 ms wall time.

## Decisions & Trade-offs

### Chose vs over

| Chose | Over | Because |
|---|---|---|
| Three binaries (`ai-guardrails`, `ai-guardrails-hk`, `ai-guardrails-hk-cc-tools`) | Single multiplexed binary (`ai-guardrails hk -c …`) | Cold-start path matters for hooks. A dedicated bytecode binary gives ~50ms cold start; subcommand routing through the main CLI adds Commander's setup cost (~80–120ms) per invocation. |
| Namespaced names (`ai-guardrails-hk`) | Generic names (`hk`) | Avoids PATH collision with users who installed `@questi0nm4rk/hook-kit` directly or another tool's `hk`. Clear ownership; trivial cost (longer to type). |
| Runtime config load inside `hooks.ts` | Per-project compile at `init` | One distributed binary set, no Bun-at-init dependency, no committed binaries per project. The ~1ms TOML parse is invisible against the 50ms cold start. |
| Single binary for all CC matchers (`Bash\|Edit\|Write\|NotebookEdit\|Read`) | Per-matcher binaries | hook-kit's matcher filter inside the engine is ~free. Per-matcher binaries triple the install size with no perf gain. |
| `--hook-timeout 60` (matches CC default) | `--hook-timeout 600` (CC max) or unset | The hook process must complete inside the agent's Bash tool budget. CC's default Bash budget is 120s; 60s leaves clean headroom and matches CC's own hook timeout default. Users with longer escalation needs bump both `BASH_DEFAULT_TIMEOUT_MS` and the hook timeout — explicit deployment decision, not a code change. |
| Hard-remove `ai-guardrails hook run` | Deprecation shim | v4.0 is already a major bump (hook-kit dependency is breaking). Carrying a shim for 1–2 versions adds dead code with no real upgrade-path benefit — `ai-guardrails generate` rewrites `.claude/settings.json` cleanly. |
| Promote `format-stage`/`allow-comment` to top-level | Keep under `hook` | They're lefthook helpers, not Claude hooks. The `hook` namespace was a misnomer once `hook run` is gone. |
| Drop the `command -v` fail-open shell guard | Keep it for safety | hook-kit's Iron Law 4 already fails open on infra errors (missing deps, parse failures, throws). The shell guard duplicated that and added per-invocation `command -v` cost. |
| Assume `hook-kit` on PATH for broker | Bundle `hook-kit broker` binary | Multi-agent escalation is an advanced use case (orchestrator listening for sub-agent escalations). Most users hit the CC native ask UI fallthrough. Not worth the 50MB binary cost for everyone. |
| TOML parse on every hook fire | Cache to disk / stat-and-mtime | Parse cost is ~1ms against a ~50ms cold start. Caching adds invalidation complexity and a stat call. Not worth it. |
| `claudeCodeAdapter` tool-name vocabulary as the canonical rule vocabulary | Neutral abstract names | hook-kit's adapter shape is already the abstraction. Inventing a second vocabulary layer just renames identifiers without buying portability. |

## Operational Readiness

### Observability

- `HOOK_KIT_VERBOSE=1` emits one stderr trace line per evaluation (event,
  tool, session, module count, decision kind, label, reason, time). Enable
  per-shell to debug a misfiring rule without changing rule code.
- Each hook decision carries a `[ai-guardrails]` label for source attribution
  in mixed-hook environments.
- Broker spool inspectable on disk when escalations route through the
  broker: `cat ~/.cache/hook-kit/sessions/$SESSION_ID/audit.jsonl`.

### Failure modes

| Failure | Behavior | Detection |
|---|---|---|
| `ai-guardrails-hk-cc-tools` binary missing | CC hook config misses entirely; CC may warn or skip | `ai-guardrails generate --check` flags drift |
| TOML config malformed | Falls back to `DEFAULT_PATH_RULES` + `ALL_RULE_GROUPS`; stderr warning from `loadHookConfig` | stderr line on every hook fire |
| Rule throws | hook-kit catches, treats as `null` (silent allow), Iron Law 4 | `HOOK_KIT_VERBOSE=1` shows the throw |
| Stdin malformed (cc-tools) | Adapter exits 0 silently (Iron Law 4) | hook fires but doesn't gate — symptom: rule didn't fire when expected |
| `escalate` with broken broker (`HOOK_KIT_ASKPASS` set, binary missing) | Deny with `[hook-kit] askpass …` (Iron Law 4 exception) | stderr `[hook-kit] askpass` message |
| Hook exceeds 60s timeout | CC kills hook process; CC's tool call fails with hook timeout error | CC reports hook timeout; user-visible |
| shell-AST WASM fails to load | All command/pipe/redirect rules return `null` (silent), stderr warning | stderr warning from hook-kit |

### Deployment

- `scripts/install.sh` writes three binaries atomically (download to
  temp, then `mv` into place). Partial install failure leaves previous
  versions intact.
- CI gate: `.github/workflows/ai-guardrails.yml` runs `bun run build:all`
  + full test suite + `dist/ai-guardrails check --project-dir .`
  (self-dogfood) on every PR.
- Smoke test in CI: `dist/ai-guardrails-hk -c "git push --force origin main"`
  must exit 1; `dist/ai-guardrails-hk -c "ls /tmp"` must exit 0.

### Rollback

- v3.x users: `ai-guardrails install --version 3.x.y && ai-guardrails generate`.
- Per-binary rollback not supported — the three binaries are released as
  a set and pinned to the same version.

### Performance budget

- Cold start of `ai-guardrails-hk-cc-tools` against a synthetic
  PreToolUse event: ≤ 100 ms wall time on a current laptop.
- TOML config parse: ≤ 5 ms for typical config files.
- Rule evaluation against a single event: ≤ 5 ms (engine measured time
  matches hook-kit's published numbers).

## Change triggers

The design assumes the following. If any of them changes, revisit the noted area.

- **Assumes:** Cold start of bun-compiled binaries stays under 100ms. **If**
  a profile shows the wrapper adds noticeable latency to interactive use
  or the hook starts hitting the 60s timeout from cold-start cost alone
  → drop bytecode (`bun build --compile` without `--bytecode`) for
  smaller faster-start binaries, or split out a long-running daemon.
  Rule semantics stay the same.

- **Assumes:** CC's Bash tool default timeout (`BASH_DEFAULT_TIMEOUT_MS`) is
  ≥ 60s. **If** CC drops the default below 60s → bump `--hook-timeout` to
  match the new floor. Check CC release notes on every hook-kit upgrade.

- **Assumes:** TOML config is the only dynamic input. **If** a feature
  requires per-event dynamic config (e.g. per-file rule sets pulled from
  remote configuration) → that data must be loadable at process startup
  inside `hooks.ts`, or the design needs a daemon model.

- **Assumes:** Hook-kit's `claudeCodeAdapter` JSON envelope shape stays
  stable across 0.3.x. **If** hook-kit ships a 0.4 with envelope changes
  → bump the dependency major and re-verify the cc-tools binary against
  CC's hook event format. Treat as another major migration.

- **Assumes:** Three ~50MB binaries per platform install (~150MB total) is
  acceptable disk footprint. **If** install-size complaints arise →
  switch the main `ai-guardrails` binary to non-bytecode build (smaller,
  slower start, but it's a CLI not a hook), or move to a shared bun
  runtime model.

- **Assumes:** Most users do not need multi-agent escalation; CC's native
  ask UI is sufficient. **If** broker-tree usage becomes common (e.g.
  multiple users on a single CC-orchestrator setup hit it) → bundle
  `hook-kit broker` in the install script and wire `HOOK_KIT_ASKPASS` by
  default.

- **Assumes:** `ai-guardrails` is the only consumer of the rule data
  modules under `src/check/`. **If** another tool wants to consume the
  same rule definitions → extract `src/check/` into its own published
  package, hook-kit-style, before doing it.

- **Assumes:** Project authors regenerate `.claude/settings.json` via
  `ai-guardrails generate` after upgrading the binary. **If** users
  routinely hand-edit `.claude/settings.json` → the generator needs a
  merge mode that preserves user additions while updating the
  ai-guardrails-managed entries.

- **Assumes:** Iron Law 4 (fail-open on infra errors, deny only on
  escalate-infra failures) is the right default for ai-guardrails. **If**
  ai-guardrails takes on a use case where silent failure is unacceptable
  (e.g. compliance / audit) → that's a new mode requiring an explicit
  decision-kind, not a tweak to the existing fail-open path.

## Out of scope

- New harness adapters (Cursor, Aider, OpenCode, KiloCode tools).
- A `--hook-timeout` flag at the project-config level. Hardcoded at build
  time in v4.0; revisit if multiple users need different defaults.
- Bundling `hook-kit broker` in the install script.
- Migrating from TOML config to a different format.
- A merge mode for `.claude/settings.json` generation.
