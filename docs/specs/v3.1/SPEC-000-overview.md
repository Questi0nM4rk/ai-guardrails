# SPEC-000: Overview

## Status: Draft
## Version: 3.1
## Last Updated: 2026-03-20

---

## Problem

AI coding agents cheat. They add `// @ts-ignore` to silence type errors. They
weaken linter configs so their code passes. They suppress warnings with
`# noqa` and move on. `CLAUDE.md` says "don't suppress lint." The agent
suppresses lint anyway. Nothing stops it.

The existing enforcement tools ask "does the code pass?" None of them ask
"is the agent trying to weaken the system that checks it?"

Teams using AI assistants (Claude Code, Cursor, Copilot) need structural
enforcement — not documentation, not guidelines, but hard stops that agents
cannot bypass. The enforcement must cover three vectors: the commands the agent
runs (destructive shell commands), the files it edits (config tampering), and
the code it writes (inline suppressions, quality regressions).

---

## Solution

Three rings of defense, each catching what the last missed:

| Ring | When | What |
|------|------|------|
| Agent hooks | Real-time, in-process | Dangerous commands, config edits, sensitive reads — blocked before execution |
| Commit hooks | Pre-commit | Suppression comments, tampered configs, formatting, secret leaks |
| CI gate | Pull request | Config freshness, new issues vs baseline, hold-the-line enforcement |

An agent can bypass one ring. Not all three simultaneously.

A single CLI binary (`ai-guardrails`) handles all three: it generates pedantic
linter configs, installs pre-commit hooks via lefthook, wires Claude Code
PreToolUse hooks, sets up CI workflows, and enforces a hold-the-line baseline
where only NEW issues fail the check.

v3.1 adds an interactive init wizard where every setup action is a modular
y/n choice, profile-based rule filtering, `ai-guardrails-allow` inline comment
integration in `checkStep`, `allow` and `query` CLI commands, shell completion,
a basic .NET runner (dotnet build warning parsing), and distribution via both
GitHub Releases and npm publish.

---

## Philosophy

1. **Everything is an error or it's ignored.** No warnings. No "acknowledged."
   A rule either blocks or doesn't exist.
   WHY: Warnings train developers to ignore alerts. A warning that nobody reads
   is worse than no check at all — it creates a false sense of security.

2. **Structural enforcement beats documentation.** A config file enforces.
   `CLAUDE.md` suggests.
   WHY: Documentation is advisory. Agents read documentation and choose to ignore
   it. Config files are structural — the tool either passes or fails, there is
   no "choose to ignore."

3. **Tamper protection.** Generated configs are owned by the tool — SHA-256
   hash headers detect any edits outside `ai-guardrails generate`.
   WHY: Without tamper detection, an agent can weaken configs silently. The hash
   header makes any change detectable — CI catches it, pre-commit catches it.

4. **Whitelist model.** Every linter runs everything by default. You subtract
   from that with explicit, reasoned exceptions.
   WHY: Blacklist models miss new rules. Whitelist models catch everything by
   default and only allow what's been consciously decided.

5. **Inline suppression requires a reason.** No bare `# noqa`. The
   `ai-guardrails-allow` syntax is the only permitted path, and it demands
   a quoted reason string.
   WHY: Bare suppressions are agent escape hatches. Requiring a reason creates
   friction that makes agents explain themselves, creating audit trails.

6. **Composition over inheritance.** Every component is an interface, composed
   at the call site. No `extends`, no class hierarchies, no IoC containers.
   WHY: Inheritance creates coupling. When Runner A extends BaseRunner, changes
   to BaseRunner cascade to all runners. Composition keeps each component
   independently testable and replaceable.

7. **Zero unsafe type operations.** No `any`, no `as` casts, no `!` assertions.
   Zod at system boundaries, `in`-operator narrowing for type guards.
   WHY: Type safety is the first line of defense against bugs. Every `as` cast
   is a lie to the compiler — and lies compound.

---

## Constraints

### Hard Constraints

