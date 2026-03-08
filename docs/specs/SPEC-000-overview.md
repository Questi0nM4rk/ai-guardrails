# SPEC-000: Overview — AI Guardrails Production MVP

## Status: Draft
## Version: 3.0 (TypeScript rewrite)

---

## Problem

AI coding agents cheat. They add `// @ts-ignore` to silence type errors. They
weaken linter configs so their code passes. They suppress warnings with
`# noqa` and move on. `CLAUDE.md` says "don't suppress lint." The agent
suppresses lint anyway. Nothing stops it.

The existing enforcement tools ask "does the code pass?" None of them ask
"is the agent trying to weaken the system that checks it?"

---

## Solution

Three rings of defense, each catching what the last missed:

| Ring | When | What |
|------|------|------|
| Agent hooks | Real-time, in-process | Dangerous commands, config edits — before execution |
| Commit hooks | Pre-commit | Suppression comments, tampered configs, lint violations |
| CI gate | Pull request | Config freshness, new issues vs baseline |

An agent can bypass one ring. Not all three simultaneously.

---

## Philosophy

1. **Everything is an error or it's ignored.** No warnings. No "acknowledged."
   A rule either blocks or doesn't exist.
2. **Structural enforcement beats documentation.** A config file enforces.
   `CLAUDE.md` suggests.
3. **Tamper protection.** Generated configs are owned by the tool — SHA-256
   hash headers detect any edits outside `ai-guardrails generate`.
4. **Whitelist model.** Every linter runs everything by default. You subtract
   from that with explicit, reasoned exceptions.
5. **Inline suppression requires a reason.** No bare `# noqa`. The
   `ai-guardrails-allow` syntax is the only permitted path, and it demands
   a quoted reason string.

---

## Technology Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Runtime | **Bun** | Single binary, built-in TS, fast, no Node version hell |
| Language | **TypeScript** | Type system fits domain modelling; TS 7 (Go compiler) incoming |
| Config validation | **Zod** | Runtime schema validation with inferred types |
| CLI parsing | **@commander-js/extra-typings** | Well-tested, type-safe, familiar |
| Testing | **Bun test** (built-in) | No extra dep; fast; vitest-compatible API |
| TOML | **Bun built-in** | `import config from "./config.toml"` just works |
| Distribution | `bun build --compile` | Single self-contained binary; Homebrew-ready |

---

## MVP Scope

### In

- `install` — global Claude Code hooks, machine config scaffold
- `init` — per-project: detect languages, generate all configs, install hooks, CI template, agent rules
- `generate` — regenerate configs from `.ai-guardrails/config.toml`
- `generate --check` — CI: fail if configs are stale or tampered
- `snapshot` — capture current lint state as baseline
- `check` — hold-the-line: new issues vs baseline, SARIF output
- `status` — health dashboard: languages, config freshness, hook status
- `report` — recent check run history from audit log
- `hook` subcommands — dangerous-cmd, protect-configs, suppress-comments, format-stage

### Out (explicitly deferred)

- `allow` / `approve` / `query` — exception governance CLI
- `team list` / `team status` — team features
- `baseline promote` / burn-down states
- Agent attribution (detecting AI commit authors)
- Enterprise / org-level auth

---

## Target User (MVP)

Solo developer or small team managing multiple repos with AI coding agents.
Has Bun installed (every AI dev does — Claude Code extensions are TS, most
hooks are TS). Wants the tool to be zero-config to start and progressively
stricter as needed.

---

## Non-Goals

- Not a linter. Orchestrates and enforces linters.
- Not a review bot. `guardrails-review` is a separate optional integration.
- Not a service. Zero runtime — runs at commit time, CI time, or on demand.
- Not an IDE plugin. CLI only for MVP.