- **Bun >= 1.2.0** as runtime — binary compilation, built-in TS, fast startup
- **TypeScript strict mode** — `strict`, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`
- **No `any`** — use `unknown` + Zod at boundaries
- **No `as` casts** — use `in`-operator narrowing or Zod parsing
- **No `!` non-null assertions** — handle `undefined` explicitly
- **No barrel files** (`index.ts`) — explicit named imports only
- **No inheritance** — `implements` only, composition over inheritance (except Error subclasses)
- **No direct infra access** in domain code — all I/O through injected interfaces
- **Max 200 lines per file** — split if larger

### Soft Constraints

- Prefer `smol-toml` over Bun built-in TOML (Bun lacks `stringify`)
- Prefer `minimatch` for glob matching (consistent API)
- Prefer Gherkin/BDD for behavior tests, bun:test for unit tests
- Prefer `@commander-js/extra-typings` for CLI (type-safe, familiar)

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| Bun cross-compilation covers Linux + macOS (x64 + arm64) | Bun drops a target | Fall back to GitHub Actions matrix with native runners |
| ruff remains the Python linter standard | ruff deprecated | Evaluate flake8 + isort + black, update SPEC-003 |
| biome v2 maintains rdjson output | biome changes format | Update parser in biome runner, update fixtures |
| lefthook v2+ is maintained | lefthook abandoned | Evaluate husky, update SPEC-006 |
| smol-toml maintains stringify() | smol-toml deprecated | Evaluate @iarna/toml or write minimal stringifier |
| Claude Code PreToolUse hook API is stable | API changes | Update hook runner input parsing, update SPEC-005 |

---

## Technology Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Runtime | Bun >= 1.2.0 | Single binary compilation, built-in TS, fast startup (~50ms) |
| Language | TypeScript (strict) | Type system fits domain modelling; compile-time safety |
| Config validation | Zod | Runtime schema validation with inferred types at boundaries |
| CLI parsing | @commander-js/extra-typings | Type-safe, well-tested, familiar |
| TOML | smol-toml | Read + write (Bun built-in has no stringify) |
| Glob matching | minimatch | For isAllowed() and ignore path filtering |
| Shell parsing | @questi0nm4rk/shell-ast | AST-based command analysis for hook engine |
| Testing | bun:test + @questi0nm4rk/feats | Built-in runner + BDD/Gherkin for behavior tests |
| Pre-commit | lefthook | Fast, Go binary, stage_fixed replaces lint-staged |
| Distribution | bun build --compile + npm publish | Cross-platform single binaries (Linux + macOS) + npm package |

---

## Scope

### In (v3.1)

- `init` — interactive wizard with modular feature selection (under 30 seconds)
- `check` — hold-the-line with content-stable baseline, `ai-guardrails-allow` comment integration
- `snapshot` — capture current lint state (excludes issues with allow comments)
- `status` — new/fixed/baseline counts
- `generate` — regenerate configs with language gates and profile-based rule selection
- `report` — text + SARIF output
- `hook` — dangerous-cmd, protect-configs, protect-reads, suppress-comments
- `allow` — `ai-guardrails allow <rule> <glob> "<reason>"` — register permanent exception
- `query` — `ai-guardrails query <rule>` — inspect active allow entries for a rule
- `completion` — shell completion (bash, zsh, fish) — implemented
- 9 language plugins, 13 linter runners (including basic .NET runner: dotnet build warning parsing)
- 8 config generators with hash headers and profile-aware rule selection
- Cross-platform binary distribution (GitHub Releases + npm publish)
- Install script with SHA-256 verification

### Out (explicitly deferred to v3.2+)

- Hook audit trail (JSONL logging) — v3.2
- Baseline diff and trend reporting — v3.2
- Interactive triage CLI — v3.2
- Hook system audit and shell tokenizer replacement — v3.2
- Monorepo/workspace support — v4
- Agent attribution (detect AI-generated commits) — v4
- Governance hierarchy (org → team → project config) — v4

---

## Target Users

- Developers using AI coding assistants (Claude Code, Cursor, Copilot, Windsurf, Cline)
- Teams wanting structural enforcement of code standards
- Projects with existing technical debt needing hold-the-line baseline

---

## Testing Strategy

**Framework:** `bun:test` for unit tests, `@questi0nm4rk/feats` for Gherkin BDD scenarios.

**Fakes, not mocks:** `FakeFileManager` (in-memory), `FakeCommandRunner` (canned responses), `FakeConsole` (captures messages).

**Coverage:** 896+ tests across 51 files. 85%+ line coverage target.

**Self-dogfood:** The binary runs its own `check` on its own codebase in CI.

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| Bun is the runtime | Migrating to Node or Deno | All compilation, TOML handling, test runner |
| TypeScript strict mode | Relaxing strictness | All type safety guarantees, SPEC-001 interfaces |
| 13 linter runners | Adding new language support | SPEC-003, language plugins, generators |
| Hold-the-line baseline | Changing to zero-tolerance | SPEC-007, check exit code semantics |
| PreToolUse hook API | Claude Code API changes | SPEC-005, hook runner, settings generator |
| GitHub Releases + npm as distribution | Distribution channel changes | SPEC-009, install script, publish workflow |

---

## Cross-References

- SPEC-001: Architecture — module structure and core interfaces
- SPEC-002: Config System — schema hierarchy and merge rules
- SPEC-003: Linter System — runners and language plugins
- SPEC-004: CLI Commands — all commands, flags, exit codes
- SPEC-005: Hook System — check engine and PreToolUse hooks
- SPEC-006: Config Generators — 8 generators, hash headers, language gates
- SPEC-007: Baseline System — fingerprinting and hold-the-line
- SPEC-008: Interactive Init — modular wizard system
- SPEC-009: Release & Distribution — cross-platform builds and install script
